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

`nornir_imageregistration` selects the matplotlib backend at **import time** (`Agg` when headless, `qtAgg` otherwise). Without headless, tests can open GUI windows, break in CI, or diverge from CI and Docker (where `NORNIR_HEADLESS=1` is already set).

`nornir-imageregistration/conftest.py` (package root, not `tests/`) calls `os.environ.setdefault("NORNIR_HEADLESS", "1")`, but only when that conftest loads. Still set `NORNIR_HEADLESS=1` explicitly when:

- running from another working directory or without collecting `conftest.py` as expected;
- spawning subprocesses or tools that import `nornir_imageregistration` before pytest sets the env;
- documenting or scripting test commands, so behavior does not depend on import order.

Interactive debugging only: `NORNIR_HEADLESS=0 pytest ...` (see `nornir-imageregistration/conftest.py`).

```bash
NORNIR_HEADLESS=1 pytest path/to/tests
```

On Windows (cmd): `set NORNIR_HEADLESS=1 && pytest ...`  
On Windows (PowerShell): `$env:NORNIR_HEADLESS='1'; pytest ...`

## Where PNGs are written

- `save_figure_to_png_artifact` / `artifact_png_path` write under `<test_output_root>/_plot_artifacts`, where `test_output_root` is `TEST_OUTPUT_DIR` if set, else `TESTOUTPUTPATH` (used by `nornir-imageregistration/tests/setup_imagetest.py` and CI), else the system temp folder.
- Tests often save figures under `TestOutputPath` (`TESTOUTPUTPATH` plus class/method segments), independent of `_plot_artifacts`. The same review and triage applies wherever the image was written.
- Map filenames to code via the `tag=` argument of `save_figure_to_png_artifact`.

Implementation: `nornir_imageregistration/headless.py` (`is_headless`, `artifact_png_path`, `save_figure_to_png_artifact`, `inspect_png_output`).

## What pytest cannot see

- Pytest's exit code reflects in-process assertions only; moving PNGs after the run does not change it.
- Headless, `ShowWithPassFail` saves a PNG and returns `True` without waiting (`nornir_imageregistration/views/__init__.py`). Tests needing a real Fail button are skipped (e.g. `nornir-imageregistration/tests/views/test_showgrayscale.py`, `@unittest.skipIf(is_headless(), ...)`).
- `inspect_png_output(path)` checks structure only (file exists, non-trivial size, readable PNG, valid dimensions). A valid but wrong plot passes it, so **treat disk-rendered images as primary evidence**.

## Agent workflow

1. **Once, immediately before** the session (one `pytest` invocation), clear `<test_output_root>/_plot_artifacts` including `pass/` and `fail/`, when `TEST_OUTPUT_DIR` or `TESTOUTPUTPATH` is set. Never clear before each test or between tests. If only system temp is in use, do not wholesale-clear temp; review files selectively. (Manual procedure until the repo adds a session-scoped pytest hook.)
2. Run tests.
3. After the run (or each logical batch), list the artifacts, open each (or use image-aware inspection) and judge it against intent:
   - read the test body, comments and setup for the behavior exercised;
   - read the plot title (`Axes.set_title`, `pyplot.title`, `Figure.suptitle`, etc.) as on-canvas documentation; it should match the image and the test's purpose (e.g. `nornir-imageregistration/tests/transforms/test_metrics.py`).
4. Move or copy each reviewed image into `pass/` (matches intent) or `fail/` (wrong, misleading or regressed), created under `_plot_artifacts` or next to the images. The library does not need these folders to write files. Visual pass/fail is independent of pytest's: a test can exit 0 with a plot in `fail/` (and the converse when debugging).
5. Verdict: **any file in `fail/` is a failure, even if pytest exited 0.** (A wrapper that fails the job on non-empty `fail/` is optional future tooling.)

## A session that leaks child processes fails

`nornir-imageregistration/conftest.py` closes pools at session end, then kills and reports any surviving descendant of the pytest process and fails the run. Leaked pool workers used to outlive pytest, accumulate across runs and contend for the GPU invisibly, giving plausible but wrong timings (one measurement on review #213 was off by two orders of magnitude). See review #217.

- The count is **OS processes, not logical workers**: a venv `Scripts/python.exe` is a launcher that spawns the real interpreter, so one leaked child appears twice.
- `POOL TEARDOWN: pool shutdown did not finish within 60s` means teardown hung, not a leak: `wait_completion` busy-spins while a task is registered active (#221). The hook bounds it on a daemon thread so it reports instead of wedging the session.
- `NORNIR_ALLOW_LEAKED_WORKERS=1` downgrades it to a printed warning. Use it when a leak is expected, not to silence a surprise.

**Before blaming the library:** on Windows `multiprocessing` uses spawn, so a script run directly (`python myscript.py`) that creates a pool outside an `if __name__ == '__main__':` guard has every worker re-execute the script and build its own pool. That recursive explosion gives exactly the "dozens of orphaned interpreters under one parent" signature, is the most likely cause of a sudden process pile-up, and is a script bug, not a `nornir_pools` bug. A wrapper using `runpy.run_path(..., run_name='__main__')` is safe even unguarded: runpy replaces `sys.modules['__main__']` with the guarded target before any pool is created.
