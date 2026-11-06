"""Screen RC2 sections for the white-stripe problem (warming filament): a brightness step across one column seam.

usage: detect_white_stripe.py <out tsv> <section> [<section> ...]     (section numbers; use "all" for every section folder)
For each section, read Stage.mosaic and take the seam between the column holding tile 0 and the column to its right,
captured when the beam returns to the centre halfway through (tile N/2 + 1); without tile 0, the seam with the largest
tile-number gap. Only that seam and the next one (control) are read: the median
ratio of mean brightness between the overlap strips (Leveled ds16 tiles, blank tiles skipped). Score = |log(seam ratio)
- log(control ratio)|; over 0.2 is flagged. Known cases (2026-11-05, Raw8 ds4 test): 1140 and 1150 have a seam ratio 0.62-0.67 where the capture
resumes; 1145 and 1190 are clean (ratio 1.0-1.1 everywhere). Writes one row per section: section, tiles, seams tested,
resume seam (left column X), ratio at it, control ratio, score, flag.
Set NORNIR_COMPUTATIONAL_LIBRARY=numpy. Reads Y:\Volumes\RC2 only; writes nothing there."""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

import nornir_imageregistration

ROOT = "Y:/Volumes/RC2/TEM"
THRESHOLD = 0.2


def origins(section_dir: str) -> dict[int, tuple[float, float]]:
    """Tile number to stage origin (Y, X)."""
    mosaic = nornir_imageregistration.Mosaic.LoadFromMosaicFile(os.path.join(section_dir, "Stage.mosaic"))
    out = {}
    for name, transform in mosaic.ImageToTransform.items():
        p = transform.Transform(np.array([[0.0, 0.0]]))[0]
        p = np.asarray(p.get() if hasattr(p, "get") else p, dtype=np.float64)
        out[int(name[:-4])] = (float(p[0]), float(p[1]))
    return out


def strip(path: str, right: bool, width: int) -> np.ndarray:
    """Overlap strip of one tile with the top and bottom rows cropped."""
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    s = a[:, -width:] if right else a[:, :width]
    return s[10:-10]


def analyse(section: int) -> tuple:
    """Return the result row for one section."""
    d = f"{ROOT}/{section:04d}/TEM"
    try:
        pos = origins(d)
    except Exception as e:  # missing or unreadable Stage.mosaic
        return (section, 0, 0, "", "", "", "", f"error {type(e).__name__}")
    level = f"{d}/Leveled/TilePyramid/016"
    if not os.path.isdir(level):
        return (section, len(pos), 0, "", "", "", "", "no Leveled ds16")
    xs = sorted({round(x, -1) for _, x in pos.values()})
    by_col: dict[float, dict[int, int]] = {}
    for t, (y, x) in pos.items():
        by_col.setdefault(round(x, -1), {})[round(y / 10)] = t
    # The stripe sits on the seam where the capture resumed: neighbouring columns whose same-row tiles were taken
    # far apart in time, i.e. the largest tile-number gap. Read only that seam and the next one (control).
    seams = []
    for xl, xr in zip(xs[:-1], xs[1:]):
        if xr - xl > 4000:
            continue
        gaps = [abs(by_col[xr][y] - t) for y, t in by_col[xl].items() if y in by_col[xr]]
        if len(gaps) >= 5:
            seams.append((float(np.median(gaps)), xl, xr))
    if len(seams) < 2:
        return (section, len(pos), len(seams), "", "", "", "", "too few seams")
    # James's definition: the column holding tile 0 and the column to its right, captured when the beam returns to the
    # centre halfway through the capture (tile N/2 + 1). Fall back to the largest tile-number gap if tile 0 is absent.
    x0 = round(pos[0][1], -1) if 0 in pos else None
    at_tile0 = [k for k, seam in enumerate(seams) if seam[1] == x0]
    i = at_tile0[0] if at_tile0 else max(range(len(seams)), key=lambda k: seams[k][0])
    control = seams[i + 1] if i + 1 < len(seams) else seams[i - 1]

    def ratio(xl: float, xr: float) -> float | None:
        width = int(round((4080 - (xr - xl)) / 16)) - 3
        r = []
        for y, tl in by_col[xl].items():
            tr = by_col[xr].get(y)
            if tr is None:
                continue
            pl, pr = f"{level}/{tl:03d}.png", f"{level}/{tr:03d}.png"
            if not (os.path.exists(pl) and os.path.exists(pr)):
                continue
            a, b = strip(pl, True, width), strip(pr, False, width)
            if a.mean() >= 20 and b.mean() >= 20:
                r.append(b.mean() / a.mean())
        return float(np.median(r)) if len(r) >= 5 else None

    r_seam, r_control = ratio(seams[i][1], seams[i][2]), ratio(control[1], control[2])
    if r_seam is None or r_control is None:
        return (section, len(pos), 2, int(seams[i][1]), "", "", "", "too few tissue tiles on the seam")
    score = abs(float(np.log(r_seam) - np.log(r_control)))
    flag = "STRIPE?" if score > THRESHOLD else ""
    return (section, len(pos), 2, int(seams[i][1]), f"{r_seam:.3f}", f"{r_control:.3f}", f"{score:.3f}", flag)


def main() -> None:
    """Run the screen over the requested sections."""
    out = sys.argv[1]
    if sys.argv[2] == "all":
        sections = sorted(int(n) for n in os.listdir(ROOT) if n.isdigit())
    else:
        sections = [int(s) for s in sys.argv[2:]]
    with open(out, "w") as f:
        f.write("section\ttiles\tseams\tworst_seam_X\tratio_at_seam\tneighbour_median\tscore\tflag\n")
        with ProcessPoolExecutor(max_workers=6) as pool:
            for row in pool.map(analyse, sections, chunksize=1):
                f.write("\t".join(str(v) for v in row) + "\n")
                f.flush()
                print(*row, flush=True)


if __name__ == "__main__":
    main()
