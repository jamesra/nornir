# CuPy host↔device audit — item outcomes

Loop: baseline common path → change → remeasure → keep / revert / gate.
High and medium only. GPU was ~46% busy (SliceToVolume) during benches; ratios still hold.

## Already decided (not re-run)

| ID | Pri | Outcome | Notes |
|----|-----|---------|-------|
| A1 | high | **Keep** | Lazy `IgnoreUnderflow`; `69722da` |
| A3 | high | **Keep** | Bool invalid mask; `df82248` |
| A4 | high | **Revert** | GPU grid default: 0195 Qhull storm; Grid690 apply 0.004s→17s |
| C1 | high | **No change** | STOS save `prefer_gpu=True` is A4 in a worse place |
| P1 | high | **Keep (gated)** | `e621e36`: host percentile &lt;160k samples; device sort above |

## This pass — kept

| ID | Pri | Baseline | After | Decision |
|----|-----|----------|-------|----------|
| P3 | high | Full LogPolar 1024, no flip: **2233 ms**. Isolated upload+coerce **2.8 ms** vs coerce-only **0 ms**. Logpolar after upload **1023 ms** vs host **1008 ms**. | Full **2156 ms**. Flipped logpolar stays on the host copy so scoring upload does not force D→H. | **Keep.** Defer `cp.asarray` until after log-polar; upload before ScoreOneAngle / hybrid fallback. |
| T1 | med | GPU `CreateBetaMatrix` N=256: **2704 ms** (CuPy `unique` on 256 pts **2035 ms**). | **2.6 ms**. CPU vs GPU max abs err **0**. | **Keep.** Vectorized pairwise RBF + host duplicate check (2 KB). |
| R2 | high | `_masked_zncc_stack` 64×96×96: **205 ms**. | **1.1 ms**. vs scalar `masked_zncc` max abs **3e-16**. Also batched `median` for shifts. | **Keep.** |
| P4 | med | Pad 512 with ImageStats: **1.35 ms** (still did min/max). | **0.21 ms**. No-stats path unchanged (~1.2 ms). | **Keep.** When stats are passed, clip noise to median±4σ instead of syncing min/max. |
| A7 | med | Invalid empty subroi: **6.16 ms** (`.get()`). | **5.78 ms**, device array like the empty-coords path. | **Keep.** Correctness / backend match; not a hot path. |
| R7 | med | Forced `.get()` before `find_offset` (dual-backend). | Stay on `GetComputationModule()`; FOV 1024→512 **35.7 ms**; recovery unit test passed. | **Keep.** |

## This pass — rejected / no change

| ID | Pri | Evidence | Decision |
|----|-----|----------|----------|
| A2 | high | Image and distance are **two buffers**. Coords already computed once and reused; second warp skips coord upload if CuPy. `TransformTile` warps each tile once. A GPU tile cache is a new feature, not a one-line reuse. | **No change.** |
| A5 | high | 12× `find_offset` 256²: serial **204 ms**, thread pool **234 ms** (worse). Same contention as `NORNIR_REFINE_TILE_PARALLEL`. | **No change.** Do not switch arrange off SerialPool. |
| P2 | high | `ScoreManyAnglesGpu` already shares one target FFT; remainder is per-angle rotate/pad/FFT. Real batching is a separate project. | **No change this pass.** |
| R1 | high | `NORNIR_REFINE_BATCHED` default ON. Serial is debug / rotation / legacy. | **Already mitigated.** |
| C3 | med | Shipping `NORNIR_REFINE_GPU_TRANSFORM=1` is A4. | **Reject** with A4. |
| R3 | med | Target crops use `CropImage` + random fill from ImageStats — not a gather. | **No change** (needs noise-fill vectorization). |
| R4 | med | Mosaic vertex extract still Python-slices then stacks; validity batching already done. | **No change** (gather rewrite is large). |
| R5 | med | Chunk AABB is **four scalars** required for a Python slice. | **No change.** |
| R6 | med | Same CropImage loop as R3 with `cval=0` (easier gather, still N kernels). | **No change this pass.** |
| A6 | med | Full mosaic `.get()` is the save/I/O boundary. | **Enhancement skipped** (`return_device` not required). |
| A8 | med | SciPy inverse is the degenerate-mesh fallback. | **No change.** |
| A9 | med | Tiles load as NumPy. `GetActiveComputationLib()` is what puts assemble on GPU. `get_array_module(source_image)` would **skip GPU warp**. | **Reject.** |
| T2 | med | CuVS brute NN slower than `cKDTree` below ~4k (256: 1.33 vs 0.28 ms). | **Gated.** `cKDTree` below 4096; CuVS at ≥4096. `cdist` stays on CuVS for GPU arrays (no size gate). |
| T3 | med | 10k-point Transform+`.get()` is a tiny host boundary; mask filters need NumPy. | **No change.** |
| Q1 | med | Quality loads from disk then warps; host ZNCC is a post-hoc report path, not refine. | **No change.** |

