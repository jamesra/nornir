---
name: nornir-docker-devcontainer
description: >-
  Nornir Docker dev container for Cursor and PyCharm: CuPy/CUDA GPU stack,
  WSL2-mounted TESTINPUTPATH, optional /data repro corpus (INPUT_NORNIR_DATA), tmp
  test output, /workspace bind mount (or named-volume clone mode), venv and editable
  installs. Use when opening Dev Containers, configuring nornir-docker/.env from
  dev/example.cursor-dev.run.env for cursor-dev, bind-mounting workspace for host
  recovery, PyCharm Docker interpreter, GPU compose options, or how TESTINPUTPATH
  maps from Windows/WSL2. Also when troubleshooting ("Failed to install Cursor
  server", /nornir-testdata not mounted, CIFS mounts lost after reboot, launch.json,
  skills or claude missing after a rebuild) and before any change that must persist
  across container rebuilds.
---

# Nornir Docker dev container (Cursor and PyCharm)

## Which Docker skill?

| Skill | Use when |
|-------|----------|
| **docker-build-run-phases** | Build vs run scripts, `example.*.env` templates, env layering |
| **docker-machine-layout** | Where machine-local files live under `D:\Docker` / `/srv/docker` (`Run` / `Builds` / `Data` / `Work`) |
| **nornir-docker-images-ci** | Image matrix, OCI/BOM, Dockerfile/CI review |
| **nornir-docker-devcontainer** (this) | Day-to-day cursor-dev / Dev Containers setup |
| **docker-publish-ghcr** | Push images to GHCR, pull them on clients, "users get the old image" |

## Source of truth

Dockerfiles, Compose files and checked-in env examples live in `nornir-docker/` (the `nornir-docker` git submodule, same content as the standalone `nornir/nornir-docker` repository). Overview and script index: [nornir-docker/README.md](../../../nornir-docker/README.md). Narrative docs: [docs/deployment/nornir_dev_and_worker.rst](../../../docs/deployment/nornir_dev_and_worker.rst) (images: `docs/docker/images.rst`). `stack.ps1 nornir-dev shell` runs the same `run-cursor-dev.ps1`.

| File | Role |
|------|------|
| `nornir-docker/compose.cursor-dev.yaml` | **cursor-dev** (bind-mounted repo root) and **cursor-dev-clone** (named volume + clone) |
| `nornir-docker/cursor-dev-entry.sh` | Workspace prep (`mounted` vs `clone`) + `install-monorepo-editables.sh` |
| `nornir-docker/install-monorepo-editables.sh` | `pip install -e --no-deps` for all headless packages (also used by `dev/Dockerfile` and `prod/Dockerfile`) |
| `nornir-docker/dev/Dockerfile` | Image `nornir:dev-cursor-base`: Python 3.14, git, ImageMagick, CuPy, pytest, venv |
| `.devcontainer/devcontainer.json` | Default: compose **cursor-dev**, `workspaceFolder` `/workspace` |
| `.devcontainer/cursor-dev-clone/devcontainer.json` | Optional: compose **cursor-dev-clone** (fresh clone in volume) |

The stack matches `.cursor/environment.json`: monorepo at `/workspace`, read-only fixtures at `/nornir-testdata`, optional repro corpus at `/data`, standard test env vars. Cursor Dev Containers and PyCharm (Docker Compose or remote interpreter) use the same container.

**Secrets:** commit only templates (`nornir-docker/dev/example.cursor-dev.run.env`, per-image `*/example.<id>.build.env`; there are no root `.env*.example` stubs, so point people at the template). Never commit real `.env` files, tokens or machine-specific paths; [`nornir-docker/.gitignore`](../../../nornir-docker/.gitignore) ignores `.env`, `build.env`, `.build.*.env`, etc.

## Preconditions

- Docker with WSL2 backend on Windows (or Linux with NVIDIA Container Toolkit for GPU).
- **CUDA (for CuPy):** the image includes CuPy (`CUPY_PACKAGE` in `nornir-docker/dev/Dockerfile`, e.g. `cupy-cuda13x`; change it at build time to target another CUDA line). The host needs a compatible NVIDIA driver, and the NVIDIA Container Toolkit (or Docker Desktop GPU support) must expose devices and libraries. Without GPU passthrough the container runs but CuPy GPU paths have no hardware.
- Test data on the **WSL2 Linux filesystem** (not `D:\...` via DrvFS) for stable I/O; that path is the bind source for `/nornir-testdata`.

## Host configuration

