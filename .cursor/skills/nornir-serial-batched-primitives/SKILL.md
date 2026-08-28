---
name: nornir-serial-batched-primitives
description: >-
  Phase correlation and serial+batched registration math: grep callers, keep
  serial/batched mirrors aligned, run the verification matrix, final perf on
  ≥100-tile sections. Use when editing phasecorrelation, batched_phase_correlation,
  stos_brute, arrange_mosaic, local_distortion_correction, or related scripts/tests.
---

# Serial + batched primitives

Paired rule: [`.cursor/rules/Serial-batched-primitives.mdc`](../../rules/Serial-batched-primitives.mdc).

## Before merge

1. **Grep callers** of any changed primitive (serial and batched entry points).
2. **Keep serial/batched mirrors aligned** — same gates, tolerances, and semantics unless an intentional divergence is documented in this skill.
3. **Run the verification matrix** below for affected pathways.
4. **Final performance sign-off** must use a **real section with ≥100 tiles** (default: RPC3 0195 per `.vscode/launch.json`), with downsample and refine parameters matching launch configs — **not** the grid refine input section fixture (4 tiles).

## Script / test inventory

Maintain these tables in the **same commit** when adding, removing, or renaming a script or pytest module that benchmarks, profiles, compares, verifies, or gates phase correlation / serial+batched registration behavior.

### Scripts (by pathway)

| Pathway | Scripts (update as inventory changes) |
|---------|----------------------------------------|
| Phase correlation | `nornir-imageregistration/scripts/microbench*.py`, `compare*.py`, `verify*.py`, `audit*.py` (incl. opt-in `audit_cupy_item_bench.py`), `tabulate*.py`, `run_*investigation*.sh` |
| STOS / refine | Scripts and launch configs that exercise `stos_brute` / refine under `nornir-imageregistration/scripts/`; `python -m nornir_imageregistration.stos_registration_debug` |
| Mosaic arrange | Scripts touching `arrange_mosaic` |

### Pytest modules

| Area | Test modules (glob / names) |
|------|----------------------------|
| Align / phase | `tests/test_*Align*.py`, `tests/test_*phase*.py`, `tests/test_find_peak_memory.py`, `tests/test_find_peak_inplace_ratio_parity.py`, `tests/test_peak_uniqueness.py` |
| STOS / refine | `tests/test_*stos*.py` (incl. `test_stos_registration_debug.py`), `tests/test_*refine*.py` |
| RBF / transform composition | `tests/test_rbf_singular_recovery.py`, `tests/transforms/test_addition.py`, `tests/transforms/test_rbf_precompute_and_duplicates.py` |
| Arrange / masks | `tests/test_arrange.py`, `tests/test_overlapmasking.py` |

### Verification matrix (minimum)

| Change touches | Minimum checks |
|----------------|----------------|
| `phasecorrelation` / `batched_phase_correlation` | Unit tests for affected APIs; serial vs batched parity on a small fixture; microbench or compare script if perf-sensitive |
| `stos_brute` / refine shared | Relevant `test_*stos*` / `test_*refine*`; ≥100-tile section for final perf sign-off |
| `arrange_mosaic` / overlap masking | `test_arrange` / `test_overlapmasking` as applicable |
| RBF weight solve / degeneracy recovery | `tests/test_rbf_singular_recovery.py`; `tests/transforms` as a whole (CPU **and** `_GPUComponent` mirrors must change together) |
| New script or gate | Add row here; run it once before merge |

### Known gaps

| Gap | Notes |
|-----|--------|
| `tests/transforms` has 18 pre-existing failures | `test_AlignmentRecord`, `test_linear_nd_cupy_fallback`, `test_metrics`, `test_points_to_linear_fit`. Same count with and without local changes; compare against a stashed baseline rather than expecting green |
| GPU (`_GPUComponent`) RBF recovery is untested | `_is_singular_matrix_error` is shared by both mirrors, but the CuPy branch needs a CUDA host to exercise |
| `TestBasicTileAlignment` flakes in combined runs | Running `-k "Align or phase or peak or overlapmask"` rotates one or two extra failures per run (`test_Alignments`, `test_MismatchSizeAlignments`, `test_best_angle_ranking_parity`), with and without local changes. The same modules run alone are stable. Judge a diff by running the file alone, or by comparing failure *sets* across repeated runs on both trees — a single combined run is not a reliable signal |
| `find_peak` uniqueness must be measured pre-threshold | `allow_in_place=True` used to apply the cutoff to the caller's surface, which erased the competing peaks the ratio depends on and returned the "nothing competes" sentinel. `batched_find_peak` never thresholds and was already correct. Any future thresholding change must keep the surface readable for `masked_peak_ratio`, and parity must be asserted on `peak_ratio`, not just offset and strength |

## Same-commit sync

If this change adds/removes/renames inventory-affecting scripts or tests, update **this file** in the same commit (tables + matrix + known gaps).
