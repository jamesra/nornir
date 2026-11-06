"""Refine one connected half of a translated mosaic with RefineGridMosaic, using the Mosaic pipeline's grid settings.

usage: refine_half.py left|right. Reads Translated_v2.mosaic and its report (edit the names for another run).
Set NORNIR_COMPUTATIONAL_LIBRARY=numpy: the CuPy path crashed in the grid-refine prewarp (2026-11-04).

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import json, os, sys, time
import numpy as np
import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_imageregistration import Mosaic

M = os.environ["RESCUE_SECTION_DIR"]
IMG = os.path.join(M, "Leveled", "TilePyramid", "004")


def half_tiles() -> dict[str, set[int]]:
    rep = json.load(open(os.path.join(M, "Translated_v2_TranslateReport.json")))
    ts = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        Mosaic.LoadFromMosaicFile(os.path.join(M, "Translated_v2.mosaic")), image_folder=IMG, image_to_source_space_scale=4)
    groups = [set(g) for g in rep["matched_groups"]]
    mean_x = [np.mean([ts[t].TargetSpaceBoundingBox.MinX for t in g]) for g in groups]
    left = groups[int(np.argmin(mean_x))]
    return {"left": left, "right": next(g for g in groups if g is not left)}


def main() -> None:
    half = sys.argv[1]
    keep = half_tiles()[half]
    mf = nornir_imageregistration.MosaicFile.Load(os.path.join(M, "Translated_v2.mosaic"))
    for fn in list(mf.ImageToTransformString):
        if int(os.path.splitext(fn)[0]) not in keep:
            del mf.ImageToTransformString[fn]
    src = os.path.join(M, f"Translated_v2_{half}.mosaic"); mf.Save(src)
    print(half, "tiles", len(mf.ImageToTransformString), flush=True)
    t0 = time.perf_counter()
    refined, diag = nornir_imageregistration.RefineGridMosaic(
        src, IMG, iterations=10, cell_size=(128, 128), mesh_shape=(8, 8), displacement_threshold=0.25,
        imageScale=0.25, return_diagnostics=True)
    out = os.path.join(M, f"Grid_v2_{half}.mosaic")
    refined.SaveToMosaicFile(out)
    print(f"{half}: {time.perf_counter() - t0:.0f}s passes {diag.iterations_completed} converged {diag.converged}", flush=True)
    print("  mean displacement per pass:", [round(float(x), 3) for x in diag.average_displacement_per_iteration], flush=True)
    print("  max displacement per pass:", [round(float(x), 2) for x in diag.max_displacement_per_iteration], flush=True)
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
