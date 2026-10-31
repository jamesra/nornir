"""Read and edit the nornir-improve-loop ledger without hand-written read-modify-write code.

Adapted from the Viking improve loops' ``ledger.py``. Every write copies the ledger to ``ledger.json.bak``,
writes a temp file and renames it into place (retrying briefly if Windows holds the file), and keeps the file's
UTF-8 BOM (if any) and line endings. ``{"value": [...]}`` wrappers left by PowerShell writes are unwrapped.

Usage (run with ``$PY -I``)::

    ledger.py LEDGER brief                                 # compact wake state + STEERING.md directives
    ledger.py LEDGER keys                                  # top-level keys with type and size
    ledger.py LEDGER get KEY
    ledger.py LEDGER set KEY JSON
    ledger.py LEDGER append KEY JSON
    ledger.py LEDGER incr KEY [N]
    ledger.py LEDGER update KEY FIELD=VALUE JSON_OBJECT    # merge into list entries whose FIELD equals VALUE
    ledger.py LEDGER upsert KEY FIELD=VALUE[,FIELD=VALUE] JSON_OBJECT   # update the match, else append
    ledger.py LEDGER remove KEY FIELD=VALUE                # drop list entries whose FIELD equals VALUE
    ledger.py LEDGER unset KEY                             # delete a key (fails if absent)

KEY may be dotted (``runner.heartbeatAt``); a ``null`` on the way becomes ``{}``. JSON may be ``@path`` (read
from a file) or ``-`` (stdin), which avoids PowerShell quoting. VALUE ``null`` matches a JSON null. ``update``
and ``remove`` fail when no entry matches, so a typo never passes silently. A top-level key outside the schema
in SKILL.md "Ledger" is written but warned about on stderr.
"""

import io
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

BOM: bytes = b"\xef\xbb\xbf"

# Keep in step with the schema under "Ledger" in SKILL.md.
SCHEMA_KEYS: frozenset[str] = frozenset({
    "startedAt", "deadline", "intervalMinutes", "nextWakeAt", "stop", "environment", "runner", "launchDirty",
    "branches", "mutationMode", "toolCommands", "hotspots", "baselineFailures", "flaky", "lastCategory",
    "wakeCount", "wakesSinceCompact", "compactSummary", "emptyWakes", "portStage", "portEvidence", "candidate",
    "commits", "countsSincePublish", "publishes", "pyreBuilds", "rejected", "deferred", "proposals", "decisions",
    "reworked", "mirrorPending", "tracker", "trackerIssues", "lastSync", "syncSkips", "modelSubstitutions",
    "lastReportAt", "reports",
})

STEERING_PREFIXES: tuple[str, ...] = ("focus:", "avoid:", "answer:")
STEERING_WORDS: frozenset[str] = frozenset({"pause", "stop"})


def load(path: str) -> tuple[dict[str, Any], bool, str]:
    """Return (data, has_bom, newline) for the ledger at ``path``."""
    with open(path, "rb") as f:
        raw = f.read()
    has_bom = raw.startswith(BOM)
    newline = "\r\n" if b"\r\n" in raw else "\n"
    data = json.loads(raw.decode("utf-8-sig"))
    for key, value in list(data.items()):
        if isinstance(value, dict) and set(value) == {"value"}:
            data[key] = value["value"]
    return data, has_bom, newline


def save(path: str, data: dict[str, Any], has_bom: bool, newline: str) -> None:
    """Back up ``path``, then replace it atomically with ``data`` in the file's original encoding and line endings."""
    shutil.copyfile(path, path + ".bak")
    text = json.dumps(data, indent=2, ensure_ascii=False).replace("\n", newline)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "wb") as f:
        if has_bom:
            f.write(BOM)
        f.write(text.encode("utf-8"))
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: an editor, indexer or antivirus briefly holds the file
            if attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


def parse_json(arg: str) -> Any:
    """Parse a JSON argument given inline, as ``@path``, or as ``-`` for stdin."""
    if arg == "-":
        return json.loads(sys.stdin.read())
    if arg.startswith("@"):
        with open(arg[1:], encoding="utf-8-sig") as f:
            return json.load(f)
    return json.loads(arg)


def resolve(data: dict[str, Any], key: str) -> tuple[dict[str, Any], str]:
    """Return the container holding the last part of dotted ``key``, and that part."""
    parts = key.split(".")
    node = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    return node, parts[-1]


def matches(entry: Any, selector: str) -> bool:
    """True when ``entry`` has every ``FIELD=VALUE`` in comma-separated ``selector`` (compared as text)."""
    if not isinstance(entry, dict):
        return False
    for clause in selector.split(","):
        field, _, value = clause.partition("=")
        actual = entry.get(field)
        if not (actual is None if value == "null" else str(actual) == value):
            return False
    return True


