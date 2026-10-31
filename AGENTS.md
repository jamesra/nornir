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
| [Monorepo-submodule-changes.mdc](.cursor/rules/Monorepo-submodule-changes.mdc) | Commit in submodule, bump umbrella pointer; mounted devcontainer preserves submodule branches on recreate |
| [Shared-checkout-safety.mdc](.cursor/rules/Shared-checkout-safety.mdc) | Checkout is shared with other sessions: never stash, stage by path, leave others' changes and `+` pointers alone |
| [Line-endings-and-encoding.mdc](.cursor/rules/Line-endings-and-encoding.mdc) | Preserve line endings; ASCII-only `.ps1` for PowerShell 5.1; Windows paths in inline Python |
| [Workspace-map.mdc](.cursor/rules/Workspace-map.mdc) | Sibling repos, data volumes, training data, scratch roots; live checkouts feed deployments |
| [Questions-and-proving-fixes.mdc](.cursor/rules/Questions-and-proving-fixes.mdc) | Answer questions without editing; evidence before "fixed"; stop circling after two failed attempts; remove debug instrumentation |

### Glob-scoped

| Rule file | Scope (see frontmatter) | Summary |
|-----------|-------------------------|---------|
| [python-standards.mdc](.cursor/rules/python-standards.mdc) | `**/*.py` | Imports, typing, class members, docstrings |
| [Numpy-CuPy-compatibility.mdc](.cursor/rules/Numpy-CuPy-compatibility.mdc) | `nornir-imageregistration` | `xp` / CuPyX / host↔device boundaries |
| [Pyre-host-array-boundary.mdc](.cursor/rules/Pyre-host-array-boundary.mdc) | `nornir-pyre` | `xp` math; `EnsureNumpyArray` only at Qt/GL/SciPy/floats |
| [Streaming-and-memory-bounded-processing.mdc](.cursor/rules/Streaming-and-memory-bounded-processing.mdc) | buildmanager, imageregistration, pools, shared | Stream work; bound peak memory |
| [Nornir-performance-envelope.mdc](.cursor/rules/Nornir-performance-envelope.mdc) | `nornir-imageregistration` | NAS latency, `/tmp` SSD cache, ~2-3 GB RAM/core, GPU class |
| [Performance-evidence.mdc](.cursor/rules/Performance-evidence.mdc) | benchmarks, profiling scripts | Measured before/after on real data; rejected-candidate lessons; pyperf `--copy-env` on Windows |
| [Pyre-coordinate-spaces.mdc](.cursor/rules/Pyre-coordinate-spaces.mdc) | `nornir-pyre` | Source vs target space, Fixed/Warped naming trap, (Y, X) order, ROI mapping |
| [Documentation-and-monodoc.mdc](.cursor/rules/Documentation-and-monodoc.mdc) | `docs/**`, READMEs | Monodoc under `docs/`; short package READMEs |
| [CI-hygiene.mdc](.cursor/rules/CI-hygiene.mdc) | workflows, tests | Recurring Actions footguns after check-in |
| [powershell-scripts.mdc](.cursor/rules/powershell-scripts.mdc) | `**/*.ps1` | Comment-based help on generated scripts |
| [nornir-docker-conventions.mdc](.cursor/rules/nornir-docker-conventions.mdc) | `nornir-docker/**`, compose, Dockerfiles, `.devcontainer` | Submodule assets, secrets, Compose bridge |
| [Serial-batched-primitives.mdc](.cursor/rules/Serial-batched-primitives.mdc) | phase/batched registration paths | Verification matrix; ≥100-tile perf sign-off |
| [Refine-grid-trust-questions.mdc](.cursor/rules/Refine-grid-trust-questions.mdc) | refine-grid (`local_distortion_correction`, `refine_shared`) | Only trusted cells shape the field; name the trust question before retuning gates |
| [Pyre-STOS-rigid-transform-UI.mdc](.cursor/rules/Pyre-STOS-rigid-transform-UI.mdc) | pyre rigid transform UI paths | Read paired skill before panel/sync changes |
| [Review-driven-bugfixing.mdc](.cursor/rules/Review-driven-bugfixing.mdc) | bug-review master list, `issue-handoff` | Findings are hypotheses; reproduce or measure before fixing |
| [Stable-path-output-parity.mdc](.cursor/rules/Stable-path-output-parity.mdc) | importers, image I/O, coordinates, transforms | Compare outputs before/after on long-stable paths |
| [Training-set-naming.mdc](.cursor/rules/Training-set-naming.mdc) | `segmentationtraining` (ExportTrainingData) | Sets are `v#.#` (same creation rules within a set number); every set gets a `training_set.json` sidecar; sets and models have separate version numbers |

