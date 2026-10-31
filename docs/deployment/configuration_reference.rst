Configuration reference
=======================

Every key in the committed templates, plus the run-time variables the ``nornir-docker`` launchers
read. Host templates (``example.host.env``, ``example.host.secrets.env``,
``example.targets.psd1``) are in ``host/`` of the `connectomes-deploy
<https://github.com/jamesra/connectomes-deploy>`_ repository, and the ``nornir-build`` and
``nornir-dashboard`` templates in its ``stacks/<stack>/``; other templates give their path. Viking
service keys (SQL connection strings, identity clients, segmentation models) are in the Viking
``deploy/examples/`` templates and the Viking deployment docs (:viking:`proxy <proxy.html>`,
:viking:`TLS <tls.html>`, :viking:`identity <identity.html>`, :viking:`segmentation
<segmentation.html>`).

"Required" means ``stack.ps1`` (or the launcher) stops without it. Blank defaults mean unset.

Naming rules
------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Pattern
     - Meaning
   * - ``NORNIR_*``
     - Nornir behaviour (build, dashboard, MQTT, mounts).
   * - ``NORNIR_DOCKER_*``
     - Machine-level Docker settings for this host (layout root, host stacks, ``docker run``
       limits).
   * - ``VIKING_*``
     - Viking deployment settings (domain, host names, repository path).
   * - ``TLS_*``
     - The shared certificate.
   * - ``*_HOST`` suffix
     - A host filesystem path used as a bind source (``NORNIR_REPO_ROOT_HOST``,
       ``NORNIR_TESTDATA_HOST``).
   * - ``*_HOSTNAME`` / ``VIKING_HOSTNAME_*``
     - A DNS name.
   * - Stack keys
     - kebab-case; the same string is the registry key, the ``Run/<stack>/`` folder, the
       ``<stack>.run.env`` file name, and the compose project name.

``Run/_host/host.env``
----------------------

