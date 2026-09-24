Developer notes
===============

This repository is an **umbrella** checkout that contains multiple ``nornir-*`` packages side by side. Contributor setup, editable installs, and test conventions are in :doc:`agents`.

* **Monodoc:** https://nornir.github.io/ — full documentation and API reference.
* **Publishing:** :doc:`development/publishing_documentation` describes how HTML is built and deployed to the ``nornir.github.io`` site.

When adding features, prefer updating the **monodoc** (reStructuredText under ``docs/``) and keep package ``README.md`` files short—overview plus links to this site.

Grid-refine and blob parity audits (C++ tools versus the Python ports) are listed under :doc:`development/index`.
