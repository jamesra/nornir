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

## Model

Treat **image build** and **container run** as **two distinct phases**, each with its **own script** (e.g. `build.sh` / `build.ps1` and `run.sh` / `run.ps1`, or language-specific equivalents). Do not fold unrelated concerns into one script unless the user explicitly asks.

| Phase | Responsibility | Typical inputs |
|-------|----------------|----------------|
| **Build** | Produce the image (tags, build args, cache). No long-lived runtime secrets required unless the Dockerfile truly needs them at build time. | Build args, registry auth for pull-only base images, optional CWD `build.env` / `.build.<id>.env` for `docker-build.ps1` |
| **Run** | Start/stop the container, mounts, ports, env, health checks, compose up. | `.env`, `.env.*`, secrets, volume mappings |

## Nornir: where Docker source lives

All **Dockerfile, Compose, and checked-in env examples** for Nornir belong in the **`nornir-docker/`** tree. In the monorepo that path is the **`nornir-docker` git submodule** (standalone repo `nornir/nornir-docker` when cloned on its own). Do **not** assume a separate monorepo-root `docker/` directory for Nornir unless the project adds one explicitly.

### Co-located env templates (committed)

Committed templates **always end in `.env`**. Names:

- **`example.<id>.build.env`** — committed **templates** for `--build-arg` defaults (copy values into your own `docker build` flags or into CWD files for `docker-build.ps1`; the script does not read these files)
- **`example.<id>.run.env`** — runtime variable templates for Compose or copy targets (e.g. `.env`, `.env.cursor-worker`)

`<id>` is the **normalized image tag** with `:` → `-` (e.g. `nornir-dev`), or a **Compose stack / service name** when the run template is for a named stack (e.g. `cursor-dev`). Shared build defaults: **`example._shared.build.env`** at the submodule root.

| Role | Example path under `nornir-docker/` |
|------|-------------------------------------|
| Shared build defaults | `example._shared.build.env` |
| `nornir:dev`, `nornir:dev-cursor-base` (from `dev/Dockerfile`) | `dev/example.nornir-dev.build.env`, `dev/example.nornir-dev-cursor-base.build.env` |
| cursor-dev run (Compose service) | `dev/example.cursor-dev.run.env` |
| `nornir:prod`, `nornir:cupy` (`prod/Dockerfile`) | `prod/example.nornir-prod.build.env`, `prod/example.nornir-cupy.build.env` |
| `nornir:cursor-worker` (`Dockerfile.cursor-worker`) | `example.nornir-cursor-worker.build.env`, `example.nornir-cursor-worker.run.env` |

There is **no** separate `build/` or `run/` directory tree under `nornir-docker/`. **`docker-build.ps1`** merges **only** two files from the **directory where you invoked the script** (captured before `cd` to the monorepo root): **`build.env`** (shared), then **`.build.<id>.env`** per image (`<id>` = tag with `:` → `-`). It logs each path as **found and merged** or **not found**. It does **not** read `nornir-docker/example.*.build.env` or `$NORNIR_DOCKER_USER_ROOT` for build args. **`run-cursor-dev.ps1`** is the dedicated run-phase script for the cursor-dev stack (optional **`-Clone`** for service `cursor-dev-clone`).

## Base images vs final images

- **Base image** — Used mainly as a **`FROM`** dependency (or intermediate tag) for another Dockerfile, **not** as the primary stack operators run. Bases do **not** get their own dedicated run-template “stack” name unless documented as a leaf; they do not need separate run **scripts** beyond the unified pipeline (e.g. one `docker-build.ps1` that builds bases as prerequisites).
- **Final image** — The **leaf** image for a line: what Compose runs, what you document for mounts/secrets, and what owns **`example.<stack>.run.env`** where applicable.

**Build-args:** Use per-tag **`example.<norm>.build.env`** in the repo as **documentation** for which args each image expects; for **`docker-build.ps1`**, put overrides in **`.build.<norm>.env`** (or shared **`build.env`**) in the invocation directory, or pass **`docker build --build-arg`** yourself. Arguments that exist **only** for a **downstream** Dockerfile (e.g. `BASE_IMAGE`) belong on the **final** image’s documented template, not as a parallel “stack” story on the base.

