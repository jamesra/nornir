---
name: nornir-improve-loop
description: >-
  Claude Code launcher for the Nornir improvement loop: a timed loop over the whole
  monorepo that makes one refactoring, bug-fix, test, performance, or XML-to-SQLite
  metadata-port change per wake, gated by tests and benchmarks, committed in the owning
  submodule when green with the umbrella pointer bumped, and dated review reports.
  Formats read outside Nornir are proposal-only. Only for when the user runs
  /nornir-improve-loop; never start it for another task.
disable-model-invocation: true
argument-hint: "[run length, e.g. 12h] [sleep between wakes, e.g. 10m]"
---

# Nornir improvement loop (Claude Code)

Claude Code adapter for the Cursor skill in `.cursor/skills/nornir-improve-loop/`. The loop's
**policy** is single-sourced there so the two tools cannot drift; this file replaces only the
tool-specific parts: launch, wake orchestration, scheduling, and model routing.

Arguments given: `$ARGUMENTS`

Start the loop only because the user launched this skill. If a wake is already pending in this
session, do not start a second copy.

## Where things live

| Name | Path |
|------|------|
| `$SKILL` | `D:\src\git\nornir\.claude\skills\nornir-improve-loop` (this folder) |
| `$SHARED` | `D:\src\git\nornir\.cursor\skills\nornir-improve-loop` (shared policy) |
| `$ROOT`, `$PY`, `$LOOP_ROOT` | the `windows` column under **Environment** in `$SHARED\SKILL.md` (`$ROOT` = `D:\src\git\nornir`) |
| Ledger | `$LOOP_ROOT\.loop\ledger.json` (schema under **Ledger** in `$SHARED\SKILL.md`) |

Shared files, read by the subagent that needs them (never pasted into prompts):

- `$SHARED\SKILL.md`: read **only** Arguments, Environment, Scope, Sync from the remote, Time box, Steering, Decisions, Ledger, and "Choosing between the port and the rotation". **Ignore its Launch, Each wake, Compactness hygiene, and Model routing sections** (Cursor-specific); this file replaces them.
- `$SHARED\protected.md`, `categories.md`, `gates.md`, `reports.md`: apply unchanged. `metadata-port.md`: only on port wakes.
- `$SKILL\main-session.md`: the thin wake playbook for the **main** session only.

## Differences from Cursor that affect the policy files

