---
name: nornir-documentation
description: Build and deploy the umbrella Sphinx monodoc under docs/; align package READMEs with nornir.github.io.
---

# Nornir documentation

Use when editing **`docs/`**, changing GitHub Pages deploy, or adjusting package **`README.md`** / **`README.rst`** files that point at the public manual.

## Build locally

From the monorepo root (Python 3.13+ recommended):

```bash
pip install -r docs/requirements.txt
pip install -e nornir-shared
pip install -e nornir-pools --no-deps && pip install "six>=1.16" "numpy>=1.26" "matplotlib>=3.8"
pip install -e nornir-imageregistration --no-deps && pip install "scipy>=1.11" "Pillow>=10.2" "pydantic>=2.9.2" "scikit-image>=0.25.1" "hypothesis>=6.96"
pip install -e nornir-buildmanager --no-deps && pip install "validators>=0.23" "python-dotenv>=1.0.1"
sphinx-build -b html docs docs/_build/html
```

Open **`docs/_build/html/index.html`**. On Unix you can run **`make -C docs html`** if **`make`** is available.

## Where things live

- **Sources:** **`docs/`** (RST primary; **MyST** for `.md`).
- **Version banner:** repo-root **`VERSION`** (read in **`docs/conf.py`**).
- **CI:** **`.github/workflows/docs.yml`** — builds on PRs; on **`main`/`master`** push, deploys to **`nornir/nornir.github.io`** using secret **`NORNIR_GITHUB_IO_DEPLOY_TOKEN`**.
- **Human-facing publish instructions:** **`docs/development/publishing_documentation.rst`**.

## README vs monodoc

Keep package READMEs short: intro + links to **https://nornir.github.io/** and the relevant **packages/** and **api/** pages. Put depth in **`docs/`**, not in README duplicates.
