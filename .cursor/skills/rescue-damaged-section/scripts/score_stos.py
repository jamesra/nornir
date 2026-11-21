"""Score a section-to-section registration: masked, contrasted NCC of control vs mapped warped by the .stos.

usage: score_stos.py <pair.stos> <control.png> <control_mask.png> <mapped.png> <mapped_mask.png> [overlay.png]

Follows the Stos-overlay-contrast rule: Leveled (not Blob) images at the stos's downsample with their Assemble
masks (STOS_IMAGE_SHRINK=2 scores a ds64 brute on ds32 images); each image is high-passed (image minus a Gaussian, sigma 25 px) and stretched over its masked tissue
(1-99 percentile) before the NCC, which counts only pixels inside both masks. Prints the NCC and the overlap
fraction; with an overlay path, writes a magenta (mapped) / green (control) overlay of the contrasted images."""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

import nornir_imageregistration
import nornir_imageregistration.assemble


SHRINK = int(os.environ.get("STOS_IMAGE_SHRINK", "1"))  # e.g. 2: score a ds64 .stos on ds32 images


def load(path: str) -> np.ndarray:
    """Greyscale image as float32, shrunk by STOS_IMAGE_SHRINK."""
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(path).convert("L")
    if SHRINK > 1:
        im = im.resize((im.width // SHRINK, im.height // SHRINK), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32)


def contrast(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """High-pass, then stretch to 0..1 over the masked tissue."""
    hp = img - ndimage.gaussian_filter(img, 25)
    vals = hp[mask]
    if vals.size == 0:
        return np.zeros_like(hp)
    lo, hi = np.percentile(vals, [1, 99])
    return np.clip((hp - lo) / max(hi - lo, 1e-6), 0, 1)


def main() -> None:
    """Warp mapped image and mask into control space and score."""
    stos_path, cp, cmp_, mp, mmp = sys.argv[1:6]
    stos = nornir_imageregistration.StosFile.Load(stos_path)
    transform = nornir_imageregistration.transforms.factory.LoadTransform(stos.Transform, pixelSpacing=1.0)
    ctrl, cmask = load(cp), load(cmp_) > 0
    mapped, mmask = load(mp), load(mmp) > 0
    warped = np.asarray(nornir_imageregistration.assemble.TransformStos(transform, fixedImage=ctrl, warpedImage=mapped))
    wmask = np.asarray(nornir_imageregistration.assemble.TransformStos(
        transform, fixedImage=ctrl, warpedImage=mmask.astype(np.float32))) > 0.5
    if hasattr(warped, "get"):
        warped = warped.get()
    both = cmask & wmask & (warped > 0)
    a, b = contrast(ctrl, cmask)[both], contrast(warped.astype(np.float32), wmask)[both]
    ncc = float(np.corrcoef(a, b)[0, 1]) if a.size > 100 else float("nan")
    print(f"ncc {ncc:.3f} overlap {both.sum() / max(cmask.sum(), 1):.3f}")
    if len(sys.argv) > 6:
        c, w = contrast(ctrl, cmask), contrast(warped.astype(np.float32), wmask)
        rgb = np.stack([w, c, w], -1) * 255
        Image.fromarray(rgb.astype(np.uint8)).save(sys.argv[6])


if __name__ == "__main__":
    main()
