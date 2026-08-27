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
| **Wall-time breakdown across phases** (UI freeze, enqueue, image prep, pool submit) | `nornir_shared.profiling.PhaseProfiler` | NDJSON + optional `.pstats` |
| **Simple elapsed-time totals** in CLI/pipeline stages | `nornir_shared.tasktimer.TaskTimer` | Prints via `prettyoutput`; no structured log |
| **Legacy script profiling** | `nornir_shared.misc.RunWithProfiler` | `cProfile.run("code string")`; prefer `PhaseProfiler` for new work |
| **Wrong value / branch / null at a line** | [debug-live](~/.agents/skills/debug-live/SKILL.md) + DebugMCP | Breakpoints first; avoid guessing runtime state |
| **Process-pool worker hotspots** | `NORNIR_PROFILE` env (see `nornir_pools`) | Writes per-worker `.pstats` under `.nornir-pools-profile/` |

Default venv: `D:\src\git\nornir\venv\pyre314` (see **Virtual-Env** rule).

---

## PhaseProfiler (preferred for agents)

Module: `nornir_shared/profiling.py`  
Tests: `nornir-shared/tests/test_profiling.py`

### Quick setup (explicit paths)

```python
from pathlib import Path
from nornir_shared.profiling import PhaseProfiler, configure_phase_profiler

configure_phase_profiler(
    PhaseProfiler(
        session_id="my-session",
        log_path=Path("debug-my-session.log"),          # NDJSON, one object per line
        profile_path=Path("debug-my-session.pstats"),   # optional cProfile dump
        run_id="pre-fix",
    ),
)
```

### Quick setup (environment variables)

```text
NORNIR_PHASE_PROFILE_LOG=d:\src\git\nornir\debug.log
NORNIR_PHASE_PROFILE_PSTATS=d:\src\git\nornir\debug.pstats
NORNIR_PHASE_PROFILE_SESSION=my-session
NORNIR_PHASE_PROFILE_RUN_ID=pre-fix
```

Then `configure_phase_profiler(PhaseProfiler())` — paths come from env.

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

Module helpers (`log_event`, `phase_timer`, `start_cprofile`, `stop_cprofile`, `next_seq`) require `configure_phase_profiler(...)` first.

### Pyre session shim pattern

For a focused investigation, keep a thin package config (example: `nornir-pyre/pyre/debug_shift_space_profile.py`) that only calls `configure_phase_profiler` with session-specific paths. Instrumentation imports the shim, not scattered paths.

**Restart the GUI app** after adding or changing profiling hooks — Pyre does not hot-reload instrumented modules.

---

## Agent workflow (performance bugs)

1. **State hypotheses** (3–5) before editing — e.g. image prep, command init, enqueue, serial queue, pool overhead.
2. **Instrument** at phase boundaries with `phase_timer` / `log_event`; map each log to a hypothesis id (`hypothesisId` in NDJSON).
3. **Clear the log file** before each run (one session file; do not delete other agents' logs).
4. **Ask the user to reproduce** once; read NDJSON after.
5. **Mark each hypothesis** CONFIRMED / REJECTED / INCONCLUSIVE with cited log lines (`elapsed_ms`, counts, `pool_kind`).
6. **Fix only with evidence**; keep instrumentation for a verification run (`run_id="post-fix"`).
7. **Remove temporary hooks** after confirmed success or explicit user request.

### Reading NDJSON

Each line is one JSON object. Key fields:

- `hypothesisId` — ties to a hypothesis
- `message` — often `phase:start` / `phase:end`
- `data.elapsed_ms` — phase duration
- `data` — counts, ids, `pool_kind`, queue depth, etc.

### Reading `.pstats`

```bash
python -m pstats debug-my-session.pstats
# or: pip install snakeviz && snakeviz debug-my-session.pstats
```

---

## Nornir-specific tips (from past investigations)

### Logging policy

- **Do not** add repo-root `debug-*.log` ad hoc sinks in library code.
- Persistent logs: `nornir_shared.misc.SetupLogging` + `NORNIR_LOG_ROOT` (see **Unified-Logging-Convention** rule).
- **Temporary agent profiling** belongs in `PhaseProfiler` NDJSON at an explicit path, not mixed into session error logs.

### Pyre Shift+Space (control-point registration)

Two different commands by transform type:

| Transform | Shift+Space command | Behavior |
|-----------|---------------------|----------|
| **MESH / RBF** | `RegisterControlPointCommand(register_all=True)` | Enqueues **every** control point |
| **GRID** | `GridRegisterAllCommand` | One-pass grid refine job (not per-point queue) |

Hot paths to profile for MESH/RBF “register all”:

1. `RegisterControlPointCommand.__init__` — `selected_points.update(range(N))`, `transform_controller.points` snapshot
2. `execute` — `contrasted_permutation_helper` on source/target (lazy unless contrast non-identity)
3. `TransformController.enqueue_point_registrations` — index→id, `_sync_register_busy`, `_pump_registration_queue`
4. **Serial queue** — only **one** alignment in flight; total time ≈ N × (per-point time + UI apply)
5. **Process pool** — used only when `uses_process_pool_for_point_alignment()` is true (**not** when active backend is CuPy); each point still waits for the previous to finish

Instrument `_pump_registration_queue` with `pool_kind` and log `wait_ms` vs `alignment_seq` to see whether slowness is queue semantics vs pool vs alignment compute.

### Multiprocessing vs threads

- `nornir_pools.GetGlobalLocalMachinePool()` — CPU work in child processes; pickle/submit overhead per task.
- `GetGlobalThreadPool()` — in-process; GIL-bound but no pickle.
- CuPy Pyre paths stay in-thread for point alignment (CUDA context not shared with pool workers).

Do not assume “multiprocessing” means all points run in parallel — check the **queue design** first.

### TaskTimer in pipelines

`nornir_buildmanager` and `nornir_imageregistration` already use `TaskTimer` for stage timing written to volume logs. Reuse that pattern for long batch jobs; use `PhaseProfiler` when you need structured, machine-readable phase logs for an agent or A/B comparison.

### Tests and headless runs

- Set `NORNIR_HEADLESS=1` for imageregistration pytest (see **nornir-headless-unit-tests** skill).
- Profiling hooks in library code should be no-ops when `PhaseProfiler(..., log_path=None)` or profiler not configured.

---

## Anti-patterns

- ❌ Fixing slowness without timing evidence.
- ❌ `print()` / ad hoc file logs when `PhaseProfiler` or DebugMCP fits.
- ❌ Profiling in CI commit paths without a feature flag or env gate.
- ❌ Leaving session-specific `configure_phase_profiler` paths in shared libraries — keep config in app/shim layer.
- ❌ Forgetting to restart Pyre after adding instrumentation.

---

## Related

- Policy: [Design-choice-confirmation](../../rules/Design-choice-confirmation.mdc) — confirm material perf/architecture changes
- Live state: personal **debug-live** skill + `user-debugmcp` MCP
- Pools: `nornir-docker` / `nornir_pools` — `NORNIR_PROFILE` for worker `.pstats`
