---
name: docker-publish-ghcr
description: >-
  Build, push, verify and pull the Nornir Docker images through GHCR
  (ghcr.io/jamesra/*) with nornir-docker's docker-build.ps1, docker-push.ps1 and
  docker-pull.ps1. Use to publish or refresh images, for exact rebuild-and-push
  commands, to check a ghcr.io login or PAT scope (permission_denied), when only
  some images built, on "No such image", when clients still run an old image, or
  to redeploy one container (for example the dashboard) from a new image. Server
  stack rollout itself: deploy-connectomes.
---

# Publish and pull Nornir images (GHCR)

## Source of truth (do not duplicate here)

- Script help: `.\nornir-docker\docker-build.ps1 -Help`, `docker-push.ps1 -Help`, `docker-pull.ps1 -Help`
- Image catalogue and build-args: [docs/docker/images.rst](../../../docs/docker/images.rst); skill **nornir-docker-images-ci**
- Maintainer publish and client refresh: [docs/deployment/nornir_build_appliance.rst](../../../docs/deployment/nornir_build_appliance.rst) ("Refreshing images", "Maintainer publish")
- Tokens: [docs/deployment/accounts_and_tokens.rst](../../../docs/deployment/accounts_and_tokens.rst)
- `stack.ps1 pull` / `-Images ghcr|load`: [docs/deployment/stacks_and_commands.rst](../../../docs/deployment/stacks_and_commands.rst)
- Rolling out to connectomes hosts (`-Target`, `-Sync`, doctor): skill **deploy-connectomes**

Run every command from the monorepo root in PowerShell 7. Owner defaults to `jamesra`
(override: `-Owner` or `$env:NORNIR_GHCR_OWNER`).

## 1. Log in and check the token

GHCR documents only **classic** PATs: `write:packages` to push (includes read), `read:packages`
to pull. `accounts_and_tokens.rst` describes fine-grained tokens; if one fails with `denied`, use a classic token.

```powershell
Select-String ghcr.io $env:USERPROFILE\.docker\config.json      # stored login present?
docker buildx imagetools inspect ghcr.io/jamesra/nornir:cupy     # succeeds = registry reachable with these creds
curl.exe -sI -H "Authorization: Bearer <PAT>" https://api.github.com/user | Select-String x-oauth-scopes
docker logout ghcr.io; docker login ghcr.io -u <github-user>     # paste the PAT as the password
```

`denied: permission_denied: The token provided does not match expected scopes`: the token
lacks `write:packages` (push) or `read:packages` (pull). Make a new classic token, log out
and log in again. `-List` on push/pull shows `unknown` when the registry check itself failed.

## 2. Build

```powershell
.\nornir-docker\docker-build.ps1 -List                 # present / missing, last recorded build
.\nornir-docker\docker-build.ps1                       # dev, dev-cursor-base, cursor-worker, prod, cupy
.\nornir-docker\docker-build.ps1 -Images prod,cupy     # appliance images only
.\nornir-docker\start-dashboard.ps1 -Rebuild           # nornir-dashboard:latest (not in docker-build)
```

`docker-build.ps1` builds only the five `nornir:*` images; `nornir-dashboard:latest`,
`nornir-annotation-gallery:latest` and `sam2-trainer:dev` have their own build commands
(`docker-push.ps1 -List` prints each). `No such image nornir-dashboard:latest`: never built here;
run `start-dashboard.ps1 -Rebuild`, or on a client `docker-pull.ps1 -Images dashboard`.

**Only the first image built?** Read the output above `Done.`:

| Output | Cause | Fix |
|--------|-------|-----|
| `[nornir:x] up to date ...; skipping build.` | Recorded inputs unchanged (`.docker-build-state.json` in the invocation dir) | Expected; `-Force` (keeps cache) or `-NoCache` to build anyway |
| `Post-build verification reported problems` | BUILD_DATE / revision label mismatch or version-tag failure; exit 2 stops the loop | Fix the warning above it, rerun |
| a `docker build` error | First failure stops the remaining images | Fix, rerun (finished images are skipped) |
| `function "org" not defined`, or stop after image 1 with no error | Old script copy (label quoting / stdout in exit code, both fixed) | Run `nornir-docker\docker-build.ps1` from the current checkout, not a stale copy |
| `Unknown image 'prod,cupy'` | `pwsh -File` passes `-Images a,b` as one string; docker-build does not split it | Call from a PowerShell prompt, or `pwsh -Command "& .\nornir-docker\docker-build.ps1 -Images prod,cupy"` |

## 3. Push

```powershell
.\nornir-docker\docker-push.ps1 -List                  # clean / dirty / missing / unknown per tag
.\nornir-docker\docker-push.ps1                        # every built, non-Viking image whose digest differs
.\nornir-docker\docker-push.ps1 -Images cupy,dashboard
```

Tags: each image pushes a floating tag and a versioned tag from the root `VERSION` file,
e.g. `ghcr.io/jamesra/nornir:cupy` + `:cupy-<VERSION>`, `nornir-dashboard:latest` +
`:<VERSION>`, `sam2-trainer:dev` + `:dev-<VERSION>`. Viking images (`-Images viking`, opt-in)
take an 8-character revision tag instead. The versioned tag is **overwritten** on every push
until `VERSION` is bumped (skill **nornir-bump-version**), so it does not identify a build; use
the digest and the revision label.

`Unchanged. Skipping` (remote digest equals the local image) or a warning `Image is N hours old`:
you did not rebuild. `-Force` pushes anyway.

## 4. Verify what was pushed

```powershell
git rev-parse HEAD
docker image inspect nornir:cupy --format '{{json .Config.Labels}}'      # org.opencontainers.image.revision / created
docker image inspect nornir:cupy --format '{{json .RepoDigests}}'
docker buildx imagetools inspect ghcr.io/jamesra/nornir:cupy             # Digest: must be in RepoDigests above
docker buildx imagetools inspect ghcr.io/jamesra/nornir:cupy --format '{{json .Image}}' | Select-String image.revision
```

Use `{{json ...}}` formats: `{{index .Config.Labels "..."}}` breaks under PowerShell quoting.

## 5. Pull on a client

```powershell
.\nornir-docker\docker-pull.ps1 -List                  # which local tags differ from GHCR
.\nornir-docker\docker-pull.ps1                        # prod, cupy only (the default)
.\nornir-docker\docker-pull.ps1 -Images dev,dashboard,gallery
stack.ps1 nornir-build pull -Target compute            # same, on a server (deploy-connectomes)
```

`docker-pull.ps1` pulls `ghcr.io/...` **and retags** the local name (`nornir:cupy`,
`nornir-dashboard:latest`). Compose files and launchers run local names, so a bare
`docker pull ghcr.io/jamesra/nornir:cupy` leaves the old `nornir:cupy` in use.

## "Users only get the old image" checklist

1. **Not rebuilt.** Push said `Unchanged. Skipping`, or the revision label is not your `HEAD`. Rebuild (`-Force` if build skipped it), push again.
2. **Built from another checkout.** The revision label is the umbrella `HEAD` of the tree that ran `docker-build.ps1`; uncommitted submodule edits do not change it. Build on the machine and branch you meant to publish.
3. **Client did not retag.** They ran `docker pull ghcr.io/...`, not `docker-pull.ps1` / `stack.ps1 <stack> pull`. On the client, the local tag's `RepoDigests` must contain the GHCR digest.
4. **Versioned tag reused.** `-PreferVersioned` or a `:cupy-<VERSION>` reference resolves to whatever was pushed last under that VERSION. Compare digests, not tag names.
5. **Pinned reference.** No `nornir-docker/compose*.yaml` pins `@sha256` today; check run-env image overrides (for example `SEGMENTATION_IMAGE`) for a digest or old tag.
6. **Container not recreated.** `stack.ps1 nornir-build up` does nothing when the container is running; use `rebuild`. For compose stacks pulled from GHCR use `up`, not `rebuild` (compose `rebuild` runs `build --pull` from source). Script stacks (`Engine = 'script'` in `deploy/stacks.psd1`, e.g. nornir-build) have no build step: `rebuild` removes the container and runs `up`, so it does use the pulled image.
7. **Wrong owner.** `NORNIR_GHCR_OWNER` differs between publisher and client.
8. **Stale layer cache at build.** Rare (the build checks BUILD_DATE); `docker-build.ps1 -NoCache` or `start-dashboard.ps1 -Rebuild -NoCache`.

## Redeploy one container

| Container | From local sources | From GHCR |
|-----------|--------------------|-----------|
| dashboard | `stack.ps1 nornir-dashboard rebuild` (Mosquitto keeps running) | `docker-pull.ps1 -Images dashboard`, then `stack.ps1 nornir-dashboard up` (not `rebuild`, which rebuilds from source) |
| nornir-build | `docker-build.ps1 -Images cupy`, then `stack.ps1 nornir-build rebuild` | `stack.ps1 nornir-build pull`, then `stack.ps1 nornir-build rebuild` |
| Viking stacks | `stack.ps1 <stack> rebuild` | `stack.ps1 <stack> up -Images ghcr` |

Add `-Target <host>` (and `-Sync` for source rebuilds) for servers; see **deploy-connectomes**.
Hard-refresh the browser after a dashboard redeploy.
