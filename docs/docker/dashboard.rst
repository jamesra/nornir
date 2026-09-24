Build dashboard (co-located)
============================

Mosquitto + ``nornir-dashboard`` for MQTT build telemetry on the same machine as the
build appliance.

Start / restart::

  .\nornir-docker\start-dashboard.ps1
  # or after Initialize-NornirBuildAppliance.ps1 (starts automatically)

Rebuild the dashboard image from local ``nornir-builddashboard`` sources and
recreate **only** the dashboard container (Mosquitto keeps retained run meta)::

  .\nornir-docker\start-dashboard.ps1 -Rebuild
  .\nornir-docker\start-dashboard.ps1 -Rebuild -NoCache

Hard-refresh the browser afterward (or wait for the WebSocket reconnect, which
reloads ``/api/runs``). Progress published while the dashboard was down is not
replayed; the run should reappear from SQLite and/or retained MQTT meta.
Run env template: ``nornir-docker/example.dashboard.run.env`` →
``<NORNIR_DOCKER_USER_ROOT>\Run\nornir-dashboard\dashboard.run.env``.

Sources live in the ``nornir-builddashboard`` git submodule at the monorepo root
(Docker **image** and compose **service** are named ``nornir-dashboard``). If the
submodule is missing, run ``git submodule update --init nornir-builddashboard``
or use ``Initialize-NornirBuildAppliance.ps1`` / ``start-dashboard.ps1``, which
initialize it automatically when a local image build is required.

Default UI bind: ``127.0.0.1:8087``. Build containers publish with
``NORNIR_MQTT_HOST=host.docker.internal`` (set by ``start-nornir-build.ps1``).

Compose file: ``nornir-docker/compose.dashboard.yaml``.

Log retention and UI history
----------------------------

``NORNIR_DASHBOARD_MAX_EVENTS`` (default ``0`` = unlimited / no prune; template in
``example.dashboard.run.env``) optionally caps how many events SQLite keeps
**per run**. Set a positive value to enable prune. Disk growth with the default
is then operator-owned (whole runs still age out via
``NORNIR_DASHBOARD_RETENTION_DAYS``). Events removed by prune or by retention are
gone from the dashboard DB; authoritative full session files remain under
``NORNIR_LOG_ROOT``.

The log pane loads a newest page first, then **Load older** / scroll-to-edge
pages through retained history without dumping the full multi‑MB transcript into
the DOM. **Search** and level checkboxes (errors, warnings, info, debug, events,
status) are applied on the server against all retained events for the run;
unchecked types are excluded from search results, filtered pages, live matches
while filtering, and **Download logs**
(``GET /api/runs/{run_id}/events/export``).
