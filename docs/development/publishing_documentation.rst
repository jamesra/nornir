Publishing the documentation
=============================

This page is the canonical description of how the Nornir **monodoc** is built and how it reaches **https://nornir.github.io/**.

Local build
-----------

#. Use **Python 3.13+** (aligned with current ``nornir-*`` packages).
#. Create or activate a virtual environment.
#. Install Sphinx dependencies and editable packages (from the monorepo root)::

    pip install -r docs/requirements.txt
    pip install -e nornir-shared
    pip install -e nornir-pools
    pip install -e nornir-imageregistration
    pip install -e nornir-buildmanager

   If dependency resolution pulls remote Git URLs instead of your local trees, install the four packages in that order and adjust pins as needed for your branch.

#. Build HTML::

    sphinx-build -b html docs docs/_build/html

#. Open ``docs/_build/html/index.html`` in a browser to preview.

Continuous integration
----------------------

The workflow **``.github/workflows/docs.yml``** in this monorepo:

* Runs on pushes to ``main`` / ``master`` (and on pull requests for a **build-only** check).
* Installs ``docs/requirements.txt`` and the same editable packages as above.
* Runs ``sphinx-build -b html docs docs/_build/html``.
* On **push** to the default branch, deploys the contents of ``docs/_build/html`` to the external repository **``nornir/nornir.github.io``** (option A: push built HTML).

See the workflow file for the exact triggers and action versions.

Deploy credentials (Option A)
-----------------------------

Pushing from this repo into **another** repository requires a token or deploy key with write access to ``nornir/nornir.github.io``. The workflow uses **peaceiris/actions-gh-pages** with:

* **Secret (placeholder name):** ``NORNIR_GITHUB_IO_DEPLOY_TOKEN`` — a fine-grained or classic PAT with ``contents: write`` on ``nornir/nornir.github.io``, stored in this monorepo’s **Settings → Secrets and variables → Actions**.

**Do not** commit real tokens into the repository. If the secret is missing, the build job may still succeed while the deploy step fails—add the secret or disable the deploy step for forks.

Version banner
--------------

Release lines such as **|version|** in Sphinx come from the monorepo **``VERSION``** file at the repository root (see ``docs/conf.py``). Update that file when bumping the umbrella release shown in the doc banner.
