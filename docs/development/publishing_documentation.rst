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
    pip install -e nornir-pools --no-deps
    pip install "six>=1.16" "numpy>=1.26" "matplotlib>=3.8"
    pip install -e nornir-imageregistration --no-deps
    pip install "scipy>=1.11" "Pillow>=10.2" "pydantic>=2.9.2" "scikit-image>=0.25.1" "hypothesis>=6.96"
    pip install -e nornir-buildmanager --no-deps
    pip install "validators>=0.23" "python-dotenv>=1.0.1"

   ``--no-deps`` keeps git URL pins in ``pyproject.toml`` from replacing the local trees.

#. Build HTML::

    sphinx-build -b html docs docs/_build/html

#. Open ``docs/_build/html/index.html`` in a browser to preview.

Continuous integration
----------------------

The workflow **``.github/workflows/docs.yml``** in this monorepo:

* Runs on pushes to ``main`` / ``master`` (and on pull requests for a **build-only** check).
  Manual **workflow_dispatch** on those branches also builds and deploys.
* Checks out **git submodules** (required for editable ``nornir-*`` installs).
* Installs ``docs/requirements.txt`` and the same editable packages as above.
* Runs ``sphinx-build -b html docs docs/_build/html``.
* On **push** or **workflow_dispatch** to the default branch, deploys the contents of
  ``docs/_build/html`` to the external repository **``nornir/nornir.github.io``**
  on branch **``master``** (the branch GitHub Pages serves; option A: push built HTML).

See the workflow file for the exact triggers and action versions.

Deploy credentials (Option A)
-----------------------------

Pushing from this repo into **another** repository requires a token or deploy key with write access to ``nornir/nornir.github.io``. The workflow uses **peaceiris/actions-gh-pages** with:

* **Secret (placeholder name):** ``NORNIR_GITHUB_IO_DEPLOY_TOKEN`` — a fine-grained or classic PAT with ``contents: write`` on ``nornir/nornir.github.io``, stored in this monorepo’s **Settings → Secrets and variables → Actions**.

Without that secret, the HTML **build** can succeed while **Publish to nornir.github.io** fails with ``not found deploy key or tokens``.

Version banner
--------------

Release lines such as **|version|** in Sphinx come from the monorepo **``VERSION``** file at the repository root (see ``docs/conf.py``). Update that file when bumping the umbrella release shown in the doc banner.
