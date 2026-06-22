#!/usr/bin/env python3
"""Emit docker-included package versions for image labels.

Default: minified JSON to stdout (for piping).
With --base64: UTF-8 JSON minified, then base64 (no newlines), for safe docker --build-arg on Windows.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def _docker_packages_dict(yaml_path: Path) -> dict[str, str]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print("Install PyYAML: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    packages = data.get("packages") or {}
    out: dict[str, str] = {}
    for dist, meta in packages.items():
        if not isinstance(meta, dict):
            continue
        if not meta.get("docker", False):
            continue
        ver = meta.get("version")
        if ver is not None:
            out[dist] = str(ver)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base64", action="store_true", help="Emit base64(JSON) for docker build-arg")
    parser.add_argument(
        "yaml_path",
        nargs="?",
        default=None,
        help="Path to package-versions.yaml (default: next to this script)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    yaml_path = Path(args.yaml_path) if args.yaml_path else script_dir / "package-versions.yaml"
    payload = _docker_packages_dict(yaml_path)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if args.base64:
        print(base64.standard_b64encode(raw).decode("ascii"), end="")
    else:
        print(raw.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
