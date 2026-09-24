---
name: nornir-bump-version
description: >-
  Bump Nornir package or monorepo versions without duplicating the number.
  Use when releasing, tagging, changing pyproject version, building the Pyre
  Windows installer, or syncing release/package-versions.yaml with VERSION.
---

# Bump Nornir versions

Two different version ids exist. Do not treat them as the same number.

| Id | Canonical file | Used for |
|----|----------------|----------|
| **Package** (e.g. pyre) | `<pkg>/pyproject.toml` → `[project].version` | PyPI-style package metadata, About UI (`importlib.metadata`), **Pyre installer** `Pyre-<ver>-Setup.exe` |
| **Monorepo release** | root `VERSION` | Docs Sphinx banner, Docker OCI labels, git tag `v<VERSION>` |

BOM mirror (must match each package’s pyproject): `release/package-versions.yaml`.

## Bump one package (e.g. pyre)

1. Edit **only** `nornir-<pkg>/pyproject.toml` (`version = "..."`).
2. Set the same string under that package in `release/package-versions.yaml`.
3. Do **not** edit:
   - `nornir-pyre/setup.py` (reads pyproject)
   - `nornir-pyre/packaging/windows/pyre-installer.iss` (requires `/DMyAppVersion` from the build script)
   - root `VERSION` (unless you are also cutting a monorepo release)
4. Verify from monorepo root:

```bash
python release/verify_package_versions.py
```

5. Commit inside the **submodule**, then bump the **umbrella pointer** (see Monorepo-submodule-changes rule). Include the yaml + docs changes in the umbrella commit when those files changed.

### Pyre installer after a package bump

1. Add a curated ``## X.Y.Z`` section to ``nornir-pyre/CHANGELOG.user.md`` (user-facing notes only).
2. From the monorepo root:

```powershell
python release/sync_pyre_user_changelog.py --write-docs
```

3. Build and publish (pick one):

```powershell
# Local (VS Code: "pyre: build and publish Windows release")
cd nornir-pyre\packaging\windows
.\build-freeze.ps1
.\validate-frozen.ps1
.\build-installer.ps1
cd ..\..\..
.\release\publish_pyre_windows_release.ps1

# Or tag (triggers CI)
git tag pyre-X.Y.Z
git push origin pyre-X.Y.Z
```

`build-installer.ps1` reads `nornir-pyre/pyproject.toml`. Override only when needed: `-Version x.y.z`.

Docs always link **latest** via
`https://github.com/jamesra/nornir/releases/latest/download/Pyre-Setup.exe`.
Versioned installers remain on prior `pyre-*` releases.

## Cut a monorepo release

1. Bump any packages that changed (steps above).
2. Bump root `VERSION` to the new release id (may equal pyre’s version, but that is coincidence — Docker/docs use `VERSION`, the installer uses pyre’s pyproject).
3. Run `python release/verify_package_versions.py`.
4. Commit, tag `v$(Get-Content VERSION)` / `git tag v$(cat VERSION)`, push the tag (triggers Pyre Windows release workflow on `v*`).

Human docs: `docs/development/release.rst`.