1. Set user env `NORNIR_DOCKER_USER_ROOT=D:\Docker` (restart Cursor after changing).
2. Copy `nornir-docker/dev/example.cursor-dev.run.env` to `$NORNIR_DOCKER_USER_ROOT/Run/nornir-dev/.env` (the run source of truth).
3. In that file set `NORNIR_TESTDATA_HOST` to the Linux / WSL path (or Docker Desktop UNC) of `nornir-testdata`. Optionally set `NORNIR_REPRO_DATA_HOST` for the repro corpus.
4. Bridge it to `nornir-docker/.env` (hardlink or copy; junctions are directories-only, SymbolicLink needs Developer Mode). Required for Compose substitution of `${NORNIR_TESTDATA_HOST}`.
5. Ensure Docker can bind-mount those paths.

`compose.cursor-dev.yaml` also loads `nornir-docker/.env` as optional `env_file`, so every key (`NORNIR_SYNC_REMOTE`, `NORNIR_SUBMODULE_UPDATE`, `GITHUB_TOKEN`, `NORNIR_TILE_*`, ...) reaches the container without editing compose; the compose `environment:` block wins for keys it sets.

Mounts: `${NORNIR_TESTDATA_HOST}` → `/nornir-testdata` (= `TESTINPUTPATH`); when set, `${NORNIR_REPRO_DATA_HOST}` → `/data` (read-only); `${NORNIR_TESTOUTPUT_HOST:-D:/nornir-test-output}` → `/tmp/nornir-test-output` (writable).

## Environment variables (inside the container)

| Variable | Typical value | Role |
|----------|---------------|------|
| `TESTINPUTPATH` | `/nornir-testdata` | Read-only mount; must match `.cursor/environment.json` and test expectations |
| `TESTOUTPUTPATH` | `/tmp/nornir-test-output` | Writable scratch (artifacts, Hypothesis DB, plots). Host path `/mnt/d/nornir-test-output` when Compose runs from WSL (mounts above) |
| `INPUT_NORNIR_DATA` | `/data` (cursor-dev compose) | Optional repro corpus root; set to `D:\Data` (or your path) for pytest on Windows without Docker |
| `NORNIR_HEADLESS` | `1` (set in image) | Headless matplotlib / CI-style tests |
| `NORNIR_CLONE_URL` | `https://github.com/jamesra/nornir.git` | Clone source when `/workspace` is empty or for **cursor-dev-clone** refresh |
| `NORNIR_CLONE_BRANCH` | `dev` | Branch for clone / optional sync (case-sensitive) |
| `NORNIR_WORKSPACE_STRATEGY` | `mounted` (default) / `clone` (**cursor-dev-clone**) | See entry script below |
| `NORNIR_SYNC_REMOTE` | unset (`0`) | `1` on **cursor-dev**: sync to `NORNIR_CLONE_BRANCH` on each start (entry step 2) |
| `NORNIR_SUBMODULE_UPDATE` | unset (`0`) | `1` on **cursor-dev**: full submodule update on recreate (entry step 3). Always bump umbrella pointers after submodule commits (**Monorepo-submodule-changes** rule). |
| `NORNIR_WORKSPACE_HOST` | `..` | Host bind source for **cursor-dev**, relative to the `nornir-docker/` compose dir (parent = monorepo root) |

Compose sets `TESTINPUTPATH` / `TESTOUTPUTPATH` on **cursor-dev**; keep PyCharm run configs aligned.

## Build and run

- Build images: `nornir-docker/docker-build.ps1` from the monorepo root (see docker-build-run-phases).
- Run: `nornir-docker/run-cursor-dev.ps1` (optional `-Gpu`, `-Clone`), or raw Compose from the monorepo root:

```bash
docker compose -f nornir-docker/compose.cursor-dev.yaml build cursor-dev
docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm --gpus all cursor-dev
docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev-clone
```

