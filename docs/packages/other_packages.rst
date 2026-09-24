Other repositories in the umbrella
====================================

These components are part of the same workspace. Their deep documentation lives in dedicated sections of this monodoc:

* **nornir-docker** — see :doc:`../docker/index`.
* **nornir-builddashboard** — MQTT build telemetry dashboard (sources submodule; Docker image/service name ``nornir-dashboard``). See :doc:`../docker/dashboard`.
* **nornir-pyre** — interactive registration and visualization (PyQt6 / OpenGL).

  * End users (Windows installer): :doc:`pyre_install`
  * Developers and packaging: :doc:`../development/pyre_development`

When a package gains stable public APIs worth autodoc, add a section under :doc:`index` and API stubs under ``docs/api/``.
