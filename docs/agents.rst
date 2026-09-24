Agents and contributors
=======================

This page is the public map of the umbrella checkout. Coding standards stay in the repository's ``.cursor/rules`` and ``AGENTS.md``; they are not copied here.

Layout
------

The repository root is an umbrella. Each ``nornir-*`` package (and ``dm4``) is a git submodule. A commit in the parent records a submodule pointer. It does not contain the package's file changes until that pointer is updated. Commit inside the package, then commit the pointer in the umbrella.

Narrative documentation lives in ``docs/`` and is published to https://nornir.github.io/. Do not edit the ``nornir.github.io`` repository by hand. See :doc:`development/publishing_documentation`.

Install
-------

Host UI work uses Python 3.13+ and ``venv/pyre314``. Editable install order, with ``--no-deps`` so git URL pins do not replace the local trees, is in :doc:`development/pyre_development`.

Docker images are Python 3.14, headless, and do not include Pyre. The Dev Container is :doc:`docker/cursor_dev`. The self-hosted worker is :doc:`docker/cursor_worker`.

Logging and tests
-----------------

Call ``nornir_shared.misc.SetupLogging``. Persistent files use ``NORNIR_LOG_ROOT``. Workers log through the parent queue listener. Details: :doc:`development/logging`.

Plotting tests need ``NORNIR_HEADLESS=1``. Headless figure output goes under the test output directory, not the repository root.

Where the code lives
--------------------

* Pipelines and ``nornir-build`` arguments: ``nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml``. A grouped list is :doc:`pipelines`.
* Registration math: ``nornir-imageregistration``. Phase correlation, grid refine (``local_distortion_correction``), and the blob filter (``blob_filter``) are the modules behind mosaic and slice-to-slice stages. The generated API page documents the package entry points, not every submodule.
* Pools: ``nornir-pools``. Which function to call is in :doc:`performance/pools`.
* Volume XML model and the controller that reads registered regions: ``nornir-volumemodel``, ``nornir-volumecontroller``.
