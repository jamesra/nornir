Cursor / local agent dev shell
==============================

``compose.cursor-dev.yaml`` defines two services for a local Docker shell that mirrors the layout in ``.cursor/environment.json``:

- Monorepo at ``/workspace``
- Read-only test input at ``/nornir-testdata``
- Optional read-only reproduction corpus at ``/data`` (``INPUT_NORNIR_DATA=/data``)
- ``TESTINPUTPATH`` / ``TESTOUTPUTPATH`` set consistently

This is for **manual** ``docker compose run`` workflows and for **Dev Containers** in Cursor/VS Code; the in-IDE Cursor Agent uses the **host** terminal unless you adopt Dev Containers or Remote.

Workspace strategy
------------------

**cursor-dev (default)** bind-mounts the **monorepo root** (parent of ``nornir-docker/``) at ``/workspace`` using ``${NORNIR_WORKSPACE_HOST:-..}``, so the container sees the same sources as your host checkout. On start, ``cursor-dev-entry.sh`` runs ``git fetch`` only; it does **not** switch branches unless you set ``NORNIR_SYNC_REMOTE=1`` (then it checks out ``NORNIR_CLONE_BRANCH`` and ``git pull --ff-only``).

On **container recreate** (not reattach), submodule handling for the bind-mounted service is:

- **Default:** initialize missing submodules only; existing checkouts stay on their branches.
- **``NORNIR_SUBMODULE_UPDATE=1``:** full ``git submodule update --init --recursive`` (match umbrella-recorded SHAs). Use after bumping umbrella pointers (see ``.cursor/rules/Monorepo-submodule-changes.mdc``).
- **Reattach** via Dev Containers ``postAttachCommand`` runs editable installs only; it does **not** reset submodules.

