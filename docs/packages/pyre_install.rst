Installing Pyre on Windows
==========================

Pyre is the interactive registration and visualization tool in the Nornir ecosystem.
For lab users who do not use Python or Git, install the **Windows installer**.

Download and install
--------------------

1. Download the **latest** installer (always current):

   * |pyre-windows-installer-latest|

   Or this exact build (|pyre-windows-installer-version|):

   * |pyre-windows-installer|

   Older builds stay on the repository
   `Releases page <https://github.com/jamesra/nornir/releases>`_
   (tags ``pyre-*``). See :doc:`pyre_changelog` for user-facing notes.
2. Run the installer and accept the default options (install location:
   ``C:\Program Files\Nornir\Pyre``).
3. Launch **Pyre** from the Start Menu (optional desktop shortcut during install).

No Python, Git, virtual environment, or CUDA setup is required for the default
installer. GPU acceleration is not included in v1; use a developer install if you
need CuPy (see :doc:`../development/pyre_development`).

First launch
------------

After installation:

1. Start **Pyre** from the Start Menu.
2. Use **File** menus to open an existing STOS file or create a new registration.
3. If OpenGL errors appear, see **Troubleshooting** below.

Logs and support
----------------

Pyre writes session logs under:

``%LOCALAPPDATA%\Nornir\Pyre\logs``

Each run creates dated folders with ``nornir-session-*`` log files. When reporting
a problem, zip that folder and send it to your support contact. You do not need to
run Python or locate a virtual environment.

User settings (window layout, last opened paths) are stored under:

``%APPDATA%\Nornir\Pyre\settings.json``

Troubleshooting
---------------

OpenGL / blank window
~~~~~~~~~~~~~~~~~~~~~

1. Update graphics drivers.
2. Reinstall Pyre from the latest installer link above.
3. If the problem persists, contact support with the log folder above.

File not found on startup
~~~~~~~~~~~~~~~~~~~~~~~~~

Pyre remembers the last STOS path in settings. If a drive is unmounted, Pyre starts
with an empty workspace and shows a warning. Use **File → Open STOS** to load data
from an available path.

Slow performance
~~~~~~~~~~~~~~~~

Close other memory-intensive applications. For very large images, use lower-resolution
copies for alignment when possible.

Developer install
-----------------

Contributors and advanced users should follow :doc:`../development/pyre_development`
for editable monorepo installs, debugging, and building the Windows installer locally.

See also
--------

* User changelog: :doc:`pyre_changelog`
* How to drive the UI: :doc:`../guides/pyre_use`
* Machine requirements: :doc:`../host_requirements`
* Package overview: :doc:`other_packages`
* Full manual: https://nornir.github.io/
