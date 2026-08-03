<#
.SYNOPSIS
  Fetch submodule remotes and advance checkouts to the branch tips recorded in .gitmodules.

.DESCRIPTION
  Solves parent-monorepo drift: after submodule repos move on their tracking branches,
  the umbrella still pins old SHAs until those pointers are updated and committed here.

  This script:
    1. Syncs submodule URLs from .gitmodules
    2. Fetches each submodule remote
    3. Runs `git submodule update --remote --merge` so each checkout follows its
       configured `branch =` in .gitmodules
    4. Prints `git status` so you can review and commit the updated pointers

  Git cannot auto-commit parent pointer bumps; after this script, commit (and push)
  the changed submodule entries in the umbrella when the new tips are intentional.

.NOTES
  Problem this solves: forgetting to bump the parent after pushing submodule work
  (e.g. nornir-pyre) leaves clones and CI on stale SHAs.
#>
[CmdletBinding()]
param(
    [switch]$Commit,
    [string]$Message = 'Bump submodules to current tracking-branch tips.'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

Write-Host 'Syncing submodule URLs from .gitmodules ...'
git submodule sync --recursive
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Fetching submodule remotes ...'
git submodule foreach --recursive 'git fetch origin --prune'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Updating checkouts to .gitmodules branch tips (--remote) ...'
git submodule update --remote --merge
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host 'Parent status (commit submodule path changes to lock new tips):'
git status -sb
git submodule status

$dirty = git status --porcelain=v1 --ignore-submodules=dirty
# Also detect staged/unstaged gitlink changes
$subDiff = git diff --submodule=short HEAD
if (-not $subDiff -and -not (git diff --cached --submodule=short HEAD)) {
    Write-Host ''
    Write-Host 'No submodule pointer changes relative to HEAD.'
    exit 0
}

if ($Commit) {
    $paths = @(git config --file .gitmodules --get-regexp path | ForEach-Object { ($_ -split '\s+', 2)[1] })
    git add -- .gitmodules @paths
    if (-not (git diff --cached --quiet)) {
        git commit -m $Message
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host 'Committed submodule pointer update.'
    }
    else {
        Write-Host 'Nothing staged to commit (pointers already match HEAD).'
    }
    git status -sb
}
else {
    Write-Host ''
    Write-Host 'Review the diff, then commit the updated gitlinks (and .gitmodules if changed).'
    Write-Host 'Or re-run:  .\update-submodules.ps1 -Commit'
}
