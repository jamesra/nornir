---
name: nornir-headless-unit-tests
description: >-
  Requires NORNIR_HEADLESS=1 for Nornir plotting-related unit tests; headless
  matplotlib PNGs from library helpers go under _plot_artifacts beneath
  TEST_OUTPUT_DIR or TESTOUTPUTPATH when set; clear that folder once per pytest
  session; triage into pass/ and fail/ after review using test source and figure
  titles; treat fail/ as overriding a green pytest for the agent’s verdict. Use
  when running pytest for nornir-imageregistration, debugging matplotlib or view
  code, CI or agent test runs, or headless plot outputs.
---

# Headless unit tests and plot artifacts

## Set `NORNIR_HEADLESS=1` for unit test runs

- `nornir_imageregistration` selects the matplotlib backend at **import time** (`Agg` when headless, `qtAgg` otherwise). Running tests without headless can open GUI windows, break in CI, or desynchronize behavior from CI and Docker (where `NORNIR_HEADLESS=1` is already set).
- For **`nornir-imageregistration` pytest**, `nornir-imageregistration/conftest.py` (at the package root, not under `tests/`) calls `os.environ.setdefault("NORNIR_HEADLESS", "1")` so the default is headless **when that conftest loads**. Still **set `NORNIR_HEADLESS=1` explicitly** when:
  - Running tests from another working directory or without collecting `conftest.py` as expected,
  - Spawning subprocesses or tools that import `nornir_imageregistration` before pytest sets the env,
  - Documenting or scripting test commands so behavior does not depend on import order.

**Interactive debugging only:** `NORNIR_HEADLESS=0 pytest ...` (see `nornir-imageregistration/conftest.py`).

## Where PNGs are written

- **`save_figure_to_png_artifact`** / **`artifact_png_path`** (see `nornir_imageregistration/headless.py`) write under **`<test_output_root>/_plot_artifacts`**, where **`test_output_root`** is **`TEST_OUTPUT_DIR`** if set, otherwise **`TESTOUTPUTPATH`** (the env used by `nornir-imageregistration/tests/setup_imagetest.py` and CI). If neither is set, the directory is the **system temp** folder.
- Tests often save figures explicitly under **`TestOutputPath`** (`TESTOUTPUTPATH` plus class/method segments); those paths are independent of `_plot_artifacts`. The same **review and triage** workflow applies wherever the test or helper wrote the image.

Implementation reference: `nornir_imageregistration/headless.py` (`is_headless`, `artifact_png_path`, `save_figure_to_png_artifact`, `inspect_png_output`).

## Artifact directory hygiene

- **Clear** the headless plot directory **`<test_output_root>/_plot_artifacts`** (including `pass/` and `fail/` if they exist) **once immediately before** a **test session** (one `pytest` invocation), so stale PNGs do not confuse review. When only system temp is in use, skip wholesale clears of temp; triage or review files selectively instead.
- **Do not** clear `_plot_artifacts` **before each test** or between tests—only that single pre-session clear when using a stable test output root.
- Until the repo adds a session-scoped pytest hook, treat this as **agent/human procedure** when preparing a run.

## Triage: `pass/` and `fail/` subfolders

After tests complete and PNGs exist, **move or copy** each reviewed image into:

- **`pass/`** — visual outcome matches the test’s stated intent (a **visual pass**).
- **`fail/`** — wrong, misleading, or regressed relative to intent (a **visual fail**).

Create `pass/` and `fail/` **under** `_plot_artifacts` (or next to the images you are triaging) as needed. This is **not** the same as pytest’s pass/fail: a test can exit 0 while a plot still belongs in **`fail/`** after visual review (and the converse can occur when debugging).

Correlate filenames with code paths using the `tag=` argument to `save_figure_to_png_artifact` in `headless.py`. Subfolders are for **post-run organization**; the library does not require them for writing files.

## Visual verdict vs pytest

### What pytest can and cannot see

- Pytest’s exit code reflects **in-process** assertions only. **Moving PNGs after the run** does not change pytest’s exit code.
- In headless mode, **`ShowWithPassFail`** saves a PNG and **returns `True` without waiting** (`nornir_imageregistration/views/__init__.py`). Tests that require a real Fail button are **skipped** when headless (e.g. `test/views/test_showgrayscale.py` uses `@unittest.skipIf(is_headless(), ...)`).

### Agent rule (post-run triage)

1. Run tests; review artifacts **after** the run (or after each logical batch).
2. Triage into **`pass/`** / **`fail/`** using test source, figure title, and image content (see below).
3. For the **agent’s overall assessment**, treat **any file in `fail/`** as a **failure**, **even if pytest exited 0**. A future **wrapper script** could fail the job if `fail/` is non-empty; that is optional tooling, not required here.

## How to judge intent: test source + figure title

- Read the **unit test** (body, **comments**, and setup) to learn what behavior is being exercised, then open the **saved PNG** and compare.
- Use **informational text in the plot title** (`Axes.set_title`, `pyplot.title`, `Figure.suptitle`, etc.) as **on-canvas documentation**: it should **align** with what you see and with the test’s purpose. Example: descriptive `set_title` strings in `nornir-imageregistration/tests/transforms/test_metrics.py`.
- **`inspect_png_output`** checks structural validity (file exists, readable PNG, dimensions); **semantic/visual** correctness still requires comparing the image to intent and title.

## Pass/fail is not only “pytest exited 0”

Many headless paths **save figures to PNG** instead of showing a window. Success includes:

1. **Automated checks** — Tests may call `inspect_png_output(path)` (or helpers that call it) to assert the file exists, has non-trivial size, and is a readable PNG with valid dimensions.
2. **Visual analysis** — Open and review generated PNGs (or use image-aware inspection). A valid but wrong plot can still satisfy structural checks; **treat disk-rendered images as primary evidence** when judging correctness.

**Agent workflow:** (1) Clear **`_plot_artifacts`** under the active test output root **once** before the session when `TEST_OUTPUT_DIR` or `TESTOUTPUTPATH` is set (see above). (2) Run tests. (3) List or glob artifact paths; read images and correlate `tag=` / paths with code under test. (4) Move or copy reviewed images into **`pass/`** or **`fail/`** using test + title + visual judgment. (5) For the final verdict, **non-empty `fail/` overrides a green pytest** (see “Agent rule” above).

## Quick command pattern

```bash
NORNIR_HEADLESS=1 pytest path/to/tests
```

On Windows (cmd): `set NORNIR_HEADLESS=1 && pytest ...`  
On Windows (PowerShell): `$env:NORNIR_HEADLESS='1'; pytest ...`
