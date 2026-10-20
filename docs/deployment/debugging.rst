Debugging
=========

Logs, shells, and exec
----------------------

Every observation command works locally or with ``-Target``::

   stack.ps1 viking-identity logs -Target web                     # last 200 lines
   stack.ps1 viking-identity logs -Follow -Tail 1000 -Target web
   stack.ps1 viking-annotation logs -Service <service> -Target web
   stack.ps1 viking-identity shell -Target web                    # bash (or sh) in DefaultService
   stack.ps1 viking-corrections exec -Service <service> -Target web -- printenv
   stack.ps1 nornir-build shell -Target compute
   stack.ps1 nornir-build logs -Target compute

``stack.ps1 <stack> config`` validates the merged env and compose files without starting
anything; ``stack.ps1 doctor`` runs it for every stack on the host.

Persistent logs
---------------

Container stdout and stderr go to Docker's log (``logs`` above). Files that must survive a
``rebuild`` go under ``<root>/Logs/<stack>/`` (``STACK_LOGS_DIR`` in compose):

* ``nornir-build``: ``Logs/nornir-build`` is mounted at ``/var/log/nornir`` and
  ``NORNIR_LOG_ROOT=/var/log/nornir``, so every ``nornir-build`` session writes its unified log
  there (``nornir_shared.misc.SetupLogging``; see :doc:`../development/logging`).
* Viking stacks: whatever their compose file mounts from ``STACK_LOGS_DIR``.

Read them on the host (``less /srv/docker/Logs/nornir-build/...``) or through VS Code
Remote-SSH.

Health checks
-------------

``stack.ps1 <stack> status`` (and ``up``, ``restart``, ``rebuild``) probes the stack's health URL
after ``compose ps``. Any answer below HTTP 500 counts as healthy; certificate errors are ignored
so a staging certificate does not hide a running service.

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Stack
     - Health URL
   * - ``nornir-dashboard``
     - ``http://127.0.0.1:8087/`` (``/api/health`` returns ``{"ok": true, ...}``)
   * - ``viking-proxy``
     - ``http://127.0.0.1/healthz``
   * - ``viking-identity``
     - ``https://identity.<domain>/.well-known/openid-configuration``
   * - ``viking-annotation``
     - ``https://annotation.<domain>/``
   * - ``viking-corrections``
     - ``https://corrections.<domain>/``
   * - ``viking-iis``
     - ``https://websvc.<domain>/``
   * - ``viking-segmentation``, ``viking-certs``, ``nornir-build``
     - none (gRPC only, a renewer, an interactive container)

Python: debugpy
---------------

For ``nornir-build`` on ``compute``. ``NORNIR_DEBUGPY=1`` only publishes the port; it does not
start a listener, and debugpy is **not** baked into the images.

1. In ``Run/nornir-build/nornir-build.run.env`` on ``compute``, enable the port and recreate the
   container (``start-nornir-build.ps1`` then publishes ``127.0.0.1:<port>`` on the container)::

      NORNIR_DEBUGPY=1
      #NORNIR_DEBUGPY_PORT=5678

   ::

      stack.ps1 nornir-build rebuild -Target compute

2. In the container, install debugpy and start the command under it.
   ``nornir_buildmanager.build`` is the module behind the ``nornir-build`` command::

      stack.ps1 nornir-build shell -Target compute
      python -m pip install debugpy
      python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m nornir_buildmanager.build <nornir-build arguments>

3. On the dev box, open the tunnel (``stack.ps1 tunnel -Target compute``; its ``Tunnels`` entry
   forwards 5678, so change it too if you set ``NORNIR_DEBUGPY_PORT``) and attach VS Code to
   ``localhost:5678`` with this ``.vscode/launch.json`` entry. ``nornir:prod`` and ``nornir:cupy`` run the packages baked under
   ``/opt/nornir``; a ``-Clone`` session runs them from ``/workspace``:

   .. code-block:: json

      {
          "name": "Attach: nornir-build on compute",
          "type": "debugpy",
          "request": "attach",
          "connect": { "host": "127.0.0.1", "port": 5678 },
          "justMyCode": false,
          "pathMappings": [
              { "localRoot": "${workspaceFolder}", "remoteRoot": "/workspace" },
              { "localRoot": "${workspaceFolder}", "remoteRoot": "/opt/nornir" }
          ]
      }

   Breakpoints bind only when your local checkout is at the commit the container runs
   (``-Sync`` deploys keep them equal).

The same attach entry works for the local ``cursor-dev`` container when you publish 5678 there.
``viking-segmentation`` has no debugpy wiring.

.NET: remote debugger
---------------------

The ``web`` tunnel forwards port 4024 for the .NET remote debugger attached to the Identity
container (published on loopback only). How the Viking images start ``vsdbg`` and which
configuration to attach with are in :viking:`Viking identity <identity.html>`.

Before you change code
----------------------

* Reproduce with ``stack.ps1 <stack> logs`` and the persistent log first.
* ``stack.ps1 doctor`` explains most start failures (missing keys, secret files, certificate,
  DNS). The full symptom list is :doc:`troubleshooting`.
