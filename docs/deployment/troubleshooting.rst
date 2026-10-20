Troubleshooting
===============

Run ``stack.ps1 doctor`` (or ``doctor -Target all``) first; most problems below show up there as
a ``[FAIL]`` line.

Hosts, SSH, and stack.ps1
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Symptom
     - Cause and fix
   * - ``pwsh: command not found`` on a target, or a remote command hangs
     - PowerShell 7 is missing. Ubuntu: re-run ``bootstrap-ubuntu.sh``. Windows: install PowerShell 7
       and set OpenSSH ``DefaultShell`` to ``pwsh`` (:ref:`deploy-windows-openssh`).
   * - ``permission denied while trying to connect to the Docker daemon socket``
     - The deploy user was added to the ``docker`` group but has not logged in again. Log out and
       back in (``ssh`` sessions too), or ``newgrp docker``.
   * - SSH asks for a password during ``-Target``
     - The key is not in ``authorized_keys`` (Windows admins:
       ``C:\ProgramData\ssh\administrators_authorized_keys``). ``stack.ps1`` cannot answer prompts.
   * - ``-Sync``: "branch is not pushed (HEAD != upstream)"
     - Push the branch (and submodule commits) first; ``-Sync`` deploys the remote, not your tree.
   * - ``Unknown stack 'viking-...'``
     - ``VIKING_REPO_ROOT_HOST`` is not set in that host's ``host.env``, so the Viking registry is
       not loaded.
   * - ``up`` fails with ``port is already allocated`` / ``address already in use`` on the dev box
     - The old ``viking`` compose project is still running. ``docker compose -p viking down``
       (``docker ps`` shows what holds the port), then ``stack.ps1 <stack> up`` again.
   * - ``NORNIR_DOCKER_HOST_STACKS is empty``
     - Set the host's stacks in ``Run/_host/host.env`` (or re-run ``Initialize-DockerHost.ps1 -Role ...``).
   * - "Stack ... is not configured" with a list of keys
     - A required key or secret file is missing; the message names the file to edit.
   * - ``NORNIR_MONOREPO_ROOT is deprecated`` warning
     - Rename it to ``NORNIR_REPO_ROOT_HOST`` in ``host.env`` or your user environment.
   * - ``Builds/nornir-build/start-nornir-build.ps1`` fails with missing ``NornirDockerRun.ps1`` /
       ``NornirDevRunMounts.ps1``
     - It is an old *copy* of the launcher; copies break because the script dot-sources sibling
       helpers. Re-run ``Initialize-DockerHost.ps1``: it replaces it with a forwarding launcher
       (the copy is kept as ``.bak``).

