# Chunk 5 — records, geometry, masks, curves, wkt, grouping

## Already seen

Mask filename, COCO RLE (`counts`, `size` `[H, W]`, Fortran), ignore list, `CropExample`.

## Findings

- `LocationRecord` is the right record for one annotation (id, z, wkt, parent, off-edge, last_modified, type, radius). `to_json` / `from_json` is the stable section JSONL shape. Keep it.
- `MaskJob` is the right picklable record (location_id, image_key, width, height, rings, mask_path, rle_path). Raster output is paths plus `bbox` `[x, y, w, h]` and `area`.
- `encode_coco_rle` is the writer for the layout `decode_coco_rle` reads. Both use Fortran order and `size: [height, width]`. Counts are an uncompressed int list. Empty mask is `counts: []`. A foreground-first mask inserts a leading 0. They live in different repos and can drift.
- `TileRect` and `CropWindow` are spatial records. `TileRect.image_key` is `{z}_X{ix0}-{ix1}_Y{iy0}-{iy1}`. Mosaic Y increases with image row (`MOSAIC_Y_INCREASES_WITH_IMAGE_ROW`). Do not fold these into imageregistration `iRect` until that axis contract is written.
- `rasterize_mask_job` uses Pillow polygon fill. That is pixel work, but the rings come from WKT/curve hydration. Moving only the fill into imageregistration still leaves `PolygonRings` behind. Prefer a leaf next to the mask job, not a new imageregistration dependency for the trainer.
- `wkt.location_from_odata_entity` is what the gallery calls through `maskrefresh`. It returns `LocationRecord` or None.

## Carry forward

`encode_coco_rle` ↔ `decode_coco_rle`, `MaskJob` result dict (`bbox`, `area`), `LocationRecord`, image-key format.
