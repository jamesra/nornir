# Nornir agent guidelines

Project-wide index for AI coding agents in the Nornir umbrella repository.

**Canonical sources**

| Kind | Location | Role |
|------|----------|------|
| **Rules** | [`.cursor/rules/*.mdc`](.cursor/rules/) | Policy / guardrails (Cursor loads these via `alwaysApply` or `globs`) |
| **Skills** | [`.cursor/skills/*/SKILL.md`](.cursor/skills/) | Procedures (read when the skill description matches the task) |

Edit rules and skills in those trees. Do **not** maintain a parallel full copy of rule bodies here.

Default virtual environment: `D:\src\git\nornir\venv\pyre314` (see **Virtual-Env** rule).

---

## Rules index

### Always applied

| Rule file | Summary |
|-----------|---------|
| [Virtual-Env.mdc](.cursor/rules/Virtual-Env.mdc) | Default venv path |
| [Design-choice-confirmation.mdc](.cursor/rules/Design-choice-confirmation.mdc) | Pause for material design risks; non-negotiable `must not` / `do not` |
| [Unified-Logging-Convention.mdc](.cursor/rules/Unified-Logging-Convention.mdc) | `SetupLogging`, `NORNIR_LOG_ROOT`, multiprocess queue logging |

### Glob-scoped

| Rule file | Scope (see frontmatter) | Summary |
|-----------|-------------------------|---------|
| [python-standards.mdc](.cursor/rules/python-standards.mdc) | `**/*.py` | Imports, typing, class members, docstrings |
| [Numpy-CuPy-compatibility.mdc](.cursor/rules/Numpy-CuPy-compatibility.mdc) | `nornir-imageregistration` | `xp` / CuPyX / host↔device boundaries |
| [Pyre-host-array-boundary.mdc](.cursor/rules/Pyre-host-array-boundary.mdc) | `nornir-pyre` | `xp` math; `EnsureNumpyArray` only at Qt/GL/SciPy/floats |
| [Streaming-and-memory-bounded-processing.mdc](.cursor/rules/Streaming-and-memory-bounded-processing.mdc) | buildmanager, imageregistration, pools, shared | Stream work; bound peak memory |
| [Documentation-and-monodoc.mdc](.cursor/rules/Documentation-and-monodoc.mdc) | `docs/**`, READMEs | Monodoc under `docs/`; short package READMEs |
| [powershell-scripts.mdc](.cursor/rules/powershell-scripts.mdc) | `**/*.ps1` | Comment-based help on generated scripts |
| [nornir-docker-conventions.mdc](.cursor/rules/nornir-docker-conventions.mdc) | `nornir-docker/**`, compose, Dockerfiles, `.devcontainer` | Submodule assets, secrets, Compose bridge |
| [Serial-batched-primitives.mdc](.cursor/rules/Serial-batched-primitives.mdc) | phase/batched registration paths | Verification matrix; ≥100-tile perf sign-off |
| [Pyre-STOS-rigid-transform-UI.mdc](.cursor/rules/Pyre-STOS-rigid-transform-UI.mdc) | pyre rigid transform UI paths | Read paired skill before panel/sync changes |

---

## Skills index

Full catalog: [`.cursor/skills/README.md`](.cursor/skills/README.md).

| Skill | When to use |
|-------|-------------|
| [archive-built-plans](.cursor/skills/archive-built-plans/SKILL.md) | Archive completed Cursor plans |
| [cupy-missing-api-bugfix](.cursor/skills/cupy-missing-api-bugfix/SKILL.md) | CuPy/NumPy API gaps — dual-backend first |
| [docker-build-run-phases](.cursor/skills/docker-build-run-phases/SKILL.md) | Build vs run scripts and env layering |
| [docker-machine-layout](.cursor/skills/docker-machine-layout/SKILL.md) | `D:\Docker\Builds` / `Run` / `mounted-configs` |
| [hypothesis-testing](.cursor/skills/hypothesis-testing/SKILL.md) | Property-based tests with Hypothesis |
| [nornir-docker-devcontainer](.cursor/skills/nornir-docker-devcontainer/SKILL.md) | cursor-dev / Dev Containers setup |
| [nornir-docker-images-ci](.cursor/skills/nornir-docker-images-ci/SKILL.md) | Image matrix, OCI/BOM, Docker CI |
| [nornir-documentation](.cursor/skills/nornir-documentation/SKILL.md) | Build/deploy Sphinx monodoc |
| [nornir-debug-profiling](.cursor/skills/nornir-debug-profiling/SKILL.md) | PhaseProfiler, slowness and queue profiling |
| [nornir-headless-unit-tests](.cursor/skills/nornir-headless-unit-tests/SKILL.md) | `NORNIR_HEADLESS`, plot artifact triage |
| [nornir-serial-batched-primitives](.cursor/skills/nornir-serial-batched-primitives/SKILL.md) | Serial/batched registration verification |
| [pyre-stos-rigid-transform-ui](.cursor/skills/pyre-stos-rigid-transform-ui/SKILL.md) | Pyre STOS rigid UI semantics |

---

## Deprecated

`.aiassistant/rules/` is **not** maintained. Use `.cursor/rules/` instead.
