"""Seam NCC at layout (ds16) for every neighbour pair touching a tile set, for one or more mosaics.

usage: seam_table.py <tile,tile,...> <layout.mosaic> [<layout.mosaic> ...]   (RESCUE_SECTION_DIR as for place_tiles)
The hard check for a placement move: compare the moved tiles' seams before and after; undo a move whose median drops."""
import sys
import numpy as np
import place_tiles as pt


def seam_table(layout: str, tiles: set[int]) -> dict[tuple[int, int], float]:
    """NCC at layout for each neighbour pair with at least one tile in `tiles`."""
    ts = pt.tiles_of(layout)
    cache: dict = {}
    out: dict[tuple[int, int], float] = {}
    for t in sorted(tiles):
        if t not in ts:
            continue
        for n in pt.neighbours(ts, t):
            key = (min(t, n), max(t, n))
            if key in out:
                continue
            a, ma = pt.load(16, key[0], cache)
            b, mb = pt.load(16, key[1], cache)
            ncc, n_pad = pt.masked_ncc(a, ma, b, mb)
            e = pt.layout_offset(ts[key[0]], ts[key[1]], 16)
            out[key] = float(ncc[int(round(e[0])) % n_pad, int(round(e[1])) % n_pad])
    return out


if __name__ == "__main__":
    tiles = {int(x) for x in sys.argv[1].split(",")}
    tables = [(m, seam_table(m, tiles)) for m in sys.argv[2:]]
    keys = sorted(set().union(*[set(t) for _, t in tables]))
    print("pair      " + "  ".join(f"{m[-22:]:>22s}" for m, _ in tables))
    for k in keys:
        print(f"{k[0]:3d}-{k[1]:<3d}   " + "  ".join(f"{t.get(k, float('nan')):22.2f}" for _, t in tables))
    for m, t in tables:
        v = np.array([x for x in t.values() if np.isfinite(x)])
        print(f"{m}: n={len(v)} median {np.median(v):.2f} <=0.3: {(v <= 0.3).sum()}")
