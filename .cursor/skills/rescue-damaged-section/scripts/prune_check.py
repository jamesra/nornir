"""Check a Prune mosaic against its scores, find flat tiles it kept, and compare with the old Prune mosaic.

usage: prune_check.py <new prune mosaic> <old prune mosaic> <cutoff> [flat std limit, default 8]
Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM).
Prints: tiles in the new Prune mosaic against 'score >= cutoff'; tiles the 2015 prune kept that the new one drops
and the reverse; and the kept tiles whose Leveled ds16 image is flat (std below the limit over non-zero pixels),
which the flat-tile rule removes (see ../SKILL.md). Writes flat_tiles.txt beside the mosaics."""
import glob
import os
import sys

import numpy as np
from PIL import Image

import nornir_imageregistration

SECTION = os.environ["RESCUE_SECTION_DIR"]


def tiles(path: str) -> set[int]:
    return {int(k[:-4]) for k in nornir_imageregistration.MosaicFile.Load(path).ImageToTransformString}


def main() -> None:
    new_path, old_path, cutoff = os.path.join(SECTION, sys.argv[1]), os.path.join(SECTION, sys.argv[2]), float(sys.argv[3])
    limit = float(sys.argv[4]) if len(sys.argv) > 4 else 8.0
    score_file = glob.glob(os.path.join(SECTION, "Raw8", "PruneScores_*.txt"))[0]
    scores = {}
    for line in open(score_file):
        name, value = line.rsplit("\t", 1)
        scores[int(os.path.splitext(os.path.basename(name.strip()))[0])] = float(value)
    new, old = tiles(new_path), tiles(old_path)
    expected = {t for t, s in scores.items() if s >= cutoff}
    print(f"scores {len(scores)} tiles; new prune {len(new)}; score >= {cutoff}: {len(expected)}; "
          f"new == scores rule: {new == expected} (only in new {sorted(new - expected)}, only in rule {sorted(expected - new)})")
    print(f"old prune {len(old)}; kept by old, dropped by new: {len(old - new)}; dropped by old, kept by new: {len(new - old)}")
    flat = []
    for t in sorted(new):
        path = os.path.join(SECTION, "Leveled", "TilePyramid", "016", "%03d.png" % t)
        if not os.path.exists(path):
            print("no Leveled ds16 image for", t)
            continue
        a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
        nz = a[a > 0]
        std = float(nz.std()) if nz.size > 100 else 0.0
        if std < limit:
            flat.append((t, std, scores.get(t, float("nan"))))
    print(f"kept tiles that are flat (std < {limit}): {len(flat)}")
    for t, std, s in flat:
        print(f"  tile {t}: std {std:.1f}, prune score {s:.0f}")
    with open(os.path.join(SECTION, "flat_tiles.txt"), "w") as f:
        f.write("\n".join(str(t) for t, _, _ in flat) + "\n")


if __name__ == "__main__":
    main()
