# Nornir GitHub Workflow Fixes

## Issues Identified

### 1. Python Version Mismatch
**Problem**: All nornir packages require Python >=3.13 in their `pyproject.toml` files, but GitHub workflows were configured to use Python 3.10.

**Impact**: All workflow runs failed with error: `ERROR: Package 'nornir-*' requires a different Python: 3.10.x not in '>=3.13'`

**Fix**: Updated all workflows to use Python 3.13

### 2. Missing Dependency Function
**Problem**: `nornir-pools` tests failed because they call `nornir_shared.misc.StartMultiprocessLoggingListener()` which was added in a recent commit to `nornir-shared` but the dependency was pinned to an older tag (`dev-v1.5.2`) that didn't have this function.

**Impact**: Tests failed with: `AttributeError: module 'nornir_shared.misc' has no attribute 'StartMultiprocessLoggingListener'`

**Fix**: Updated dependency references to use the latest `dev` branch instead of the outdated tag

### 3. Outdated GitHub Actions
**Problem**: Workflows used deprecated GitHub Actions versions (v3) which trigger warnings and will stop working in the future.

**Impact**: Warnings in workflow output about Node.js 20 deprecation

**Fix**: Updated to latest action versions:
- `actions/checkout@v3` → `actions/checkout@v4`
- `actions/setup-python@v3` → `actions/setup-python@v5`

## Changes Made

### Successfully Applied (with push access)

#### nornir-pools
- ✅ Updated workflow to Python 3.13
- ✅ Updated GitHub Actions to v4/v5
- ✅ Updated `nornir_shared` dependency from `dev-v1.5.2` tag to `dev` branch
- ✅ Committed and pushed to `dev` branch

### Pending (requires manual application)

The following repositories need the patches applied manually due to access restrictions:

#### nornir-buildmanager
- Patch file: `nornir-buildmanager-fix.patch`
- Changes:
  - Updated workflow to Python 3.13
  - Updated GitHub Actions to v4/v5
  - Updated dependencies to use latest `dev` branches
  - Changed `nornir_imageregistration` reference from `cupy-v1.6.5` to `CuPy` branch

#### nornir-imageregistration
- Patch file: `nornir-imageregistration-fix.patch`
- Changes:
  - Updated workflow to Python 3.13
  - Updated GitHub Actions to v4/v5
  - Updated dependencies to use latest `dev` branches

#### nornir-shared
- Patch file: `nornir-shared-fix.patch`
- Changes:
  - Updated workflow to Python 3.13
  - Updated GitHub Actions to v4/v5

## How to Apply Patches

For each repository that needs fixes:

```bash
# Navigate to the repository
cd /path/to/nornir-buildmanager

# Apply the patch
git am < /path/to/nornir-buildmanager-fix.patch

# Push to the appropriate branch
git push origin dev
```

## Recommended Improvements

### 1. Centralized Workflow Configuration
Consider using GitHub's reusable workflows to maintain a single workflow definition that all nornir packages can use. This would:
- Reduce duplication
- Ensure consistency across packages
- Make updates easier

Example structure:
```
nornir/.github/workflows/
├── reusable-python-test.yml  # Centralized workflow
└── ...

nornir-pools/.github/workflows/
└── test.yml  # Calls reusable workflow
```

### 2. Multi-Python Version Testing
Add a matrix strategy to test against multiple Python versions:
```yaml
strategy:
  matrix:
    python-version: ["3.13", "3.14"]
    os: [ubuntu-latest, macos-latest, windows-latest]
```

### 3. Dependency Management
- Consider using version tags consistently across all packages
- When adding new features that other packages depend on, create and push tags immediately
- Document the dependency graph clearly

### 4. Automated Dependency Updates
- Use Dependabot or Renovate to keep GitHub Actions and Python dependencies up to date
- Set up automated PRs for dependency updates

### 5. Better Test Coverage
- Add code coverage reporting
- Run linting (flake8, pylint, mypy) in CI
- Add pre-commit hooks for local development

## Testing Status

After applying these fixes:
- ✅ nornir-pools: Workflow should now pass (pushed to dev)
- ⏳ nornir-buildmanager: Awaiting patch application
- ⏳ nornir-imageregistration: Awaiting patch application  
- ⏳ nornir-shared: Awaiting patch application

## Next Steps

1. Apply the patches to the repositories without push access
2. Monitor the next workflow runs to verify fixes
3. Consider implementing the recommended improvements
4. Update documentation to reflect Python 3.13 requirement
