Migrating from the old layout
=============================

The old ``D:\Docker`` tree grew one convention per service (``Builds\IdentityServer\.env.All*``,
``mounted-configs\...``, ``Run\segmentation-server``, Nginx Proxy Manager). The stack layout
gives every stack the same shape (:doc:`host_layout`). Moving over is a copy, not a rename: old
files stay where they are until you delete them.

Copy files with ``Move-DockerHostLayout.ps1``
---------------------------------------------

Always run with ``-WhatIf`` first; it prints the old-to-new table without copying::

   .\nornir-docker\deploy\Move-DockerHostLayout.ps1 -WhatIf
   .\nornir-docker\deploy\Move-DockerHostLayout.ps1
   .\nornir-docker\deploy\Move-DockerHostLayout.ps1 -From D:\Docker -To \\newserver\c$\srv\docker

It never deletes or overwrites. Env files that map to one ``<stack>.run.env`` are concatenated
with a header naming each source; when a destination already exists it writes
``<dest>.migrated`` next to it for you to diff and merge. Old ``mounted-configs\nornir-build-*``
sessions are left alone unless you pass ``-IncludeWork``. Then:

1. ``Initialize-DockerHost.ps1 -Role <role>`` (creates the rest of the tree and the forwarding
   launchers);
2. compare each migrated env file with its ``example.<stack>.run.env`` and rename keys (the
   script does not rename variables);
3. ``stack.ps1 doctor``;
4. on the dev box, stop the old all-in-one ``viking`` compose project before the first
   ``stack.ps1 ... up`` (``docker compose -p viking down``); its published ports clash with the
   new stacks;
5. delete the old files once the stacks run.

Old to new
----------

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - Old
     - New
   * - ``C:\Docker`` (old script default)
     - ``D:\Docker`` on Windows, ``/srv/docker`` on Ubuntu; set ``NORNIR_DOCKER_USER_ROOT`` to keep
       another root
   * - ``mounted-configs\nornir-build-*``
     - ``Work\nornir-build-*`` (``stack.ps1 prune``)
   * - ``Run\nornir-dashboard\dashboard.run.env``
     - ``Run\nornir-dashboard\nornir-dashboard.run.env`` (old name still read)
   * - ``Builds\IdentityServer\.env.All``, ``.env.All.Production``, ``.env.All.Docker``
     - ``Run\viking-identity\viking-identity.run.env`` (secrets into
       ``Run\viking-identity\secrets\secrets.env``)
   * - ``Configs\IdentityServer\Duende_License.key`` (or ``mounted-configs\IdentityServer\``)
     - ``Run\viking-identity\secrets\Duende_License.key``
   * - ``mounted-configs\IdentityServer\secrets.json``
     - ``Run\viking-identity\secrets\secrets.json``
   * - ``mounted-configs\IdentityServer\DataProtectionKeys``, or
       ``<Viking repo>\Servers\IdentityServer\DataProtectionKeys``
     - ``Data\viking-identity\DataProtectionKeys``. Copy before the first ``viking-identity``
       start, or every user is signed out. ``Move-DockerHostLayout.ps1`` copies only the
       ``mounted-configs`` source; copy the repository folder by hand.
   * - ``Builds\cloudflare.ini``, ``Builds\*\cloudflare.ini``
     - ``Run\viking-certs\secrets\cloudflare.ini``
   * - ``Builds\GrpcAnnotationService\.env.Docker``, ``Builds\AnnotationSql\.env``
     - ``Run\viking-annotation\viking-annotation.run.env``
   * - ``Builds\GrpcAnnotationService\corrections``
     - ``Data\viking-annotation\corrections``
   * - ``Builds\SectionCorrectionService\.env.Docker``
     - ``Run\viking-corrections\viking-corrections.run.env``
   * - ``Builds\SegmentationServer\.env``, ``models.json``
     - ``Run\viking-segmentation\viking-segmentation.run.env``, ``Run\viking-segmentation\models.json``
   * - ``Run\segmentation-server`` (model files)
     - ``Data\viking-segmentation\models``
   * - ``Builds\AnnotationGallery\.env``
     - copied to ``Run\sam2-gallery\sam2-gallery.run.env`` by the script, but the gallery is not a
       ``stack.ps1`` stack: start it from the Sam2Trainer repository
   * - ``Builds\ReverseProxy`` (Nginx Proxy Manager GUI, admin port 81)
     - ``viking-proxy`` stack: routes come from ``VIKING_HOSTNAME_*``; no admin UI
   * - ``*-letsencrypt`` Docker volumes
     - ``Certs\<TLS_CERT_NAME>\`` (``stack.ps1 certs ...``)
   * - ``Builds\*\rebuild-and-start.ps1``, ``restart_omni.cmd``
     - ``stack.ps1 <stack> rebuild`` / ``restart``
   * - ``Builds\nornir-build\*.ps1`` (copies of the launchers)
     - forwarding launchers written by ``Initialize-DockerHost.ps1``
   * - ``Run\nornir-dev\`` net-mount files
     - ``Run\nornir-net-mounts\`` (old location still read as a fallback)
   * - ``Builds\nornir-cursor-worker\.env.cursor-worker``
     - ``Run\nornir-cursor-worker\nornir-cursor-worker.run.env`` (old file still found)

