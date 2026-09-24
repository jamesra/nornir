Run the stack
==============

Headless Nornir runs in Docker. Pyre does not. Three roles stay separate:

.. list-table::
   :header-rows: 1
   :widths: 22 40 38

   * - Role
     - Use it for
     - Start here
   * - Programmer shell
     - Editable checkout, tests, Dev Containers
     - :doc:`../docker/cursor_dev`
   * - Cursor agent worker
     - Self-hosted Cursor worker process
     - :doc:`../docker/cursor_worker`
   * - Build appliance
     - Interactive ``nornir-build`` with NAS mounts and the dashboard
     - :doc:`../docker/remote_deployment`

Image tags, GPU versus CPU images, and how to build them are in :doc:`../docker/images`. Run one ``nornir-build`` command in a container with :doc:`../docker/nd_build`.

Also:

* :doc:`../docker/dashboard` — MQTT build dashboard on port 8087.
* :doc:`../docker/annotation_gallery` — annotation crop review, a service on the SAM2 trainer Compose file. That image does not install Nornir.
* :doc:`../docker/windows_cursor_layout` — ``D:\Docker`` layout for the Cursor worker. ``NORNIR_DOCKER_USER_ROOT`` defaults to ``C:\Docker`` and is often set to ``D:\Docker``; that page assumes ``D:\Docker``.

Host checks (driver, WSL2, open-file limit) are in :doc:`../host_requirements`.
