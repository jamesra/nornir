#!/usr/bin/env python3
"""Create one private GitHub issue per Nornir bug-review finding. Resumable.

Reads findings.json, creates the target private repo and its labels if needed,
then files one issue per finding. Every finding is recorded in
created_issues.json *before* the creating API call and updated with the issue
URL immediately after, so an interrupted, killed or rate-limited run can be
restarted with the same command without double-filing or losing an entry.

Prerequisites (real runs only; --dry-run needs none of them):
  * gh CLI installed and authenticated with `repo` scope
    (`gh auth status` must succeed, or set GH_TOKEN)

Usage:
  python create_issues.py --dry-run          # print what would be created
  python create_issues.py --setup-only       # create repo + labels, no issues
  python create_issues.py --limit 3          # smoke test
  python create_issues.py                    # create everything (resumable)
  python create_issues.py --severity P0 P1   # file only the higher severities
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINDINGS = HERE / "findings.json"
LEDGER = HERE / "created_issues.json"

DEFAULT_REPO = "nornir-review"
MASTER_DOC = ".cursor/nornir-bug-review-master.md"

# GitHub hard limits.
TITLE_MAX = 256
LABEL_DESC_MAX = 100

SEVERITY_COLORS = {"P0": "b60205", "P1": "d93f0b", "P2": "fbca04", "P3": "c2e0c6"}
TYPE_COLORS = {"bug": "d73a4a", "perf": "0e8a16", "parity": "5319e7", "debt": "cfd3d7"}
STATUS_COLORS = {"confirmed": "0052cc", "open": "ededed"}
FALLBACK_COLOR = "ededed"

SEVERITY_TEXT = {
    "P0": "P0 - data loss or wrong science",
    "P1": "P1 - silent wrong output",
    "P2": "P2 - performance or operational pain",
    "P3": "P3 - maintainability / debt",
}
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

WAVE_TEXT = {
    1: "Wave 1 - hangs and fail-open gates (small diffs, large blast radius)",
    2: "Wave 2 - stop destroying or silently corrupting output",
    3: "Wave 3 - the Flip/Flop coordinate contract",
    4: "Wave 4 - memory and throughput",
    5: "Wave 5 - parity and debt",
}

UNVERIFIED_NOTE = (
    "> **Not yet reproduced.** This finding comes from static reading of the "
    "source, not from an observed failure. Confirm it with a test that fails "
    "before the fix and passes after, and only then treat the diagnosis as "
    "settled. If it turns out to be unreachable in current configurations, "
    "close it as `wontfix` with a note explaining why."
)

CONFIRMED_NOTE = (
    "> **Verified.** The cited line was read directly during the review pass "
    "and matches the described behavior. A reproducing test is still worth "
    "adding alongside the fix."
)

# gh/GitHub failures worth retrying rather than aborting the whole run.
TRANSIENT_MARKERS = (
    "rate limit", "secondary", "abuse", "try again", "too quickly",
    "429", "500", "502", "503", "504", "timeout", "timed out",
    "connection reset", "connection refused", "temporary failure",
    "eof", "server error",
)

PENDING = "pending"


class GhError(RuntimeError):
    """A gh invocation failed in a way the caller should report, not trace back."""


def run(args: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run gh, never raising on non-zero exit; callers inspect returncode."""
    try:
        return subprocess.run(
            args, input=stdin, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise GhError(
            "gh CLI not found on PATH. Install it: https://cli.github.com/"
        ) from exc


def gh_available() -> tuple[bool, str]:
    """Report whether gh is installed and authenticated."""
    if shutil.which("gh") is None:
        return False, "gh CLI not found on PATH. Install it: https://cli.github.com/"
    probe = run(["gh", "auth", "status"])
    if probe.returncode != 0:
        return False, (
            "gh is installed but not authenticated. Run `gh auth login` "
            "(needs `repo` scope) or export GH_TOKEN.\n"
            + (probe.stderr or "").strip()
        )
    return True, ""


def current_login() -> str:
    """Return the authenticated GitHub login."""
    proc = run(["gh", "api", "user", "--jq", ".login"])
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GhError(
            "could not determine your GitHub login from `gh api user`:\n"
            + (proc.stderr or "").strip()
        )
    return proc.stdout.strip()


def ensure_repo(slug: str, *, dry_run: bool) -> None:
    """Create the private tracker repo unless it already exists."""
    if dry_run:
        print(f"[dry-run] would ensure private repo {slug} exists")
        return
    if run(["gh", "repo", "view", slug]).returncode == 0:
        print(f"repo {slug} already exists")
        return
    proc = run([
        "gh", "repo", "create", slug,
        "--private",
        "--description",
        "Private tracker for the Nornir chunked bug and performance review",
    ])
    if proc.returncode != 0:
        raise GhError(
            f"could not create {slug}:\n{(proc.stderr or '').strip()}\n"
            "If the name is taken, re-run with --repo <other-name> "
            "(or --repo owner/name for an org)."
        )
    print(f"created private repo {slug}")


def wanted_labels(findings: list[dict]) -> dict[str, tuple[str, str]]:
    """Build the full label set (name -> colour, description) from the data."""
    wanted: dict[str, tuple[str, str]] = {}
    for sev, color in SEVERITY_COLORS.items():
        wanted[sev] = (color, SEVERITY_TEXT[sev])
    for ftype, color in TYPE_COLORS.items():
        wanted[ftype] = (color, f"Finding type: {ftype}")
    for status, color in STATUS_COLORS.items():
        wanted[f"status:{status}"] = (color, f"Review status: {status}")
    # Derive the remaining labels from the findings so unexpected values in the
    # master list still get a label rather than an issue-create failure.
    for f in findings:
        wanted.setdefault(f["severity"], (FALLBACK_COLOR, f"Severity {f['severity']}"))
        wanted.setdefault(f["type"], (FALLBACK_COLOR, f"Finding type: {f['type']}"))
        wanted.setdefault(
            f"status:{f['status']}", (FALLBACK_COLOR, f"Review status: {f['status']}")
        )
        wanted[f"chunk-{f['chunk']}"] = (
            "bfd4f2", f"Review chunk {f['chunk']}: {f['chunk_name']}"
        )
        wanted[f"repo:{f['repo']}"] = ("d4c5f9", f"Owning submodule: {f['repo']}")
        if f.get("wave"):
            wanted[f"wave-{f['wave']}"] = (
                "f9d0c4", WAVE_TEXT.get(f["wave"], f"Fix-order wave {f['wave']}")
            )
    return wanted


def ensure_labels(slug: str, findings: list[dict], *, dry_run: bool) -> None:
    """Create or update every label the issues will reference."""
    wanted = wanted_labels(findings)
    if dry_run:
        print(f"[dry-run] would ensure {len(wanted)} labels:")
        for name, (color, desc) in sorted(wanted.items()):
            print(f"    {name:28} #{color}  {desc[:LABEL_DESC_MAX]}")
        return

    failed: list[str] = []
    for name, (color, desc) in sorted(wanted.items()):
        # --force makes this idempotent: creates or updates.
        proc = run([
            "gh", "label", "create", name,
            "--repo", slug, "--color", color,
            "--description", desc[:LABEL_DESC_MAX], "--force",
        ])
        if proc.returncode != 0:
            failed.append(name)
            print(f"  label {name!r} failed: {(proc.stderr or '').strip()}",
                  file=sys.stderr)
    if failed:
        raise GhError(
            f"{len(failed)} label(s) could not be created: {', '.join(failed)}. "
            "Issue creation would fail on a missing label, so fix this first."
        )
    print(f"ensured {len(wanted)} labels on {slug}")


def issue_title(f: dict) -> str:
    """Build a single-line title that fits GitHub's 256-character limit."""
    prefix = f"[{f['id']}] {f['severity']} - "
    concern = " ".join(f["concern"].replace("`", "").split())
    room = TITLE_MAX - len(prefix)
    if len(concern) > room:
        concern = concern[: max(1, room - 1)].rstrip(" ,;:-") + "\u2026"
    return (prefix + concern)[:TITLE_MAX]


def cell(text: object) -> str:
    """Make a value safe inside a one-line markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def issue_body(f: dict) -> str:
    """Render the issue body: verification banner, concern, evidence, metadata."""
    lines = [
        CONFIRMED_NOTE if f["status"] == "confirmed" else UNVERIFIED_NOTE,
        "",
        "## Concern",
        "",
        f["concern"],
        "",
        "## Evidence",
        "",
        f["evidence"],
        "",
        "## Details",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Finding ID | `{f['id']}` |",
        f"| Location | {cell(f['location'])} |",
        f"| Owning submodule | `{cell(f['repo'])}` |",
        f"| Severity | {cell(SEVERITY_TEXT.get(f['severity'], f['severity']))} |",
        f"| Type | `{cell(f['type'])}` |",
        f"| Review chunk | {cell(f['chunk'])} - {cell(f['chunk_name'])} |",
        f"| Review status | `{cell(f['status'])}` |",
    ]
    if f.get("wave"):
        wave = WAVE_TEXT.get(f["wave"], f"Fix-order wave {f['wave']}")
        lines.append(f"| Suggested fix order | {cell(wave)} |")
    if f.get("duplicate_of"):
        lines.append(f"| Duplicate of | `{cell(f['duplicate_of'])}` |")
    lines += [
        "",
        "---",
        "",
        "Filed from the Nornir chunked bug and performance review "
        f"(`{MASTER_DOC}`), which catalogued 208 findings across 10 chunks. "
        "See that file for the full context, the summary of top risks, and the "
        "recommended fix order.",
    ]
    return "\n".join(lines)


def labels_for(f: dict) -> list[str]:
    """Return the label names for one finding."""
    out = [f["severity"], f["type"], f"chunk-{f['chunk']}",
           f"repo:{f['repo']}", f"status:{f['status']}"]
    if f.get("wave"):
        out.append(f"wave-{f['wave']}")
    return out


def load_ledger() -> dict[str, dict]:
    """Read created_issues.json, tolerating the older url-only string format."""
    if not LEDGER.is_file():
        return {}
    try:
        raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"{LEDGER} is not valid JSON ({exc}). Inspect it by hand before "
            "resuming; deleting it would re-file every issue."
        )
    ledger: dict[str, dict] = {}
    for fid, value in raw.items():
        ledger[fid] = {"url": value} if isinstance(value, str) else dict(value)
    return ledger


def save_ledger(ledger: dict[str, dict]) -> None:
    """Write the ledger atomically so an interrupt cannot truncate it."""
    tmp = LEDGER.with_suffix(".json.tmp")
    payload = json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, LEDGER)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


URL_RE = re.compile(r"https://\S+/issues/\d+")


def parse_issue_url(stdout: str) -> str | None:
    """Pull the issue URL out of gh's output."""
    match = URL_RE.search(stdout or "")
    return match.group(0) if match else None


def find_existing_issue(slug: str, fid: str) -> str | None:
    """Look for an already-filed issue for this finding ID (resume recovery)."""
    proc = run([
        "gh", "issue", "list", "--repo", slug, "--state", "all",
        "--search", f'"[{fid}]" in:title', "--limit", "5",
        "--json", "number,title,url",
    ])
    if proc.returncode != 0:
        raise GhError(
            f"could not query existing issues for {fid}: "
            f"{(proc.stderr or '').strip()}"
        )
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return None
    for row in rows:
        if row.get("title", "").startswith(f"[{fid}]"):
            return row.get("url")
    return None


def create_issue(slug: str, f: dict, *, retries: int, backoff: float) -> str:
    """Create one issue, backing off on secondary rate limits. Returns the URL."""
    args = ["gh", "issue", "create", "--repo", slug,
            "--title", issue_title(f), "--body-file", "-"]
    for label in labels_for(f):
        args += ["--label", label]

    delay = backoff
    for attempt in range(1, retries + 1):
        proc = run(args, stdin=issue_body(f))
        if proc.returncode == 0:
            url = parse_issue_url(proc.stdout) or parse_issue_url(proc.stderr)
            if url:
                return url
            raise GhError(
                f"{f['id']}: gh reported success but printed no issue URL:\n"
                f"{(proc.stdout or '').strip()}"
            )
        err = ((proc.stderr or "") + (proc.stdout or "")).strip()
        if attempt == retries or not any(m in err.lower() for m in TRANSIENT_MARKERS):
            raise GhError(f"{f['id']}: gh issue create failed: {err}")
        print(f"  {f['id']}: transient error, retry {attempt}/{retries} "
              f"in {delay:.0f}s ({err.splitlines()[0][:120] if err else 'no output'})",
              file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    raise AssertionError("unreachable")


def reconcile_pending(slug: str, ledger: dict[str, dict], *, dry_run: bool) -> None:
    """Resolve entries left mid-flight by a previous kill: filed, or not?

    A pending entry means the create call was issued but the outcome was never
    recorded, so the issue may or may not exist. Ask GitHub rather than guess.
    """
    pending = sorted(fid for fid, e in ledger.items() if e.get("url") == PENDING)
    if not pending:
        return
    if dry_run:
        print(f"[dry-run] {len(pending)} pending entr(ies) would be reconciled "
              f"against GitHub: {', '.join(pending)}")
        return
    print(f"reconciling {len(pending)} pending entr(ies) from a previous run")
    for fid in pending:
        url = find_existing_issue(slug, fid)
        if url:
            ledger[fid] = {"url": url, "recorded": now(), "recovered": True}
            print(f"  {fid} was already filed -> {url}")
        else:
            del ledger[fid]
            print(f"  {fid} was never filed; re-queued")
        save_ledger(ledger)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=DEFAULT_REPO,
                    help=f"repo name or owner/name (default: {DEFAULT_REPO})")
    ap.add_argument("--dry-run", action="store_true",
                    help="print planned actions; never runs gh or touches the network")
    ap.add_argument("--setup-only", action="store_true",
                    help="create the repo and labels, then stop")
    ap.add_argument("--severity", nargs="+", choices=["P0", "P1", "P2", "P3"],
                    help="only file these severities (default: all)")
    ap.add_argument("--chunk", nargs="+", help="only file these chunks, e.g. 03 05")
    ap.add_argument("--limit", type=int, help="stop after N issues this run")
    ap.add_argument("--delay", type=float, default=2.5,
                    help="seconds between creations (default: 2.5)")
    ap.add_argument("--retries", type=int, default=4,
                    help="attempts per issue on transient errors (default: 4)")
    ap.add_argument("--backoff", type=float, default=15.0,
                    help="first retry wait in seconds, doubling (default: 15)")
    ap.add_argument("--include-duplicates", action="store_true",
                    help="also file entries marked as duplicates of another finding")
    args = ap.parse_args()

    if args.limit is not None and args.limit <= 0:
        print("--limit must be positive", file=sys.stderr)
        return 1

    if not FINDINGS.is_file():
        print(f"{FINDINGS} not found - run extract_findings.py first", file=sys.stderr)
        return 1
    findings: list[dict] = json.loads(FINDINGS.read_text(encoding="utf-8"))

    slug = args.repo
    if args.dry_run:
        if "/" not in slug:
            slug = f"<your-login>/{slug}"
    else:
        ok, why = gh_available()
        if not ok:
            print(why, file=sys.stderr)
            return 1
        if "/" not in slug:
            slug = f"{current_login()}/{slug}"

    # Chunks are two-digit strings in the data; accept "3" as well as "03".
    chunks = {c.zfill(2) for c in args.chunk} if args.chunk else None

    print(f"target repo: {slug}  (private)")
    ensure_repo(slug, dry_run=args.dry_run)
    ensure_labels(slug, findings, dry_run=args.dry_run)
    if args.setup_only:
        return 0

    ledger = load_ledger()
    reconcile_pending(slug, ledger, dry_run=args.dry_run)

    queue = []
    for f in findings:
        if f.get("duplicate_of") and not args.include_duplicates:
            continue
        if args.severity and f["severity"] not in args.severity:
            continue
        if chunks and f["chunk"] not in chunks:
            continue
        if f["id"] in ledger:
            continue
        queue.append(f)

    # File the worst first so an interrupted run still leaves the P0s tracked.
    queue.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["id"]))
    if args.limit:
        queue = queue[: args.limit]

    filed = sum(1 for e in ledger.values() if e.get("url") != PENDING)
    print(f"{filed} already filed, {len(queue)} to create this run")
    if args.dry_run:
        for f in queue:
            print(f"  [dry-run] {f['id']:10} {','.join(labels_for(f)):72} "
                  f"{issue_title(f)}")
        print(f"[dry-run] {len(queue)} issues would be created in {slug}; "
              f"no repo, label or issue was touched")
        return 0

    if queue:
        eta = len(queue) * args.delay / 60.0
        print(f"estimated {eta:.0f} min at --delay {args.delay}")

    for i, f in enumerate(queue, 1):
        # Claim the finding before calling gh: if we are killed between the call
        # and the result, the next run reconciles this marker instead of
        # blindly re-filing.
        ledger[f["id"]] = {"url": PENDING, "started": now()}
        save_ledger(ledger)
        try:
            url = create_issue(slug, f, retries=args.retries, backoff=args.backoff)
        except GhError as exc:
            print(f"\nSTOPPED: {exc}", file=sys.stderr)
            print(f"{filed} issues confirmed in {LEDGER.name}; {f['id']} left "
                  f"pending. Re-run the same command to reconcile and resume.",
                  file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print(f"\ninterrupted during {f['id']}; it is marked pending in "
                  f"{LEDGER.name}. Re-run the same command to resume.",
                  file=sys.stderr)
            return 130
        ledger[f["id"]] = {"url": url, "recorded": now()}
        save_ledger(ledger)
        filed += 1
        print(f"  [{i}/{len(queue)}] {f['id']} {f['severity']} -> {url}")
        if i < len(queue):
            try:
                time.sleep(args.delay)
            except KeyboardInterrupt:
                print(f"\ninterrupted after {f['id']}; {filed} issues recorded. "
                      f"Re-run the same command to resume.", file=sys.stderr)
                return 130

    print(f"\ndone. {filed} issues recorded in {LEDGER.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GhError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        raise SystemExit(130)
