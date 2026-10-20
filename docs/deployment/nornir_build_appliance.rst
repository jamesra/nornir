Build appliance (``nornir-build``)
==================================

The production box that runs ``nornir-build`` against volumes on the NAS: ``compute`` (Ubuntu,
GPU), or a Windows workstation with Docker Desktop and WSL2. It is not the programmer shell and
not the Cursor worker (:doc:`nornir_dev_and_worker`); keep the roles separate.

.. list-table::
   :header-rows: 1
   :widths: 22 48 30

   * - Role
     - Image
     - Launcher
   * - Build appliance (GPU)
     - ``nornir:cupy``: production packages + CuPy (``cupy-cuda13x``) + cuVS. CUDA 13 needs compute
       capability 7.5 or newer (Turing and later); plan on 7.5+ for the GPU mesh and transform
       paths.
     - ``stack.ps1 nornir-build`` (``start-nornir-build.ps1``)
   * - Build appliance (CPU)
     - ``nornir:prod``: CPU only, no CuPy.
     - same
   * - Live packages (rare)
     - ``nornir:dev-cursor-base`` with ``start-nornir-build.ps1 -Clone``: clones the monorepo into
       the session folder and installs editables from it.
     - ``start-nornir-build.ps1 -Clone [-CloneBranch <b>]``

Images come from GHCR; the appliance does not build them. Image tags and how they are built are
in :doc:`../docker/images`.

One-time setup
--------------

Ubuntu (``compute``)
~~~~~~~~~~~~~~~~~~~~

Steps 2 to 4 of :doc:`index` cover this host. In short::

   sudo ubuntu-drivers install && sudo reboot
   sudo bash bootstrap-ubuntu.sh --user deploy --gpu      # Docker, pwsh, cifs-utils, NVIDIA toolkit
   # re-login, clone /srv/src/nornir and /srv/src/Viking
   pwsh /srv/src/nornir/nornir-docker/deploy/Initialize-DockerHost.ps1 -Role compute -VikingRepoRoot /srv/src/Viking -SetUserEnv
   echo cifs | sudo tee /etc/modules-load.d/nornir-cifs.conf
   sudo modprobe cifs && grep cifs /proc/filesystems

Then edit the site files (next section) and pull the images::

   docker login ghcr.io -u <github-user>          # token: Packages read
   stack nornir-build pull

Windows (Docker Desktop + WSL2)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Install Docker Desktop with the WSL2 backend, Git, PowerShell 7, and (for ``nornir:cupy``) a
   current NVIDIA driver.
2. Clone the monorepo with submodules and run, from the checkout::

      .\nornir-docker\deploy\Initialize-DockerHost.ps1 -Role compute -SetUserEnv

