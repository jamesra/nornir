---
name: docker-build-run-phases
description: >-
  Separates Docker workflows into build and run phases with dedicated scripts,
  env-file discovery (.env and image-named env files), prompting for missing
  required variables, base vs final image layout, and Nornir co-located
  example.<id>.build.env / example.<id>.run.env templates plus NORNIR_DOCKER_USER_ROOT
  for run-phase and hand-maintained files (docker-build.ps1 merges only CWD build.env / .build.<id>.env).
  Use when authoring or reviewing Docker build/run scripts, Compose wrappers, CI image
  steps, or env layering for the nornir-docker submodule.
---

# Docker build and run phases

## Which Docker skill?

| Skill | Use when |
|-------|----------|
| **docker-build-run-phases** (this) | Build vs run scripts, `example.*.env` templates, env layering (only) |
| **deploy-connectomes** | Deploying or debugging the connectomes.pitt.edu hosts with `stack.ps1` |
| **docker-machine-layout** | Where machine-local files live (`Run` / `Builds` / `Data` / `Certs` / `Work` / `Logs` under `D:\Docker` / `/srv/docker`) |
| **nornir-docker-images-ci** | Image matrix, `docker-build.ps1` order, OCI/BOM, Dockerfile/CI review checklist |
| **nornir-docker-devcontainer** | Day-to-day cursor-dev / Dev Containers setup, test data mounts |

## Model

Build and run are **two phases**, each with **its own script** (e.g. `build.sh` / `build.ps1` and `run.sh` / `run.ps1`, or language-specific equivalents). Do not fold unrelated concerns into one script unless the user explicitly asks.

| Phase | Responsibility | Typical inputs |
|-------|----------------|----------------|
| **Build** | Produce the image (tags, build args, cache). No long-lived runtime secrets unless the Dockerfile truly needs them at build time. | Build args, registry auth for pull-only base images, optional CWD `build.env` / `.build.<id>.env` for `docker-build.ps1` |
| **Run** | Start/stop the container, mounts, ports, env, health checks, compose up. | `.env`, `.env.*`, secrets, volume mappings |

## Where Nornir Docker source lives

Dockerfiles, Compose files, and checked-in env examples belong in **`nornir-docker/`** (the `nornir-docker` git submodule; standalone repo `nornir/nornir-docker`). Do **not** assume a monorepo-root `docker/` directory unless the project adds one explicitly. There is no `build/` or `run/` tree under `nornir-docker/`.

### Committed env templates

Committed templates **always end in `.env`**:

- **`example.<id>.build.env`** — documents the `--build-arg`s each image expects. No script reads it; copy values into your own `docker build` flags or into CWD files for `docker-build.ps1`.
- **`example.<id>.run.env`** — runtime variables for Compose or copy targets (e.g. `.env`, `.env.cursor-worker`).

`<id>` is the **normalized image tag** (`:` → `-`, e.g. `nornir-dev`), or a **Compose stack / service name** for a named-stack run template (e.g. `cursor-dev`, or a `stack.ps1` stack key such as `nornir-build`). There is no shared build template; shared build overrides go in a machine-local `build.env` in the invocation directory. `stack.ps1` run templates live in `nornir-docker/deploy/examples/` (`example.<stack>.run.env`, `example.host.env`).

| Role | Example path under `nornir-docker/` |
|------|-------------------------------------|
| `nornir:dev`, `nornir:dev-cursor-base` (from `dev/Dockerfile`) | `dev/example.nornir-dev.build.env`, `dev/example.nornir-dev-cursor-base.build.env` |
| cursor-dev run (Compose service) | `dev/example.cursor-dev.run.env` |
| `nornir:prod`, `nornir:cupy` (`prod/Dockerfile`) | `prod/example.nornir-prod.build.env`, `prod/example.nornir-cupy.build.env` |
| `nornir:cursor-worker` (`Dockerfile.cursor-worker`) | `example.nornir-cursor-worker.build.env`, `example.nornir-cursor-worker.run.env` |

**`run-cursor-dev.ps1`** is the run-phase script for the cursor-dev stack (optional **`-Clone`** for service `cursor-dev-clone`).

## Base images vs final images

- **Base** — mainly a `FROM` dependency (or intermediate tag) for another Dockerfile, not what operators run. No run-template "stack" name unless documented as a leaf, and no run script beyond the unified pipeline (e.g. one `docker-build.ps1` that builds bases as prerequisites).
- **Final** — the **leaf** image for a line: what Compose runs, what you document mounts/secrets for, and the owner of `example.<stack>.run.env` where applicable.

