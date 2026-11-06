"""Pairwise tile overlap statistics: how many tile pairs overlap by more than 15/25/50/90% of a tile.

usage: tile_overlap_stats.py <mosaic name> [...]. Nominal montage overlap is about 12%; a layout with pairs
over 25% has tiles piled on each other.

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import os, sys, time
import numpy as np
import nornir_imageregistration, nornir_imageregistration.mosaic_tileset
from nornir_imageregistration import Mosaic
SECTION = os.environ["RESCUE_SECTION_DIR"]
IMG = os.path.join(SECTION, "Leveled", "TilePyramid", "016")

def boxes(name):
    ts = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)), image_folder=IMG, image_to_source_space_scale=16)
    ids = sorted(ts)
    return ids, np.array([[ts[i].TargetSpaceBoundingBox.MinY, ts[i].TargetSpaceBoundingBox.MinX,
                           ts[i].TargetSpaceBoundingBox.MaxY, ts[i].TargetSpaceBoundingBox.MaxX] for i in ids])

def stats(name):
    ids, b = boxes(name)
    h, w = b[0, 2] - b[0, 0], b[0, 3] - b[0, 1]
    y0, x0, y1, x1 = (b[:, k] for k in range(4))
    oy = np.clip(np.minimum(y1[:, None], y1[None]) - np.maximum(y0[:, None], y0[None]), 0, None)
    ox = np.clip(np.minimum(x1[:, None], x1[None]) - np.maximum(x0[:, None], x0[None]), 0, None)
    frac = oy * ox / (h * w); np.fill_diagonal(frac, 0)
    iu = np.triu_indices(len(ids), 1); f = frac[iu]
    print(f"{name}: tiles {len(ids)} size {h:.0f}x{w:.0f} full-res px")
    for t in (0.9, 0.5, 0.25, 0.15):
        print(f"  pairs overlapping > {t:.0%} of a tile: {(f > t).sum()}")
    big = np.argwhere(np.triu(frac > 0.5, 1))
    for a, c in big[:8]:
        print("   atop:", ids[a], ids[c], f"{frac[a, c]:.0%}")
    return ids, b

def main():
    for n in sys.argv[1:]:
        stats(n)

if __name__ == "__main__":
    main()
