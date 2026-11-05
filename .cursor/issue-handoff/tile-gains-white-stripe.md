# Tile gains: fixing the white stripe and per-tile beam drift (2026-11-05)

Implements the plan's brightness-drift item (`.cursor/plans/crush_optimized_pipeline.plan.md`, "Decided (James,
2026-11-01): ... a gain per tile").

## What was built

- `nornir_imageregistration/tile_gains.py`
  - `neighbour_pairs` (left-right / top-bottom neighbours from any mosaic's tile boxes).
  - `measure_overlaps`: robust strip statistic (median of tissue pixels; blank, saturated and flat strips skipped).
    Each tile is read once by a bounded thread pool and reduced at once to its strip statistics, so memory holds only
    the tiles in flight.
  - `solve_tile_gains`: robust least squares (rejects outlier overlaps, and every overlap of a tile that loses half
    or more of its overlaps), one shading constant per direction, a weak capture-order prior with a redescending
    (Cauchy) weight so a resumed pass stays a step, median gain 1.
  - `stamp_gain_png`: writes `gain`, `effective_step`, `effective_offset` into a crushed tile's `nornir_crush`
    chunk without decoding pixels.
- `nornir_buildmanager/operations/tilegains.py` + pipeline `TileGains` (`-InputTransform Stage|Translated_*|Grid_*`,
  `-Filters`, `-Downsample`, default 4): writes `TileGains_<transform>.json` in the filter folder,
  `TileGainsSource` / `TileGainsChecksum` on the filter, and for crushed filters the chunk at every pyramid level
  (only when some gain moved more than 0.5%). Legacy filters: JSON and attributes only, tiles untouched.
- Tests: `nornir-imageregistration/tests/test_tile_gains.py` (8, synthetic sections with known gains).

## Design findings (not in the plan; for James)

1. **Shading constants and a gain ramp are degenerate.** A constant per overlap direction trades exactly against a
   gain ramp across columns (or rows): both give identical overlap ratios. Something outside the data must pick.
   Tried and rejected on RC2:
   - flat-field estimate inside the tiles (left strip vs right strip of each tile): biased by large-scale tissue
     gradients; bent clean sections;
   - capture-time continuity as the pin: spreads a resumed pass's step into a section-wide ramp.
   Chosen convention: **the gains carry no trend of degree 2 over the section** (planar plus quadratic). They correct
   tile-to-tile differences and seams; the section's smooth large-scale brightness is left as captured (display
   contrast handles it, as the plan's RC3 notes already suggested for the anchor).
2. **Why quadratic, not only planar.** Chaining overlap ratios across ~30 columns integrates a small systematic bias
   in the ratios (RC2 1145: the left-right ratio drifts ~0.2% per column) into a bowl that is not in the image:
   with only the planar convention, clean sections came out 15-20% brighter in the centre.
3. **Cost of the convention:** a step near the centre projects slightly onto the planar term; about 2-3% of the step
   remains on a 32-column section (synthetic test), invisible next to the original 20-35% stripe.
4. A hard "sum of log gains = 0" row, or any convention row that includes tiles without overlaps, is met by moving
   those tiles instead (RC2 1226: gain 4e-16). The rows now cover only tiles with overlaps.
5. The loader does not apply the gains yet (plan item "loader" is still pending): today the gains are metadata in
   the chunk and the JSON.

## Validation (isolated copies; no volume touched)

Legacy Raw8 ds4 tiles mapped back to counts through each filter's contrast cutoffs, Stage placements
(`C:\Temp\Nornir\gain_test\`; script `gain_validate.py` in the session scratchpad). Seam = median right/left
ratio across the seam between tile 0's column and the column captured when the beam returns to the centre; control =
the next seam.

| Section | Stripe | Seam before -> after | Control before -> after | Gains p5-p95 | Pair residual MAD | Time |
|---|---|---|---|---|---|---|
| 1140 | yes | 0.782 -> 0.998 | 1.017 -> 1.002 | 0.90-1.10 | 0.9% | 7 s |
| 1150 | yes | 0.828 -> 1.000 | 1.011 -> 1.002 | 0.92-1.07 | 0.7% | 5-16 s |
| 1145 | no | 1.021 -> 0.998 | 1.015 -> 1.002 | 0.96-1.04 | 1.1% | 5-8 s |
| 1190 | no | 1.000 -> 0.999 | 1.014 -> 1.002 | 0.95-1.03 | 1.2% | 5-22 s |

Times vary with machine load. The seam numbers after correction are close to 1 partly by construction (the same
overlaps are solved and scored); the independent check is the images: `Y:\_nornir_work\white_stripe\gain_test\`
(`<section>_before_ds16.png`, `_after_ds16.png`, side by side in `<section>_before_after_preview.png`). The stripe is
gone in 1140 and 1150; 1145 and 1190 are nearly unchanged (the per-tile checkerboard is reduced). The pair residual
MAD (about 1%) is larger than RC3's 0.07-0.36% because the quadratic convention does not let the gains follow the
systematic ratio drift; without it the residual is 0.12-0.14% but the gains bend clean sections into a bowl.

Crushed: RC2 1226 reimported by Build2 (crushed, step 259), scratch volume `C:\Temp\Nornir\gain_test\vol1226`:
`BuildTilePyramids -Downsample 1,2,4,8,16`, then `TileGains -InputTransform Stage -Downsample 4`: 1270 tiles, 2420
overlaps (1 rejected), gains p5-p95 0.904-1.119, 15 s for the solve; chunks written at all 5 levels (pixels
unchanged), `TileGainsSource` / `TileGainsChecksum` saved on the filter; a second run writes nothing (gains within
0.5%).

## Import step (buildmanager `bfa346e`)

ImportIDoc and ImportMRC now end with a step in their pipeline definitions that iterates the imported sections and
calls `tilegains.TileGains` on `Stage` at level 1 (the only level an import writes; its tiles are still in the OS
cache), with `CrushedOnly` (legacy `-NoCrush` filters are skipped, as the plan's gain chunk is for crushed tiles) and
`SkipIfCurrent` (a re-import does not recompute gains already computed from this Stage checksum). Level-1 reads use 8
reader threads to keep memory near 1 GB.

Tested with a real import (`ImportIDoc` of `D:\nornir-testdata\PlatformRaw\IDOC\RC2_Micro\17`, 25 tiles, crushed,
scratch volume `C:\Temp\Nornir\gain_test\importtest\vol`): gains computed (40 overlaps, 0.99-1.01, 6 s) and recorded on
the filter; a second import skipped the step. Guards: `tests/test_tilegains_op.py`.

Not verified end to end: a `-NoCrush` import of the same data crashed (segfault after "Starting a Matplotlib GUI
outside of the main thread" in the legacy histogram plot) and, with `MPLBACKEND=Agg`, hung with no tile written. Both
happen inside the import call, before the new step, so they are not caused by it; not checked on the previous commit.

## Not done

- Applying the gains when loading crushed tiles (loader item), Viking reading them, assembled images re-crushed with
  gain 1.
- Translate pipelines re-running gains after every translate (plan: provided it is fast; it is ~5-40 s per section).
