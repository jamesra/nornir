"""Check a new section-to-section pose against the old registration carried through a mosaic repair.

usage: pose_check.py <old_mosaic> <new_mosaic> <old.stos> <old_ds> <new.stos> <new_ds> <new_mapped_mask.png> <mask_ds>
           [--write-carried <out.stos> <control.png> <mapped.png> <control_mask.png> <mapped_mask.png>]

A mosaic repair moves tiles but does not rotate the section, so the old registration (trusted, e.g. the old Grid32)
composed with the new->old mosaic mapping predicts where each point of the repaired section belongs in the control
section. For a grid of points inside the new mapped mask: new mosaic -> old mosaic (MosaicPointRemapper, shared
tiles) -> old .stos -> control, against new .stos -> control. Prints the median and p90 distance in control pixels
at the old stos's downsample. --write-carried also writes the carried pose itself (a mesh through the predicted
point pairs, at the old stos's downsample) as a .stos, to score it or to seed a refine. Assembled images are drawn from mosaic (0, 0), so image px * ds = mosaic px."""
import sys

import numpy as np
from PIL import Image

import nornir_imageregistration
from nornir_imageregistration.mosaic_remap import MosaicPointRemapper, RemapStatus


def stos_transform(path: str):
    """Transform of a .stos (mapped -> control)."""
    stos = nornir_imageregistration.StosFile.Load(path)
    return nornir_imageregistration.transforms.factory.LoadTransform(stos.Transform, pixelSpacing=1.0)


def main() -> None:
    """Compare predicted and new control positions."""
    old_m, new_m, old_s, old_ds, new_s, new_ds, mask, mask_ds = sys.argv[1:9]
    old_ds, new_ds, mask_ds = float(old_ds), float(new_ds), float(mask_ds)
    Image.MAX_IMAGE_PIXELS = None
    m = np.asarray(Image.open(mask).convert("L")) > 0
    step = max(1, min(m.shape) // 40)
    yy, xx = np.mgrid[step // 2:m.shape[0]:step, step // 2:m.shape[1]:step]
    keep = m[yy, xx]
    pts_full = np.stack([yy[keep], xx[keep]], 1).astype(np.float64) * mask_ds
    res = MosaicPointRemapper(new_m, old_m).remap(pts_full)  # new mosaic frame -> old mosaic frame
    ok = res.status == RemapStatus.MAPPED
    old_pts = res.new_points[ok]
    pred = np.asarray(stos_transform(old_s).Transform(old_pts / old_ds))
    got = np.asarray(stos_transform(new_s).Transform(pts_full[ok] / new_ds)) * (new_ds / old_ds)
    if "--write-carried" in sys.argv:
        out, cimg, mimg, cmask, mmask = sys.argv[sys.argv.index("--write-carried") + 1:][:5]
        pairs = np.hstack([pred, pts_full[ok] / old_ds])  # ControlY, ControlX, MappedY, MappedX
        t = nornir_imageregistration.transforms.MeshWithRBFFallback(pairs)
        nornir_imageregistration.StosFile.Create(cimg, mimg, t, cmask, mmask).Save(out, relative_paths=False)
        print("wrote", out)
    d = np.hypot(*(pred - got).T)
    print(f"points {ok.sum()} of {len(pts_full)}: distance to the old pose (control px at ds{old_ds:g}) "
          f"median {np.median(d):.1f}, p90 {np.percentile(d, 90):.1f}")


if __name__ == "__main__":
    main()
