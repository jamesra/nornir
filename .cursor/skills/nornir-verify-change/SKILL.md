---
name: nornir-verify-change
description: >-
  Verify a change before claiming it is done: canonical headless pytest command
  (host and container), per-package targets, when TESTINPUTPATH matters, known
  flaky/baseline failures and how to tell them from new ones without stashing,
  ruff/pyright delta on touched files. Use before reporting a fix, before
  committing, and when a test fails and you need to know whether you caused it.
---

# Verify a change before claiming done

Implements [Questions-and-proving-fixes](../../rules/Questions-and-proving-fixes.mdc) and
[Shared-checkout-safety](../../rules/Shared-checkout-safety.mdc). Plot artifacts:
[nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md).

## 1. Run the tests

From the umbrella root, always with a path (bare `pytest` collects every testpath).

Windows host (PowerShell 7):

```powershell
$env:NORNIR_HEADLESS = '1'; $env:PYTHONIOENCODING = 'utf-8'
venv\pyre314\Scripts\pytest.exe <pkg>/tests/<file-or-dir> -m "not graphical and not slow and not gpu and not needs_data" -q -rfE
```

Container (`cursor-dev`; repo at `/workspace`, venv `/opt/venv`, `NORNIR_HEADLESS=1`,
`TESTINPUTPATH=/nornir-testdata` and `TESTOUTPUTPATH=/tmp/nornir-test-output` are already set):

```bash
cd /workspace
/opt/venv/bin/python -m pytest <pkg>/tests/<file-or-dir> -m "not graphical and not slow and not gpu and not needs_data" -q -rfE
```

Long output goes to `TESTOUTPUTPATH` or scratch (`*> "$env:TESTOUTPUTPATH\verify\run.txt"`), never
the repo root. Narrow with `::Class::test` or `-k`, not a new command shape.

Config (check the `rootdir:` / `configfile:` header line):

- Paths under `nornir-imageregistration/` or `nornir-shared/` alone use that submodule's
  `pyproject.toml` (`rootdir` = submodule). Everything else, including mixed-package runs, uses the
  umbrella `pytest.ini` (`--import-mode=importlib`, the `pythonpath` list, root `conftest.py`).
- Only `slow` is attached to tests (imageregistration). `graphical`, `gpu`, `needs_data` are declared
  but unattached, so the filter does **not** skip data-dependent tests. Keep it; it tightens as marks land.

| Package | Target | Notes |
|---------|--------|-------|
| nornir-buildmanager | `nornir-buildmanager/tests/...` | Test package is named `tests`. Segmentation training suites: `tests/operations/test_segtrain_*.py`, `test_segmentationtraining*.py` (~1200 tests, ~3 min). `tests/pipeline/**` builds volumes and needs `TESTINPUTPATH`. |
| nornir-imageregistration | `nornir-imageregistration/tests/...` | Package-root `conftest.py` defaults `NORNIR_HEADLESS=1`, reseeds padding noise, and fails the session on leaked pool workers. |
| nornir-pyre | `nornir-pyre/tests/...` | ~835 tests, ~2.5 min. `conftest.py` skips `*_qt.py`, `test_enum*.py`, `test_qopengl.py`, and `test_pure_units.py` without PyQt6. |
| nornir-pools | `nornir-pools/tests/` | 180 s per-test timeout (POSIX only). |
| nornir-shared | `nornir-shared/tests/...` | Own `pyproject.toml`: `--continue-on-collection-errors`. |
| nornir-volumecontroller | `nornir-volumecontroller` | In umbrella testpaths. |
| dm4, nornir-web, nornir-builddashboard, nornir-volumemodel | explicit path only | Not in umbrella testpaths (Django / fastapi deps). |

Changing `nornir-shared`, `nornir-pools` or `nornir-imageregistration`: also run the A-class list in
`.github/workflows/unit-tests.yml` ("Run A-class unit tests") with an empty `TESTINPUTPATH`, as CI does.

### When TESTINPUTPATH matters

- Host `TESTINPUTPATH=D:\nornir-testdata`, `TESTOUTPUTPATH=C:\Temp\Nornir`; container
  `/nornir-testdata` (read-only). Layout: `TEST_DATA_SETUP.md` (its commands predate the `test/` to
  `tests/` rename; use the ones above).
- Needed by tests reading `Images/`, `PlatformRaw/`, `Transforms/`, `VolumeMetaData/`: buildmanager
  `tests/pipeline/**` and importers, the imageregistration B-class list in `unit-tests.yml`,
  `nornir-shared/tests/test_images.py`.
- With it empty these **fail** with `FileNotFoundError` rather than skip (125, per `pytest.ini`).
  That is an environment gap, not a regression; check `Test-Path $env:TESTINPUTPATH\<subdir>` first.

## 2. Known flaky and baseline failures

Measured 2026-10-26, Windows host, `TESTINPUTPATH` set. Known = same test id **and** same error text
(identical assertion values). Update the table when one is fixed or a new one confirmed.

