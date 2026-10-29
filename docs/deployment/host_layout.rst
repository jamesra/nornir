Host layout
===========

Every machine that runs a stack (dev box, ``compute``, ``web``, ``iis``) has the same folder tree
under one root, ``NORNIR_DOCKER_USER_ROOT``:

* Windows: ``D:\Docker``
* Ubuntu: ``/srv/docker``

Nothing under the root is committed. Templates live in the repositories (``example.*`` files) and
are copied in by ``nornir-docker/deploy/Initialize-DockerHost.ps1``, which never overwrites an
existing file. Re-run it after adding a stack to a host; it only fills in what is missing.

The tree
--------

::

   <root>/
     stack.ps1                              forwarding launcher -> <repo>/nornir-docker/deploy/stack.ps1
     Run/
       _host/
         host.env                           machine settings for every stack on this host
         secrets/secrets.env                machine-wide secrets (GITHUB_TOKEN)
         targets.psd1                       remote targets (on the machines you deploy from)
       <stack>/
         <stack>.run.env                    settings for one stack
         secrets/
           secrets.env                      generated or pasted secrets for that stack
           ...                              secret files (Duende_License.key, secrets.json, ...)
       nornir-net-mounts/                   CIFS shares for nornir-build (compute)
         net-mounts/nas-mounts.tsv
         secrets/net-creds/*.cred
         .run.nornir-net-mounts.env
     Builds/<stack>/                        build-time env (docker-build.ps1 build.env) and
                                            forwarding launchers for older habits
     Data/<stack>/                          persistent service data (models, keys, databases)
     Certs/<cert-name>/                     the TLS certificate shared by every TLS service
       cert.pem chain.pem fullchain.pem privkey.pem cert.pfx .renewed-at
     Work/nornir-build-<version>-<stamp>/   per-session /workspace for nornir-build
     Logs/<stack>/                          persistent logs (nornir-build: NORNIR_LOG_ROOT)

What goes where
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Folder
     - Contents and rules
   * - ``stack.ps1``
     - A small generated launcher that resolves ``NORNIR_REPO_ROOT_HOST`` at run time and calls
       the real ``stack.ps1`` in the checkout, so it keeps working after ``git pull``. Never copy
       the real script here; it dot-sources sibling helpers and breaks when copied.
   * - ``Run/_host/``
     - Settings that apply to the whole host: which stacks it runs, the domain, the TLS mode, the
       repository paths. ``targets.psd1`` only exists where you run ``-Target`` commands from.
   * - ``Run/<stack>/``
     - One folder per stack key (the same name as the compose project and the registry key).
       ``<stack>.run.env`` holds settings; ``secrets/`` holds anything secret.
   * - ``Builds/<stack>/``
     - Build-time overrides for ``docker-build.ps1`` (``build.env``, ``.build.<id>.env``; the
       script reads them from the directory you invoke it in). ``Builds/nornir-build/`` also
       holds forwarding launchers for ``start-nornir-build.ps1`` and ``start-dashboard.ps1``.
   * - ``Data/<stack>/``
     - Data a service must keep across ``rebuild``: segmentation models
       (``Data/viking-segmentation/models``), Identity data-protection keys, and similar. Back it
       up. Exported to compose as ``STACK_DATA_DIR``.
   * - ``Certs/<cert-name>/``
     - Written only by ``viking-certs`` (automatic modes) or ``stack.ps1 certs manual``. Every TLS
       container mounts ``Certs/`` read-only and loads
       ``/certs/<TLS_CERT_NAME>/{fullchain,privkey}.pem``. ``cert.pfx`` is for IIS.
   * - ``Work/``
     - Disposable ``nornir-build`` session folders. Clean with ``stack.ps1 prune``
       (:doc:`stacks_and_commands`). Replaces the old ``mounted-configs/``. Build a given volume
       from **one machine at a time**: volume metadata saves (``VolumeData.xml`` and
       ``VolumeData.db``) are not locked across machines, so two hosts saving the same volume on a
       share can fail or diverge.
   * - ``Logs/<stack>/``
     - Host-side log folders. ``nornir-build`` mounts ``Logs/nornir-build`` at
       ``/var/log/nornir`` and sets ``NORNIR_LOG_ROOT=/var/log/nornir``. Exported to compose as
       ``STACK_LOGS_DIR``.

Checkouts are outside the root: ``/srv/src/nornir`` and ``/srv/src/Viking`` on Ubuntu (created by
``bootstrap-ubuntu.sh``), any path on Windows (for example ``D:\src\git\nornir``).

Permissions
-----------

On Ubuntu ``bootstrap-ubuntu.sh`` makes the deploy user own ``/srv/docker`` and ``/srv/src``.
``Initialize-DockerHost.ps1`` and ``stack.ps1`` then set:

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Path
     - Mode
     - Set by
   * - ``Run/_host/secrets/``, ``Run/<stack>/secrets/``, ``Run/nornir-net-mounts/secrets/net-creds/``
     - ``700``
     - ``Initialize-DockerHost.ps1``
   * - ``Run/_host/secrets/secrets.env``, copied secret templates, ``*.cred``
     - ``600``
     - ``Initialize-DockerHost.ps1``
   * - ``Run/<stack>/secrets/secrets.env``
     - ``600``
     - ``stack.ps1 secrets new``
   * - ``Certs/<name>/`` and its ``*.pem`` / ``cert.pfx``
     - ``755`` / ``644``
     - ``stack.ps1 certs manual`` (containers run as non-root users and must read them)
   * - ``stack.ps1`` and other launchers
     - ``755``
     - ``Initialize-DockerHost.ps1``

Files you copy in by hand keep whatever mode they had; fix them with ``chmod 600``. On Windows,
keep ``D:\Docker\Run`` readable only by your account (default for a folder outside your profile is
readable by all local users; tighten the ACL with ``icacls`` if the box is shared).

Environment merge order
-----------------------

For a stack, ``stack.ps1`` merges these files; a later file wins for the same key:

1. ``Run/_host/host.env``
2. ``Run/_host/secrets/secrets.env``
3. ``Run/<stack>/<stack>.run.env``
4. ``Run/<stack>/secrets/secrets.env``

Compose stacks get all four as ``--env-file`` arguments (in that order) for variable substitution,
and every merged value is also set in the process environment while compose runs. Script stacks
(``nornir-build``, ``nornir-dashboard``, ``nornir-dev``, ``nornir-cursor-worker``) get the
merged values as process environment for their launcher. A value already set in your shell does
not override the files for ``stack.ps1``; the files win.

Contract variables
------------------

After the merge, ``stack.ps1`` adds these. Compose files reference them instead of hard-coding
paths. Paths use forward slashes (``D:/Docker/...``), which Docker Desktop accepts.

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Variable
     - Value
   * - ``NORNIR_DOCKER_USER_ROOT``
     - The layout root.
   * - ``STACK_NAME``
     - The stack key, for example ``viking-identity``.
   * - ``STACK_RUN_DIR``
     - ``<root>/Run/<stack>``
   * - ``STACK_SECRETS_DIR``
     - ``<root>/Run/<stack>/secrets``
   * - ``STACK_DATA_DIR``
     - ``<root>/Data/<stack>``
   * - ``STACK_LOGS_DIR``
     - ``<root>/Logs/<stack>``
   * - ``DOCKER_CERTS_DIR``
     - ``<root>/Certs``
   * - ``DOCKER_WORK_DIR``
     - ``<root>/Work``
   * - ``NORNIR_REPO_ROOT_HOST``
     - nornir checkout on this host (from ``host.env``; defaults to the checkout that contains
       ``stack.ps1``).
   * - ``VIKING_REPO_ROOT_HOST``
     - Viking checkout on this host (from ``host.env``).
   * - ``VIKING_HOSTNAME_<SERVICE>``
     - ``<sub>.<VIKING_DOMAIN>`` for each service not overridden in ``host.env``
       (:doc:`configuration_reference`).
   * - ``TLS_CERT_NAME``
     - ``VIKING_DOMAIN`` unless set.

``NORNIR_DOCKER_USER_ROOT``, ``STACK_*`` and ``DOCKER_*`` are always recomputed from the layout
root; values for them in env files are replaced. The other contract variables are only filled in
when empty.