Template ``example.host.env``. Machine settings for every stack on the host; no secrets.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Key
     - Default
     - Required
     - Consumer / meaning
   * - ``NORNIR_DOCKER_USER_ROOT``
     - ``D:\Docker`` / ``/srv/docker``
     - yes
     - Layout root (:doc:`host_layout`). Filled in by ``Initialize-DockerHost.ps1``. Also read from
       the process environment by every launcher.
   * - ``DEPLOY_REPO_ROOT_HOST``
     - checkout containing ``stack.ps1``
     - yes
     - connectomes-deploy checkout on this host (``/srv/connectomes-deploy`` on Ubuntu). Filled in
       by ``Initialize-DockerHost.ps1``; ``<root>/stack.ps1`` forwards to it, and ``-Sync`` uses it.
   * - ``NORNIR_REPO_ROOT_HOST``
     -
     - ``nornir-*`` stacks
     - nornir checkout on this host (``/srv/src/nornir``), needed until the ``nornir-*`` images run
       without it; the ``nornir-build`` / ``nornir-dashboard`` launchers and the nornir dev-stack
       registry live there. ``-Sync`` uses it.
   * - ``VIKING_REPO_ROOT_HOST``
     -
     - Viking hosts
     - Viking checkout; without it the Viking registry is not loaded.
   * - ``STACK_EXTRA_REGISTRIES``
     - see meaning
     -
     - Source-repo stack registries loaded after connectomes-deploy's ``stacks.psd1``, comma list
       of ``<RepoRootVar>:<path>``. Empty loads ``VIKING_REPO_ROOT_HOST:deploy/stacks.psd1`` and
       ``NORNIR_REPO_ROOT_HOST:nornir-docker/dev-stacks.psd1``. ``none`` loads only
       connectomes-deploy's registry.
   * - ``NORNIR_DOCKER_HOST_STACKS``
     - role preset
     - yes
     - Comma list of stacks this host runs (``stack.ps1 all``, ``doctor``). Presets:
       compute ``nornir-build,nornir-dashboard,viking-segmentation``; web
       ``viking-proxy,viking-certs,viking-identity,viking-annotation,viking-corrections``;
       iis ``viking-iis``; dev ``nornir-dashboard``.
   * - ``VIKING_DOMAIN``
     - ``connectomes.pitt.edu``
     - Viking hosts
     - Parent domain; every ``VIKING_HOSTNAME_*`` defaults to ``<sub>.$VIKING_DOMAIN``.
   * - ``VIKING_HOSTNAME_IDENTITY``
     - ``identity.<domain>``
     -
     - Override for one service name. Same for ``_WEBSVC`` (``websvc``), ``_ANNOTATION``
       (``annotation``), ``_CORRECTIONS`` (``corrections``), ``_SEGMENTATION``
       (``segmentation``), ``_SEGMENTATIONDEMO`` (``segmentationdemo``), ``_GALLERY``
       (``gallery``), ``_TEM_GALLERY`` (``gallery-tem``), ``_SEM_GALLERY`` (``gallery-sem``).
       Keep overrides single-label under the domain so one wildcard certificate still covers them.
       The other segmentation models are rows of ``Run/viking-segmentation/models.json``
       (``stack.ps1 viking-segmentation model``).
   * - ``VIKING_BACKEND_NETWORK``
     -
     -
     - Docker network shared by ``viking-proxy`` and the segmentation model servers on the same
       host (for example ``viking-backend``); the proxy then reaches them by name and nothing is
       published (connectomes-deploy ``stacks/viking-proxy/compose.backend.yaml``).
   * - ``VIKING_IDENTITY_URL``
     - ``https://$VIKING_HOSTNAME_IDENTITY/``
     -
     - Token issuer used by identity, annotation, corrections and segmentation. A stack's own
       setting (``IDENTITY_AUTHORITY``, ``IdentityServer__Endpoint``,
       ``SEGMENTATION_IDENTITY_ENDPOINT``) wins.
   * - ``VIKING_IDENTITY_API_URL``
     - ``https://$VIKING_HOSTNAME_IDENTITY/webapi/``
     -
     - Identity WebApi (permissions, resources).
   * - ``VIKING_CORRECTIONS_DIR``
     - ``<root>/Data/viking-corrections``
     -
     - Published section corrections: ``viking-corrections`` writes ``<dir>/corrections``,
       ``viking-annotation`` reads it.
   * - ``VIKING_ACME_WEBROOT``
     - ``<root>/Data/viking-certs/webroot``
     -
     - HTTP-01 challenge webroot: ``viking-certs`` writes it, ``viking-proxy`` serves it on port 80.
   * - ``VIKING_COMPUTE_HOST``
     -
     - ``web``
     - LAN name or IP of ``compute``; the proxy forwards the segmentation names to it (ports
       40443-40447).
   * - ``VIKING_IIS_HOST``
     -
     - ``web``
     - LAN name or IP of ``iis``; the proxy forwards ``websvc`` to it on 443.
   * - ``VIKING_UPSTREAM_DEFAULT``
     - the IIS host
     -
     - ``viking-proxy`` setting; the template puts it in ``Run/viking-proxy/viking-proxy.run.env``.
       ``host:port`` for TLS connections whose SNI name matches no service.
   * - ``VIKING_HTTP_UPSTREAM_WEBSVC``
     -
     -
     - ``viking-proxy`` setting; the template puts it in ``Run/viking-proxy/viking-proxy.run.env``.
       ``host:port``: pass plain-HTTP ``websvc`` traffic through on port 80 instead of redirecting
       it to https, so old Viking clients' ``http://`` WCF and tile requests keep working.
   * - ``TLS_MODE``
     - ``letsencrypt``
     - Viking hosts
     - ``letsencrypt`` | ``acme-eab`` | ``manual``; tells ``viking-certs`` what to renew.
   * - ``TLS_EMAIL``
     -
     - letsencrypt, acme-eab
     - ACME account contact for expiry notices.
   * - ``TLS_CERT_NAME``
     - ``$VIKING_DOMAIN``
     -
     - Folder under ``Certs/``; every TLS service loads ``/certs/<TLS_CERT_NAME>/``.
   * - ``TLS_HOSTNAMES``
     - every ``VIKING_HOSTNAME_*``
     -
     - Comma list the certificate must cover (``certs manual``, ``certs status``).
   * - ``TLS_ACME_SERVER``
     -
     - acme-eab
     - ACME directory URL from Pitt IT. The EAB key id and HMAC key go in
       ``Run/viking-certs/secrets/secrets.env`` as ``TLS_EAB_KID`` and ``TLS_EAB_HMAC_KEY``.
   * - ``TLS_STAGING``
     - ``0``
     -
     - ``1`` uses the Let's Encrypt staging endpoint (untrusted certificates; no rate limits).
   * - ``TLS_PFX_PASSWORD``
     - empty
     -
     - Password for ``Certs/<name>/cert.pfx``. Also accepted as ``-PfxPassword``.
   * - ``NORNIR_GHCR_OWNER``
     - ``jamesra``
     -
     - GHCR namespace for ``docker-pull.ps1`` / ``docker-push.ps1`` (``ghcr.io/<owner>/nornir:*``).