Pass `--gpus all` on every run (or use compose `deploy` reservations) to see GPUs; without it the container starts but CuPy has no devices. For Dev Containers, make GPU the default with NVIDIA reservations on the **cursor-dev** service (Compose v2 + Docker Engine) or devcontainer `runArgs` / features ([VS Code GPU docs](https://code.visualstudio.com/remote/advancedcontainers/add-gpu-support)), so you do not rely on the CLI flag.

## Entry script behavior

`cursor-dev-entry.sh` runs on container start, before your shell.

**`cursor-dev` (`mounted`):**

1. `/workspace` empty: shallow `git clone` of `NORNIR_CLONE_URL` / `NORNIR_CLONE_BRANCH` (first-time empty bind only).
2. `/workspace` is a git repo: `git fetch`; only with `NORNIR_SYNC_REMOTE=1`, checkout the clone branch and `git pull --ff-only`.
3. `submodule-sync.sh`: by default init missing submodules only (preserves host checkout branches) and warn on `+` in `git submodule status` (submodule ahead of the umbrella pointer). `NORNIR_SUBMODULE_UPDATE=1` runs full `git submodule update --init --recursive` after pointer bumps.
4. `install-monorepo-editables.sh`: `pip install -e --no-deps` for `nornir-shared`, `nornir-pools`, `nornir-imageregistration`, `dm4`, `nornir-buildmanager` (`--no-deps` stops git sibling deps overwriting local editables).

**`cursor-dev-clone` (`clone`):** clone when empty; when `.git` exists, fetch/checkout/pull to `NORNIR_CLONE_BRANCH`. `NORNIR_CLONE_REFRESH=1` wipes `/workspace` before clone (parity with cursor worker). Then full submodule update and the same editable installs.

**Dev Containers:** `postAttachCommand` in `.devcontainer/*/devcontainer.json` reruns the editable install on attach (persistent containers skip entry). Reattach does **not** update submodules.

**Submodules:** a shallow clone may omit full submodule trees; use `NORNIR_CLONE_DEPTH=0` or `full`. Some submodule URLs are SSH (`git@github.com:...`); HTTPS-only environments need URL rewrites or SSH keys in the container.

After entry, run `pytest` from `/workspace`; the headless stack is preinstalled.

## `/workspace` and Cursor Dev Containers

| Mode | `/workspace` | Open with |
|------|--------------|-----------|
| **cursor-dev** (default) | Bind mount of the monorepo root (`${NORNIR_WORKSPACE_HOST:-..}`); host edits appear in the container | Open the monorepo root, **Reopen in Container** (`.devcontainer/devcontainer.json`) |
| **cursor-dev-clone** | Named volume `cursor-dev-work`: survives container removal, not a normal host folder | **Dev Containers: Reopen in Container** → **Nornir (cursor-dev clone)** (`.devcontainer/cursor-dev-clone/devcontainer.json`), or `run-cursor-dev.ps1 -Clone` |

## PyCharm

- Docker Compose interpreter: `nornir-docker/compose.cursor-dev.yaml`, service **cursor-dev** or **cursor-dev-clone**, Python `/opt/venv/bin/python`.
- Map the project dir to `/workspace`.
- Set `TESTINPUTPATH` / `TESTOUTPUTPATH` in run/debug templates if PyCharm does not inherit them from Compose.
- PyCharm ignores `.devcontainer/devcontainer.json`; it uses the same Compose and env files.

## Git commit and push

The image includes git. For push, mount the SSH agent or `~/.ssh` read-only, or use HTTPS with a credential helper / PAT (never bake secrets into the image). Set `user.name` / `user.email` in the container or repo-local config before committing.

## Quick verification checklist

- [ ] `$NORNIR_DOCKER_USER_ROOT/Run/nornir-dev/.env` is the run source of truth; `nornir-docker/.env` is a hardlink/copy bridge with `NORNIR_TESTDATA_HOST` set
- [ ] Optional: `NORNIR_REPRO_DATA_HOST` set for a real `/data` repro mount (otherwise placeholder empty `/data`)
- [ ] `docker compose ... run` includes `--gpus all` (or compose-level GPU) when GPU access is required
- [ ] In container: `echo $TESTINPUTPATH` → `/nornir-testdata`, `echo $TESTOUTPUTPATH` → under `/tmp`, `echo $INPUT_NORNIR_DATA` → `/data`
- [ ] `/workspace` contains the monorepo; `pip list` shows editable installs for Nornir packages
- [ ] `git status` works; remote push tested with your chosen auth method
- [ ] `pytest` runs from `/workspace` for the packages you care about
- [ ] With GPU: `import cupy` works and `cupy.arange(3)` runs without CUDA runtime errors

## Persistent container changes

A change made in the running container is lost on **Rebuild Container**; put it in the image or Compose.

| Change | Put it in |
|--------|-----------|
| Tools, CLIs, apt/pip packages (for example Claude Code) | `nornir-docker/dev/Dockerfile`; rebuild `nornir:dev-cursor-base` |
| Mounts, env vars, named volumes for state (logins, config) | `nornir-docker/compose.cursor-dev.yaml` (both services) and `dev/example.cursor-dev.run.env` |
| Editor extensions and settings | `.devcontainer/devcontainer.json` (and `cursor-dev-clone/devcontainer.json`) |

Do not install tools from the bind-mounted entry scripts (`cursor-dev-entry.sh`, `install-monorepo-editables.sh`); they run on every start and are for workspace prep. Do not run `docker compose down -v` casually: it deletes the `claude-config` and `cursor-dev-work` volumes. Interpreter in every image: `/opt/venv/bin/python`.

## Troubleshooting (by error message)

First check state: `docker ps -a --filter name=cursor-dev`, then `docker logs <name>`. `cursor-dev-entry.sh` runs with `set -euo pipefail`, so a failed step stops the container.

| Message / symptom | Verified cause and fix |
|-------------------|------------------------|
| **Failed to install Cursor server** (every rebuild, after reboot) | Container `Exited`: entry script failed; read `docker logs` (`mount-network-shares: FAILED` = CIFS row below). Container running: **unknown, investigate**; save the Dev Containers log and the container's network state, and record the cause here. |
| Compose error: `.../Run/nornir-dev/compose.net-mounts.override.yaml` not found | `.devcontainer/devcontainer.json` requires `${localEnv:NORNIR_DOCKER_USER_ROOT}/Run/nornir-dev/compose.net-mounts.override.yaml` (legacy location; `run-cursor-dev.ps1` prefers `Run/nornir-net-mounts/`). Set the user env var, restart Cursor, copy `dev/example.compose.net-mounts.override.yaml` there. |
| `/nornir-testdata` empty or missing, `TESTINPUTPATH` tests fail | `nornir-docker/.env` missing or a stale copy of `Run/nornir-dev/.env`, so `NORNIR_TESTDATA_HOST` misses Compose. Recreate the bridge; check the bind source with `docker compose -f nornir-docker/compose.cursor-dev.yaml config`; then **Rebuild Container** (substitution happens at create, not reattach). The path must exist where Docker resolves it (WSL path or `\\wsl$` UNC). |
| CIFS / `/storage4` gone after host reboot | Only the entry script mounts, at start; `CAP_SYS_ADMIN` is then dropped, so shell remounts fail by design. `wsl grep cifs /proc/filesystems`; if empty, `wsl -u root modprobe cifs` and restart the container. Persist with `dev/example.modules-load.net-shares.conf` (needs `systemd=true`) or a `[boot] command` in `/etc/wsl.conf` (`docs/deployment/nornir_build_appliance.rst`). Still lost after that: **unknown, investigate** (maybe the distro holding the config boots after Docker starts the container). |
| `launch.json` configurations not shown | `.vscode/launch.json` is tracked: `/workspace/.vscode/launch.json` (clone mode: only if committed on `NORNIR_CLONE_BRANCH`). Entries are `"type": "debugpy"`: `ms-python.debugpy` must be installed **in the container** (listed in `devcontainer.json`; check Extensions), and the folder opened at `/workspace`. Both hold: **unknown, investigate.** Its `PYTHONPATH` uses `;` and `D:/` (Windows-only); the container relies on editable installs. |
| Skills or rules not found inside the container | Project skills: `/workspace/.cursor/skills/` (read per `CLAUDE.md` / `AGENTS.md`). Claude Code discovers only `/workspace/.claude/skills/` (currently just `nornir-improve-loop`). Host user-level skills and rules (`%USERPROFILE%\.claude\skills`, `~/.cursor/rules`) are absent: `/root/.claude` is the `claude-config` volume. A Compose bind mount would fix it persistently. **Unknown, investigate**: confirm the design with the user first. |
| `claude: command not found` after rebuild | Image predates `dev/Dockerfile` installing Claude Code (`/root/.local/bin/claude`; login kept on the `claude-config` volume). Rebuild the image (`docker compose -f nornir-docker/compose.cursor-dev.yaml build cursor-dev` or `docker-build.ps1 -Images dev-cursor-base`), then **Rebuild Container**. |
| `py-spy` / `strace`: `Permission denied` / `Failed to copy Py_Version` / `ptrace EPERM` | Container missing `CAP_SYS_PTRACE` or still on Docker's default seccomp. Base compose grants `SYS_PTRACE` + `seccomp:unconfined`, but the net-mounts override **replaces** those lists — it must re-include both (see `example.compose.net-mounts.override.yaml`). **Rebuild Container** (create-time, not reattach). Detach debugpy before attaching py-spy to the same process. Image includes `strace`; `pip install py-spy` into `/opt/venv` if needed. |
| `NORNIR_TESTDATA_HOST` / `libnvrtc` / `\\wsl.localhost` socket errors | See "Programmer shell" in `docs/deployment/troubleshooting.rst`. |
