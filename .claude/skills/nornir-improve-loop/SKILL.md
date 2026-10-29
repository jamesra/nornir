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

Claude Code adapter for the Cursor skill in `.cursor/skills/nornir-improve-loop/`, where the loop's **policy** is single-sourced so the two tools cannot drift. This file replaces only the tool-specific parts: launch, wake orchestration, scheduling, and model routing.

Arguments given: `$ARGUMENTS`

Start the loop only because the user launched this skill. If a wake is already pending in this session, do not start a second copy.

## Where things live

| Name | Path |
|------|------|
| `$SKILL` | `D:\src\git\nornir\.claude\skills\nornir-improve-loop` (this folder) |
| `$SHARED` | `D:\src\git\nornir\.cursor\skills\nornir-improve-loop` (shared policy) |
| `$ROOT`, `$PY`, `$LOOP_ROOT` | the `windows` column under **Environment** in `$SHARED\SKILL.md` (`$ROOT` = `D:\src\git\nornir`) |
| Ledger | `$LOOP_ROOT\.loop\ledger.json` (schema under **Ledger** in `$SHARED\SKILL.md`) |

Shared files, read by the subagent that needs them (never pasted into prompts):

- `$SHARED\SKILL.md`: read **only** Arguments, Environment, Scope, Sync from the remote, Time box, Steering, Decisions, Ledger, and "Choosing between the port and the rotation". **Ignore its Launch, Each wake, Compactness hygiene, and Model routing sections** (Cursor-specific); this file replaces them, except where a step below points to a numbered shared Launch step.
- `$SHARED\ledger.py`: the only way to read or edit the ledger (Ledger in `$SHARED\SKILL.md`).
- `$SHARED\protected.md`, `categories.md`, `gates.md`, `reports.md`: apply unchanged. `metadata-port.md`: port wakes only.
- `$SKILL\main-session.md`: the wake playbook for the **main** session only.

## Differences from Cursor that affect the policy files

