"""Placement-only tile fixes: measure, then rigidly move chosen tiles of a mosaic with every other tile pinned.

usage: place_tiles.py diagnose <layout.mosaic> <tile ids>          per-neighbour corrections for each tile
       place_tiles.py apply <layout.mosaic> <out.mosaic> <plan.json>  move groups, write mosaic + report

RESCUE_SECTION_DIR is the channel folder of the isolated copy (<copy>/TEM/<section>/TEM); tile images come from its
Leveled pyramid (ds16 for the windowed search, ds4 to sharpen the result). No grid step: a moved tile keeps its own
transform, translated rigidly in target space (James 2026-11-20: "stop doing grid as part of repair").

Correction for tile t against neighbour n: masked NCC of n vs t searched in a window of +-WINDOW full-res px around the
offset the layout gives them; the correction is (peak - layout offset), i.e. how far t should move relative to n.
A tile is misplaced when two or more neighbours above the noise floor agree on a correction; a correct tile shows
corrections near zero.

plan.json: {"groups": [{"tiles": [117, 119, 120]}, {"tiles": [46], "fixed": {"ref": 29, "layout": "<old.mosaic>"}}],
            "window": 600}
A group moves by one vector. "fixed" sets the group so that the offset of its FIRST tile to tile ref equals the one
in the given layout (for pairs the user says were right before) instead of measuring it; list that tile first."""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import fft

import nornir_imageregistration
import nornir_imageregistration.mosaic_tileset
from nornir_imageregistration import Mosaic

import crosscheck_pairs

SECTION = os.environ["RESCUE_SECTION_DIR"]
MIN_OVERLAP_FRAC = 0.03
FLOOR = 0.45          # NCC below this is treated as noise for a repeating-cell tissue at ds16
AGREE_PX = 48         # full-res px; two neighbour corrections within this agree


def load(ds: int, tid: int, cache: dict) -> tuple:
    """Tile image and validity mask (non-zero, extrema-masked like translate) at a pyramid level."""
    key = (ds, tid)
    if key not in cache:
        a = np.asarray(Image.open(os.path.join(SECTION, "Leveled", "TilePyramid", "%03d" % ds, "%03d.png" % tid)),
                       dtype=np.float32)
        valid = a > 0
        valid &= np.asarray(nornir_imageregistration.CreateExtremaMask(a, mask=valid, size_cutoff=0.01), dtype=bool)
        cache[key] = (a * valid, valid.astype(np.float32))
    return cache[key]


def masked_ncc(a, ma, b, mb):
    """NCC for every placement of b relative to a (shift s: b's origin at +s in a's frame), plus overlap count."""
    n_pad = fft.next_fast_len(2 * max(a.shape + b.shape))
    F = lambda x: fft.rfft2(x, (n_pad, n_pad))
    inv = lambda x: fft.irfft2(x, (n_pad, n_pad))
    fa, fa2, fma = F(a), F(a * a), F(ma)
    fb, fb2, fmb = F(b), F(b * b), F(mb)
    n = np.maximum(inv(fma * np.conj(fmb)), 0)
    sa, sb, sab = inv(fa * np.conj(fmb)), inv(fma * np.conj(fb)), inv(fa * np.conj(fb))
    saa, sbb = inv(fa2 * np.conj(fmb)), inv(fma * np.conj(fb2))
    min_n = MIN_OVERLAP_FRAC * a.size
    safe = np.where(n >= min_n, n, np.inf)
    num = sab - sa * sb / safe
    va, vb = saa - sa * sa / safe, sbb - sb * sb / safe
    ok = (n >= min_n) & (va > 4.0 * safe) & (vb > 4.0 * safe)
    ncc = np.where(ok, num / np.sqrt(np.where(ok, va * vb, 1.0)), -np.inf)
    return np.where(ncc > 1.0001, -np.inf, ncc), n_pad


def windowed_peak(ncc, n_pad, centre, radius):
    """Best NCC within +-radius (pyramid px) of centre (dy, dx); returns (ncc, dy, dx) or None."""
    cy, cx = int(round(centre[0])), int(round(centre[1]))
    r = int(np.ceil(radius))
    best = None
    for dy in range(cy - r, cy + r + 1):
        for dx in range(cx - r, cx + r + 1):
            v = ncc[dy % n_pad, dx % n_pad]
            if np.isfinite(v) and (best is None or v > best[0]):
                best = (float(v), dy, dx)
    return best


def layout_offset(ta, tb, ds):
    """Where the layout puts tb's image origin in ta's image frame, in pyramid px at ds (crosscheck_pairs method)."""
    crosscheck_pairs.DS = ds
    corner = np.array([tb.TargetSpaceBoundingBox.MinY - ta.TargetSpaceBoundingBox.MinY,
                       tb.TargetSpaceBoundingBox.MinX - ta.TargetSpaceBoundingBox.MinX])
    return np.array(crosscheck_pairs.expected_offset(ta, tb, corner))


def tiles_of(name: str) -> dict:
    """Tileset (tile id -> tile) of a mosaic in the section folder, ds16 images."""
    return nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
        Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)),
        image_folder=os.path.join(SECTION, "Leveled", "TilePyramid", "016"), image_to_source_space_scale=16)


