# Nornir Test Data Setup Guide

## Overview

This document describes the test data infrastructure for nornir packages and how to use it for local development and CI/CD.

## Test Data Location

- **Source**: http://rogue1.codepharm.net/nornir-testdata.zip
- **Size**: ~24GB (compressed and extracted)
- **Local Path**: `/workspace/nornir-testdata/`

## Directory Structure

```
nornir-testdata/
├── Images/           # Test images for various formats and operations
├── PlatformRaw/      # Raw platform data
├── Transforms/       # Transform test data including mosaics
└── VolumeMetaData/   # Volume metadata for testing
```

## Environment Variables

Tests require two environment variables to be set:

- `TESTINPUTPATH`: Path to the test data root directory
  - Local: `/workspace/nornir-testdata`
  - CI: `${{ github.workspace }}/nornir-testdata`

- `TESTOUTPUTPATH`: Path for test output files
  - Local: `/tmp/nornir-test-output`
  - CI: `${{ github.workspace }}/testdata_output`

## Local Development Setup

### For Cloud Agents

The test data is already available at `/workspace/nornir-testdata/`. The environment variables are set up as follows:

```bash
export TESTINPUTPATH=/workspace/nornir-testdata
export TESTOUTPUTPATH=/tmp/nornir-test-output
mkdir -p $TESTOUTPUTPATH
```

### For Local Development

1. Download the test data:
   ```bash
   wget -O nornir-testdata.zip http://rogue1.codepharm.net/nornir-testdata.zip
   ```

2. Extract it:
   ```bash
   unzip nornir-testdata.zip
   ```

3. Set environment variables:
   ```bash
   export TESTINPUTPATH=/path/to/nornir-testdata
   export TESTOUTPUTPATH=/tmp/nornir-test-output
   mkdir -p $TESTOUTPUTPATH
   ```

4. Run tests:
   ```bash
   cd nornir-shared
   python -m unittest discover -s ./test -p 'test_*.py'
   ```

## Running Tests

Activate the virtual environment and set environment variables before running tests:

```bash
source /workspace/venv/pyre314/bin/activate
export TESTINPUTPATH=/workspace/nornir-testdata
export TESTOUTPUTPATH=/tmp/nornir-test-output
mkdir -p $TESTOUTPUTPATH
```

### GUI Tests and Non-Interactive Mode

Several `nornir-imageregistration` tests display matplotlib figures with **Pass/Fail** buttons
(`ShowWithPassFail`). These tests block until a human clicks Pass or Fail.

For **non-interactive** (automated) runs, set `NORNIR_TEST_AUTOPASS=1`. This patches
`ShowWithPassFail` to auto-return `True` and switches matplotlib to the `Agg` backend:

```bash
export NORNIR_TEST_AUTOPASS=1
```

For **interactive** (GUI) runs, leave the variable unset and ensure `DISPLAY` is set
(the cloud agent VM uses `DISPLAY=:1` via VNC). The tests will show matplotlib windows
and wait for you to click Pass or Fail.

### nornir-shared

```bash
cd /workspace/nornir-shared
python -m pytest test/ -v --tb=short
```

Expected: ~65% pass rate (11/17 tests)

### nornir-pools

```bash
cd /workspace/nornir-pools
python -m pytest test/ -v --tb=short
```

Expected: ~78% pass rate (7/9 tests)

### nornir-imageregistration

```bash
cd /workspace/nornir-imageregistration
PYTHONPATH=test:$PYTHONPATH NORNIR_TEST_AUTOPASS=1 \
  python -m pytest test/ -v --tb=short \
    --ignore=test/transforms --ignore=test/__init__.py \
    --ignore=test/test_SliceToSliceBrute.py --ignore=test/test_assemble.py \
    -k "not test_volume"
```

Expected: ~64% pass rate (97/151 tests in auto-pass mode)

Note: Some tests require ImageMagick (`convert` command).
`test_SliceToSliceBrute.py` requires Qt. `test_assemble.py` has shared-memory issues
on some systems. The `transforms` subpackage has import-path issues with pytest.

### nornir-buildmanager

