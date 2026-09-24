Docker images
=============

The ``nornir-docker`` directory provides container images for running the **headless** Nornir stack (Python 3.14, no Pyre UI). Pyre is **not** shipped in these images. Which role to launch is :doc:`../guides/run_the_stack`. Host checks are :doc:`../host_requirements`.

* End users: install the Windows app — |pyre-windows-installer-latest| (see :doc:`../packages/pyre_install`).
* Developers: use ``venv/pyre314`` on the host for the PyQt-based UI (see :doc:`../development/pyre_development`).

.. toctree::
   :maxdepth: 2

   images
   nd_build
   remote_deployment
   dashboard
   annotation_gallery
   cursor_dev
   cursor_worker
   windows_cursor_layout