3. Load the CIFS driver in the WSL2 kernel (shared by Docker Desktop's containers). In the WSL
   distro, with ``systemd=true`` under ``[boot]`` in ``/etc/wsl.conf``::

      sudo cp /mnt/d/src/git/nornir/nornir-docker/dev/example.modules-load.net-shares.conf /etc/modules-load.d/net-shares.conf
      sudo modprobe cifs
      grep cifs /proc/filesystems

   Without systemd, add ``command = /sbin/modprobe cifs nfsv4`` under ``[boot]`` instead. Run
   ``wsl --shutdown`` and check again.
4. ``docker login ghcr.io`` and ``D:\Docker\stack.ps1 nornir-build pull``.

NAS shares (path B, in-container CIFS)
--------------------------------------

The container mounts the NAS shares itself, from a manifest; the host does not mount them. The
files live in one shared tree that ``Initialize-DockerHost.ps1`` creates:

::

   <root>/Run/nornir-net-mounts/
     net-mounts/nas-mounts.tsv          which shares to mount (no secrets)
     secrets/net-creds/<id>.cred        credentials per share (mode 600)
     .run.nornir-net-mounts.env         optional host-path and MQTT overrides
     compose.net-mounts.override.yaml   cursor-dev only (:doc:`nornir_dev_and_worker`)

``nas-mounts.tsv`` is **tab**-separated, one share per line; ``#`` starts a comment:

.. code-block:: text

   # fstype	source	target	options
   cifs	//storage.example.edu/Data/Volumes	/storage4	vers=3.1.1,cache=loose,actimeo=30,iocharset=utf8,mfsymlinks,credentials=/run/secrets/net-creds/storage4.cred,nobrl,noperm

* ``fstype``: ``cifs`` or ``nfs4`` (the driver must be loaded in the host kernel).
* ``source``: ``//server/share/subdir`` (CIFS) or ``server:/export/path`` (NFS).
* ``target``: absolute mount point inside the container (for example ``/storage4``).
* ``options``: ``mount -o`` options. ``uid``/``gid`` are added automatically. CIFS lines point
  ``credentials=`` at ``/run/secrets/net-creds/<id>.cred``.

The full option set used in the lab is in ``nornir-docker/dev/example.nas-mounts.tsv``.

Each ``<id>.cred`` is plain text with LF line endings::

   username=svc-nornir
   password=...
   domain=PITT

``chmod 600`` it on Linux. ``mount.cifs`` rejects group- or world-readable credential files;
because Windows bind mounts show up as ``0777``, ``mount-network-shares.sh`` copies every
``*.cred`` to ``/run/nornir-cifs-creds`` with mode ``0600`` and mounts from there.

``.run.nornir-net-mounts.env`` is only needed when the two folders are not in the default
location; then set both ``NORNIR_NET_MOUNTS_DIR_HOST`` and ``NORNIR_NET_CREDS_DIR_HOST``
(Windows paths, ``\\wsl.localhost\<Distro>\...`` UNC paths, or ``/mnt/...`` from a WSL shell).

The launcher grants ``CAP_SYS_ADMIN`` and ``DAC_READ_SEARCH`` with ``apparmor=unconfined`` for the
mount step; the entrypoint drops ``CAP_SYS_ADMIN`` afterwards when ``setpriv`` or ``capsh`` is
available. The shares stay mounted; remounting needs a container restart.

Every session
-------------

::

   stack.ps1 nornir-build up -Target compute       # long-lived container "nornir-build"
   stack.ps1 nornir-build shell -Target compute    # attach a bash shell

``up`` creates ``Work/nornir-build-<version>-<stamp>/`` and starts a detached container with that
folder at ``/workspace``, the CIFS shares mounted, ``--shm-size=64g``, ``nofile`` 65536, and
``Logs/nornir-build`` at ``/var/log/nornir``. ``shell`` attaches to it; if it is not running,
``shell`` starts a throwaway interactive container (``--rm``) with a new session folder instead.
Without ``stack.ps1`` the same launcher runs directly:
``pwsh /srv/docker/Builds/nornir-build/start-nornir-build.ps1`` (interactive, ``--rm``); run that
way it does not read ``nornir-build.run.env``, so export any overrides in the shell first.

A shell exec'd over SSH ends when the connection drops. For long builds, ``ssh`` to ``compute``,
start ``tmux``, and run ``stack nornir-build shell`` inside it.

Check the shell before starting a build:

.. code-block:: bash

   echo "$NORNIR_NET_MOUNTS"        # 1
   findmnt -t cifs                  # the shares from nas-mounts.tsv
   ls /storage4 | head
   ulimit -n                        # 65536
   nvidia-smi                       # nornir:cupy only

Interactive shells print a short ``nornir-build`` welcome and put ``TEMImport``, ``TEMBuild``,
``TEMBuild-import`` and ``TEMAlign`` on ``PATH``. Those are the lab build; what each stage does is
:doc:`../guides/tem_scripts`.

GPU selection
-------------

With no ``-Image``, ``start-nornir-build.ps1`` runs ``Test-NornirGpu.ps1``, which starts a short
``nvidia-smi`` container with ``--gpus all``:

* success: ``NORNIR_DOCKER_GPU=1``, image ``nornir:cupy``, ``--gpus all``;
* failure: image ``nornir:prod``, no GPU flags.

Force it with ``NORNIR_DOCKER_GPU=1`` in ``nornir-build.run.env`` (or ``-Gpu``), or turn it off
with ``-NoGpu``. On Ubuntu the probe needs the NVIDIA container toolkit registered with Docker
(``bootstrap-ubuntu.sh --gpu``; ``stack.ps1 doctor`` checks it). Run the probe by hand with
``pwsh nornir-docker/Test-NornirGpu.ps1``.

Progress on the dashboard
-------------------------

Start ``nornir-dashboard`` first (:doc:`dashboard`). When ``NORNIR_MQTT_HOST`` is unset, the
launcher looks for the Docker network ``nornir-dashboard_default`` (``NORNIR_MQTT_NETWORK``); if
it exists, the container joins it and publishes to ``mosquitto:1883``. This works on Linux, where
the broker is bound to ``127.0.0.1`` and is not reachable through ``host.docker.internal``. If the
network does not exist, it falls back to ``host.docker.internal``. ``NORNIR_MQTT_ENABLE=1`` (the
template default) turns publishing on. Open the dashboard with ``stack.ps1 tunnel -Target compute``.

Work sessions and pruning
-------------------------

Each ``up`` / interactive start gets its own ``Work/nornir-build-<version>-<stamp>/`` (the old
layout used ``mounted-configs/``). Builds write their output to the NAS, so these folders are
scratch::

   stack.ps1 prune -Target compute              # list folders older than 14 days
   stack.ps1 prune -Days 30 -Force -Target compute

Folders mounted by a running container are never removed.

Refreshing images
-----------------

::

   stack.ps1 nornir-build pull -Target compute       # docker-pull.ps1: nornir:prod + nornir:cupy
   stack.ps1 nornir-build rebuild -Target compute    # recreate the container on the new image
   stack.ps1 nornir-dashboard rebuild -Target compute

``docker-pull.ps1`` can also run directly: ``-IncludeDashboard`` adds the dashboard image,
``-PreferVersioned`` pins to the monorepo ``VERSION``, ``-List`` shows which local tags differ
from GHCR, ``-ContinueOnError`` keeps going past one failed pull, ``-Help`` prints every flag. A
tag whose GHCR digest is already local is skipped.

Maintainer publish
------------------

On the machine that builds images (not part of the appliance checklist)::

   .\nornir-docker\docker-build.ps1 -List
   .\nornir-docker\docker-build.ps1
   .\nornir-docker\docker-push.ps1 -List
   .\nornir-docker\docker-push.ps1

``docker-push.ps1`` with no image list pushes every catalogue image that is built locally and
whose GHCR digest differs; ``-Images cupy,gallery`` limits the set.

Problems: :doc:`troubleshooting`.
