# AGENTS.md

## Cursor Cloud specific instructions

### Project structure

Nornir is a monorepo using git submodules for scientific image processing (2D registration, mosaic assembly, 3D volume construction). The flagship GUI is **Pyre** (wxPython + OpenGL image registration tool).

Submodule install order (dependency chain):
`nornir-shared` → `nornir-pools` → `dm4` → `nornir-imageregistration` → `nornir-buildmanager` → `nornir-pyre`

### Virtual environment

- Python 3.13+ is required (`>=3.13` in all `pyproject.toml` files). Installed via `deadsnakes/ppa`.
- Venv lives at `/workspace/venv/pyre314`.
- Activate with: `source /workspace/venv/pyre314/bin/activate`

### Installing packages (editable mode)

All submodules must be installed with `--no-deps` to avoid git dependency URLs overwriting local editable installs:
```
pip install --no-deps -e ./nornir-shared
pip install --no-deps -e ./nornir-pools
pip install --no-deps -e ./dm4
pip install --no-deps -e ./nornir-imageregistration
pip install --no-deps -e ./nornir-buildmanager
pip install --no-deps -e ./nornir-pyre
```

Actual transitive dependencies are installed separately (numpy, scipy, matplotlib, Pillow, scikit-image, pydantic, hypothesis, python-dotenv, validators, dependency-injector, rtree, PyOpenGL, PyYAML, wxPython).

### wxPython installation

wxPython does **not** have a PyPI wheel for Linux. Use the extras repository:
```
pip install -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-24.04 wxPython
```

### Running tests

Tests use Python `unittest`. Set env vars `TESTINPUTPATH` and `TESTOUTPUTPATH`:
```bash
export TESTINPUTPATH=/workspace/testdata
export TESTOUTPUTPATH=/workspace/testdata_output
mkdir -p "$TESTINPUTPATH" "$TESTOUTPUTPATH"
```

CI-scoped tests per submodule:
- `nornir-shared`: `python -m unittest discover -s ./test -p 'test_Histogram*.py'`
- `nornir-imageregistration`: `python -m unittest discover -s ./test -p 'test_grid_division*.py'` (very slow, CPU-intensive)
- `nornir-pools`: `python -m unittest discover -s ./test -p 'test_*.py'`

Full test suites can be run with: `python -m unittest discover -s ./test -p 'test_*.py'`

Some `nornir-shared` tests are Windows-specific (path separators, `start` command) and will fail on Linux — this is expected.

### Type checking

`pyright` is configured at the workspace root via `pyrightconfig.json`. Run: `pyright`

Large number of pre-existing type errors exist (4000+) — this is expected for the codebase.

### Pyre GUI

- Pyre requires OpenGL 4.5 with debug context support (`glDebugMessageCallback`).
- In Cloud Agent VMs (Mesa software renderer), Pyre initializes but crashes at `glpanel.py:81` due to `NullFunctionError` on `glDebugMessageCallback`. The DI container, transforms, and UI framework all load correctly.
- To run Pyre: `DISPLAY=:1 python -m pyre` (uses TigerVNC display).
- Full GUI testing requires a real GPU or an OpenGL 4.5-capable software renderer.

### External tools (optional, for buildmanager pipeline)

- **ImageMagick 7** (`magick` on PATH) — needed by `nornir-shared` and `nornir-buildmanager`
- **SCI ir-tools** (`ir-refine-grid`, `ir-assemble`, etc.) — needed by `nornir-buildmanager` pipeline
- These are not required for core library development or unit tests.

### CuPy (optional GPU acceleration)

CuPy is optional. Without it, all computation falls back to NumPy. See `.cursor/rules/Numpy-CuPy-compatibility.mdc` for coding conventions when working with the NumPy/CuPy dual path.
