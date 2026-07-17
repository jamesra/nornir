Build dashboard (co-located)
============================

Mosquitto + ``nornir-dashboard`` for MQTT build telemetry on the same machine as the
build appliance.

Start / restart::

  .\nornir-docker\start-dashboard.ps1
  # or after Initialize-NornirBuildAppliance.ps1 (starts automatically)

Run env template: ``nornir-docker/example.dashboard.run.env`` →
``<NORNIR_DOCKER_USER_ROOT>\Run\nornir-dashboard\dashboard.run.env``.

Default UI bind: ``127.0.0.1:8087``. Build containers publish with
``NORNIR_MQTT_HOST=host.docker.internal`` (set by ``start-nornir-build.ps1``).

Compose file: ``nornir-docker/compose.dashboard.yaml``.
