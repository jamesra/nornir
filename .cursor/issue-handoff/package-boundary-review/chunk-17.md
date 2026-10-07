# Chunk 17 — volumemodel, volumecontroller, web, dashboard, dm4

## Findings

- `nornir_volumecontroller` depends on imageregistration for mosaic bounds and downsample (`ChangeImageDownsample`, `Mosaic.LoadFromMosaicFile`, `BoundingBox`). That is the allowed direction. No second image stack.
- `nornir_volumemodel/model_old.py` has commented imageregistration imports. Dead comments, not a live dependency. No pixel issue.
- `dm4` reads the DM4 tag tree and arrays. It does not call Pillow or imageregistration. File format stays here. Buildmanager’s DM4 importer should keep calling this package rather than re-decoding tags.
- Web and dashboard were not carrying pixel algorithms or a copy of the crop catalog. No move.

## Carry forward

None. End of the chunk list.
