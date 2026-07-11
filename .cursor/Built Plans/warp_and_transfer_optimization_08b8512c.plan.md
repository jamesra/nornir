---
name: Warp and transfer optimization
overview: Cut the now-dominant prewarp GPU cost by eliminating the redundant coverage (ones-image) warp and deriving the validity mask from the existing scatter indices, plus remove per-cell device-host syncs in the batched vertex path. Golden-parity and benchmark gated; no default behavior change beyond the speedup.
todos:
  - id: warp-mask-return
    content: Add opt-in return_valid_mask to _TransformImageUsingCoords (scatter-derived bool mask; handle empty/early returns); default False keeps callers unchanged
    status: completed
  - id: prewarp-drop-coverage
    content: Use return_valid_mask in _prewarp_tile_for_grid_refine; remove ones-image coverage warp, its allocation, coverage>0.999, and the now-redundant xp.where
    status: completed
  - id: batch-validity
    content: Batch the cell-validity reduction in _measure_grid_vertex_displacements_batched to remove per-cell count_nonzero D2H syncs (single batched count + one .get())
    status: completed
  - id: parity-bench
    content: Golden parity (verify_cpu_vs_batched + compare_refine_peakfinder) and benchmark (microbench --batched --phase-timing) to confirm no output change and quantify prewarp drop / cells/s
    status: completed
  - id: doc-decide
    content: Document before/after + transfer audit in mosaic_refine_grid_gpu_assessment.md; record go/no-go on GPU-native InverseTransform follow-up
    status: completed
isProject: false
---

## Goal

Reduce the prewarp bucket (2.04s, ~75% of GPU refine time) and trim residual host/device syncs, to push the batched-GPU path clearly past CPU. Every change is golden-parity gated against the C++ mosaic; no registration-output change is acceptable.

## Findings recap (from this investigation)

- `_prewarp_tile_for_grid_refine` ([local_distortion_correction.py](nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py):422) warps each tile twice/pass: the image and a `ones`-image for the validity mask.
- In `_TransformImageUsingCoords` ([assemble.py](nornir-imageregistration/nornir_imageregistration/assemble.py):374-385), `order=0` output is `cval` everywhere except a scatter at `target_coords_flat`. So `coverage > 0.999` == "pixel is in `target_coords_flat`" — derivable for free.
- Per-cell `float(xp.count_nonzero(valid_region))` ([local_distortion_correction.py](nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py):623) is a D2H scalar sync per cell, not removed by batching.
- Per-pass CPU `InverseTransform` round-trip (D2H grid -> SciPy -> H2D coords) is real but high-effort; deferred.

## Step 1 - Return validity mask from the warp (no second warp)

Add an opt-in `return_valid_mask: bool = False` to `_TransformImageUsingCoords` ([assemble.py](nornir-imageregistration/nornir_imageregistration/assemble.py):242). When set (and not `return_shared_memory`), also return a bool array of `output_area` that is True exactly at `target_coords_flat`:

- Build it next to the existing scatter (lines 371-385): `valid = xp.zeros(prod(output_area), bool); valid[target_coords_flat] = True; valid.reshape(output_area)`.
- Handle the early/empty returns (lines 288-291, 316-327) by returning an all-False mask of `output_area`.
- Default `False` keeps every existing caller unchanged. The mask equals the old `coverage>0.999` for `order=0` (prewarp's case).

## Step 2 - Drop the coverage warp in prewarp

In `_prewarp_tile_for_grid_refine` ([local_distortion_correction.py](nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py):464-494):
- Call the image warp with `return_valid_mask=True`, take `(warped_image, valid_mask)`.
- Delete the `coverage_source = xp.ones(...)` allocation, the second `_TransformImageUsingCoords`, and the `coverage > 0.999` line.
- The `xp.where(valid_mask, warped_image, 0)` becomes a no-op for `order=0` (non-scattered pixels are already `cval=0`); drop it. This halves `map_coordinates` calls and removes one full-tile allocation per tile per pass.

## Step 3 - Batch the cell-validity reduction (cut per-cell syncs)

In `_measure_grid_vertex_displacements_batched` ([local_distortion_correction.py](nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py):689): currently each `_extract_refinement_cell` call does its own `count_nonzero` sync. Restructure so the per-vertex loop only does the cheap host-side center-in-buffer check and the device slice, collecting cells + valid sub-regions; then compute all valid fractions in one batched `xp.count_nonzero(stack, axis=(1,2))` with a single `.get()`, and apply the `cell_min_overlap` filter on host. Keep the serial path as-is. (Add a small variant of `_extract_refinement_cell` that returns the cell + valid-region without the scalar sync, or returns the cell and defers the count.)

## Step 4 - Parity + benchmark gate

- Golden parity: rerun `scripts/verify_cpu_vs_batched.py` and `scripts/compare_refine_peakfinder.py`; require CPU-vs-batched mean <= 1.0 px / max <= 3.0 px and batched-vs-golden <= 2.2 px, seam MAE < 35 (same gates as before; expect numbers essentially unchanged since `order=0` semantics are preserved).
- Benchmark: `scripts/microbench_mosaic_refine.py --backend cupy --batched --phase-timing` to quantify the new prewarp bucket and cells/s vs the 80.7 baseline and CPU ~89.

## Step 5 - Document + decide on the CPU-inverse-transform trip

Append a "Warp + transfer optimization" section to [docs/mosaic_refine_grid_gpu_assessment.md](nornir-imageregistration/docs/mosaic_refine_grid_gpu_assessment.md): before/after phase split, cells/s, parity numbers, and the explicit host/device transfer audit. Record a go/no-go on the larger follow-up (GPU-native grid `InverseTransform` to remove the per-pass coord D2H/H2D round-trip), which is out of scope here due to its size/risk.

## Out of scope (this phase)

GPU-native `InverseTransform` / grid-transform residency; region-limited warping (mesh cells tile most of the tile, so the win is marginal); any STOS wiring. No change to the NumPy default path semantics.