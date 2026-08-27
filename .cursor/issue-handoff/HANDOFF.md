# Nornir bug-review issue handoff

Self-contained package for filing the Nornir code-review findings as GitHub
issues. You need no context from the conversation that produced it — everything
required is in this directory.

## What this package does

A review pass over the Nornir monorepo catalogued **208 bug / performance /
parity / debt findings** into `.cursor/nornir-bug-review-master.md`. This package
turns that markdown into **one GitHub issue per finding** (207 filed; one entry
is a known duplicate and is skipped by default) inside a single **new private
repository**, default name `nornir-review`.

Each issue carries:

- a title of the form `[C03-B001] P0 - <concern>` (truncated to GitHub's 256-char limit),
- labels for severity (`P0`–`P3`), type (`bug`/`perf`/`parity`/`debt`), review
  chunk (`chunk-03`), owning submodule (`repo:nornir-imageregistration`),
  verification status (`status:confirmed` / `status:open`) and, where the review
  assigned one, fix-order wave (`wave-1`),
- a body with the concern, the evidence, a metadata table naming the owning
  submodule, and — most importantly — a **verification banner** at the top.

### Why a private repo, and not the public submodule repos

All six Nornir submodules point at public `github.com/jamesra/*` repositories.
**GitHub has no per-issue privacy**: an issue in a public repo is public, and
there is no visibility switch for individual issues. Filing 208 findings there
would publish the entire list of suspected defects, including 194 that have not
been reproduced. So everything goes into **one new private repo** instead, and
each issue names its owning submodule via the `repo:*` label and the
`Owning submodule` row in the body.

### Why the verification banner matters

Only **14** findings are `status:confirmed` (the cited line was re-read and
verified). The other **194** are `status:open` — produced by static reading, never
reproduced. Every `status:open` issue body opens with a blockquote saying so and
asking for a failing-then-passing test before the diagnosis is trusted. Do not
strip that banner; it is the guard against someone treating an unreproduced
reading as a diagnosed bug.

## Where this lives

Inside the container where the package was built, the monorepo is `/workspace`.
On your Windows host that same checkout is `D:\src\git\nornir`, so:

| Container path | Your host path |
|----------------|----------------|
| `/workspace/.cursor/issue-handoff/` | `D:\src\git\nornir\.cursor\issue-handoff\` |
| `/workspace/.cursor/nornir-bug-review-master.md` | `D:\src\git\nornir\.cursor\nornir-bug-review-master.md` |

Run every command below from `D:\src\git\nornir\.cursor\issue-handoff`.

## Prerequisites

1. **Python 3.9+** on PATH (`python --version`). Standard library only; nothing to install.
2. **GitHub CLI** installed (`gh --version`) — https://cli.github.com/
3. **Authenticated with `repo` scope**:

```powershell
gh auth status          # must report "Logged in to github.com"
gh auth refresh -s repo # only if the repo scope is missing
```

`GH_TOKEN` / `GITHUB_TOKEN` in the environment also works; the token needs the
`repo` scope so it can create a private repository and its issues.

## Run these commands in order

```powershell
cd D:\src\git\nornir\.cursor\issue-handoff

# 1. Dry run. Touches nothing, needs no gh and no credentials.
python create_issues.py --dry-run

# 2. Create the private repo and all 33 labels, then stop.
python create_issues.py --setup-only

# 3. Smoke test: file the three worst findings and eyeball them on GitHub.
python create_issues.py --limit 3

# 4. Full run. Resumable; re-run the same command after any interruption.
python create_issues.py
```

Add `--repo <name>` to any of these if `nornir-review` is taken, or
`--repo owner/name` to file into an organisation. Use the **same** `--repo` value
for every step of a run.

### Expected counts (check these)

| Check | Expected |
|-------|----------|
| Findings parsed from the master list | 208 |
| Issues filed (208 minus the `C00-P001` duplicate) | **207** |
| Severity split of filed issues | P0 = 9, P1 = 63, P2 = 99, P3 = 36 |
| Type split | bug 116, perf 59, parity 15, debt 18 |
| Owning submodules | nornir-imageregistration 101, nornir-buildmanager 62, nornir-pyre 19, nornir-shared 15, nornir-pools 9, dm4 1, cross-cutting 1 |
| Verification status | `status:confirmed` 14, `status:open` 194 (193 filed + the skipped duplicate is `open`) |
| Labels created | 33 |

(The P0 total in the master list is 10; one P0, `C00-P001`, is a duplicate of
`C01-P001` and is not filed. Pass `--include-duplicates` if you want all 208.)

Verify on GitHub after the full run:

```powershell
gh issue list --repo <owner>/nornir-review --state all --limit 500 | Measure-Object -Line   # expect 207
gh issue list --repo <owner>/nornir-review --label P0 --state all                            # expect 9
gh issue list --repo <owner>/nornir-review --label status:confirmed --state all --limit 50    # expect 14
```

## Interruptions, resuming and rate limits

Issues are filed **worst-first** (P0, then P1, P2, P3; alphabetical by finding ID
within a severity), so an interrupted run always leaves the most serious findings
tracked.

`created_issues.json` is the ledger. Before each create call the script writes a
`pending` marker for that finding, and replaces it with the issue URL immediately
afterwards, using an atomic file replace. Consequences:

- **To resume, re-run the exact same command.** Anything already in the ledger is
  skipped.
- If the process was killed between the call and the recorded result, the next
  run *reconciles* the `pending` entry by asking GitHub whether an issue whose
  title starts with `[<finding-id>]` already exists — recording it if so,
  re-queueing it if not. This is why the run cannot double-file or silently drop
  a finding.
- **Do not delete `created_issues.json`** to "start over" unless you also delete
  the repo; deleting it re-files everything.

GitHub throttles content creation to roughly **80 creations per minute** and
**500 per hour**, and additionally applies an unpublished "secondary rate limit"
to bursts. The default `--delay 2.5` (seconds between issues) gives ~24/min, so
207 issues take about **9–10 minutes**. That is deliberately under the per-hour
cap; do not lower it much. On a rate-limit or 5xx response the script retries the
same issue up to 4 times with 15s → 30s → 60s backoff (`--retries`, `--backoff`).
If it still fails it stops, prints the finding ID, and tells you to re-run.

## Useful options

| Option | Effect |
|--------|--------|
| `--dry-run` | Print the plan. Never invokes `gh`, never touches the network. |
| `--setup-only` | Create the repo and labels, file no issues. |
| `--limit N` | File at most N issues this run (composes with the ledger, so `--limit 20` four times files 80 distinct issues). |
| `--severity P0 P1` | Only these severities. |
| `--chunk 03 05` | Only these review chunks (`3` and `03` both work). |
| `--delay S` | Seconds between creations (default 2.5). |
| `--retries N`, `--backoff S` | Transient-error retry budget and first backoff. |
| `--include-duplicates` | Also file `C00-P001`, filed as a duplicate of `C01-P001`. |
| `--repo NAME` / `--repo owner/NAME` | Target repository. |

## Regenerating findings.json

`findings.json` is generated from the master list and is already current. If the
master list changes, regenerate before filing:

```powershell
python extract_findings.py
```

It prints the parsed count and the severity/type/repo/status breakdown — compare
against the expected counts above. It only reads the master list; it never writes
to it. New findings added later are filed by simply re-running
`create_issues.py`, since the ledger skips everything already filed.

## Optional post-step: link the issues back into the master list

After a successful full run you can stamp the issue numbers into the master list
so the narrative document and the tracker stay linked. This **modifies**
`.cursor/nornir-bug-review-master.md`, so commit or stash first.

```powershell
python link_issues_back.py            # preview only, writes nothing
python link_issues_back.py --write    # add an "Issue" column to each finding table
```

It appends one `Issue` column to every finding table, holding `[#42](url)` for
each filed finding and `-` for anything unfiled. It is idempotent (a second
`--write` updates the column instead of adding another) and it never alters the
existing cell text. It was tested against a copy of the master list, not the real
one — preview first.

## Troubleshooting

**`gh CLI not found on PATH`** — install the GitHub CLI and reopen the shell.
`--dry-run` is the only mode that works without it.

**`gh is installed but not authenticated`** — run `gh auth login` (choose
github.com, HTTPS) or export `GH_TOKEN`.

**Repo created but labels or issues fail with 403 / "Resource not accessible"** —
the token lacks the `repo` scope. `gh auth refresh -s repo`, then re-run; the
ledger makes the retry safe.

**`could not create <slug>` / name already taken** — pick another name and use it
consistently: `python create_issues.py --repo nornir-review-2 --setup-only`, then
the same `--repo` for the real run. If a *previous* attempt of yours created the
repo, that is fine: the script detects an existing repo and continues.

**`n label(s) could not be created`** — the script stops here on purpose, because
`gh issue create` fails outright on a label that does not exist. Fix the cause
(usually scope or a name collision with a pre-existing label of a different
colour) and re-run `--setup-only`.

**Secondary rate limit** — the script backs off and retries automatically. If it
gives up, wait a few minutes and re-run the same command; already-filed findings
are skipped. Raising `--delay` to 5 halves the request rate.

**A run died halfway / Ctrl-C** — just re-run the same command. Expect a line like
`reconciling 1 pending entr(ies) from a previous run`. Exit code 130 means you
interrupted it; the ledger is consistent.

**Duplicate issues on GitHub** — should not happen, but if you re-ran with a
deleted ledger, find them with
`gh issue list --repo <slug> --state all --limit 500 --json number,title` and
close the extras; titles start with the unique finding ID.

## File inventory

| File | Purpose |
|------|---------|
| `HANDOFF.md` | This document. Start here. |
| `extract_findings.py` | Parses `.cursor/nornir-bug-review-master.md` into `findings.json`. Read-only w.r.t. the master list. |
| `findings.json` | The 208 findings as structured records (id, chunk, severity, type, location, concern, evidence, status, owning repo, wave, duplicate flag). Generated; current. |
| `create_issues.py` | Creates the private repo, the labels, and one issue per finding. Resumable. The script you actually run. |
| `link_issues_back.py` | Optional post-step: writes issue numbers back into the master list. |
| `created_issues.json` | **Not shipped** — created by the first real run. The ledger of finding ID → issue URL. Keep it; it is what makes resuming safe. |

## What you must decide or supply

- **The GitHub credential.** Nothing in this package contains a token; the
  package was built in a container with no GitHub access at all.
- **The repository name and owner.** Default `nornir-review` under your own
  account. Use `--repo owner/name` for an organisation, and keep the value
  identical across `--setup-only`, smoke test and full run.
- **Whether to file the duplicate** `C00-P001` (`--include-duplicates`).
- **Whether to run the optional link-back step**, which is the only thing here
  that modifies the master list.
