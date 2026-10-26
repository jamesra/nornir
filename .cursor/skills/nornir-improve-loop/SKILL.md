---
name: nornir-improve-loop
description: >-
  Runs a timed improvement loop over the whole Nornir monorepo: one refactoring,
  bug-fix, test, performance, or metadata-port change per wake, gated by tests
  and benchmarks, committed in the owning submodule when green, with the umbrella
  pointer bumped and dated review reports. Alternates between the staged
  XML-to-SQLite volume-metadata port and a rotation of Python improvement
  categories. File formats read outside Nornir are proposal-only. Use when the
  user launches this skill or a wake payload says to follow nornir-improve-loop.
disable-model-invocation: true
---

# Nornir improvement loop

Start the loop only when this skill is launched, not when this file is opened for another task. If `AGENT_LOOP_WAKE_nornir_improve` is already sleeping in this session, do not start a second copy.

Files (each subagent reads only its own, see Each wake; Task prompts carry the skill folder and ledger paths, never file bodies):

- [main-session.md](main-session.md): wake playbook for the **main** session only (context budget); after launch, main reads nothing else here.
- [protected.md](protected.md): areas the loop never edits.
- [categories.md](categories.md): hotspots, the 19 categories, proposals.
- [gates.md](gates.md): what a change must pass; tests, mutation, benchmarks, commit, publish.
- [metadata-port.md](metadata-port.md): XML-to-SQLite metadata port stages and gates; port wakes only.
- [reports.md](reports.md): report format and learning from reverts.

The gates lean on [nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md), [hypothesis-testing](../hypothesis-testing/SKILL.md), [nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md), [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md), [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md), and the rules in [`.cursor/rules/`](../../rules/).

## Arguments

`/nornir-improve-loop [X] [Y]`: X = run length (default 24 hours), Y = sleep after each wake (default 10 minutes). Accept `30m`, `4h`, `1d`, or bare minutes. Deadline = launch time + X. Use America/Los_Angeles in messages to the user.

## Environment

The loop runs on the **Windows host** or in the **Linux dev container** (`cursor-dev`, see [nornir-docker-devcontainer](../nornir-docker-devcontainer/SKILL.md)). At launch, record `environment` in the ledger: `container` if `/.dockerenv` exists or `NORNIR_WORKSPACE_STRATEGY` is set; `windows` if `$env:OS` is `Windows_NT`; anything else (native Linux or macOS) uses the `container` column, but `NORNIR_LOOP_ROOT` must be set.

Other files in this skill use these names instead of literal paths:

| Name | `windows` | `container` |
|------|-----------|-------------|
| `$ROOT`, the umbrella checkout | `d:\src\git\nornir` | `/workspace` |
| `$PY`, the Python to run tools and tests with | `$ROOT\venv\pyre314\Scripts\python.exe` | `python` from the image environment |
| `$LOOP_ROOT`, holds reports, `STEERING.md`, `.loop\ledger.json` | `$env:NORNIR_LOOP_ROOT`, else `d:\src\git\Nornir Automatic Improvement Reports` | `$NORNIR_LOOP_ROOT`, else `$TESTOUTPUTPATH/nornir-improve-loop` |
| Shell for commands | PowerShell | bash |
| Decision alert | Windows toast from PowerShell, plus chat | chat, plus a line appended to `$LOOP_ROOT/PENDING-DECISIONS.txt` |
| Mutation check | mutmut in the container if reachable, else manual | mutmut directly (`os.fork` works) |
| Pyre installer build | allowed (see gates.md Publish) | skipped and recorded as `skipped: not Windows` |

In both:

