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

When changes are made to registration code invoked by pyre. Check the profiler results after a pyre run to get a sense of the impact. We want to maintain fast performance. A user should get a registration result within 1 second of requesting a registration on a control point.

Treat **>1 s request→result for a single control point** as a regression unless the user explicitly accepts a slower path (e.g. huge ROI, many angles, or intentional diagnostics).

## When this skill applies

Any change that can affect wall time on these paths:

| Path | Typical trigger |
|------|-----------------|
| Single / selected control points | Space / click register → `RegisterControlPointCommand` → `enqueue_point_registrations` → `AttemptAlignPoint` |
| Register-all (mesh/RBF) | Shift+Space → same queue, N points serial |
| Grid refine from Pyre | Refine w/ Grid / `GridRegisterAllCommand` → `RegistrationJobRunner` |

Also covers shared math under `nornir-imageregistration` (phase correlation, ROI extract, masks) when Pyre is a caller.

## Required workflow after code changes

1. **Restart Pyre** so the edited modules load (no hot reload).
2. **Reproduce** the registration the change touches (prefer one control point for the 1 s budget; use Refine Grid only when that path changed).
3. **Read profiler output** under `NORNIR_LOG_ROOT/<date>/`:
   - `nornir-phase-profile-<session>.ndjson` — `worker:end` `elapsed_ms`, `cProfile saved` → `top_cumtime`, `refine_phase_totals` when present
   - `nornir-phase-profile-<session>.pstats` — optional deeper dump
4. **Judge impact** before calling the change done:
   - Single-point: request→result should stay **≤ 1 s** on a normal STOS pair / default alignment area.
   - If slower, identify the dominant `top_cumtime` / phase bucket and fix or flag before merge-minded wrap-up.
5. **Do not** leave the task as “code compiles / tests pass” without profiler evidence when registration latency could have changed.

Job-scoped cProfile (not the Qt UI loop) is configured by `pyre.phase_profile` when `NORNIR_LOG_ROOT` is set. Opt out only with `NORNIR_PHASE_PROFILE_JOBS=0` (avoid while checking this budget).

## How to read the NDJSON quickly

- `message: "worker:end"` + `data.elapsed_ms` — whole registration job / worker wall time.
- `message: "cProfile saved"` + `data.top_cumtime` — hottest frames for that job.
- `message: "refine_phase_totals"` — grid-refine phase buckets (`fft`, `prewarp`, …) in seconds.
- For **single-point** work that does not go through `RegistrationJobRunner`, use [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md) (`phase_timer` / `log_event` on enqueue → align → apply) if job NDJSON is empty; still enforce the 1 s user-visible budget.

## Related

- Tooling detail: [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md)
- Serial queue / register-all semantics: same profiling skill (Shift+Space section)
- Batched/serial math parity: [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md)