``Run/_host/secrets/secrets.env``
---------------------------------

Template ``example.host.secrets.env``. Mode ``600`` on Linux.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Key
     - Default
     - Required
     - Consumer / meaning
   * - ``GITHUB_TOKEN``
     -
     -
     - GitHub fine-grained PAT (:doc:`accounts_and_tokens`). The launchers never load it into the
       host process; it reaches containers only through ``--env-file``. Also run
       ``docker login ghcr.io`` once per host.

``Run/_host/targets.psd1``
--------------------------

Template ``example.targets.psd1``; a PowerShell data file, one entry per target under ``Targets``.

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Field
     - Meaning
   * - ``Ssh``
     - ``user@host`` or a ``Host`` alias from ``~/.ssh/config``. Must log in without a password
       prompt.
   * - ``SshOptions``
     - Extra ``ssh``/``scp`` arguments, for example ``@('-p', '2222')`` or ``@('-J', 'jump.example.edu')``.
   * - ``Os``
     - ``linux`` or ``windows`` (Windows targets need ``pwsh`` as the OpenSSH default shell).
   * - ``Root``
     - That host's ``NORNIR_DOCKER_USER_ROOT``.
   * - ``Stacks``
     - Stacks ``all`` means for this target (informational for ``-Images load``; the target's own
       ``NORNIR_DOCKER_HOST_STACKS`` decides what ``all`` runs there).
   * - ``Repos``
     - ``@{ DEPLOY_REPO_ROOT_HOST = '<path>'; NORNIR_REPO_ROOT_HOST = '<path>';
       VIKING_REPO_ROOT_HOST = '<path>' }``: checkouts that ``-Sync`` fast-forwards (list only
       those the target has).
   * - ``Tunnels``
     - ``ssh -L`` specs (``local:host:port``) opened by ``stack.ps1 tunnel``.
   * - ``CertPush``
     - ``$true``: ``stack.ps1 certs push`` (usually ``-From web``) without ``-Target`` copies the
       certificate here.

``Run/nornir-build/nornir-build.run.env``
-----------------------------------------

Template ``example.nornir-build.run.env``. Read by ``start-nornir-build.ps1``.

.. list-table::
   :header-rows: 1
   :widths: 30 20 10 40

   * - Key
     - Default
     - Required
     - Consumer / meaning
   * - ``NORNIR_DOCKER_SHM_SIZE``
     - ``64g``
     -
     - ``docker run --shm-size``. Multiprocessing pools fail with Docker's 64 MB default.
   * - ``NORNIR_DOCKER_NOFILE_SOFT`` / ``_HARD``
     - ``65536`` / ``65536``
     -
     - ``--ulimit nofile``. Tile I/O on CIFS exhausts the default 1024.
   * - ``NORNIR_DOCKER_GPU``
     - auto
     -
     - ``1`` forces ``--gpus all``. Unset: ``Test-NornirGpu.ps1`` probes and sets it, which picks
       ``nornir:cupy`` (GPU) or ``nornir:prod`` (CPU).
   * - ``NORNIR_MQTT_ENABLE``
     - ``1``
     -
     - Publish build progress to the dashboard broker.
   * - ``NORNIR_MQTT_HOST``
     - auto
     -
     - Broker host seen from the container. Unset: join ``NORNIR_MQTT_NETWORK`` and use
       ``mosquitto`` when that network exists, else ``host.docker.internal``.
   * - ``NORNIR_MQTT_PORT``
     - ``1883``
     -
     - Broker port.
   * - ``NORNIR_MQTT_NETWORK``
     - ``nornir-dashboard_default``
     -
     - Docker network the build container joins to reach Mosquitto by name.
   * - ``NORNIR_DEBUGPY``
     -
     -
     - ``1`` publishes ``127.0.0.1:<NORNIR_DEBUGPY_PORT>`` on the container for debugpy. It does not
       start a listener; debugpy is not in the images (:doc:`debugging`).
   * - ``NORNIR_DEBUGPY_PORT``
     - ``5678``
     -
     - Port for ``NORNIR_DEBUGPY``; also passed into the container.
   * - ``NORNIR_DOCKER_EXTRA_ARGS``
     -
     -
     - Extra ``docker run`` tokens, space separated.

