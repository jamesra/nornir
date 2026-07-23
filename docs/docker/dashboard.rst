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

Default UI bind: ``127.0.0.1:8087``. Build containers publish with
``NORNIR_MQTT_HOST=host.docker.internal`` (set by ``start-nornir-build.ps1``).

Compose file: ``nornir-docker/compose.dashboard.yaml``.