- `$LOOP_ROOT` must be outside every git repo and survive a container recreate. In the container, `$TESTOUTPUTPATH` (bind-mounted from host default `D:\nornir-test-output`) qualifies; `/workspace` and `/tmp` do not. If neither `NORNIR_LOOP_ROOT` nor `TESTOUTPUTPATH` is set, stop and raise a decision; never pick a path inside a repo. To share ledger and reports between host and container runs, set `NORNIR_LOOP_ROOT` to the same folder on both.
- **One runner per checkout.** The container bind-mounts the host checkout, so loops on both sides would edit the same files. The ledger holds `runner: { environment, host, startedAt, heartbeatAt }`, refreshed every wake. At launch, if another runner's heartbeat is newer than `max(3 * Y minutes, 30 minutes)`, do not start; tell the user which runner holds it. A stopped loop clears `runner`.
- Prefer a **dedicated chat** so wake noise stays out of human-work threads.
- Never rely on user-level skills: `~/.cursor/skills*` is not mounted in the container (see Launch for the `loop` fallback).
- Commands are written once; translate path separators and shell syntax to the environment.
- In the container, do not change git configuration. If `git` reports `dubious ownership`, or `user.name`/`user.email` is unset, raise a decision (the user decides on `safe.directory` or an identity) and make no commits until answered.
- Host and container edits to one bind mount can show mass mode or line-ending changes. Record each repo's `git status --short` at launch as `launchDirty`; if the whole tree looks modified, stop with a decision rather than guess which edits are the loop's.

## Scope

In scope: the umbrella repo (`$ROOT`), every `nornir-*` submodule, and `dm4`, each on its checked-out branch (at the time of writing: `dev` for buildmanager, imageregistration, pyre, shared; `master` for pools, volumemodel, volumecontroller, web, dm4; `main` for docker, builddashboard). At launch the scout records each branch in the ledger and refuses to edit a submodule on a detached HEAD.

Do not edit generated files (`*.egg-info`, build output), comment code out to compile, push, or tag. Confirm the owning submodule's branch before the first edit in it.

## Sync from the remote