---

## Skills index

Full catalog: [`.cursor/skills/README.md`](.cursor/skills/README.md).

| Skill | When to use |
|-------|-------------|
| [nornir-commit-push](.cursor/skills/nornir-commit-push/SKILL.md) | "Commit (and push) everything incl. submodules", pointer refresh, release, lost-work audit; push order |
| [nornir-verify-change](.cursor/skills/nornir-verify-change/SKILL.md) | Before claiming done: test commands, known flaky/baseline failures, lint/type delta on touched files |
| [segmentation-training-export](.cursor/skills/segmentation-training-export/SKILL.md) | `ExportTrainingData` / SAM2 crop export: flags, re-export vs update, OData paging, trainer handoff |
| [docker-publish-ghcr](.cursor/skills/docker-publish-ghcr/SKILL.md) | Ship new code to the build hosts (push, clean-clone build, publish, verify, notify); build, push, verify and pull Nornir images on GHCR; "users get the old image" |
| [nornir-realworld-refine-benchmark](.cursor/skills/nornir-realworld-refine-benchmark/SKILL.md) | Real-data refine-grid A/B: fixture semantics, baseline runner, acceptance criteria |
| [archive-built-plans](.cursor/skills/archive-built-plans/SKILL.md) | Archive completed Cursor plans |
| [cupy-missing-api-bugfix](.cursor/skills/cupy-missing-api-bugfix/SKILL.md) | CuPy/NumPy API gaps — dual-backend first |
| [deploy-connectomes](.cursor/skills/deploy-connectomes/SKILL.md) | Deploying or debugging connectomes.pitt.edu hosts: `stack.ps1 doctor` → `-Sync` → up/rebuild → status; certs |
| [deploy-compute-host](.cursor/skills/deploy-compute-host/SKILL.md) | Bringing up a NEW Ubuntu GPU compute host from a bare OS (nornir-build, segmentation, viking-certs); first-deploy failures |
| [docker-build-run-phases](.cursor/skills/docker-build-run-phases/SKILL.md) | Build vs run scripts and env layering |
| [docker-machine-layout](.cursor/skills/docker-machine-layout/SKILL.md) | `D:\Docker` / `/srv/docker`: `Run` / `Builds` / `Data` / `Certs` / `Work` / `Logs` |
| [hypothesis-testing](.cursor/skills/hypothesis-testing/SKILL.md) | Property-based tests with Hypothesis |
| [nornir-docker-devcontainer](.cursor/skills/nornir-docker-devcontainer/SKILL.md) | cursor-dev / Dev Containers setup |
| [nornir-docker-images-ci](.cursor/skills/nornir-docker-images-ci/SKILL.md) | Image matrix, OCI/BOM, Docker CI |
| [nornir-documentation](.cursor/skills/nornir-documentation/SKILL.md) | Build/deploy Sphinx monodoc |
| [nornir-bump-version](.cursor/skills/nornir-bump-version/SKILL.md) | Package vs monorepo version bumps; Pyre installer |
| [nornir-debug-profiling](.cursor/skills/nornir-debug-profiling/SKILL.md) | PhaseProfiler, slowness and queue profiling |
| [pyre-registration-performance](.cursor/skills/pyre-registration-performance/SKILL.md) | After Pyre registration edits: check profiler; ≤1 s/control point |
| [nornir-headless-unit-tests](.cursor/skills/nornir-headless-unit-tests/SKILL.md) | `NORNIR_HEADLESS`, plot artifact triage |
| [nornir-review-issue-fixing](.cursor/skills/nornir-review-issue-fixing/SKILL.md) | Working the bug-review queue end to end |
| [nornir-improve-loop](.cursor/skills/nornir-improve-loop/SKILL.md) | Only when the user launches it: timed improvement loop over the monorepo, incl. the XML-to-SQLite metadata port |
| [nornir-serial-batched-primitives](.cursor/skills/nornir-serial-batched-primitives/SKILL.md) | Serial/batched registration verification |
| [refine-grid-trust-review](.cursor/skills/refine-grid-trust-review/SKILL.md) | Trust-question review of refine-grid gates and mesh membership |
| [pyre-stos-rigid-transform-ui](.cursor/skills/pyre-stos-rigid-transform-ui/SKILL.md) | Pyre STOS rigid UI semantics |

---

## Deprecated

`.aiassistant/rules/` is **not** maintained. Use `.cursor/rules/` instead.
