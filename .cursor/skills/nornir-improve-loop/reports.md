# Reports and learning from your changes

Read by whichever subagent writes a report (the scout model), and by the main session when it relays one.

## Reports

Folder: `$LOOP_ROOT` (SKILL.md Environment; create if missing). It is outside every repo; never `git add` it or write reports inside a repo.

File name: `YYYY-MM-DD_HHmm_<kind>.md` in America/Los_Angeles time. Never overwrite an existing file; add `_2` if the name is taken. Kinds:

- `final`: when the loop stops for any reason; covers the whole run.
- `daily`: on the first wake at least 24 hours after `lastReportAt` (or `startedAt` if no report yet).
- `requested`: whenever the user asks, without waiting for the next wake.

Interim (`daily`, `requested`) reports cover the period since `lastReportAt`. After writing, set `lastReportAt`, append the path to `reports`, and post the path and a two-line summary in chat.

## Cumulative list

`$LOOP_ROOT/CHANGES-BY-REGION.md` is the running total across every run (dated reports cover one run), grouped by package then code region, for the user to review. Update it in place whenever a report is written; do not start a new file per run: add each commit since its **As of** line under the matching region with its label (Fix, Faster, Refactor, Cleanup, Tests, Port), one plain-English line, and the short sha; add new fixes to "Review these first"; move reverted commits to "Reverted and rejected"; refresh **As of** and "Open items", and regenerate the "At a glance" table from `git log --grep "Improvement-Loop:"` in each repo (per package and label) instead of adjusting numbers by hand.

Name categories in words wherever a person reads them (reports, chat, `CHANGES-BY-REGION.md`): "bug fix", "dead code", "untested code", not "cat 13". Numbers appear only in the `Improvement-Loop:` trailer and ledger fields.

Keep each report reviewable in a few minutes:

1. **Totals** (counts generated from git and the ledger, never typed): `environment` (and `$LOOP_ROOT`), period covered, wakes, commits (how many were port commits), total production and test line deltas, publishes with the Pyre installer builds they triggered, commit count per category and per package, any model substitutions.
2. **Metadata port:** current `portStage`; what each completed stage measured (parity result per fixture volume, shadow-write cost per container, database size versus XML, load and save timings, concurrency and network-share test status); what the next stage needs; any stage blocked on a decision.
3. **Commits, riskiest first:** every commit in the period, sorted by risk (weigh shared-package or cross-package reach, port commits, latent-bug fixes, performance changes, closeness to protected areas, size). One line each: short sha (and umbrella pointer-bump sha), category or stage, package, summary, line delta, models that worked on it; performance commits add the before/after headline number, bug fixes the regression-test failure count against the old code, changed-test commits the surviving mutants and mutation mode. A commit with a notable risk gets one indented line saying what it is and what to check; others get none.
4. **Open decisions:** each pending `decisions` entry with its id and options.
5. **Reworked:** loop commits you reverted or rewrote, and the pattern now avoided.
6. **Proposals:** each in full: protected areas first, then port proposals, unmeasurable performance work, deferred refactors.
7. **Follow-ups:**
   - **Unpushed work:** per package, loop commits not yet on the remote, and the push order (submodules first, then the umbrella; see gates.md "Before commit and commit");
   - `git submodule status` lines with a `+` prefix, and whether the loop or the user caused them;
   - Pyre installer builds and results, and whether a publish is owed;
   - `baselineFailures` and `flaky` tests, skipped tiers and why, and `syncSkips` (repos that could not fast-forward and why);
   - categories that came up empty, and the current top five hotspots per package that has any;
   - `mirrorPending` twins to update by hand, and new bug patterns in `$LOOP_ROOT/BUG-PATTERNS.md` to fold into categories.md.

## Learning from your changes

With each daily report, check every loop commit from the last 14 days (found by the `Improvement-Loop:` trailer: `git log --grep "Improvement-Loop:"` in each submodule and in the umbrella). A commit that was reverted, or whose changed lines a non-loop commit has since rewritten, goes in `reworked`; add its pattern (category, file, kind of change) to `rejected` so later wakes avoid it, and flag it in the report. A performance change that a later measurement shows slower than its recorded benchmark also goes in `reworked`, with its entry appended to `.cursor/issue-handoff/optimization-loop-rejections.md`.
