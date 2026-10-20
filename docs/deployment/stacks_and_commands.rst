Stacks and commands
===================

``stack.ps1`` is the one entry point for every stack. This page is the command reference; the
Viking deployment docs link here instead of repeating it. ``Get-Help <root>/stack.ps1 -Full``
prints the same options from the script. Viking service specifics (what each stack needs) start at
the :viking:`Viking bring-up checklist <index.html>`.

::

   stack.ps1 [<stack>|all|<tool>] [<action>] [-Target <name>|all] [-Sync] [-Images build|ghcr|load]
             [-Profile <p>[,<p>]] [-Service <svc>] [-Follow] [-Tail <n>] [-Force] [-Days <n>]
             [-Root <path>] [-Cert <file> -Key <file> [-Chain <file>] [-PfxPassword <pw>]]
             [-- <command for exec>]

With no arguments it runs ``list``. A stack with no action runs ``status``. The stack and the
action can come in either order: ``stack.ps1 viking-identity up`` and ``stack.ps1 up
viking-identity`` are the same (the Viking docs use the second form).

Stacks
------

Stack keys are kebab-case and are also the ``Run/<stack>/`` folder name and the compose project
name. The registries are ``nornir-docker/deploy/stacks.psd1`` and
``<VIKING_REPO_ROOT_HOST>/deploy/stacks.psd1`` (Viking stacks appear only when
``VIKING_REPO_ROOT_HOST`` is set in ``host.env``). ``stack.ps1 list`` prints both, with a
``ThisHost`` column for the stacks in ``NORNIR_DOCKER_HOST_STACKS``.

.. list-table::
   :header-rows: 1
   :widths: 22 10 12 56

   * - Stack
     - Engine
     - Host
     - What it is
   * - ``nornir-build``
     - script
     - compute
     - Build appliance container ``nornir-build`` (``nornir:cupy`` or ``nornir:prod``) with
       in-container CIFS. :doc:`nornir_build_appliance`
   * - ``nornir-dashboard``
     - script
     - compute, dev
     - Mosquitto + build dashboard on 127.0.0.1:8087. :doc:`dashboard`
   * - ``nornir-dev``
     - script
     - dev
     - Programmer shell (``cursor-dev`` compose service). :doc:`nornir_dev_and_worker`
   * - ``nornir-cursor-worker``
     - script
     - dev
     - Cursor self-hosted agent worker. :doc:`nornir_dev_and_worker`
   * - ``viking-proxy``
     - compose
     - web
     - nginx SNI passthrough on 443; ACME HTTP-01 webroot and https redirect on 80
   * - ``viking-certs``
     - compose
     - web
     - The single certificate renewer (``letsencrypt`` / ``acme-eab``; idle in ``manual``)
   * - ``viking-identity``
     - compose
     - web
     - Duende IdentityServer (OIDC issuer, WebApi, Management)
   * - ``viking-annotation``
     - compose
     - web
     - gRPC annotation service
   * - ``viking-corrections``
     - compose
     - web
     - gRPC section-correction service
   * - ``viking-segmentation``
     - compose
     - compute
     - SAM2 segmentation gRPC servers (GPU); profile ``models`` adds v3, v4, and sem-v1
   * - ``viking-iis``
     - iis
     - iis
     - Legacy IIS sites behind ``websvc.<domain>``

The annotation gallery (``gallery``, ``gallery-tem``, ``gallery-sem``) is not a ``stack.ps1``
stack: its compose file lives in the Sam2Trainer repository, and the proxy routes those names to
port 8442 on ``web``. Start and update it from that repository.

``all`` means the stacks in this host's ``NORNIR_DOCKER_HOST_STACKS``, in that order (``down``
runs in reverse). It stops at the first failure, except for ``status``.

Stack actions
-------------

.. list-table::
   :header-rows: 1
   :widths: 12 44 44

   * - Action
     - Compose stacks
     - Script stacks (``nornir-build``; ``nornir-dashboard`` noted)
   * - ``up``
     - ``compose up -d --remove-orphans``, then the health check
     - ``nornir-build``: starts a detached, kept container named ``nornir-build``; if it exists
       and is stopped, ``docker start``; if running, does nothing. Dashboard: ``start-dashboard.ps1``.
   * - ``down``
     - ``compose down``
     - ``docker rm -f nornir-build``. Dashboard: ``start-dashboard.ps1 -Down``.
   * - ``restart``
     - ``compose up -d --force-recreate --remove-orphans``
     - ``docker restart nornir-build`` (or ``up`` when absent).
   * - ``rebuild``
     - ``compose build --pull``, then ``up -d --force-recreate``
     - ``nornir-build``: remove the container and ``up`` again (new ``Work/`` session; picks up a
       pulled image). Dashboard: ``start-dashboard.ps1 -Rebuild`` (Mosquitto keeps running).
   * - ``build``
     - ``compose build``
     - via the stack's compose files, when it has them
   * - ``pull``
     - ``compose pull --ignore-buildable``
     - ``nornir-build``: ``docker-pull.ps1`` (``nornir:prod`` and ``nornir:cupy`` from GHCR)
   * - ``push``
     - not supported
     - ``nornir-build``: ``docker-push.ps1`` (maintainers only)
   * - ``logs``
     - ``compose logs --tail <Tail> [-f] [<Service>]``
     - ``docker logs --tail <Tail> [-f] nornir-build``
   * - ``ps``, ``status``
     - ``compose ps``; ``status`` also probes the health URL
     - ``docker ps -a`` filtered to the container
   * - ``exec``
     - ``compose exec <Service> <command after -->``
     - ``docker exec -it nornir-build <command after -->``
   * - ``shell``
     - ``compose exec <Service>`` bash (or sh)
     - ``nornir-build``: ``docker exec -it nornir-build bash`` when running, otherwise a new
       interactive ``--rm`` container
   * - ``config``
     - ``compose config --quiet`` (validates the merged env and files)
     - via the stack's compose files, when it has them
   * - ``deploy``
     - iis only: runs the Viking IIS deploy script (``up`` and ``rebuild`` are aliases)
     - not supported