| Test id | Kind | Symptom | Status |
|---------|------|---------|--------|
| `nornir-pyre/tests/test_stos_file_browser_async_scan.py::TestStosFileBrowserAsyncScan::test_startup_selects_last_session_mid_list_file` | flaky | `[WinError 145] The directory is not empty` during temp dir cleanup, under machine load | passed 2026-10-26 |
| `nornir-pyre/tests/test_stos_file_browser_navigation.py::TestStosFileBrowserNavigation::test_rescan_picks_up_new_files_and_keeps_selection` | flaky | same WinError 145 cleanup; passes on re-run | passed 2026-10-26 |
| `nornir-pyre/tests/test_control_point_registration_queue.py::TestRegistrationApply::test_cupy_submits_thread_pool_worker` | order-dependent | fails in the full pyre suite, passes alone | passed 2026-10-26 |
| `nornir-pyre/tests/test_masked_grid_relax.py::TestControlPointMaskSkip::test_spacebar_mixed_selection_registers_unmasked_only` | order-dependent | fails in the full pyre suite, passes in its own file | passed 2026-10-26 |
| `nornir-pyre/tests/test_shaders_qt.py`, `nornir-pyre/tests/test_vao_shaders_qt.py` | collection error | `ImportError: cannot import name 'TransformShaderQt'` / `'PointSetShaderQt'` from `pyre.gl_engine.shaders` | only when named explicitly or by a shell glob; directory runs skip them. Do not pass them. |
| `nornir-buildmanager/tests/pipeline/operations/test_BlockOperations.py::SliceToSliceRegistrationSkipBrute::testRefineSectionAlignment` | baseline (needs data) | `AssertionError: '4589c2b8b2f1e4ed7e7be84aa3ef9789' != '0ac883bd6faaa744b443a514d8a0dcb5'`; log: `... cannot generate downsample 16 image` for sections 0005/0006 (test notes section 7 input is missing) | fails 2026-10-26 |
| `nornir-imageregistration/tests/test_TileToTileAlignment.py::TestBasicTileAlignment::test_MismatchSizeAlignments` | flaky | `X dimension incorrect: <value> != -94` outside the 1.0 delta; the value changes between runs (-95.44, -92.46) | failed twice 2026-10-26 |
| `nornir-imageregistration/tests/test_TileToTileAlignment.py::TestBasicTileAlignment::test_alignment_cmp` | baseline (env) | `Unable to load image: D:Data\miniRCx1\...`: hard-coded `os.path.join("D:", "Data", ...)` | fails 2026-10-26 |
| `nornir-imageregistration/tests/test_TileToTileAlignment.py::TestMosaicTilesetTileOffsets::test_Alignment_RC3_0001` | baseline (data) | `FileNotFoundError: ...\Transforms\TestMosaicTilesetTileOffsets\RC3\...\mosaic_tileset.pickle` | fails 2026-10-26 |
| `nornir-buildmanager/tests/importers/test_recover_notes.py::TestTryAddNotesRoundTrip::test_notes_text_round_trips_to_file_and_xml` | flaky (Hypothesis) | `AssertionError: False is not true` at `TryAddNotes`, e.g. `notes_text='0\n'`; `setUp` runs once per method, so examples share one source dir and a repeated text is "unchanged". Seeds 1 and 5 fail, 2-4 pass, identically on `HEAD` | fails identically on HEAD 2026-10-30 |
| buildmanager segmentation training suites | formerly baseline | 26 failures (`plan_section_crops()` unexpected kwarg `'pad'`, `StitchJob` `tile_x`, `export_section_crops` drift) | **fixed**: 1223 passed, 0 failed 2026-10-26. Any failure there is now new. |

`nornir-imageregistration/tests/transforms` (cited as carrying known failures in the improve-loop
gates) passed in full on 2026-10-26.

### Baseline or mine?

1. Re-run it alone once. Passes alone: flaky or order-dependent; record it, don't blame the change.
2. Same test id and error text as the table: known.
3. Otherwise run it on pre-change code in a detached worktree under scratch (**never `git stash`**),
   with `python -m pytest` from inside it so its package shadows the venv's editable install:

   ```powershell
   $wt = "$env:TESTOUTPUTPATH\wt-nornir-pyre"
   git -C nornir-pyre worktree add --detach $wt HEAD
   Push-Location $wt; $env:NORNIR_HEADLESS = '1'
   D:\src\git\nornir\venv\pyre314\Scripts\python.exe -c "import pyre; print(pyre.__file__)"   # must be under $wt
   D:\src\git\nornir\venv\pyre314\Scripts\python.exe -m pytest tests/test_x.py::Cls::test_y -q -rfE
   Pop-Location
   git -C nornir-pyre worktree remove --force $wt
   ```

   A new regression test: copy it into `$wt` first; it must fail there. Other nornir packages still
   import from the main checkout (right when only one repo changed). For one file,
   `git -C <repo> show HEAD:<path> > <scratch>\<file>` is enough to diff or inspect.
4. Fails identically at `HEAD`: baseline (report "fails identically on HEAD"). Passes at `HEAD` but
   fails with the change: yours.

## 3. Lint and type delta, touched files only

