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

### nornir-shared

```bash
cd /workspace/nornir-shared
python -m unittest discover -s ./test -p 'test_*.py'
```

Expected: ~65% pass rate (11/17 tests)

### nornir-pools

```bash
cd /workspace/nornir-pools
python -m unittest discover -s ./test -p 'test_*.py'
```

Expected: ~78% pass rate (7/9 tests)

### nornir-imageregistration

```bash
cd /workspace/nornir-imageregistration
python -m unittest discover -s ./test -p 'test_grid_division*.py'
```

Note: Some tests require ImageMagick to be installed.

### nornir-buildmanager

```bash
cd /workspace/nornir-buildmanager
python -m unittest discover -s ./test -p 'test_pipelinemanager*.py'
```

Expected: 100% pass rate for pipeline manager tests

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
2. **GUI Tests**: Console/curses tests fail without a display server
3. **Memory**: Full imageregistration test suite may cause memory issues
4. **Path Separators**: Some tests have hardcoded Windows paths that fail on Linux

## Test Results Summary

| Package | Total Tests | Pass Rate | Notes |
|---------|-------------|-----------|-------|
| nornir-shared | 17 | 64.7% | 4 GUI-related errors |
| nornir-pools | 9 | 77.8% | 2 skipped tests |
| nornir-buildmanager | 1+ | 100% | Sample tests |
| nornir-imageregistration | Many | Varies | Requires ImageMagick |

## Future Improvements

1. **Caching**: Implement caching strategy for CI to avoid repeated downloads
2. **Optimization**: Reduce test data size by removing unused files
3. **Dependencies**: Add ImageMagick to CI environment
4. **Selective Testing**: Run only relevant tests based on changed files
5. **Test Data Hosting**: Consider faster/more reliable hosting options
