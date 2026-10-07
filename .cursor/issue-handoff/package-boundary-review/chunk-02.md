# Chunk 2 — model, metrics, infer, evaluate, validate

## Already seen

Chunk 1 list, plus ImageNet mean `(0.485, 0.456, 0.406)` and std `(0.229, 0.224, 0.225)`.

## Findings

- `evaluate._denorm_preview` hardcodes the same ImageNet mean and std as `dataset.IMAGENET_MEAN` / `IMAGENET_STD`. Inverse of `imagenet_normalize`. Output is HxWx3 uint8.
- Two EM image contracts, not one loader:
  - Training: gray uint8, stack to RGB, ImageNet normalize. No percentile stretch (`_load_gray_uint8`, `to_rgb_uint8`, `imagenet_normalize`).
  - Inference: percentile 1–99 stretch to uint8, then stack (`normalise_em`, `load_em_rgb`). `EMPredictor.set_image_array` repeats that stack for 2-D arrays.
- `evaluate`, `EMPredictor.__init__`, and (chunk 3) `export_serve_checkpoint` each do `build_em_sam2` + `torch.load` + `load_state_dict` + `eval`. `evaluate` passes `weights_only=True` and treats the file as a raw state dict.
- `evaluate()` takes eleven keyword arguments (checkpoint, data root, volumes, split, image size, threshold, grids, workers). Same fields are parsed again in `main`.
- `validate._read_json_stats` repeats `_annotation_for_id`: scan `annotations` for `id == location_id`.
- `focal_loss` and `iou_prediction_loss` are `.mean()` of the per-sample functions. Keep them; callers want a scalar.
- Pixel IoU exists twice on purpose: NumPy `metrics.confusion` / `iou_dice_pr` (tp, fp, fn, eps `1e-6`) and Torch `iou_prediction_loss_per_sample` (sigmoid > 0.5, same eps). Do not merge across frameworks. Outputs must stay numerically aligned.
- `build_report` calls `index_volumes` twice (skip_missing false, then true), so ignore-mask moves can run twice.

## Carry forward

ImageNet constants, two image contracts, checkpoint load triple, annotation-id lookup, eval argument list.