- No ruff config is checked in; venv ruff 0.17 runs its broad default set (`BLE001`, `S110`,
  `SIM114`, ...), so most files carry old findings (`pyre/controllers/transformcontroller.py`: 28).
  Never ruff a whole package or fix unrelated findings; report only new ones.
- Pyright uses the umbrella `pyrightconfig.json` (basic) only when run from the umbrella root. Exit 1
  means it reported errors, not a tool failure.
- `ruff` and `pyright` are not in the dev container image; run them on the Windows host, in PowerShell 7
  or bash (5.1 re-encodes pipes and writes `>` as UTF-16).

**Touched files:** `git -C <repo> diff --name-only HEAD -- '*.py'` plus
`git -C <repo> ls-files --others --exclude-standard -- '*.py'`; keep only files you changed (others'
edits show up too).

**Ruff delta** (matches on rule and message, not line numbers, which shift):

```powershell
$ruff = 'venv\pyre314\Scripts\ruff.exe'
$repo = 'nornir-pyre'; $files = @('pyre/controllers/transformcontroller.py')   # relative to $repo
function RuffDiag { $input | ConvertFrom-Json | ForEach-Object { "$($_.code) $($_.message)" } }
foreach ($f in $files) {
    $head = git -C $repo show "HEAD:$f" 2>$null | & $ruff check --output-format json --stdin-filename "$repo/$f" - | RuffDiag
    $now  = & $ruff check --output-format json "$repo/$f" | RuffDiag
    "== $repo/$f  HEAD=$(@($head).Count) now=$(@($now).Count)"
    Compare-Object @($head | Where-Object { $_ }) @($now | Where-Object { $_ }) |
        Where-Object SideIndicator -eq '=>' | ForEach-Object { "  NEW $($_.InputObject)" }
}
```

A file new since `HEAD` gets `HEAD=0` (every finding is new). Locate NEW lines with
`ruff check --output-format concise <file>`. Bash (prints only new findings):

```bash
strip() { grep -E ':[0-9]+:[0-9]+: ' | sed -E 's/^[^ ]*:[0-9]+:[0-9]+: //' | sort; }
diff <(git -C nornir-pyre show HEAD:$f | ruff check --output-format concise --stdin-filename nornir-pyre/$f - | strip) \
     <(ruff check --output-format concise nornir-pyre/$f | strip) | grep '^>'
```

**Pyright delta.** Output to `TESTOUTPUTPATH` or scratch, never the repo root (~25 old
`pyright_*.json` dumps sit there; add none, ask before deleting). Check **both** sides as scratch
copies: a copy outside its package can't resolve relative imports, so scratch `HEAD` vs the in-tree
file reports false NEW errors (3 on an unchanged `transformcontroller.py`).

```powershell
$out = Join-Path $env:TESTOUTPUTPATH 'verify-pyright'; New-Item -ItemType Directory -Force $out | Out-Null
function PyrightDiag($json) { (Get-Content $json -Raw | ConvertFrom-Json).generalDiagnostics |
    ForEach-Object { "$($_.severity) $($_.rule): $($_.message.Split("`n")[0])" } }
foreach ($f in $files) {
    $n = $f -replace '[/\\]', '_'
    git -C $repo show "HEAD:$f" > "$out\head_$n"
    Copy-Item "$repo/$f" "$out\now_$n"
    foreach ($side in 'head', 'now') { venv\pyre314\Scripts\pyright.exe --outputjson "$out\${side}_$n" > "$out\${side}_$n.json" }
    "== $repo/$f  HEAD=$(@(PyrightDiag "$out\head_$n.json").Count) now=$(@(PyrightDiag "$out\now_$n.json").Count)"
    Compare-Object @(PyrightDiag "$out\head_$n.json") @(PyrightDiag "$out\now_$n.json") |
        Where-Object SideIndicator -eq '=>' | ForEach-Object { "  NEW $($_.InputObject)" }
}
```

Relatively imported names are unknown on both sides, hiding errors on them. When the change touches
such names, run pyright (from the umbrella root) on `<repo>/<path>` and on the same path in a detached
`HEAD` worktree (section 2, step 3), where relative imports resolve.

Report as "ruff 28 -> 28, pyright 0 -> 0 on touched files, no new diagnostics", or list the new ones.

## 4. Before claiming fixed

- [ ] Original failure reproduced on unchanged code (test, script or log line); command kept.
- [ ] Same command passes with the change; a new regression test fails on a `HEAD` worktree
      ("N of N fail on old code").
- [ ] Covering tests run with the canonical command; each failure is known (table) or baseline
      (fails identically on `HEAD`).
- [ ] No new ruff or pyright diagnostics on touched files.
- [ ] UI, interactivity, performance: measured number before and after (ms per drag, s per control
      point, peak RSS). Headless plots triaged; a non-empty `fail/` overrides a green pytest.
- [ ] Anything not runnable here (GUI, GPU, real data, live service) stated with exact steps for the
      user; not called "fixed".
- [ ] `git -C <repo> diff --stat` shows only intended lines (no whole-file rewrite:
      [Line-endings-and-encoding](../../rules/Line-endings-and-encoding.mdc)); nothing new of yours in
      the repo root (`git status --short`).
