# Chunk 7 — ingest, update, cleanup, overview, progress, poolutil, sam2 writer

## Already seen

RLE bbox copy, `refresh` stub, `LocationRecord`, ignore moves, mask name.

## Findings

- `update.refresh_existing_location_masks` already delegates to `maskrefresh.refresh_existing_location_masks` so callers can skip `update.py`’s pipeline imports. The package `__init__` still imports pipeline and catalog, which is why the gallery stubs parent packages.
- `update._bbox_area_from_rle` is the copy called out in chunk 6.
- `poolutil.submit_bounded` matches `tile.py._submit_bounded`: deque, yield in submission order, cap `max_in_flight`. Segmentation adds `on_in_flight`. Home is `nornir_pools`, not a segmentation module and not a private helper in `tile.py`.
- `ingest` owns OData paging, section JSONL, and `source.json`. Gallery `load_source_document` is a second reader of that file. Leave the HTTP walker in ingest; a shared source-document record is enough if both sides must agree on keys.
- `maskrefresh._crop_image` and `stitch.resolve_crop_image` both find `{image_key}` under `images/` (png then jpeg in the gallery thumbs helper; stitch has `crop_image_filename`).

## Carry forward

`submit_bounded` pair, maskrefresh leaf, source document.
