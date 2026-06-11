Developer notes
=================

This repository is an **umbrella** checkout that contains multiple ``nornir-*`` packages side by side. Typical development uses a dedicated virtual environment (see project ``.cursor/rules`` for the recommended path on this machine) and editable installs of the packages you are changing.

* **Monodoc:** https://nornir.github.io/ — full documentation and API reference.
* **Publishing:** :doc:`development/publishing_documentation` describes how HTML is built and deployed to the ``nornir.github.io`` site.

When adding features, prefer updating the **monodoc** (reStructuredText under ``docs/``) and keep package ``README.md`` files short—overview plus links to this site.

Grid refine parity (C++ ``ir-refine-grid`` vs Python ``RefineGridMosaic``):

* ``docs/refine-grid-cpp-parity-checklist.md`` — C++ audit mapping
* ``docs/refine-grid690-python-parity-changelog.md`` — implementation change log