**Example:** `nornir:dev-cursor-base` is a base for `nornir:cursor-worker`. Operator-facing run env and run helpers target **cursor-dev** / **cursor-worker** stacks, not a separate `example.nornir-dev-cursor-base.run.env` unless you explicitly add one for documentation.

## User-local configuration root (not in git)

Per-developer machine settings—real `.env` files, secrets, host-specific bind paths—**must not** be committed. For **run** templates and Compose, they often live under a **user-local root** (`NORNIR_DOCKER_USER_ROOT`) with filenames that **mirror** the co-located layout but **drop the `example.` prefix** (e.g. `nornir-cursor-worker.run.env`). **`docker-build.ps1` does not merge that tree** for image build args; use invocation-directory **`build.env`** / **`.build.<id>.env`** instead.

- **Convention:** `NORNIR_DOCKER_USER_ROOT` points to that directory (set in the user shell or system environment). Scripts should document this variable and fail clearly if a required path is missing when not using defaults.
- Developers may **copy** from `example.*` in the submodule and rename, or maintain parallel non-example files under `$NORNIR_DOCKER_USER_ROOT`.
- CI should supply build-args via **CWD `build.env` / `.build.<id>.env`**, **`docker build --build-arg`**, or the CI provider’s secret/env injection—**no** interactive user directory. **`docker-build.ps1`** does not read committed `example.*.build.env` automatically.

## Environment file discovery

**Build (`docker-build.ps1`):** merge **only** from the **invocation directory**, in order (later overrides earlier for overlapping keys; then script `-ExtraArgs`; then fixed OCI/BOM args on the `docker build` command line):

1. `build.env` (shared across all images in that script run)
2. `.build.<id>.env` per image (`<id>` = normalized tag, `:` → `-`)

Committed **`example.*.build.env`** under `nornir-docker/` are **not** read by this script—copy from them when authoring `build.env` / `.build.<id>.env` or when calling `docker build` manually.

**Run:** copy from `example.<id>.run.env` to the runtime filename the stack expects (e.g. `nornir-docker/.env` for cursor-dev, `nornir-docker/.env.cursor-worker` for the worker), or point Compose at an env file path you control. Optional **`$NORNIR_DOCKER_USER_ROOT`** mirrors apply to **run** / local Compose workflows as documented per script—not to **`docker-build.ps1`** build-arg merge.

Unless the user specifies otherwise, for **run** templates load and **merge** so **later layers override earlier** (same key wins for the last source listed).

After loading, if **required** variables for that phase are still unset or empty, **prompt interactively** (or fail with a clear message in non-interactive contexts) rather than silently continuing.

**Prompting:** Enumerate which variables are **required** for the phase (document them in script comments or `--help`). For each missing required variable, ask once with a short description of its purpose. Optional variables may use defaults without prompting unless the user asks for strict validation.

## Agent checklist when adding or changing Docker automation

- [ ] **Two scripts** (or clearly separated subcommands): one for **build**, one for **run**
- [ ] **Classify** images as **base** vs **final**; only **final** stacks typically get **`example.<stack>.run.env`** and dedicated run scripts
- [ ] **Put** build-args that exist for a downstream image on the **final** image’s co-located build template, not a separate base “stack”
- [ ] **Document** required env vars per phase; **prompt** or **fail fast** when missing
- [ ] **Build (`docker-build.ps1`):** optional CWD `build.env` + `.build.<id>.env`; script logs each file as merged or not found
- [ ] **Run / Compose:** merge or copy from `example.*.run.env` and user-local `$NORNIR_DOCKER_USER_ROOT/...` as documented for that stack
- [ ] **Name** new committed templates `example.<id>.build.env` or `example.<id>.run.env` and place them next to the relevant Dockerfile or compose docs
- [ ] **Do not** commit secrets; reference secret **file paths** in run configs where possible

## Relationship to other project skills

- **nornir-docker-devcontainer** — cursor-dev / Dev Containers / test data mounts
- **nornir-docker-images-ci** — image matrix, `docker-build.ps1` order, OCI/BOM, Dockerfile review checklist
- **docker-machine-layout** — `D:\Docker\Builds` / `Run` / `mounted-configs` on Windows

This skill covers **phased scripts and env layering** only.
