---
name: nornir-commit-push
description: >-
  Commit, and optionally push, work across the Nornir umbrella and its submodules
  in the right order. Use when the user says "commit and push everything
  (including submodules)", "commit but don't push", "update submodules to the
  latest pushed version", "bump the version and tag", or "check all repos and
  branches for uncommitted or unmerged work" (stray cursor/* branches,
  worktrees, unpushed commits).
---

# Commit and push across the umbrella

Policy lives in the **Shared-checkout-safety** (commit only your own files) and
**Monorepo-submodule-changes** (submodule commit, then pointer bump) rules. This is the procedure:
push submodules before the umbrella, and verify the remote has each SHA before recording it.

## Pick the mode first

| User said | Mode | Stop after |
|-----------|------|-----------|
| "commit", "don't push", "commit locally" | Commit only | Step 4; report what is unpushed |
| "commit and push (everything)" | Full | Step 9 |
| "update submodules to latest pushed version" | Pointer refresh | See `update-submodules.ps1` below |
| "bump the version and tag" | Release | Full, plus [nornir-bump-version](../nornir-bump-version/SKILL.md) |
| "check for uncommitted / unmerged / lost work" | Audit | Report only; change nothing |

"Don't push" holds for the rest of the task, including follow-ups, until the user says otherwise.

## Repos, branches, CI

Verified against `.gitmodules` (`branch =`), `git -C <sub> rev-parse --abbrev-ref HEAD` / `@{u}`,
and `git ls-remote --symref origin HEAD`. All remotes are `https://github.com/jamesra/<repo>`.

| Repo (path) | Work branch (`.gitmodules`) | GitHub default | Package CI workflow |
|-------------|-----------------------------|----------------|---------------------|
| umbrella (`.`) | `dev` | `master` | `docs.yml`, `unit-tests.yml`, `pyre-windows-release.yml` |
| `nornir-shared` | `dev` | `master` | `python-app.yml` |
| `dm4` | `master` | `master` | none |
| `nornir-pools` | `master` | `master` | `python-app.yml` |
| `nornir-imageregistration` | `dev` | `master` | `python-app.yml` |
| `nornir-volumemodel` | `master` | `master` | none |
| `nornir-volumecontroller` | `master` | `master` | none |
| `nornir-web` | `master` | `master` | none |
| `nornir-buildmanager` | `dev` | `master` | `python-app.yml` |
| `nornir-pyre` | `dev` | `master` | `python-app.yml` |
| `nornir-builddashboard` | `main` | `main` | none |
| `nornir-docker` | `main` | `main` | none |

Push to the work branch. Do not merge `dev` into `master` unless asked.

## Push order (dependencies first)

From each package's `pyproject.toml` / `setup.py` dependencies and imports:

