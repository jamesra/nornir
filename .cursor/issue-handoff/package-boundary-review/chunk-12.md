# Chunk 12 — imageregistration transforms

## Findings

- Transform types (`ITransform`, grid, RBF, triangulation, factory, converters) are the right home. Pyre and buildmanager already depend on them downward.
- No second transform implementation showed up in the segmentation package. `TileRect` / `CropWindow` are crop lattice records, not transforms. Leave them in segmentation until the mosaic-Y contract is explicit.
- `iRect` / `BoundingBox` / `iPoint` are the older spatial records. A later mapping from `TileRect` onto `iRect` is only safe after axis evidence. Do not propose that move now.

## Carry forward

Transforms stay. Crop lattice stays in segmentation.
