Remote build appliance
======================

Production Windows+WSL2 box for interactive ``nornir-build`` with shared NAS mounts
and a co-located MQTT dashboard. Keep this role separate from the programmer Dev
Container (``run-cursor-dev.ps1``) and the Cursor AI worker (``start-cursor-worker.ps1``).

Quickstart: new production box
------------------------------

**One-time (4 steps)**

1. **Prerequisites:** Docker Desktop + WSL2, CIFS module on WSL
   (``modprobe cifs`` / modules-load), NVIDIA driver if GPU, Git.
2. **Clone** the monorepo with submodules (scripts/compose only — images come from GHCR).
3. **Initialize** once (layout + pull + dashboard)::

     .\nornir-docker\Initialize-NornirBuildAppliance.ps1
     # prompts for monorepo root; Enter accepts parent of nornir-docker
     # or: -MonorepoRoot D:\src\git\nornir
     # On auth failure: docker login ghcr.io -u <github-user> (PAT with read:packages)

4. **Edit site-specific files only:**

   - ``<ROOT>\Run\nornir-net-mounts\net-mounts\nas-mounts.tsv``
   - ``<ROOT>\Run\nornir-net-mounts\secrets\net-creds\*.cred``
   - UNC/WSL host paths in ``.run.nornir-net-mounts.env`` when needed

**Every session (1 step)**::

  & "$env:NORNIR_DOCKER_USER_ROOT\Builds\nornir-build\start-nornir-build.ps1"
  # GPU probe picks nornir:cupy vs nornir:prod; path-B CIFS; interactive shell

Dashboard UI: http://127.0.0.1:8087 — see :doc:`dashboard`.

Open file limits
----------------

Production, cursor-dev, and cursor-worker containers ship with ``nofile`` **65536** (Compose ``ulimits`` or ``docker run --ulimit``). Heavy tile assembly on CIFS can exhaust the default **1024** limit. After starting a container, confirm with ``ulimit -n``.

Roles (do not collapse)
-----------------------

============= ========================================= ======================================
Role          Image / stack                             Launcher
============= ========================================= ======================================
Programmer    ``cursor-dev`` / ``nornir:dev-cursor-base`` ``run-cursor-dev.ps1``
Cursor AI     ``nornir:cursor-worker``                   ``start-cursor-worker.ps1``
Build appliance ``nornir:cupy`` or ``nornir:prod``       ``start-nornir-build.ps1``
============= ========================================= ======================================

``nornir:dev-cursor-base`` is a shared base layer, not the AI image. Use
``-Image nornir:dev-cursor-base -Clone`` on the appliance only when you need live
git packages in ``/workspace``.

Shared ``nornir-net-mounts`` (path B)
------------------------------------

Layout::

  <NORNIR_DOCKER_USER_ROOT>\Run\nornir-net-mounts\
    net-mounts\nas-mounts.tsv
    secrets\net-creds\*.cred
    .run.nornir-net-mounts.env

**Path B (sole NAS path):** in-container CIFS via ``mount-network-shares.sh`` with
``CAP_SYS_ADMIN``, ``DAC_READ_SEARCH``, and ``apparmor:unconfined`` for the mount
phase. After mounts succeed, the entrypoint drops ``CAP_SYS_ADMIN`` when
``setpriv`` or ``capsh`` is available (CIFS stays mounted; remount requires a
container restart). Credentials stay outside the image; privileges are opt-in
per container start.

Verify checklist
----------------

Inside the appliance shell::

  echo "$NORNIR_NET_MOUNTS"   # expect 1
  findmnt -t cifs
  # expect shares from nas-mounts.tsv (e.g. /storage4)
  # CAP_SYS_ADMIN should be dropped after entry when setpriv/capsh are present

Interactive shells print a short welcome with ``nornir-build`` usage and list
entry wrappers in ``~/scripts`` (on ``PATH``): ``TEMImport.sh``, ``TEMBuild.sh``,
``TEMBuild-import.sh``, ``TEMAlign.sh``. Bind-mounted workspace trees refresh
those scripts from ``nornir-buildmanager/scripts`` on container start.

On the host: open http://127.0.0.1:8087 for the dashboard.

Troubleshooting
---------------

==================================== ===============================================
Symptom                              Likely cause
==================================== ===============================================
Missing ``nas-mounts.tsv``           Run initializer; edit site files
``Operation not permitted`` on mount Caps/override missing (path B not applied)
``cifs`` mount error (2)             ``cifs`` not loaded in WSL kernel
``Permission denied`` (13)           Bad/missing ``.cred``, wrong password, or cred file permissions (Windows hosts: rebuild image with current ``mount-network-shares.sh``)
No GPU / wrong image                 ``Test-NornirGpu.ps1``; NVIDIA Docker setup
Dashboard unreachable                ``start-dashboard.ps1``; bind host 127.0.0.1
==================================== ===============================================

Maintainer publish (build machine)
----------------------------------

Not part of the operator checklist::

  .\nornir-docker\docker-build.ps1
  .\nornir-docker\docker-push.ps1 -IncludeDashboard
