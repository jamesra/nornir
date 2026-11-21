"""Pyre merge pack for loose pieces of a repaired mosaic: one image per piece in a shared frame, plus identity .stos.

usage: pyre_merge_pack.py <layout.mosaic> <downsample> <out folder> <name>=<tile,tile,...> [<name>=...]

Tiles not named in any piece form `main`. Every image (main.png, <name>.png and their *_mask.png) is assembled at the
given downsample on the same canvas (the whole mosaic's bounding box), so a piece's .stos starts as the identity:
it opens in Pyre with the piece exactly where the layout puts it now. Align the piece onto main in Pyre (rigid:
translate and, in the Composite view, rotate) and save the .stos; the rescue session then moves the piece's tiles by
that transform (scaled back to full resolution). Placement only: no tile is warped.

RESCUE_SECTION_DIR is the channel folder of the isolated copy, as for the other rescue scripts."""
import json
import os
import sys

import numpy as np
from PIL import Image

import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_imageregistration import Mosaic
from nornir_imageregistration.transforms.rigid import Rigid

SECTION = os.environ["RESCUE_SECTION_DIR"]


def assemble(mosaic: Mosaic, tiles: set[str], ds: int) -> tuple[np.ndarray, np.ndarray]:
    """Assemble the named tiles; returns (uint8 image, bool mask). AssembleImage draws from mosaic (0, 0)."""
    sub = Mosaic({k: v for k, v in mosaic.ImageToTransform.items() if k in tiles})
    ts = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        sub, image_folder=os.path.join(SECTION, "Leveled", "TilePyramid", "%03d" % ds), image_to_source_space_scale=ds)
    img, mask = ts.AssembleImage(target_space_scale=1.0 / ds)
    a = np.nan_to_num(np.asarray(img).astype(np.float32))
    if a.max() <= 1.0:
        a *= 255.0
    return np.clip(a, 0, 255).astype(np.uint8), np.asarray(mask) > 0


def main() -> None:
    """Write main/piece images, masks, identity .stos files and pieces.json."""
    layout, ds, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    pieces = {}
    for arg in sys.argv[4:]:
        name, ids = arg.split("=", 1)
        pieces[name] = {"%03d.png" % int(t) for t in ids.split(",")}
    os.makedirs(out, exist_ok=True)
    Image.MAX_IMAGE_PIXELS = None
    mosaic = Mosaic.LoadFromMosaicFile(os.path.join(SECTION, layout))
    every = set(mosaic.ImageToTransform)
    missing = set().union(*pieces.values()) - every
    if missing:
        raise SystemExit(f"tiles not in {layout}: {sorted(missing)}")
    full = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        mosaic, image_folder=os.path.join(SECTION, "Leveled", "TilePyramid", "%03d" % ds),
        image_to_source_space_scale=ds).TargetBoundingBox
    if min(full.MinY, full.MinX) < -64:
        raise SystemExit(f"{layout} starts below (0, 0) at ({full.MinY:.0f}, {full.MinX:.0f}); Assemble would crop it")
    origin = np.array([0.0, 0.0])  # every image is drawn from mosaic (0, 0), as Assemble does
    shape = (int(np.ceil(full.MaxY / ds)) + 2, int(np.ceil(full.MaxX / ds)) + 2)
    groups = {"main": every - set().union(*pieces.values()), **pieces}
    for name, tiles in groups.items():
        img, mask = assemble(mosaic, tiles, ds)
        canvas = np.zeros(shape, np.uint8)
        cmask = np.zeros(shape, np.uint8)
        h, w = min(img.shape[0], shape[0]), min(img.shape[1], shape[1])
        canvas[:h, :w] = img[:h, :w]
        cmask[:h, :w] = mask[:h, :w] * 255
        Image.fromarray(canvas).save(os.path.join(out, f"{name}.png"), compress_level=1)
        Image.fromarray(cmask).save(os.path.join(out, f"{name}_mask.png"), compress_level=1)
        print(name, len(tiles), "tiles", flush=True)
    for name in pieces:
        stos = nornir_imageregistration.StosFile.Create(
            os.path.join(out, "main.png"), os.path.join(out, f"{name}.png"), Rigid([0.0, 0.0], [0.0, 0.0], 0.0),
            os.path.join(out, "main_mask.png"), os.path.join(out, f"{name}_mask.png"))
        stos.Save(os.path.join(out, f"{name}.stos"))
    json.dump({"layout": os.path.join(SECTION, layout), "downsample": ds, "origin_full_res_yx": origin.tolist(),
               "canvas_shape": shape, "pieces": {k: sorted(int(t.split(".")[0]) for t in v) for k, v in pieces.items()}},
              open(os.path.join(out, "pieces.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
