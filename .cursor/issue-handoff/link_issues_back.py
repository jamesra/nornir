#!/usr/bin/env python3
"""Optional post-step: add an `Issue` column to the bug-review master list.

Reads created_issues.json and appends one column to every finding table in
nornir-bug-review-master.md holding a markdown link to the filed issue, so the
narrative document and the tracker stay linked.

Only tables whose header starts with `| ID | Chunk |` are touched, and only rows
whose first cell is a finding ID. Re-running is safe: an already-linked table is
updated in place rather than gaining a second column.

Usage:
  python link_issues_back.py            # preview the diff, write nothing
  python link_issues_back.py --write    # rewrite the master list in place
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MASTER = HERE.parent / "nornir-bug-review-master.md"
DEFAULT_LEDGER = HERE / "created_issues.json"

HEADER_RE = re.compile(r"^\|\s*ID\s*\|\s*Chunk\s*\|")
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|\s*$")
ROW_RE = re.compile(r"^\|\s*(C\d{2}-[BPD]\d{3})\s*\|")
ISSUE_NUM_RE = re.compile(r"/issues/(\d+)\s*$")
COLUMN_TITLE = "Issue"


def issue_ref(url: str) -> str:
    """Render a ledger URL as a short markdown link, e.g. `[#42](url)`."""
    match = ISSUE_NUM_RE.search(url)
    return f"[#{match.group(1)}]({url})" if match else f"[link]({url})"


def split_cells(line: str) -> tuple[list[str], bool]:
    """Split a table row into cells, reporting whether it had a closing pipe."""
    body = line.rstrip()
    closed = body.endswith("|")
    inner = body[1:-1] if closed else body[1:]
    return inner.split("|"), closed


def append_cell(line: str, value: str, *, already_extended: bool) -> str:
    """Append the trailing cell of a table row, or replace it when re-running."""
    cells, closed = split_cells(line)
    if already_extended and cells:
        cells[-1] = f" {value} "
    else:
        cells.append(f" {value} ")
    del closed  # every rewritten row gets a closing pipe, normalising the table
    return "|" + "|".join(cells) + "|"


def transform(lines: list[str], refs: dict[str, str]) -> tuple[list[str], int]:
    """Return the rewritten lines and the number of rows given an issue link."""
    out: list[str] = []
    in_table = False
    extended = False
    linked = 0

    for line in lines:
        if HEADER_RE.match(line):
            in_table = True
            header_cells, _ = split_cells(line)
            extended = bool(header_cells) and header_cells[-1].strip() == COLUMN_TITLE
            out.append(append_cell(line, COLUMN_TITLE, already_extended=extended))
            continue
        if in_table and SEPARATOR_RE.match(line):
            out.append(append_cell(line, "---", already_extended=extended))
            continue
        row = ROW_RE.match(line) if in_table else None
        if row is not None:
            fid = row.group(1)
            url = refs.get(fid)
            cell = issue_ref(url) if url else "-"
            if url:
                linked += 1
            out.append(append_cell(line, cell, already_extended=extended))
            continue
        if in_table and not line.startswith("|"):
            in_table = False
        out.append(line)

    return out, linked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--write", action="store_true",
                    help="rewrite the master list (default: preview only)")
    args = ap.parse_args()

    if not args.master.is_file():
        print(f"master list not found: {args.master}")
        return 1
    if not args.ledger.is_file():
        print(f"ledger not found: {args.ledger} — run create_issues.py first")
        return 1

    raw = json.loads(args.ledger.read_text(encoding="utf-8"))
    refs = {
        fid: (value if isinstance(value, str) else value.get("url", ""))
        for fid, value in raw.items()
    }
    refs = {fid: url for fid, url in refs.items() if url.startswith("http")}

    original = args.master.read_text(encoding="utf-8").splitlines()
    updated, linked = transform(original, refs)

    if not args.write:
        changed = sum(1 for a, b in zip(original, updated) if a != b)
        print(f"[preview] {linked} findings would get an issue link "
              f"({changed} lines change). Re-run with --write to apply.")
        for a, b in zip(original, updated):
            if a != b and linked:
                print(f"  - {a}\n  + {b}")
                break
        return 0

    args.master.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"linked {linked} findings into {args.master}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
