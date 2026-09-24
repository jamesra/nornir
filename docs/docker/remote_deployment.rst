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

To refresh images later without re-running initialize::

  .\nornir-docker\docker-pull.ps1 -IncludeDashboard -ContinueOnError
  # or pin to monorepo VERSION: -PreferVersioned

Dashboard UI: http://127.0.0.1:8087 — see :doc:`dashboard`.

Environment variables
---------------------

Host variables and the shared run-env file configure layout, GHCR, NAS mounts, and
MQTT. ``start-nornir-build.ps1`` loads
``<ROOT>\Run\nornir-net-mounts\.run.nornir-net-mounts.env`` when present (template:
``nornir-docker/example.nornir-net-mounts.run.env``). Dashboard-only keys live in
``Run\nornir-dashboard\dashboard.run.env`` (see :doc:`dashboard`).

**Host / run-env (set before launch or in ``.run.nornir-net-mounts.env``)**

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Variable
     - Expected value
   * - ``NORNIR_DOCKER_USER_ROOT``
     - Machine-local Docker root for Builds / Run / mounted-configs. The default
       is ``C:\Docker``; many lab machines set it to ``D:\Docker``. Examples on
       each page say which path they assume. Set as a user or system env var.
   * - ``NORNIR_GHCR_OWNER``
     - GHCR namespace for pull/push (``docker-pull.ps1``, initialize). Default
       ``jamesra``. Example: ``nornir`` for org packages.
   * - ``NORNIR_NET_MOUNTS_DIR_HOST``
     - Host directory that contains ``nas-mounts.tsv``. Optional when the default
       ``<ROOT>\Run\nornir-net-mounts\net-mounts`` is correct. Use a Windows path,
       WSL UNC (``\\wsl.localhost\<Distro>\...``), or ``/mnt/c/...`` from a WSL shell.
   * - ``NORNIR_NET_CREDS_DIR_HOST``
     - Host directory of per-share ``*.cred`` files mounted read-only at
       ``/run/secrets/net-creds``. Must be set together with
       ``NORNIR_NET_MOUNTS_DIR_HOST`` when overriding defaults.
   * - ``NORNIR_MQTT_HOST``
     - MQTT broker hostname as seen from the build container. Appliance default
       ``host.docker.internal`` (co-located dashboard). Leave unset to get that
       default from ``start-nornir-build.ps1``.
   * - ``NORNIR_MQTT_PORT``
     - MQTT port. Default ``1883``.
   * - ``NORNIR_MQTT_ENABLE``
     - ``1`` to enable MQTT telemetry publishers in Nornir tools; omit or unset to
       leave publishing off unless the process enables it another way.
   * - ``NORNIR_DOCKER_GPU``
     - ``1`` when ``Test-NornirGpu.ps1`` (or ``-Gpu``) succeeds; selects
       ``nornir:cupy`` if ``-Image`` is omitted. Set by the launcher; usually do not
       set by hand.
   * - ``NORNIR_DOCKER_NOFILE_SOFT`` / ``NORNIR_DOCKER_NOFILE_HARD``
     - Soft/hard ``nofile`` ulimits for ``docker run``. Default ``65536`` /
       ``65536``. Raise only if tile I/O still hits ``EMFILE``.
   * - ``NORNIR_DOCKER_EXTRA_ARGS``
     - Optional extra ``docker run`` tokens (space-separated) appended by the
       launcher helpers.

**Inside the appliance container**

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Variable
     - Expected value
   * - ``NORNIR_NET_MOUNTS``
     - ``1`` when path-B CIFS is enabled (set by ``start-nornir-build.ps1``).
       ``echo "$NORNIR_NET_MOUNTS"`` should print ``1``.
   * - ``NORNIR_NET_MOUNTS_MANIFEST``
     - Path to the mount table inside the container. Default
       ``/etc/nornir-net-mounts/nas-mounts.tsv`` (from the host mounts dir).
   * - ``NORNIR_NET_CREDS_SRC``
     - Read-only credentials dir. Default ``/run/secrets/net-creds``.
   * - ``NORNIR_MQTT_HOST`` / ``NORNIR_MQTT_PORT``
     - Passed through from the host so ``nornir-build`` can publish to the
       co-located dashboard.
   * - ``NORNIR_LOG_ROOT``
     - Optional root for persistent Nornir session logs (unified logging
       convention). Not required for mounts; set if you want file logs under a
       known host-visible path.

Open file limits
----------------

Production, cursor-dev, and cursor-worker containers ship with ``nofile`` **65536** (Compose ``ulimits`` or ``docker run --ulimit``). Heavy tile assembly on CIFS can exhaust the default **1024** limit. After starting a container, confirm with ``ulimit -n``.

Roles (do not collapse)
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 22 48 30

   * - Role
     - Image / stack
     - Launcher
   * - Programmer
     - ``cursor-dev`` / ``nornir:dev-cursor-base``
     - ``run-cursor-dev.ps1``
   * - Cursor AI
     - ``nornir:cursor-worker``
     - ``start-cursor-worker.ps1``
   * - Build appliance (GPU)
     - ``nornir:cupy`` — for build machines with an NVIDIA GPU (``cupy-cuda13x``).
       CUDA Toolkit **13.2** requires compute capability **7.5+** (Turing and
       newer; Maxwell / Pascal / Volta are out of support). CuPy Delaunay
       (``cupyx.scipy.spatial.Delaunay`` / GDel2D) does not document a higher
       architecture floor than CuPy itself, so plan on **7.5+** for GPU mesh
       and transform paths that use it.
     - ``start-nornir-build.ps1``
   * - Build appliance (CPU)
     - ``nornir:prod`` — CPU-only systems (no GPU / no CuPy).
     - ``start-nornir-build.ps1``

``nornir:dev-cursor-base`` is a shared base layer, not the AI image. Use
``-Image nornir:dev-cursor-base -Clone`` on the appliance only when you need live
git packages in ``/workspace``.

Shared ``nornir-net-mounts`` (path B)
-------------------------------------

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
entry wrappers in ``~/scripts`` (on ``PATH``): ``TEMImport``, ``TEMBuild``,
``TEMBuild-import``, ``TEMAlign``. Bind-mounted workspace trees refresh
those scripts from ``nornir-buildmanager/scripts`` on container start
(extension stripped for the ``TEM*`` entry points).

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
