# Chunk 4 — `annotation-gallery/`

## Already seen

`location_scores` schema, `ignore.json` array of ints, mask name `{imageKey}_{locationId}.png`, sqlite `annotation_crops.sqlite`.

## Findings

- `catalog.load_ignore_ids` / `save_ignore_ids` match nornir `catalog.py` (same path, same sorted JSON array). Trainer `manifest.load_ignore_ids` is the same read but swallows `OSError` / `JSONDecodeError` and prints. Gallery and nornir let a corrupt file raise. Outputs differ on bad JSON.
- `catalog._ensure_score_schema` is a copy of `train._ensure_score_schema` (same SQL, same empty-string image key for legacy rows).
- `image_key_from_mask_name` and trainer `mask_location_id` both `rpartition("_")` on a `.png` stem. Gallery also requires `IMAGE_KEY` to match. Nornir `_location_id_from_mask_name` uses `rsplit("_", 1)` and does not check the key pattern. Same filename, three parsers.
- `refresh.py` stubs `nornir_buildmanager` and its parent packages so `maskrefresh.refresh_existing_location_masks` can import without running `segmentationtraining/__init__.py` (that init imports catalog, pipeline, and cleanup). The gallery image does not install Nornir. This is the dependency to remove: a leaf import, not a stub.
- `server.intersect_keep` and `identity.intersect_grants` both filter a grant dict down to registry names.
- `thumbs._write_jpeg` is `_write_jpegs` for one size. Small, local.
- OData paging (`server._odata_values`) is a second walker next to nornir `ingest._iter_odata_pages`. Gallery needs one location; ingest needs a volume. Do not pull ingest into the gallery.

## Carry forward

Ignore list, mask filename, score schema, gallery stub of buildmanager, sqlite path.
