"""Masked NCC of every tile pair within RADIUS stage pitches of each other, at ds16; writes crosscheck_pairs.tsv.

Environment: CROSSCHECK_STAGE_MOSAIC (mosaic whose positions define neighbours), CROSSCHECK_LAYOUT (the layout
to test, a mosaic name in the section folder), CROSSCHECK_EXTREMA=1 (mask large black/white regions as translate
does), CROSSCHECK_OUT (output file name).

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image
from scipy import fft

SECTION = os.environ["RESCUE_SECTION_DIR"]
OUT = os.environ.get("RESCUE_WORK_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.environ["RESCUE_SECTION_DIR"]))))
IMG = os.path.join(SECTION, "Leveled", "TilePyramid", "016")
DS = 16
N = 512                # padded size for 255 px tiles
MIN_OVERLAP_PX = 3000  # ~4.6% of a ds16 tile; smaller overlaps are noise
RADIUS = 4.5           # in stage pitches
LAYOUT = os.environ.get("CROSSCHECK_LAYOUT", "Translated_final.mosaic")
_cache: dict = {}


def tile_ffts(tid: int):
    """Return (image, mask, FFT of a*m, a^2*m, m) for a tile, cached per worker."""
    if tid not in _cache:
        a = np.asarray(Image.open(os.path.join(IMG, "%03d.png" % tid)), dtype=np.float32)
        valid = a > 0
        if os.environ.get("CROSSCHECK_EXTREMA") == "1":
            # Large black/white regions are excluded the way translate does (size cutoff 1% of the tile).
            import nornir_imageregistration
            valid = valid & np.asarray(nornir_imageregistration.CreateExtremaMask(a, mask=valid, size_cutoff=0.01), dtype=bool)
        m = valid.astype(np.float32)
        a = a * m
        _cache[tid] = (a, m, fft.rfft2(a, (N, N)), fft.rfft2(a * a, (N, N)), fft.rfft2(m, (N, N)))
        if len(_cache) > 600:
            _cache.pop(next(iter(_cache)))
    return _cache[tid]


def masked_ncc(ta: int, tb: int):
    """NCC for every placement of tile b relative to tile a; shift s means b sits at +s in a's frame."""
    _, _, fa, fa2, fma = tile_ffts(ta)
    _, _, fb, fb2, fmb = tile_ffts(tb)
    inv = lambda x: fft.irfft2(x, (N, N))
    n = np.maximum(inv(fma * np.conj(fmb)), 0)
    sa = inv(fa * np.conj(fmb))
    sb = inv(fma * np.conj(fb))
    sab = inv(fa * np.conj(fb))
    saa = inv(fa2 * np.conj(fmb))
    sbb = inv(fma * np.conj(fb2))
    safe = np.where(n >= MIN_OVERLAP_PX, n, np.inf)
    num = sab - sa * sb / safe
    var_a = saa - sa * sa / safe
    var_b = sbb - sb * sb / safe
    # intensity std below ~2 grey levels in the overlap is flat resin or background: NCC is meaningless there
    ok = (n >= MIN_OVERLAP_PX) & (var_a > 4.0 * safe) & (var_b > 4.0 * safe)
    den = np.sqrt(np.where(ok, var_a * var_b, 1.0))
    ncc = np.where(ok, num / den, -np.inf)
    ncc = np.where(ncc > 1.0001, -np.inf, ncc)
    return ncc, n


def work(job):
    ta, partners, exp = job   # exp: {tb: (dy, dx) expected shift in ds16 px}
    rows = []
    for tb in partners:
        ncc, n = masked_ncc(ta, tb)
        iy, ix = np.unravel_index(int(np.argmax(ncc)), ncc.shape)
        best = float(ncc[iy, ix])
        dy = iy if iy < N // 2 else iy - N
        dx = ix if ix < N // 2 else ix - N
        ey, ex = exp[tb]
        ey_i, ex_i = int(round(ey)) % N, int(round(ex)) % N
        at_expected = float(ncc[ey_i, ex_i])
        rows.append((ta, tb, best, dy * DS, dx * DS, float(n[iy, ix]) / (255 * 255), at_expected, ey * DS, ex * DS,
                     float(tile_ffts(ta)[0][tile_ffts(ta)[1] > 0].std()), float(tile_ffts(tb)[0][tile_ffts(tb)[1] > 0].std())))
    return rows


def main() -> None:
    import nornir_imageregistration.mosaic_tileset
    from nornir_imageregistration import Mosaic

    def centres(name):
        ts = nornir_imageregistration.mosaic_tileset.CreateFromMosaic(
            Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)), image_folder=IMG, image_to_source_space_scale=DS)
        ids = sorted(ts)
        c = np.array([[ts[i].TargetSpaceBoundingBox.MinY, ts[i].TargetSpaceBoundingBox.MinX] for i in ids])
        return ids, c

    # The pre-2026-11-04 pruned mosaic (moved to the backup folder), so the pair list matches the earlier run.
    ids, stage = centres(os.environ["CROSSCHECK_STAGE_MOSAIC"])
    _, layout = centres(LAYOUT)
    d = np.linalg.norm(stage[:, None] - stage[None], axis=2)
    pitch = np.median(np.sort(d, axis=1)[:, 1])
    jobs = []
    for i, ta in enumerate(ids):
        near = [j for j in range(i + 1, len(ids)) if d[i, j] <= RADIUS * pitch]
        if near:
            exp = {ids[j]: tuple((layout[j] - layout[i]) / DS) for j in near}
            jobs.append((ta, [ids[j] for j in near], exp))
    print("tiles", len(ids), "pairs", sum(len(j[1]) for j in jobs), "pitch", pitch, flush=True)
    workers = max(1, (os.cpu_count() or 4) // 2)
    t0 = time.perf_counter()
    out = os.path.join(OUT, os.environ.get("CROSSCHECK_OUT", "crosscheck_pairs.tsv"))
    with open(out, "w", encoding="ascii") as f, ProcessPoolExecutor(workers) as pool:
        f.write("A\tB\tbest_ncc\tbest_dy\tbest_dx\toverlap_frac\tncc_at_layout\tlayout_dy\tlayout_dx\tstdA\tstdB\n")
        for k, rows in enumerate(pool.map(work, jobs, chunksize=4)):
            for r in rows:
                f.write("\t".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in r) + "\n")
            if k % 100 == 0:
                print(f"{k}/{len(jobs)} {time.perf_counter() - t0:.0f}s", flush=True)
    print("done", time.perf_counter() - t0, "s ->", out, flush=True)


if __name__ == "__main__":
    main()
