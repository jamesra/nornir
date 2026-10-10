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

When this skill is launched, start the loop. Do not start it because this file was opened for another task. If `AGENT_LOOP_WAKE_nornir_improve` is already sleeping in this session, do not start a second copy.

Files in this skill (each subagent reads only its own; see Each wake). Do not paste file bodies into Task prompts — pass the skill folder path and ledger path only:

- [main-session.md](main-session.md): thin wake playbook for the **main** session only (context budget). After launch, main reads this and nothing else from the skill.
- [protected.md](protected.md): areas the loop never edits.
- [categories.md](categories.md): hotspots, the 19 categories, proposals.
- [gates.md](gates.md): what a change must pass; tests, mutation, benchmarks, commit, publish.
- [metadata-port.md](metadata-port.md): stages and gates for the XML-to-SQLite metadata port. Read only on port wakes.
- [reports.md](reports.md): report format and learning from reverts.

Related skills and rules the gates lean on: [nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md), [hypothesis-testing](../hypothesis-testing/SKILL.md), [nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md), [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md), [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md), and the rules in [`.cursor/rules/`](../../rules/).

## Arguments

`/nornir-improve-loop [X] [Y]`

- X is the run length; default 24 hours. Y is the sleep after each wake; default 10 minutes.
- Accept `30m`, `4h`, `1d`, or a bare number of minutes.
- Deadline = launch time + X. Use America/Los_Angeles in messages to the user.

## Environment

The loop runs either on the **Windows host** or inside the **Linux dev container** (`cursor-dev`, see [nornir-docker-devcontainer](../nornir-docker-devcontainer/SKILL.md)). At launch, detect which and write it to the ledger as `environment`:

- `container` if `/.dockerenv` exists or `NORNIR_WORKSPACE_STRATEGY` is set;
- `windows` if `$env:OS` is `Windows_NT`;
- anything else (native Linux or macOS) is treated as `container` for the table below, but `NORNIR_LOOP_ROOT` must be set.

Every other file in this skill uses these names instead of literal paths:

| Name | `windows` | `container` |
|------|-----------|-------------|
| `$ROOT`, the umbrella checkout | `d:\src\git\nornir` | `/workspace` |
| `$PY`, the Python to run tools and tests with | `$ROOT\venv\pyre314\Scripts\python.exe` | `python` from the image environment |
| `$LOOP_ROOT`, holds reports, `STEERING.md`, `.loop\ledger.json` | `$env:NORNIR_LOOP_ROOT`, else `d:\src\git\Nornir Automatic Improvement Reports` | `$NORNIR_LOOP_ROOT`, else `$TESTOUTPUTPATH/nornir-improve-loop` |
| Shell for commands | PowerShell | bash |
| Decision alert | Windows toast from PowerShell, plus chat | chat, plus a line appended to `$LOOP_ROOT/PENDING-DECISIONS.txt` |
| Mutation check | mutmut in the container if reachable, else manual | mutmut directly (`os.fork` works) |
| Pyre installer build | allowed (see gates.md Publish) | skipped and recorded as `skipped: not Windows` |

Rules that apply in both:

- `$LOOP_ROOT` must be outside every git repo and survive a container recreate. In the container, `$TESTOUTPUTPATH` is bind-mounted from the host (default `D:\nornir-test-output`), which satisfies both; `/workspace` and `/tmp` do not. If neither `NORNIR_LOOP_ROOT` nor `TESTOUTPUTPATH` is set, stop and raise a decision instead of choosing a path inside a repo. Set `NORNIR_LOOP_ROOT` to the same folder on both sides if you want the ledger and reports shared between host and container runs.
- **One runner per checkout.** The container bind-mounts the host checkout, so a loop on each side would edit the same files. The ledger holds `runner: { environment, host, startedAt, heartbeatAt }`, refreshed every wake. At launch, if another runner's heartbeat is newer than `max(3 * Y minutes, 30 minutes)`, do not start; tell the user which runner holds it. A stopped loop clears `runner`.
- Prefer a **dedicated chat** for this loop so wake noise does not fill a human-work thread (same spirit as the one-runner rule).
- Never rely on user-level skills being present: `~/.cursor/skills*` is not mounted in the container. See Launch for the `loop` fallback.
- Commands in this skill are written once; translate path separators and shell syntax to the detected environment.
- In the container, do not change git configuration. If `git` reports `dubious ownership`, or `user.name`/`user.email` is unset, raise a decision (the user decides whether to set `safe.directory` or an identity) and do no commits until answered. Edits made by the host and by the container to the same bind mount can show mass mode or line-ending changes; record each repo's `git status --short` at launch as `launchDirty`, and if the whole tree looks modified, stop with a decision rather than guess which edits are the loop's.

