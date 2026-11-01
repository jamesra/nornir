# Publication notes: nornir

Image processing, registration and volume build pipeline for serial-section electron microscopy (the nornir packages),
including the export of training data for the SAM2 segmentation trainer. Material for future papers: citations,
formulas, algorithmic decisions and the reasoning behind them. Index of all projects: `~/.cursor/publication-notes.md`.
Format and rules: the `publication-notes` skill.

## Methods and contributions

- **Section registration and volume assembly** (`nornir-imageregistration`, `nornir-buildmanager`): to fill with the
  registration, stos and mosaicking methods as they are written up.
- **Segmentation training export** (`nornir-buildmanager/nornir_buildmanager/operations/segmentationtraining`): crops,
  masks, `circle_annotations.json` and `shapes.jsonl` per volume for the trainer. Circles are written at their true
  radii, either as annotated or as the polygon's inscribed circle (the largest circle inside the exterior ring, holes
  ignored); scaling a circle into a prompt is the trainer's job, never the exporter's.
- **Carried prompts at export (planned)** (Sam2Trainer `docs/adjacent_circle_seed_plan.md`): circles and polygons linked
  to a target polygon within two sections are carried into the target's section at export (section transform, published
  residual correction, inverse transform) and stored on the target's `shapes.jsonl` line as `linked_circles` and
  `linked_polygons`, with their overlap with the target and a provenance record (source position, size, LastModified,
  and a thumbprint of the section-to-section mapping) so only changed carries are recomputed.

- **Noise-crushed import** (`nornir-imageregistration/nornir_imageregistration/noise_crush.py`, ImportIDoc/ImportMRC):
  raw 16-bit TEM tiles are stored as section-wide noise-step codes, $q = \lfloor (x - o)/\Delta \rfloor$ with
  $\Delta = k\hat\sigma$, instead of contrast-stretched 8-bit. About 86% smaller than raw uint16 at $k = 2.5$; the step
  and estimator are recorded in each PNG and on the filter so counts can be recovered to within $\Delta/2$.

## Formulas

Noise sigma per tile, Donoho-Johnstone MAD of the orthonormal Haar diagonal subband over an even-aligned center crop of
at most 2048²: $h = (a - b - c + d)/2$ for each 2x2 block, $\hat\sigma = \mathrm{median}(|h - \mathrm{median}(h)|)/0.6745$.
Section $\hat\sigma$ is the median over up to 16 evenly sampled tiles. Crush: $\Delta = \max(1, \mathrm{round}(k\hat\sigma))$,
$q = \min(\lfloor \max(x - o, 0)/\Delta \rfloor, 2^b - 1)$, $o = \min(0, \lfloor x_{\min} \rfloor)$ for signed data else 0;
recovery $\hat x = q\Delta + \Delta/2 + o$. Added error: RMS $\Delta/\sqrt{12}$ ($0.72\hat\sigma$ at $k = 2.5$).

Circle carry, five-point mean scale (Sam2Trainer `docs/depth_relative_trust.md`, section 7):
$c' = \Phi(c)$, $R' = R \cdot \frac{1}{4} \sum_{k=1}^{4} \lVert \Phi(c + R e_k) - \Phi(c) \rVert / R$, with
$\Phi = T_t^{-1} \circ C \circ T_s$.

Overlap of a carried shape $X$ with the target $T$: $o = |X \cap T| / |X|$ (whole cell, holes excluded); the trainer
keeps $o \ge 0.60$.

Pyre composite view, display to camera solve (`nornir-pyre/pyre/views/composite_display.py`,
`lookat_from_display_position`): find the source-space camera centre $\ell$ with $T(\ell) = d$ for a display point $d$
by $\ell_0 = T^{-1}(d)$, $\ell_{k+1} = \ell_k + T^{-1}(d) - T^{-1}(T(\ell_k))$, keeping the best $\ell_k$ and stopping
when $\lVert T(\ell_k) - d \rVert_\infty \le 0.01$ px or after 8 steps ($T$ maps source to target).

## Algorithmic decisions

