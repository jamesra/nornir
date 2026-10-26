---
name: pyre-registration-performance
description: >-
  After changing registration code invoked by Pyre, check PhaseProfiler results
  from a Pyre run and keep control-point registration interactive. Use when
  editing AttemptAlignPoint, local_distortion_correction, RegisterControlPointCommand,
  TransformController enqueue/queue paths, RegistrationJobRunner, grid refine from
  Pyre, phase correlation used by point registration, or when the user mentions
  Pyre registration latency, Space-to-register, or sub-second alignment.
---

# Pyre registration performance

## Performance goal (non-negotiable)

After changing registration code Pyre invokes, check the profiler results from a Pyre run. A user
must get a registration result within **1 second** of requesting it on a control point.

Treat **>1 s request→result for a single control point** as a regression unless the user explicitly
accepts a slower path (e.g. huge ROI, many angles, intentional diagnostics).

## Paths covered

| Path | Typical trigger |
|------|-----------------|
| Single / selected control points | Space / click register → `RegisterControlPointCommand` → `enqueue_point_registrations` → `AttemptAlignPoint` |
| Register-all (mesh/RBF) | Shift+Space → same queue, N points serial |
| Grid refine from Pyre | Refine w/ Grid / `GridRegisterAllCommand` → `RegistrationJobRunner` |

Also shared math under `nornir-imageregistration` (phase correlation, ROI extract, masks) when Pyre
is a caller.

## Required workflow after code changes

1. **Restart Pyre** so edited modules load (no hot reload).
2. **Reproduce** the registration the change touches (prefer one control point for the 1 s budget;
   Refine Grid only when that path changed).
3. **Read profiler output** under `NORNIR_LOG_ROOT/<date>/`:
   - `nornir-phase-profile-<session>.ndjson`:
     - `message: "worker:end"` + `data.elapsed_ms`: whole job / worker wall time;
     - `message: "cProfile saved"` + `data.top_cumtime`: hottest frames for that job;
     - `message: "refine_phase_totals"` (when present): grid-refine phase buckets (`fft`, `prewarp`, …) in seconds.
   - `nornir-phase-profile-<session>.pstats`: optional deeper dump.
4. **Judge impact** before calling it done: single-point request→result stays **≤ 1 s** on a normal
   STOS pair / default alignment area. If slower, find the dominant `top_cumtime` / phase bucket and
   fix or flag it before wrap-up.
5. **Do not** finish on "compiles / tests pass" without profiler evidence when registration latency
   could have changed.

Job-scoped cProfile (not the Qt UI loop) is configured by `pyre.phase_profile` when `NORNIR_LOG_ROOT`
is set. `NORNIR_PHASE_PROFILE_JOBS=0` opts out; avoid it while checking this budget.

Single-point work that bypasses `RegistrationJobRunner` may leave the job NDJSON empty; then
instrument enqueue → align → apply with `phase_timer` / `log_event`
([nornir-debug-profiling](../nornir-debug-profiling/SKILL.md)). The 1 s budget still applies.

## Benchmarks outside Pyre

Isolated benchmarks of the math Pyre calls follow [Performance-evidence](../../rules/Performance-evidence.mdc)
(step's share of the registration first, then pyperf `compare_to` JSON plus an old-vs-new
equivalence test; pyperf on Windows needs `--copy-env`). A micro-benchmark win does not replace the
profiler check above. Grid refine changes also need the real-data A/B in
[nornir-realworld-refine-benchmark](../nornir-realworld-refine-benchmark/SKILL.md).

## Related

- Tooling and serial queue / register-all semantics (Shift+Space section): [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md)
- Batched/serial math parity: [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md)
