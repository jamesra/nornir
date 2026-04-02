# Local Test Environment Setup

## Status: ✅ Ready for Testing

This environment has been configured for local testing of nornir packages.

## Installed Components

### Python
- **Version**: Python 3.13.12
- **Location**: `/usr/bin/python3.13`
- **pip**: 26.0.1 (latest)

### Nornir Packages (Editable Installs)

All packages are installed in **editable mode**, meaning changes to the source code are immediately reflected when you import the packages.

1. **nornir-shared** (v1.5.3)
   - Location: `/workspace/nornir-shared`
   - Status: ✅ Editable install
   - Includes: `StartMultiprocessLoggingListener` function

2. **nornir-pools** (v1.5.3)
   - Location: `/workspace/nornir-pools`
   - Status: ✅ Editable install
   - Tests: ✅ Passing (9 tests, 2 skipped)

3. **nornir-imageregistration** (v1.6.5)
   - Location: `/workspace/nornir-imageregistration`
   - Status: ✅ Editable install
   - Note: Depends on GitHub versions of nornir-shared/pools (not local)

4. **nornir-buildmanager** (v1.6.6)
   - Status: ❌ Not installed (dependency conflicts)
   - Issue: Requires updated nornir-imageregistration with latest dependency refs

## Testing

### Run Tests
```bash
# Test nornir-pools
cd /workspace/nornir-pools
python3.13 -m unittest discover -s ./test -p 'test_nornir_pools*.py'

# Test nornir-imageregistration
cd /workspace/nornir-imageregistration
python3.13 -m unittest discover -s ./test -p 'test_grid_division*.py'

# Test nornir-shared
cd /workspace/nornir-shared
python3.13 -m unittest discover -s ./test -p 'test_Histogram*.py'
```

### Verify Editable Installs
```bash
python3.13 -c "import nornir_pools; print(nornir_pools.__file__)"
# Should show: /workspace/nornir-pools/nornir_pools/__init__.py

python3.13 -c "import nornir_shared; import sys; print(sys.modules['nornir_shared'].__path__)"
# Should show: ['/workspace/nornir-shared/nornir_shared']
```

### Make Changes and Test
1. Edit source files in `/workspace/nornir-*/`
2. Changes are immediately available - no reinstall needed
3. Run tests to verify changes

## Test Results

### nornir-pools
```
Ran 9 tests in 33.776s
OK (skipped=2)
```
✅ All tests passing

### Known Warnings
- `WARNING:root:Multiprocess file logging disabled because NORNIR_LOG_ROOT is not set`
  - This is expected - it's an optional environment variable
  - Tests still pass without it

## Dependency Notes

### Current Setup
- nornir-shared and nornir-pools use **local editable** versions
- nornir-imageregistration uses **local editable** but its dependencies still point to GitHub
- nornir-buildmanager cannot be installed until nornir-imageregistration is updated with the patches

### To Complete Setup
Apply the patches to nornir-imageregistration and nornir-buildmanager:
```bash
cd /workspace/nornir-imageregistration
git am < /workspace/nornir-imageregistration-fix.patch

cd /workspace/nornir-buildmanager
git am < /workspace/nornir-buildmanager-fix.patch

# Then reinstall
cd /workspace/nornir-buildmanager
python3.13 -m pip install -e .
```

## Environment Variables

Optional environment variables you can set:
```bash
# Enable multiprocess logging
export NORNIR_LOG_ROOT=/tmp/nornir_logs

# Test data paths (for tests that need them)
export TESTINPUTPATH=/workspace/testdata
export TESTOUTPUTPATH=/workspace/testdata_output
```

## Package Locations

```
/workspace/
├── nornir-buildmanager/     (not installed - dependency conflict)
├── nornir-imageregistration/ (editable install)
├── nornir-pools/            (editable install) ✅ Tests passing
├── nornir-shared/           (editable install)
├── nornir-volumecontroller/ (not installed)
├── nornir-volumemodel/      (not installed)
└── nornir-web/              (not installed)
```

## Next Steps

1. ✅ Environment is ready for testing nornir-pools and nornir-shared
2. ⏳ Apply patches to nornir-imageregistration and nornir-buildmanager
3. ⏳ Install remaining packages if needed
4. ✅ Make changes to source code and test immediately

## Troubleshooting

### If tests fail
```bash
# Reinstall in editable mode
cd /workspace/nornir-pools
python3.13 -m pip install -e . --force-reinstall --no-deps
```

### If import fails
```bash
# Check installation
python3.13 -m pip show nornir_pools

# Verify editable location
python3.13 -m pip show nornir_pools | grep "Editable project location"
```

### If dependency conflicts
```bash
# This means patches need to be applied first
# See "To Complete Setup" section above
```
