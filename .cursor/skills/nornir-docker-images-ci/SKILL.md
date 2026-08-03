---
name: nornir-docker-images-ci
description: >-
  Maintains the Nornir Docker image catalogue (dev, prod, cupy, dev-cursor-base,
  cursor-worker): which Dockerfile and build-args apply, docker-build.ps1 OCI/BOM
  labels, constraints-headless.txt, submodule commit order, and Compose review
  checklist. Use when changing Dockerfiles, adding images, bumping Python/CuPy bases,
  CI build steps, or reviewing image/compose diffs—not for day-to-day devcontainer
  setup (see nornir-docker-devcontainer).
---

# Nornir Docker images and CI maintenance

## Source of truth (do not duplicate long guides here)

- Image catalogue and build commands: [docs/docker/images.rst](../../../docs/docker/images.rst)
- Script index: [nornir-docker/README.md](../../../nornir-docker/README.md)
- Monodoc index: <https://nornir.github.io/docker/index.html>
- Build/run env layering: **docker-build-run-phases** skill
- Dev shell / Dev Containers: **nornir-docker-devcontainer** skill
- Windows `D:\Docker` layout: **docker-machine-layout** skill

## Image matrix

| Tag | Dockerfile | Key build-args | Monorepo at build | Packages at runtime |
|-----|------------|----------------|-------------------|---------------------|
| `nornir:dev` | `dev/Dockerfile` | `CUPY_PACKAGE` (default `cupy-cuda13x`), `INSTALL_MONOREPO_EDITABLES=1` | Baked under `/opt/nornir` | Same (image) |
| `nornir:dev-cursor-base` | `dev/Dockerfile` | `INSTALL_MONOREPO_EDITABLES=0` | Not baked | `install-monorepo-editables.sh` from `/workspace` at start |
| `nornir:cursor-worker` | `Dockerfile.cursor-worker` | `BASE_IMAGE=nornir:dev-cursor-base` | Not baked | `/workspace` via `cursor-worker-entry.sh` |
| `nornir:prod` | `prod/Dockerfile` | `INSTALL_CUPY=0` (default) | Baked | Image |
| `nornir:cupy` | `prod/Dockerfile` | `INSTALL_CUPY=1`, `CUPY_PACKAGE` | Baked | Image |

**Compose stacks (run phase, not separate image tags):** `cursor-dev` / `cursor-dev-clone` (`compose.cursor-dev.yaml`), `nornir-cursor-worker` (`compose.cursor-worker.yaml`), `nornir` / `nornir-prod` / `nornir-cupy` (`compose.yaml`).

Shared constraints: `nornir-docker/constraints-headless.txt` (dev + prod pip installs).

## `docker-build.ps1` build order

From the **invocation directory** (script `cd`s to monorepo root for context `.`). Default builds all five in this order; `-Images` filters the set (same order):

1. `nornir:dev`
2. `nornir:dev-cursor-base` (`INSTALL_MONOREPO_EDITABLES=0`)
3. `nornir:cursor-worker` (depends on `dev-cursor-base`; selecting `cursor-worker` auto-includes the base)
4. `nornir:prod`
5. `nornir:cupy`

Examples: `.\docker-build.ps1 -Images prod,cupy` (appliance only); `-NoCache` passes `--no-cache`. Accepts `cupy`, `nornir:cupy`, or `nornir-cupy`.

Reads **`VERSION`**, git `HEAD` → `SOURCE_REVISION`, UTC `BUILD_DATE`, and `release/docker_package_versions_json.py` + `release/package-versions.yaml` → `PACKAGE_VERSIONS_JSON_B64`. Sets OCI labels (`org.opencontainers.image.*`, `org.nornir.variant`, `org.nornir.package_versions.json.base64`). Tags `nornir:<suffix>-<VERSION>` after each successful build.

Optional per-invocation overrides: `build.env`, `.build.<id>.env` where `<id>` is tag with `:` → `-` (e.g. `.build.nornir-dev.env`). Committed `example.*.build.env` files are **templates only**—copy values into invocation-dir files if needed.

## When to change what

| Change | Touch |
|--------|--------|
| Python 3.14 base, ImageMagick, pytest, shared pip pins | `dev/Dockerfile`, `prod/Dockerfile`, `constraints-headless.txt` |
| CuPy CUDA generation | `CUPY_PACKAGE` in Dockerfiles / compose build args; document host driver requirement |
| New headless package in editable set | `install-monorepo-editables.sh`, `dev/Dockerfile` COPY list, `prod/Dockerfile` if prod bakes it |
| Cursor dev workspace behavior | `cursor-dev-entry.sh`, `compose.cursor-dev.yaml` (see **nornir-docker-devcontainer**) |
| Worker agent CLI / workspace strategies | `Dockerfile.cursor-worker`, `cursor-worker-entry.sh`, `example.nornir-cursor-worker.run.env` |
| BOM / release versions | `release/package-versions.yaml`, `VERSION`; rebuild images for label refresh |

## Submodule commit order

1. Commit and push (if applicable) inside **`nornir-docker`**.
2. In the parent monorepo, commit the updated submodule pointer.
3. Update monodoc under `docs/docker/` when operator-facing behavior changes.

## Dockerfile / Compose review checklist

- [ ] Build context remains **monorepo root** (`context: ..` from `nornir-docker/` compose files).
- [ ] `COPY` order: expensive layers (ImageMagick compile, pip installs) before frequently changing `COPY` of source.
- [ ] `ARG` scope: args used in `RUN` must be declared before that `RUN`; document intentional defaults in `example.*.build.env`.
- [ ] No secrets in `ARG`/`ENV`/`LABEL`; runtime secrets only via `--env-file` / Compose env files (gitignored).
- [ ] Compose: `${NORNIR_TESTDATA_HOST}` and other required vars documented in `example.*.run.env`; unset vars produce empty bind sources (fail loudly in docs, not silently in production).
- [ ] No duplicate `/workspace` mounts between Compose and devcontainer.json.
- [ ] GPU: document `--gpus all` or compose device reservations where CuPy GPU paths matter.
- [ ] After image changes: `docker compose -f nornir-docker/compose.cursor-dev.yaml config` (or relevant compose file) validates merge.

## CI / release notes

- Prefer **`docker-build.ps1`** (or `build.cmd`) over raw `docker build` when OCI labels and BOM JSON must match release artifacts.
- Inspect labels: `docker image inspect nornir:dev --format '{{json .Config.Labels}}'`
- Decode BOM: see [docs/docker/images.rst](../../../docs/docker/images.rst) (base64 label `org.nornir.package_versions.json.base64`).
- Release checklist: `release/README.md`; tag policy `v` + `VERSION` file.

## Anti-patterns

- Baking monorepo into `dev-cursor-base` / worker images (`INSTALL_MONOREPO_EDITABLES=0` is intentional).
- Committing `nornir-docker/.env`, `.env.cursor-worker`, or personal `build.env` with secrets.
- Using `GetComputationModule()`-style global backend choices in Docker docs (unrelated but common confusion): image Python is `/opt/venv/bin/python`.
- Duplicating long operational prose in this skill—link to monodoc and README instead.
