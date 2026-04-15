Cursor / local agent dev shell
==============================

``compose.cursor-dev.yaml`` defines a **cursor-dev** service for a local Docker shell that mirrors the layout in ``.cursor/environment.json``:

- Monorepo at ``/work``
- Read-only test input at ``/nornir-testdata``
- ``TESTINPUTPATH`` / ``TESTOUTPUTPATH`` set consistently

This is for **manual** ``docker compose run`` workflows; the in-IDE Cursor Agent uses the **host** terminal unless you adopt Dev Containers or Remote.

On start, ``cursor-dev-entry.sh`` reinstalls editable packages from ``/work`` in the same order as ``dev/Dockerfile``, so host edits are immediately reflected in Python imports inside the container.

Build (from monorepo root)::

    docker compose -f nornir-docker/compose.cursor-dev.yaml build nornir

Interactive shell::

    docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm cursor-dev

With GPU::

    docker compose -f nornir-docker/compose.cursor-dev.yaml run --rm --gpus all cursor-dev

Test data
---------

By default ``D:/nornir-testdata`` is bind-mounted read-only at ``/nornir-testdata``.
Override with **``NORNIR_TESTDATA_HOST``** (see ``.env.cursor-dev.example``). Ensure Docker Desktop file sharing allows that drive.
