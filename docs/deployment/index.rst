Deployment and configuration
============================

Every Nornir and Viking container stack is started, stopped, and inspected with one command,
``stack.ps1``, on the machine itself or on a remote target over SSH. This section is the
canonical guide for the hosts behind ``connectomes.pitt.edu``. Viking-specific service
configuration (proxy routes, TLS renewer, identity clients, SQL databases, segmentation models,
IIS) is in the Viking deployment docs, starting at the :viking:`Viking bring-up checklist
<index.html>`; those pages link back here for the commands and the host layout.

The deploy tooling (``stack.ps1``, ``Initialize-DockerHost.ps1``, ``bootstrap-ubuntu.sh``, the
``nornir-build`` / ``nornir-dashboard`` stack registry and the host and stack templates) lives in
the `connectomes-deploy <https://github.com/jamesra/connectomes-deploy>`_ repository, cloned to
``/srv/connectomes-deploy`` on Ubuntu hosts. ``nornir-docker/deploy/`` in the nornir checkout is
an old copy from before the move (2026-10-21); do not use it. Stacks that still run from source
checkouts come from registries there: ``<Viking>/deploy/stacks.psd1`` and
``<nornir>/nornir-docker/dev-stacks.psd1`` (:doc:`stacks_and_commands`).

.. toctree::
   :maxdepth: 1

   host_layout
   stacks_and_commands
   configuration_reference
   accounts_and_tokens
   ports_and_remote_access
   debugging
   nornir_build_appliance
   nornir_dev_and_worker
   dashboard
   troubleshooting
   migrating_from_old_layout

What runs where
---------------

.. list-table::
   :header-rows: 1
   :widths: 14 30 56

   * - Target
     - Machine
     - Stacks (``NORNIR_DOCKER_HOST_STACKS``)
   * - ``compute``
     - Dedicated Ubuntu 26 GPU server
     - ``nornir-build`` (build appliance, :doc:`nornir_build_appliance`),
       ``nornir-dashboard`` (MQTT broker + build dashboard, :doc:`dashboard`),
       ``viking-segmentation`` (SAM2 gRPC servers; terminates its own TLS behind the proxy)
   * - ``web``
     - Separate dedicated Ubuntu server
     - ``viking-proxy`` (nginx: SNI passthrough on 443; ACME HTTP-01 and https redirect on 80),
       ``viking-certs`` (the one certificate renewer), ``viking-identity``,
       ``viking-annotation``, ``viking-corrections``. The annotation gallery also runs here,
       but it is not a ``stack.ps1`` stack: start it from the Sam2Trainer repository (the proxy
       routes ``gallery``, ``gallery-tem`` and ``gallery-sem`` to port 8442 on ``web``).
   * - ``iis``
     - Legacy Windows Server with IIS
     - ``viking-iis``: WCF annotation, OData, DataExport, tiles, and the client feed, served
       as ``websvc.<domain>`` through the proxy
   * - dev box
     - Windows workstation with Docker Desktop
     - ``nornir-dashboard`` locally; ``nornir-dev`` and ``nornir-cursor-worker``
       (:doc:`nornir_dev_and_worker`). Deploys to every target with ``-Target <name>``.

The service names are single labels under ``VIKING_DOMAIN`` (``connectomes.pitt.edu``), so one
wildcard certificate ``*.connectomes.pitt.edu`` (or one SAN certificate) covers them:

``identity``, ``websvc``, ``annotation``, ``corrections``, ``segmentation``,
``segmentationdemo``, ``gallery``, ``gallery-tem``, ``gallery-sem``.

Each further segmentation model is a row of ``Run/viking-segmentation/models.json`` and is named
``<prefix>.segmentation.<domain>`` (for example ``v3.segmentation.connectomes.pitt.edu``). That
name has two labels, so ``*.connectomes.pitt.edu`` does not cover it: the certificate also needs
``*.segmentation.connectomes.pitt.edu``, or each model name listed (:ref:`deploy-segmentation-network`).

All of them resolve to ``web``. The proxy forwards each TLS connection by SNI name, unopened, to
the right backend: a container on ``web``, ``viking-segmentation`` on ``compute`` (or the
segmentation server's own LAN address when it runs on macvlan), or IIS on ``iis`` (route table:
:viking:`Viking proxy <proxy.html>`).

Zero to running
---------------

Do these steps in order. Each step is a set of commands; the pages linked from each step explain
the details. Commands that start with ``stack.ps1`` run from the dev box. After
``Initialize-DockerHost.ps1 -SetUserEnv`` on Ubuntu (and a re-login), ``stack`` is an alias for
``pwsh /srv/docker/stack.ps1``. On Windows, run ``D:\Docker\stack.ps1``.

1. Pitt IT tickets
~~~~~~~~~~~~~~~~~~

Open these before anything else; they take the longest. The exact port lists are in
:doc:`ports_and_remote_access`, and what each credential is in :doc:`accounts_and_tokens`.

