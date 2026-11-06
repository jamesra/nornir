"""Detection-only study: do loose tiles (left unresolved by the translation pass) match a settled neighbour better when rotated?

usage: rotation_study.py <layout mosaic> <crosscheck tsv> <solve report> <out tsv> [max tiles, default 40] [tile ...]
For each loose tile (the 'unresolved' list of replace_tiles.py's report, or the tiles given), take its 2-4 nearest settled
neighbours (settled = every immediate-neighbour edge above the noise floor's p95 at the layout, no misplaced pair), and for
each pair:
  1. estimate the rotation with the log-polar StosBrute path (SliceToSliceRigidRegistration, method LogPolar,
     search_scale=False, no flip) on Leveled ds8 tiles;
  2. rotate the loose tile by that angle (both signs are tried; the better is kept) and take the best masked NCC over every
     translation at ds16, large overlaps included (the same masked NCC as crosscheck_pairs.py);
  3. compare with the best translation-only NCC for the pair from the crosscheck TSV.
Writes one row per pair plus a per-tile verdict: 'worth rotating' when the rotated NCC beats translation-only by
ROT_MARGIN, is above the noise floor's p95 + ROT_MARGIN, the angle is at least 1 degree, and two or more neighbours agree on
the angle within ANGLE_AGREE degrees. Writes no mosaic. Rotation is for the repair path only; translate stays rigid-free.

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy, CROSSCHECK_EXTREMA=1 and
NORNIR_COMPUTATIONAL_LIBRARY=numpy. See ../SKILL.md."""
import csv
import os
import re
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage

import nornir_imageregistration
from nornir_imageregistration.stos_brute import SliceToSliceRigidRegistration, SliceToSliceMethod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I does not add the script folder
import crosscheck_pairs as cc  # noqa: E402

SECTION = os.environ["RESCUE_SECTION_DIR"]
PITCH = 3590.0
ROT_MARGIN = 0.1
ANGLE_AGREE = 1.0
MAX_NEIGHBOURS = int(os.environ.get("ROTATION_NEIGHBOURS", "3"))  # log-polar at ds8 takes 15-130 s per pair


def positions(name: str) -> dict[int, np.ndarray]:
    """Tile number to origin (Y, X)."""
    out = {}
    for k, t in nornir_imageregistration.Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)).ImageToTransform.items():
        p = t.Transform(np.array([[0.0, 0.0]]))[0]
        out[int(k[:-4])] = np.asarray(p.get() if hasattr(p, "get") else p, dtype=np.float64)
    return out


def load(level: str, t: int) -> np.ndarray:
    """Leveled tile as float32."""
    return np.asarray(Image.open(os.path.join(SECTION, "Leveled", "TilePyramid", level, "%03d.png" % t)).convert("L"), dtype=np.float32)


def rotated_best_ncc(t: int, n: int, angle: float) -> float:
    """Best masked NCC of tile t rotated by angle against tile n, over every translation (ds16)."""
    a, m, *_ = cc.tile_ffts(t)
    ra = ndimage.rotate(a, angle, reshape=False, order=1)
    rm = ndimage.rotate(m, angle, reshape=False, order=0)
    ra = ra * rm
    key = -(t * 1000 + int(round(angle * 10)) % 1000) - 1
    cc._cache[key] = (ra, rm, cc.fft.rfft2(ra, (cc.N, cc.N)), cc.fft.rfft2(ra * ra, (cc.N, cc.N)), cc.fft.rfft2(rm, (cc.N, cc.N)))
    ncc, _ = cc.masked_ncc(n, key)
    cc._cache.pop(key, None)
    return float(ncc.max())


