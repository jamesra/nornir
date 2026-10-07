# Reports and learning from your changes

Read by whichever subagent writes a report (the scout model), and by the main session when it relays one.

## Reports

Folder: `$LOOP_ROOT` (see SKILL.md Environment; create it if missing). It is outside every repo; never `git add` it and never write reports inside a repo.

File name: `YYYY-MM-DD_HHmm_<kind>.md` in America/Los_Angeles time, where `<kind>` is `final` (loop stopped), `daily` (24 hours since `lastReportAt`), or `requested` (user asked). Never overwrite an existing file; add `_2` if the name is taken.

When to write:

- **Final:** when the loop stops for any reason.
- **Daily:** on the first wake at least 24 hours after `lastReportAt` (or `startedAt` if no report yet).
- **Requested:** whenever the user asks, without waiting for the next wake.

An interim (`daily` or `requested`) report covers the period since `lastReportAt`. A `final` report covers the whole run. After writing, set `lastReportAt`, append the path to `reports`, and post the path and a two-line summary in chat.

Keep each report reviewable in a few minutes:

1. **Totals:** the `environment` the loop ran in (and `$LOOP_ROOT`), period covered, wakes, commits (and how many were port commits), total production line delta, total test line delta, publishes with the Pyre installer builds they triggered, commit count per category and per package, and any model substitutions.
2. **Metadata port:** current `portStage`, what each completed stage measured (parity result per fixture volume, shadow-write cost per container, database size versus XML, load and save timings, concurrency and network-share test status), what the next stage needs, and any stage blocked on a decision.
3. **Commits, riskiest first:** every commit in the period, sorted by risk. Weigh shared-package or cross-package reach, port commits, latent-bug fixes, performance changes, closeness to protected areas, and size. One line per commit: short sha (and the umbrella pointer-bump sha), category or stage, package, summary, line delta, and the models that worked on it; performance commits also show the before/after headline number, bug fixes show the regression-test failure count against the old code, and changed-test commits show surviving mutants and the mutation mode. When a commit carries a notable risk, add one indented line saying what it is and what to check. Commits with no notable risk get no extra line.
4. **Open decisions:** each pending entry in `decisions` with its id and options.
5. **Reworked:** loop commits you reverted or rewrote, and the pattern now avoided.
6. **Proposals:** each proposal in full, protected areas first, then port proposals, then unmeasurable performance work, then deferred refactors.
7. **Follow-ups:**
   - **Unpushed work:** per package, the loop commits not yet on the remote, and the push order (submodules first, then the umbrella; see gates.md Commit);
   - `git submodule status` lines with a `+` prefix and whether the loop or the user caused them;
   - Pyre installer builds and their results, and whether a publish is owed;
   - `baselineFailures` and `flaky` tests, tiers that were skipped and why, and `syncSkips` (repos that could not fast-forward and why);
   - categories that came up empty, and the current top five hotspots per package that has any.

## Learning from your changes

With each daily report, check every loop commit (found by the `Improvement-Loop:` trailer, searched in each submodule with `git log --grep "Improvement-Loop:"` and in the umbrella) from the last 14 days. A commit that was reverted, or whose changed lines a non-loop commit has since rewritten, goes in `reworked`. Add its pattern (category, file, kind of change) to `rejected` so later wakes avoid repeating it, and flag it in the report. A performance change that a later measurement shows slower than its recorded benchmark also goes in `reworked`, and its entry is appended to `.cursor/issue-handoff/optimization-loop-rejections.md`.
