"""Assemble a mosaic of the isolated copy at a downsample from its Leveled tile pyramid and save an 8-bit PNG.

usage: assemble_mosaic.py <mosaic name> <downsample> [output folder, default the section folder]
Writes <output folder>/<mosaic name without extension>_ds<N>.png. Assemble translated or grid mosaics, not Stage
(stage mosaics have negative Y and render as a sliver).

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import os
import sys
import time

import numpy as np
from PIL import Image

import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_imageregistration import Mosaic

SECTION = os.environ["RESCUE_SECTION_DIR"]


def main() -> None:
    """Assemble one mosaic and write the PNG."""
    name, ds = sys.argv[1], int(sys.argv[2])
    out_dir = sys.argv[3] if len(sys.argv) > 3 else SECTION
    Image.MAX_IMAGE_PIXELS = None
    ts = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)),
        image_folder=os.path.join(SECTION, "Leveled", "TilePyramid", "%03d" % ds), image_to_source_space_scale=ds)
    t0 = time.perf_counter()
    img, mask = ts.AssembleImage(target_space_scale=1.0 / ds)
    img = np.asarray(img)
    print("assembled", img.shape, img.dtype, f"{time.perf_counter() - t0:.0f}s",
          "coverage %.2f" % float(np.mean(np.asarray(mask) > 0)), flush=True)
    a = np.nan_to_num(img.astype(np.float32, copy=False))
    if a.max() <= 1.0:
        a *= 255.0
    out = os.path.join(out_dir, f"{os.path.splitext(name)[0]}_ds{ds}.png")
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(out, compress_level=1)
    print("wrote", out, os.path.getsize(out) // 2**20, "MB")


if __name__ == "__main__":
    main()
