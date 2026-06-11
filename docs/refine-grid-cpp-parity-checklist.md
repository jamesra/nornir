# ir-refine-grid C++ → Python Parity Checklist

Audit of the legacy C++ `ir-refine-grid` tool (SCI trunk, mounted at `/legacycode`)
mapped against the Python `RefineGridMosaic` implementation in
`nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py`.

Golden reference output:
`RC2_4Square_Assembled/TEM/0690/TEM/Grid_Cel96_Mes8_sp4_Mes8_Thr0.5.mosaic`
(parameters: `-cell 96 -mesh 8 8 -sp 4 -displacement_threshold 0.5`, `-it` default 10).

## 1. CLI and initialization (`/legacycode/code/ir-tools/ir-refine-grid.cxx`)

| # | C++ behavior (file:line) | Python equivalent | Parity |
|---|--------------------------|-------------------|--------|
| 1.1 | Defaults: `iterations = 10`, `displacement_threshold = 1.0` (ir-refine-grid.cxx L219, L224) | `RefineGridMosaic(iterations=10, displacement_threshold=...)` | OK |
| 1.2 | `cell`/`mesh` auto formulas: `cell = max(3*dim/(mesh-1))`, `mesh = 1 + 3*dim/cell` (L402–420) | `_resolve_mesh_shape_and_cell_size` | OK |
| 1.3 | Tiles loaded via `std_tile` with `shrink_factor` and `pixel_spacing`; all math runs at working resolution (`sp 4` → 1/4 scale) | `imageScale = 1/sp`; warps run at `target_space_scale = imageScale` | OK (shifts must be converted back to full-res before mesh update) |
| 1.4 | `setup_grid_transform(transform_, mesh_rows-1, mesh_cols-1, tile_min, tile_max, mask, tbase, ...)` (L443–453): per-tile grid transform whose vertex `uv_` lattice spans the tile and `xy_` holds mosaic positions | `_initialize_tile_grid_transforms` → `ConvertTransformToGridTransform(grid_dims=mesh_shape)`; `SourcePoints` = lattice, `TargetPoints` = mosaic positions | OK |
| 1.5 | `refine_mosaic_mt(..., cell_size, prewarp=true, min_overlap=0.25, median_radius=1, iterations, keep_first_tile_fixed=false, displacement_threshold, threads)` (L479–491) | `RefineGridMosaic` must hardcode `prewarp` semantics, `min_overlap=0.25` per-cell, `median_radius=1` | **Port** (Python previously used overlap-fraction min_overlap and no median filter) |

Vertex index ordering matches: C++ `i = col + row*mesh_cols` (col fastest); Python
`build_coords_array` produces `index = row*grid_dims[1] + col` (col fastest).

## 2. Pass structure (`refine_mosaic_mt`, mosaic_refinement_common.hxx L1440–1803)

| # | C++ behavior | Python target | Parity |
|---|--------------|---------------|--------|
| 2.1 | Neighbors = all tiles whose mosaic-space bboxes intersect (L1511–1531); recomputed once before the pass loop | per-pass neighbor list from `FixedBoundingBox` intersection | **Port** |
| 2.2 | Each pass: re-warp every tile in full into mosaic space using current grid transform (`prewarp_tiles`, L1573–1596) | `_prewarp_tile_for_grid_refine` per tile per pass | **Port** (Python previously warped overlap ROIs only) |
| 2.3 | Per tile i, per neighbor j: `calc_displacements(fixed=warped[j], moving=warped[i], forward_1=transform[i], cell, 0.25, median_radius=1)` accumulating shared `mass` across neighbors (L1366–1398) | `_measure_grid_vertex_displacements` per neighbor; regularize per neighbor; `mass` accumulates | **Port** |
| 2.4 | Blend: `shift[i][k] = sum_j shift_j[k]`, then `scale = 1/(1+mass[k])`, `shift[i][k] *= scale` (L1400–1419; `keep_first_tile_fixed=false`) | identical blend; replaces Python `SplitDisplacements` d/2 convention (single-neighbor special case of `1/(1+mass)`) | **Port** |
| 2.5 | Apply only after all tiles measured: `gt.grid_.update(&shift[i][0])` → `v.xy_ += shift` for every vertex, then `transform[i]->setup(gt)` (L1705–1710; the_grid_transform.cxx L315–327) | buffer per-tile shifts; `UpdateTargetPointsByIndex(arange(N), TargetPoints + shift)` after all tiles measured | **Port** |
| 2.6 | Convergence metric: `avg = mean(|sx| + |sy|)` over all vertices of all tiles, `count += 2` per vertex, computed from the **applied (post-scale) shifts** in working-resolution pixels (L1775–1789) | same metric in working-res units | **Port** |
| 2.7 | Dual early stop: `if (avg <= threshold) break; else if (avg >= last_average) break;` (L1793–1801) | both conditions | **Port** (Python only had threshold) |
| 2.8 | No final lattice resample — the grid IS the transform; mosaic saved from updated grid | skip final `ConvertTransformToGridTransform` when transform already on output lattice | **Port** |

