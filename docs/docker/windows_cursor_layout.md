# Standard `D:\` layout for nornir-cursor-worker

This layout keeps **secrets and env** under `D:\Docker` while launchers stay in the repo (symlinked once).

## One-time initializer

**Git clone and Docker do not create these paths.** Run `Initialize-NornirCursorWorkerLayout.ps1` once (Developer Mode or elevated shell for symlinks):

```powershell
& 'D:\src\git\nornir\nornir-docker\windows-docker-layout\Initialize-NornirCursorWorkerLayout.ps1' `
  -ScriptsRepoRoot 'D:\src\git\nornir' `
  -DockerUserRoot 'D:\Docker'
```

## Directory layout

| Path | Purpose |
|------|---------|
| `D:\Docker\Builds\nornir\` | Build env + `build-nornir-images.ps1` symlink |
| `D:\Docker\Builds\nornir-cursor-worker\` | Thin launcher symlink |
| `D:\Docker\Run\nornir-cursor-worker\` | Run secrets (`nornir-cursor-worker.run.env`) |
| `D:\Docker\mounted-configs\nornir-cursor-worker\` | Per-run agent clone folders at `/workspace` |

Set `NORNIR_DOCKER_USER_ROOT=D:\Docker` and `NORNIR_MONOREPO_ROOT` to your clone (host scripts only).

## Disk cleanup

Per-run folders under `D:\Docker\mounted-configs\nornir-cursor-worker\` can accumulate. Run `nornir-docker/Cleanup-CursorWorkerClones.ps1` with `-WhatIf` first. See {doc}`cursor_worker`.

## Build and run

```powershell
cd D:\Docker\Builds\nornir
.\build-nornir-images.ps1

# Edit CURSOR_API_KEY in:
#   D:\Docker\Run\nornir-cursor-worker\nornir-cursor-worker.run.env

& D:\Docker\Builds\nornir-cursor-worker\start-nornir-cursor-worker.ps1
```

## Dev mount parity (opt-in)

After configuring `D:\Docker\Run\nornir-dev\` per the dev volumes doc, set `NORNIR_WORKER_DEV_PARITY_MOUNTS=1` in the worker run env or pass `-DevParityMounts` to the launcher.

## Compose

```powershell
$env:NORNIR_CURSOR_WORKER_ENV_FILE = 'D:\Docker\Run\nornir-cursor-worker\nornir-cursor-worker.run.env'
docker compose -f nornir-docker/compose.cursor-worker.yaml run --rm nornir-cursor-worker
```

See also `nornir-docker/windows-docker-layout/CONFIG_LAYOUT.md` in the repo.