## Code locations (kept)

- P3: `stos_brute.SliceToSliceRigidRegistrationWithPreprocessedImages`
- T1: `transforms/one_way_rbftransform.py` `_tps_beta_matrix`
- R2: `local_distortion_correction._masked_zncc_stack` / `_shift_moving_stack_by_peaks`
- P4: `phasecorrelation.pad_image_for_phase_correlation`
- A7: `assemble._TransformImageUsingCoords` empty subroi
- R7: `refine_shared/coherent_residual.estimate_global_fov_residual_translation`

## CuVS follow-up (`cuvs-cu13` 26.8.1, `HasCuVS=True`)

Same microbenches as the pass above. GPU ~30% busy (was ~46%). CuVS only changes **pairwise `cdist`** and **nearest-neighbor index** (T1/T2). Other items are noise / load.

### Paths CuVS actually touches

| Path | N | No CuVS (prior) | With CuVS | vs host SciPy |
|------|---|-----------------|-----------|---------------|
| `spatial_distance.cdist` GPU | 256 | **1.30 ms** (H↔D + SciPy) | **0.40 ms** | host 0.13 ms (**0.32×**, launch-bound) |
| same | 1024 | (not measured; would H↔D) | **0.45 ms** | host 1.98 ms (**4.4×**) |
| same | 4096 | — | **1.02 ms** | host 38.2 ms (**38×**) |
| same | 10000 | — | **5.72 ms** | host 224 ms (**39×**) |
| T1 GPU `CreateBetaMatrix` | 256 | **2.6 ms** (vectorized, SciPy `cdist` via H↔D) | **1.4–1.7 ms** | ~1.5× vs that 2.6 ms |
| T2 NN build+query k=1 | 256 | scipy `cKDTree` **0.28 ms** | CuVS brute **1.33 ms** | **0.21×** (worse) |
| same | 1024 | 0.33 ms | 1.29 ms | **0.25×** |
| same | 4096 | 1.63 ms | 1.38 ms | 1.19× |
| same | 10000 | 4.38 ms | 2.69 ms | 1.63× |

`build_nearest_neighbor_index` uses `cKDTree` below 4096 points and `_CuVSNNIndex` at or above. GPU `cdist` stays a CuPy array (CuVS, no size gate).

T1 CPU vs GPU Beta max abs err went from **0** (both used SciPy `cdist`) to **~7** on values up to 1.3e7 (~3.5% relative where `|cpu| > 1`). CuVS Euclidean is not bit-identical to SciPy; `r² log(r)` amplifies it.

### Re-run of items CuVS does not touch

| Item | Prior (kept change, no CuVS) | With CuVS | Verdict |
|------|------------------------------|-----------|---------|
| P3 full LogPolar 1024 | 2156 ms | 2005 ms | Unrelated; load |
| R2 ZNCC 64×96×96 | 1.1 ms | 1.0 ms | Unrelated |
| P4 pad with stats | 0.21 ms | 0.08 ms | Unrelated |
| A7 invalid subroi | 5.78 ms | 5.11 ms | Unrelated |
| A5 serial find_offset | 204 ms | 162 ms | Unrelated; still worse threaded (212 ms) |
| R7 FOV 1024→512 | 35.7 ms | 34.1 ms | Unrelated |

### Takeaway

- **Keep CuVS in the image** for `cdist` / RBF Beta: N=256 already beats the old GPU H↔D fallback; N≥1024 beats host SciPy by a lot.
- **T2 NN at typical mesh sizes (hundreds–1k control points) is slower** than `cKDTree` because CuVS brute-force is O(N²) in 2D. Crossover ~4k points. **Shipped:** host tree below 4096, CuVS at ≥4096 (`NORNIR_CUVS_NN_MIN_POINTS`).
- T1 was already kept; CuVS is an extra ~1.5× on the N=256 Beta path.

Uncommitted. Do not mix with refine-recovery edits in `local_distortion_correction.py`.
