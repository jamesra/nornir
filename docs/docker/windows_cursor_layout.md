# Standard `D:\` layout for nornir-cursor-worker

This layout keeps **secrets and env** under a fixed Windows path while the **repo launcher** stays a single file in git (no duplicate copies of `start-cursor-worker.ps1`).

## Symlinks are not automatic

**Git clone and Docker do not create these links.** Run `Initialize-NornirCursorWorkerLayout.ps1` once (from the repo), or follow the snippet under [Thin launcher](thin-launcher-symlink) below. Creating symlinks usually requires **Windows Developer Mode** or an **elevated** PowerShell/cmd.

```powershell
& 'D:\src\git\nornir\nornir-docker\windows-docker-layout\Initialize-NornirCursorWorkerLayout.ps1' -MonorepoRoot 'D:\src\git\nornir'
```

Use `-LayoutRoot 'D:\your\path'` if your layout root differs from the default.

**Folder name:** the documented layout root is `D:\Docker\Builds\nornir-cursor-worker` (`Builds`, plural). `D:\Docker\Build\...` (singular `Build`) is a different path; use `Builds` or pass `-LayoutRoot` to the initializer.

## Recommended directories

| Path | Purpose |
|------|---------|
| `D:\Docker\Builds\nornir-cursor-worker\` | **Layout root**: `.env.cursor-worker`, optional symlink to the thin launcher. |
| `D:\Docker\mounted-configs\nornir-cursor-worker\` | **Default parent** for per-run unique workspace folders (`nornir-cursor-worker-<timestamp>-<guid>`). |

## Disk cleanup

Per-run folders under `D:\Docker\mounted-configs\nornir-cursor-worker\` and isolated clones under `D:\agents\` can accumulate. Run `nornir-docker/Cleanup-CursorWorkerClones.ps1` to remove disposable directories only when no Docker container bind-mounts that path and the git working tree is clean. Use `-WhatIf` first. See {doc}`cursor_worker` for behavior and parameters.

(thin-launcher-symlink)=
## Thin launcher (symlink)

From an elevated PowerShell (or with Developer Mode enabled):

```powershell
$Target = 'D:\src\git\nornir\nornir-docker\windows-docker-layout\start-nornir-cursor-worker.ps1'
$Link   = 'D:\Docker\Builds\nornir-cursor-worker\start-nornir-cursor-worker.ps1'
New-Item -ItemType Directory -Force -Path (Split-Path $Link) | Out-Null
if (Test-Path $Link) { Remove-Item $Link -Force }
New-Item -ItemType SymbolicLink -Path $Link -Target $Target
```

Place `D:\Docker\Builds\nornir-cursor-worker\.env.cursor-worker` next to the symlink. Set `NORNIR_MONOREPO_ROOT` (User or Machine env) to your clone root, e.g. `D:\src\git\nornir`, or pass `-RepoRoot` each time.

## What the thin launcher does

- Calls `start-cursor-worker.ps1` with `-LiveMount -UseUniqueWorkspaceFolder` and `-WorkspaceRunParent D:\Docker\mounted-configs\nornir-cursor-worker`.
- Each run creates a unique folder (`nornir-cursor-worker-<stamp>-<guid>`), bind-mounts it at `/workspace`, and the entrypoint **clones** into it.

## Compose (point at a specific env file)

```powershell
$env:NORNIR_CURSOR_WORKER_ENV_FILE = 'D:\Docker\Builds\nornir-cursor-worker\.env.cursor-worker'
docker compose -f nornir-docker/compose.cursor-worker.yaml run --rm nornir-cursor-worker
```
