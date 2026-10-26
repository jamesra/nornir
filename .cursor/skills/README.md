# Nornir Cursor skills

Procedures for agents. Policy/guardrails live in [`.cursor/rules/`](../rules/). Index also in root [`AGENTS.md`](../../AGENTS.md).

| Skill | When to use | Related rule |
|-------|-------------|--------------|
| [nornir-commit-push](nornir-commit-push/SKILL.md) | Commit (and push) across umbrella + submodules in dependency order; pointer refresh; lost-work audit | [Monorepo-submodule-changes](../rules/Monorepo-submodule-changes.mdc), [Shared-checkout-safety](../rules/Shared-checkout-safety.mdc) |
| [nornir-verify-change](nornir-verify-change/SKILL.md) | Verify before claiming done: tests, known flaky/baseline failures, lint/type delta | [Questions-and-proving-fixes](../rules/Questions-and-proving-fixes.mdc) |
| [segmentation-training-export](segmentation-training-export/SKILL.md) | `ExportTrainingData` / SAM2 crop export and trainer handoff | [Training-set-naming](../rules/Training-set-naming.mdc) |
| [docker-publish-ghcr](docker-publish-ghcr/SKILL.md) | Build, push, verify, pull images on GHCR | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [nornir-realworld-refine-benchmark](nornir-realworld-refine-benchmark/SKILL.md) | Real-data refine-grid A/B and acceptance criteria | [Refine-grid-trust-questions](../rules/Refine-grid-trust-questions.mdc), [Performance-evidence](../rules/Performance-evidence.mdc) |
| [archive-built-plans](archive-built-plans/SKILL.md) | Archive completed plans into `.cursor/Built Plans/` | — |
| [cupy-missing-api-bugfix](cupy-missing-api-bugfix/SKILL.md) | CuPy missing/incompatible APIs; dual-backend first | [Numpy-CuPy-compatibility](../rules/Numpy-CuPy-compatibility.mdc) |
| [deploy-connectomes](deploy-connectomes/SKILL.md) | Deploying or debugging the connectomes.pitt.edu hosts with `stack.ps1`: doctor, -Sync, up/rebuild, status, certs | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [docker-build-run-phases](docker-build-run-phases/SKILL.md) | Build vs run scripts, env layering | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [docker-machine-layout](docker-machine-layout/SKILL.md) | Host layout `Run` / `Builds` / `Data` / `Certs` / `Work` / `Logs` | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [hypothesis-testing](hypothesis-testing/SKILL.md) | Property-based tests with Hypothesis | — |
| [nornir-docker-devcontainer](nornir-docker-devcontainer/SKILL.md) | cursor-dev / Dev Containers | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [nornir-docker-images-ci](nornir-docker-images-ci/SKILL.md) | Image matrix, OCI/BOM, Docker CI review | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [nornir-documentation](nornir-documentation/SKILL.md) | Sphinx monodoc build/deploy | [Documentation-and-monodoc](../rules/Documentation-and-monodoc.mdc) |
| [nornir-bump-version](nornir-bump-version/SKILL.md) | Package vs monorepo version bumps; Pyre installer source | [Monorepo-submodule-changes](../rules/Monorepo-submodule-changes.mdc) |
| [nornir-debug-profiling](nornir-debug-profiling/SKILL.md) | PhaseProfiler, performance investigation | [Unified-Logging-Convention](../rules/Unified-Logging-Convention.mdc) |
| [pyre-registration-performance](pyre-registration-performance/SKILL.md) | After Pyre registration changes: check profiler; ≤1 s/control point | [Unified-Logging-Convention](../rules/Unified-Logging-Convention.mdc) |
| [nornir-headless-unit-tests](nornir-headless-unit-tests/SKILL.md) | `NORNIR_HEADLESS`, plot artifact triage | — |
| [nornir-review-issue-fixing](nornir-review-issue-fixing/SKILL.md) | Working a bug-review finding end to end: verify, test, commit, close | [Review-driven-bugfixing](../rules/Review-driven-bugfixing.mdc), [Stable-path-output-parity](../rules/Stable-path-output-parity.mdc) |
| [nornir-improve-loop](nornir-improve-loop/SKILL.md) | Timed, gated improvement loop over the monorepo, including the staged XML-to-SQLite metadata port (user-launched only). Main session uses [main-session.md](nornir-improve-loop/main-session.md) to keep chat context flat. | [Monorepo-submodule-changes](../rules/Monorepo-submodule-changes.mdc), [Review-driven-bugfixing](../rules/Review-driven-bugfixing.mdc), [Stable-path-output-parity](../rules/Stable-path-output-parity.mdc) |
| [nornir-serial-batched-primitives](nornir-serial-batched-primitives/SKILL.md) | Serial/batched registration verification | [Serial-batched-primitives](../rules/Serial-batched-primitives.mdc) |
| [refine-grid-trust-review](refine-grid-trust-review/SKILL.md) | Trust-question review of refine-grid gates and mesh membership | [Refine-grid-trust-questions](../rules/Refine-grid-trust-questions.mdc) |
| [pyre-stos-rigid-transform-ui](pyre-stos-rigid-transform-ui/SKILL.md) | Pyre STOS rigid UI semantics | [Pyre-STOS-rigid-transform-UI](../rules/Pyre-STOS-rigid-transform-UI.mdc) |

## Docker skill split

| Skill | Owns |
|-------|------|
| docker-build-run-phases | Build vs run scripts + env layering |
| deploy-connectomes | `stack.ps1` deploy/debug procedure for the servers |
| docker-publish-ghcr | Push/pull/verify images on GHCR (client side and publisher side) |
| docker-machine-layout | `D:\Docker` / `/srv/docker` host paths + Compose bridge |
| nornir-docker-devcontainer | Day-to-day cursor-dev / IDE setup |
| nornir-docker-images-ci | Image matrix, OCI/BOM, CI/maintenance |
