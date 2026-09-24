Release process
===============

This page covers how to cut a new Nornir monorepo release: bumping versions, updating the bill
of materials, tagging, and building OCI-labelled Docker images.

Source files
------------

``VERSION`` (monorepo root)
    Single line containing the current **monorepo release id** in semver form (e.g. ``1.7.0``).
    This file drives:

    - The Sphinx ``version`` / ``release`` fields used in this documentation.
    - The ``NORNIR_RELEASE`` build-arg passed to Docker images.
    - Git release tags (``v<VERSION>``).

``release/package-versions.yaml``
    Bill of materials (BOM).  Maps each distribution name to the version shipped in the current
    monorepo release, plus the package's subdirectory and whether it is included in headless
    Docker images.  Example entry:

    .. code-block:: yaml

        packages:
          nornir_shared:
            version: "1.5.3"
            path: nornir-shared
            docker: true
          pyre:
            version: "1.5.2"
            path: nornir-pyre
            docker: false

``release/verify_package_versions.py``
    Reads ``package-versions.yaml``, reads each package's ``pyproject.toml`` (and ``dm4``'s
    ``__version__``), and exits non-zero on any mismatch.  Run from the repo root::

        pip install pyyaml   # one-time
        python release/verify_package_versions.py

Release checklist
-----------------

1. Bump individual package versions in their ``pyproject.toml`` files (or ``dm4/dm4/__init__.py``).
2. Update ``release/package-versions.yaml`` so every ``version`` matches the tree.
3. Bump ``VERSION`` when you are creating a new **monorepo** release (not every package bump
   requires a monorepo version change — only when you intend to tag).
4. Run the verify script::

       python release/verify_package_versions.py

5. Commit all version changes.
6. Tag: ``git tag v$(cat VERSION)`` and push the tag.
7. Build and publish Docker images (see below).

Docker images and OCI labels
-----------------------------

Build using ``nornir-docker/docker-build.ps1`` (PowerShell) or ``build.cmd`` (cmd) from the
``nornir-docker/`` directory.  These scripts read ``VERSION``, run ``git rev-parse HEAD``,
record the UTC build time, and embed a base64-encoded JSON BOM into the image as an OCI label.

Images declare the following `OCI annotations <https://github.com/opencontainers/image-spec/blob/main/annotations.md>`_:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Label key
     - Source
   * - ``org.opencontainers.image.version``
     - ``VERSION`` file
   * - ``org.opencontainers.image.revision``
     - ``git rev-parse HEAD``
   * - ``org.opencontainers.image.source``
     - Repository URL
   * - ``org.opencontainers.image.created``
     - UTC build time (RFC 3339)
   * - ``org.nornir.variant``
     - ``dev`` / ``prod`` / ``prod-cupy``
   * - ``org.nornir.package_versions.json.base64``
     - Base64-encoded JSON of docker-included packages

Inspect labels::

    docker image inspect nornir:dev --format '{{json .Config.Labels}}'

Decode the BOM (PowerShell)::

    $b64 = (docker image inspect nornir:dev --format '{{index .Config.Labels "org.nornir.package_versions.json.base64"}}')
    [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))

Sphinx documentation version
-----------------------------

The monodoc reads ``VERSION`` at build time (in ``docs/conf.py``) and sets the Sphinx
``version`` and ``release`` fields.  A single live site is published — there are no
separate versioned URL trees.  When you bump ``VERSION`` and the CI workflow runs, the
published documentation banner automatically reflects the new version.

.. seealso::

   :doc:`publishing_documentation` — how the docs CI workflow builds and deploys to ``nornir.github.io``.
   :doc:`../docker/images` — Docker image catalogue and build options.
   :doc:`pyre_development` — Pyre Windows installer build (PyInstaller + Inno Setup); CI workflow ``pyre-windows-release.yml`` runs on ``pyre-*`` / ``v*`` tags and ``workflow_dispatch``.

Pyre Windows installer
----------------------

Pyre ships a native Windows installer (``Pyre-<version>-Setup.exe``), not a Docker image.
Docs always link the **latest** build as |pyre-windows-installer-latest|
(:doc:`../packages/pyre_install`). Version history stays on ``pyre-*`` GitHub Releases.

Release automation (``.github/workflows/pyre-windows-release.yml`` or
``release/publish_pyre_windows_release.ps1``):

1. Builds the frozen bundle and Inno Setup installer from ``nornir-pyre/pyproject.toml``.
2. Publishes GitHub Release ``pyre-<version>`` with both ``Pyre-<version>-Setup.exe`` and
   ``Pyre-Setup.exe``, marks it **latest**, and fills the release body from
   ``nornir-pyre/CHANGELOG.user.md``.
3. Regenerates :doc:`../packages/pyre_changelog` and triggers the Documentation workflow.

The installer filename and ``AppVersion`` come from ``nornir-pyre/pyproject.toml``
(via ``packaging/windows/build-installer.ps1``), not from the monorepo root ``VERSION``
file. Keep ``release/package-versions.yaml``'s ``pyre`` entry in sync with that
``pyproject.toml`` (``setup.py`` reads the same file and must not hardcode a version).

Maintainers: see the **Windows packaging and release** section in :doc:`pyre_development`.
End users: :doc:`../packages/pyre_install`.