``Run/nornir-dashboard/nornir-dashboard.run.env``
-------------------------------------------------

Template ``example.nornir-dashboard.run.env`` (``start-dashboard.ps1`` still reads the legacy
``dashboard.run.env``). Consumed by ``compose.dashboard.yaml``. Full table: :doc:`dashboard`.

.. list-table::
   :header-rows: 1
   :widths: 34 16 50

   * - Key
     - Default
     - Meaning
   * - ``NORNIR_DASHBOARD_BIND_HOST``
     - ``127.0.0.1``
     - Host address the UI port 8087 is published on.
   * - ``NORNIR_MQTT_BIND_HOST``
     - ``127.0.0.1``
     - Host address the broker port 1883 is published on (template and compose default).
   * - ``NORNIR_DASHBOARD_TOKEN``
     -
     - Required before widening the bind host; put it in ``Run/nornir-dashboard/secrets/secrets.env``.
   * - ``NORNIR_DASHBOARD_ALLOW_DELETE``
     - ``1``
     - ``0`` refuses ``DELETE /api/runs/{id}``.
   * - ``NORNIR_DASHBOARD_MAX_EVENTS``
     - ``0``
     - Max SQLite events per run (``0`` = unlimited).
   * - ``NORNIR_DASHBOARD_RETENTION_DAYS``
     - ``30``
     - Delete runs idle this many days (``0`` disables).
   * - ``NORNIR_DASHBOARD_STALE_AFTER``
     - ``600``
     - Seconds without events before a run shows as stale.
   * - ``NORNIR_BUILDDASHBOARD_CONTEXT``
     - ``../nornir-builddashboard``
     - Build context for the dashboard image (set by ``start-dashboard.ps1``).

``Run/nornir-net-mounts/``
--------------------------

Shared by ``start-nornir-build.ps1``, cursor-dev net mounts, and the worker's
``-DevParityMounts``. Format details: :doc:`nornir_build_appliance`.

.. list-table::
   :header-rows: 1
   :widths: 34 20 46

   * - File / key
     - Template
     - Meaning
   * - ``net-mounts/nas-mounts.tsv``
     - ``nornir-docker/dev/example.nas-mounts.tsv``
     - Tab-separated ``fstype source target options`` per share.
   * - ``secrets/net-creds/<id>.cred``
     - connectomes-deploy ``stacks/nornir-build/example.net-creds.cred`` (copied as
       ``storage.cred``)
     - ``username=``, ``password=``, ``domain=`` (optional), LF line endings.
   * - ``.run.nornir-net-mounts.env``
     - ``nornir-docker/example.nornir-net-mounts.run.env``
     - Optional overrides below.
   * - ``NORNIR_NET_MOUNTS_DIR_HOST``
     - ``<root>/Run/nornir-net-mounts/net-mounts``
     - Host folder holding ``nas-mounts.tsv``. Set together with the next key, or neither.
   * - ``NORNIR_NET_CREDS_DIR_HOST``
     - ``<root>/Run/nornir-net-mounts/secrets/net-creds``
     - Host folder of ``*.cred`` files.
   * - ``NORNIR_MQTT_HOST`` / ``_PORT`` / ``_ENABLE``
     - unset (commented ``mosquitto``) / ``1883`` / ``1``
     - MQTT for containers started with this file. Leave ``NORNIR_MQTT_HOST`` unset so
       ``nornir-build`` joins the dashboard network; files copied from the old template set it to
       ``host.docker.internal`` (:doc:`troubleshooting`).

