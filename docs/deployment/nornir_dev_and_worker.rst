Programmer shell and Cursor worker
==================================

Two dev-box roles, both built on ``nornir:dev-cursor-base`` (Python 3.14, CuPy, pytest, a venv,
no baked monorepo):

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Stack
     - Image / compose service
     - Use
   * - ``nornir-dev``
     - ``cursor-dev`` (or ``cursor-dev-clone``) in ``compose.cursor-dev.yaml``
     - Editable checkout, tests, Dev Containers, PyCharm Docker interpreter
   * - ``nornir-cursor-worker``
     - ``nornir:cursor-worker`` (``Dockerfile.cursor-worker``)
     - Cursor's self-hosted cloud agent: connects outbound to Cursor and runs
       ``agent worker start``

Neither is the build appliance (:doc:`nornir_build_appliance`).

Programmer shell (``nornir-dev``)
---------------------------------

Configuration: one file, bridged
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The machine-local source of truth is ``D:\Docker\Run\nornir-dev\.env``. Docker Compose and Dev
Containers only read ``nornir-docker/.env`` (the compose project folder), so that path is a
**hardlink** to the Run file::

   New-Item -ItemType Directory -Force D:\Docker\Run\nornir-dev
   Copy-Item nornir-docker\dev\example.cursor-dev.run.env D:\Docker\Run\nornir-dev\.env
   New-Item -ItemType HardLink -Path nornir-docker\.env -Target D:\Docker\Run\nornir-dev\.env

A hardlink needs both paths on the same volume; otherwise copy the file and keep the two in sync.
Junctions are directories only, and a symbolic link needs Developer Mode or an elevated shell.

``compose.cursor-dev.yaml`` uses the file twice: for ``${VAR}`` substitution in the compose file,
and as ``env_file``, so every setting in it (``NORNIR_SYNC_REMOTE``, ``NORNIR_SUBMODULE_UPDATE``,
``GITHUB_TOKEN``, ``NORNIR_TILE_*`` ...) reaches the container. Keys in the compose
``environment:`` block win over the file. There are no repo-root ``.env*.example`` stubs any more;
the template is ``nornir-docker/dev/example.cursor-dev.run.env`` (every key is in
:doc:`configuration_reference`).

Set at least ``NORNIR_TESTDATA_HOST``. Keep ``nornir-testdata`` on the **WSL2 Linux filesystem**
(not ``D:\`` through DrvFS) for stable I/O, and give Docker Desktop the
``\\wsl.localhost\<Distro>\home\<you>\nornir-testdata`` UNC path (exact distro casing from
``wsl -l -v``), or ``/home/<you>/nornir-testdata`` when you run compose from a WSL shell.

Start
~~~~~

::

   D:\Docker\stack.ps1 nornir-dev shell             # = .\nornir-docker\run-cursor-dev.ps1
   .\nornir-docker\run-cursor-dev.ps1 -Gpu
   .\nornir-docker\run-cursor-dev.ps1 -Clone        # cursor-dev-clone service

or raw compose from the monorepo root::

   docker compose -f nornir-docker/compose.cursor-dev.yaml build cursor-dev
   docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev
   docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev-clone

``run-cursor-dev.ps1`` stops when neither ``nornir-docker/.env`` nor ``NORNIR_TESTDATA_HOST`` is
set, and warns when the value is still the template placeholder. With ``NORNIR_DOCKER_USER_ROOT``
set it adds ``Run/nornir-net-mounts/compose.net-mounts.override.yaml`` (or the legacy
``Run/nornir-dev/`` copy) when present.

In the container
~~~~~~~~~~~~~~~~

* ``/workspace``: the monorepo. ``TESTINPUTPATH=/nornir-testdata`` (read-only),
  ``TESTOUTPUTPATH=/tmp/nornir-test-output`` (from ``NORNIR_TESTOUTPUT_HOST``, default
  ``D:/nornir-test-output``), ``INPUT_NORNIR_DATA=/data`` (``NORNIR_REPRO_DATA_HOST``, or an empty
  placeholder), ``/legacycode`` (read-only), ``NORNIR_HEADLESS=1``,
  ``NORNIR_LOG_ROOT=/workspace/.nornir-logs``.
* ``shm_size`` 64 GB, ``nofile`` 65536, ``gpus: all``.
* MQTT goes to the dashboard on the host (``host.docker.internal:1883``) by default.

Outside Docker on Windows, set ``INPUT_NORNIR_DATA`` yourself (for example ``D:\Data``);
``NORNIR_REPRO_DATA_HOST`` is only the bind source.

Workspace strategy
~~~~~~~~~~~~~~~~~~

``cursor-dev`` (default) bind-mounts the monorepo root (``${NORNIR_WORKSPACE_HOST:-..}``) at
``/workspace``. On start, ``cursor-dev-entry.sh``:

