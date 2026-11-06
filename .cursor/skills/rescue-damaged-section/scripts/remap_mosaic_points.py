"""Rescue annotations for a repaired mosaic: map mosaic-space points from the old mosaic's coordinates to the new.

usage: remap_mosaic_points.py <old.mosaic> <new.mosaic> <points.csv> <out prefix> [--order xy|yx] [--tile-shape H W]
       remap_mosaic_points.py <old.mosaic> <new.mosaic> --sample <out prefix>

The CSV needs a header with columns id, x, y (any other columns are kept). x, y are full-resolution mosaic pixels
in Viking order (X, Y); --order yx reads them as (Y, X). Writes <out prefix>.csv (every input column plus new_x,
new_y, tile, status, shift) and <out prefix>.report.txt, which install_rescue.py accepts as --annotation-rescue-report.

Points are mapped through the tiles both mosaics contain (nornir_imageregistration.mosaic_remap), using the tile whose
centre is closest where tiles overlap, as Assemble does. Points that no shared tile covers get status
NO_SHARED_TILE and an empty new position: they must be looked at by hand, not guessed. --sample maps a regular grid of
points plus every tile centre, then maps them back, to show how well the two mosaics agree; use it when you do not yet
have the annotation export. This script only maps mosaic-space positions. Volume-space positions are recomputed
afterwards from the volume transform, which changes again when the section is re-registered.
"""
import argparse
import csv
import datetime
import hashlib
import os

import numpy as np

import nornir_imageregistration
from nornir_imageregistration.mosaic_remap import MosaicPointRemapper, RemapStatus


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _report(lines: list[str], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def run_csv(args) -> None:
    tile_shape = tuple(args.tile_shape) if args.tile_shape else None
    remapper = MosaicPointRemapper(args.old, args.new, tile_shape=tile_shape)
    with open(args.points, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("The points file has no rows")
    columns = {c.lower(): c for c in rows[0]}
    for needed in ("id", "x", "y"):
        if needed not in columns:
            raise SystemExit(f"The points file needs a column named {needed}; it has {list(rows[0])}")
    xy = np.array([[float(r[columns["x"]]), float(r[columns["y"]])] for r in rows])
    yx = xy if args.order == "yx" else xy[:, ::-1]
    result = remapper.remap(yx)
    new_yx = result.new_points
    new_xy = new_yx if args.order == "yx" else new_yx[:, ::-1]
    with open(args.out + ".csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(list(rows[0]) + ["new_x", "new_y", "tile", "status", "shift", "overlap_disagreement"])
        for row, p, tile, status, shift, disagree in zip(rows, new_xy, result.tile_names, result.status, result.shift,
                                                         result.overlap_disagreement):
            writer.writerow(list(row.values()) + [("" if np.isnan(p[0]) else f"{p[0]:.2f}"), ("" if np.isnan(p[1]) else f"{p[1]:.2f}"),
                                                  tile or "", RemapStatus(int(status)).name, "" if np.isnan(shift) else f"{shift:.1f}",
                                                  "" if np.isnan(disagree) else f"{disagree:.1f}"])
    summary = result.summary()
    unmapped = [r[columns["id"]] for r, s in zip(rows, result.status) if s == RemapStatus.NO_SHARED_TILE]
    _report([f"Annotation rescue report, {datetime.datetime.now():%Y-%m-%d %H:%M}",
             f"old mosaic: {args.old} (sha256 {_sha(args.old)})", f"new mosaic: {args.new} (sha256 {_sha(args.new)})",
             f"points file: {args.points}", f"coordinate order in the file: {args.order}",
             f"shared tiles: {len(remapper.names)}",
             f"points {summary['points']}: mapped {summary['mapped']}, extrapolated {summary['extrapolated']}, "
             f"no shared tile {summary['no_shared_tile']}",
             f"shift (px): median {summary['shift_median']:.1f}, p95 {summary['shift_p95']:.1f}, max {summary['shift_max']:.1f}",
             f"points in an overlap of two shared tiles: {summary['in_overlap']}; the two tiles put them more than 5 px apart "
             f"in the new mosaic for {summary['overlap_disagree_gt5px']} (p95 {summary['overlap_disagree_p95']:.1f} px)",
             f"ids with no shared tile (review by hand): {unmapped[:50]}{' ...' if len(unmapped) > 50 else ''}"],
            args.out + ".report.txt")


def run_sample(args) -> None:
    remapper = MosaicPointRemapper(args.old, args.new)
    forward_back = MosaicPointRemapper(args.new, args.old)
    pts = np.concatenate([remapper._centre, remapper._lo, remapper._hi])
    grid_y = np.linspace(remapper._lo[:, 0].min(), remapper._hi[:, 0].max(), 40)
    grid_x = np.linspace(remapper._lo[:, 1].min(), remapper._hi[:, 1].max(), 40)
    pts = np.concatenate([pts, np.array([[y, x] for y in grid_y for x in grid_x])])
    forward = remapper.remap(pts)
    ok = forward.status != RemapStatus.NO_SHARED_TILE
    back = forward_back.remap(forward.new_points[ok])
    cycle = np.linalg.norm(back.new_points - pts[ok], axis=1)
    mapped_only = forward.status[ok] == RemapStatus.MAPPED
    cycle = cycle[mapped_only & ~np.isnan(cycle)]
    summary = forward.summary()
    _report([f"Annotation rescue SAMPLE report (no annotation file), {datetime.datetime.now():%Y-%m-%d %H:%M}",
             f"old mosaic: {args.old} (sha256 {_sha(args.old)})", f"new mosaic: {args.new} (sha256 {_sha(args.new)})",
             f"shared tiles: {len(remapper.names)}",
             f"sample points {summary['points']}: mapped {summary['mapped']}, extrapolated {summary['extrapolated']}, "
             f"no shared tile {summary['no_shared_tile']}",
             f"shift (px): median {summary['shift_median']:.1f}, p95 {summary['shift_p95']:.1f}, max {summary['shift_max']:.1f}",
             f"points in an overlap of two shared tiles: {summary['in_overlap']}; the two tiles put them more than 5 px apart "
             f"in the new mosaic for {summary['overlap_disagree_gt5px']} (p95 {summary['overlap_disagree_p95']:.1f} px)",
             f"old -> new -> old error for MAPPED points (px): median {np.median(cycle):.2f}, p95 {np.percentile(cycle, 95):.2f}; "
             f"above 5 px: {(cycle > 5).sum()} of {len(cycle)}. Large values are points where the new mosaic's closest-centre tile "
             f"differs from the old one (overlaps), not a mapping error"],
            args.out + ".report.txt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old")
    parser.add_argument("new")
    parser.add_argument("points", nargs="?")
    parser.add_argument("out", nargs="?")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--order", choices=("xy", "yx"), default="xy")
    parser.add_argument("--tile-shape", nargs=2, type=float)
    args = parser.parse_args()
    if args.sample:  # usage: old new --sample <out prefix>; argparse puts the prefix in `points`
        args.out = args.points
        run_sample(args)
    else:
        if not args.points or not args.out:
            parser.error("points.csv and out prefix are required (or use --sample <out prefix>)")
        run_csv(args)


if __name__ == "__main__":
    main()
