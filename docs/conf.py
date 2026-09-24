# Sphinx configuration for the Nornir umbrella monodoc.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parent
_ROOT = _DOCS_DIR.parent
_PYRE_DOWNLOADS = _DOCS_DIR / "_static" / "downloads"

# -- Path setup for autodoc -------------------------------------------------
for _pkg in (
    _ROOT / "nornir-shared",
    _ROOT / "nornir-pools",
    _ROOT / "nornir-imageregistration",
    _ROOT / "nornir-buildmanager",
    _ROOT / "nornir-volumecontroller",
    _ROOT / "nornir-volumemodel",
):
    p = str(_pkg.resolve())
    if p not in sys.path:
        sys.path.insert(0, p)

# -- Project metadata from repo VERSION ------------------------------------
def _read_version() -> str:
    vf = _ROOT / "VERSION"
    if vf.is_file():
        return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


_version = _read_version()

project = "Nornir"
copyright = "Nornir contributors"
author = "Nornir contributors"
version = _version
release = _version

# -- General ----------------------------------------------------------------
extensions = [
    "myst_parser",
    "sphinxarg.ext",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]

templates_path: list[str] = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# MyST registers ``.md`` with the ``markdown`` parser name; keep that key in sync.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"
pygments_style = "sphinx"

# Optional imports that may be absent in doc CI (GPU / UI).
autodoc_mock_imports = [
    "cupy",
    "cupyx",
    "cupyx.scipy",
    "scipy.misc",          # removed from modern SciPy; used by nornir_volumecontroller
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "imported-members": False,
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

# -- HTML -------------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = f"{project} {release} documentation"


def _latest_pyre_installer() -> Path | None:
    """Return the highest-versioned ``Pyre-*-Setup.exe`` under ``_static/downloads``."""
    if not _PYRE_DOWNLOADS.is_dir():
        return None
    pattern = re.compile(r"^Pyre-(\d+)\.(\d+)\.(\d+)-Setup\.exe$", re.IGNORECASE)
    found: list[tuple[tuple[int, int, int], Path]] = []
    for path in _PYRE_DOWNLOADS.glob("Pyre-*-Setup.exe"):
        match = pattern.match(path.name)
        if match is None:
            continue
        ver = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        found.append((ver, path))
    if not found:
        return None
    found.sort(key=lambda item: item[0])
    return found[-1][1]


_pyre_installer = _latest_pyre_installer()
_NORNIR_GITHUB_REPO = "jamesra/nornir"
# Stable docs download: always the GitHub Releases "latest" asset named Pyre-Setup.exe.
# Versioned history lives on pyre-<ver> releases (Pyre-<ver>-Setup.exe).
_PYRE_LATEST_DOWNLOAD_URL = (
    f"https://github.com/{_NORNIR_GITHUB_REPO}/releases/latest/download/Pyre-Setup.exe"
)


def _pyre_version_from_github_latest() -> str | None:
    """Best-effort: version from the repo's latest GitHub Release tag (pyre-X.Y.Z)."""
    url = f"https://api.github.com/repos/{_NORNIR_GITHUB_REPO}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nornir-sphinx-docs",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    tag = str(payload.get("tag_name") or "")
    match = re.match(r"^pyre-(\d+\.\d+\.\d+)$", tag, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback: asset name Pyre-X.Y.Z-Setup.exe on the latest release
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        asset_match = re.match(r"^Pyre-(\d+\.\d+\.\d+)-Setup\.exe$", name, re.IGNORECASE)
        if asset_match:
            return asset_match.group(1)
    return None


def _pyre_version_from_pyproject() -> str | None:
    pyproject = _ROOT / "nornir-pyre" / "pyproject.toml"
    if not pyproject.is_file():
        return None
    match = re.search(
        r'(?m)^version\s*=\s*["\'](\d+\.\d+\.\d+)["\']\s*$',
        pyproject.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else None


_version_match = (
    re.match(r"Pyre-(\d+\.\d+\.\d+)-Setup\.exe", _pyre_installer.name, re.IGNORECASE)
    if _pyre_installer
    else None
)
pyre_windows_installer_version = (
    (_version_match.group(1) if _version_match else None)
    or _pyre_version_from_github_latest()
    or _pyre_version_from_pyproject()
    or "unknown"
)
pyre_windows_installer_name = f"Pyre-{pyre_windows_installer_version}-Setup.exe"
_pyre_versioned_download_url = (
    f"https://github.com/{_NORNIR_GITHUB_REPO}/releases/download/"
    f"pyre-{pyre_windows_installer_version}/{pyre_windows_installer_name}"
)

rst_epilog = f"""
.. |pyre-windows-installer| replace:: `{pyre_windows_installer_name} <{_pyre_versioned_download_url}>`__
.. |pyre-windows-installer-latest| replace:: `Pyre-Setup.exe <{_PYRE_LATEST_DOWNLOAD_URL}>`__
.. |pyre-windows-installer-version| replace:: {pyre_windows_installer_version}
"""


def _alias_pyre_installer(app, exception: Exception | None) -> None:
    """Write a download landing page; copy installer into HTML output when present."""
    if exception is not None:
        return
    dest_dir = Path(app.outdir) / "_static" / "downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source = _latest_pyre_installer()
    if source is not None:
        shutil.copy2(source, dest_dir / "Pyre-Setup.exe")
    # GitHub Pages cannot host the .exe; redirect to the always-latest Release asset.
    (dest_dir / "index.html").write_text(
        (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8"/>\n'
            "  <title>Pyre Windows installer</title>\n"
            f'  <meta http-equiv="refresh" content="0; url={_PYRE_LATEST_DOWNLOAD_URL}"/>\n'
            "</head>\n"
            "<body>\n"
            f'  <p>Download <a href="{_PYRE_LATEST_DOWNLOAD_URL}">Pyre-Setup.exe</a>'
            f" (latest; currently Pyre {pyre_windows_installer_version}).</p>\n"
            f'  <p>This version: <a href="{_pyre_versioned_download_url}">'
            f"{pyre_windows_installer_name}</a>.</p>\n"
            "</body>\n"
            "</html>\n"
        ),
        encoding="utf-8",
    )


def setup(app) -> None:
    app.connect("build-finished", _alias_pyre_installer)


# -- MyST -------------------------------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist"]
