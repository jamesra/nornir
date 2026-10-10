# Main session playbook (Claude Code, Nornir)

After launch, this is the only skill file the main session reads. Do not open `SKILL.md` or the shared `gates.md`, `categories.md`, `metadata-port.md`, `reports.md` in the main session; subagents load those.

Goal: keep the main context nearly flat across dozens of wakes. Main only schedules, relays, and talks to the user: no Sync, no code, no git exploration.

## Paths

- Skill folder: `D:\src\git\nornir\.claude\skills\nornir-improve-loop`
- Shared policy folder: `D:\src\git\nornir\.cursor\skills\nornir-improve-loop`
- Ledger: from the wake payload (default `D:\src\git\Nornir Automatic Improvement Reports\.loop\ledger.json`, or under `$env:NORNIR_LOOP_ROOT`)

## Agent calls

`Agent` with `subagent_type: "general-purpose"`, `run_in_background: false`, no `effort`. Prompt is one sentence plus two paths, nothing else.

| Role | `model` |
|------|---------|
| Scout / reports | `sonnet` |
| Low-risk implementer (cats 11, 12, 7, 14; one package; away from protected) | `sonnet` |
| High-risk implementer (everything else, `nornir-shared`/`nornir-pools`, multi-package, numeric dtype, `volumemanager`, port stages) | `opus` |
| Reviewer (high-risk commits only) | `fable` |

If a model is unavailable, use the closest same-family tier and record `modelSubstitutions` in the ledger.

## On every `AGENT_LOOP_WAKE_nornir_improve`

1. Parse the payload for the ledger path. Record any chat answers into the ledger `decisions[].answer`. (No stale-sleeper check; scheduling is via `ScheduleWakeup`.)
2. Launch the scout: `Run the scout step of skill nornir-improve-loop (Claude Code port). Skill folder: <skill folder>. Ledger: <ledger>.`
3. If the scout wrote a candidate and did not say stop/pause, launch the implementer: `Run the implement step of skill nornir-improve-loop (Claude Code port) for the candidate in the ledger. Skill folder: <skill folder>. Ledger: <ledger>.` Choose the model from the scout's `risk: low|high` and the table above.
4. If the implementer committed with risk `high`, launch the reviewer: `Review commit <sha> in <submodule> against the gates in <shared folder>. Report problems only.` On problems, one implementer pass: `Follow-up after review of <sha>. Skill folder: <skill folder>. Ledger: <ledger>.`
5. Tell the user in at most two sentences about a commit, a **new** decision, a publish (include the push-submodules-before-umbrella reminder), or a stop. Stay silent on empty, reject, and pause wakes unless the user asked for status.
6. Before arming: increment `wakeCount` (never reset) and `wakesSinceCompact` in the ledger, and refresh `runner.heartbeatAt`. If `wakesSinceCompact >= 25`, write a one-paragraph `compactSummary` (deadline, interval, last outcome, open decisions count), tell the user **once** to start a fresh session re-armed from the ledger, then reset `wakesSinceCompact` to 0.
7. Arm exactly one `ScheduleWakeup` for Y minutes with the same wake prompt (`noop: true` for empty/reject/pause wakes, `false` otherwise). On stop (user, deadline, three empty wakes), call `ScheduleWakeup` with `stop: true` or arm nothing, and clear `runner` in the ledger.

## Forbidden in main (these burn context)

- Running Sync from the remote (the scout does it after launch).
- Re-reading `SKILL.md` or any shared policy file after launch.
- Multi-paragraph "Context:", wake history, or ledger JSON in Agent prompts.
- Restating open decisions every wake unless a **new** one appeared.
- Narrating empty, reject, or pause wakes.
- Any production-code edit, test run, or commit from the main session.
- `AskUserQuestion` or plan mode: the loop is unattended; questions go through the ledger `decisions` and a Windows toast.
