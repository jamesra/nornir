---
name: deploy-connectomes
description: Deploy, update, or debug the connectomes.pitt.edu hosts (compute, web, iis, dev box) with nornir-docker's stack.ps1. Use when bringing a stack up or down on a server, rolling out a change, renewing or distributing the TLS certificate, or diagnosing a server stack.
---

# Deploy connectomes.pitt.edu

Human docs (canonical): `docs/deployment/` (https://nornir.github.io/deployment/). Viking service
specifics: Viking `Documentation/source/deployment/`. Rule: `.cursor/rules/nornir-docker-conventions.mdc`.
First-time setup of a new compute host: `deploy-compute-host` skill.

## Hosts

| Target | Stacks |
|--------|--------|
| `compute` (Ubuntu GPU) | `nornir-build`, `nornir-dashboard`, `viking-segmentation` |
| `web` (Ubuntu) | `viking-proxy`, `viking-certs`, `viking-identity`, `viking-annotation`, `viking-corrections` (+ annotation gallery from Sam2Trainer, not a stack) |
| `iis` (Windows IIS) | `viking-iis` |
| dev box (Windows) | deploys to all of them with `-Target <name>`; local `nornir-dashboard`, `nornir-dev` |

Layout root: `D:\Docker` (Windows) / `/srv/docker` (Ubuntu). Targets: `Run/_host/targets.psd1` on the dev box.

## Procedure (every change)

1. **Check:** `stack.ps1 doctor -Target <host>` (or `all`). Fix every `[FAIL]` before going on.
2. **Push** the commits you want deployed (submodule commits first, then the umbrella pointer).
3. **Sync + roll out:** `stack.ps1 <stack> rebuild -Target <host> -Sync`
   (`up` when nothing changed in the image; `-Images ghcr` to pull instead of build on the target).
4. **Verify:** `stack.ps1 <stack> status -Target <host>` (health URL), then
   `stack.ps1 <stack> logs -Target <host>` if anything looks wrong.

`-Sync` refuses when the local branch is not pushed; never work around it by editing files on the server.

## Certificates

- Issue/renew on `web`: `stack.ps1 certs letsencrypt -Target web` (needs public port 80 and
  `viking-proxy` up); fallback `certs acme-eab` (Pitt ACME, `TLS_EAB_KID` / `TLS_EAB_HMAC_KEY`) or
  `certs manual -Cert -Key -Chain` (validates key match, SAN coverage, expiry).
- Check: `stack.ps1 certs status -Target web`.
- Distribute from the dev box: `stack.ps1 certs push -From web` (fetches `Certs/<name>/` from web,
  copies it to targets with `CertPush = $true` (`compute`, `iis`), runs `certs reload` / `certs
  install-iis` there). Running `certs push` on web itself (e.g. cron) is optional and needs web's
  own targets.psd1 and keys.
- Reload after a manual change: `stack.ps1 certs reload -Target <host>`.

## Secrets

- `stack.ps1 secrets new <stack> [KEY ...] -Target <host>`: fills registry-listed and
  `REPLACE_WITH_GENERATED...` keys plus any named keys. Name optional client secrets explicitly
  (empty = client disabled). Never generates `SQL_SERVER_PASSWORD` or connection strings.
- Argument order is free: `stack.ps1 up viking-identity` = `stack.ps1 viking-identity up`.

## Debugging

- Shell / exec / logs: `stack.ps1 <stack> shell|exec|logs -Target <host> [-Service s] [-Follow]`.
- Tunnels: `stack.ps1 tunnel -Target compute` (8087 dashboard, 5678 debugpy) or `-Target web`
  (4024 .NET debugger, 1433 SQL).
- debugpy: `NORNIR_DEBUGPY=1` in `Run/nornir-build/nornir-build.run.env` only publishes the port;
  install and start debugpy inside the container (`docs/deployment/debugging.rst`).

## Must not

- **Never commit** anything from `Run/`, `Certs/`, `Data/`, or a filled-in env/secret file. Templates only.
- Do not put secrets in `host.env` or `<stack>.run.env` (use `secrets/`), or in tickets/chat.
- Do not publish internal ports (1883, 8087, 4024, 5678, Docker API) beyond `127.0.0.1`; Docker
  bypasses ufw on Linux. Cross-host ports are filtered in `DOCKER-USER`.
- Do not copy repo scripts into the layout; launchers there forward to the checkout.
- Do not run destructive actions (`down`, `prune -Force`, `certs manual -Force`) on a server
  without the user's explicit go-ahead.
