---
name: nornir-debug-profiling
description: >-
  Investigates Nornir/Pyre performance and runtime bugs with structured phase
  profiling (nornir_shared.profiling.PhaseProfiler), TaskTimer, cProfile, and
  hypothesis-driven NDJSON logs. Use when debugging slowness, hangs, queue
  throughput, multiprocessing bottlenecks, Shift+Space registration, or before
  adding temporary print/log instrumentation. Pair with debug-live for
  breakpoint inspection when state at a line matters more than wall time.
---

# Nornir debug and profiling

## Choose the tool

| Situation | Tool | Notes |
|-----------|------|-------|
| Wall-time breakdown across phases (UI freeze, enqueue, image prep, pool submit) | `nornir_shared.profiling.PhaseProfiler` | NDJSON + optional `.pstats` |
| Simple elapsed-time totals in CLI/pipeline stages | `nornir_shared.tasktimer.TaskTimer` | Prints via `prettyoutput`; no structured log |
| Legacy script profiling | `nornir_shared.misc.RunWithProfiler` | `cProfile.run("code string")`; prefer `PhaseProfiler` for new work |
| Wrong value / branch / null at a line | [debug-live](~/.agents/skills/debug-live/SKILL.md) + DebugMCP (`user-debugmcp` MCP) | Breakpoints first; avoid guessing runtime state |
| Process-pool worker hotspots | `NORNIR_PROFILE` env (see `nornir_pools`) | Writes per-worker `.pstats` under `.nornir-pools-profile/` |

Default venv: `D:\src\git\nornir\venv\pyre314` (see **Virtual-Env** rule).

Before claiming a speed-up, meet [Performance-evidence](../../rules/Performance-evidence.mdc): measured
before/after numbers, the step's share of end-to-end time, pyperf `compare_to` JSON plus an old-vs-new
equivalence test. pyperf on Windows needs `--copy-env` or its workers cannot import the venv. Rejected
candidates: [optimization-loop-rejections.md](../../issue-handoff/optimization-loop-rejections.md). Confirm
material perf/architecture changes per [Design-choice-confirmation](../../rules/Design-choice-confirmation.mdc).

---

## PhaseProfiler (preferred for agents)

Module: `nornir_shared/profiling.py`; tests: `nornir-shared/tests/test_profiling.py`.

### Setup (explicit paths)

```python
import os
from pathlib import Path
from nornir_shared.profiling import PhaseProfiler, configure_phase_profiler

out = Path(os.environ["TESTOUTPUTPATH"])  # never the repo root
configure_phase_profiler(
    PhaseProfiler(
        session_id="my-session",
        log_path=out / "debug-my-session.log",          # NDJSON, one object per line
        profile_path=out / "debug-my-session.pstats",   # optional cProfile dump
        run_id="pre-fix",
    ),
)
```

### Setup (environment variables)

```text
NORNIR_LOG_ROOT=d:\logs\nornir
NORNIR_PHASE_PROFILE_LOG=1
# or a basename / relative name → lands in NORNIR_LOG_ROOT/<date>/
# NORNIR_PHASE_PROFILE_LOG=agent-phases.ndjson
# Absolute path still allowed for an explicit agent override:
# NORNIR_PHASE_PROFILE_LOG=C:\Temp\Nornir\debug.log   (never the repo root)
NORNIR_PHASE_PROFILE_PSTATS=1
NORNIR_PHASE_PROFILE_SESSION=my-session
NORNIR_PHASE_PROFILE_RUN_ID=pre-fix
```

Then `configure_phase_profiler(PhaseProfiler())`; paths come from env (session layout when `NORNIR_LOG_ROOT` is set and the log path is relative or a sentinel).

### Instrument a code path

```python
from nornir_shared.profiling import log_event, phase_timer, start_cprofile, stop_cprofile

log_event(
    hypothesis_id="A",
    location="module.py:fn",
    message="enter",
    data={"count": n},
)

with phase_timer("A", "module.py:fn", "expensive_step", count=n):
    ...

start_cprofile("hot_path")
try:
    ...
finally:
    stop_cprofile("hot_path")  # logs top cumtime frames into NDJSON
```

Module helpers (`log_event`, `phase_timer`, `start_cprofile`, `stop_cprofile`, `next_seq`) require `configure_phase_profiler(...)` first. Hooks in library code must be no-ops when the profiler is not configured or `PhaseProfiler(..., log_path=None)`.

### Pyre

