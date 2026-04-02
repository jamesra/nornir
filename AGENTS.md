# Nornir Development Guide

## Cursor Cloud specific instructions

### Project overview

Nornir is a Python monorepo for 2D/3D image registration and volume construction from microscopy image sets. The active subpackages (installed in editable mode) and their dependency order:

1. **nornir-shared** — shared utilities (histogram, logging, etc.)
2. **nornir-pools** — thread/process pool abstraction (depends on nornir-shared)
3. **nornir-imageregistration** — core image registration algorithms (depends on nornir-shared, nornir-pools)
4. **nornir-buildmanager** — 3D volume build pipeline (depends on all above)
5. **nornir-pyre** — GUI/CLI application (depends on all above)
6. **dm4** — DM4 file reader (standalone)

### Virtual environment

- **Path:** `/workspace/venv/pyre314/`
- **Python:** 3.13 (via deadsnakes PPA; `pyproject.toml` requires `>=3.13`)
- **Activate:** `source /workspace/venv/pyre314/bin/activate`

### Environment variables

These must be set before running tests:

```bash
export TESTINPUTPATH=/workspace/nornir-testdata
export TESTOUTPUTPATH=/tmp/nornir-test-output
```

Both are persisted in `~/.bashrc`. If they are unset in your shell, re-export them.

### Installing packages

All pyproject.toml files declare inter-package dependencies via git URLs (e.g. `nornir_shared @ git+https://github.com/...`). When doing local editable installs, you **must** use `--no-deps` to avoid pip trying to resolve the git URLs:

```bash
source /workspace/venv/pyre314/bin/activate
pip install --no-deps -e nornir-shared -e nornir-pools -e nornir-imageregistration -e nornir-buildmanager -e nornir-pyre -e dm4
```

### Running tests

Tests use `unittest` (not pytest). CI test patterns per subpackage:

| Subpackage | Command |
|---|---|
| nornir-shared | `cd nornir-shared && python -m unittest discover -p 'test_Histogram*.py'` |
| nornir-pools | `cd nornir-pools && python -m unittest discover -p 'test_nornir_pools*.py'` |
| nornir-imageregistration | `cd nornir-imageregistration && python -m unittest discover -p 'test_grid_division*.py'` |
| nornir-buildmanager | `cd nornir-buildmanager && python -m unittest discover -p 'test_pipelinemanager*.py'` |

**Known issue:** `nornir-imageregistration` tests have a broken import chain in `test/transforms/__init__.py` (tries to import `.test` submodule). The test discovery via `unittest discover` fails due to eager imports in `test/__init__.py`. Individual test files can be run directly if needed.

### Linting / type-checking

```bash
cd /workspace && pyright
```

Pyright is configured via `pyrightconfig.json` at the repo root. There are ~4000 pre-existing type errors in the codebase — focus on not introducing new ones.

### ImageMagick

ImageMagick is required by `nornir-buildmanager` for image format conversions. It must be installed as a system package (`sudo apt-get install -y imagemagick`). Verify with `convert --version`.

### Test data

Tests expect `TESTINPUTPATH` to point to extracted test data from `http://rogue1.codepharm.net/nornir-testdata.zip` (~25 GB). Use Python's `zipfile` module or `7z` to extract (standard `unzip` may fail on large files). The extraction target is `/workspace/nornir-testdata`.

### Docker dev image

An updated Dockerfile for the dev environment is at `nornir-docker/dev/Dockerfile`. It builds an Ubuntu 24.04 image with Python 3.13, ImageMagick 7.1.1-27, and all Python dependencies pre-installed. Mount the nornir source tree into the container and run `pip install --no-deps -e ...` to install packages in editable mode.

### Optional dependencies

- **cupy** (GPU acceleration): `pip install cupy>=13.0` — requires NVIDIA GPU + CUDA
- **mkl_fft / mkl_random** (Intel MKL): optional performance packages

### Notes

- The `pyre` GUI requires wxPython and a display server (X11). It cannot be tested headlessly.
- cupy/mkl_fft warnings on import are informational and can be ignored.
- No external services (databases, message queues, etc.) are required.
