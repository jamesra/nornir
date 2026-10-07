# Chunk 6 — stitch, planning, pipeline, catalog, product index, freshness

## Already seen

RLE layout, mask filename, ignore list, `LocationRecord`, `MaskJob`, image key `{z}_X…_Y…`.

## Findings

- `_bbox_area_from_rle` is copied in `pipeline.py` and `update.py`. Same input (COCO RLE dict), same output `([x, y, w, h], area)`. Column index is `index // height`, row is `index % height`. `update.py` also guards `if value == 1 and height`. One function should own this. `encode_coco_rle` already computes bbox from the bitmap; the RLE walk exists for the sidecar-only path.
- `catalog.load_ignore_ids` / `save_ignore_ids` / `ignore_path` / `sqlite_path` match the gallery copies. Nornir `connect` also migrates `locations` (jpeg_relpath → image_relpath, drops origin columns). Gallery `connect` creates the file; nornir catalog is the writer of `locations`.
- `upsert_sam2_scores` updates `locations` SAM2 columns. It does not write `location_scores`. Two tables, two meanings.
- `stitch.probe_tile_pixel_size` and `pipeline._repair_one_overlay` open files with `PIL.Image.open`. `LoadImage` is the wrong replacement: it masks the image and replaces extrema with noise. A raw pixel read belongs in imageregistration beside `pillow_helpers`, which today only sniffs dtype.
- `stitch.write_png` and `assemble._save_rgb_png` both write PNG. Different inputs (gray canvas vs RGB preview). Do not merge without a parity check.
- `stitch_from_loader` copies axis-aligned tiles into a crop. `assemble_tiles.TilesToImage` warps a mosaic. Same word, different geometry. Keep the sweep scheduler in buildmanager.
- `PlannedCrop`, `ImageWatermark`, `SectionWatermark`, `ExportParams`, `ResolvedTileset` are already records. `export_section_crops` still threads many of them as loose arguments.
- `catalog.py` imports `ingest`, `stitch`, and `product_index`, so a gallery that only needs ignore-list I/O cannot import this module.

## Carry forward

Duplicate RLE bbox, two score stores, catalog import fan-out, raw PIL opens that must not call `LoadImage`.
