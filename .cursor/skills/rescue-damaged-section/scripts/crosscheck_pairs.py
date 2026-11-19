"""Masked NCC of every tile pair within RADIUS stage pitches of each other, at ds16; writes crosscheck_pairs.tsv.

Environment: CROSSCHECK_STAGE_MOSAIC (mosaic whose positions define neighbours), CROSSCHECK_LAYOUT (the layout
to test, a mosaic name in the section folder), CROSSCHECK_EXTREMA=1 (mask large black/white regions as translate
does), CROSSCHECK_OUT (output file name).

Every tile's FFTs are computed once into one shared array (nornir's create_shared_memory_array: /dev/shm, or a
temp-file memmap when it doesn't fit) that all workers read; each pair then costs only its six inverse FFTs. The
array is released when the run ends.

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy (<copy>/TEM/<section>/TEM). See ../SKILL.md."""
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image
from scipy import fft

SECTION = os.environ["RESCUE_SECTION_DIR"]
OUT = os.environ.get("RESCUE_WORK_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.environ["RESCUE_SECTION_DIR"]))))
IMG = os.path.join(SECTION, "Leveled", "TilePyramid", "016")
DS = 16
MIN_OVERLAP_PX = 3000  # ~4.6% of a ds16 tile; smaller overlaps are noise
RADIUS = 4.5           # in stage pitches
WORKERS = 16
LAYOUT = os.environ.get("CROSSCHECK_LAYOUT", "Translated_final.mosaic")

# Set in each worker by _attach: the shared FFT array (tiles x 3 x N x N//2+1), tile id -> row, padded size.
_ffts: np.ndarray | None = None
_slot: dict = {}
N = 0


def _attach(meta, slot: dict) -> None:
    import nornir_imageregistration
    global _ffts, _slot, N
    _ffts = nornir_imageregistration.ImageParamToNumpyImageArray(meta)
    _slot = slot
    N = _ffts.shape[2]


def fill(tid: int) -> float:
    """Write FFT of a*m, a^2*m and m for one tile into the shared array; return the tile's intensity std."""
    a = np.asarray(Image.open(os.path.join(IMG, "%03d.png" % tid)), dtype=np.float32)
    valid = a > 0
    if os.environ.get("CROSSCHECK_EXTREMA") == "1":
        # Large black/white regions are excluded the way translate does (size cutoff 1% of the tile).
        import nornir_imageregistration
        valid = valid & np.asarray(nornir_imageregistration.CreateExtremaMask(a, mask=valid, size_cutoff=0.01), dtype=bool)
    m = valid.astype(np.float32)
    a = a * m
    row = _ffts[_slot[tid]]
    row[0] = fft.rfft2(a, (N, N))
    row[1] = fft.rfft2(a * a, (N, N))
    row[2] = fft.rfft2(m, (N, N))
    return float(a[valid].std()) if valid.any() else 0.0


def masked_ncc(ta: int, tb: int):
    """NCC for every placement of tile b relative to tile a; shift s means b sits at +s in a's frame."""
    fa, fa2, fma = _ffts[_slot[ta]]
    fb, fb2, fmb = _ffts[_slot[tb]]
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
    ta, partners, exp, std = job   # exp: {tb: (dy, dx) expected shift in ds16 px}; std: {tile: intensity std}
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
                     std[ta], std[tb]))
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

    # Pad to twice the largest tile so every relative placement is scored without wrap-around.
    size = max(max(Image.open(os.path.join(IMG, f"{t:03d}.png")).size) for t in ids)
    n_pad = fft.next_fast_len(2 * size)
    shape = (len(ids), 3, n_pad, n_pad // 2 + 1)
    meta, ffts = nornir_imageregistration.create_shared_memory_array(shape, np.complex64, read_only=False)
    print(f"tile FFTs {ffts.nbytes / 2**30:.1f} GB ({type(meta).__name__})", flush=True)
    slot = {t: k for k, t in enumerate(ids)}

    workers = min(WORKERS, os.cpu_count() or 4)
    t0 = time.perf_counter()
    out = os.path.join(OUT, os.environ.get("CROSSCHECK_OUT", "crosscheck_pairs.tsv"))
    try:
        with open(out, "w", encoding="ascii") as f, \
                ProcessPoolExecutor(workers, initializer=_attach, initargs=(meta, slot)) as pool:
            # pool.map returns only after every tile is filled, so the pair phase never reads an unfilled row.
            std = dict(zip(ids, pool.map(fill, ids, chunksize=8)))
            print(f"tile FFTs done {time.perf_counter() - t0:.0f}s", flush=True)
            jobs = [(ta, partners, exp, {t: std[t] for t in (ta, *partners)}) for ta, partners, exp in jobs]
            f.write("A\tB\tbest_ncc\tbest_dy\tbest_dx\toverlap_frac\tncc_at_layout\tlayout_dy\tlayout_dx\tstdA\tstdB\n")
            for k, rows in enumerate(pool.map(work, jobs, chunksize=4)):
                for r in rows:
                    f.write("\t".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in r) + "\n")
                if k % 100 == 0:
                    print(f"{k}/{len(jobs)} {time.perf_counter() - t0:.0f}s", flush=True)
    finally:
        del ffts
        nornir_imageregistration.unlink_shared_memory(meta)
    print("done", time.perf_counter() - t0, "s ->", out, flush=True)


if __name__ == "__main__":
    main()