Main runs Sync once at **Launch**; on **later wakes** the **scout** runs it, keeping fetch/merge output out of the long-lived chat (deliberately unlike Viking's loop, which Syncs in main). Write results to `lastSync` and `syncSkips`.

- Umbrella and each submodule: `git fetch origin`, then `git merge --ff-only @{u}` on the checked-out branch.
- Never run `git submodule update`; it detaches submodules at the umbrella-recorded pointers ([Monorepo-submodule-changes](../../rules/Monorepo-submodule-changes.mdc)).
- Fast-forward only. If a repo cannot (diverged history, or uncommitted local edits the incoming commits touch), leave it, work from the current tree, and record `{repo, reason, date}` in `syncSkips`. Never stash, reset, rebase, force, or discard anything to make a pull succeed; never push.
- A branch with no upstream is skipped silently and noted once in `syncSkips`.
- If the pull touches the `candidate`'s files, the scout re-checks the candidate before the implementer runs.

## Time box

If a wake passes about 60 minutes of work without a candidate clearing the gates, revert, add it to `deferred`, and end the wake.

## Launch

1. Detect the environment; check the one-runner rule. Read the `loop` skill once if available (`~/.cursor/skills-cursor/loop/SKILL.md`; absent in the container, so use the fallback below). Use the dynamic local schedule with sentinel `AGENT_LOOP_WAKE_nornir_improve`; never arm a fixed repeating sleeper.
2. Create `$LOOP_ROOT`, `.loop/ledger.json`, and `STEERING.md` if missing. Run Sync from the remote.
3. Install missing dev tools into the `$PY` environment: `ruff`, `vulture`, `radon`, `pylint`, `pyright`, `pyperf`, `crosshair-tool`, plus `mutmut` in the container. Never add them to a package `pyproject.toml` or constraints files. Container installs vanish on recreate; that is not a failure (the next launch reinstalls).
4. Mutation check mode: in the container, confirm `$PY -m mutmut --version` works and set `mutationMode: "native"`. On Windows, check that the `cursor-dev` container is reachable (needed for mutmut, see [gates.md](gates.md) Mutation check); if not, set `mutationMode: "manual"` and tell the user once.
5. Build `hotspots`, run the tiered test baseline, then run one wake immediately.
6. Arm the next wake with:

```json
{"prompt":"Follow skill nornir-improve-loop.","deadline":"<ISO-8601>","intervalMinutes":<Y>}
```

**Fallback without the `loop` skill:** each turn, arm one one-shot background wake with `notify_on_output` matching `^AGENT_LOOP_WAKE_nornir_improve`; track its PID so stop can kill it:

```bash
sleep <seconds>
echo 'AGENT_LOOP_WAKE_nornir_improve {"prompt":"Follow skill nornir-improve-loop.","deadline":"<ISO-8601>","intervalMinutes":<Y>}'
```

On Windows PowerShell use `Start-Sleep -Seconds <seconds>` and `Write-Output` with the same line. Never leave two sleepers armed.

## Each wake

Main only schedules, relays, and talks to the user, per [main-session.md](main-session.md) (its only skill reading after launch). All work runs in fresh `generalPurpose` subagents (models per Model routing), foreground, one at a time, so main's context does not grow. Each subagent gets only the skill folder path and the ledger path and opens only the files named for its role below. **Never** paste wake history, open-decision lists, ledger JSON, or multi-paragraph "Context:" into the Task prompt; the ledger and `STEERING.md` are the memory.

1. Main: read the payload (not the `loop` skill or full `SKILL.md`); record chat decision answers into the ledger. **Do not Sync in main** after launch.
2. **Scout** (Syncs first; reads SKILL.md, protected.md, categories.md, the ledger, `STEERING.md`; metadata-port.md on port wakes; reports.md and gates.md Test baseline only when a report or baseline is due). Prompt exactly: `Run the scout step of skill nornir-improve-loop. Skill folder: <path>. Ledger: <path>.` In order:
   1. run Sync from the remote; write `lastSync` / `syncSkips`; refresh `runner.heartbeatAt`;
   2. read `$LOOP_ROOT/STEERING.md` (absolute path, not the working directory; if missing, recreate the template and treat it as no steering) and the ledger;
   3. on `stop`, the deadline, or `emptyWakes` reaching 3: write the `final` report and stop;
   4. 24 hours after `lastReportAt` (or `startedAt`): write the `daily` report, rebuild `hotspots`, re-run the test baseline, check for reworked commits;
   5. on `pause`, end the wake;
   6. otherwise write one candidate to `candidate`: category (or port stage), package, files, one-paragraph plan, risk `low` or `high` (per Model routing). Edit no production code. A protected or unmeasurable candidate becomes a proposal or decision, and the wake ends.
   Return at most four lines: candidate and risk, or why none; new decisions; report path if written; whether to stop.
3. **Implementer** (reads SKILL.md Scope and Time box, protected.md, gates.md, the ledger; metadata-port.md on port wakes). Prompt exactly: `Run the implement step of skill nornir-improve-loop for the candidate in the ledger. Skill folder: <path>. Ledger: <path>.` Runs the candidate through the gates, tests, mutation check, and benchmark when needed; if green, commits in the owning submodule and bumps the umbrella pointer; publishes if due; clears `candidate`; writes the ledger. If the candidate proves riskier than the scout said, stop without committing and set risk `high`; the next wake re-runs it with the high-risk model. Return at most four lines: commit sha and summary or why nothing passed; new decisions; whether a publish ran.
4. **Reviewer, high risk only** (reads protected.md, gates.md). After a high-risk commit: `Review commit <sha> in <submodule> against the gates in <skill folder>. Report problems only.` On a gate violation or likely defect, run the implementer once more with `Follow-up after review of <sha>. Skill folder: <path>. Ledger: <path>.`, or revert the commit and its pointer bump when the fix is unclear. Record the outcome in the commit's ledger entry.
5. Main: post only for a commit, a **new** decision (as a question), a publish, a compact notice, or a stop; empty / reject / pause wakes re-arm silently unless the user asked for status. When arming, increment `wakeCount` and `wakesSinceCompact` and run Compactness hygiene if due. Arm one Y-minute sleep, or nothing when the scout said stop. Ignore stale sleeper completion notices (see main-session.md).
6. Report requested: launch the scout model to write a `requested` report now; the loop keeps running. Stop requested: kill the tracked sleeper PID, launch the scout model to write the `final` report, arm nothing.

### Compactness hygiene

`wakesSinceCompact` is separate from `wakeCount` so port/rotation odd-even is never reset. Main increments it when arming each sleeper and every **25** wakes writes `compactSummary`, tells the user **once**, and resets it to 0, as [main-session.md](main-session.md) step 7 specifies. Between notices, empty wakes stay silent; ignore bare sleeper-completion noise after a handled wake.

### Choosing between the port and the rotation

- **Port wakes:** odd `wakeCount`, when `metadata-port.md` has a stage open and not blocked on a decision; the scout takes the lowest open stage. Main increments `wakeCount` once per armed wake and never resets it for compactness.
- **Rotation wakes:** even `wakeCount`, and port wakes with no open stage. Start at the category after `lastCategory` (see categories.md). Category 15 is the port, chosen only by the odd-wake rule.
- A `focus:` or `avoid:` line in `STEERING.md` overrides this alternation.

## Steering

`$LOOP_ROOT/STEERING.md` is the user's; the loop reads it every wake and never edits it. Understood lines:

- `focus: <path, package, category, or "port">`: search there first.
- `avoid: <path, pattern, package, or category>`: treat as protected for this run.
- `answer: <decision id> <choice>`: answers a pending decision.
- `pause`: skip work but keep arming wakes. `stop`: write the final report and stop.

Anything else is guidance to follow when it applies. If missing at launch, create it with a short commented template.

## Decisions

When a candidate needs the user's call (two reasonable designs, a behavior change that might be wanted, a protected-area proposal blocking other work, a port decision listed in metadata-port.md), do not guess ([Design-choice-confirmation](../../rules/Design-choice-confirmation.mdc)). Add it to `decisions` with an id, the question, and the options; raise the environment's decision alert with the question's first line; move to another candidate. Main posts the question in chat. An answer in chat or an `answer:` line in `STEERING.md` is recorded in the ledger; a later wake acts on it. Every report lists open decisions.

## Ledger

`$LOOP_ROOT/.loop/ledger.json`, shared by every fresh subagent. Read it at the start of each wake; write it before the wake ends.

```json
{
  "startedAt": "", "deadline": "", "intervalMinutes": 10,
  "environment": "windows|container", "runner": {}, "launchDirty": {},
  "branches": {}, "mutationMode": "native|container|manual",
  "hotspots": [], "baselineFailures": [], "flaky": [],
  "lastCategory": 0, "wakeCount": 0, "wakesSinceCompact": 0, "compactSummary": "", "emptyWakes": 0,
  "portStage": 0, "portEvidence": [],
  "candidate": { "category": 0, "stage": null, "package": "", "files": [], "plan": "", "risk": "low|high" },
  "commits": [{ "package": "", "sha": "", "umbrellaSha": "", "category": 0, "stage": null, "summary": "", "lineDelta": 0,
                "benchmark": "", "mutation": "", "risk": "", "models": {}, "review": "" }],
  "countsSincePublish": 0, "publishes": [], "pyreBuilds": [],
  "rejected": [], "deferred": [], "proposals": [],
  "decisions": [{ "id": "", "question": "", "options": [], "askedAt": "", "answer": null }],
  "reworked": [],
  "lastSync": {}, "syncSkips": [], "modelSubstitutions": [],
  "lastReportAt": null, "reports": []
}
```

## Model routing

The loop is long-running and not time-sensitive, so it saves tokens instead of using fast tiers: never route a step to a `-fast` variant. The user chose these models; pass them as the subagent's `model`. At launch, check each slug against the session's available subagent models. If one is missing, use the closest listed model of the same family and tier (never fast), or omit `model` to use the parent's, and record it in `modelSubstitutions`. Context window size cannot be set; keep each subagent's input small.

| Role | `model` | When |
|------|---------|------|
| Scout, reports, ledger upkeep | `composer-2.5` | |
| Low-risk implementer | `claude-sonnet-5-5-high` | dead weight (11), resolvable debt notes (12), hand-rolled helpers (7), test-only wakes (14), when the change stays inside one package and away from protected areas |
| High-risk implementer | `claude-opus-5-5-high` | everything else, plus any low-risk category touching a shared package (`nornir-shared`, `nornir-pools`), more than one package, a numeric dtype, a file next to a protected area, the `volumemanager` package, or any metadata-port stage |
| Reviewer | `gpt-5.5-medium` | only after high-risk commits, so the second opinion comes from a different model family |

Main can run on Auto or any inexpensive non-fast model; it does no code work. [main-session.md](main-session.md) duplicates this table so main never re-opens this file. Record the model used for each step in the commit's ledger entry.