Inside the containers (set by the launchers, read by ``mount-network-shares.sh``):
``NORNIR_NET_MOUNTS=1`` (path B enabled), ``NORNIR_NET_MOUNTS_MANIFEST``
(``/etc/nornir-net-mounts/nas-mounts.tsv``), ``NORNIR_NET_CREDS_SRC``
(``/run/secrets/net-creds``), ``NORNIR_NET_CREDS_SECURE`` (``/run/nornir-cifs-creds``, the
``0600`` copy mount.cifs uses), ``NORNIR_LOG_ROOT`` (``/var/log/nornir`` in ``nornir-build``).

cursor-dev (``Run/nornir-dev/.env`` bridged to ``nornir-docker/.env``)
------------------------------------------------------------------------

Template ``nornir-docker/dev/example.cursor-dev.run.env``. Compose substitutes these and also
passes the whole file into the container (``env_file``). See :doc:`nornir_dev_and_worker`.

.. list-table::
   :header-rows: 1
   :widths: 30 26 44

   * - Key
     - Default
     - Meaning
   * - ``NORNIR_TESTDATA_HOST``
     - required
     - Host path of ``nornir-testdata`` (WSL2 filesystem recommended); read-only at
       ``/nornir-testdata`` (``TESTINPUTPATH``).
   * - ``NORNIR_REPRO_DATA_HOST``
     - empty placeholder
     - Large repro corpus, read-only at ``/data`` (``INPUT_NORNIR_DATA=/data``).
   * - ``NORNIR_TESTOUTPUT_HOST``
     - ``D:/nornir-test-output``
     - Writable ``/tmp/nornir-test-output`` (``TESTOUTPUTPATH``).
   * - ``NORNIR_LEGACY_CODE_HOST``
     - ``D:/src/SVN/SCI/trunk``
     - Read-only ``/legacycode``.
   * - ``NORNIR_IMPORT_CACHE_PATH``
     - ``/tmp/nornir-test-output/ImportCache``
     - Redirects import caches out of the read-only test input.
   * - ``NORNIR_WORKSPACE_HOST``
     - ``..`` (monorepo root)
     - Bind source for ``/workspace``.
   * - ``NORNIR_CLONE_URL`` / ``NORNIR_CLONE_BRANCH``
     - ``https://github.com/jamesra/nornir.git`` / ``dev``
     - Clone source for an empty ``/workspace`` or ``cursor-dev-clone``.
   * - ``NORNIR_SYNC_REMOTE``
     - unset
     - ``1``: checkout ``NORNIR_CLONE_BRANCH`` and ``git pull --ff-only`` on every start.
   * - ``NORNIR_SUBMODULE_UPDATE``
     - unset
     - ``1``: full ``git submodule update --init --recursive`` on container recreate.
   * - ``NORNIR_NET_MOUNTS_DIR_HOST`` / ``NORNIR_NET_CREDS_DIR_HOST``
     -
     - Needed for ``compose.net-mounts.override.yaml``.
   * - ``NORNIR_MQTT_HOST`` / ``_PORT`` / ``_ENABLE``
     - ``host.docker.internal`` / ``1883`` / ``1``
     - Dashboard broker on the host.
   * - ``NORNIR_TILE_IO_WORKERS``, ``NORNIR_TILE_ENCODE_WORKERS``, ``NORNIR_TILE_COPY_WORKERS``
     -
     - AssembleTiles worker counts.
   * - ``GITHUB_TOKEN``
     -
     - Optional, for private submodules or rate limits.

Cursor worker (``Run/nornir-cursor-worker/nornir-cursor-worker.run.env``)
--------------------------------------------------------------------------

Template ``nornir-docker/example.nornir-cursor-worker.run.env``.

.. list-table::
   :header-rows: 1
   :widths: 34 20 46

   * - Key
     - Default
     - Meaning
   * - ``CURSOR_API_KEY``
     - required
     - Cursor API key for ``agent worker start``.
   * - ``GITHUB_TOKEN``
     -
     - Passed to the container only via ``--env-file``.
   * - ``NORNIR_WORKSPACE_STRATEGY``
     - ``clone``
     - ``clone`` or ``mounted``.
   * - ``NORNIR_CLONE_URL`` / ``NORNIR_CLONE_BRANCH``
     - ``https://github.com/jamesra/nornir.git`` / ``dev``
     - Clone source.
   * - ``NORNIR_CLONE_REFRESH``
     - unset
     - ``1`` wipes ``/workspace`` before cloning.
   * - ``NORNIR_SYNC_REMOTE``
     - unset
     - ``mounted``: ``git pull --ff-only`` on start.
   * - ``NORNIR_WORKER_DEV_PARITY_MOUNTS``
     - unset
     - ``1`` adds the cursor-dev data mounts and in-container CIFS.
   * - ``NORNIR_CURSOR_WORKER_ENV_FILE`` (host)
     - discovery
     - Explicit path of this file for ``start-cursor-worker.ps1`` and ``compose.cursor-worker.yaml``.