**cursor-dev-clone** mounts a **named Docker volume** (``cursor-dev-work``) at ``/workspace``. On first start, ``cursor-dev-entry.sh`` clones with ``NORNIR_CLONE_URL`` / ``NORNIR_CLONE_BRANCH`` (defaults ``https://github.com/jamesra/nornir.git`` / ``dev``); on later starts it refreshes that branch (clone strategy) and runs a full submodule update. Use this for an isolated tree or when you do not want to bind-mount the host repo.

**Dev Containers:** default ``.devcontainer/devcontainer.json`` uses service **cursor-dev**. To open a dev container backed by **cursor-dev-clone**, use **Dev Containers: Reopen in Container** (or reopen with configuration) and pick **Nornir (cursor-dev clone)** (``.devcontainer/cursor-dev-clone/devcontainer.json``). The editor workspace folder is still the path you opened on the host; only the container's ``/workspace`` differs between bind and clone modes.

Dev Containers: default vs clone config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Default (bind):** ``.devcontainer/devcontainer.json`` / service ``cursor-dev`` — your host monorepo root is visible at ``/workspace``.
- **Fresh clone:** ``.devcontainer/cursor-dev-clone/devcontainer.json`` / service ``cursor-dev-clone`` — ``/workspace`` is the named volume with a clone from ``NORNIR_CLONE_URL`` (see Workspace strategy above). In Cursor or VS Code, use the command palette to pick the configuration when reopening in a container.

WSL2 test data (recommended)
----------------------------

Keep **nornir-testdata** on the **WSL2 Linux filesystem** (not ``D:\\...`` / DrvFS) and mount it read-only at ``/nornir-testdata``.

Copy ``nornir-docker/dev/example.cursor-dev.run.env`` to ``nornir-docker/.env`` and set ``NORNIR_TESTDATA_HOST`` to that Linux path (use ``echo $HOME`` in WSL to build a full path). The flat ``nornir-docker/.env.cursor-dev.example`` file remains a pointer to the same template.

**Reproduction corpus (optional):** set ``NORNIR_REPRO_DATA_HOST`` in the same ``.env`` to a **WSL/Linux** path whose contents mirror the Windows corpus (for example what you keep under ``D:\\Data``). Compose mounts it read-only at ``/data`` and sets ``INPUT_NORNIR_DATA=/data`` so tests and scripts can build paths without hard-coding a drive letter. If ``NORNIR_REPRO_DATA_HOST`` is unset, compose uses a tiny placeholder directory so the stack still starts; ``/data`` is then empty until you set a real host path. For pytest on Windows **outside** Docker, set ``INPUT_NORNIR_DATA`` yourself (for example ``D:\\Data``).

On start, ``cursor-dev-entry.sh`` runs ``install-monorepo-editables.sh``, which ``pip install -e --no-deps`` each monorepo package from ``/workspace`` (``nornir-shared``, ``nornir-pools``, ``nornir-imageregistration``, ``dm4``, ``nornir-buildmanager``). ``--no-deps`` is required because ``pyproject.toml`` files reference sibling packages via git URLs; without it, a later editable install can replace earlier ones with non-editable git checkouts. Dev Containers also run the same install on attach via ``postAttachCommand`` in ``.devcontainer/devcontainer.json``.

Build (from monorepo root)::

    docker compose -f nornir-docker/compose.cursor-dev.yaml build cursor-dev

Interactive shell::

    docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev

Named-volume clone service::

    docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev-clone

With GPU::

    docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm --gpus all cursor-dev

PowerShell helper (checks for ``nornir-docker/.env`` or ``NORNIR_TESTDATA_HOST``)::

    .\nornir-docker\run-cursor-dev.ps1
    .\nornir-docker\run-cursor-dev.ps1 -Gpu
    .\nornir-docker\run-cursor-dev.ps1 -Clone
    .\nornir-docker\run-cursor-dev.ps1 -Clone -Gpu

Test data
---------

``NORNIR_TESTDATA_HOST`` must be set (via ``nornir-docker/.env``—see ``nornir-docker/dev/example.cursor-dev.run.env``). Use a path on the **WSL2** filesystem when developing under WSL; ensure Docker Desktop **file sharing** allows that path if prompted.

**Test output:** compose bind-mounts ``${NORNIR_TESTOUTPUT_HOST:-D:/nornir-test-output}`` to ``/tmp/nornir-test-output`` (``TESTOUTPUTPATH``). Create the host directory if needed. When you run ``docker compose`` from WSL, set ``NORNIR_TESTOUTPUT_HOST=/mnt/d/nornir-test-output`` (or another Linux path) in ``nornir-docker/.env`` instead of the Windows ``D:/`` form.

``INPUT_NORNIR_DATA`` is the root path for the **optional** large reproduction dataset used by some tests (for example arrange tests that fall back from ``TESTINPUTPATH``). In cursor-dev, compose sets ``INPUT_NORNIR_DATA=/data``. On Windows hosts running pytest without Docker, set ``INPUT_NORNIR_DATA`` to your corpus root (commonly ``D:\Data``). ``NORNIR_REPRO_DATA_HOST`` in ``.env`` is only the **host** bind source for ``/data``; it does not replace setting ``INPUT_NORNIR_DATA`` when you run tests on the host outside Compose.

Headless pytest and nornir-pyre
-------------------------------

The cursor-dev image sets ``NORNIR_HEADLESS=1`` and does not ship PyQt6 for OpenGL/Qt UI tests. Umbrella ``pytest`` still includes ``nornir-pyre`` on ``testpaths`` / ``pythonpath``.

- **Pure logic** tests (for example ``nornir-pyre/tests/test_pure_units.py`` and the transform/STOS helpers in ``nornir-pyre/test_comprehensive_menu.py``) are intended to run in that environment.
- **Qt/OpenGL driver scripts** under ``nornir-pyre/tests/`` (files named ``*_qt.py``, ``test_qopengl.py``, ``test_enum.py``, ``test_enum2.py``) are **not** pytest suites; they import PyQt at import time. ``nornir-pyre/conftest.py`` registers ``pytest_ignore_collect`` so those modules are **never collected**, which avoids import failures when PyQt is absent.
- For future real pytest items that need a display, use ``@pytest.mark.graphical`` (registered in the root ``pytest.ini``) and ``@pytest.mark.skipif(...)`` using the same rules as ``nornir_imageregistration.headless.is_headless`` (``NORNIR_HEADLESS`` plus non-Windows ``DISPLAY``)—``nornir-pyre/conftest.py`` defines a matching ``is_headless()`` for hooks and for local skips. The reference pattern for headless **file** output (PNG artifacts, ``inspect_png_output``) lives under ``nornir-imageregistration`` (see ``nornir_imageregistration/headless.py`` and view tests that branch on ``is_headless()``).

The dev image installs **PyOpenGL**, **libgl1**, **libosmesa6**, and sets ``PYOPENGL_PLATFORM=osmesa`` so ``OpenGL.GL`` can load headlessly. ``nornir-pyre/tests/test_pure_units.py`` still imports **PyQt6** via ``gl_engine``; the headless image does not ship PyQt6, so ``nornir-pyre/conftest.py`` **skips collecting** ``test_pure_units.py`` when ``PyQt6`` is not installed. Install PyQt6 in the environment if you need that module collected. Real GPU-backed GL contexts are not the goal in this image; use ``@pytest.mark.graphical`` and skips for anything that needs a display.

No extra ``PYTEST_ADDOPTS`` is required for cursor-dev for this layout: graphical driver files are excluded at collection time instead of installing Qt in the headless image.

Umbrella pytest, CuPy, and bind-mounted checkouts
-------------------------------------------------

**nornir-buildmanager:** Root ``pytest.ini`` lists ``nornir-buildmanager/tests`` on ``testpaths`` (not the whole ``nornir-buildmanager`` tree). The canonical layout uses the ``tests`` package and ``tests.testbase``; do not point umbrella collection at a stray legacy tree missing those helpers.

**CuPy / ``libnvrtc``:** The image installs ``cupy-cuda13x``. JIT and many kernels need **``libnvrtc.so``**, which normally comes from the **NVIDIA Container Toolkit** when the container is started with GPU access (``compose.cursor-dev.yaml`` sets ``gpus: all`` on ``cursor-dev`` / ``cursor-dev-clone``; manual ``docker compose run`` still needs a working GPU driver on the host). If you see ``DynamicLibNotFoundError: libnvrtc`` or ``cudaErrorInsufficientDriver``, upgrade the **host** NVIDIA driver to one that supports the CUDA generation used by the wheel, or run GPU-free subsets until the driver and toolkit injection match. Tests that probe CUDA at import time fall back to NumPy thunks when CuPy is present but initialization fails (see ``nornir-imageregistration/tests/test_local_distortion.py``); the ``tests`` package ``__init__`` does not import that module eagerly, so sibling tests (for example under ``tests/settings/``) collect without initializing CUDA.

**Windows paths in Linux tracebacks:** If the repo is bind-mounted from Windows into a Linux container and tracebacks show ``D:\\...`` while the process runs on Linux, clear stale ``__pycache__`` / ``*.pyc`` trees on the host (or under ``/workspace``) so line metadata is not carried from a prior Windows interpreter run.