- **2026-11-01 StosBrute reseeds the noise generator before each section pair.** Why: the masked-area / padding
  noise came from one process-wide generator, so a pair's result depended on the pairs before it. On a 7-section IDOC
  test volume (6 pairs, Blob at downsample 16, NumPy) two runs of the unchanged code gave different transforms for 5 of
  6 pairs, by up to 56 degrees on a weak pair (the threaded angle sweep draws noise in thread order). With a reseed per
  pair, single-threaded scoring gave byte-identical .stos files whatever ran before; the threaded NumPy sweep still
  varied on 1 of 6 pairs (0.6 degrees). `AlignSections` calls `StosBruteAll` once per block, which registers pairs one
  at a time on the active backend and saves the StosGroup at most every 15 s. A NumPy worker-process pool (2-4
  workers, same outputs) was tried and dropped, because `nornir_imageregistration` keeps pool children off the GPU
  and one CuPy pair (~19-25 s) beats one NumPy core (~73-104 s). Where:
  `nornir-buildmanager/nornir_buildmanager/operations/stos_brute_pairs.py`, `block.py` (`StosBruteAll`).
- **2026-11-01 StosBrute pairs can run in several CuPy worker processes sharing one GPU (`-GpuWorkers N`).** Why: about
  18 of CuPy's ~25 s per pair is host NumPy (log-polar scale search) and the GPU was ~6-12% busy, so N CuPy processes
  interleave their GPU work while each does its host work on its own core. Workers are spawned, never forked (a
  forked child may inherit CUDA state), and opt in with `SetActiveComputationLib(cupy, allow_in_child=True)`; other
  pool children still run NumPy. Measured on the 6 IDOC test pairs (Blob at 16) repeated, Ryzen 9950X + RTX 4500 Ada,
  machine shared with other jobs using 10-19 cores: in process 6.4 pairs/min (GPU 12%), 2 workers 9.9, 4 workers 12.7
  (12 pairs, last round half empty), 8 workers 26.4 (24 pairs, GPU 52% mean, 91% peak); with 28 other cores busy:
  in process 1.7, 2 workers 9.0, 4 workers 12.7, 8 workers 15.8. Outputs were byte-identical for every N (per-pair
  reseed). About 500 MB GPU memory per worker (CuPy pool ~320 MB plus the CUDA context). Main-process prepare and
  publish took 2-9 ms per pair, so it is not the bottleneck. Where: `nornir_imageregistration/computational_lib.py`,
  `nornir-buildmanager/nornir_buildmanager/operations/stos_brute_pairs.py` (`GpuWorkerPairExecutor`).