``-Service`` defaults to the registry's ``DefaultService``. ``up``, ``restart``, ``rebuild``,
``build`` and ``config`` first check the stack's required keys and secret files and stop with a
list of what is missing.

Examples::

   stack.ps1 list
   stack.ps1 viking-identity up
   stack.ps1 viking-identity logs -Follow -Tail 500
   stack.ps1 viking-annotation exec -Service <service> -- ls /app
   stack.ps1 viking-segmentation up -Profile seg-v3
   stack.ps1 all down

Tools
-----

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - What it does
   * - ``stack.ps1 list``
     - Registered stacks, engines, and which ones this host runs.
   * - ``stack.ps1 targets``
     - The targets in ``Run/_host/targets.psd1``.
   * - ``stack.ps1 doctor``
     - Checks the layout folders, ``host.env``, Docker engine and compose v2, each host stack's
       configuration and ``compose config``, launchers, GPU runtime (GPU stacks), certificate
       validity and hostname coverage, DNS for every ``VIKING_HOSTNAME_*`` (Viking stacks), ufw and
       sshd (Linux). Exit code 1 when any check fails.
   * - ``stack.ps1 secrets new <stack> [KEY ...]``
     - Generates a random 32-byte URL-safe value for: every ``*_SECRET``, ``*_TOKEN`` or
       ``*_PASSWORD`` key the stack's registry lists (``Required`` or ``GeneratedSecrets``); every
       key in ``<stack>.run.env`` or ``secrets/secrets.env`` still holding a
       ``REPLACE_WITH_GENERATED...`` placeholder; and every ``KEY`` named on the command line.
       The value replaces the placeholder in ``secrets.env`` if the key is there, else in
       ``<stack>.run.env``, else it is appended to ``secrets.env``. Keys with a real value are
       kept. Never generates ``SQL_SERVER_PASSWORD`` or connection strings, and leaves empty
       optional client secrets alone (empty = client disabled) unless you name them.
   * - ``stack.ps1 certs status``
     - Installed certificate: key match, issuer, days left, intermediates, SAN coverage of every
       hostname, last renewal.
   * - ``stack.ps1 certs letsencrypt``
     - One-shot ``viking-certs`` issuance with HTTP-01 (needs public port 80 to ``web`` and
       ``viking-proxy`` up), then starts the renewer. Set ``TLS_MODE=letsencrypt`` in ``host.env``.
   * - ``stack.ps1 certs acme-eab``
     - Same, against ``TLS_ACME_SERVER`` with External Account Binding (InCommon/Sectigo).
   * - ``stack.ps1 certs manual -Cert <pem> -Key <pem> [-Chain <pem>] [-PfxPassword <pw>] [-Force]``
     - Validates that the key matches, the certificate is currently valid and covers every
       hostname (or ``TLS_HOSTNAMES``), then writes ``Certs/<name>/{cert,chain,fullchain,privkey}.pem``,
       ``cert.pfx`` and ``.renewed-at``, keeping the old files in ``previous-<stamp>/``. Refuses a
       certificate that expires sooner than the installed one unless ``-Force``. Then restarts
       containers labelled ``viking.tls-reload=true``. Set ``TLS_MODE=manual``.
   * - ``stack.ps1 certs push -From web [-Target <name>]``
     - Run on the dev box. ``-From`` fetches ``Certs/<name>/`` from that target over ``scp``; the
       command then copies it to the given targets, or to every target with ``CertPush = $true``,
       and runs ``certs reload`` (Linux) or ``certs install-iis`` (Windows) there. Without
       ``-From`` it pushes the local ``Certs/<name>/``; running ``stack.ps1 certs push`` on ``web``
       itself (for example from cron) works too, but then ``web`` needs its own
       ``targets.psd1`` and SSH keys on the destinations.
   * - ``stack.ps1 certs reload``
     - Restarts running containers labelled ``viking.tls-reload=true``.
   * - ``stack.ps1 certs install-iis``
     - On the IIS host: imports ``Certs/<name>/cert.pfx`` and binds it to ``VIKING_HOSTNAME_WEBSVC``.
   * - ``stack.ps1 tunnel -Target <name>``
     - ``ssh -N`` with a ``-L`` forward for every entry in that target's ``Tunnels``
       (:doc:`ports_and_remote_access`).
   * - ``stack.ps1 prune [-Days 14] [-Force]``
     - Lists ``Work/nornir-build-*`` (and legacy ``mounted-configs/nornir-build-*``) folders older
       than ``-Days``, skipping any folder a running container mounts. ``-Force`` deletes them.

