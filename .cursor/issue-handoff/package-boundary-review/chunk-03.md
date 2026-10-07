# Chunk 3 — train, checkpoint, mqtt, paths, export

## Already seen

ImageNet constants, checkpoint load, `CropExample` meta keys (`volume`, `image_key`, `location_id`), ignore-list path `AnnotationCrops/ignore.json`.

## Findings

- `train._ensure_score_schema` is the same migration as `annotation-gallery/catalog.py._ensure_score_schema`: table `location_scores (location_id, image_key, epoch, score)`, primary key those three, legacy rows copied with `image_key=''`. Output: a window-keyed table.
- `record_location_scores` writes that table at `{volume}/AnnotationCrops/annotation_crops.sqlite`. It is training loss, not the `locations.sam2*` columns in nornir `catalog.upsert_sam2_scores` (`sam2PredIou`, `sam2ObjectScore`, `sam2Stability`, `sam2GtIou`, `sam2Checkpoint`, `sam2ScoredAt`).
- `_write_run_inputs` takes seventeen parameters that are one run’s identity (paths, counts, seed, fraction, image size, batch, epochs, model config, pretrained checkpoint).
- `_snapshot` takes twelve parameters that are one resume payload (model, optimizer, scheduler, scaler, epoch, steps, best IoU, freeze mode, rng).
- `_counts_by_volume` repeats the volume tally inside `summarize_index`.
- `export_serve.finetuned_state_dict` is the only helper that accepts either a raw state dict or `{"model": ...}`. `evaluate` and `EMPredictor` do not use it.
- `paths.data_root` / `output_root` / `checkpoint_root` are the same env-or-default shape. Fine as three functions; a `TrainerRoots` record would stop `_resolve_paths` returning an unlabeled 4-tuple.
- MQTT sample labels use the same three meta keys as `collate_em`. `format_batch_samples` and `format_ranked_samples` share the “+N more” tail.

## Carry forward

`location_scores` schema, sqlite path, meta keys, checkpoint wrapper vs raw state dict.