- **2026-11-01 Translate checks that the mosaic holds together, by image, and applies manual offsets.** Why: on RC3
  1637 a ~300-tile block sits ~5,500 px from its stage positions in the 2022 layout, and the current code leaves it
  at the stage positions, with no warning. Scoring overlaps across that block's boundary (NCC at downsample 32): 2022
  layout median 0.34 (53% of 70 pairs above 0.3), current code 0.03 (none of 32), against ~0.5 inside the blocks. The
  pairs across the join were not reported as failed: translate measured them at a false peak near the stage offset
  and kept them, so a check on translate's own grouping missed it. The check therefore works from the images: score
  every overlap on the final layout, link tiles through overlaps with NCC $\ge 0.5\,\tilde\rho$ ($\tilde\rho$ the
  section median), and flag two components of $\ge 3$ tiles that touch only through non-matching overlaps ($\ge 2$
  scored). RC3 0800 holds as one component of 849 tiles plus 2 singles (median 0.75). Every 1637 layout, 2022
  included, splits into a left block of ~420 tiles and a right block of ~230-280 along a strip of poorly matched
  tiles near $x \approx 57{,}000$-$60{,}000$ px, so neither join is confirmed by the images (the 2022 mosaic is
  known to be misregistered).
  Manual offsets (`*_ManualOffsets.csv`) had been read into `TranslateSettings.known_offsets` and never used; they now
  enter the spring model with 10x the weight of any measured offset (measured weights are scaled down, since
  relaxation asserts weights $\le 1$ and normalizes them per node). Rejected: only widening the pair search; padding
  2 instead of 1 (the 2022 effective value, see f16c0f6 / #195) moved 1637's block 1,800 px of the needed 1,800 in X
  but 1,100 of 5,200 in Y. Where: `nornir-imageregistration/nornir_imageregistration/translate_report.py`,
  `arrange_mosaic.py` (`_apply_known_offsets`), `nornir-buildmanager/nornir_buildmanager/operations/registration.py`.
- **2026-10-31 Mosaic grid refine measures each vertex with the ir-refine-grid estimator.** Why: with the stop rule
  matched, Python still trailed the 2022 C++ grids by 4-33% seam MAE on RC3 (0800, 1061, 1300, 1637). The port had
  replaced the legacy `match_one_pair` with a single-peak phase correlation. The faithful port
  (`refine_shared/legacy_cell_match.py`): low-pass both spectra and the Girod-Kuo cross-power spectrum (reproducing
  the legacy `apply_lp_filter` bug that adds $s_y$ for $s_y^2$), threshold the PDF to its top
  $\min(64/A, \max(5/A, 0.01))$ fraction, cluster 8-connected periodic blobs, keep peaks within 2x of the best,
  reject the vertex when more than 10 remain, then pick among the zero shift and the four wrap permutations of each
  peak by $-\mathrm{NCC}$ of the moving cell against the whole fixed tile, a pixel counting as valid when inside the
  tile buffer. RC3 0800 seam MAE 0.0859 / p90 0.1449 vs C++ 0.0857 / 0.1432 (0.1007 / 0.1509 before); Grid690 0.0824
  vs golden 0.0901. Rejected: further tuning of the single-peak path. Where:
  `nornir-imageregistration/docs/refine_grid_step_inventory.md` rows 15-17.
- **2026-10-30 Mosaic grid refine stops on the legacy mean shift, in full-resolution pixels.** Why: the Python port of
  ir-refine-grid stopped on the max $|s|$ component (non-monotonic, follows the noisiest vertex) and compared
  working-resolution shifts with a threshold the C++ tool applies in full-resolution pixels (`-sp` sets the ITK tile
  spacing), a 4x looser stop at `-sp 4`. The stop metric is now
  $\bar{s} = \frac{d}{2V}\sum_{v}(|s_{v,x}| + |s_{v,y}|)$ over all $V$ vertices of all tiles, $d$ the downsample;
  refinement stops when $\bar{s} \le \tau$ or $\bar{s}$ fails to fall. RC3 0800: 5 passes, seam MAE 0.1007 (max rule
  0.1000 after 4; working-res mean 0.1061 after 2; C++ 0.0857). RC3 1061: 0.0933 against 0.1011 (C++ 0.0831). The
  stop explains under half the gap to C++; the rest was the per-vertex estimator (2026-10-31 entry above). Rejected:
  working-res mean (stops after 2 passes). Where: `nornir-imageregistration/nornir_imageregistration/local_distortion_correction.py`
  (`_refine_tileset`), `nornir-imageregistration/docs/grid_refine_stos_vs_mosaic.md`.
- **2026-10-30 Grid-refine and translate throughput: process-pool prewarp and pass-wide FFT batches on both
  backends.** Why: on 850-tile RC3 sections the GPU ran at a median 10% SM and the host at 1-2% CPU; CuPy prewarp
  from threads took 188 s against 17 s for the NumPy process pool (RC3 1061, 2 passes, 128 cores), and per-pair FFT
  batches held ~121 cells. Output-neutral (bit-identical on Grid690; CuPy vs NumPy 2e-7 px mean on RC3 0800). Rejected:
  thread-parallel tiles (measured regression, GIL and single CUDA stream). Where:
  `nornir-imageregistration/docs/mosaic_refine_grid_gpu_assessment.md` (Full-section throughput).
- **2026-10-30 Import crushes raw TEM tiles by default (`-NoCrush` opts out), at $k = 2.5$ true sigma.** Why: on three
  4080² uint16 tiles (`C:\Temp\000-002.png`, 2026-09-26 prototype) $k = 2.5$ keeps 34-39 levels (tissue p0.5-p99.5
  spans 10-17) at 4.65-4.79 MB, 86% below raw (33.3 MB) and about 56% below today's stretched 8-bit PNG (~10.5 MB);
  10.2 TB of raw tiles would be about 1.45 TB. The September prototype's "90% at 3 sigma" summed the Haar HH without
  the 1/2 factor (2 sigma on synthetic $\sigma = 10$) and averaged in a structure-inflated patch estimate, so its step
  was about 6 true sigma: 15-21 levels and RMS error 1.73 sigma, larger than the noise removed. Rejected: $k = 3$ (86%,
  29-34 levels, user preferred the level count of 2.5), $k \approx 6$ (above), per-tile steps (tiles in a section would
  have different units, breaking the section histogram, contrast and assembly), TIFF+DEFLATE (4.6-5.1 MB vs PNG level 6
  4.3-4.4 MB, and a changed tile extension would rewrite every `.mosaic` and checksum), PNG level 9 (5-6 s/tile).
  An existing uncrushed `Raw8` is never replaced, so re-importing to add sections does not rebuild old ones. Prune
  scores of crushed tiles are scaled by $255/(q_{\max} - q_{\min})$ of the section cutoffs so existing thresholds keep
  their meaning. Where: `nornir_imageregistration/noise_crush.py`,
  `nornir-buildmanager/nornir_buildmanager/importers/{shared,idoc,mrc}.py`, `operations/pruneobj.py`
  (`CrushedScoreScale`).

- **2026-10-26 Pyre holds images deeper than 8 bits as float32; 8-bit images stay float16.** Why: float16 keeps 11
  significant bits, so a 16-bit image loses about 5 bits in Pyre. Save Warped Image of a real 16-bit TEM tile
  (`nornir-testdata/Images/16-bit/10000.tif`, identity transform) matched the source at 34.3% of pixels with errors up
  to 16 levels when held as float16, and at 100% as float32. float16 represents every 8-bit level exactly, so 8-bit
  images keep it. Cost: 16-bit images use twice the memory (4080 x 4080: 32 to 64 MiB). Rejected: changing the library
  default `default_image_dtype()` (doubles memory in the build pipeline too); re-reading the source file at export
  time (registration would still see the reduced precision). Where: `nornir-pyre/pyre/viewmodels/imageviewmodel.py`
  (`working_float_dtype`), `nornir-pyre/pyre/state/imageloader.py`.
- **2026-10-26 Integer images to float16 are scaled in float32.** Why: `ImageParamToImageArray` cast to float16 and
  then divided by the integer maximum, but that maximum (65535 for uint16) is above float16's largest value, 65504.
  Every 16- or 32-bit image raised an overflow (the package sets `np.seterr(over='raise')`) or, without that setting,
  would load as all zeros, so Pyre could not open 16-bit images (the 1.8.1 installer included). Only that case now
  divides in float32, one row slab at a time; 8-bit images and float32/float64 conversions keep the original expression
  and are pixel-identical to before on real 8-bit mosaic and Blob images and on 16-bit TEM/SEM tiles; 16-bit to float16
  is within 2.4e-4 of a float64 reference. Where: `nornir-imageregistration/nornir_imageregistration/core/_core.py`
  (`_int_image_to_unit_float`, `4358e8d`).
- **2026-10-26 Save Warped Image warps the source image into target space, at the source file's bit depth.** Why: it
  warped the target image onto a source-sized canvas. On a real StosBrute64 pair
  (`100-101_ctrl-TEM_Blob_map-TEM_Blob.stos`) the export now matches `TransformStos` (correlation 0.998, target shape
  683 x 682). The default "PNG 16-bit" choice also wrote 8-bit sources as 16-bit PNGs; the export depth is now capped
  at the source file's depth. Where: `nornir-pyre/pyre/common.py` (`warped_image_export`),
  `nornir-pyre/pyre/ui/windows/stoswindow.py` (`onSaveWarpedImage`), `4eb7418`.
- **2026-10-26 Save STOS: `ControlImageDim` from the target image, `MappedImageDim` from the source.** Why: Pyre wrote
  them swapped (in `StosState` the deprecated "Fixed" names hold Source), and `StosFile.Save` keeps preset sizes, so
  every `.stos` Pyre saved with differently sized images carried swapped sizes. They feed the grid transform's bounds
  and the refine plausibility check. Files saved before nornir-pyre `6cb309f` with unequal image sizes keep the swap
  until saved again. Where: `nornir-pyre/pyre/common.py` (`stos_image_dims_from_stos_config`).
- **2026-10-22 Pyre composite view: solve $T(\ell) = d$ instead of applying $T^{-1}$ once (formula above).** Why: mesh
  forward and inverse triangulate different point sets and RBF fits two separate functions, so $T(T^{-1}(p))$ missed
  $p$ by up to 15 px (mesh) and 5 px (RBF) on a jittered 8x8 grid; each registration re-centred through it, and the
  view crept about 45 px over 40 results. With the solve the worst miss is 0.026 px (mesh, 300 points, mean about 6
  single-point transforms) and 0.01 px (RBF); the re-centred framing is also pinned so it cannot move. Rejected: 4
  steps (worst 0.88 px on mesh). Where: `nornir-pyre/pyre/views/composite_display.py`.
- **2026-10-22 Pyre: a held Space registers each point once per hold.** Why: key auto-repeat (about 30 presses/s)
  re-registered the hovered point every 100-200 ms, and point alignment is not idempotent at subpixel level: the point
  moved 0.3-1 px on every repeat indefinitely (process pool, synthetic image). The user chose once per point per hold
  over once per key press and over continuous re-registration. Where:
  `nornir-pyre/pyre/controllers/control_point_registration_queue.py` (`SpaceHoldRegistrations`).

- **2026-10-26 Exporter window placement: quarter-step lattice rejected; free placement under consideration, not implemented.** Why: on RPC2 (set v3, `shapes.jsonl`, outlines simplified so approximate) 2,388 of about 5,500 masks that fit one 1024 crop sit between half-step (512 px) lattice positions and are split by the tile-aligned phase search (location 29308: 641 x 419 px, split 6% / 94%). A quarter-step lattice would fix only 1,234 of them; centring a window on the mask (clamped to contain the padded bbox) fixes all. The trainer sees one image per example with no tile-grid awareness, and the client/server fuse aligned 1024 cells at inference, so whole-object crops match inference better than clipped fragments. Image sharing (`group_windows`, identical windows only) is 1.8% of RPC2 v3 images (953 of 52,332), so a mask-specific window costs little. Rejected: quarter-step lattice (user, 2026-10-26; half the cases remain). Open: effect on training is unmeasured; needs a v4 export and a fixed whole-mask validation set. Any change is a new set number (`Training-set-naming.mdc`). Where: `nornir-buildmanager/nornir_buildmanager/operations/segmentationtraining/geometry.py` (`place_mask_windows`).
- **2026-10-26 Pyre point registration: send CPU transforms to pool workers; one hovered point per press.** Why: on a real STOS pair (3248 points, CuPy) a point took 3.4-10.1 s because the GPU grid/mesh transform was pickled to each cold worker, which started CUDA and compiled kernels (2.6-2.9 s per worker); a CPU rebuild of the transform brings it to about 0.12 s warm and 0.5-0.6 s on a worker's first task. Hover-and-Space also added the hovered point to the shared selection, so press N aligned N points; each press now aligns one. The CPU and GPU snapshots differ by a median of 0.7 px (max about 3 px on 30 points), within the run-to-run variation of about 0.9 px, and both are equally accurate against a synthetic ground truth. Rejected: killing in-flight pool workers on cancel (the pool is shared; results are discarded instead). Where: `nornir-pyre/pyre/controllers/transformcontroller.py`.
- **2026-10-25 Carry at export, not in the trainer.** One implementation of the carry for circles and polygons, matched
  to Viking's production carry, with per-circle provenance so a new correction set or an edited annotation re-carries
  only what changed. All linked circles are exported with their overlap; the trainer filters (threshold changes need no
  re-export). Links alone decide what is carried: a link between a circle and a polygon means the process continues, so
  no terminal flag is needed.
- **2026-10-25 Links must include circles.** `shapes.py` links only polygon locations, so circle-polygon links were
  dropped. In the v5 data only 619 of 40,998 RPC1 locations and 581 of 13,024 RPC2 locations had a linked outline 1-2
  sections away, and the trainer's adjacent-polygon prompt realised 0.7% of its 15% share.
- **Exporter writes true circle radii** (nornir `3b6fe2f` removed `-CircleDiameterScale`): the scale is a training
  choice and can change without a re-export.

## Discussion points

- Measured pixel noise is shot-noise-shaped but far below what the camera's counts-per-electron predicts. Binned
  variance against mean is linear (r 0.95-0.998). RC2 Gatan tiles (2012, `nornir-testdata` RC2_Micro/17): effective
  gain 1.2-2.1 counts/e⁻, read noise near 0, $\sigma^2/S$ 1.3-1.45. OneView tiles (`Y:\AshCameraTest`, Aug 2026; RPC3's
  2023 idoc records `CountsPerElectron = 115.93` for that camera): effective gain 0.44-1.22, so pixel sigma is 130-155
  counts where Poisson at 116 counts/e⁻ predicts ~1,600. Likely cause: the scintillator spreads each electron over many
  pixels (neighbour correlation 0.87-0.99, partly structure). So the step must come from measured pixel noise, not
  from `CountsPerElectron`; the latter is useful for expressing codes in electrons (one $k = 2.5$ OneView step is about
  3 e⁻). (2026-10-30, `photon_transfer.py` in the session scratchpad.)
- One section-wide step is coarse in dark regions and fine in bright ones because shot noise grows as $\sqrt{S}$; a
  variance-stabilising transform before quantizing would equalise it (open question below).

- Registered (warped) images exported from Pyre's Save Warped Image before nornir-pyre `4eb7418` (2026-10-26) are
  the target image warped by the source-to-target transform, not the source image in target space; they should be
  re-exported. When the swap was introduced is not established (verify).
- Linked annotations across sections are sparse in the exports so far; link coverage, not model capacity, limits how much
  adjacent-section prompting can be trained.

## References

- Anderson, J. R., et al. (2009). A computational framework for ultrastructural mapping of neural circuitry. *PLoS
  Biology* 7(3), e1000074. (verify) Used for: the serial-section registration workflow nornir continues.
- Anscombe, F. J. (1948). The transformation of Poisson, binomial and negative-binomial data. *Biometrika* 35(3/4),
  246-254. doi:10.2307/2332343 (verify). Used for: the planned variance-stabilised crush ($2\sqrt{N + 3/8}$).
- Donoho, D. L., & Johnstone, I. M. (1994). Ideal spatial adaptation by wavelet shrinkage. *Biometrika* 81(3),
  425-455. doi:10.1093/biomet/81.3.425 (verify). Used for: the MAD/0.6745 noise estimate on the finest wavelet subband.

## Open questions for a paper

- Carry accuracy: carried-centre error against Viking's production carry and against the linked polygon, per volume.
- ~~Mosaic grid refine vs ir-refine-grid: which per-pass step differs~~ answered 2026-10-31: the per-vertex
  estimator. Still to measure: whether the legacy estimator closes the gap on RC3 1061, 1300 and 1637 as on 0800.
- Crushed tiles: effect on mosaic registration (seam MAE and offsets vs `-NoCrush` on the same sections), on SAM2
  training and inference when both use crushed tiles, and visible banding in Leveled/Viking views (only 10-17 codes
  span the tissue). Whether an Anscombe-stabilised crush in electron units (gain from `CountsPerElectron` or a
  per-section photon-transfer fit) keeps fewer levels for the same fidelity.