- **Rules and skills are not auto-loaded.** Cursor attaches `.cursor/rules/*.mdc` by glob; Claude Code does not. `.claude\rules\` mirrors the glob-scoped ones (loaded when a matching file is read or edited), but the implementer still reads, before editing, the rules in `$ROOT\.cursor\rules\` matching the files it touches: those `gates.md` "Nornir rules respected" lists, plus `Stable-path-output-parity`, `Monorepo-submodule-changes`, `Shared-checkout-safety`, `CI-hygiene`, `Unified-Logging-Convention`, and `powershell-scripts`. Skills linked from the shared files (`nornir-review-issue-fixing`, `hypothesis-testing`, `nornir-headless-unit-tests`, `nornir-debug-profiling`, ...) are plain markdown under `$ROOT\.cursor\skills\`; read them by path when a gate points to one.
- **Windows host only** (`environment: windows`); do not use the Environment table's container column. `mutationMode` is `container` if the `cursor-dev` container is reachable, else `manual` (see `gates.md`).
- **Unattended.** Never call `AskUserQuestion` or enter plan mode inside the loop. A question for the user becomes a `decisions` entry plus the Windows toast, per Decisions in `$SHARED\SKILL.md`.
- **Commits are authorized by launching this skill.** Follow `gates.md` commit rules: stage by path only (never `git add -A`/`.`), never push, never `git submodule update`; submodule commit first, then the umbrella pointer bump. Each commit ends with the `Improvement-Loop: <category>` trailer, then the attribution trailer Claude Code is configured to add.
- **Shell:** PowerShell; do not chain with `&&` (use `;` or separate calls).
- **Permissions:** pre-approve `git`, `$PY`, `ruff`, `pyright`, `pyperf`, `docker` (for mutmut), and file edits (Auto mode or an allowlist), or the loop stalls on a prompt with no one watching. Use a dedicated session.
- **Dirty tree at launch:** the umbrella and some submodules have uncommitted edits (including the shared skill files themselves). Record them as `launchDirty`; `protected.md` already forbids touching files with edits the loop did not make. Never edit `$SHARED` or this folder from the loop.
- **Scheduling** uses `ScheduleWakeup`, not sleeper processes: no `runner.sleeperPid`/`sleeperShellId`, no stale-sleeper check.

## Launch

1. Parse `$ARGUMENTS` per Arguments in `$SHARED\SKILL.md` (X = run length, default 24h; Y = sleep, default 10m; deadline = launch time + X). `ScheduleWakeup` accepts 60-3600 s: for Y over 60 minutes, write `nextWakeAt` to the ledger and arm 60-minute wakes that do no work until it is due.
2. Set `environment: windows`. One-runner rule: if the ledger `runner.heartbeatAt` is newer than `max(3 * Y minutes, 30 minutes)`, do not start; say which runner holds it.
3. Create `$LOOP_ROOT`, `.loop\ledger.json`, and `STEERING.md` (short commented template) if missing; archive an earlier run's ledger and start a fresh one as shared Launch step 2 says. Record each repo's branch and `git status --short` as `branches` / `launchDirty`; a submodule on a detached HEAD is not editable. Run **Sync from the remote** once (main may Sync at launch only).
4. Install missing dev tools into `$PY` and record `toolCommands` as shared Launch step 3 says (never into a `pyproject.toml` or constraints file). Check `cursor-dev` reachability and set `mutationMode`.
5. Build `hotspots` and run the tiered test baseline (seeding known flakes) per `categories.md` / `gates.md`; these may run inside the first scout to keep main small.
6. Run one wake immediately (Each wake, below). Tell the user the deadline, the interval, and that `STEERING.md` is read every wake (say so if it already contains `pause`).
7. Arm the next wake (see **Scheduling**).

## Each wake

Main only schedules, relays, and talks to the user, following `$SKILL\main-session.md`. All work runs in fresh subagents, **one at a time, foreground**: `Agent` with `subagent_type: "general-purpose"`, `run_in_background: false`, a `model` per Model routing, and **no `effort` override**. Each prompt carries only the two paths: never ledger JSON, wake history, or file bodies.

1. **Scout**, prompt: `Run the scout step of skill nornir-improve-loop (Claude Code port). Skill folder: <$SKILL>. Ledger: <ledger>.`
   Reads this file, the allowed sections of `$SHARED\SKILL.md`, `protected.md`, `categories.md`, the ledger, `STEERING.md`; `metadata-port.md` on port wakes; `reports.md` and the `gates.md` Test baseline only when a report or baseline is due. In order:
   1. Sync; write `lastSync` / `syncSkips`; refresh `runner.heartbeatAt`;
   2. run `$PY -I $SHARED\ledger.py <ledger> brief`: it prints the wake state and the `$LOOP_ROOT\STEERING.md` directives, or `MISSING <path>` (recreate the template and treat it as no steering). Open `STEERING.md` only when `brief` reports guidance lines; `get` other keys as needed;
   3. on `stop`, a wake starting after the deadline (`startedAfterDeadline`), or `emptyWakes` reaching 3: write the `final` report (unless `stop` is already true and this run's `final` exists), set `stop: true`, and stop;
   4. on `pause`, end the wake (no daily report, hotspot rebuild, or baseline; an owed daily report is written on the first unpaused wake);
   5. 24 hours after `lastReportAt` (or `startedAt`): write the `daily` report, rebuild `hotspots`, re-run the baseline, check reworked commits;
   6. otherwise write one candidate to `candidate` (category or port stage, package, files, one-paragraph plan, risk `low|high`). Edit no production code. A protected or unmeasurable candidate becomes a proposal or decision and the wake ends.
   Return only the scout block from Each wake in `$SHARED\SKILL.md` (`candidate:`, `risk:`, `decisions:`, `report:`, `stop:`).
2. **Implementer**, prompt: `Run the implement step of skill nornir-improve-loop (Claude Code port) for the candidate in the ledger. Skill folder: <$SKILL>. Ledger: <ledger>.`
   Reads this file, Scope and Time box from `$SHARED\SKILL.md`, `protected.md`, `gates.md`, the ledger, `metadata-port.md` on port wakes, and the `.cursor/rules` files matching what it touches. Runs the gates, tests, mutation check, and benchmark when needed; if green, commits in the owning submodule and bumps the umbrella pointer; publishes if due; clears `candidate`. If the change is riskier than the scout said, stop without committing and set risk `high`. Return only the implementer block from Each wake in `$SHARED\SKILL.md` (`outcome:`, `decisions:`, `publish:`, `countsSincePublish:`).
3. **Reviewer, high-risk commits only**, prompt: `Review commit <sha> in <submodule> against the gates in <$SHARED>. Report problems only.` Reads `protected.md` and `gates.md`; gets only the commit, not the implementer's reasoning, and reruns its mutation check (`gates.md` Mutation check, reviewer rerun). On a violation, run the implementer once (`Follow-up after review of <sha>. Skill folder: <$SKILL>. Ledger: <ledger>.`) or revert the commit and its pointer bump; record the outcome.
4. Main posts a one- or two-sentence summary (see `main-session.md`) and arms the next wake, or nothing on stop.
5. User asks for a report: the scout writes a `requested` report immediately; the loop continues. User stop: `ScheduleWakeup` with `stop: true`, the scout writes `final`, arm nothing.

Compactness: follow the `wakesSinceCompact` rule in `main-session.md`.

## Scheduling

Use `ScheduleWakeup`; never more than one pending wake.

```
ScheduleWakeup(
  delaySeconds: <Y * 60>,
  reason: "nornir-improve-loop: next wake",
  noop: <true on empty/reject/pause wakes, false when something was committed or decided>,
  prompt: "AGENT_LOOP_WAKE_nornir_improve - Read D:\src\git\nornir\.claude\skills\nornir-improve-loop\main-session.md and follow it. Ledger: <ledger path>."
)
```

The wake prompt points at `main-session.md` by path so a wake works without re-invoking this (model-invocation-disabled) skill. Deadline and interval live in the ledger, not the prompt. If `ScheduleWakeup` is unavailable or errors, tell the user and offer `/loop <Y>m` with the same prompt; never silently run without a schedule.

## Model routing

Pass as the Agent `model`. Record the model used per commit in the ledger, and any substitution in `modelSubstitutions`.

| Role | `model` | Notes |
|------|---------|-------|
| Scout, reports, ledger upkeep | `sonnet` | picks candidates and judges protected-area risk |
| Low-risk implementer | `sonnet` | dead weight (11), resolvable debt notes (12), hand-rolled helpers (7), test-only (14), within one package and away from protected areas |
| High-risk implementer | `opus` | everything else, plus any low-risk category touching `nornir-shared` or `nornir-pools`, more than one package, a numeric dtype, a file next to a protected area, `volumemanager`, or any metadata-port stage |
| Reviewer (high-risk commits only) | `fable` | deliberately a different model from the implementer |

If an Agent call rejects a model, retry once with `sonnet` (for a rejected `fable` reviewer, use `opus` in a fresh subagent) and record it in `modelSubstitutions`.

Claude Code has no per-agent equivalent of the Cursor version's `-high` variants, `composer`, or GPT reviewer that the loop may set, so those are dropped. Retune this table here, not in the shared files.