* **DNS:** a wildcard record ``*.connectomes.pitt.edu`` pointing at the ``web`` server's public
  address (or one A/CNAME record per name above, including each segmentation model name).
* **Firewall:** the per-host rules in :ref:`deploy-firewall-request`.
* **Certificate (only if Let's Encrypt is not allowed):** either an ACME EAB credential for the
  InCommon/Sectigo ACME server (key id, HMAC key, and server URL), or a wildcard/SAN certificate
  issued for the names above (with ``*.segmentation.connectomes.pitt.edu`` for the extra models).
* **Segmentation server on its own IP (optional):** a DHCP reservation for a MAC address, a second
  MAC on the switch port, and a network ACL for 443 from ``web``
  (:ref:`deploy-segmentation-network`).

2. Bootstrap the Ubuntu servers (``compute`` and ``web``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On each server, logged in as the account you will deploy as (it must be able to sudo; it becomes
the deploy user). To use a dedicated account, create it first (``sudo adduser deploy``) and add
``--user deploy``. On ``compute``, install the NVIDIA driver first
(``sudo ubuntu-drivers install`` and reboot)::

   curl -fsSL https://raw.githubusercontent.com/jamesra/connectomes-deploy/main/bootstrap-ubuntu.sh -o bootstrap-ubuntu.sh
   sudo bash bootstrap-ubuntu.sh --gpu          # compute
   sudo bash bootstrap-ubuntu.sh --open-web     # web
   # log out and back in (docker group)

   git clone https://github.com/jamesra/connectomes-deploy.git /srv/connectomes-deploy
   git clone --recurse-submodules https://github.com/jamesra/nornir.git /srv/src/nornir     # compute only
   git clone https://github.com/jamesra/Viking.git /srv/src/Viking
   git -C /srv/src/Viking submodule update --init gRPC_Protos

   pwsh /srv/connectomes-deploy/Initialize-DockerHost.ps1 -Role compute -NornirRepoRoot /srv/src/nornir -VikingRepoRoot /srv/src/Viking -SetUserEnv
   pwsh /srv/connectomes-deploy/Initialize-DockerHost.ps1 -Role web -VikingRepoRoot /srv/src/Viking -SetUserEnv

The nornir checkout is needed only on hosts that run ``nornir-*`` stacks, until their images are
published. Viking image builds need only its ``gRPC_Protos`` submodule; the other Viking submodules
are not needed. The layout this creates is :doc:`host_layout`.

3. Prepare the dev box
~~~~~~~~~~~~~~~~~~~~~~

In PowerShell 7 on the Windows dev box, with connectomes-deploy cloned next to the other
checkouts (``D:\src\git\connectomes-deploy``). If the dev box still runs the old ``viking``
compose project, stop it first (``docker compose -p viking down``); its ports clash with the new
stacks::

   D:\src\git\connectomes-deploy\Initialize-DockerHost.ps1 -Role dev -NornirRepoRoot D:\src\git\nornir -VikingRepoRoot D:\src\git\Viking -WithTargets -SetUserEnv

   ssh-keygen -t ed25519
   type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh deploy@compute.connectomes.pitt.edu "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh deploy@web.connectomes.pitt.edu "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

Edit ``D:\Docker\Run\_host\targets.psd1`` (``Ssh``, ``Root``, ``Repos`` per target). Then make
SSH key-only on both servers (``sudo bash bootstrap-ubuntu.sh --harden-ssh``). The
``iis`` host needs Windows OpenSSH with ``pwsh`` as its default shell; see
:ref:`deploy-windows-openssh`. Only the dev box needs keys and ``targets.psd1``; the servers do
not need keys on each other.

4. Fill in the configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On each host, ``Initialize-DockerHost.ps1`` copied a template into every file below. Edit them on
that host (``ssh`` in, or VS Code Remote-SSH). Every key is described in
:doc:`configuration_reference`.

* ``Run/_host/host.env``: ``VIKING_DOMAIN`` (the parent domain, without a host label),
  ``TLS_MODE``, ``TLS_EMAIL`` (``NORNIR_DOCKER_USER_ROOT``, ``DEPLOY_REPO_ROOT_HOST``,
  ``NORNIR_REPO_ROOT_HOST``, ``VIKING_REPO_ROOT_HOST`` and ``NORNIR_DOCKER_HOST_STACKS`` are
  pre-filled). On ``web``, also the proxy's upstreams: ``VIKING_COMPUTE_HOST`` (LAN name or IP of
  ``compute``) and ``VIKING_IIS_HOST``. ``VIKING_UPSTREAM_DEFAULT`` (default: IIS) and
  ``VIKING_HTTP_UPSTREAM_WEBSVC`` (keeps old Viking clients' ``http://`` WCF and tile requests
  working instead of redirecting them to https) are optional ``viking-proxy`` settings in
  ``Run/viking-proxy/viking-proxy.run.env``.
* ``Run/_host/secrets/secrets.env``: ``GITHUB_TOKEN`` if the host pulls from GHCR.
* ``Run/<stack>/<stack>.run.env`` for every stack the host runs.
* ``compute`` only: ``Run/nornir-net-mounts/net-mounts/nas-mounts.tsv`` and
  ``Run/nornir-net-mounts/secrets/net-creds/*.cred`` (:doc:`nornir_build_appliance`).

Generate the random client secrets, tokens, and passwords, then copy the shared ones to the stacks
that consume them (:doc:`accounts_and_tokens`). Name optional client secrets explicitly; an empty
one means that client is disabled::

   stack.ps1 secrets new viking-identity -Target web
   stack.ps1 secrets new viking-identity CORRECTION_SERVICE_CLIENT_SECRET -Target web
   stack.ps1 secrets new viking-annotation -Target web
   stack.ps1 secrets new viking-corrections -Target web
   stack.ps1 secrets new nornir-dashboard -Target compute

``SQL_SERVER_PASSWORD`` and connection strings are never generated: they belong to existing SQL
logins, so set them by hand.

On ``web``, put the Duende license in ``Run/viking-identity/secrets/Duende_License.key`` and
``secrets.json`` next to it, and copy the existing Identity data-protection keys **before the first
start**, or every user is signed out::

   mkdir -p /srv/docker/Data/viking-identity/DataProtectionKeys
   cp -a /srv/src/Viking/Servers/IdentityServer/DataProtectionKeys/. /srv/docker/Data/viking-identity/DataProtectionKeys/

Per-service keys are in the Viking pages: :viking:`identity <identity.html>`,
:viking:`annotation <annotation_grpc.html>`, :viking:`corrections <corrections.html>`,
:viking:`segmentation <segmentation.html>`, :viking:`SQL <sql.html>`.

5. Check everything
~~~~~~~~~~~~~~~~~~~

::

   stack.ps1 doctor -Target all

Fix every ``[FAIL]`` line. Certificate and DNS checks fail until steps 1 and 6 are done.

6. Bring up ``web`` and get the certificate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The proxy must be up first, because Let's Encrypt validates through it on port 80::

   stack.ps1 viking-proxy up -Target web
   stack.ps1 certs letsencrypt -Target web
   stack.ps1 certs status -Target web

If port 80 cannot be opened to the internet, use the Pitt ACME server instead (set
``TLS_MODE=acme-eab`` and ``TLS_ACME_SERVER``, and ``TLS_EAB_KID`` / ``TLS_EAB_HMAC_KEY`` in
``Run/viking-certs/secrets/secrets.env``; details in :viking:`Viking TLS <tls.html>`)::

   stack.ps1 certs acme-eab -Target web

Or install a certificate Pitt IT issued by hand (copy the files to ``web`` first)::

   stack.ps1 certs manual -Target web -Cert /home/deploy/connectomes.crt -Key /home/deploy/connectomes.key -Chain /home/deploy/incommon-chain.pem

Copy the certificate to the hosts that terminate TLS themselves (``compute`` and ``iis``; every
target with ``CertPush = $true``), then start the rest of ``web``. ``-From web`` fetches the
certificate from ``web`` to the dev box first, then pushes it::

   stack.ps1 certs push -From web
   stack.ps1 all up -Target web

Then start the annotation gallery from the Sam2Trainer repository on ``web`` (its own compose
file; it listens on 8442 for the proxy).

7. Bring up ``compute``
~~~~~~~~~~~~~~~~~~~~~~~

::

   stack.ps1 nornir-dashboard up -Target compute
   stack.ps1 nornir-build up -Target compute
   stack.ps1 viking-segmentation up -Target compute
   stack.ps1 nornir-build shell -Target compute        # interactive build shell

Start the dashboard before ``nornir-build`` so the build container joins its network. Open the
dashboard through ``stack.ps1 tunnel -Target compute`` at http://127.0.0.1:8087.

``viking-segmentation up`` starts the default model only, on host port 40443 unless the run env
puts it on its own IP (:ref:`deploy-segmentation-network`). Add the other models on ``compute``
with ``stack viking-segmentation model <prefix> <file.pt>``.

8. Deploy ``iis``
~~~~~~~~~~~~~~~~~

::

   stack.ps1 viking-iis deploy -Target iis
   stack.ps1 certs install-iis -Target iis

``certs push`` in step 6 already ran ``install-iis`` when ``CertPush = $true`` for ``iis``; run
it again after a manual PFX change. What the IIS deploy installs: :viking:`IIS legacy services
<iis_legacy_services.html>`.

9. Final check
~~~~~~~~~~~~~~

::

   stack.ps1 doctor -Target all
   stack.ps1 all status -Target all

``status`` prints each stack's health URL result (:doc:`debugging`). Day-to-day updates are
``stack.ps1 <stack> rebuild -Target <host> -Sync`` (:doc:`stacks_and_commands`).
