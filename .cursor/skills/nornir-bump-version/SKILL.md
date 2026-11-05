---
name: nornir-bump-version
description: >-
  Bump Nornir package or monorepo versions without duplicating the number.
  Use when releasing, tagging, changing pyproject version, building the Pyre
  Windows installer, or syncing release/package-versions.yaml with VERSION.
---

# Bump Nornir versions

Two different version ids exist; do not treat them as the same number.

| Id | Canonical file | Used for |
|----|----------------|----------|
| **Package** (e.g. pyre) | `<pkg>/pyproject.toml` → `[project].version` | PyPI-style package metadata, About UI (`importlib.metadata`), **Pyre installer** `Pyre-<ver>-Setup.exe` |
| **Monorepo release** | root `VERSION` | Docs Sphinx banner, Docker OCI labels, git tag `v<VERSION>` |

BOM mirror (must match each package’s pyproject): `release/package-versions.yaml`.

## Bump one package (e.g. pyre)

1. Edit **only** `nornir-<pkg>/pyproject.toml` (`version = "..."`).
2. Set the same string under that package in `release/package-versions.yaml`.
3. Do **not** edit `nornir-pyre/setup.py` (reads pyproject), `nornir-pyre/packaging/windows/pyre-installer.iss` (requires `/DMyAppVersion` from the build script), or root `VERSION` (unless also cutting a monorepo release).
4. Verify from the monorepo root:

```bash
python release/verify_package_versions.py
```

5. Commit inside the **submodule**, then bump the **umbrella pointer** (Monorepo-submodule-changes rule), including the yaml and docs changes in the umbrella commit when those changed.

### Pyre installer after a package bump

1. Add a curated ``## X.Y.Z — not yet released`` section (user-facing notes only) to
   ``nornir-pyre/pyre/CHANGELOG.user.md``. Each bullet: bold skim summary, then detail
   (see **user-changelog** rule). When the installer ships, replace ``not yet released``
   with the release date ``YYYY-MM-DD``; leave older sections below.
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

`build-installer.ps1` reads `nornir-pyre/pyproject.toml`; override only when needed with `-Version x.y.z`.

**Automatic patch bump (local builds).** Do not hand-bump the patch number for a local installer build:

- `build-freeze.ps1` first runs `release/bump_pyre_version.py --if-released`: when the current
  version's changelog heading is already dated (shipped), it moves to the next patch and opens an
  empty `## X.Y.Z+1 — not yet released` section. Move any bullets added after that release into it.
- After Inno Setup succeeds, `build-installer.ps1` writes `dist/installer/last-built-version.txt`,
  then runs `bump_pyre_version.py`: the built section gets today's date, and pyproject, the BOM and a
  new `not yet released` changelog section move to the next patch. `-NoBump` or `-Version` skips it;
  so does GitHub Actions.
- `publish_pyre_windows_release.ps1` publishes `last-built-version.txt`, not the bumped pyproject.
  A new release is tagged at the umbrella HEAD, which must already be pushed (never the default
  `master`, whose old workflow would rebuild and publish stale code). The tag push starts
  `pyre-windows-release.yml`, which skips when the release already has its installer or the tag
  version differs from that commit's pyproject.
- Commit the bumped `pyproject.toml` / `CHANGELOG.user.md` (submodule), then `package-versions.yaml`
  and the pointer (umbrella).

Docs always link the latest installer, `https://github.com/jamesra/nornir/releases/latest/download/Pyre-Setup.exe`; versioned installers stay on prior `pyre-*` releases.

## Cut a monorepo release

1. Bump any changed packages (steps above).
2. Bump root `VERSION` to the new release id. It may equal pyre’s version only by coincidence: Docker/docs use `VERSION`, the installer uses pyre’s pyproject.
3. Run `python release/verify_package_versions.py`.
4. Commit, tag `v$(Get-Content VERSION)` / `git tag v$(cat VERSION)`, push the tag (triggers the Pyre Windows release workflow on `v*`).

Human docs: `docs/development/release.rst`.
