Pyre development
================

Pyre (``nornir-pyre``) is the PyQt6 / OpenGL desktop application for interactive
image registration in the Nornir umbrella. This page covers local development,
testing, and building the Windows installer.

Monorepo layout
---------------

Prefer an **umbrella checkout** of the Nornir monorepo so sibling packages resolve
from local trees. Pyre depends on:

* ``nornir-shared``
* ``nornir-pools``
* ``nornir-imageregistration`` (CPU-only for UI work; optional ``[gpu]`` extra)
* ``nornir-buildmanager``

Pyre is **not** shipped in Docker images (``docker: false`` in
``release/package-versions.yaml``). Use a host virtual environment for UI development.

Local development environment
-----------------------------

Prerequisites
~~~~~~~~~~~~~

* Python **3.13+**
* Windows, Linux, or macOS host with OpenGL
* Monorepo checkout with submodules initialized

Recommended venv (this machine): ``venv/pyre314`` — see :doc:`../developer_notes`.

Editable install (BOM order)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install siblings with ``--no-deps`` so git URL pins in ``pyproject.toml`` do not
override local sources (same pattern as :doc:`../docker/cursor_dev`):

.. code-block:: powershell

   python -m venv venv\pyre314
   venv\pyre314\Scripts\activate
   pip install -e nornir-shared
   pip install -e nornir-pools --no-deps
   pip install -e nornir-imageregistration --no-deps
   pip install scipy Pillow pydantic scikit-image hypothesis
   pip install -e nornir-buildmanager --no-deps
   pip install validators python-dotenv
   pip install -e nornir-pyre --no-deps
   pip install PyQt6 PyOpenGL matplotlib rtree PyYAML dependency-injector six

Or use ``nornir-pyre/requirements-qt.txt`` as a baseline after editable siblings
are installed.

Run and debug
~~~~~~~~~~~~~

.. code-block:: powershell

   pyre
   python -m pyre
   python -m pyre -stos D:\data\section.stos

VS Code launch configurations live in ``.vscode/launch.json`` at the monorepo root.

Settings and logs
~~~~~~~~~~~~~~~~~

+---------------------------+-----------------------------------------------+
| Dev build                 | Frozen Windows install                        |
+===========================+===============================================+
| ``pyre/settings.json``    | ``%APPDATA%\Nornir\Pyre\settings.json``     |
| (package tree, dev)       | (user-writable)                               |
+---------------------------+-----------------------------------------------+
| ``NORNIR_LOG_ROOT`` env   | Defaults to                                   |
| or cwd fallback           | ``%LOCALAPPDATA%\Nornir\Pyre\logs``           |
+---------------------------+-----------------------------------------------+

Set ``NORNIR_LOG_ROOT`` in development to follow the unified logging convention
(:doc:`logging`).

Testing
~~~~~~~

From ``nornir-pyre/``:

.. code-block:: powershell

   pytest

Graphical tests use ``@pytest.mark.graphical`` and require a display. Headless CI
uses ``NORNIR_HEADLESS=1`` where applicable (see imageregistration headless test
conventions).

GPU (optional)
~~~~~~~~~~~~~~

UI development does not require CuPy. For GPU-backed registration:

.. code-block:: powershell

   pip install -e "nornir-imageregistration[gpu]" --no-deps

Windows packaging and release
-----------------------------

End users install ``Pyre-<version>-Setup.exe`` from GitHub Releases
(:doc:`../packages/pyre_install`). Maintainers build it from
``nornir-pyre/packaging/windows/``.

Prerequisites
~~~~~~~~~~~~~

* Windows 10/11 x64
* Python 3.13+
* Inno Setup 6
* Monorepo checkout at the release tag
* Submodules initialized

Build steps
~~~~~~~~~~~

From a terminal::

   cd nornir-pyre\packaging\windows
   .\build-freeze.ps1
   .\validate-frozen.ps1
   .\build-installer.ps1

Or from VS Code / Cursor: **Terminal → Run Task…** and choose one of:

* ``pyre: freeze bundle``
* ``pyre: validate frozen bundle``
* ``pyre: build installer``
* ``pyre: build Windows installer (full)`` — runs all three in sequence

Tasks are defined in ``.vscode/tasks.json``. Use **launch.json** for debugging
``pyre`` or pytest, not for packaging scripts.

Output:

* Frozen bundle: ``dist/pyre/pyre.exe`` (one-folder layout)
* Installer: ``dist/installer/Pyre-<version>-Setup.exe``

``build-freeze.ps1`` generates ``release/pyre-windows-constraints.txt`` (local
``file://`` URLs from ``release/package-versions.yaml``), installs CPU-only
monorepo packages, and runs PyInstaller via ``pyre.spec``.

PyInstaller notes
~~~~~~~~~~~~~~~~~

* Entry point: ``pyre.__main__:main`` (console script ``pyre``)
* ``console=False`` (GUI)
* Collects PyQt6 plugins, SciPy, scikit-image, and Nornir packages
* Excludes ``cupy`` / ``cupyx`` from the default bundle
* Package data: ``pyre/resources/*.png``, bundled ``README.rst``

Debugging frozen builds
~~~~~~~~~~~~~~~~~~~~~~~

* ``sys.frozen`` is set by PyInstaller; ``pyre.frozen_paths`` centralizes AppData paths.
* Missing modules: add hidden imports in ``pyre.spec`` or ``hook-pyre.py``.
* Smoke test without GUI: ``pyre.exe --smoke-test``

CI and releases
~~~~~~~~~~~~~~~

On push of a ``v*`` tag, ``.github/workflows/pyre-windows-release.yml``:

1. Verifies ``release/package-versions.yaml``
2. Runs ``build-freeze.ps1`` and ``validate-frozen.ps1``
3. Compiles Inno Setup
4. Uploads ``Pyre-<version>-Setup.exe`` to the GitHub Release

See :doc:`release` for the full monorepo release checklist.

Optional: Authenticode-sign the installer to reduce SmartScreen warnings.

VM validation checklist
~~~~~~~~~~~~~~~~~~~~~~~

Before declaring a release ready, test on a **clean Windows VM** (no Python/Git):

1. Install ``Pyre-<version>-Setup.exe``
2. Launch from Start Menu; confirm the main window opens
3. Open a sample STOS or mosaic from test fixtures
4. Confirm logs under ``%LOCALAPPDATA%\Nornir\Pyre\logs``
5. Uninstall from Settings → Apps

See also
--------

* End-user install: :doc:`../packages/pyre_install`
* Packaging cheat sheet: ``nornir-pyre/packaging/windows/README.md``
* Release process: :doc:`release`
