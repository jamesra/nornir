Build dashboard (``nornir-dashboard``)
======================================

Mosquitto plus the ``nornir-dashboard`` web UI, for live MQTT telemetry from ``nornir-build`` on
the same machine. Sources are the ``nornir-builddashboard`` submodule; the Docker image and the
compose service are named ``nornir-dashboard``. Compose file:
``nornir-docker/compose.dashboard.yaml`` (fixed project name ``nornir-dashboard``, so volumes and
the ``nornir-dashboard_default`` network are the same from any directory).

Start, rebuild, stop
--------------------

::

   stack.ps1 nornir-dashboard up            # start-dashboard.ps1
   stack.ps1 nornir-dashboard rebuild       # start-dashboard.ps1 -Rebuild
   stack.ps1 nornir-dashboard down          # start-dashboard.ps1 -Down
   stack.ps1 nornir-dashboard status        # compose ps + http://127.0.0.1:8087/
   stack.ps1 nornir-dashboard logs -Follow

Add ``-Target compute`` for the server. ``rebuild`` rebuilds the image from local
``nornir-builddashboard`` sources and recreates **only** the dashboard container; Mosquitto keeps
running, so retained run metadata survives. For a clean layer rebuild run
``.\nornir-docker\start-dashboard.ps1 -Rebuild -NoCache``. Hard-refresh the browser afterwards
(the UI also reloads ``/api/runs`` when its WebSocket reconnects). Progress published while the
dashboard was down is not replayed; the run reappears from SQLite and the retained MQTT metadata.

If the submodule is missing, ``start-dashboard.ps1`` initializes it when a local image build is
needed (or run ``git submodule update --init nornir-builddashboard``).

The UI is at http://127.0.0.1:8087. On a server, open it through
``stack.ps1 tunnel -Target compute``.

Run env
-------

``<root>/Run/nornir-dashboard/nornir-dashboard.run.env``, from
``nornir-docker/deploy/examples/example.nornir-dashboard.run.env``. ``start-dashboard.ps1`` falls
back to the legacy name ``dashboard.run.env``. Secrets (the token) go in
``Run/nornir-dashboard/secrets/secrets.env``; ``stack.ps1`` merges both
(:doc:`host_layout`).

.. list-table::
   :header-rows: 1
   :widths: 36 18 46

   * - Variable
     - Default
     - Purpose
   * - ``NORNIR_DASHBOARD_BIND_HOST``
     - ``127.0.0.1``
     - Host address for the published UI port 8087.
   * - ``NORNIR_MQTT_BIND_HOST``
     - ``127.0.0.1``
     - Host address for the published broker port 1883 (template and compose default). Keep it
       on loopback: the broker has no authentication, and on Linux published ports bypass ufw.
   * - ``NORNIR_DASHBOARD_TOKEN``
     - unset
     - When set, every ``/api/*`` request and the WebSocket must present it. Required before
       widening ``NORNIR_DASHBOARD_BIND_HOST``.
   * - ``NORNIR_DASHBOARD_ALLOW_DELETE``
     - ``1``
     - ``0`` refuses ``DELETE /api/runs/{run_id}``.
   * - ``NORNIR_DASHBOARD_MAX_EVENTS``
     - ``0``
     - Max retained events per run in SQLite (``0`` = unlimited, no prune).
   * - ``NORNIR_DASHBOARD_RETENTION_DAYS``
     - ``30``
     - Delete runs with no activity for this many days (``0`` disables).
   * - ``NORNIR_DASHBOARD_STALE_AFTER``
     - ``600``
     - Seconds without traffic before a running build shows as stale (``<=0`` falls back to 600).

Set inside the container by the compose file (change only when running the dashboard outside
Docker): ``NORNIR_MQTT_HOST`` (``mosquitto``; app default ``127.0.0.1``), ``NORNIR_MQTT_PORT``
(``1883``), ``NORNIR_MQTT_RUN_TOPIC_ROOT`` (``nornir/run``), ``NORNIR_DASHBOARD_HOST``
(``0.0.0.0``; app default ``127.0.0.1``), ``NORNIR_DASHBOARD_PORT`` (``8087``),
``NORNIR_DASHBOARD_DB`` (``/data/nornir-dashboard.db`` on the ``dashboard-data`` volume). The app
also reads ``NORNIR_DASHBOARD_STALE_SWEEP_INTERVAL`` (``60``) and
``NORNIR_DASHBOARD_RETENTION_SWEEP_INTERVAL`` (``86400``). Malformed numbers log a warning and use
the default.

Generate the token with ``stack.ps1 secrets new nornir-dashboard`` (:doc:`accounts_and_tokens`). Clients send it as ``Authorization: Bearer <token>``, an
``X-Dashboard-Token`` header, or ``?token=``; open ``http://127.0.0.1:8087/?token=<token>`` once
and the page keeps it for the session. ``/``, ``/static/*`` and ``/api/health`` are not gated.

Publishers
----------

``nornir-build`` joins the ``nornir-dashboard_default`` network and publishes to
``mosquitto:1883`` (:doc:`nornir_build_appliance`); cursor-dev publishes to
``host.docker.internal:1883``. Start the dashboard first so the network exists. Topics are
``nornir/run/{run_id}/...`` (``meta`` retained, ``log/<level>``, ``progress``, ``status``,
``event``).

History and logs
----------------

SQLite keeps run summaries and events, so past runs stay visible after the build exits or the
broker restarts. ``NORNIR_DASHBOARD_MAX_EVENTS`` caps events per run; whole runs age out after
``NORNIR_DASHBOARD_RETENTION_DAYS``. Pruned events are gone from the dashboard; the full session
log stays under ``NORNIR_LOG_ROOT`` (``Logs/nornir-build`` on the host).

The log pane loads the newest page first and pages back with **Load older** or scrolling. Search
and the level checkboxes (errors, warnings, info, debug, events, status) run on the server
against all retained events, and also filter live matches and **Download logs**
(``GET /api/runs/{run_id}/events/export``).

If ``up`` fails with "attempt to write a readonly database", the data volume was created by a
root container; ``start-dashboard.ps1`` re-owns ``nornir-dashboard_dashboard-data`` to uid 10001
on each start, so run ``stack.ps1 nornir-dashboard up`` again.