Other launcher variables
------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Variable
     - Default
     - Consumer
   * - ``NORNIR_DOCKER_IMAGE``
     - ``nornir:dev``
     - ``nd-build.ps1`` image.
   * - ``NORNIR_DEV_PORT_PUBLISH``
     -
     - ``docker-run-nornir-dev.ps1``: ``host:container`` pairs separated by ``;``.
   * - ``NORNIR_RELEASE``, ``NORNIR_IMAGE_VARIANT``
     - from ``VERSION``
     - ``docker-build.ps1`` build args (``Builds/nornir/build.env``).

Viking keys that ``stack.ps1`` checks
-------------------------------------

The Viking registry marks these as required; set them in the Viking stack's run env (templates in
``<Viking>/deploy/examples/``):

* ``viking-proxy``: ``VIKING_DOMAIN``, ``VIKING_COMPUTE_HOST``, ``VIKING_IIS_HOST`` (in
  ``host.env`` on ``web``, above).
* ``viking-certs``: ``VIKING_DOMAIN``, ``TLS_MODE``, ``TLS_CERT_NAME``.
* ``viking-identity``: ``SQL_SERVER_HOST``, ``SQL_SERVER_USER``, ``SQL_SERVER_PASSWORD``,
  ``SQL_SERVER_IDENTITY_DB``, ``SQL_SERVER_CONFIG_DB``, ``SQL_SERVER_GRANTS_DB``,
  ``IDENTITY_SERVER_SECRET``, ``IDENTITY_SERVER_API_SECRET``, ``IDENTITY_SERVER_MVC_SECRET``,
  ``IDENTITY_SERVER_RO_VIKING_SECRET``; secret files ``secrets.json``, ``Duende_License.key``.
* ``viking-annotation``: ``ConnectionStrings__AnnotationConnection``,
  ``IdentityServer__Endpoint``, ``IdentityServer__ClientId``, ``IdentityServer__ClientSecret``.
* ``viking-corrections``: ``IdentityServer__Endpoint``, ``IdentityServer__ClientSecret``,
  ``CorrectionService__Name``.
* ``viking-iis``: ``VIKING_IIS_DEPLOY_ROOT``.

Deprecated names
----------------

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Old
     - New
     - Still read?
   * - ``NORNIR_MONOREPO_ROOT`` (host side)
     - ``NORNIR_REPO_ROOT_HOST``
     - yes, with a warning
   * - ``Run/nornir-dashboard/dashboard.run.env``
     - ``Run/nornir-dashboard/nornir-dashboard.run.env``
     - yes (``start-dashboard.ps1``)
   * - ``mounted-configs/nornir-build-*``
     - ``Work/nornir-build-*``
     - ``prune`` still cleans the old folder
   * - ``C:\Docker`` default root
     - ``D:\Docker`` (Windows), ``/srv/docker`` (Linux)
     - set ``NORNIR_DOCKER_USER_ROOT`` to keep ``C:\Docker``
   * - ``Run/nornir-dev/.run.nornir-dev.env`` (net mounts)
     - ``Run/nornir-net-mounts/.run.nornir-net-mounts.env``
     - yes, as a fallback
   * - ``Builds/nornir-cursor-worker/.env.cursor-worker``, ``nornir-docker/.env.cursor-worker``
     - ``Run/nornir-cursor-worker/nornir-cursor-worker.run.env``
     - yes, as fallbacks
   * - ``Initialize-NornirBuildAppliance.ps1 -MonorepoRoot``
     - connectomes-deploy ``Initialize-DockerHost.ps1 -Role compute -NornirRepoRoot`` (``-RepoRoot``
       is still accepted as an alias)
     - removed

``NORNIR_MONOREPO_ROOT`` inside containers (``cursor-dev-entry.sh``, the image build) is a
container path and is unaffected.