Network and TLS
---------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Symptom
     - Cause and fix
   * - A port is reachable from outside although ufw denies it
     - Docker-published ports bypass ufw. Bind internal ports to ``127.0.0.1`` and filter
       cross-host ports in ``DOCKER-USER`` (:doc:`ports_and_remote_access`).
   * - ``certs status``: "certificate does not cover: ..."
     - The certificate lacks a SAN for some ``VIKING_HOSTNAME_*``. Get a wildcard
       ``*.<domain>`` (or SAN) certificate; a wildcard only covers single-label names, so keep
       hostname overrides one level under the domain. Or narrow ``TLS_HOSTNAMES``.
   * - ``certs status``: no intermediate certificates
     - Pass the issuer chain with ``-Chain``; gRPC clients and the Viking desktop client reject a
       leaf-only ``fullchain.pem``.
   * - ``certs letsencrypt`` times out or fails HTTP-01
     - Port 80 on ``web`` is not reachable from the internet, DNS does not point at ``web`` yet, or
       ``viking-proxy`` is not up. If Pitt will not open port 80, use ``TLS_MODE=acme-eab`` (Pitt
       IT's ACME server with EAB) or ``certs manual``.
   * - Let's Encrypt rate-limit errors while testing
     - Set ``TLS_STAGING=1`` until the flow works, then back to ``0`` and re-issue.
   * - ``certs manual``: key is encrypted / key does not match / expires sooner
     - Decrypt (``openssl pkey -in key.pem -out key.dec.pem``); check you have the key for this
       certificate; use ``-Force`` to replace a later-expiring certificate on purpose.
   * - Segmentation names fail through the proxy
     - ``compute`` does not accept 40443-40447 from ``web`` (Pitt firewall or ``DOCKER-USER``), or
       ``stack.ps1 certs push -From web`` has not copied the certificate to ``compute``.
   * - ``doctor``: ``DNS <name> does not resolve yet``
     - The Pitt DNS ticket is not done, or the record is not a wildcard.

Build appliance and dashboard
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Symptom
     - Cause and fix
   * - ``network nornir-dashboard_default not found``, or builds never appear on the dashboard
     - Start ``nornir-dashboard`` before ``nornir-build``, then ``stack.ps1 nornir-build rebuild``.
       If ``Run/nornir-net-mounts/.run.nornir-net-mounts.env`` was copied from the old template,
       it sets ``NORNIR_MQTT_HOST=host.docker.internal``; comment that line out. While it is set
       the launcher does not join the dashboard network, and on Linux the loopback-bound broker
       is unreachable.
   * - ``Bus error``, ``No space left on device`` under ``/dev/shm``, or pool workers dying
     - Shared memory too small. The launcher passes ``--shm-size=64g`` (``NORNIR_DOCKER_SHM_SIZE``);
       recreate containers started by older scripts (``stack.ps1 nornir-build rebuild``).
   * - ``Too many open files`` (``EMFILE``)
     - ``ulimit -n`` should be 65536; check ``NORNIR_DOCKER_NOFILE_*`` and recreate the container.
   * - Missing ``nas-mounts.tsv``
     - Run ``Initialize-DockerHost.ps1 -Role compute`` and edit the site files.
   * - ``mount: ... Operation not permitted``
     - Path B not applied: the container lacks ``SYS_ADMIN`` (started without the launcher or the
       net-mounts override).
   * - CIFS ``mount error(2)``
     - The ``cifs`` driver is not loaded in the host kernel (Ubuntu: ``modprobe cifs``; Windows:
       the WSL2 kernel). Check ``grep cifs /proc/filesystems``.
   * - CIFS ``mount error(13): Permission denied``
     - Wrong user/password/domain in the ``.cred``, a share ACL, or a ``credentials=`` path in
       ``nas-mounts.tsv`` that does not match a file in ``net-creds/``. Images older than the
       ``0600`` copy fix need a pull.
   * - ``/storage4`` (or another target) empty
     - ``NORNIR_NET_MOUNTS`` is not ``1`` in the container; check how it was started.
   * - Remount fails after the shell starts
     - Expected: ``CAP_SYS_ADMIN`` is dropped after the mount step. Restart the container.
   * - Wrong image or no GPU
     - Run ``pwsh nornir-docker/Test-NornirGpu.ps1``; on Ubuntu install the NVIDIA container
       toolkit (``bootstrap-ubuntu.sh --gpu``). Force with ``NORNIR_DOCKER_GPU=1``.
   * - TEM scripts fail importing CuPy on a CPU-only host
     - Fixed: the TEM wrappers select NumPy when no GPU is present. Pull current images.
   * - Dashboard unreachable
     - ``stack.ps1 nornir-dashboard status``; it binds ``127.0.0.1`` only, so use the tunnel.
   * - Dashboard: "attempt to write a readonly database"
     - Run ``stack.ps1 nornir-dashboard up`` again; the launcher re-owns the data volume to uid
       10001.

Programmer shell
----------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Symptom
     - Cause and fix
   * - ``NORNIR_TESTDATA_HOST`` missing, or settings in ``Run/nornir-dev/.env`` ignored
     - ``nornir-docker/.env`` is missing or is a stale copy; recreate the hardlink
       (:doc:`nornir_dev_and_worker`).
   * - ``DynamicLibNotFoundError: libnvrtc`` / ``cudaErrorInsufficientDriver``
     - Host NVIDIA driver too old for the CuPy wheel, or no GPU passthrough.
   * - ``distro-services/*.sock`` errors with ``\\wsl.localhost`` paths
     - Wrong distro name or casing; use the exact name from ``wsl -l -v`` (or ``\\wsl$\...``).
