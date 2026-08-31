# Nornir Cursor skills

Procedures for agents. Policy/guardrails live in [`.cursor/rules/`](../rules/). Index also in root [`AGENTS.md`](../../AGENTS.md).

| Skill | When to use | Related rule |
|-------|-------------|--------------|
| [archive-built-plans](archive-built-plans/SKILL.md) | Archive completed plans into `.cursor/Built Plans/` | — |
| [cupy-missing-api-bugfix](cupy-missing-api-bugfix/SKILL.md) | CuPy missing/incompatible APIs; dual-backend first | [Numpy-CuPy-compatibility](../rules/Numpy-CuPy-compatibility.mdc) |
| [docker-build-run-phases](docker-build-run-phases/SKILL.md) | Build vs run scripts, env layering | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [docker-machine-layout](docker-machine-layout/SKILL.md) | `D:\Docker\Builds` / `Run` / `mounted-configs` | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [hypothesis-testing](hypothesis-testing/SKILL.md) | Property-based tests with Hypothesis | — |
| [nornir-docker-devcontainer](nornir-docker-devcontainer/SKILL.md) | cursor-dev / Dev Containers | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [nornir-docker-images-ci](nornir-docker-images-ci/SKILL.md) | Image matrix, OCI/BOM, Docker CI review | [nornir-docker-conventions](../rules/nornir-docker-conventions.mdc) |
| [nornir-documentation](nornir-documentation/SKILL.md) | Sphinx monodoc build/deploy | [Documentation-and-monodoc](../rules/Documentation-and-monodoc.mdc) |
| [nornir-debug-profiling](nornir-debug-profiling/SKILL.md) | PhaseProfiler, performance investigation | [Unified-Logging-Convention](../rules/Unified-Logging-Convention.mdc) |
| [nornir-headless-unit-tests](nornir-headless-unit-tests/SKILL.md) | `NORNIR_HEADLESS`, plot artifact triage | — |
| [nornir-review-issue-fixing](nornir-review-issue-fixing/SKILL.md) | Working a bug-review finding end to end: verify, test, commit, close | [Review-driven-bugfixing](../rules/Review-driven-bugfixing.mdc), [Stable-path-output-parity](../rules/Stable-path-output-parity.mdc) |
| [nornir-serial-batched-primitives](nornir-serial-batched-primitives/SKILL.md) | Serial/batched registration verification | [Serial-batched-primitives](../rules/Serial-batched-primitives.mdc) |
| [pyre-stos-rigid-transform-ui](pyre-stos-rigid-transform-ui/SKILL.md) | Pyre STOS rigid UI semantics | [Pyre-STOS-rigid-transform-UI](../rules/Pyre-STOS-rigid-transform-UI.mdc) |

## Docker skill split

| Skill | Owns |
|-------|------|
| docker-build-run-phases | Build vs run scripts + env layering |
| docker-machine-layout | Windows `D:\Docker\...` host paths + Compose bridge |
| nornir-docker-devcontainer | Day-to-day cursor-dev / IDE setup |
| nornir-docker-images-ci | Image matrix, OCI/BOM, CI/maintenance |