1. `nornir-shared` (no nornir deps)
2. `dm4` (no deps; imported by buildmanager's dm4 importer)
3. `nornir-pools` (shared)
4. `nornir-imageregistration` (shared, pools)
5. `nornir-volumemodel` (shared, imageregistration), then `nornir-volumecontroller` (imageregistration, volumemodel), `nornir-web`
6. `nornir-buildmanager` (shared, pools, imageregistration, dm4)
7. `nornir-pyre` (shared, pools, imageregistration; `requirements-qt.txt` pins buildmanager for the installer)
8. `nornir-builddashboard` (optional `nornir_shared`), `nornir-docker` (builds images from the packages)
9. umbrella, last

## Procedure

### 1. Inventory (umbrella + every submodule: dirty files and commits ahead of upstream)

PowerShell:

```powershell
foreach ($r in @('.') + (git config -f .gitmodules --get-regexp 'path$' | ForEach-Object { ($_ -split ' ')[1] })) { $s = git -C $r status --porcelain=v1; $a = git -C $r rev-list --count '@{u}..HEAD' 2>$null; if ($s -or $a -ne '0') { "== $r [$(git -C $r rev-parse --abbrev-ref HEAD)] ahead=$a"; $s } }
```

bash:

```bash
for r in . $(git config -f .gitmodules --get-regexp 'path$' | awk '{print $2}'); do s=$(git -C $r status --porcelain=v1); a=$(git -C $r rev-list --count @{u}..HEAD 2>/dev/null || echo '?'); if [ -n "$s" ] || [ "$a" != 0 ]; then echo "== $r [$(git -C $r rev-parse --abbrev-ref HEAD)] ahead=$a"; echo "$s"; fi; done
```

Also run `git submodule status` in the umbrella. A `+` line is a pointer that differs from `HEAD`.

### 2. Decide what is yours

- Yours: files you edited this task and commits you made (`git -C <repo> log --oneline @{u}..HEAD`,
  `git -C <repo> diff --stat`).
- Not yours: everything else, including a `+` pointer you did not create and another session's
  unpushed commits below yours. Ask before pushing a branch that carries them.
- If the user said "everything, regardless of who made it", list what you will include before committing.

### 3. Check line endings

`core.autocrlf=true` is set; `LF will be replaced by CRLF` warnings are normal. A diff that rewrites
every line means the editor dropped the file's line endings:

```bash
git -C <repo> diff --stat -- <path>          # vs.
git -C <repo> diff --stat --ignore-cr-at-eol -- <path>
git -C <repo> ls-files --eol -- <path>       # i/crlf in the index + w/lf in the tree = lost CRLF
```

Restore the original endings; do not commit a whole-file rewrite.

### 4. Commit inside each submodule (dependency order)

After the rule's pre-commit `status` / `log -3 --oneline` check:

```bash
git -C nornir-<pkg> add -- <new files you created>
git -C nornir-<pkg> commit -m "<what and why>" -- <every path you changed>
```

`git commit -- <paths>` commits only those paths, even if another session staged other files.

**Commit-only mode ends here.** Report per repo: commits made, `ahead=` count, and pointer bumps
still needed.

### 5. Push each submodule, in push order

```bash
git -C nornir-<pkg> push origin <work-branch>
```

On a non-fast-forward rejection: `git -C <sub> fetch`, show `git -C <sub> log --oneline HEAD..@{u}`,
and ask before merging or rebasing.

### 6. Verify the remote has the SHA

```bash
sha=$(git -C nornir-<pkg> rev-parse HEAD)
git -C nornir-<pkg> fetch origin
git -C nornir-<pkg> branch -r --contains $sha      # must list origin/<work-branch>
# or: git -C nornir-<pkg> ls-remote origin refs/heads/<work-branch>   (equals $sha right after your push)
```

Pre-push gate for the umbrella: every recorded pointer must be on a remote branch.

```bash
for r in $(git config -f .gitmodules --get-regexp 'path$' | awk '{print $2}'); do sha=$(git ls-tree HEAD $r | awk '{print $3}'); git -C $r branch -r --contains $sha 2>/dev/null | grep -qv HEAD || echo "NOT ON REMOTE: $r $sha"; done
```

Any `NOT ON REMOTE` line breaks umbrella CI (`upload-pack: not our ref`). Push that submodule first.

### 7. Bump umbrella pointers

```bash
git add -- nornir-<pkg> [nornir-<other>]
git commit -m "Update nornir-<pkg>: <why>" -- nornir-<pkg> [nornir-<other>]
```

Several packages in one commit: `Update nornir-imageregistration, nornir-pyre: <why>`. Bump only
the pointers you moved.

### 8. Push the umbrella

```bash
git push --recurse-submodules=check origin dev
git submodule status          # no '+' lines for your packages
```

`--recurse-submodules=check` refuses the push if a recorded submodule commit is not on a remote.

### 9. Check CI

```bash
gh run list --repo jamesra/<repo> --limit 3
```

Run for every pushed repo with a workflow (table above) and for `jamesra/nornir`. Open failures
with `gh run view <id> --log-failed`; see the **CI-hygiene** rule.

Report per repo: branch, pushed SHA, CI status. To pull elsewhere the user needs `git pull` then
`git submodule update --init`.

## `update-submodules.ps1` (pointer refresh)

Root script: `git submodule sync`, fetch every submodule, then `git submodule update --remote --merge`
(each checkout merges `origin/<branch from .gitmodules>`), then print status. Use it to move
checkouts and pointers to the latest **pushed** tips.

- Run the inventory first. `--merge` merges into dirty or locally-ahead submodules; if any is dirty or
  ahead and not yours, ask first.
- `-Commit` stages `.gitmodules` and **every** submodule path. Use it only when every moved pointer is
  intended, with `-Message "Update nornir-X, nornir-Y: <why>"`; otherwise commit by path (step 7).
- It does not push; push the umbrella with step 8.

## Release mode

[nornir-bump-version](../nornir-bump-version/SKILL.md) says which files change. Commit and push the
package (steps 4-6), bump the umbrella (steps 7-8), then tag and push the tag by name:

```bash
git tag v$(cat VERSION)           # or pyre-X.Y.Z
git push origin v$(cat VERSION)   # one tag; not --tags
```

## Audit mode (report, change nothing)

```bash
for r in . $(git config -f .gitmodules --get-regexp 'path$' | awk '{print $2}'); do
  b=$(git config -f .gitmodules submodule.$r.branch || echo dev)
  echo "== $r [$b]"
  git -C $r log --oneline @{u}..HEAD                                     # unpushed commits
  git -C $r branch -a --no-merged origin/$b --format='%(refname:short)' | grep -v '^origin$'  # unmerged branches
  git -C $r branch -a --list 'cursor/*' 'origin/cursor/*'                # agent branches
  git -C $r stash list                                                   # old stashes (lost-work candidates)
  git -C $r worktree list                                                # incl. prunable ones
done
git worktree list                                                        # umbrella, incl. .claude/worktrees/*
```

For each extra worktree, run `git -C <worktree> status --short` and
`git -C <worktree> log --oneline origin/<branch>..HEAD`. `master` showing as unmerged into `dev` is
normal for some packages; report it but do not merge. Do not pop stashes, prune worktrees, or delete
branches without asking.
