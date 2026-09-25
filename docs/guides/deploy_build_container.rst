Deploy the build container
==========================

This is the production box that runs ``nornir-build`` against volumes on a NAS. It is not the programmer Dev Container and not the Cursor worker. Host checks are in :doc:`../host_requirements`. Variable tables, open-file limits, and the troubleshooting list stay in :doc:`../docker/remote_deployment`.

One-time setup
--------------

1. Install Docker Desktop with WSL2. Load the CIFS module in WSL (``modprobe cifs``) if this machine will mount NAS shares. Install an NVIDIA driver only when you want the GPU image. Git is required to clone the scripts.
2. Clone the monorepo with submodules. The container images are pulled from GHCR. You do not build them on this machine. If the pull asks you to log in::

     docker login ghcr.io -u <github-user>

   The token needs ``read:packages``.
3. From the monorepo, run the initializer once. It creates the local Docker layout, pulls the images, and starts the dashboard::

     .\nornir-docker\Initialize-NornirBuildAppliance.ps1

   Press Enter to use the parent of ``nornir-docker`` as the monorepo root, or pass ``-MonorepoRoot``.
4. Edit only the site files under ``NORNIR_DOCKER_USER_ROOT`` (default ``C:\Docker``; many lab machines set ``D:\Docker``):

   * ``Run\nornir-net-mounts\net-mounts\nas-mounts.tsv`` — which shares to mount
   * ``Run\nornir-net-mounts\secrets\net-creds\*.cred`` — credentials for those shares
   * ``Run\nornir-net-mounts\.run.nornir-net-mounts.env`` — only when a host path is not the default

   The committed template is ``nornir-docker/example.nornir-net-mounts.run.env``.

Every session
-------------

::

   & "$env:NORNIR_DOCKER_USER_ROOT\Builds\nornir-build\start-nornir-build.ps1"

The launcher probes the GPU. A usable NVIDIA GPU selects ``nornir:cupy``. Otherwise it selects the CPU image ``nornir:prod``. It mounts the shares from inside the container and opens a shell.

Confirm the shell before starting a build:

* ``echo "$NORNIR_NET_MOUNTS"`` prints ``1``.
* ``findmnt -t cifs`` lists the shares from ``nas-mounts.tsv``.
* The dashboard is at http://127.0.0.1:8087.
* ``TEMImport``, ``TEMBuild``, ``TEMBuild-import``, and ``TEMAlign`` are on ``PATH``.

Those four commands are the lab build. What each stage does is :doc:`tem_scripts`.

To refresh images later without re-running the initializer::

   .\nornir-docker\docker-pull.ps1 -IncludeDashboard -ContinueOnError

Pass ``-PreferVersioned`` to pin the pull to the monorepo ``VERSION``.
