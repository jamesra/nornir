# Nornir release metadata

## Files

- **[../VERSION](../VERSION)** — One line: the **monorepo release id** (e.g. `1.7.0`). Git tag releases as `v` + that value (e.g. `v1.7.0`).
- **[package-versions.yaml](package-versions.yaml)** — Maps each **distribution** to the version shipped in that monorepo release, plus `path` and whether it is included in **headless Docker** images (`docker: true` / `false`).

## Release checklist

1. Bump versions in individual packages (`pyproject.toml` or `dm4/dm4/__init__.py`) as needed.
2. Update **[package-versions.yaml](package-versions.yaml)** so each `version` matches the tree.
3. Bump **[../VERSION](../VERSION)** when you are cutting a new **monorepo** release (not every package bump requires a monorepo bump—only when you tag).
4. Run **`python release/verify_package_versions.py`** from the repo root (requires **PyYAML**: `pip install pyyaml`).
5. Commit; tag **`v$(cat VERSION)`**.
6. Build Docker images using **[nornir-docker/docker-build.ps1](../nornir-docker/docker-build.ps1)** or pass the same `--build-arg` values documented in [nornir-docker/README.md](../nornir-docker/README.md).
7. **Pyre (Windows):** pushing a `v*` tag runs `.github/workflows/pyre-windows-release.yml`; verify `Pyre-<version>-Setup.exe` on the GitHub Release.

## Pyre Windows installer

- **End-user docs:** `docs/packages/pyre_install.rst`
- **Developer / packaging:** `docs/development/pyre_development.rst`
- **Generate local constraints:** `python release/generate_pyre_windows_constraints.py` → `release/pyre-windows-constraints.txt` (machine-local paths; do not commit)
- **Build locally:** `nornir-pyre/packaging/windows/build-freeze.ps1`

## Docker OCI labels

Image build passes `NORNIR_RELEASE` (from `VERSION`), `SOURCE_REVISION` (git SHA), `BUILD_DATE`, and **base64(minified JSON)** of docker-included package versions for `org.nornir.package_versions.json.base64`. Decode with base64 then parse JSON, or inspect all labels with `docker image inspect nornir:dev --format '{{json .Config.Labels}}'`.