1. clones ``NORNIR_CLONE_URL`` / ``NORNIR_CLONE_BRANCH`` only if ``/workspace`` is empty;
2. otherwise runs ``git fetch``, and with ``NORNIR_SYNC_REMOTE=1`` checks out the clone branch and
   ``git pull --ff-only``;
3. syncs submodules: by default initializes missing ones only and keeps existing checkouts on
   their branches (warns on ``+`` in ``git submodule status``); ``NORNIR_SUBMODULE_UPDATE=1`` runs
   a full ``git submodule update --init --recursive`` (use after bumping umbrella pointers);
4. runs ``install-monorepo-editables.sh``: ``pip install -e --no-deps`` for ``nornir-shared``,
   ``nornir-pools``, ``nornir-imageregistration``, ``dm4``, ``nornir-buildmanager``.
   ``--no-deps`` matters: the ``pyproject.toml`` files pin siblings by git URL, and without it a
   later install replaces earlier editables with git checkouts.

``cursor-dev-clone`` mounts the named volume ``cursor-dev-work`` at ``/workspace`` instead:
clone on first start, fetch/checkout/pull of ``NORNIR_CLONE_BRANCH`` later
(``NORNIR_CLONE_REFRESH=1`` wipes it first), always a full submodule update. ``NORNIR_CLONE_DEPTH``
(``0`` or ``full``) controls the clone depth.

Dev Containers and PyCharm
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Default ``.devcontainer/devcontainer.json``: service ``cursor-dev``, ``workspaceFolder``
  ``/workspace``. Open the monorepo root and **Reopen in Container**.
* ``.devcontainer/cursor-dev-clone/devcontainer.json`` ("Nornir (cursor-dev clone)"): the
  named-volume clone.
* ``postAttachCommand`` reruns the editable installs on attach; reattach never resets submodules.
* PyCharm: Docker Compose interpreter on ``nornir-docker/compose.cursor-dev.yaml``, service
  ``cursor-dev``, Python ``/opt/venv/bin/python``, project mapped to ``/workspace``.

NAS shares in cursor-dev
~~~~~~~~~~~~~~~~~~~~~~~~

Same path-B mounts as the appliance (:doc:`nornir_build_appliance`). Copy
``nornir-docker/dev/example.compose.net-mounts.override.yaml`` to
``D:\Docker\Run\nornir-net-mounts\compose.net-mounts.override.yaml`` and set
``NORNIR_NET_MOUNTS_DIR_HOST`` / ``NORNIR_NET_CREDS_DIR_HOST`` in ``Run\nornir-dev\.env``.
``run-cursor-dev.ps1`` picks the override up; by hand::

   docker compose -f nornir-docker/compose.cursor-dev.yaml -f D:/Docker/Run/nornir-net-mounts/compose.net-mounts.override.yaml run --rm cursor-dev

The override is the only thing that grants ``CAP_SYS_ADMIN``; plain ``cursor-dev`` stays
unprivileged.

``docker-run-nornir-dev.ps1``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The older ``docker run`` path for ``nornir:dev`` (baked packages) is kept for
``D:\Docker\Run\nornir-dev\run.ps1``. It reads ``.run.nornir-dev.env`` and ``secrets.env`` from
the directory you call it in, and optionally publishes ports from ``NORNIR_DEV_PORT_PUBLISH``.

Headless tests in the container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* The image sets ``NORNIR_HEADLESS=1`` and ships no PyQt6. ``nornir-pyre/conftest.py`` skips
  collecting the Qt/OpenGL driver scripts (``*_qt.py``, ``test_qopengl.py``, ``test_enum*.py``)
  and ``test_pure_units.py`` when PyQt6 is missing. Mark future display tests
  ``@pytest.mark.graphical`` and skip them with the ``is_headless()`` rules
  (``nornir_imageregistration/headless.py``).
* PyOpenGL with ``PYOPENGL_PLATFORM=osmesa`` lets ``OpenGL.GL`` load without a display.
* Root ``pytest.ini`` collects ``nornir-buildmanager/tests`` (the ``tests`` package), not the
  whole package tree.
* CuPy JIT needs ``libnvrtc.so`` from the NVIDIA Container Toolkit at run time. ``libnvrtc`` or
  ``cudaErrorInsufficientDriver`` errors mean the host driver is too old for the wheel's CUDA
  generation; upgrade it or run GPU-free subsets.
* Tracebacks showing ``D:\...`` paths inside Linux come from stale ``__pycache__`` written by a
  Windows interpreter; delete the ``__pycache__`` trees.

Cursor worker (``nornir-cursor-worker``)
----------------------------------------

Layout
~~~~~~

Run ``Initialize-NornirCursorWorkerLayout.ps1`` once (Developer Mode or elevated, for the
symlinks). It is worker-only; everything else uses ``Initialize-DockerHost.ps1``::

   & .\nornir-docker\windows-docker-layout\Initialize-NornirCursorWorkerLayout.ps1 -ScriptsRepoRoot D:\src\git\nornir -DockerUserRoot D:\Docker