def neighbours(ts, t, exclude=()):
    """Tiles whose target boxes overlap tile t by at least MIN_OVERLAP_FRAC of a tile."""
    bt = ts[t].TargetSpaceBoundingBox
    out = []
    for k, tile in ts.items():
        if k == t or k in exclude:
            continue
        b = tile.TargetSpaceBoundingBox
        oy, ox = min(bt.MaxY, b.MaxY) - max(bt.MinY, b.MinY), min(bt.MaxX, b.MaxX) - max(bt.MinX, b.MinX)
        if oy > 0 and ox > 0 and oy * ox >= MIN_OVERLAP_FRAC * bt.Width * bt.Height:
            out.append(k)
    return out


def correction(ts, n, t, window, cache):
    """(ncc_at_layout, best ncc, correction (dy, dx) in full-res px) for moving t relative to pinned n."""
    a, ma = load(16, n, cache)
    b, mb = load(16, t, cache)
    ncc, n_pad = masked_ncc(a, ma, b, mb)
    e16 = layout_offset(ts[n], ts[t], 16)
    at = ncc[int(round(e16[0])) % n_pad, int(round(e16[1])) % n_pad]
    pk = windowed_peak(ncc, n_pad, e16, window / 16.0)
    if pk is None:
        return float(at), None, None
    # sharpen at ds4 around the ds16 peak
    a4, ma4 = load(4, n, cache)
    b4, mb4 = load(4, t, cache)
    ncc4, n4 = masked_ncc(a4, ma4, b4, mb4)
    pk4 = windowed_peak(ncc4, n4, (pk[1] * 4, pk[2] * 4), 6)
    e4 = layout_offset(ts[n], ts[t], 4)
    if pk4 is None:
        return float(at), pk[0], (np.array(pk[1:]) - e16) * 16
    return float(at), pk[0], (np.array(pk4[1:]) - e4) * 4


def consensus(corrs):
    """Largest set of above-floor corrections agreeing within AGREE_PX; returns (vector, members) or (None, [])."""
    good = [(k, c) for k, nc, c in corrs if c is not None and nc >= FLOOR]
    best = (None, [])
    for k, c in good:
        members = [(k2, c2) for k2, c2 in good if np.hypot(*(c2 - c)) <= AGREE_PX]
        if len(members) > len(best[1]):
            best = (np.median([m[1] for m in members], axis=0), [m[0] for m in members])
    return best


def diagnose(layout: str, ids: list[int]) -> None:
    """Print each tile's per-neighbour corrections and their consensus."""
    ts = tiles_of(layout)
    cache = {}
    for t in ids:
        rows = []
        for n in neighbours(ts, t):
            at, nc, c = correction(ts, n, t, 600, cache)
            rows.append((n, nc if nc is not None else -1, c))
            cs = "-" if c is None else f"({c[0]:+.0f}, {c[1]:+.0f})"
            print(f"tile {t} vs {n}: ncc at layout {at:.2f}, windowed peak {nc if nc is not None else float('nan'):.2f}, correction {cs}")
        v, mem = consensus(rows)
        print(f"  tile {t}: consensus " + ("none" if v is None else f"({v[0]:+.0f}, {v[1]:+.0f}) from {mem}"), flush=True)


def apply(layout: str, out: str, plan_path: str) -> None:
    """Move each plan group rigidly (measured or fixed offset), pins held; write the mosaic and a report."""
    plan = json.load(open(plan_path))
    window = plan.get("window", 600)
    mosaic = Mosaic.LoadFromMosaicFile(os.path.join(SECTION, layout))
    report = []
    mosaic.SaveToMosaicFile(out)  # groups are measured against the layout as moved so far
    for g in plan["groups"]:
        ts = tiles_of(os.path.basename(out))
        group = g["tiles"]
        if "fixed" in g:
            old = tiles_of(g["fixed"]["layout"])
            ref = g["fixed"]["ref"]
            t = group[0]
            want = layout_offset(old[ref], old[t], 1)
            have = layout_offset(ts[ref], ts[t], 1)
            v, why = want - have, f"fixed to tile {ref}'s offset in {g['fixed']['layout']}"
        else:
            cache = {}
            rows = []
            for t in group:
                for n in neighbours(ts, t, exclude=group):
                    _, nc, c = correction(ts, n, t, window, cache)
                    rows.append((n, nc if nc is not None else -1, c))
            v, mem = consensus(rows)
            if v is None or len(mem) < 2:
                report.append(f"group {group}: not moved (fewer than 2 agreeing neighbours)")
                continue
            why = f"{len(mem)} agreeing neighbours {mem}"
        for t in group:
            mosaic.ImageToTransform["%03d.png" % t].TranslateFixed(np.array(v))
        mosaic.SaveToMosaicFile(out)
        report.append(f"group {group}: moved by (dy {v[0]:+.0f}, dx {v[1]:+.0f}) px; {why}")
        print(report[-1], flush=True)
    open(out + ".report.txt", "w").write("\n".join(report) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "diagnose":
        diagnose(sys.argv[2], [int(x) for x in sys.argv[3:]])
    elif sys.argv[1] == "apply":
        apply(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
