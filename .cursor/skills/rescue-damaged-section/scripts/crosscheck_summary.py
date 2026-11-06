"""Summarise a crosscheck_pairs.py TSV: how well the layout agrees with the best correlation peaks.

usage: crosscheck_summary.py <tsv> [more tsv ...]
Immediate neighbours are pairs whose layout distance is under 1.3 tile pitches. For them it prints the median NCC at the
layout, how many score 0.3 or less, and the 'misplaced' pairs: best NCC above 0.6 with the peak more than 640 full-res px
away from the layout offset. Tiles that appear in several misplaced pairs are the likely culprits."""
import collections
import csv
import sys

import numpy as np

PITCH = 3590.0  # TSV offsets are full-resolution pixels


def summarise(path: str) -> None:
    """Print the layout-agreement summary for one TSV."""
    rows = list(csv.DictReader(open(path), delimiter="\t"))
    near = [r for r in rows if np.hypot(float(r["layout_dy"]), float(r["layout_dx"])) < 1.3 * PITCH]
    at_layout = np.array([float(r["ncc_at_layout"]) for r in near])
    at_layout = at_layout[np.isfinite(at_layout)]
    bad = [r for r in near if np.isfinite(float(r["ncc_at_layout"])) and float(r["ncc_at_layout"]) <= 0.3]
    misplaced = [r for r in near if float(r["best_ncc"]) > 0.6 and
                 np.hypot(float(r["best_dy"]) - float(r["layout_dy"]), float(r["best_dx"]) - float(r["layout_dx"])) > 640]
    count = collections.Counter(t for r in misplaced for t in (int(r["A"]), int(r["B"])))
    print(f"{path}: {len(near)} neighbour pairs, median NCC at layout {np.median(at_layout):.2f}, "
          f"{len(bad)} at or below 0.3, {len(misplaced)} misplaced (best NCC > 0.6, peak > 640 px from layout)")
    print("  tiles in most misplaced pairs:", count.most_common(12))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        summarise(p)
