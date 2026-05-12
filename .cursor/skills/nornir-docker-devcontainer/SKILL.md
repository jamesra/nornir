---
name: nornir-docker-devcontainer
description: >-
  Sets up the Nornir Docker-based dev container for Cursor and PyCharm: CuPy on a
  CUDA-capable GPU stack, WSL2-mounted test input as TESTINPUTPATH, tmp test output,
  bind-mounted monorepo at /workspace by default (optional named-volume clone mode),
  pytest-ready venv, and editable installs. Use when opening Dev Containers,
  configuring nornir-docker/.env from dev/example.cursor-dev.run.env for cursor-dev,
  bind-mounting workspace for host
  recovery, PyCharm Docker interpreter, GPU compose options, or explaining how
  TESTINPUTPATH maps from Windows/WSL2.
---

# Nornir Docker dev container (Cursor and PyCharm)

## Source of truth

Dockerfiles, Compose files, and **checked-in env examples** for Nornir live in the **`nornir-docker/`** directory. In the monorepo that directory is the **`nornir-docker` git submodule** (same content as the standalone `nornir/nornir-docker` repository). Overview and script index: [nornir-docker/README.md](../../../nornir-docker/README.md); narrative docs in the monodoc under `docs/docker/`.

For **build vs run scripts**, `docker-build.ps1` CWD-only build-arg files (`build.env`, `.build.<id>.env`), user-local `NORNIR_DOCKER_USER_ROOT` for run templates, and co-located `example.<id>.build.env` / `example.<id>.run.env` templates, see the **docker-build-run-phases** skill.

## Examples vs local environment (do not commit secrets)

- **Committed:** templates such as `nornir-docker/dev/example.cursor-dev.run.env`, `nornir-docker/example._shared.build.env`, plus root stubs like `.env.cursor-dev.example` pointing at those files.
- **Not committed:** real `.env` files, tokens, or machine-specific paths. [`nornir-docker/.gitignore`](../../../nornir-docker/.gitignore) ignores `.env`, `build.env`, `.build.*.env`, legacy `.env.build*`, non-example `*.build.env` / `*.run.env`, etc.; keep secrets in a **user-local** tree or paths under `$NORNIR_DOCKER_USER_ROOT` (see docker-build-run-phases).

**cursor-dev:** copy **`nornir-docker/dev/example.cursor-dev.run.env`** to **`nornir-docker/.env`** so Compose can substitute `${NORNIR_TESTDATA_HOST}` (project directory `nornir-docker/`). Prefer the user-local root for overrides rather than committing a personal `.env`.

## What this is

The repo ships a **cursor-dev** Compose stack (services **cursor-dev** and **cursor-dev-clone**) and image `nornir:dev-cursor-base` that match `.cursor/environment.json`: monorepo at `/workspace`, read-only fixtures at `/nornir-testdata`, and standard test env vars. Same layout works for **Cursor Dev Containers** and **PyCharm** (Docker Compose or remote interpreter against the same container).

**CuPy and CUDA:** the dev image **includes CuPy** (see `CUPY_PACKAGE` in `nornir-docker/dev/Dockerfile`, e.g. `cupy-cuda13x`). Treat the stack as **building on a working CUDA environment**: the **host** must run a compatible NVIDIA driver, Docker must expose GPUs to the container (`--gpus all` or equivalent), and the NVIDIA Container Toolkit (or Docker Desktop GPU support) must be correctly installed so device nodes and libraries are available at runtime. Without GPU passthrough, the container still runs, but CuPy GPU paths are not usable.

Authoritative files:

- `nornir-docker/compose.cursor-dev.yaml` — **cursor-dev** (bind-mounted repo root) and **cursor-dev-clone** (named volume + clone)
- `nornir-docker/cursor-dev-entry.sh` — workspace prep (`mounted` vs `clone`) + `pip install -e` order
- `nornir-docker/dev/Dockerfile` — image: Python 3.14, git, ImageMagick, CuPy, pytest, venv
- `.devcontainer/devcontainer.json` — default: compose **cursor-dev** + `workspaceFolder` `/workspace`
- `.devcontainer/cursor-dev-clone/devcontainer.json` — optional: compose **cursor-dev-clone** (fresh clone in volume)
- `docs/docker/cursor_dev.rst` — human-oriented walkthrough

## Preconditions

