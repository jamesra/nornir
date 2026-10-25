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

## Algorithmic decisions

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

- Linked annotations across sections are sparse in the exports so far; link coverage, not model capacity, limits how much
  adjacent-section prompting can be trained.

## References

- Anderson, J. R., et al. (2009). A computational framework for ultrastructural mapping of neural circuitry. *PLoS
  Biology* 7(3), e1000074. (verify) Used for: the serial-section registration workflow nornir continues.

## Open questions for a paper

- Carry accuracy: carried-centre error against Viking's production carry and against the linked polygon, per volume.
