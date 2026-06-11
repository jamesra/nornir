# Grid690 Python Refine-Grid Parity — Change Log

Summary of work aligning Python `RefineGridMosaic` with legacy C++ `ir-refine-grid` for
RC2_4Square_Assembled section 0690 (Grid690 / IDocBuildTest).

See also: [refine-grid-cpp-parity-checklist.md](refine-grid-cpp-parity-checklist.md) for the
C++→Python audit mapping.

## Package: `nornir-imageregistration`

### Core algorithm (`local_distortion_correction.py`)

- Replaced overlap-subcell incremental delta model with C++ mesh-vertex update architecture:
  - Per-pass full-tile prewarp (`_prewarp_tile_for_grid_refine`)
  - Per-mesh-vertex phase correlation against each overlapping neighbor (`_measure_grid_vertex_displacements`)
  - Legacy regularization pipeline (`_regularize_displacements`: median r=1, gap-fill, Gaussian σ=1.0)
  - `1/(1+mass)` shift blending and direct `TargetPoints` updates
  - Dual convergence stop (threshold **or** no improvement vs prior pass)
- `min_overlap` default for mosaic refine path set to **0.25** (per-cell valid-area gate, matching C++)
- Removed `estimate_cutoff` gating from mosaic refine hot path (retained for STOS refine)
- Skip final lattice resample when transforms are already on the output grid
- Refinement cells use direct equal-size FFT (no random-noise padding) for deterministic parity
- Added vertex measurement diagnostics per pass

### Supporting modules

- `transforms/gridtransform.py`: bulk `UpdateTargetPointsByIndex` support
- `transforms/factory.py`, `mosaic_tileset.py`, `__init__.py`: export/API wiring
- `assemble_tiles.py`: assemble buffer size guard (`NORNIR_MAX_ASSEMBLE_BUFFER_BYTES`) for exploded target bounds
- `phasecorrelation.py`: guard flat correlation normalization (divide-by-zero)

### Tests and fixtures

- `tests/grid_seam_metrics.py` — seam MAE, golden target-point delta, chained-pass helpers
  - `REFINE_MAX_PASSES = 10`, `GOLDEN_TARGET_DELTA_MAX = 2.0 px`
  - `REFINE_DISPLACEMENT_THRESHOLD = 0.2` (test calibration; golden mosaic filename uses Thr0.5)
  - Chained passes stop when displacement ≤ threshold (matches C++ breaking after a converged pass)
  - Golden comparison removes global translation gauge before per-tile deltas
- `tests/grid690_diagnostics.py` — headless PNG/JSON diagnostics for functional tests
- `tests/test_refine_grid_690_functional.py` — RC2 Grid690 end-to-end functional suite
- `tests/test_refine_grid_legacy_parity.py` — optional exe parity (skipped without `NORNIR_LEGACY_IR_REFINE_GRID`)
- `tests/test_local_distortion.py` — `TestMosaicGridRefinementApi` unit coverage

### Validation (RC2 fixture)

| Metric | Result |
|--------|--------|
| Functional tests | 3/3 pass |
| Mean target delta vs golden (gauge-removed) | ~1.79 px (gate 2.0) |
| Mean seam MAE (1 pass, thr 0.2) | ~0.096 (golden ~0.091) |
| Worst vertical seam pair | `015-397` (~0.125 MAE) vs horizontal pairs ~0.065 |

## Package: umbrella `docs/`

- `refine-grid-cpp-parity-checklist.md` — Phase 0 C++ audit deliverable

## Other Nornir packages

No Grid690-specific code changes were made in `nornir-buildmanager`, `nornir-shared`,
`nornir-pools`, `nornir-pyre`, `nornir-web`, `nornir-docker`, `nornir-volumecontroller`,
or `nornir-volumemodel`. Submodule working trees may show line-ending noise unrelated to this work.

**Excluded:** `dm4` (per request).

## Known follow-ups (Bugbot / review)

| Severity | Location | Finding |
|----------|----------|---------|
| High | `assemble.py` prewarp interpolation | `_TransformImageUsingCoords` uses cubic (`order=3`) sampling; legacy prewarp may expect nearest-neighbor — review for full FFT-cell parity |
| Medium | `tests/grid_seam_metrics.py` | Chained single-iteration passes reset `last_average` each call; cross-pass “no improvement” stop only applies inside one `RefineGridMosaic` invocation |
| High | `assemble.py` `TransformStos` | Image warp call commented out — verify STOS path if touched in same branch |