def main() -> None:
    layout, tsv, report, out = sys.argv[1:5]
    max_tiles = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    pos = positions(layout)
    rows = [{k: (float(v) if k not in ("A", "B") else int(v)) for k, v in r.items()} for r in csv.DictReader(open(tsv), delimiter="\t")]
    far = np.array([r["best_ncc"] for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) > 12000 and np.isfinite(r["best_ncc"])])
    p95, fmax = float(np.percentile(far, 95)), float(far.max())
    near = [r for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) < 1.3 * PITCH]
    edges: dict[int, list[float]] = {}
    for r in near:
        if np.isfinite(r["ncc_at_layout"]):
            for t in (r["A"], r["B"]):
                edges.setdefault(t, []).append(r["ncc_at_layout"])
    misplaced = {t for r in near if r["best_ncc"] > 0.6 and np.hypot(r["best_dy"] - r["layout_dy"], r["best_dx"] - r["layout_dx"]) > 640
                 for t in (r["A"], r["B"])}
    settled = {t for t, v in edges.items() if v and min(v) >= p95 and t not in misplaced}
    best_trans = {}
    for r in rows:
        best_trans[(r["A"], r["B"])] = best_trans[(r["B"], r["A"])] = r["best_ncc"]
    if len(sys.argv) > 6:
        loose = [int(x) for x in sys.argv[6:]]
    else:
        text = open(report).read()
        m = re.search(r"unresolved \(kept in place\): \[([^\]]*)\]", text)
        loose = [int(x) for x in m.group(1).split(",") if x.strip()] if m else []
        loose += [int(x) for x in re.findall(r"tile (\d+): added but unresolved", text)]
        # tear-edge tiles first: fewest good edges
        loose.sort(key=lambda t: sum(v >= p95 for v in edges.get(t, [])))
    loose = [t for t in loose if t in pos][:max_tiles]
    print(f"noise floor p95 {p95:.2f} max {fmax:.2f}; settled {len(settled)}; loose tiles studied {len(loose)}", flush=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["tile", "neighbour", "angle", "rotated_ncc", "translation_ncc", "seconds", "verdict"])
        for t in loose:
            cands = sorted((u for u in settled if u != t and np.linalg.norm(pos[u] - pos[t]) < 1.6 * PITCH),
                           key=lambda u: np.linalg.norm(pos[u] - pos[t]))[:MAX_NEIGHBOURS]
            if len(cands) < 2:  # fall back to the strongest translation partners among settled tiles
                cands = sorted((u for u in settled if (t, u) in best_trans), key=lambda u: -best_trans[(t, u)])[:MAX_NEIGHBOURS]
            results = []
            src8 = load("008", t)
            for n in cands:
                t0 = time.perf_counter()
                tgt8 = load("008", n)
                rec = SliceToSliceRigidRegistration(target_image=tgt8, source_image=src8, target_mask=tgt8 > 0, source_mask=src8 > 0,
                                                    AngleSearchRange=[0.0], MinOverlap=0.05, TestFlip=False, SingleThread=True,
                                                    method=SliceToSliceMethod.LogPolar, search_scale=False, use_gpu=False)
                angle = float(rec.angle)
                angle = (angle + 180.0) % 360.0 - 180.0
                score, sign = max((rotated_best_ncc(t, n, s * angle), s) for s in (1, -1))
                secs = time.perf_counter() - t0
                tr = best_trans.get((t, n), float("nan"))
                results.append((n, sign * angle, score, tr, secs))
            good = [r for r in results if abs(r[1]) >= 1.0 and r[2] >= p95 + ROT_MARGIN and r[2] >= (r[3] if np.isfinite(r[3]) else -1) + ROT_MARGIN]
            agree = max((sum(abs(g[1] - h[1]) <= ANGLE_AGREE for h in good) for g in good), default=0)
            verdict = "worth rotating" if agree >= 2 else "no"
            for n, ang, score, tr, secs in results:
                w.writerow([t, n, f"{ang:.2f}", f"{score:.3f}", f"{tr:.3f}", f"{secs:.1f}", verdict])
            f.flush()
            print(t, verdict, [(n, round(a, 1), round(s, 2), round(tr, 2), round(sec, 1)) for n, a, s, tr, sec in results], flush=True)


if __name__ == "__main__":
    main()
