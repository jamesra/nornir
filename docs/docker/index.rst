Docker images
=============

The ``nornir-docker`` directory provides container images for running the **headless** Nornir stack (Python 3.14, no Pyre UI). Pyre is **not** shipped in these images. Deploying and running the stacks (build appliance, dashboard, Dev Container, Cursor worker, Viking servers) is :doc:`../deployment/index`. Host checks are :doc:`../host_requirements`.

* End users: install the Windows app — |pyre-windows-installer-latest| (see :doc:`../packages/pyre_install`).
* Developers: use ``venv/pyre314`` on the host for the PyQt-based UI (see :doc:`../development/pyre_development`).

.. toctree::
   :maxdepth: 2

   images
   annotation_gallery