Args that exist **only** for a **downstream** Dockerfile (e.g. `BASE_IMAGE`) belong on the **final** image's documented template, not on the base.

Example: `nornir:dev-cursor-base` is the base for `nornir:cursor-worker`. Run env and run helpers target the **cursor-dev** / **cursor-worker** stacks; there is no `example.nornir-dev-cursor-base.run.env` unless you add one for documentation.

## User-local configuration root (not in git)

Real `.env` files, secrets, and host-specific bind paths **must not** be committed. Root: **`NORNIR_DOCKER_USER_ROOT`** (default **`D:\Docker`**; see **docker-machine-layout**).

| Phase | Machine-local path | Notes |
|-------|--------------------|--------|
| **Build** | `$NORNIR_DOCKER_USER_ROOT/Builds/nornir/` | `build.env`, `.build.<id>.env`; invoke `docker-build.ps1` from here |
| **Run (cursor-dev)** | `$NORNIR_DOCKER_USER_ROOT/Run/nornir-dev/.env` | Source of truth for host paths / MQTT / etc. |
| **Compose bridge** | `nornir-docker/.env` | Hardlink or copy of the Run file — Compose/Dev Containers only auto-load this path |
| **Run (worker)** | `$NORNIR_DOCKER_USER_ROOT/Run/nornir-cursor-worker/nornir-cursor-worker.run.env` | See `start-cursor-worker.ps1` |
| **Net mounts** | `$NORNIR_DOCKER_USER_ROOT/Run/nornir-net-mounts/` | Prefer over legacy `Run/nornir-dev/` for shared CIFS |
| **Run (`stack.ps1` stacks)** | `$NORNIR_DOCKER_USER_ROOT/Run/<stack>/<stack>.run.env` + `Run/<stack>/secrets/` | Merged after `Run/_host/host.env` and host secrets (later wins); see `docs/deployment/host_layout.rst` |

- Do **not** use `$NORNIR_DOCKER_USER_ROOT/dev/cursor-dev.run.env` (obsolete); use `Run/nornir-dev/`.
- CI supplies build-args via **CWD `build.env` / `.build.<id>.env`**, **`docker build --build-arg`**, or the CI provider's secret/env injection.

## Environment file discovery

**Build (`docker-build.ps1`)** merges **only** two files from the **directory you invoked it from** (captured before it `cd`s to the monorepo root), later overriding earlier for overlapping keys:

1. `build.env` (shared across all images in that run)
2. `.build.<id>.env` per image (`<id>` = normalized tag, `:` → `-`)

Script `-ExtraArgs` override those, then fixed OCI/BOM args on the `docker build` command line. Each path is logged as **found and merged** or **not found**. It does **not** read `nornir-docker/example.*.build.env`, `$NORNIR_DOCKER_USER_ROOT`, or the Run tree.

**Run (cursor-dev):** copy `dev/example.cursor-dev.run.env` to `$NORNIR_DOCKER_USER_ROOT/Run/nornir-dev/.env`, then **bridge** it to `nornir-docker/.env` (hardlink or copy; junctions do not work for files) so Compose substitutes `${NORNIR_TESTDATA_HOST}`.

**Run templates:** unless the user says otherwise, merge so **later layers override earlier** (last source listed wins per key).

**Required variables:** list them per phase in script comments or `--help`. If one is still unset or empty after loading, **prompt interactively** once with a short description of its purpose (or fail with a clear message in non-interactive contexts); never silently continue. Optional variables may use defaults without prompting unless the user asks for strict validation.

## Agent checklist when adding or changing Docker automation

- [ ] **Two scripts** (or clearly separated subcommands): one for **build**, one for **run**
- [ ] **Classify** images as **base** vs **final**; only **final** stacks typically get **`example.<stack>.run.env`** and dedicated run scripts
- [ ] **Put** build-args that exist for a downstream image on the **final** image's co-located build template, not a separate base "stack"
- [ ] **Document** required env vars per phase; **prompt** or **fail fast** when missing
- [ ] **Build (`docker-build.ps1`):** optional CWD `build.env` + `.build.<id>.env`; script logs each file as merged or not found
- [ ] **Run / Compose:** machine-local under `Run/<key>/`; cursor-dev bridged to `nornir-docker/.env`
- [ ] **Name** new committed templates `example.<id>.build.env` or `example.<id>.run.env` and place them next to the relevant Dockerfile or compose docs
- [ ] **Do not** commit secrets; reference secret **file paths** in run configs where possible