```bash
cd /workspace/nornir-buildmanager
PYTHONPATH=test:$PYTHONPATH python -m pytest test/ -v --tb=short
```

Expected: ~67% pass rate (28/42 tests)

## GitHub Actions Integration

**Important**: Due to the large size of the test data (24GB), the GitHub workflows do NOT automatically download the test data during CI runs. This is intentional to keep CI times reasonable.

### Current CI Behavior
- Creates empty test data directories
- Sets environment variables correctly
- Runs tests (many will skip or fail without actual test data)
- Suitable for basic smoke tests and tests that don't require the full dataset

### Options for Full Test Coverage in CI

1. **Self-Hosted Runner** (Recommended)
   - Set up a self-hosted GitHub Actions runner
   - Pre-download test data to the runner's storage
   - Configure workflows to use the self-hosted runner for full test runs

2. **Minimal Test Dataset**
   - Create a subset of test data (<10GB) for CI
   - Use GitHub Actions cache to store it between runs
   - Keep full dataset for local/manual testing

3. **Manual Workflow Dispatch**
   - Add a workflow_dispatch trigger with an option to download full test data
   - Use only when needed (e.g., before releases)

### Workflow Configuration

The workflows are configured in:
- `nornir-shared/.github/workflows/python-app.yml`
- `nornir-imageregistration/.github/workflows/python-app.yml`
- `nornir-buildmanager/.github/workflows/python-app.yml`

## Dependencies

### ImageMagick
Some imageregistration tests require ImageMagick:
- **Cloud Agents**: ImageMagick is pre-installed (version 6.9.12)
  - Command: `convert` (ImageMagick 6.x)
  - Verify: `convert --version`
- **Local Development**: Install via package manager
  - Ubuntu/Debian: `sudo apt-get install imagemagick`
  - macOS: `brew install imagemagick`
  - Windows: Download from https://imagemagick.org/

### Python Requirements
All packages require Python 3.13+. Use the virtual environment at `/workspace/venv/pyre314/` for cloud agents.

## Known Issues

1. **CI Test Data**: GitHub Actions workflows do NOT download the 24GB test data automatically
   - Use self-hosted runners or create a minimal test dataset for full CI coverage
2. **GUI Tests (Pass/Fail)**: Several imageregistration tests use `ShowWithPassFail` which
   blocks until a Pass or Fail button is clicked. Use `NORNIR_TEST_AUTOPASS=1` for CI or
   provide a display server (VNC) for interactive runs.
3. **Console Tests**: `nornir-shared` console/curses tests fail without a display server
4. **Memory / Bus Errors**: `test_assemble.py::test_TransformImage*` can crash with Bus error
   due to shared memory usage
5. **Path Separators**: Some tests have hardcoded Windows paths that fail on Linux
6. **ImageMagick Version**: Tests call `magick` (v7 syntax) but cloud agents have v6 (`convert`)
7. **Qt Dependency**: `test_SliceToSliceBrute.py` requires PyQt6/PySide6
8. **Import Paths**: `nornir-buildmanager` and `nornir-imageregistration` tests use bare imports
   (`import testbase`, `import setup_imagetest`) — add `PYTHONPATH=test:$PYTHONPATH`

## Test Results Summary

| Package | Passed | Failed | Pass Rate | Notes |
|---------|--------|--------|-----------|-------|
| nornir-shared | 11 | 6 | 64.7% | 4 console/curses, 2 path issues |
| nornir-pools | 7 | 0 | 100% | 2 skipped base classes |
| nornir-buildmanager | 28 | 14 | 66.7% | Missing `ir-refine-grid`, `magick` v7 |
| nornir-imageregistration | 97 | 54 | 64.2% | Auto-pass mode, excludes transforms/assemble |

## Future Improvements

1. **Caching**: Implement caching strategy for CI to avoid repeated downloads
2. **Optimization**: Reduce test data size by removing unused files
3. **Dependencies**: Add ImageMagick v7 to CI environment
4. **Selective Testing**: Run only relevant tests based on changed files
5. **Test Data Hosting**: Consider faster/more reliable hosting options
6. **Fix `magick` vs `convert`**: Update tests or install ImageMagick v7
