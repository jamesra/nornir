# Main-session wake playbook

Read **only this file** on wakes after launch. Do not open full `SKILL.md`, `gates.md`, `categories.md`, `metadata-port.md`, or `reports.md` in the main session. Subagents load those.

Goal: keep the main chat context nearly flat across dozens of wakes. The main session only schedules, relays, and talks to the user — no Sync, no code, no git exploration. Prefer a **dedicated chat** for this loop.

## Model routing (do not re-open SKILL.md for this)

Never pass a `-fast` model. If a listed slug is unavailable, use the closest same-family non-fast tier (or omit `model`), and record `modelSubstitutions` in the ledger.

| Role | Model |
|------|--------|
| Scout / reports | `composer-2.5` |
| Low-risk implementer | `claude-sonnet-5-5-high` (cats 11, 12, 7, 14; one package; away from protected) |
| High-risk implementer | `claude-opus-5-5-high` (everything else, shared packages, multi-package, port stages) |
| Reviewer (high-risk commits only) | `gpt-5.5-medium` |

## On every `AGENT_LOOP_WAKE_nornir_improve`

1. If the notifying shell id is not `runner.sleeperShellId` in the ledger, reply one short "stale sleeper" line and stop (no tools).
2. Paste any new `answer:` / decision replies from chat into the ledger (`decisions[].answer`) with a tiny shell/python one-liner if needed. Do not re-read all of `STEERING.md` in main; the scout reads it.
3. Launch **scout** only (`generalPurpose`, foreground), with this exact prompt (fill paths):

   `Run the scout step of skill nornir-improve-loop. Skill folder: <path>. Ledger: <path>.`

   No "Context:" dump. No wake-history paraphrase. No file contents pasted into the Task prompt — only the two paths. Ledger + STEERING are authoritative.
4. If scout returns a candidate and does not say stop/pause: launch **implementer** with:

   `Run the implement step of skill nornir-improve-loop for the candidate in the ledger. Skill folder: <path>. Ledger: <path>.`

   Pick low- vs high-risk from the scout's four-line return (`risk: low|high`) and the table above.
5. If the commit was high-risk: launch **reviewer** with:

   `Review commit <sha> in <submodule> against the gates in <skill folder>. Report problems only.`

   On gaps, one follow-up implementer prompt: `Follow-up after review of <sha>. Skill folder: <path>. Ledger: <path>.` — still no history dump.
6. User-facing reply: **silent** on empty / reject / pause wakes (no status line unless the user asked for status). One or two sentences only for a commit, a **new** decision question, a publish, or a stop. No recap of prior wakes or open-decision lists.
7. Before arming: increment `wakeCount` (port/rotation; never reset for hygiene) and `wakesSinceCompact` in the ledger. If `wakesSinceCompact >= 25`, write a one-paragraph `compactSummary` (deadline, interval, last outcome, open decisions count, runner/sleeper ids), tell the user **once** to `/summarize` or start a fresh chat re-armed from the ledger + that summary, then reset `wakesSinceCompact` to 0.
8. Arm exactly one Y-minute sleeper; write `runner.sleeperPid` / `sleeperShellId` / `heartbeatAt` to the ledger. When the scout said stop, arm nothing.

## Forbidden in main (context burns)

- Running Sync from the remote (scout does sync — Nornir divergence from Viking, where Sync was in main; Viking improve now Syncs in the orchestrator too).
- Re-reading `SKILL.md` or any other skill file after launch.
- Pasting multi-paragraph "Context:", wake history, or ledger JSON into Task prompts.
- Tooling on stale sleeper completion notices.
- Restating open decision lists every wake unless a **new** decision appeared.
- Narrating empty / reject / pause wakes.
- Any production-code edit, test run, or commit from the main session.

## Launch only (not each wake)

Launch still does environment detect, ledger/STEERING create, one Sync, tool install, baseline, first wake — per `SKILL.md` Launch. After that, use this playbook.
