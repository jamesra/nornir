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

The GitHub workflows have been updated to automatically download and extract test data during CI runs. The workflow:

1. Downloads `nornir-testdata.zip` from rogue1.codepharm.net
2. Extracts it to the workspace
3. Sets environment variables
4. Runs the tests

### Workflow Configuration

The workflows are configured in:
- `nornir-shared/.github/workflows/python-app.yml`
- `nornir-imageregistration/.github/workflows/python-app.yml`
- `nornir-buildmanager/.github/workflows/python-app.yml`

## Known Issues

1. **ImageMagick Dependency**: Some imageregistration tests require the `magick` command
2. **GUI Tests**: Console/curses tests fail without a display server
3. **Memory**: Full imageregistration test suite may cause memory issues
4. **Download Time**: 24GB download adds significant time to CI runs

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