def parse_time(value: Any) -> datetime | None:
    """Parse an ISO-8601 ledger timestamp, or return None for an empty or unparsable value."""
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def steering_lines(ledger_path: str) -> list[str]:
    """Directive lines of ``$LOOP_ROOT/STEERING.md`` (the ledger lives in ``$LOOP_ROOT/.loop``)."""
    steering = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(ledger_path))), "STEERING.md")
    if not os.path.exists(steering):
        return [f"MISSING {steering}: recreate the template; no steering this wake"]
    with open(steering, encoding="utf-8-sig") as f:
        lines = [line.strip() for line in f]
    directives = [line for line in lines if line.startswith(STEERING_PREFIXES) or line in STEERING_WORDS]
    other = sum(1 for line in lines if line and not line.startswith("#") and line not in directives)
    return directives + ([f"(+{other} guidance lines; read the file)"] if other else [])


def brief(data: dict[str, Any], ledger_path: str) -> dict[str, Any]:
    """The small slice of the ledger a wake needs to decide what to do."""
    now = datetime.now(UTC)
    deadline = parse_time(data.get("deadline"))
    last_report = parse_time(data.get("lastReportAt") or data.get("startedAt"))
    open_decisions = [
        {"id": d.get("id"), "answered": d.get("answer") is not None, "answerSource": d.get("answerSource")}
        for d in data.get("decisions", [])
        if d.get("answer") is None or not d.get("answerSource")
    ]
    return {
        "now": now.isoformat(timespec="seconds"),
        "deadline": data.get("deadline"),
        "startedAfterDeadline": bool(deadline and now >= deadline),
        "stop": data.get("stop", False),
        "dailyReportDue": bool(last_report and now - last_report >= timedelta(hours=24)),
        "wakeCount": data.get("wakeCount", 0),
        "wakeParity": "odd (port)" if data.get("wakeCount", 0) % 2 else "even (rotation)",
        "emptyWakes": data.get("emptyWakes", 0),
        "lastCategory": data.get("lastCategory"),
        "portStage": data.get("portStage"),
        "candidate": data.get("candidate"),
        "countsSincePublish": data.get("countsSincePublish", 0),
        "openDecisions": open_decisions,
        "runner": data.get("runner"),
        "sizes": {k: len(v) for k, v in data.items() if isinstance(v, list)},
        "steering": steering_lines(ledger_path),
    }


def main(argv: list[str]) -> None:
    """Run one ledger command; see the module docstring."""
    if isinstance(sys.stdout, io.TextIOWrapper):  # Windows consoles default to a legacy code page
        sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) < 3 or (len(argv) < 4 and argv[2] not in ("brief", "keys")):
        sys.exit(__doc__)
    path, command = argv[1], argv[2]
    data, has_bom, newline = load(path)
    if command == "brief":
        print(json.dumps(brief(data, path), indent=1, ensure_ascii=False))
        return
    if command == "keys":
        for k, v in data.items():
            size = len(v) if isinstance(v, (list, dict, str)) else v
            print(f"{k}\t{type(v).__name__}\t{size}")
        return

    key, args = argv[3], argv[4:]
    node, last = resolve(data, key)
    if command == "get":
        print(json.dumps(node.get(last), indent=2, ensure_ascii=False))
        return
    if command == "set":
        node[last] = parse_json(args[0])
    elif command == "unset":
        if last not in node:
            sys.exit(f"no key {key}")
        del node[last]
    elif command == "append":
        node.setdefault(last, []).append(parse_json(args[0]))
    elif command == "incr":
        node[last] = (node.get(last) or 0) + (int(args[0]) if args else 1)
    elif command in ("update", "remove", "upsert"):
        entries = node.setdefault(last, []) if command == "upsert" else node.get(last) or []
        hits = [e for e in entries if matches(e, args[0])]
        if command == "upsert" and not hits:
            entries.append(parse_json(args[1]))
        elif not hits:
            sys.exit(f"no entry in {key} has {args[0]}")
        elif command == "remove":
            node[last] = [e for e in entries if not matches(e, args[0])]
        else:
            patch = parse_json(args[1])
            for entry in hits:
                entry.update(patch)
    else:
        sys.exit(f"unknown command {command}\n{__doc__}")
    top = key.split(".")[0]
    if top not in SCHEMA_KEYS:
        print(f"warning: top-level key {top!r} is not in the SKILL.md Ledger schema", file=sys.stderr)
    save(path, data, has_bom, newline)


if __name__ == "__main__":
    main(sys.argv)