## 3. Measurement loop (`calc_displacements`, mosaic_refinement_common.hxx L224–395)

| # | C++ behavior | Python target | Parity |
|---|--------------|---------------|--------|
| 3.1 | Loops over **all** `mesh_size` grid vertices of the moving tile, not overlap FFT subcells (L317) | per-vertex loop over `grid.TargetPoints` | **Port** |
| 3.2 | Mosaic-space measurement center: `gt.transform_inv(vertex.uv_, center)` (L324). At a vertex's own uv this evaluates to the vertex mosaic position `v.xy_` — i.e. the vertex **TargetPoint** | `center = TargetPoints[k]` (scaled by `imageScale` to index warped images) | **Port** (replaces inverse-warp of FFT-cell centers) |
| 3.3 | `dx`, `dy`, `db` mesh-lattice images; unmeasured vertices = 0 (L288–301, L330–332) | `(rows, cols)` float arrays | **Port** |
| 3.4 | Prewarped path: `refine_one_point_fft(tile_0=warped[j], tile_1=warped[i], center, min_overlap, ...)` (L338–354) | extract aligned cells from the two prewarped images | **Port** |
| 3.5 | On success: `dx=shift[0]`, `dy=shift[1]`, `db=1` (L388–390) | same | **Port** |
| 3.6 | Ends with `regularize_displacements(xy_shift, mass, dx, dy, db, median_radius)` (L394) | `_regularize_displacements` | **Port** |

## 4. FFT cell preprocessing (`grid_common.hxx` / `fft_common.cxx`)

C++ chain for the prewarped path:
`refine_one_point_fft` (grid_common.hxx L1257) → `refine_one_point_helper`
(neighborhood extraction) → `refine_one_point_fft` (L820) → `match_one_pair`
(L269) → `find_correlation` (fft_common.cxx L467) → `estimate_displacement`.

| # | C++ behavior | Python (`_phase_correlate_refinement_cell` / `find_offset`) | Parity |
|---|--------------|--------------------------------------------------------------|--------|
| 4.1 | Neighborhood: `sz = cell × cell` window in mosaic space, `origin = center - cell/2` sampled on the common mosaic grid for **both** tiles (grid_common.hxx L632–673) — cells are pre-aligned in mosaic space | cells sliced from both prewarped images at the same mosaic window | **Port** |
| 4.2 | Pixels outside the image buffer or mask → value 0, mask 0 (L651–655, L667–671); **no random-noise fill** | zero-fill outside valid region | Accepted difference: Python keeps its validated random-noise fill for invalid pixels (avoids zero-edge correlation bias); area-ratio gate below limits exposure |
| 4.3 | Per-cell area gate: `area[k]/cell²  >= min_overlap (0.25)` for **both** cells, else no measurement (L675–685) | identical fraction test on valid masks | **Port** |
| 4.4 | Skip if center not inside the fixed tile's buffer (L616–621) | skip if scaled center outside fixed warped image extent | **Port** |
| 4.5 | FFT: pad both to common size (equal already → no-op), low-pass filter `r=0.5, s=0.1` on each spectrum, Girod-Kuo normalized cross-power spectrum (phase correlation) with `eps=1e-8`, second low-pass `r*0.8` on P, ifft → PDF (fft_common.cxx L480–558) | `find_offset(..., fft_required=True)` phase correlation; Python applies its own normalization/padding | Accepted difference: Python translate-path estimator (validated vs `ir-translate`) stands in for Girod-Kuo + lp-filter chain |
| 4.6 | Peak handling: `find_maxima_cm(percentage=0.9995)`, `reject_negligible_maxima(2.0)`, fail if `num_peaks > 10`; consider zero-displacement; evaluate 4 wrap-around permutations of each peak with masked mean-square `my_metric`, require overlap ratio in `[0.25, 1.0]` (grid_common.hxx L296–372) | Python `find_offset` resolves wrap-around internally with overlap constraints `min_overlap=0.25, max_overlap=1.0`; single-peak weight | Accepted difference; the `weight` is only used for diagnostics in the C++ model (no estimate_cutoff gating) |
| 4.7 | `shift = -translate->GetOffset()` = mosaic-space correction to move the **moving** tile content into alignment with the fixed neighbor (L885) | `record.peak` from `find_offset(fixed_cell, moving_cell)` = shift to apply to moving tile | OK (sign convention verified) |

