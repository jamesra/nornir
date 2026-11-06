"""Rebuild Leveled tiles at levels 1..256 from Raw8 level 1 the way AutolevelTiles + BuildTilePyramids do.

usage: rebuild_leveled_tiles.py validate <tile ids>   (rebuilds tiles that already have Leveled images and compares)
       rebuild_leveled_tiles.py <section folder to write into> <tile ids>
RESCUE_PRODUCTION_SECTION_DIR is the read-only production section folder (use forward slashes). MINMAX and GAMMA
are this section's Leveled filter values from its channel VolumeData.xml; edit them for another section. Use a
drive letter, not a UNC path, for the folder to write into (ConvertImagesInDictGpu drops a leading backslash)."""
import os, shutil, sys
import numpy as np
from PIL import Image
import nornir_imageregistration

RC2 = os.environ["RESCUE_PRODUCTION_SECTION_DIR"]
MINMAX, GAMMA = (120, 225), 0.795     # Leveled filter in the channel VolumeData.xml (1240); override with RESCUE_MINMAX="2,255" RESCUE_GAMMA=1
if "RESCUE_MINMAX" in os.environ:
    MINMAX = tuple(int(v) for v in os.environ["RESCUE_MINMAX"].split(","))
    GAMMA = float(os.environ["RESCUE_GAMMA"])
LEVELS = (1, 2, 4, 8, 16, 32, 64, 128, 256)


def build(tiles: list[int], out_root: str, src_root: str = RC2) -> None:
    """Convert Raw8 level 1 -> Leveled level 1, then shrink level by level into out_root/Leveled/TilePyramid/<level>."""
    convert = {}
    for t in tiles:
        src = os.path.join(out_root, "Raw8", "TilePyramid", "001", "%03d.png" % t)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        if not os.path.exists(src):
            shutil.copy2(os.path.join(src_root, "Raw8", "TilePyramid", "001", "%03d.png" % t), src)
        dst = os.path.join(out_root, "Leveled", "TilePyramid", "001", "%03d.png" % t)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        convert[src] = dst
    nornir_imageregistration.ConvertImagesInDictGpu(convert, MinMax=MINMAX, Gamma=GAMMA, InputBpp=8, OutputBpp=8)
    for up, this in zip(LEVELS[:-1], LEVELS[1:]):
        for t in tiles:
            i = os.path.join(out_root, "Leveled", "TilePyramid", "%03d" % up, "%03d.png" % t)
            o = os.path.join(out_root, "Leveled", "TilePyramid", "%03d" % this, "%03d.png" % t)
            os.makedirs(os.path.dirname(o), exist_ok=True)
            nornir_imageregistration.Shrink(i, o, float(up) / float(this))


def load(p):
    return np.asarray(Image.open(p))


def main() -> None:
    if sys.argv[1] == "validate":
        tmp = os.path.join(os.environ.get("RESCUE_WORK_DIR", "."), "leveled_validation")
        shutil.rmtree(tmp, ignore_errors=True)
        tiles = [int(x) for x in sys.argv[2:]]
        build(tiles, tmp)
        for t in tiles:
            for lvl in (1, 2, 4, 8, 16):
                mine = os.path.join(tmp, "Leveled", "TilePyramid", "%03d" % lvl, "%03d.png" % t)
                ref = os.path.join(RC2, "Leveled", "TilePyramid", "%03d" % lvl, "%03d.png" % t)
                if not os.path.exists(ref):
                    print(t, lvl, "no reference on RC2"); continue
                a, b = load(mine), load(ref)
                same = a.shape == b.shape
                d = np.abs(a.astype(int) - b.astype(int)) if same else None
                print(f"tile {t} level {lvl}: shape {a.shape} vs {b.shape}; identical {same and bool((d == 0).all())}; max diff {None if d is None else int(d.max())}; mean diff {None if d is None else round(float(d.mean()), 4)}")
    else:
        build([int(x) for x in sys.argv[2:]], sys.argv[1])


if __name__ == "__main__":
    main()
