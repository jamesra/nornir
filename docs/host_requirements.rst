Host requirements
=================

These are guidelines for whether a machine can run Nornir. They are not measured installer checks. Production dataset size, scratch disk, and GPU class are in :doc:`performance/envelope`.

Pyre on Windows
---------------

* 64-bit Windows.
* A GPU and driver that can open an OpenGL window.
* The Windows installer does not need Python, Git, or CUDA. It does not include CuPy. See :doc:`packages/pyre_install`.
* A developer build needs Python 3.13+ and the host virtual environment ``venv/pyre314``. See :doc:`development/pyre_development`.

Headless pipeline on a workstation
----------------------------------

* 64-bit operating system. Development has focused on Windows; Docker images are Linux.
* Python 3.13+ for a host install of ``nornir-build``.
* Plan on about 2 GB of RAM per CPU core you will keep busy. That is a sizing guideline, not a startup check. Heavy pipelines sometimes need closer to 3 GB per core; see :doc:`performance/envelope`.

Docker and the build appliance
------------------------------

* Docker Desktop with WSL2.
* The CIFS kernel module when the container mounts NAS shares.
* ``nornir:prod`` is CPU-only and does not need a GPU.
* ``nornir:dev`` and ``nornir:cupy`` need an NVIDIA driver on the host and a GPU with compute capability 7.5 or newer (Turing and later). The image does not need a GPU at build time. Pass ``--gpus all`` (or the launcher's GPU switch) at run time.
* Container images use Python 3.14 and do not ship Pyre.
* Tile I/O on CIFS needs a raised open-file limit. Launchers set ``nofile`` to 65536. Confirm with ``ulimit -n`` inside the container.
* ``NORNIR_DOCKER_USER_ROOT`` defaults to ``C:\Docker``. Many lab machines set it to ``D:\Docker``. Each example on the Docker pages states which path it assumes.

Roles and launchers are in :doc:`guides/run_the_stack`.
