# Sphinx configuration for the Nornir umbrella monodoc.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import sys
from pathlib import Path

_DOCS_DIR = Path(__file__).resolve().parent
_ROOT = _DOCS_DIR.parent

# -- Path setup for autodoc -------------------------------------------------
for _pkg in (
    _ROOT / "nornir-shared",
    _ROOT / "nornir-pools",
    _ROOT / "nornir-imageregistration",
    _ROOT / "nornir-buildmanager",
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

# -- MyST -------------------------------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist"]
