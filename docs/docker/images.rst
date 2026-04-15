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
``nornir:cursor-worker`` does **not** bake those; it installs editables from ``/workspace`` at container start.

Monorepo version and package map
---------------------------------

- ``VERSION`` at the monorepo root — single-line release id (e.g. ``1.7.0``). Release tags use ``v`` + that value (``v1.7.0``).
- ``release/package-versions.yaml`` — bill of materials (each distribution version, ``docker: true/false``).
- ``release/README.md`` — release checklist.

Build commands
--------------

Recommended (OCI labels + BOM JSON) — run from ``nornir-docker/``::

    .\docker-build.ps1     # PowerShell
    build.cmd              # cmd

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

GPU runtime
-----------

Use ``nd-build -Gpu`` / ``NORNIR_DOCKER_GPU=1`` or ``docker run --gpus all`` to expose NVIDIA
devices. A GPU is **not** required at image build time.
