# Publish a built Pyre Windows installer to GitHub Releases and refresh docs metadata.
#
# Expects a built installer at:
#   nornir-pyre/packaging/windows/dist/installer/Pyre-<ver>-Setup.exe
#
# Creates/updates release tag pyre-<ver> with:
#   - Pyre-<ver>-Setup.exe  (versioned; kept forever)
#   - Pyre-Setup.exe        (same bytes; stable name for /releases/latest/download/)
# Release notes come from nornir-pyre/CHANGELOG.user.md (## <ver> section).
# Also regenerates docs/packages/pyre_changelog.rst.
#
# Examples:
#   .\release\publish_pyre_windows_release.ps1
#   .\release\publish_pyre_windows_release.ps1 -SkipDocsTrigger
#   .\release\publish_pyre_windows_release.ps1 -Version 1.7.7

[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$Repo = "jamesra/nornir",
    [switch]$SkipDocsTrigger,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "nornir-pyre"))) {
    $RepoRoot = Split-Path -Parent $RepoRoot
}

$Python = Join-Path $RepoRoot "venv\pyre314\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Set-Location $RepoRoot

if (-not $Version) {
    $Version = & $Python -c "from release.sync_pyre_user_changelog import read_pyre_version; print(read_pyre_version())"
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Version)) {
        throw "Could not read Pyre version from nornir-pyre/pyproject.toml"
    }
}
$Version = $Version.Trim()
$Tag = "pyre-$Version"
$InstallerDir = Join-Path $RepoRoot "nornir-pyre\packaging\windows\dist\installer"
$VersionedExe = Join-Path $InstallerDir "Pyre-$Version-Setup.exe"
$LatestExe = Join-Path $InstallerDir "Pyre-Setup.exe"
$NotesFile = Join-Path $RepoRoot "release\_pyre_release_notes.md"

if (-not (Test-Path $VersionedExe)) {
    throw "Missing installer: $VersionedExe — run pyre: build Windows installer (full) first."
}

Write-Host "Preparing release $Tag from $VersionedExe"
Copy-Item -Force $VersionedExe $LatestExe

& $Python (Join-Path $RepoRoot "release\sync_pyre_user_changelog.py") `
    --version $Version `
    --notes-file $NotesFile `
    --write-docs
if ($LASTEXITCODE -ne 0) { throw "sync_pyre_user_changelog.py failed" }

if ($DryRun) {
    Write-Host "DryRun: would publish $Tag with:"
    Write-Host "  $VersionedExe"
    Write-Host "  $LatestExe"
    Write-Host "  notes: $NotesFile"
    Get-Content $NotesFile
    exit 0
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required"
}

$existing = gh release view $Tag --repo $Repo 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Updating existing release $Tag"
    gh release upload $Tag $VersionedExe $LatestExe --repo $Repo --clobber
    gh release edit $Tag --repo $Repo --notes-file $NotesFile --latest
} else {
    Write-Host "Creating release $Tag"
    gh release create $Tag $VersionedExe $LatestExe `
        --repo $Repo `
        --title "Pyre $Version Windows installer" `
        --notes-file $NotesFile `
        --latest
}

Write-Host "Published: https://github.com/$Repo/releases/tag/$Tag"
Write-Host "Latest download: https://github.com/$Repo/releases/latest/download/Pyre-Setup.exe"

if (-not $SkipDocsTrigger) {
    Write-Host "Triggering documentation workflow…"
    gh workflow run docs.yml --repo $Repo -f "" 2>$null
    if ($LASTEXITCODE -ne 0) {
        # workflow_dispatch without inputs
        gh workflow run Documentation --repo $Repo
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not trigger docs workflow; push docs changelog changes or run it manually."
    }
}

Write-Host "Done. Commit regenerated docs/packages/pyre_changelog.rst if it changed."