## 5. Regularization (`regularize_displacements`, mosaic_refinement_common.cxx L36–171)

| # | C++ behavior | Python target | Parity |
|---|--------------|---------------|--------|
| 5.1 | Median filter on `dx`, `dy` with radius 1 (3×3 kernel, ITK MedianImageFilter, zero-flux Neumann = replicate edges); `db` NOT filtered (L55–60) | `scipy.ndimage.median_filter(size=3, mode='nearest')` | **Port** |
| 5.2 | Gap fill for vertices with `db==0`: sample ring of radius 1 (the loop's `max_r = min(1, ...)` caps the "expanding" radius at exactly 1), average measured neighbors from the median-filtered `dx/dy`, write into blurred copies, set `db_blurred=1` if any sample found (L62–149). Ring sampling uses the C++ offset pattern (left col offset +1 down, bottom row offset +1 right) | faithful port including the radius-1 cap and offset pattern | **Port** |
| 5.3 | Gaussian blur on the entire `dx/dy` fields: ITK DiscreteGaussianImageFilter with `SetVariance(sigma²)`, `sigma=1.0`, `UseImageSpacing=false`, `MaximumError=0.1` (common.hxx L1166–1189; cxx L152–153). Applied to measured vertices too. `db` NOT blurred | `scipy.ndimage.gaussian_filter(sigma=1.0, mode='nearest', truncate≈2.5)` | **Port** |
| 5.4 | Output: `xy_shift[i] = (dx, dy)` for every vertex; `mass[i] += db[i]` where `db ∈ {0, 1}` after gap fill (L160–170) | per-vertex `(dy, dx)` shifts + measured flag | **Port** |
| 5.5 | NOT `estimate_cutoff`: the C++ pipeline has no weight-percentile gating | remove `_filter_weighted_point_pair_updates` from the mosaic refine path (keep for STOS refine) | **Port** |

## 6. Removed/retired Python behaviors (mosaic refine path)

- Overlap-subcell FFT measurement grid (`grid_dim × subregion_shape` cells over the
  padded overlap ROI) — replaced by per-mesh-vertex measurement (3.1/3.2).
- `SplitDisplacements` d/2 convention — replaced by `1/(1+mass)` blending (2.4).
- `_filter_weighted_point_pair_updates` (`estimate_cutoff`) — no C++ equivalent (5.5).
- `_merge_weighted_point_pairs` / `_apply_point_pair_updates_to_grid_transform`
  nearest-node incremental deltas — replaced by full-mesh vertex update (2.5).
- Final `_resample_transform_to_output_grid` in `RefineGridMosaic` — C++ never
  resamples; tiles are already on the output lattice after pass 0 (2.8).

These functions remain available for unit tests and the STOS refine path.

## 7. Coordinate/unit conventions

| Quantity | C++ | Python |
|----------|-----|--------|
| Axis order | `(x, y)` | `(y, x)` = `(row, col)` |
| Mesh vertex source lattice | `vertex.uv_` (normalized tile space) | `grid.SourcePoints` (full-res source pixels) |
| Mesh vertex mosaic position | `vertex.xy_` (working-res mosaic space) | `grid.TargetPoints` (full-res mosaic space) |
| Measured shift | working-res mosaic pixels | scaled peak → divide by `imageScale` before adding to `TargetPoints` |
| Convergence `avg` | working-res pixels | working-res pixels (compute before unit conversion) |
| `displacement_threshold` | working-res pixels (golden run: 0.5) | same units |
