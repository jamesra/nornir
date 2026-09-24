``nd-build`` — run nornir-build inside Docker
==============================================

``nd-build`` runs the same CLI as ``nornir-build`` but **inside** a Docker container, mounting the current directory at ``/workspace``.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Where it runs
   * - ``nornir-build``
     - Local install / venv on the host
   * - ``nd-build``
     - Same CLI **inside** Docker; current directory mounted at ``/workspace``

Default image is ``nornir:dev`` (CuPy + pytest). Use ``NORNIR_DOCKER_IMAGE=nornir:prod`` for CPU-only.

Host wrappers (from repo root)::

    .\nornir-docker\nd-build.ps1 -- --help
    .\nornir-docker\nd-build.cmd -- --help

Environment variables
---------------------

- ``NORNIR_DOCKER_IMAGE`` — default ``nornir:dev``; set to ``nornir:prod`` for CPU-only.
- ``NORNIR_DOCKER_GPU=1`` — same as ``-Gpu`` (PowerShell) or ``--gpu`` (sh).
- ``NORNIR_DOCKER_EXTRA_ARGS`` — optional extra ``docker run`` tokens.

Compose alternative::

    docker compose -f nornir-docker/compose.yaml run --rm -v "$PWD:/workspace" -w /workspace nornir nornir-build --help

Add ``--gpus all`` for GPU with the dev image; use service ``nornir-prod`` for CPU-only.