- **Docker** with WSL2 backend on Windows (or Linux with NVIDIA Container Toolkit when using GPU).
- **CUDA stack (for GPU / CuPy):** NVIDIA driver on the host, GPU-enabled Docker, and a CuPy wheel in the image that matches the CUDA generation you rely on (change `CUPY_PACKAGE` at image build time if you must target a different CUDA line).
- **Test data** on the **WSL2 Linux filesystem** (not `D:\...` via DrvFS) for stable I/O; that host path becomes the bind source for `/nornir-testdata` in the container.
- **GPU passthrough**: use `--gpus all` (or compose `deploy` reservations) when you want devices visible; omitting GPU flags leaves CuPy installed but GPU code paths without hardware.

## Environment variables (inside the container)

| Variable | Typical value | Role |
|----------|-----------------|------|
| `TESTINPUTPATH` | `/nornir-testdata` | Read-only mount; must match `.cursor/environment.json` and test expectations |
| `TESTOUTPUTPATH` | `/tmp/nornir-test-output` | Writable scratch for artifacts, Hypothesis DB, plot outputs, etc. |
| `NORNIR_HEADLESS` | `1` (set in image) | Headless matplotlib / CI-style tests |
| `NORNIR_CLONE_URL` | `https://github.com/jamesra/nornir.git` | Clone source when `/workspace` is empty or for **cursor-dev-clone** refresh |
| `NORNIR_CLONE_BRANCH` | `dev` | Branch for clone / optional sync (case-sensitive git branch name) |
| `NORNIR_WORKSPACE_STRATEGY` | `mounted` (default service) / `clone` (**cursor-dev-clone**) | `mounted`: bind-mounted checkout — fetch only unless `NORNIR_SYNC_REMOTE=1`. `clone`: appliance-style refresh to clone branch. |
| `NORNIR_SYNC_REMOTE` | unset (`0` effective) | Set to `1` on **cursor-dev** to checkout `NORNIR_CLONE_BRANCH` and `git pull --ff-only` on each start |
| `NORNIR_WORKSPACE_HOST` | `..` (default) | Host bind source for **cursor-dev**; relative to `nornir-docker/` compose file dir (parent = monorepo root) |

Compose sets `TESTINPUTPATH` / `TESTOUTPUTPATH` on **cursor-dev**; keep PyCharm run configs aligned with the same values.

## Host configuration (WSL test data)

1. Copy `nornir-docker/dev/example.cursor-dev.run.env` to `nornir-docker/.env` (or place the same variables under `$NORNIR_DOCKER_USER_ROOT/dev/cursor-dev.run.env`—see docker-build-run-phases; Compose still expects `nornir-docker/.env` for variable substitution unless you use another mechanism).
2. Set `NORNIR_TESTDATA_HOST` to the **Linux path** where `nornir-testdata` lives (e.g. from WSL: `echo $HOME` and append `/nornir-testdata`).
3. Ensure Docker can bind-mount that path (Docker Desktop file sharing prompts if needed).

Compose binds `${NORNIR_TESTDATA_HOST}` → `/nornir-testdata`; the container exposes that path as the value of `TESTINPUTPATH`.

## Build and run

**Build (images):** `nornir-docker/docker-build.ps1` from the monorepo root (see docker-build-run-phases).

**Run (cursor-dev container):** `nornir-docker/run-cursor-dev.ps1` (optional `-Gpu`, `-Clone`), or raw Compose:

From monorepo root:

```bash
docker compose -f nornir-docker/compose.cursor-dev.yaml build cursor-dev
docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm --gpus all cursor-dev
docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev-clone
```

- **`--gpus all`**: pass on every run if you want **all GPUs visible by default** (matches the expectation for GPU development). For Dev Containers, add equivalent GPU settings (see below) so you do not rely on remembering the CLI flag.
- Without `--gpus all`, the container still starts; CuPy/GPU code paths need the flag (or compose-level `deploy` reservations) to see devices.

## Entry script behavior

On container start, **`cursor-dev-entry.sh`** runs before your shell:

**Service `cursor-dev` (`NORNIR_WORKSPACE_STRATEGY=mounted`):**

