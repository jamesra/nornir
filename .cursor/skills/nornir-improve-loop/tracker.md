# The nornir-review tracker

`jamesra/nornir-review` is the private issue tracker for Nornir bugs and performance findings ([nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md)). The loop reads it as a source of candidates and files there what it finds but cannot fix. Read by the scout (Snapshot, Candidates) and by whichever subagent files, comments on, or resolves an issue. Filing, commenting, and labelling are the only GitHub writes the loop makes; it still never pushes, tags, or opens PRs.

## Access

At launch, run `gh auth status` and `gh repo view jamesra/nornir-review --json name`. Both succeed: set ledger `tracker` to `{ "mode": "gh", "checkedAt": "<ISO>" }`. Otherwise set `mode` to `none` with the reason (no `gh`, not authenticated, no access; in the container, `GITHUB_TOKEN`/`GH_TOKEN` unset in `.env.cursor-worker`), tell the user once, and keep going: in `none` mode the loop does everything below except the `gh` calls, keeps each item in the ledger with `issue: null`, and the first run with `mode: gh` files that backlog (Filing, the per-wake cap applies). A `gh` call that fails mid-run (network, rate limit) leaves the item unfiled for a later wake; it does not switch the mode or end the wake.

If the `improve-loop` label is missing, create it once: `gh label create improve-loop --repo jamesra/nornir-review --color 1d76db --description "Filed or updated by nornir-improve-loop"`. Use only labels that already exist otherwise; never create severity, type, status, or `repo:` labels.

## Snapshot

At launch and with each daily report, the scout writes the open issues to `$LOOP_ROOT/.loop/tracker-open.json` (not the ledger, which stays small):

```bash
gh issue list --repo jamesra/nornir-review --state open --limit 500 --json number,title,labels,updatedAt
```

Wakes read the snapshot, not the live tracker; only the dedupe search and the resolve step below query GitHub during a wake.

## Candidates from the tracker

When a wake's category or `focus:` matches an open issue's type and `repo:<package>` label (`bug` -> bug fixes, `perf` -> the performance categories, `debt` -> the nearest refactoring category, `parity` -> bug fixes, usually a proposal under Stable-path-output-parity), the scout prefers it over a fresh search, highest severity first (P0 -> P3). Skip issues labelled `status:blocked`, `wontfix`, or `status:wontfix`, and issues the loop filed itself as not fixable here unless the stated reason no longer holds (fixtures now present, protected area since released).

An issue is a hypothesis, not a diagnosis: the gates.md bug-fix procedure applies unchanged. Before planning, check whether the code moved since the issue was written: if its Details carry a `Found at` sha, run `git -C <package> log --oneline <sha>..HEAD -- <path>`; if they do not, compare the cited lines against the current file. Moved code goes back to "reproduce first", and a finding that no longer reproduces is commented on (Commenting) and left for the user to close.

Record the issue number in `candidate.issue` and, after a commit, in the commit's ledger entry.

## Version info

Every issue body and comment the loop writes carries the state of the code it describes:

- **Owning package:** distribution version (`$PY -c "import importlib.metadata as m; print(m.version('<distribution>'))"`, falling back to `version` in its `pyproject.toml`), branch, and short `HEAD` sha (`git -C <package> rev-parse --abbrev-ref HEAD`, `git -C <package> rev-parse --short HEAD`).
- **Umbrella:** branch and short `HEAD` sha, plus the umbrella's `VERSION` file when present.
- **Dirty:** `yes` if `git -C <package> status --short -- <paths>` lists any cited file (the line numbers may then not match `HEAD`), else `no`.
- **Environment and runner:** ledger `environment`, the run's `startedAt`, and the role and model writing the post.

If a value cannot be read, write `unknown` and why; never leave the field out.

## Filing

File an issue for:

- a bug the loop could not reproduce on this machine, or could not fix because it is in a protected area, needs a GUI, GPU, or live service, or would change user-visible behavior (gates.md Bug fixes steps 1, 4, and 7);
- a performance problem with no feasible benchmark in one wake (gates.md Performance step 7);
- a parity or protected-area proposal (categories.md Proposals);
- a sibling-sweep pattern (gates.md Bug fixes step 8): **one** issue per pattern listing every hit as `path:line`, not one per hit.

Do not file refactoring deferrals, `rejected` entries (contrived input, dead or test-only code), port-stage decisions, or anything that needs the user's choice: those stay in the ledger and the reports, and decisions are asked in chat.

Before filing, dedupe: search the tracker (`gh issue list --repo jamesra/nornir-review --state all --search "<file name or symbol> in:title,body" --json number,title,state,labels --limit 10`) and `.cursor/nornir-bug-review-master.md`. An open match gets a comment instead (Commenting). A closed `wontfix` match is not re-filed unless the code it measured has changed since; add the item to `rejected` citing the issue. A closed `fixed` match that the loop can reproduce again is filed as a new issue linking the old one.

At most **three** new issues per wake; the rest keep `issue: null` and are filed on later wakes, oldest first.

Title: `[Loop] <P0|P1|P2|P3> - <one-line symptom>`. Labels: severity, type (`bug`, `perf`, `parity`, `debt`), `repo:<package>` (`repo:cross-cutting` for several), `status:open` (`status:confirmed` only when the loop reproduced it), and `improve-loop`. Severity follows the master-list legend: P0 data loss or wrong science, P1 silent wrong output, P2 performance or operational pain, P3 maintainability.

Body, in the tracker's existing layout (write it to a temp file under `$LOOP_ROOT/.loop/` and pass `--body-file`, which avoids shell quoting on both platforms):

```markdown
## Concern

<what goes wrong, for whom, and when; the likely fix>

## Evidence

<what the loop ran and saw: test name and failure, benchmark numbers, the reason it could not reproduce or fix here>

## Details

| Field | Value |
|-------|-------|
| Location | `<package>/<path>:<lines>` |
| Owning submodule | `<package>` |
| Severity | <P0-P3> |
| Type | `<bug|perf|parity|debt>` |
| Found at | `<package>` <version> on `<branch>` @ `<sha>`; umbrella `<branch>` @ `<sha>` (VERSION <x>); dirty: <yes|no> |
| Found by | nornir-improve-loop, run <startedAt>, wake <wakeCount>, <environment>; <role>, <model> |
| Ledger | `<proposals|deferred|rejected>` entry `<title or path>` |

---
_Filed by nornir-improve-loop (<role>, <model>)_
```

Store the returned number in the ledger item's `issue` field and append `{ number, title, package, action: "filed", at }` to `trackerIssues`.

## Commenting

On an existing issue, comment only with something new: a reproduction, a measurement, a failed attempt and why, or the observation that the cited code has changed. Start the comment with the Version info line (`Checked at ...`, same fields as `Found at`) and end it with the same footer. Never edit or retitle someone else's issue body, and never remove labels the loop did not add. Append `{ number, action: "commented", at }` to `trackerIssues`.

## Resolving

A loop commit that fixes a tracker issue names it in the commit message (`(nornir-review#<n>)`) and the implementer comments with the commit sha, the regression test, and its failure count against the old code, then adds `status:fixed`. Loop commits are not pushed, so **do not close** the issue yet: the scout closes it, with a one-line comment naming the remote branch, at the first Sync where `git -C <package> branch -r --contains <sha>` lists `origin/<branch>`. A loop commit that is later reverted (reports.md, Learning from your changes) removes `status:fixed` and comments with the revert sha.

Updating `.cursor/nornir-bug-review-master.md` stays with the user or a review session; the loop only reports which issues changed.
