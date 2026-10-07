# Chunk 8 — buildmanager pixel-facing operations

Files: `tile.py`, `filter.py`, `pruneobj.py`, `registration.py`, `block.py`.

## Already seen

`submit_bounded` / `_submit_bounded`.

## Findings

- `tile.py` is pipeline orchestration (filter nodes, pyramid levels, checksums) mixed with pixel work: `_load_image_pixels` (`PIL.Image.open`), `_crop_or_pad_to_shape`, `BuildTilesetLevel`, `BuildTilesetLevelWithPillow`. Orchestration stays in buildmanager. Pixel load, pad, and level shrink should call imageregistration after an output comparison. This path has been stable for years.
- `tile._submit_bounded` duplicates `poolutil.submit_bounded` (chunk 7). Same queue window. `tile.py` has no `on_in_flight` callback.
- `filter.py` and `registration.py` already call imageregistration (`TranslateMosaicFileToZeroOrigin`, assemble entry points) and mostly own volume nodes. That split is the one to keep.
- `registration.py` uses `from nornir_shared import *`. Out of scope for a move; worth cleaning when that file is next edited.

## Carry forward

Stable tile pyramid I/O must be compared before any loader change. Bounded submit belongs in pools.