1. If `/workspace` is empty: shallow `git clone` from `NORNIR_CLONE_URL` / `NORNIR_CLONE_BRANCH` (first-time empty bind only).
2. If `/workspace` is already a git repo: `git fetch`; **only** if `NORNIR_SYNC_REMOTE=1`: checkout clone branch and `git pull --ff-only`.
3. Best-effort `git submodule update --init --recursive`.
4. **`pip install --no-cache-dir -e`** for `nornir-shared`, `nornir-pools`, `nornir-imageregistration`, `dm4`, `nornir-buildmanager` in that order (same as `dev/Dockerfile`).

**Service `cursor-dev-clone` (`NORNIR_WORKSPACE_STRATEGY=clone`):** clone when empty; when `.git` exists, fetch/checkout/pull to `NORNIR_CLONE_BRANCH`. Optional `NORNIR_CLONE_REFRESH=1` wipes `/workspace` before clone (parity with cursor worker). Then submodules (best effort) and the same editable installs.

**Submodules:** shallow clone may omit full submodule trees; use `NORNIR_CLONE_DEPTH=0` or `full` for a full clone if needed. Some submodule URLs are SSH (`git@github.com:...`); HTTPS-only environments need URL rewrites or SSH keys inside the container.

After entry completes, **`pytest`** from `/workspace` is the supported path for unit tests; no extra image configuration is required for a basic run (headless stack is preinstalled).

## `/workspace`: bind default vs named volume clone

**Default (`cursor-dev`):** `/workspace` is a **bind mount** of the monorepo root (`${NORNIR_WORKSPACE_HOST:-..}` relative to the `nornir-docker/` compose file). Edits on the host appear in the container.

**Clone (`cursor-dev-clone`):** `/workspace` is the **named volume** `cursor-dev-work`. Data survives container removal but is not a normal host folder. Use **cursor-dev-clone**, `run-cursor-dev.ps1 -Clone`, or the **Nornir (cursor-dev clone)** Dev Container configuration.

## Cursor Dev Containers

Default **`.devcontainer/devcontainer.json`** uses compose service **`cursor-dev`** and `workspaceFolder` `/workspace`. Open the **monorepo root** and use **Reopen in Container**.

For a **fresh clone inside Docker** (named volume), use **Dev Containers: Reopen in Container** (or reopen with configuration) and select **Nornir (cursor-dev clone)** — **`.devcontainer/cursor-dev-clone/devcontainer.json`**, service **`cursor-dev-clone`**.

To make **GPU the default** for Dev Containers, add NVIDIA-style reservations to the **cursor-dev** service in compose (Compose v2 + Docker Engine), or use the devcontainer `runArgs` / features approach [documented by VS Code for GPU](https://code.visualstudio.com/remote/advancedcontainers/add-gpu-support) so every attach gets GPU without manual `docker compose run` flags.

## PyCharm

- **Docker Compose** interpreter: select `nornir-docker/compose.cursor-dev.yaml`, service **cursor-dev** (bind mount) or **cursor-dev-clone** (named volume clone), Python **`/opt/venv/bin/python`** (image venv).
- Map project dir to **`/workspace`** so paths match the container.
- Set env vars in run/debug templates to match `TESTINPUTPATH` / `TESTOUTPUTPATH` if PyCharm does not inherit them from Compose.

PyCharm does not use `.devcontainer/devcontainer.json`; it consumes the same Compose file and env files.

## Git commit and push

The image includes **git**. For **push**, configure credentials inside the persistent workspace or mount:

- Mount **SSH agent** or `~/.ssh` read-only, **or**
- Use HTTPS with a credential helper / personal access token (avoid baking secrets into the image).

Set `user.name` / `user.email` in the container (or via repo-local git config) before committing.

## Quick verification checklist

- [ ] `nornir-docker/.env` exists with `NORNIR_TESTDATA_HOST` pointing at WSL-side test data
- [ ] `docker compose ... run` includes **`--gpus all`** (or compose-level GPU) when GPU access is required
- [ ] In container: `echo $TESTINPUTPATH` → `/nornir-testdata`, `echo $TESTOUTPUTPATH` → under `/tmp`
- [ ] `/workspace` contains the monorepo; `pip list` shows editable installs for Nornir packages
- [ ] `git status` works; remote push tested with your chosen auth method
- [ ] `pytest` runs from `/workspace` for the packages you care about
- [ ] When using GPU: inside the container, `import cupy` works and a trivial GPU array (e.g. `cupy.arange(3)`) runs without CUDA runtime errors

## Additional documentation

For narrative docs and diagrams, see [docs/docker/cursor_dev.rst](../../../docs/docker/cursor_dev.rst).
