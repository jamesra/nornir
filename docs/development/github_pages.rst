GitHub Pages hosting
====================

The public documentation site **https://nornir.github.io/** is served by **GitHub Pages** from the GitHub repository named ``nornir.github.io`` under the **nornir** organization:

* Repository: ``https://github.com/nornir/nornir.github.io``

**What to verify (once per org/repo setup):**

#. In that repository, open **Settings → Pages** and confirm the published source is the ``master`` branch at the repository root. CI publishes built HTML to ``master`` (see :doc:`publishing_documentation`); it does not publish to ``main``.
#. Confirm you have permission to push to ``nornir/nornir.github.io`` or that a machine account / deploy key is configured for the workflow described in :doc:`publishing_documentation`.

The umbrella **source** documentation lives in this monorepo under ``docs/``; the ``nornir.github.io`` repository holds **built HTML** only (generated output), not hand-edited copies of the manuals.
