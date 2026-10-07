# Chunk 1 — `sam2_segmentation_trainer/data/`

## Already seen

- `CropExample` (volume, z, downsample, image_key, location_id, paths, split_key, width, height)
- Mask file `{imageKey}_{locationId}.png` via `mask_location_id`
- `ignore.json` as a JSON array of location ids (`load_ignore_ids`), plus mtime stamps (`ignore_list_stamps`)
- Uncompressed column-major COCO RLE (`decode_coco_rle` / `_decode_uncompressed`): `counts` + `size` `[height, width]`, Fortran order, uint8 `{0,1}`
- Gray load: `_load_gray_uint8` (PIL `convert("L")`) then `to_rgb_uint8` (channel stack, no dtype cast, no percentile stretch)
- ImageNet mean/std constants on the dataset module
- Train/val clamp: if a group has at least two keys, keep at least one train and one val (`make_location_split` and `include_new_keys`)

## Findings

- `annotation_ids_in_json` only returns the id half of `sidecar_ids_and_size`. Nothing else in the repo calls it.
- `make_location_split` and `include_new_keys` repeat the same `n_train` clamp (lines 50–56 and 106–111). Parameters: key count and `train_fraction`. Output: an integer count in `[1, n-1]` when `n >= 2`.
- `index_volumes` both lists crops and moves ignored masks (`move_ignored_masks`). Inventory and filesystem mutation are one function.
- `summarize_index` lists `images/` and `masks/` again after `_index_manifest` already listed them when `skip_missing` is true.
- Sidecar JSON is parsed here (`sidecar_ids_and_size`) and again per sample in the dataset (`_annotation_for_id`).
- `to_rgb_uint8` does not cast to uint8. A float gray array stays float after the stack.
- `collate_em` rebuilds a meta dict from fields that already live on `CropExample` (`volume`, `location_id`, `image_key`, `downsample`, `split_key`).

## Carry forward

Mask name, ignore list, RLE layout, gray→RGB, ImageNet constants, `CropExample` meta keys.
