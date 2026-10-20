---
name: docker-machine-layout
description: Standardizes the machine-local Docker host layout (D:\Docker on Windows, /srv/docker on Ubuntu) for run env, secrets, data, certificates, work folders and logs, while keeping templates in the project repository. Use when creating or reviewing Docker image workflows, env placement, layout initialization, or host-mounted paths.
---

# Docker machine layout

## Which Docker skill?

| Skill | Use when |
|-------|----------|
| **deploy-connectomes** | Deploying or debugging the connectomes.pitt.edu hosts with `stack.ps1` |
| **docker-build-run-phases** | Build vs run scripts, `example.*.env` templates, env layering |
| **docker-machine-layout** (this) | Where machine-local files live under the layout root |
| **nornir-docker-images-ci** | Image matrix, OCI/BOM, Dockerfile/CI review |
| **nornir-docker-devcontainer** | Day-to-day cursor-dev / Dev Containers setup |

Human docs: `docs/deployment/host_layout.rst` (https://nornir.github.io/deployment/host_layout.html).

## Canonical rule text

Any project that has docker images keeps the instances, variables, configurations, secrets, data
and certificates for my machines under one layout root: `D:\Docker` on Windows, `/srv/docker` on
Ubuntu (`NORNIR_DOCKER_USER_ROOT`). The configuration templates, docker files, and docker compose
files for the same go in the project repository.

Every stack gets the same shape, keyed by its kebab-case stack name (= compose project name):

- `Run\<stack>\<stack>.run.env` for variables needed when the container starts, and
  `Run\<stack>\secrets\` for its secrets. Machine-wide settings are in `Run\_host\host.env`
  (+ `Run\_host\secrets\secrets.env`, `Run\_host\targets.psd1`).
- `Builds\<stack>\` (Builds plural, not Build) for build-time variables and forwarding launchers.
- `Data\<stack>\` for data a service must keep across rebuilds (models, keys, databases).
- `Certs\<cert-name>\` for the TLS certificate every service shares (written by the renewer or
  `stack.ps1 certs manual`).
- `Work\` for disposable per-session folders (replaces `mounted-configs\` for `nornir-build`).
- `Logs\<stack>\` for persistent logs.

## How to apply this

- **Machine-local runtime state** (real env files, secrets, data, certs, host-specific config): under the layout root.
- **Versioned templates** (`example.*`, sample envs, docs): in the repository next to the Docker assets
  (`nornir-docker/deploy/examples/` for deploy templates).
- **Never commit** real secrets, `Run/` files, or machine-specific resolved env files.
- Create the tree with `nornir-docker/deploy/Initialize-DockerHost.ps1 -Role compute|web|iis|dev`
  (copies templates only when missing; writes forwarding launchers, never copies of repo scripts).
- Run stacks with `stack.ps1` (it merges `host.env` → host secrets → `<stack>.run.env` → stack secrets
  and exports `STACK_*_DIR`, `DOCKER_CERTS_DIR`, `DOCKER_WORK_DIR` to compose).
- Override the root with `NORNIR_DOCKER_USER_ROOT` (or `-Root`) and keep the same directory model.
- Old layouts migrate with `deploy/Move-DockerHostLayout.ps1 -WhatIf` (copies, never deletes).

## cursor-dev Compose bridge

Run env for cursor-dev belongs under **`Run\nornir-dev\.env`**, not under `Builds\`.

Docker Compose and Cursor Dev Containers only auto-load **`nornir-docker/.env`** (Compose project
directory). Bridge with a **hardlink** or **copy** from the Run file to `nornir-docker/.env`:

- Windows **junctions are directories-only** — do not use them for `.env` files.
- **SymbolicLink** needs Developer Mode or an elevated shell.
- Prefer: `New-Item -ItemType HardLink -Path '...\nornir-docker\.env' -Target 'D:\Docker\Run\nornir-dev\.env'` (same volume) or `Copy-Item`.

`compose.cursor-dev.yaml` also passes that file as `env_file`, so all of its keys reach the container.

Shared CIFS layout and the cursor-dev net-mount override: `Run\nornir-net-mounts\` (legacy
`Run\nornir-dev\` still works). See `docs/deployment/nornir_build_appliance.rst`.

## Exception: Cursor worker

`nornir-cursor-worker` still keeps per-run workspaces under
`mounted-configs\nornir-cursor-worker\` (created by
`windows-docker-layout/Initialize-NornirCursorWorkerLayout.ps1`). Do not move them without
updating `start-cursor-worker.ps1` and `Cleanup-CursorWorkerClones.ps1` together.

## Implementation checklist

- [ ] Defaults are `D:\Docker` (Windows) and `/srv/docker` (Linux) via `NORNIR_DOCKER_USER_ROOT`
- [ ] Start-time variables in `Run\<stack>\<stack>.run.env`; secrets in `Run\<stack>\secrets\`
- [ ] Persistent data in `Data\<stack>\`; certificates in `Certs\<name>\`; scratch in `Work\`; logs in `Logs\<stack>\`
- [ ] Compose files use the contract variables, not hard-coded host paths
- [ ] Build-time variables resolve from `Builds\<stack>\` (invocation directory for `docker-build.ps1`)
- [ ] cursor-dev: Run file bridged to `nornir-docker/.env`
- [ ] Repo contains only templates and examples
- [ ] Linux: secrets dirs 700, secret files 600

## Related skills

- **deploy-connectomes** — `stack.ps1` deploy/debug procedure
- **docker-build-run-phases** — build vs run env files and `docker-build.ps1` invocation directory
- **nornir-docker-images-ci** — image tags, `docker-build.ps1` order, OCI/BOM labels
- **nornir-docker-devcontainer** — cursor-dev Compose and Dev Containers
