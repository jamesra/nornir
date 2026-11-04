#!/usr/bin/env python3
"""Bump the Pyre patch version after a successful local installer build.

Every local build of the Windows installer should carry a version number that has not
shipped before, so Pyre's update check and **Help -> What's New** see each published
build as new. ``build-installer.ps1`` runs this after Inno Setup succeeds; the version
just built keeps its changelog section (dated today) and the next patch version gets a
new ``not yet released`` section on top.

Files changed (line endings and encoding preserved):

* ``nornir-pyre/pyproject.toml`` ``[project].version``
* ``release/package-versions.yaml`` ``packages.pyre.version``
* ``nornir-pyre/pyre/CHANGELOG.user.md`` headings

Examples::

    # After a successful build: date the built version, open the next one
    python release/bump_pyre_version.py

    # Before a build: bump only if the current version has already shipped
    # (its changelog heading carries a date instead of "not yet released")
    python release/bump_pyre_version.py --if-released
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "nornir-pyre" / "pyproject.toml"
_BOM = _ROOT / "release" / "package-versions.yaml"
_CHANGELOG = _ROOT / "nornir-pyre" / "pyre" / "CHANGELOG.user.md"

UNRELEASED = "not yet released"
_PYPROJECT_VERSION = re.compile(r'(?m)^(version\s*=\s*["\'])(\d+)\.(\d+)\.(\d+)(["\'])')
_BOM_PYRE_VERSION = re.compile(
    r'(?ms)^(  pyre:\s*$.*?^    version:\s*["\']?)(\d+\.\d+\.\d+)(["\']?)')
_HEADING = re.compile(r"(?m)^##\s+(\d+\.\d+\.\d+)(?:\s+[—–-]\s+(.+?))?[ \t]*(\r?)$")


def _read(path: Path) -> str:
    # newline="" keeps CRLF/LF exactly as stored.
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def current_version(pyproject_text: str) -> tuple[int, int, int]:
    match = _PYPROJECT_VERSION.search(pyproject_text)
    if match is None:
        raise SystemExit(f"Could not find [project] version in {_PYPROJECT}")
    return int(match.group(2)), int(match.group(3)), int(match.group(4))


def set_pyproject_version(text: str, version: str) -> str:
    return _PYPROJECT_VERSION.sub(lambda m: f"{m.group(1)}{version}{m.group(5)}", text, count=1)


def set_bom_version(text: str, version: str) -> str:
    new_text, count = _BOM_PYRE_VERSION.subn(
        lambda m: f"{m.group(1)}{version}{m.group(3)}", text, count=1)
    if count != 1:
        raise SystemExit(f"Could not find packages.pyre.version in {_BOM}")
    return new_text


def heading_label(changelog_text: str, version: str) -> str | None:
    """Return the text after the dash in ``## <version> — <label>``, or None if absent."""
    for match in _HEADING.finditer(changelog_text):
        if match.group(1) == version:
            return (match.group(2) or "").strip()
    return None


def is_released(changelog_text: str, version: str) -> bool:
    label = heading_label(changelog_text, version)
    return label is not None and label != "" and label != UNRELEASED


def bump_changelog(text: str, built: str, nxt: str, today: str) -> str:
    """Date the *built* section (if still unreleased) and insert an empty *nxt* section above it."""
    nl = _newline(text)
    match = next((m for m in _HEADING.finditer(text) if m.group(1) == built), None)
    if match is None:
        first = _HEADING.search(text)
        if first is None:
            raise SystemExit(f"No '## <version>' headings in {_CHANGELOG}")
        insert_at = first.start()
    else:
        if (match.group(2) or "").strip() in ("", UNRELEASED):
            text = text[:match.start()] + f"## {built} — {today}{match.group(3)}" + text[match.end():]
        insert_at = match.start()
    if heading_label(text, nxt) is not None:
        return text
    return text[:insert_at] + f"## {nxt} — {UNRELEASED}{nl}{nl}" + text[insert_at:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--if-released", action="store_true",
        help="Bump only when the current version's changelog heading is dated (already shipped).")
    parser.add_argument("--dry-run", action="store_true", help="Print the change; write nothing.")
    args = parser.parse_args(argv)

    pyproject_text = _read(_PYPROJECT)
    changelog_text = _read(_CHANGELOG)
    major, minor, patch = current_version(pyproject_text)
    built = f"{major}.{minor}.{patch}"
    nxt = f"{major}.{minor}.{patch + 1}"

    if args.if_released and not is_released(changelog_text, built):
        print(f"Pyre {built} has not shipped yet; keeping it.")
        return 0

    today = datetime.date.today().isoformat()
    new_pyproject = set_pyproject_version(pyproject_text, nxt)
    new_bom = set_bom_version(_read(_BOM), nxt)
    new_changelog = bump_changelog(changelog_text, built, nxt, today)

    print(f"Pyre version {built} -> {nxt}")
    if args.dry_run:
        return 0
    _write(_PYPROJECT, new_pyproject)
    _write(_BOM, new_bom)
    _write(_CHANGELOG, new_changelog)
    print(f"Updated {_PYPROJECT.relative_to(_ROOT)}, {_BOM.relative_to(_ROOT)}, "
          f"{_CHANGELOG.relative_to(_ROOT)}. Commit them (submodule first, then the umbrella).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
