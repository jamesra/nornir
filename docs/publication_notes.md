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

## Formulas

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

- Registered (warped) images exported from Pyre's Save Warped Image before nornir-pyre `4eb7418` (2026-10-26) are
  the target image warped by the source-to-target transform, not the source image in target space; they should be
  re-exported. When the swap was introduced is not established (verify).
- Linked annotations across sections are sparse in the exports so far; link coverage, not model capacity, limits how much
  adjacent-section prompting can be trained.

## References

- Anderson, J. R., et al. (2009). A computational framework for ultrastructural mapping of neural circuitry. *PLoS
  Biology* 7(3), e1000074. (verify) Used for: the serial-section registration workflow nornir continues.

## Open questions for a paper

- Carry accuracy: carried-centre error against Viking's production carry and against the linked polygon, per volume.
