#!/usr/bin/env python3
"""Parse the Nornir bug-review master list into structured findings.json.

Reads the markdown tables in nornir-bug-review-master.md and emits one record
per finding. Re-run this whenever the master list changes; create_issues.py
consumes the JSON, never the markdown.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MASTER = HERE.parent / "nornir-bug-review-master.md"
DEFAULT_OUT = HERE / "findings.json"

# A finding row has exactly 8 cells. The severity column may be bolded (**P0**).
ROW = re.compile(r"^\|\s*(C\d{2}-[BPD]\d{3})\s*\|(.+)\|\s*$")

SEVERITIES = {"P0", "P1", "P2", "P3"}
TYPES = {"bug", "perf", "parity", "debt"}

# Owning submodule inferred from the location path when possible, else from the
# chunk. Chunk 00 is seeded/cross-cutting so it always relies on the path.
PATH_TO_REPO = (
    ("nornir-imageregistration", "nornir-imageregistration"),
    ("nornir_imageregistration", "nornir-imageregistration"),
    ("nornir-buildmanager", "nornir-buildmanager"),
    ("nornir_buildmanager", "nornir-buildmanager"),
    ("nornir-shared", "nornir-shared"),
    ("nornir_shared", "nornir-shared"),
    ("nornir-pools", "nornir-pools"),
    ("nornir_pools", "nornir-pools"),
    ("nornir-pyre", "nornir-pyre"),
    ("pyre/", "nornir-pyre"),
    ("dm4/dm4", "dm4"),
)

CHUNK_TO_REPO = {
    "01": None,  # split between shared and pools; must come from the path
    "02": "nornir-imageregistration",
    "03": "nornir-imageregistration",
    "04": "nornir-imageregistration",
    "05": "nornir-imageregistration",
    "06": "nornir-imageregistration",
    "07": "nornir-buildmanager",
    "08": "nornir-buildmanager",
    "09": "nornir-buildmanager",
    "10": "nornir-pyre",
}

# Seeded chunk-00 entries describe a subsystem rather than a file path, so the
# owning repo cannot be inferred and is pinned explicitly here.
ID_TO_REPO = {
    "C00-P003": "nornir-imageregistration",
    "C00-P004": "nornir-imageregistration",
    "C00-P005": "nornir-buildmanager",
    "C00-D004": "cross-cutting",  # Flip/Flop contract spans importers + transforms
    "C00-D005": "nornir-buildmanager",
    "C00-B001": "nornir-imageregistration",
}

CHUNK_NAMES = {
    "00": "seed (carried from prior review)",
    "01": "foundation (shared + pools)",
    "02": "phase correlation + STOS brute",
    "03": "grid refine + local distortion",
    "04": "assemble + tile I/O",
    "05": "transforms + spatial",
    "06": "mosaic arrange + overlap",
    "07": "buildmanager pipeline core",
    "08": "buildmanager operations",
    "09": "importers + dm4",
    "10": "Pyre UI + GL",
}

# Fix-order wave from the master list summary, keyed by finding ID.
WAVES = {
    1: ["C07-B001", "C07-B002", "C03-B001", "C05-B001", "C10-B001", "C07-B005"],
    2: ["C08-B001", "C08-B002", "C08-B007", "C08-B003", "C07-B003", "C07-B009",
        "C04-B001", "C04-B002", "C08-B004"],
    3: ["C09-B001", "C09-B002", "C09-B004", "C09-B006"],
    4: ["C04-P001", "C08-P001", "C09-P002", "C03-P001", "C10-P001", "C10-P002",
        "C01-P001", "C07-P002", "C09-P001", "C06-P001", "C07-P001"],
    5: ["C05-B002", "C05-B005", "C05-B006", "C05-B012", "C02-B003", "C02-P001",
        "C02-B012", "C06-B012", "C01-P005", "C01-P006"],
}
ID_TO_WAVE = {fid: wave for wave, ids in WAVES.items() for fid in ids}

# Findings that restate an earlier entry at a more concrete location. The
# duplicate is kept in the data (for traceability) but not filed as an issue.
DUPLICATES = {"C00-P001": "C01-P001"}


def strip_md(cell: str) -> str:
    """Flatten a table cell to plain text, keeping inline code readable."""
    text = cell.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.strip()


def repo_for(fid: str, chunk: str, location: str) -> str:
    if fid in ID_TO_REPO:
        return ID_TO_REPO[fid]
    haystack = location.replace("\\", "/")
    for needle, repo in PATH_TO_REPO:
        if needle in haystack:
            return repo
    fallback = CHUNK_TO_REPO.get(chunk)
    if fallback:
        return fallback
    return "unknown"


def parse(master: Path) -> list[dict]:
    findings: list[dict] = []
    seen: set[str] = set()

    for lineno, line in enumerate(master.read_text(encoding="utf-8").splitlines(), 1):
        m = ROW.match(line)
        if not m:
            continue

        fid = m.group(1)
        cells = [c for c in m.group(2).split("|")]
        # Finding tables have 7 cells after the ID; the summary table has 2.
        if len(cells) != 7:
            continue

        chunk_raw, severity, ftype, location, concern, evidence, status = (
            strip_md(c) for c in cells
        )
        severity = severity.upper()
        if severity not in SEVERITIES or ftype not in TYPES:
            print(f"  skip {fid} at line {lineno}: severity={severity!r} type={ftype!r}",
                  file=sys.stderr)
            continue
        if fid in seen:
            print(f"  WARNING duplicate ID {fid} at line {lineno}", file=sys.stderr)
            continue
        seen.add(fid)

        chunk = fid[1:3]
        findings.append({
            "id": fid,
            "chunk": chunk,
            "chunk_label": chunk_raw or chunk,
            "chunk_name": CHUNK_NAMES.get(chunk, chunk),
            "severity": severity,
            "type": ftype,
            "location": location,
            "concern": concern,
            "evidence": evidence,
            "status": status,
            "repo": repo_for(fid, chunk, location),
            "wave": ID_TO_WAVE.get(fid),
            "duplicate_of": DUPLICATES.get(fid),
        })

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.master.is_file():
        print(f"master list not found: {args.master}", file=sys.stderr)
        return 1

    findings = parse(args.master)
    args.out.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")

    print(f"parsed {len(findings)} findings -> {args.out}")
    for key in ("severity", "type", "repo", "status"):
        counts: dict[str, int] = {}
        for f in findings:
            counts[f[key]] = counts.get(f[key], 0) + 1
        summary = "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"  {key:9} {summary}")
    dupes = [f["id"] for f in findings if f["duplicate_of"]]
    print(f"  marked as duplicates (not filed): {dupes or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
