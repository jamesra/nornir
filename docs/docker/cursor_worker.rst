Cursor self-hosted cloud agent worker
======================================

The ``nornir:cursor-worker`` image is for Cursor's **self-hosted cloud agent** process. It differs from the ``cursor-dev`` dev shell: it connects **outbound** to Cursor and runs ``agent worker start`` after preparing ``/workspace``.

Components
----------

- ``Dockerfile.cursor-worker`` — ``FROM nornir:dev-cursor-base`` (venv + CuPy, no monorepo snapshot). Adds ``git``, ``curl``, and the Cursor lab ``agent-cli-package``.
- ``cursor-worker-entry.sh`` — Entrypoint. Requires ``CURSOR_API_KEY``.

Workspace strategies (``NORNIR_WORKSPACE_STRATEGY``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``clone`` (default)
    Empty ``/workspace`` → clone from ``NORNIR_CLONE_URL`` (default ``https://github.com/jamesra/nornir.git``) branch ``NORNIR_CLONE_BRANCH`` (default ``dev``). Existing ``.git`` → fetch/checkout/pull. ``NORNIR_CLONE_REFRESH=1`` wipes ``/workspace``.

``mounted``
    Host bind-mount at ``/workspace`` with an existing checkout. Empty mount → same clone flow. Existing repo → ``git fetch``; ``NORNIR_SYNC_REMOTE=1`` does ``git pull --ff-only``.

Secrets
-------

Copy ``.env.cursor-worker.example`` to ``nornir-docker/.env.cursor-worker`` (gitignored). Set at minimum:

- ``CURSOR_API_KEY``
- ``GITHUB_TOKEN`` (optional; for private submodules or rate limits)

.. warning::

   Never commit real tokens. The ``GITHUB_TOKEN`` / ``GH_TOKEN`` variables are passed into the container only via ``--env-file``; they are never loaded onto the host process by the launcher scripts.

Build::

    docker build -f nornir-docker/dev/Dockerfile --build-arg INSTALL_MONOREPO_EDITABLES=0 -t nornir:dev-cursor-base .
    docker build -f nornir-docker/Dockerfile.cursor-worker -t nornir:cursor-worker .

Compose (build then run)::

    docker compose -f nornir-docker/compose.cursor-worker.yaml build nornir-cursor-base nornir-cursor-worker
    docker compose -f nornir-docker/compose.cursor-worker.yaml run --rm nornir-cursor-worker

PowerShell launcher ``start-cursor-worker.ps1``
------------------------------------------------

``start-cursor-worker.ps1`` has several modes:

- **Default:** host ``git clone`` into a unique directory under ``D:\agents`` (override with ``-AgentCloneParent``), bind-mount at ``/workspace``, pass ``NORNIR_WORKSPACE_STRATEGY=mounted``.
- ``-LiveMount``: bind-mount ``WorkspaceMountPath`` or ``RepoRoot`` at ``/workspace``, ``mounted`` strategy.
- ``-LiveMount -UseUniqueWorkspaceFolder``: empty unique folder per run under ``WorkspaceRunParent`` (default ``D:\Docker\mounted-configs\nornir-cursor-worker``), mount at ``/workspace``, ``clone`` strategy.
- ``-UseNamedDockerVolume``: named Docker volume at ``/workspace``, ``clone`` strategy.
- ``-RemoveCloneAfter``: delete isolated host clone or per-run folder after exit (skipped if ``git status --porcelain`` is non-empty; see ``CursorWorkerWorkspaceGit.ps1``).
- ``-Rebuild``: builds ``nornir:dev-cursor-base`` then ``nornir:cursor-worker``.
- ``-Gpu``, ``-SmokeTest``, ``-CloneUrl``, ``-CloneBranch``.

For the **standard Windows ``D:\`` layout**, see :doc:`windows_cursor_layout`.

Cleanup script ``Cleanup-CursorWorkerClones.ps1``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``nornir-docker/Cleanup-CursorWorkerClones.ps1`` on the **host** to remove leftover disposable workspace folders when:

- **Docker:** ``docker`` must be on ``PATH``. The script scans **all** containers (running and stopped), collects each bind mount ``Source``, and **never** deletes a directory whose normalized path is still a bind source.
- **Git:** Same rules as ``-RemoveCloneAfter``, implemented in ``CursorWorkerWorkspaceGit.ps1`` (``Get-CursorWorkerRemoveCloneAfterDisposition``): delete if there is no ``.git``, or if ``git status --porcelain`` is empty; otherwise skip.

**Scope (name patterns):** under ``WorkspaceRunParent`` (default ``D:\Docker\mounted-configs\nornir-cursor-worker``), only directories named ``nornir-cursor-worker-*``; under ``AgentCloneParent`` (default ``D:\agents``), only ``nornir-agent-*``. Override parents with ``-WorkspaceRunParent`` and ``-AgentCloneParent``.

**Safety:** Use ``-WhatIf`` to list removals without deleting. Confirmation uses ``ShouldProcess`` (``-Confirm:$false`` to skip prompts).