Local and remote
----------------

Without ``-Target``, everything runs on this machine. With ``-Target <name>`` (a key in
``Run/_host/targets.psd1``, a comma list, or ``all``), ``stack.ps1`` runs the same arguments on
each target over SSH, as ``pwsh -File <Root>/stack.ps1 ...``. The target uses its own layout and
env files; nothing from your machine's ``Run/`` is sent. Interactive actions (``shell``,
``exec``, ``logs -Follow``) get a TTY (``ssh -t``).

Two commands are exceptions: ``tunnel`` opens SSH from this machine, and ``certs push`` runs
here, uses ``-From`` as the source and ``-Target`` as the destination list.

``-Sync``
   Before running the command, for each checkout in the target's ``Repos``: checks that your local
   branch is pushed (HEAD equals its upstream; stops otherwise) and warns about uncommitted
   changes, then runs ``git pull --ff-only`` and ``git submodule update --init --recursive`` on the
   target. Push first; ``-Sync`` deploys what is on the remote, not your working tree.

``-Images``
   Where the target's images come from:

   * ``build`` (default): the target builds them (``rebuild`` runs ``compose build --pull``).
   * ``ghcr``: before ``up``, ``restart`` or ``rebuild``, runs ``pull`` on the target (GHCR login on
     the target required).
   * ``load``: ``docker save`` each image here and ``docker load`` it on the target over SSH; for
     hosts that cannot reach the registry. Images missing locally are skipped with a warning.

Examples::

   stack.ps1 doctor -Target all
   stack.ps1 viking-segmentation rebuild -Target compute -Sync
   stack.ps1 all up -Target web -Sync -Images ghcr
   stack.ps1 nornir-build shell -Target compute
   stack.ps1 viking-identity logs -Follow -Target web

Where to run what
-----------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Task
     - Run
   * - Deploy or update any server stack
     - Dev box: ``stack.ps1 <stack> rebuild -Target <host> -Sync``
   * - Health of everything
     - Dev box: ``stack.ps1 doctor -Target all`` and ``stack.ps1 all status -Target all``
   * - Issue or renew a certificate
     - Dev box: ``stack.ps1 certs letsencrypt|acme-eab|manual -Target web``
   * - Distribute the certificate
     - Dev box: ``stack.ps1 certs push -From web``
   * - Interactive volume build
     - Dev box: ``stack.ps1 nornir-build shell -Target compute`` (inside ``tmux`` on ``compute``
       for long builds, see :doc:`nornir_build_appliance`)
   * - Dashboard, debugger ports
     - Dev box: ``stack.ps1 tunnel -Target compute``
   * - Programmer shell, tests
     - Dev box: ``stack.ps1 nornir-dev shell`` (:doc:`nornir_dev_and_worker`)

Exit codes
----------

* A stack action exits with the docker or launcher exit code (0 on success).
* ``all`` exits with the first failing stack's code and stops there (``status`` keeps going).
* ``doctor`` exits 1 when any check is ``[FAIL]``.
* With ``-Target``, the exit code is the last non-zero code from any target (0 when all succeed);
  a failing ``-Sync`` stops before the command runs.
* A configuration error (unknown stack, missing required key, unknown target) throws and exits 1.

``nd-build``: one ``nornir-build`` command in a container
---------------------------------------------------------

``nornir-docker/nd-build.ps1`` (and ``nd-build.cmd``) run the ``nornir-build`` CLI inside a
throwaway container with the current directory at ``/workspace``, without the appliance's CIFS
mounts or ``Work/`` session::

   .\nornir-docker\nd-build.ps1 -- --help
   .\nornir-docker\nd-build.ps1 -Gpu -- <nornir-build arguments>

Default image ``nornir:dev``; set ``NORNIR_DOCKER_IMAGE=nornir:prod`` for CPU-only or
``nornir:cupy``. ``NORNIR_DOCKER_GPU=1`` equals ``-Gpu``; ``NORNIR_DOCKER_EXTRA_ARGS`` adds
``docker run`` arguments. It publishes to the dashboard when ``NORNIR_MQTT_HOST`` is set. The
compose equivalent::

   docker compose -f nornir-docker/compose.yaml run --rm -v "$PWD:/workspace" -w /workspace nornir nornir-build --help
