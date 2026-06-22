#!/usr/bin/env python3
"""Verify release/package-versions.yaml matches each package tree (pyproject version or dm4 __version__)."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def _read_dm4_version(repo_root: Path) -> str:
    init_path = repo_root / "dm4" / "dm4" / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        raise ValueError(f"Could not parse __version__ in {init_path}")
    return m.group(1)


def _read_pyproject_version(repo_root: Path, rel_path: str) -> str:
    pp = repo_root / rel_path / "pyproject.toml"
    data = tomllib.loads(pp.read_text(encoding="utf-8"))
    proj = data.get("project")
    if not isinstance(proj, dict) or "version" not in proj:
        raise ValueError(f"No static project.version in {pp}")
    return str(proj["version"])


def main() -> int:
    release_dir = Path(__file__).resolve().parent
    repo_root = release_dir.parent
    bom_path = release_dir / "package-versions.yaml"
    data = yaml.safe_load(bom_path.read_text(encoding="utf-8"))
    packages = data.get("packages") or {}
    errors: list[str] = []

    for dist, meta in packages.items():
        if not isinstance(meta, dict):
            continue
        expected = str(meta.get("version", ""))
        path = meta.get("path")
        if not path:
            errors.append(f"{dist}: missing path in BOM")
            continue
        try:
            if dist == "dm4":
                actual = _read_dm4_version(repo_root)
            else:
                actual = _read_pyproject_version(repo_root, str(path))
        except (OSError, ValueError, tomllib.TOMLDecodeError) as e:
            errors.append(f"{dist}: failed to read tree: {e}")
            continue
        if actual != expected:
            errors.append(f"{dist}: BOM says {expected!r} but tree has {actual!r}")

    if errors:
        print("verify_package_versions: FAILED", file=sys.stderr)
        for line in errors:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("verify_package_versions: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