Removed scripts and files
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - Removed (``nornir-docker/``)
     - Use instead
   * - ``Initialize-NornirBuildAppliance.ps1``
     - ``deploy/Initialize-DockerHost.ps1 -Role compute``
   * - ``link-build-env.ps1``
     - ``nornir-docker\.env``: hardlink to ``Run\nornir-dev\.env`` (:doc:`nornir_dev_and_worker`).
       Build args: run ``docker-build.ps1`` from ``Builds\nornir\``, which reads ``build.env`` /
       ``.build.<id>.env`` there
   * - ``NornirDevParityMounts.ps1``
     - built into ``start-cursor-worker.ps1 -DevParityMounts`` (``NornirDevRunMounts.ps1``)
   * - ``nd-build.sh``
     - ``nd-build.ps1`` (``pwsh nornir-docker/nd-build.ps1`` on Linux) / ``nd-build.cmd``
   * - ``legacy-interactive-container.ps1``
     - ``stack.ps1 nornir-build shell`` or ``stack.ps1 nornir-dev shell``
   * - ``dev/start.ps1``, ``prod/start.ps1``, ``nornir_cupy/start.ps1``, ``start-sample.ps1``
     - ``stack.ps1`` (deploy), ``run-cursor-dev.ps1`` (dev shell), ``docker-build.ps1`` (images)
   * - ``nornir_cupy/`` (whole folder)
     - ``prod/Dockerfile --build-arg INSTALL_CUPY=1`` (``nornir:cupy``)
   * - ``*/compose-dev.yaml``
     - ``compose.cursor-dev.yaml``, ``compose.yaml``
   * - ``*/nornir-projects.txt``, ``*/requirements.txt`` stubs
     - nothing; images install from the monorepo and ``constraints-headless.txt``
   * - ``.env.build.example``, ``.env.cursor-dev.example``, ``.env.cursor-worker.example``
     - the ``example.*.env`` templates they pointed at
   * - ``example._shared.build.env``
     - ``Builds\nornir\build.env`` (per-image templates ``*/example.<id>.build.env`` remain)
   * - ``example.dashboard.run.env``
     - ``deploy/examples/example.nornir-dashboard.run.env``

Kept on purpose: ``docker-run-nornir-dev.ps1`` (used by ``D:\Docker\Run\nornir-dev\run.ps1``),
``Cleanup-CursorWorkerClones.ps1`` (its ``-AgentCloneParent`` default now matches
``start-cursor-worker.ps1``), ``windows-docker-layout/Initialize-NornirCursorWorkerLayout.ps1``
(worker only), and ``nd-build.ps1`` / ``nd-build.cmd``.

Renamed variables
-----------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Old
     - New
   * - ``NORNIR_MONOREPO_ROOT`` (host scripts, user environment)
     - ``NORNIR_REPO_ROOT_HOST`` (old name still read, with a warning)
   * - ``-MonorepoRoot`` (``Initialize-NornirBuildAppliance.ps1``)
     - ``-RepoRoot`` (``Initialize-DockerHost.ps1``)

Viking service keys that changed with the move to ``Run/<stack>/`` are listed in the Viking
deployment docs.

Behaviour changes worth knowing
-------------------------------

* Launchers under ``Builds\nornir-build`` used to be copies and broke after ``git pull``; they are
  now forwarding launchers.
* ``nornir-build`` joins ``nornir-dashboard_default`` automatically and publishes to
  ``mosquitto`` (the old default network name did not match the compose project).
* ``nornir-build`` passes ``--shm-size=64g`` by default.
* The TEM scripts choose NumPy automatically when no GPU is present.
* ``compose.cursor-dev.yaml`` loads ``nornir-docker/.env`` with ``env_file``, so settings such as
  ``NORNIR_SYNC_REMOTE`` reach the container without editing the compose file.
