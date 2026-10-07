# Chunk 11 — imageregistration image I/O, filters, assemble, mosaic, tile

## Already seen

PIL opens in stitch, pipeline, tile.py, mrc importer, trainer dataset, trainer infer. `LoadImage` is not a raw read.

## Findings

- `LoadImage` loads, converts to greyscale, applies a mask, and replaces extrema with noise matched to the unmasked median and std. Training crops and annotation stitch must not call it. Output would change.
- `pillow_helpers.get_image_file_dtype` opens a file only to read mode. There is no public “pixels only” loader next to it. That is the missing function if buildmanager is to stop calling `Image.open` itself.
- `SaveImage` / `SaveImage_JPeg2000` already own encoded writes for the registration stack. `stitch.write_png` and `assemble._save_rgb_png` are narrower. Point stitch at `SaveImage` only after a PNG parity check.
- `assemble_tiles.TilesToImage` composites transformed mosaic tiles. Segmentation `stitch_from_loader` copies unwarped tiles into a crop window. Do not merge them. Shared idea: bounded prefetch of tile files. The segmentation sweep already has its own shared-memory prefetch; leave it until a profile says the assemble prefetcher is the same contract.
- `image_to_uint8` is what Pyre uses at the GL boundary. Trainer uint8 conversion is a different contract (no noise fill).

## Carry forward

Raw load is missing. `LoadImage` stays the registration loader.