- **Session shim:** keep profiler config in a thin app-layer module that only calls `configure_phase_profiler`; instrumentation imports it. Never leave session-specific paths in shared libraries. Current example: `nornir-pyre/pyre/phase_profile.py` (`ensure_configured`, env-driven paths under `NORNIR_LOG_ROOT`). The old hard-coded `pyre/debug_shift_space_profile.py` shim was removed in nornir-pyre `ae4bbdb`.
- **Display-path timing without NDJSON:** `nornir-pyre/pyre/perf_debug.py` prints `timed(label)` blocks when `PYRE_PERF_DEBUG=1`.
- **Registration jobs (Refine w/ Grid, rotate/translate, …):** `pyre.phase_profile` configures PhaseProfiler after `SetupLogging` when `NORNIR_LOG_ROOT` is set. cProfile runs **only** inside `RegistrationJobRunner` workers (`profile_registration_job`), not during Qt UI message processing. Opt out with `NORNIR_PHASE_PROFILE_JOBS=0`. Outputs: `nornir-phase-profile-<session>.ndjson` / `.pstats` next to the session log.
- After changing registration code Pyre invokes, follow [pyre-registration-performance](../pyre-registration-performance/SKILL.md) (≤1 s per control-point registration; always read profiler output after a Pyre run).
- **Restart the GUI app** after adding or changing profiling hooks; Pyre does not hot-reload instrumented modules.

---

## Agent workflow (performance bugs)

1. **State 3–5 hypotheses** before editing (e.g. image prep, command init, enqueue, serial queue, pool overhead).
2. **Instrument** phase boundaries with `phase_timer` / `log_event`; map each log to a hypothesis id (`hypothesisId` in NDJSON).
3. **Clear the log file** before each run (one session file; do not delete other agents' logs).
4. **Ask the user to reproduce** once; read the NDJSON after.
5. **Mark each hypothesis** CONFIRMED / REJECTED / INCONCLUSIVE, citing log lines (`elapsed_ms`, counts, `pool_kind`).
6. **Fix only with timing evidence**; keep instrumentation for a verification run (`run_id="post-fix"`).
7. **Remove temporary hooks** after confirmed success or on explicit user request.

NDJSON: one JSON object per line. `hypothesisId` ties to a hypothesis; `message` is often `phase:start` / `phase:end`; `data.elapsed_ms` is phase duration; `data` also carries counts, ids, `pool_kind`, queue depth.

```bash
python -m pstats "$TESTOUTPUTPATH/debug-my-session.pstats"
# or: pip install snakeviz && snakeviz "$TESTOUTPUTPATH/debug-my-session.pstats"
```

---

## Nornir-specific tips

### Logging policy

- **Do not** add repo-root `debug-*.log` ad hoc sinks in library code, or `print()` / ad hoc file logs where `PhaseProfiler` or DebugMCP fits.
- Persistent logs: `nornir_shared.misc.SetupLogging` + `NORNIR_LOG_ROOT` (**Unified-Logging-Convention** rule).
- Temporary agent profiling goes in `PhaseProfiler` NDJSON at an explicit path, not mixed into session error logs.
- No profiling in CI commit paths without a feature flag or env gate.

### Pyre Shift+Space (control-point registration)

| Transform | Shift+Space command | Behavior |
|-----------|---------------------|----------|
| **MESH / RBF** | `RegisterControlPointCommand(register_all=True)` | Enqueues **every** control point |
| **GRID** | `GridRegisterAllCommand` | One-pass grid refine job (not per-point queue) |

Hot paths for MESH/RBF "register all":

1. `RegisterControlPointCommand.__init__`: `selected_points.update(range(N))`, `transform_controller.points` snapshot
2. `execute`: `contrasted_permutation_helper` on source/target (lazy unless contrast non-identity)
3. `TransformController.enqueue_point_registrations`: index→id, `_sync_register_busy`, `_pump_registration_queue`
4. **Serial queue**: only **one** alignment in flight; total time ≈ N × (per-point time + UI apply)
5. **Process pool**: only when `uses_process_pool_for_point_alignment()` is true (**not** when the active backend is CuPy); each point still waits for the previous one

Instrument `_pump_registration_queue` with `pool_kind` and log `wait_ms` vs `alignment_seq` to separate queue semantics from pool from alignment compute.

### Multiprocessing vs threads

- `nornir_pools.GetGlobalLocalMachinePool()`: CPU work in child processes; pickle/submit overhead per task.
- `GetGlobalThreadPool()`: in-process; GIL-bound, no pickle.
- CuPy Pyre paths stay in-thread for point alignment (CUDA context not shared with pool workers).

"Multiprocessing" does not mean all points run in parallel; check the **queue design** first.

### TaskTimer and tests

- `nornir_buildmanager` and `nornir_imageregistration` use `TaskTimer` for stage timing in volume logs; reuse it for long batch jobs. Use `PhaseProfiler` for structured, machine-readable phase logs (agent or A/B comparison).
- Set `NORNIR_HEADLESS=1` for imageregistration pytest (**nornir-headless-unit-tests** skill).

## Related

- Real-data refine A/B: [nornir-realworld-refine-benchmark](../nornir-realworld-refine-benchmark/SKILL.md)
- Pools: `nornir-docker` / `nornir_pools`; `NORNIR_PROFILE` for worker `.pstats`