- **Rules and skills are not auto-loaded.** Cursor attaches `.cursor/rules/*.mdc` by glob; Claude Code does not. Before editing, the implementer reads the rules in `$ROOT\.cursor\rules\` that match the files it touches (`python-standards`, `Numpy-CuPy-compatibility`, `Stable-path-output-parity`, `Monorepo-submodule-changes`, `CI-hygiene`, `Streaming-and-memory-bounded-processing`, `Serial-batched-primitives`, `Unified-Logging-Convention`, `powershell-scripts`, as `gates.md` "Nornir rules respected" lists). Related skills linked from the shared files (`nornir-review-issue-fixing`, `hypothesis-testing`, `nornir-headless-unit-tests`, `nornir-debug-profiling`, ...) are plain markdown under `$ROOT\.cursor\skills\`; read them by path when a gate points to one.
- **Windows host only.** This port runs on the Windows host (`environment: windows`). Do not use the container branch of the Environment table. Mutation check: `mutationMode` is `container` if the `cursor-dev` container is reachable, else `manual` (see `gates.md`).
- **Unattended.** Never call `AskUserQuestion` or enter plan mode inside the loop. A question for the user becomes a `decisions` entry plus the Windows toast, per Decisions in `$SHARED\SKILL.md`.
- **Commits are authorized by launching this skill.** Stage by path only, never `git add -A`/`.`, never push, never `git submodule update`. Each commit ends with the `Improvement-Loop: <category>` trailer, then the attribution trailer Claude Code is configured to add. Submodule commit first, then the umbrella pointer bump, per `gates.md`.
- **Shell:** PowerShell; do not chain with `&&` (use `;` or separate calls).
- **Permissions:** the loop needs `git`, `$PY`, `ruff`, `pyright`, `pyperf`, `docker` (for mutmut), and file edits pre-approved (Auto mode or an allowlist), or it stalls on a prompt with no one watching. Use a dedicated session.
- **Dirty tree at launch:** the umbrella and some submodules have uncommitted edits (including the shared skill files themselves). Record them as `launchDirty`; `protected.md` already forbids touching files with edits the loop did not make. Never edit `$SHARED` or this folder from the loop.
- **Scheduling** uses `ScheduleWakeup` instead of sleeper processes; there is no `runner.sleeperPid`/`sleeperShellId` and no stale-sleeper check.

## Launch

1. Parse `$ARGUMENTS` per Arguments in `$SHARED\SKILL.md` (X = run length, default 24h; Y = sleep, default 10m). `ScheduleWakeup` accepts 60-3600 s, so **cap Y at 60 minutes** and tell the user if capped. Deadline = launch time + X.
2. Set `environment: windows`. One-runner rule: if the ledger `runner.heartbeatAt` is newer than `max(3 * Y minutes, 30 minutes)`, do not start; say which runner holds it.
3. Create `$LOOP_ROOT`, `.loop\ledger.json`, and `STEERING.md` (short commented template) if missing. Record each repo's branch and `git status --short` as `branches` / `launchDirty`; a submodule on a detached HEAD is not editable. Run **Sync from the remote** once (main may do this at launch only).
4. Install any missing dev tools into `$PY` as listed in Launch step 3 of `$SHARED\SKILL.md` (never into a `pyproject.toml` or constraints file). Check `cursor-dev` reachability and set `mutationMode`.
5. Build `hotspots` and run the tiered test baseline (seeding known flakes) per `categories.md` / `gates.md`. These may run inside the first scout to keep main small.
6. Run one wake immediately (Each wake, below).
7. Arm the next wake (see **Scheduling**).

## Each wake

The main session only schedules, relays, and talks to the user. All work runs in fresh subagents, **one at a time, foreground**: `Agent` with `subagent_type: "general-purpose"`, `run_in_background: false`, a `model` per Model routing, and **no `effort` override**. Each prompt contains only the two paths, never ledger JSON, wake history, or file bodies. Main follows `$SKILL\main-session.md`.

1. **Scout**, prompt: `Run the scout step of skill nornir-improve-loop (Claude Code port). Skill folder: <$SKILL>. Ledger: <ledger>.`
   Reads: this file, the allowed sections of `$SHARED\SKILL.md`, `protected.md`, `categories.md`, the ledger, `STEERING.md`; `metadata-port.md` on port wakes; `reports.md` and the `gates.md` Test baseline only when a report or baseline is due. In order:
   1. Sync; write `lastSync` / `syncSkips`; refresh `runner.heartbeatAt`;
   2. read `STEERING.md` and the ledger;
   3. stop on `stop`, the deadline, or `emptyWakes` reaching 3, writing the `final` report;
   4. when 24 hours since `lastReportAt` (or `startedAt`): write the `daily` report, rebuild `hotspots`, re-run the baseline, check reworked commits;
   5. on `pause`, end the wake;
   6. otherwise pick one candidate into `candidate` (category or port stage, package, files, one-paragraph plan, risk `low|high`). It edits no production code. A protected or unmeasurable candidate becomes a proposal or decision and the wake ends.
   Returns at most four lines.
2. **Implementer**, prompt: `Run the implement step of skill nornir-improve-loop (Claude Code port) for the candidate in the ledger. Skill folder: <$SKILL>. Ledger: <ledger>.`
   Reads: this file, Scope and Time box from `$SHARED\SKILL.md`, `protected.md`, `gates.md`, the ledger, `metadata-port.md` on port wakes, and the `.cursor/rules` files matching what it touches. Runs the gates, tests, mutation check, and benchmark when needed; commits in the owning submodule if green and bumps the umbrella pointer; publishes if due; clears `candidate`. If the change is riskier than the scout said, it stops without committing and sets risk `high`. Returns at most four lines.
3. **Reviewer, high-risk commits only**, prompt: `Review commit <sha> in <submodule> against the gates in <$SHARED>. Report problems only.` Reads `protected.md` and `gates.md`. On a violation, run the implementer once (`Follow-up after review of <sha>. Skill folder: <$SKILL>. Ledger: <ledger>.`) or revert the commit and its pointer bump, and record the outcome.
4. Main posts a one- or two-sentence summary (see `main-session.md`) and arms the next wake, or nothing on stop.
5. User-requested report: the scout writes a `requested` report immediately; the loop continues. User stop: `ScheduleWakeup` with `stop: true`, the scout writes `final`, arm nothing.

Compactness: follow the `wakesSinceCompact` rule in `main-session.md`.

## Scheduling

Use `ScheduleWakeup`. Never arm more than one pending wake.

```
ScheduleWakeup(
  delaySeconds: <Y * 60>,
  reason: "nornir-improve-loop: next wake",
  noop: <true on empty/reject/pause wakes, false when something was committed or decided>,
  prompt: "AGENT_LOOP_WAKE_nornir_improve - Read D:\src\git\nornir\.claude\skills\nornir-improve-loop\main-session.md and follow it. Ledger: <ledger path>."
)
```

The wake prompt points at `main-session.md` by path so a wake works without re-invoking this (model-invocation-disabled) skill. Deadline and interval live in the ledger, not the prompt. If `ScheduleWakeup` is unavailable or errors, tell the user and offer `/loop <Y>m` with the same prompt; do not silently run without a schedule.

## Model routing

Pass as the Agent `model`. Record the model used per commit in the ledger; record any substitution in `modelSubstitutions`.

| Role | `model` | Notes |
|------|---------|-------|
| Scout, reports, ledger upkeep | `sonnet` | picks candidates and judges protected-area risk |
| Low-risk implementer | `sonnet` | dead weight (11), resolvable debt notes (12), hand-rolled helpers (7), test-only (14), within one package and away from protected areas |
| High-risk implementer | `opus` | everything else, plus any low-risk category touching `nornir-shared` or `nornir-pools`, more than one package, a numeric dtype, a file next to a protected area, `volumemanager`, or any metadata-port stage |
| Reviewer (high-risk commits only) | `fable` | deliberately a different model from the implementer |

The Cursor version used `-high` variants, `composer`, and a GPT reviewer; Claude Code has no per-agent equivalent the loop may set, so those are dropped. Retune this table here, not in the shared files.
