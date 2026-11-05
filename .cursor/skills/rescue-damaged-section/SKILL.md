---
name: rescue-damaged-section
description: >-
  Rebuild the mosaic of a damaged section (torn, folded, tissue moved so tiles stop overlapping)
  without touching production until the result is proven: isolated copy, a prune that actually
  drops blank tiles, translate and per-half grid refine, diagnostics that separate real
  displacement from noise, then install and lock the result as the section's transforms in the
  volume and re-assemble its images for manual registration in Pyre. Worked example: RC2 section
  1240 ("bad tear in section", 2026-11-04). Use when a section's Translated/Grid mosaic has tiles
  piled up or scattered, large dark folds or white tear regions, or the user asks to rescue a
  damaged mosaic.
---

# Rescue a damaged section's mosaic

Everything up to **Install** happens on an isolated copy under `C:\Temp\Nornir\<section>_retranslate\`.
Nothing in the volume changes until the result is proven and backed up. The standing rules apply:
[Questions-and-proving-fixes](../../rules/Questions-and-proving-fixes.mdc) (evidence before "fixed"),
[Shared-checkout-safety](../../rules/Shared-checkout-safety.mdc), and the line-ending rules for any file you commit.

Scripts are in [`scripts/`](scripts/). They read `RESCUE_SECTION_DIR` (the channel folder of the copy,
`<copy>\TEM\<section>\TEM`) and write beside it. Run Python as `venv\pyre314\Scripts\python.exe`.
`NORNIR_COMPUTATIONAL_LIBRARY=numpy` for refine and assemble (see Pitfalls). Long jobs: run them in the
background and wait on the log; they take minutes to tens of minutes.

## What the damage looks like

Section 1240: the tissue tore into two halves that moved apart, plus a white tear strip, black fold
wedges and a flat resin hole. Translate treated the tear-strip tiles as real tissue and scrunched them
onto each other (13 tile pairs overlapped by more than 50%); pruning left 77 dead tiles in and 33 live
tiles out; and no tile pair across the tear shares any tissue. Tiles on either side of a tear **cannot
be registered by correlation**; plan on a manual merge in Pyre.

## Procedure

1. **Isolated copy.** `robocopy` the section folder to the scratch root, leaving out the full-resolution
   levels you do not need (`Raw8\TilePyramid\001,002`, `Leveled\TilePyramid\001,002`, `Registered_TEM`).
   ds4 tiles (`...\004`) are what translate and refine read. For the pipelines to run on the copy, give it a
   volume root `VolumeData.xml` (copy of the volume's) and a block `TEM\VolumeData.xml` holding only the
   section's `Section_Link`. Robocopy preserves the original dates, so a later "older than two weeks"
   temp cleanup will catch the copy: exclude it.
2. **Prune properly** (this was the first big win). The 2015 prune left both mistakes in:
   - Modern `image_stats.Prune` scores are the 2015 scores **times about 217** (1008..8032 instead of
     4.7..36). A stored cutoff of 10 therefore removes nothing, and a stored score file with the new
     cutoff removes everything. **Move the old `PruneScores_*` files aside** (not `Histogram_*`, that is the
     intensity histogram Leveled's contrast came from) so the pipeline regenerates them.
   - Pick the cutoff from the histogram: look for the empty valley between the blank-tile cluster and
     real tissue, then **look at the tiles on both sides** (Raw8 ds4) with the user. 1240: valley at
     1,535-1,710, but a kept tile at 2,416 and a cut tile at 1,920 put the line between them; 2200 (old
     10 on the new scale is 2,169) matched the user's judgement. Score-only does not catch every blank
     tile: add the **flat-tile rule** (intensity std below 8 over non-zero pixels on Leveled ds16).
   - `nornir-build SetPruneCutoff <volume> -Sections N -Channels TEM -Filters Raw8 -Value 2200`, then
     `nornir-build Prune <volume> -Sections N -Channels TEM -InputFilter Raw8 -Downsample 4 -DefaultThreshold 2200 -overlap 0.1`.
     Check that the written `Prune_Thr2200.0.mosaic` equals "score >= cutoff".
   - **The old prune dropped live tiles.** The 2015 mosaic held 33 tiles scoring below 10 and lacked 33
     scoring above (up to 29.9). Compare the tile set against the scores. Dropped tiles have no Leveled
     image. Rebuild them with `scripts/rebuild_leveled_tiles.py` (Raw8 level 1 through the section's
     min/max/gamma, then 2x shrink per level). Validate the method first on tiles that do have images:
     it matched RC2's within 1-2 grey levels, not bit-for-bit.
3. **Re-translate on the pruned set** (`scripts/retranslate.py <tag> Stage.mosaic`) with the section's own
   `Translated_Prune_Settings.json`. Extrema masking is on by default; leave it. Read the report: groups,
   matched groups, failed pairs, `needs_review`. A good result for a torn section is **two groups** (the two
   halves), no failed pairs, no joins flagged, and `scripts/tile_overlap_stats.py` showing no pair over 15%
   (nominal overlap is about 12%). Worse than that means tiles are being placed on each other: fix the prune
   first. 1240 went from 13 pairs over 50% to none just by pruning correctly, with no translate changes.
   **Nominal overlap differs by section.** 825 was recaptured with 20% overlap, so over 1,600 of its pairs are
   over 15% and only pairs over about 50% are suspect. Work out the section's own overlap from the Stage mosaic
   (tile pitch against tile size) or its capture notes before reading the threshold.
4. **Diagnose with an all-pairs NCC** (`scripts/crosscheck_pairs.py`, ds16, every pair within 4 stage
   pitches, about 39k pairs, 3-4 minutes on 16 cores). Run it with `CROSSCHECK_EXTREMA=1`.
   - Use a **masked** NCC with a minimum overlap (3,000 px at ds16) and a variance floor; without the
     floor flat regions return NCC far above 1.
   - Estimate the noise floor from pairs more than 12,000 px apart (their best peak is noise). Then
     "strong peaks that disagree with the layout" should be compared with the count the noise floor predicts:
     at 1240 they matched, so there was **no evidence** of far-displaced tiles.
   - Immediate-neighbour pairs scoring at or below 0.3 at the layout are the real problem tiles. At 1240
     all of them were tear-strip tiles; one pair (805/806, NCC 0.93 one tile pitch away from where the layout
     put it) was a true misplacement and was fixed by moving the tile.
   - Without extrema masking, large black or white regions produced spurious 0.99 matches (noise floor 0.69
     instead of 0.49). Always mask them.
5. **Refine each half on its own** (`scripts/refine_half.py left|right`): `RefineGridMosaic` with the Mosaic
   pipeline's grid settings (cell 128, mesh 8x8, 10 iterations, threshold 0.25, ds4). Merge the two results
   into one `Grid_*.mosaic` (disjoint tile sets). Both halves converged in 4 passes (mean displacement
   about 1.3-1.6 px down to 0.15-0.19). Large single-vertex shifts (up to 160 px) sat over blank regions
   (folds, white tear strip) and did not move the tissue; look at before/after crops before worrying.
6. **Review the assembled image** (`Assemble` at ds8/ds16 from the copy, or `tile_overlap_stats`) before
   installing. Put images on `Y:\_nornir_work\<section>\` and give the `Y:` path: do not upload images to
   chat (30 MiB and 8000 px limits, and the user reads from another device).
7. **Annotations first (policy, set by the user 2026-11-04 for every repaired mosaic).** Before a repaired
   mosaic is installed, the section's annotations are rescued: their mosaic-space positions are mapped from the
   old mosaic coordinates to the new ones, through the tiles both mosaics share
   (`scripts/remap_mosaic_points.py`), and volume-space positions are recomputed afterwards from the
   volume transform. `install_rescue.py` enforces this: a real install needs `--annotation-rescue-report` (the
   report that script writes) or `--no-annotations` after the user confirms the section has none. The
   centre-tile anchor below is only a stopgap; with annotation rescue it is not needed and the mosaic can sit at
   its new coordinates.
   The mapping is `nornir_imageregistration.mosaic_remap.MosaicPointRemapper`: a point at old mosaic position p in
   tile t goes to `new_t.Transform(old_t.InverseTransform(p))` (`Transform` is tile pixels to mosaic,
   `InverseTransform` the reverse). Where tiles overlap it uses the closest-centre tile, as Assemble does. Each
   point comes back MAPPED, EXTRAPOLATED (inside a tile outline but off its image: warp edge) or NO_SHARED_TILE
   (no tile in both mosaics covers it; look at these by hand), plus an overlap disagreement: how far apart two
   overlapping tiles put the same point in the new mosaic, which exposes annotations drawn where the old mosaic
   was misregistered. On 1240 the sample round trip for MAPPED points was 0.20 px median. Run
   `scripts/remap_mosaic_points.py --sample` first when no annotation export exists yet. Still open: exporting a
   section's mosaic-space annotations from Viking and importing the result, and recomputing volume-space
   positions from the volume transform afterwards.
8. **Install in production** (needs the user's approval for the section, and step 7 done).
   1. Back up everything you will change to `Y:\_nornir_backups\RC2\<date>-section<N>-rescue\` with the same
      relative layout: the channel `VolumeData.xml` (and `.backup.xml`), `Stage`, `Prune_*`,
      `Translated_Prune_Max0.5.mosaic`, `Grid_*.mosaic`, `ChannelToVolume*`, `Raw8` prune files and metadata,
      `Leveled` and `Mask` metadata and `Images`. Verify sizes against the source.
   2. Generate the missing Leveled tiles in the volume at every level (new files only). Use a drive-letter path.
   3. Move the old `Raw8\PruneScores_*` files aside, then `SetPruneCutoff` and `Prune` as above.
   4. `scripts/install_rescue.py <volume> <section> <translated.mosaic> <grid.mosaic>` (try `--dry-run`
      first). It refuses a mosaic that uses a tile missing from the new Prune mosaic, **anchors the centre
      tile** (below), copies the files, re-points each node at its input's current checksum (`SetTransform`),
      recomputes checksums, and locks `Translated_Prune` and `Grid`.
   5. **Anchor the centre tile before anything is installed.** Annotations are stored in mosaic coordinates, so
      the new mosaic is shifted rigidly (every tile's target space translated by one vector) until the centre
      tile has the coordinates it has in the mosaic being replaced. Tile 0 is the centre tile for these
      montages; if tile 0 is not in both mosaics (pruned, or not placed) the script anchors on the common tile
      nearest the old mosaic's centre and says so. The shift is computed separately for Translated and Grid
      (each against its own predecessor), so both stay in the old frame; the mosaic origin is then usually not
      (0, 0). `--anchor-tile N` picks the tile, `--no-anchor` installs at the new coordinates.
      Always read the dry run first. Two things can make anchoring wrong:
      - **Negative coordinates.** `Assemble` draws from (0, 0) and keeps only the part at non-negative
        coordinates (`_warn_if_mosaic_origin_is_negative` in `tile.py`, limit -64 px). The script refuses when
        the shifted mosaic starts below that, unless `--allow-negative-origin` (cropped assembled images).
      - **Two pieces.** If the new translate places the halves differently from the old one, one anchor tile
        fixes only its own half; the other half's coordinates still differ from the old by the change in the
        relative offset. Section 1240: anchoring on tile 83 meant a shift of (-75,325, +224) px, putting
        the origin at (-75,325, 224) and the other half wrong anyway. The better solution is then to
        **translate the annotations from the old mosaic coordinates to the new** (one affine/rigid per piece,
        from matching tissue), and install at the new coordinates with `--no-anchor`. Ask the user which.
      Record in the section's repair notes which of the two was done: installing without the anchor leaves
      existing annotations displaced.
   6. `nornir-build Assemble <volume> -Sections N -Channels TEM -Downsample 8,16,32,64 -Filters Leveled -Transform Grid`.
      This also rebuilds the `Mask` images. Then regenerate `Blob` with the values `scripts/TEMAlign.sh`
      uses (they are not recorded in the metadata): `CreateBlobFilter <volume> -Sections N -Channels TEM
      -InputFilter Leveled -Levels 16,32,64 -OutputFilter Blob -Radius 9 -Median 7 -Max 3` (about 3 minutes
      for 1240). Back up the old `Blob\Images` first.
   7. Rehearse steps 3-6 on the copy first. The rehearsal on 1240 reproduced the same Prune checksum and node
      checksums as production.
9. **After install.** `ChannelToVolume_Untranslated` / `ChannelToVolume` and the section's stos files were
   built from the old Grid and are stale. Do not run `MosaicToVolume` or later steps blindly: they rewrite
   `ChannelToVolume.mosaic`. The user merges the two halves and registers the section to its neighbours in
   Pyre; slice-to-volume follows from that.

## Check what was dropped at each stage

Compare tile sets Stage, Prune, Translated, Grid before deciding what is wrong. A drop can be correct (blank
tiles) or a fault. Section 75: Prune 782, Translated and Grid 627, so 155 tiles survived the prune and never
reached the translation. Section 152 (not damaged): Stage = Prune = Translated = 1,164 but Grid 1,158, six
low-texture tiles lost in the grid refine. A section like 152 needs only those tiles put back (re-run the grid
refine with them, or add them with their translation), not a full rescue. Pair each dropped tile with its prune
score and whether it has a Leveled image (`.cursor/skills/rescue-damaged-section/scripts` has no helper yet;
the comparison is a few lines over `MosaicFile.Load(...).ImageToTransformString` and the `PruneScores` file).

## Pitfalls met on 1240

- `RefineGridMosaic` on the default CuPy backend raises `Implicit conversion to a NumPy array is not allowed`
  in `_prewarp_tile_for_grid_refine` (CuPy array into SciPy `map_coordinates`). Use
  `NORNIR_COMPUTATIONAL_LIBRARY=numpy`. Not investigated; may affect pipeline runs.
- `ConvertImagesInDictGpu` drops one leading backslash of a UNC path. Use `Y:\...` or stage files locally.
- `CreateExtremaMask` summed region sizes over labels `0..nLabels-1`, so the last region was always masked
  however small. Fixed in `nornir-imageregistration` `d878af3`; tests in `tests/test_extrema_masking.py`.
- Stage mosaics have negative Y; `MosaicTileset.AssembleImage` renders from origin (0, 0), so assembling a
  stage mosaic returns a sliver. Assemble translated or grid mosaics.
- The prune pipeline reuses an existing score file whatever its scale. A stale scale gives "All tiles removed".
- Editing `Stage.mosaic` invalidates the Prune node's input checksum and the pipeline then cleans its data.
  In the volume, never edit `Stage.mosaic`; keep Stage original and express extra rules in the Prune mosaic.
  The 1240 flat-tile exclusion (tile 314) lives only in the translated and grid mosaics, so the installed
  Prune mosaic has one more tile than they do.
- `nornir-build` prints a spinner; filter output with `grep` for `Error|Traceback|Removed|Cleaning`.
- Brute-forcing a rotation between the two halves (`StosBrute`, log-polar, `search_scale=False`) gave scores at
  the noise level (1.6-1.7; real match 3-4) and inconsistent angles. Per-tile StosBrute on healthy pairs works
  (angle about 0, weight 2.5-3.7, about 8 s per pair at ds8) but is too slow to run broadly. Skip both.
- Do not stop a pair search early on a "good" score when the tile has a fold: a constant-width fold matches
  itself at many offsets.
- The workstation GPU also drives the display and is shared; keep one GPU job at a time.

## Record of the 1240 run (2026-11-04)

Prune cutoff 2200 plus the flat-tile rule; 1,363 tiles of 1,441. Translated: two groups (699 and 664),
0 failed pairs, median NCC 0.914, no overlaps over 15%. Grid: both halves converged. Installed and locked
in `RC2\TEM\1240\TEM\` **at the new coordinates, not anchored** (that run predates the anchor step; a dry run
of the anchor afterwards gave a shift of -75,325 px in Y, so annotations on 1240 would need to be translated
from the old mosaic coordinates); backup in `Y:\_nornir_backups\RC2\2026-11-04-section1240-rescue\`; working files
and images in `Y:\_nornir_work\section1240\`. `Blob` regenerated at levels 16/32/64 with the TEMAlign values.
Open: manual merge of the two halves in Pyre, stos to the neighbours (a manual StosBrute, so the Blob images
matter less).
