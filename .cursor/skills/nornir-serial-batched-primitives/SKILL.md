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
| Align / phase | `tests/test_*Align*.py`, `tests/test_*phase*.py`, `tests/test_find_peak_memory.py`, `tests/test_find_peak_inplace_ratio_parity.py`, `tests/test_peak_uniqueness.py`, `tests/test_batched_low_content_gate.py`, `tests/test_padding_noise_reproducible.py`, `tests/test_batched_centroid_window_wraps.py`, `tests/test_correlation_peak_ratio_characterization.py`, `tests/test_logpolar_scale_seed_saturation.py` |
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
| An import-time `matplotlib.use` can undo headless for the whole session | The combined matrix run used to wedge forever with no output and leak workers, while every file passed alone. Cause was not pool state: `nornir_buildmanager/build.py` ran `matplotlib.use('QtAgg')` at package import, overriding the `Agg` that `nornir_imageregistration` picks when headless. Pytest collection imports *every* test module regardless of `-k`, and two tests import `nornir_buildmanager`, so one import made the entire session GUI-backed; a later `plt.show()` then blocked on a Qt event loop waiting for a window nobody could close. Fixed in `build.py` (headless keeps Agg) and in `nornir_shared.plot.Histogram` (no `show()` when the caller passed `axes=`). When a run hangs with no output, arm `faulthandler.dump_traceback_later(N, exit=True)` from a tiny `-p` plugin re-armed per test — the stack names the culprit in one run. Check `matplotlib.get_backend()` per test before suspecting pools |
| GPU (`_GPUComponent`) RBF recovery is untested | `_is_singular_matrix_error` is shared by both mirrors, but the CuPy branch needs a CUDA host to exercise |
| `TestBasicTileAlignment` flakes in combined runs | Running `-k "Align or phase or peak or overlapmask"` rotates one or two extra failures per run (`test_Alignments`, `test_MismatchSizeAlignments`, `test_best_angle_ranking_parity`), with and without local changes. The same modules run alone are stable. Judge a diff by running the file alone, or by comparing failure *sets* across repeated runs on both trees — a single combined run is not a reliable signal |
| Batched cell gates must mirror `is_alignable_cell`, not just span | The batched gate checked only nonzero span and nonzero max, while serial also enforces a `NORNIR_REFINE_LOW_CONTENT_STD_MIN` std floor. Since each cell is normalized by its own span, a cell with std 3e-5 was amplified to full range and returned weight ~1.77 where serial returned 0. The batched call site in `local_distortion_correction` gates on overlap *coverage* only, so nothing upstream compensates. When adding a serial cell-validity rule, mirror it in `batched_find_offset` and assert on the reject/accept *decision*, not just on healthy-cell values |
| Contrast gates can use the range bound instead of a full reduction | For `n` samples with range `span`, std >= span / sqrt(2n). Real cells span most of their range, so comparing the already-computed span against `threshold * sqrt(2n)` normally clears the batch and the std reduction is skipped. A naive masked std cost 21% on `batched_find_offset`; the bound made it a wash. Any similar gate should reuse statistics the function already computes |
| A brute alignment fills noise **twice**, and seeding one source is worse than seeding neither | Padding fills the frame (`GenRandomData` via `pad_image_for_phase_correlation`); `rotate_image` fills the corners a rotation leaves empty (`ImageStats.GenerateNoise`). Both were on the unseeded legacy global RNG, so `np.random.seed(N)` covered both at once. Seeding only the padding left five identical calls flipping between two peaks (~3.51 and ~4.5) and broke `test_fixed_angle_fft_reuse`'s cached-vs-fresh equivalence in 286 of 300 seeds — it agreed 300/300 before. Both now share one generator via `nornir_imageregistration.random_generator`; reseed with `seed_random_data`, not `np.random.seed`, which no longer reaches either. If you add a third noise fill, route it through the same generator |
| The batched centroid window must **wrap**, but the centroid must **not** be re-wrapped | `batched_find_peak` refines the argmax over a `(2r+1)` window. Clamping the window's *centre* into bounds keeps the samples valid but slides the window off any peak within `r` of an edge, leaving the peak on the rim and dragging the centroid inward — border error up to 0.72px against known sub-pixel shifts, and it *grew* with radius (1.14px at r=3) since a wider window slides further. The correlation is circular (`ifft2` then `fftshift`), so wrapping is the true neighbourhood: 0.06px, and border peaks become as accurate as interior ones. Truncating instead only halves the error (0.58px), because baseline subtraction on fewer samples more often flattens to nothing. Two traps: weight the *relative* offsets and add the peak back, or a wrapped index drags the mean across the image; and do **not** re-wrap the centroid into `[0, dim)` afterwards — that flips the sign at the seam, turning a `+16.0` shift into `-15.86` on a 32px cell and breaking `test_matches_serial_measurement`. Serial `find_peak` does not wrap (connected-component COM splits a lobe at the seam); that divergence is inherent to the two algorithms. Pinned by `tests/test_batched_centroid_window_wraps.py`; issue #89 |
| `power_of_two=True` **replaces** `desired_shape`, so the 0°/+180° asymmetry in `_find_angle_and_scale_with_logpolar` is deliberate | `pad_and_rotate_image`'s `power_of_two` does not round `desired_shape` up; it discards it for `NearestPowerOfTwo(rotated_image.shape)`, which can be **smaller** than requested (a 64×64 source at 0° yields 64×64 even when 128×128 was asked for). The 0° call sets it; the +180° call must not, because by then the shape has been reconciled against `padded_target` via `max_shape`, and a source-only power of two undershoots it whenever the target drove the shared shape larger. Rotating by *t* and *t*+180 gives the same bounding box, so there is nothing for the flag to discover. Adding it produced 425 `ValueError`s from `fft_phase_correlation` over a 1600-case sweep of shapes and angles; leaving it off produced none. Pinned by `tests/test_stos_brute_rotate_180_shape.py`; reviewed as issue #86 and closed `wontfix` |
| Batched runs at the caller's precision, floored at float32 — do not reintroduce an upcast | `batched_image_phase_correlation` and `batched_find_offset` opened with an unconditional `xp.asarray(..., dtype=xp.float64)` while serial `image_phase_correlation` has always used the native dtype. Callers pass float32 (`local_distortion_correction` builds stacks from `fixed.image.dtype`), so every batch paid a conversion serial never made and carried complex128 transforms. Both backends honour single precision — `numpy.fft` and `cupy.fft` each return complex64 for float32 — so the upcast bought no transform accuracy, only workspace: measured **exactly 2x** device memory at every size (302 → 151 MB for 256 cells of 128px) and up to **3.4x** faster on GPU, 1.16x on CPU. Accuracy is unaffected: across ordinary texture, contrast down to 0.005, added noise, and 64–256px cells the integer peak choice was identical for every cell and the refined peak moved ≤ 6.1e-07 px, against a ~0.1px method error. Two traps: the `1.0` literal in the cross-power `where` must take the working dtype, or `denom` promotes the result back; and `offsets = xp.arange(-r, r+1)` is int64, so the centroid weighting needs a float view (`offsets.astype(images.dtype)`) while the index arithmetic keeps the integer one. `_FFT_PEAK_BYTES_PER_CELL_128` in `gpu_batch_budget` still assumes float64 and is now ~1.8x conservative — safe, but chunks are half the size they could be. Pinned by `tests/test_batched_correlation_dtype.py`; issue #92 |
| Anything derived from a **chunk** must not reach the output — crop and prefilter over the whole batch | `_sample_source_rois_batched` reduced the sample AABB over each chunk's own coordinates and cropped the source to it. With `order=3` the spline prefilter's boundary conditions depend on the extent it runs over, so a cell's values depended on which cells shared its chunk — up to 8e-02, ~8% of full intensity range, against a float32 epsilon near 1e-07. `chunk_cells` comes from a memory budget, so a tuning knob changed registration output. Chunking is a memory strategy and must be numerically invisible; when adding one, assert equality across several chunk sizes rather than only checking shapes. Fix: crop and `spline_filter` once over the union of all cells' samples, then sample each chunk with `prefilter=False` — scipy applies no prepadding for `mode='constant'` (`_prepad_for_spline_filter` returns `npad=0`), so that is bit-equivalent to what `map_coordinates` did internally. Get the union bounds from the four corners of each cell's sample grid, not the full coordinate set: the maps are affine, so a rectangle's image is a parallelogram whose extremes are its corners' images — exact, and `(n, 4, 2)` instead of the `(n, H*W, 2)` that forced the chunking. Production runs in one chunk (budget allows 7812 cells of 128px), where the union crop *is* the chunk crop, so values were byte-identical and `test_refine_grid_legacy_parity` reported the same mean delta to all 15 digits. Also 1.3–1.6x faster, since the prefilter runs once and a per-chunk four-scalar device sync disappears. Cost: the prefiltered array is held for the whole loop, so lowering the sample budget no longer shrinks it — bounded by the single-chunk peak. Pinned by `tests/test_batched_roi_coord_memory.py`; issue #211 |
| `find_peak` uniqueness must be measured pre-threshold | `allow_in_place=True` used to apply the cutoff to the caller's surface, which erased the competing peaks the ratio depends on and returned the "nothing competes" sentinel. `batched_find_peak` never thresholds and was already correct. Any future thresholding change must keep the surface readable for `masked_peak_ratio`, and parity must be asserted on `peak_ratio`, not just offset and strength |

## Same-commit sync

If this change adds/removes/renames inventory-affecting scripts or tests, update **this file** in the same commit (tables + matrix + known gaps).