## Scope

Any code in the umbrella repo (`$ROOT`) and in every `nornir-*` submodule plus `dm4` is in scope, on each submodule's currently checked-out branch. At the time of writing that is `dev` for buildmanager, imageregistration, pyre and shared; `master` for pools, volumemodel, volumecontroller, web and dm4; `main` for docker and builddashboard. At launch, the scout records each branch in the ledger and refuses to edit a submodule that is on a detached HEAD.

Do not edit generated files (`*.egg-info`, build output), comment code out to compile, push, or tag. Confirm the branch of the owning submodule before the first edit in it.

## Sync from the remote

**Launch** runs Sync once in the main session. On **later wakes**, the **scout** runs Sync (not main), so fetch/merge output stays out of the long-lived chat context. (Viking's loop Syncs in main every wake; Nornir keeps Sync in the scout on purpose.) Write results to `lastSync` and `syncSkips` in the ledger.

- For the umbrella and for each submodule: `git fetch origin`, then `git merge --ff-only @{u}` on the checked-out branch.
- Never run `git submodule update`. It would detach submodules at the umbrella-recorded pointers (see [Monorepo-submodule-changes](../../rules/Monorepo-submodule-changes.mdc)).
- Fast-forward only. If a repo cannot fast-forward (diverged history, or uncommitted local edits the incoming commits touch), leave it as it is, work from the current tree, and record `{repo, reason, date}` in `syncSkips`. Never stash, reset, rebase, force, or discard anything to make a pull succeed, and never push.
- A branch with no upstream is skipped silently and noted once in `syncSkips`.
- If the pull touches the `candidate`'s files, the scout re-checks the candidate before the implementer runs.

## Time box

If a wake passes about 60 minutes of work without a candidate clearing the gates, revert, add it to `deferred`, and end the wake.

## Launch

1. Detect the environment (see Environment) and check the one-runner rule. Read the `loop` skill once if it is available (`~/.cursor/skills-cursor/loop/SKILL.md`); it is not in the container, so there use the fallback below. Use the dynamic local schedule with sentinel `AGENT_LOOP_WAKE_nornir_improve`. Never arm a fixed repeating sleeper.
2. Create `$LOOP_ROOT`, `.loop/ledger.json`, and `STEERING.md` if missing. Run Sync from the remote.
3. Install any missing dev tools into the `$PY` environment: `ruff`, `vulture`, `radon`, `pylint`, `pyright`, `pyperf`, `crosshair-tool`, and in the container also `mutmut`. Never add them to a package `pyproject.toml` or to constraints files. In the container, installs live in the container and vanish on recreate, so do not treat that as a failure; the next launch reinstalls.
4. Mutation check mode: in the container, confirm `$PY -m mutmut --version` works and set `mutationMode: "native"`. On Windows, check that the `cursor-dev` container is reachable (needed for mutmut, see [gates.md](gates.md) Mutation check); if not, set `mutationMode: "manual"` and tell the user once.
5. Build `hotspots`, run the tiered test baseline, then run one wake immediately.
6. Arm the next wake with:

```json
{"prompt":"Follow skill nornir-improve-loop.","deadline":"<ISO-8601>","intervalMinutes":<Y>}
```

**Fallback when the `loop` skill is unavailable.** Arm one one-shot background wake per turn, with `notify_on_output` matching `^AGENT_LOOP_WAKE_nornir_improve`, and track its PID so it can be killed on stop:

```bash
sleep <seconds>
echo 'AGENT_LOOP_WAKE_nornir_improve {"prompt":"Follow skill nornir-improve-loop.","deadline":"<ISO-8601>","intervalMinutes":<Y>}'
```

On Windows PowerShell, use `Start-Sleep -Seconds <seconds>` and `Write-Output` with the same line. Never leave two sleepers armed.

## Each wake

The main session only schedules, relays, and talks to the user. Follow [main-session.md](main-session.md) — after launch, that file is the main session's only skill reading. All work runs in fresh `generalPurpose` subagents (models per Model routing), in the foreground, one at a time, so the main session's context does not grow. Give each subagent only the skill folder path and the ledger path; each role then opens only the files named for it above. **Never** paste wake history, open-decision lists, ledger JSON, or multi-paragraph "Context:" into the Task prompt. The ledger and `STEERING.md` are the memory.

1. Main: read the payload; do not re-read the `loop` skill or full `SKILL.md`. Record any decision answers from chat into the ledger. **Do not Sync in main** after launch.
2. **Scout** (runs Sync first; then reads SKILL.md, protected.md, categories.md, the ledger, `STEERING.md`; metadata-port.md on port wakes; reports.md and gates.md Test baseline only when a report or baseline is due). Prompt exactly: `Run the scout step of skill nornir-improve-loop. Skill folder: <path>. Ledger: <path>.` In order, the scout:
   1. runs Sync from the remote; writes `lastSync` / `syncSkips` / refreshes `runner.heartbeatAt`;
   2. reads `STEERING.md` and the ledger;
   3. stops on `stop`, the deadline, or `emptyWakes` reaching 3, writing the `final` report;
   4. when 24 hours have passed since `lastReportAt` (or `startedAt`), writes the `daily` report, rebuilds `hotspots`, re-runs the test baseline, and checks for reworked commits;
   5. on `pause`, ends the wake;
   6. otherwise picks one candidate and writes it to `candidate`: category (or port stage), package, files, a one-paragraph plan, and a risk level (`low` or `high`, per Model routing). It edits no production code. A protected or unmeasurable candidate becomes a proposal or decision, and the wake ends.
   It returns at most four lines: the candidate and its risk or why there is none; new decisions; report path if written; whether to stop.
3. **Implementer** (reads SKILL.md Scope and Time box, protected.md, gates.md, the ledger; metadata-port.md on port wakes). Prompt exactly: `Run the implement step of skill nornir-improve-loop for the candidate in the ledger. Skill folder: <path>. Ledger: <path>.` It runs the candidate through the gates, tests, mutation check, and benchmark when needed; commits in the owning submodule if green and bumps the umbrella pointer; publishes if due; clears `candidate`; and writes the ledger. If it finds the candidate riskier than the scout said, it stops without committing and sets the risk to `high`; the next wake re-runs it with the high-risk model. It returns at most four lines: commit sha and summary or why nothing passed, new decisions, whether a publish ran.
4. **Reviewer, high risk only** (reads protected.md, gates.md). After a high-risk commit: `Review commit <sha> in <submodule> against the gates in <skill folder>. Report problems only.` On a gate violation or likely defect, launch the implementer once more with `Follow-up after review of <sha>. Skill folder: <path>. Ledger: <path>.`, or revert the commit (and its pointer bump) when a fix is not clear. Record the outcome in the commit's ledger entry.
5. Main: post to the user only when there is a commit, a **new** decision (as a question), a publish, a compact notice, or a stop — otherwise stay silent (empty / reject / pause wakes re-arm with no status line unless the user asked for status). When arming: increment `wakeCount` and `wakesSinceCompact`; run compactness hygiene if due (see below). Arm one Y-minute sleep, or arm nothing when the scout said stop. Ignore stale sleeper completion notices (see main-session.md).
6. When the user asks for a report, launch the scout model to write a `requested` report right away; the loop keeps running. When the user asks to stop, kill the tracked sleeper PID, launch the scout model to write the `final` report, and arm nothing.

### Compactness hygiene

Ledger field `wakesSinceCompact` (separate from `wakeCount`) drives parent-chat hygiene so port/rotation odd-even is never reset. Parent increments `wakesSinceCompact` when arming each sleeper. Every **25** wakes: write a one-paragraph `compactSummary` (deadline, interval, last outcome, open decisions count, runner/sleeper ids if any); tell the user **once** to `/summarize` or start a fresh chat re-armed from the ledger + that summary; then reset `wakesSinceCompact` to 0. Between notices, empty wakes stay silent. Still ignore bare sleeper-completion noise after the wake was handled.

### Choosing between the port and the rotation

- Odd-numbered wakes (`wakeCount` odd) are **port wakes** when `metadata-port.md` has a stage that is open and not blocked on a decision. The scout takes the lowest open stage. Parent increments `wakeCount` once per armed wake; never reset it for compactness.
- Even-numbered wakes, and port wakes with no open stage, are **rotation wakes**: start at the category after `lastCategory` (see categories.md). Category 15 is the port, so it is only chosen by the odd-wake rule.
- A `focus:` or `avoid:` line in `STEERING.md` overrides this alternation.

## Steering

`$LOOP_ROOT/STEERING.md` is the user's; the loop reads it every wake and never edits it. Lines it understands:

- `focus: <path, package, category, or "port">`: search there first.
- `avoid: <path, pattern, package, or category>`: treat as protected for this run.
- `answer: <decision id> <choice>`: answers a pending decision.
- `pause`: skip work but keep arming wakes. `stop`: write the final report and stop.

Anything else is guidance the loop follows when it applies. Create the file with a short commented template at launch if it is missing.

## Decisions

When a candidate needs the user's call (two reasonable designs, a behavior change that might be wanted, a protected-area proposal that blocks other work, a port decision listed in metadata-port.md), do not guess. This follows [Design-choice-confirmation](../../rules/Design-choice-confirmation.mdc). Add it to `decisions` with an id, the question, and the options; raise the environment's decision alert (see Environment) with the question's first line; and move to another candidate. The main session posts the question in chat. An answer in chat or as an `answer:` line in `STEERING.md` is recorded in the ledger, and a later wake acts on it. Open decisions appear in every report.

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

The loop is long-running and not time-sensitive, so it spends fewer tokens instead of using fast-tier models: never route a step to a `-fast` variant. The user chose these models by writing them here. Pass them as the subagent's `model`. At launch, check each slug against the session's available subagent models. If one is missing, use the closest listed model of the same family and tier (never a fast variant), or omit `model` to use the parent's, and record it in `modelSubstitutions`. Context window size cannot be set; keep each subagent's input small.

- **Scout, reports, ledger upkeep:** `composer-2.5`
- **Low-risk implementer:** `claude-sonnet-5-5-high`. Dead weight (11), resolvable debt notes (12), hand-rolled helpers (7), and test-only wakes (14), when the change stays inside one package and away from protected areas.
- **High-risk implementer:** `claude-opus-5-5-high`. Everything else, plus any low-risk category that touches a shared package (`nornir-shared`, `nornir-pools`), more than one package, a numeric dtype, a file next to a protected area, the `volumemanager` package, or any metadata-port stage.
- **Reviewer:** `gpt-5.5-medium`. Only after high-risk commits, so the second opinion comes from a different model family.

The main session can run on Auto or any inexpensive model that is not a fast variant; it does no code work. After launch it follows [main-session.md](main-session.md) only (model table is duplicated there so main never re-opens this file). Record the model used for each step in the commit's ledger entry.
