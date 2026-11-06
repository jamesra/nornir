"""Grid-refine a whole translated mosaic (one connected piece) with the Mosaic pipeline's grid settings.

usage: refine_mosaic.py <input mosaic name> <output mosaic name>
Same settings as refine_half.py (cell 128, mesh 8x8, 10 iterations, threshold 0.25, ds4). Use refine_half.py when the
mosaic is two separate halves. Set NORNIR_COMPUTATIONAL_LIBRARY=numpy (the CuPy path crashed in the prewarp).

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import os
import sys
import time

import nornir_imageregistration

SECTION = os.environ["RESCUE_SECTION_DIR"]
IMG = os.path.join(SECTION, "Leveled", "TilePyramid", "004")


def main() -> None:
    """Refine the input mosaic and save the result."""
    src, out = os.path.join(SECTION, sys.argv[1]), os.path.join(SECTION, sys.argv[2])
    t0 = time.perf_counter()
    refined, diag = nornir_imageregistration.RefineGridMosaic(
        src, IMG, iterations=10, cell_size=(128, 128), mesh_shape=(8, 8), displacement_threshold=0.25,
        imageScale=0.25, return_diagnostics=True)
    refined.SaveToMosaicFile(out)
    print(f"{time.perf_counter() - t0:.0f}s passes {diag.iterations_completed} converged {diag.converged}", flush=True)
    print("mean displacement per pass:", [round(float(x), 3) for x in diag.average_displacement_per_iteration], flush=True)
    print("max displacement per pass:", [round(float(x), 2) for x in diag.max_displacement_per_iteration], flush=True)
    print("saved", out, flush=True)


if __name__ == "__main__":
    main()
