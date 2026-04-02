# Nornir Workflow Improvement Guide

## Quick Start: Applying Fixes

### For Repositories with Push Access

The fixes have already been applied and pushed to:
- ✅ **nornir-pools** (dev branch)

### For Repositories Requiring Manual Application

Apply the provided patches to fix the immediate issues:

```bash
# nornir-buildmanager
cd /path/to/nornir-buildmanager
git checkout dev
git am < nornir-buildmanager-fix.patch
git push origin dev

# nornir-imageregistration  
cd /path/to/nornir-imageregistration
git checkout CuPy
git am < nornir-imageregistration-fix.patch
git push origin CuPy

# nornir-shared
cd /path/to/nornir-shared
git checkout dev
git am < nornir-shared-fix.patch
git push origin dev
```

## Workflow Configuration Options

Three workflow configuration approaches are provided:

### Option 1: Reusable Workflow (Recommended for Consistency)

**Best for**: Maintaining consistency across all nornir packages

**Setup**:
1. The reusable workflow is defined in `nornir/.github/workflows/reusable-python-test.yml`
2. Each package calls this workflow with custom parameters
3. See `example-package-test.yml` for usage

**Pros**:
- Single source of truth
- Easy to update all packages at once
- Consistent behavior across packages

**Cons**:
- Requires packages to reference the main nornir repo
- Less flexibility for package-specific needs

### Option 2: Enhanced Standalone Template (Recommended for Flexibility)

**Best for**: Packages with unique testing requirements

**Setup**:
1. Copy `enhanced-python-test-template.yml` to each package's `.github/workflows/`
2. Customize the test pattern and any package-specific steps
3. Commit and push

**Pros**:
- Full control over workflow in each package
- Easy to customize per-package
- No external dependencies

**Cons**:
- Need to update each package individually
- Potential for drift between packages

### Option 3: Current Approach (Already Fixed)

**Best for**: Minimal changes to existing setup

The patches already applied use this approach - updating existing workflows in place.

## Detailed Improvement Recommendations

### 1. Multi-Version Python Testing

Add a matrix to test multiple Python versions:

```yaml
strategy:
  matrix:
    python-version: ["3.13", "3.14"]
```

**Benefits**:
- Catch version-specific issues early
- Ensure compatibility across Python versions
- Build confidence in version support claims

**When to implement**: After current fixes are stable

### 2. Code Coverage Tracking

Add coverage reporting to workflows:

```yaml
- name: Run tests with coverage
  run: |
    pip install pytest pytest-cov
    pytest --cov=. --cov-report=xml --cov-report=html

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
```

**Benefits**:
- Track test coverage over time
- Identify untested code paths
- Improve code quality

**Setup required**:
1. Sign up for Codecov
2. Add repository to Codecov
3. Add CODECOV_TOKEN to repository secrets

### 3. Linting and Type Checking

Add a separate linting job:

```yaml
lint:
  runs-on: ubuntu-latest
  steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.13"
  - name: Install tools
    run: pip install flake8 mypy pylint black
  - name: Run linters
    run: |
      flake8 . --count --statistics
      mypy . --ignore-missing-imports
      black --check .
```

**Benefits**:
- Enforce code style consistency
- Catch type errors before runtime
- Improve code maintainability

### 4. Dependency Management

#### Automated Updates with Dependabot

Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
```

**Benefits**:
- Automatic PR creation for dependency updates
- Security vulnerability notifications
- Keep dependencies current

#### Version Pinning Strategy

Current approach (after fixes):
- Use `dev` branch for inter-nornir dependencies
- Pin external dependencies with minimum versions

**Recommendation**: Create version tags when features are stable:

```bash
# In nornir-shared after adding new features
git tag -a v1.5.3 -m "Add centralized logging support"
git push origin v1.5.3

# Then update dependent packages to use the tag
# pyproject.toml:
# nornir_shared @ git+https://github.com/jamesra/nornir-shared.git@v1.5.3
```

### 5. Pre-commit Hooks

Add `.pre-commit-config.yaml` to each repository:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

**Benefits**:
- Catch issues before committing
- Enforce code style locally
- Reduce CI failures

**Setup**:
```bash
pip install pre-commit
pre-commit install
```

### 6. Documentation Generation

Add a docs job to build and publish documentation:

```yaml
docs:
  runs-on: ubuntu-latest
  steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.13"
  - name: Install dependencies
    run: |
      pip install sphinx sphinx-rtd-theme
      pip install .
  - name: Build docs
    run: |
      cd docs
      make html
  - name: Deploy to GitHub Pages
    uses: peaceiris/actions-gh-pages@v3
    if: github.ref == 'refs/heads/master'
    with:
      github_token: ${{ secrets.GITHUB_TOKEN }}
      publish_dir: ./docs/_build/html
```

## Implementation Priority

### Immediate (Critical Fixes)
1. ✅ Fix Python version mismatch
2. ✅ Fix missing dependency function
3. ✅ Update GitHub Actions versions
4. ⏳ Apply patches to remaining repositories

### Short Term (Next 2 Weeks)
1. Verify all workflows pass after fixes
2. Choose and implement workflow configuration approach (Option 1 or 2)
3. Add code coverage tracking
4. Set up Dependabot

### Medium Term (Next Month)
1. Add linting to CI
2. Implement pre-commit hooks
3. Add multi-version Python testing
4. Document dependency management strategy

### Long Term (Next Quarter)
1. Implement automated documentation builds
2. Add performance benchmarking
3. Consider containerized test environments
4. Explore GitHub Actions caching strategies

## Monitoring and Maintenance

### Weekly
- Review Dependabot PRs
- Check workflow success rates
- Monitor test execution times

### Monthly
- Review code coverage trends
- Update Python versions in matrix
- Audit dependency versions

### Quarterly
- Review and update workflow configurations
- Evaluate new GitHub Actions features
- Update documentation

## Getting Help

### Common Issues

**Issue**: Workflow fails with "Permission denied"
**Solution**: Check repository settings → Actions → Workflow permissions

**Issue**: Tests pass locally but fail in CI
**Solution**: Check environment variables and test data paths

**Issue**: Dependency installation takes too long
**Solution**: Enable pip caching in setup-python action

### Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Packaging Guide](https://packaging.python.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)

## Questions?

For questions about these improvements, open an issue in the main nornir repository.
