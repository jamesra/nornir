Image catalogue
===============

All images are built from the monorepo root (context ``.``).

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Image tag
     - Dockerfile
     - Notes
   * - ``nornir:dev``
     - ``dev/Dockerfile``
     - CuPy (``cupy-cuda13x`` by default) + pytest. Use ``--gpus all`` / ``nd-build -Gpu`` for GPU.
   * - ``nornir:prod``
     - ``prod/Dockerfile``
     - CPU-only production (``INSTALL_CUPY=0``, default).
   * - ``nornir:cupy``
     - ``prod/Dockerfile`` with ``--build-arg INSTALL_CUPY=1``
     - Production + CuPy.
   * - ``nornir:dev-cursor-base``
     - ``dev/Dockerfile`` with ``INSTALL_MONOREPO_EDITABLES=0``
     - CuPy + pytest + venv **without** baking the monorepo; base for ``cursor-worker``.
   * - ``nornir:cursor-worker``
     - ``Dockerfile.cursor-worker``
     - ``dev-cursor-base`` + Cursor lab agent CLI; packages come from ``/workspace`` at start.

Packages baked into ``nornir:dev``, ``nornir:prod``, and ``nornir:cupy`` (from the monorepo at build time):
``nornir_shared``, ``nornir_pools``, ``nornir_imageregistration``, ``dm4``, ``nornir_buildmanager``.
``nornir:cursor-worker`` and ``nornir:dev-cursor-base`` do **not** bake those; they install editables from ``/workspace`` at container start.

Monorepo version and package map
---------------------------------

- ``VERSION`` at the monorepo root — single-line release id (e.g. ``1.7.0``). Release tags use ``v`` + that value (``v1.7.0``).
- ``release/package-versions.yaml`` — bill of materials (each distribution version, ``docker: true/false``).
- ``release/README.md`` — release checklist.

Build commands
--------------

Recommended (OCI labels + BOM JSON) — run from ``nornir-docker/`` (or any directory; the script captures the current directory before changing to the monorepo root)::

    .\docker-build.ps1     # PowerShell
    build.cmd              # cmd

Build only selected tags with ``-Images`` (catalogue order; skips everything else).
Names may be short (``prod``), ``nornir:prod``, or ``nornir-prod``. Selecting
``cursor-worker`` also builds ``dev-cursor-base`` first. ``prod`` / ``cupy`` do
**not** require ``nornir:dev``::

    .\docker-build.ps1 -Images prod,cupy

Force a clean rebuild of those tags::

    .\docker-build.ps1 -Images prod,cupy -NoCache

After each successful image, the script prints ``Id`` / ``Created`` / OCI labels and also tags
``nornir:<name>-<VERSION>`` (from the monorepo ``VERSION`` file). ``docker-push.ps1`` prints the
same local metadata before push and warns if the floating tag looks stale.

Optional build-arg overrides: place ``build.env`` (shared) and ``.build.<id>.env`` per image (``<id>`` is the tag with ``:`` replaced by ``-``, e.g. ``.build.nornir-dev.env``) in that **invocation** directory. The script does not read committed ``example.*.build.env`` files; use those files in the repo only as templates.

Minimal samples (Compose / same builds from repo root)::

    .\nornir-docker\start-sample.ps1 -Sample List

This reads ``VERSION``, git SHA, build time, and embeds a base64-encoded JSON bill of materials.

Manual ``docker build`` (from monorepo root)::

    docker build -f nornir-docker/dev/Dockerfile -t nornir:dev .
    docker build -f nornir-docker/prod/Dockerfile -t nornir:prod .
    docker build -f nornir-docker/prod/Dockerfile --build-arg INSTALL_CUPY=1 -t nornir:cupy .

Override the CuPy wheel (default ``cupy-cuda13x``)::

    docker build -f nornir-docker/dev/Dockerfile --build-arg CUPY_PACKAGE=cupy-cuda12x -t nornir:dev .

OCI image labels
-----------------

Images declare `OCI annotations <https://github.com/opencontainers/image-spec/blob/main/annotations.md>`_
including ``org.opencontainers.image.version``, ``org.opencontainers.image.revision``,
``org.opencontainers.image.source``, ``org.opencontainers.image.created``,
``org.nornir.variant``, and ``org.nornir.package_versions.json.base64``
(base64-encoded JSON map of docker-included packages).

Inspect (PowerShell)::

    docker image inspect nornir:dev --format '{{json .Config.Labels}}'

Decode the BOM::

    $b64 = (docker image inspect nornir:dev --format '{{index .Config.Labels "org.nornir.package_versions.json.base64"}}')
    [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))

Running ``nornir:dev`` interactively (bind mounts)
--------------------------------------------------

The ``nornir:dev`` image **bakes** the monorepo packages under ``/opt/nornir`` at **build** time.
It does **not** clone sources into ``/workspace`` on start: the default command is ``bash`` only,
so ``WORKDIR /workspace`` is usually an **empty** directory unless you mount something there.

- **Empty ``/workspace``** — If you bind-mount an empty host folder at ``/workspace``, the
  container shell will show an empty tree. Mount your **actual monorepo checkout** instead
  (same layout as the build context), e.g. ``-v D:\src\git\nornir:/workspace``, then work or
  re-run ``pip install -e`` on packages from ``/workspace`` if you need editables against the
  mount.

- **Clone into an empty mount** — The image ships ``/usr/local/bin/cursor-dev-entry.sh`` (same
  script used by the Cursor dev compose flow). It is **not** the default ``CMD``; run it
  explicitly so an empty ``/workspace`` is populated by ``git clone`` (requires network and
  ``NORNIR_CLONE_URL`` / ``NORNIR_CLONE_BRANCH`` if you override defaults), then drops into
  your shell, for example (one line, or use ``^`` continuation in ``cmd`` / backtick in PowerShell)::

    docker run --rm -it --env-file secrets.env --env-file .env.run.nornir-dev -v "D:\Docker\mounted-configs\nornir-dev:/workspace" -w /workspace nornir:dev /usr/local/bin/cursor-dev-entry.sh bash

  If the mount is **non-empty** and not a git repo, the script refuses to clone (see script
  error text); use an empty directory or a real checkout.

- **``/nornir-testdata``** — Nothing in ``nornir:dev`` creates this path. For tests that need
  ``TESTINPUTPATH`` (often ``/nornir-testdata``), add a **second** read-only bind mount from
  the host (WSL Linux paths are recommended on Docker Desktop) and set the env vars, e.g. in
  your env file::

    TESTINPUTPATH=/nornir-testdata
    TESTOUTPUTPATH=/tmp/nornir-test-output

  ``compose.cursor-dev.yaml`` bind-mounts ``NORNIR_TESTOUTPUT_HOST`` (default ``D:/nornir-test-output``) to that path.

  and::

    -v "//wsl$/Ubuntu/home/you/nornir-testdata:/nornir-testdata:ro"

  Or use ``docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev``, which
  wires ``NORNIR_TESTDATA_HOST``, ``TESTINPUTPATH``, and ``cursor-dev-entry.sh`` for bind-mounted sources (service **cursor-dev**), or use ``cursor-dev-clone`` for a named-volume clone (see
  :doc:`cursor_dev`).

GPU runtime
-----------

Use ``nd-build -Gpu`` / ``NORNIR_DOCKER_GPU=1`` or ``docker run --gpus all`` to expose NVIDIA
devices. A GPU is **not** required at image build time.