.. list-table::
   :header-rows: 1
   :widths: 46 54

   * - Path
     - Contents
   * - ``D:\Docker\Builds\nornir\``
     - Image build overrides (``build.env``, ``.build.nornir-dev-cursor-base.env``,
       ``.build.nornir-cursor-worker.env``) and ``build-nornir-images.ps1`` (link to
       ``docker-build.ps1``)
   * - ``D:\Docker\Builds\nornir-cursor-worker\``
     - ``start-nornir-cursor-worker.ps1`` launcher link
   * - ``D:\Docker\Run\nornir-cursor-worker\nornir-cursor-worker.run.env``
     - ``CURSOR_API_KEY``, ``GITHUB_TOKEN``, clone settings
   * - ``D:\Docker\mounted-configs\nornir-cursor-worker\``
     - Per-run workspaces (``nornir-cursor-worker-<stamp>-<guid>``) and host clones
       (``nornir-agent-*``). The worker still uses ``mounted-configs``; only ``nornir-build``
       moved to ``Work/``.

``start-cursor-worker.ps1`` finds the run env in this order: ``-EnvFilePath``,
``NORNIR_CURSOR_WORKER_ENV_FILE``, ``Run/nornir-cursor-worker/nornir-cursor-worker.run.env``,
legacy ``Builds/nornir-cursor-worker/.env.cursor-worker``, ``nornir-docker/.env.cursor-worker``.
``GITHUB_TOKEN`` / ``GH_TOKEN`` are never loaded into the host process (Git Credential Manager
would pick them up); they reach the container only through ``--env-file``.

Build and run
~~~~~~~~~~~~~

::

   cd D:\Docker\Builds\nornir
   .\build-nornir-images.ps1 -Images cursor-worker       # also builds dev-cursor-base

   D:\Docker\stack.ps1 nornir-cursor-worker up           # = Builds\nornir-cursor-worker\start-nornir-cursor-worker.ps1

The thin launcher calls ``start-cursor-worker.ps1 -LiveMount -UseUniqueWorkspaceFolder``: a new
empty folder under ``mounted-configs\nornir-cursor-worker`` is mounted at ``/workspace`` and the
entrypoint clones from GitHub into it (not from your dev checkout).

``start-cursor-worker.ps1`` modes:

* default: host ``git clone`` into a unique folder under ``-AgentCloneParent``, mounted with the
  ``mounted`` strategy;
* ``-LiveMount``: mount ``-WorkspaceMountPath`` (or the repo root);
* ``-LiveMount -UseUniqueWorkspaceFolder``: empty per-run folder under ``-WorkspaceRunParent``,
  ``clone`` strategy;
* ``-UseNamedDockerVolume``: named volume at ``/workspace``;
* ``-RemoveCloneAfter``: delete the per-run folder after exit, unless ``git status --porcelain``
  shows changes;
* ``-Rebuild``, ``-Gpu``, ``-SmokeTest``, ``-CloneUrl``, ``-CloneBranch``, ``-Detach``,
  ``-KeepContainer``;
* ``-DevParityMounts`` (or ``NORNIR_WORKER_DEV_PARITY_MOUNTS=1``): the same testdata, ``/data``,
  test output, and in-container CIFS mounts as cursor-dev, read from
  ``Run/nornir-net-mounts/.run.nornir-net-mounts.env`` and ``nornir-docker/.env``.

Workspace strategies inside the container (``NORNIR_WORKSPACE_STRATEGY``): ``clone`` (default;
clone into an empty ``/workspace``, else fetch/checkout/pull; ``NORNIR_CLONE_REFRESH=1`` wipes
first) and ``mounted`` (existing checkout; ``git fetch``, ``git pull --ff-only`` with
``NORNIR_SYNC_REMOTE=1``).

Compose (no dev-parity mounts)::

   $env:NORNIR_CURSOR_WORKER_ENV_FILE = 'D:\Docker\Run\nornir-cursor-worker\nornir-cursor-worker.run.env'
   docker compose -f nornir-docker/compose.cursor-worker.yaml build nornir-cursor-base nornir-cursor-worker
   docker compose -f nornir-docker/compose.cursor-worker.yaml run --rm nornir-cursor-worker

Cleaning up worker folders
~~~~~~~~~~~~~~~~~~~~~~~~~~

``nornir-docker/Cleanup-CursorWorkerClones.ps1`` removes ``nornir-cursor-worker-*`` and
``nornir-agent-*`` folders under ``<root>\mounted-configs\nornir-cursor-worker`` (override with
``-WorkspaceRunParent`` / ``-AgentCloneParent``). It skips any folder that is a bind source of any
container (running or stopped) and any git checkout with a non-empty ``git status --porcelain``.
Run it with ``-WhatIf`` first; ``-Confirm:$false`` skips the prompts.
