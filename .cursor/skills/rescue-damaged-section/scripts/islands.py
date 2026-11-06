"""Unresolved tiles: search them against every tile, then lay out what is left as islands outside the main body.

usage: islands.py <layout mosaic> <layout crosscheck tsv> <solve report> <out mosaic> <islands tsv> [workers, default 6]
1. Wide search: every tile the solve left unresolved is correlated (masked NCC, ds16, extrema masked, large overlaps
   allowed) with every tile of the section. A tile is placed when 3 or more different settled tiles (settled: every
   immediate-neighbour edge above the noise floor's p95 at the layout, no misplaced pair) put it at the same spot
   (within TOL px), each peak at least ACCEPT above the floor (max(0.6, far-pair p95) + 0.05), the rule replace_tiles.py
   uses for far moves.
2. Islands: the tiles still unresolved are linked by their mutual pairs within RADIUS stage pitches when the peak is
   above the acceptance level and its offset agrees with the stage offset within half a pitch (or the peak beats the
   noise floor's maximum by 0.05). Connected components are laid out along a maximum spanning tree from their
   lowest-numbered tile and placed in a row below the main body's bounding box, one pitch apart; tiles with no confirmed
   pair (singletons) go in a row after that.
3. Each island is then tried as one rigid group (3+ members spread over a pitch agreeing within 30 px on one
   offset against settled tiles, then the group edge check); <out mosaic> with '_placed' is that variant.
Writes <out mosaic> (a review mosaic, not a repair output) and <islands tsv>: island id, tiles, internal median NCC,
stage position of the anchor, and the island's best NCC/offset against the main body even when below the threshold.

Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy and NORNIR_COMPUTATIONAL_LIBRARY=numpy."""
import csv
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image
from scipy import fft

import nornir_imageregistration

SECTION = os.environ["RESCUE_SECTION_DIR"]
IMG = os.path.join(SECTION, "Leveled", "TilePyramid", "016")
DS = 16
N = 512
MIN_OVERLAP_PX = 3000
PITCH = 3590.0
TILE_PX = 4080.0
RADIUS = 4.5
TOL = 64.0           # px; ds16 peaks are quantised to 16 px
MARGIN = 0.05
MIN_AGREE = 3
GROUP_TOL = 30.0     # px; members of a rigid island must agree this closely on its offset
_spec: dict[int, tuple] = {}


def spectra(tid: int) -> tuple:
    """FFTs (complex64) of a*m, a^2*m and m for a ds16 tile, extrema masked as translate does."""
    if tid not in _spec:
        a = np.asarray(Image.open(os.path.join(IMG, "%03d.png" % tid)), dtype=np.float32)
        valid = a > 0
        valid &= np.asarray(nornir_imageregistration.CreateExtremaMask(a, mask=valid, size_cutoff=0.01), dtype=bool)
        m = valid.astype(np.float32)
        a = a * m
        _spec[tid] = tuple(fft.rfft2(x, (N, N)).astype(np.complex64) for x in (a, a * a, m))
    return _spec[tid]


def best_peak(ta: int, tb: int) -> tuple[float, float, float]:
    """Best masked NCC of tile b against tile a and the shift (dy, dx, full-res px) where b sits in a's frame."""
    fa, fa2, fma = spectra(ta)
    fb, fb2, fmb = spectra(tb)
    inv = lambda x: fft.irfft2(x, (N, N))
    n = np.maximum(inv(fma * np.conj(fmb)), 0)
    sa, sb = inv(fa * np.conj(fmb)), inv(fma * np.conj(fb))
    sab, saa, sbb = inv(fa * np.conj(fb)), inv(fa2 * np.conj(fmb)), inv(fma * np.conj(fb2))
    safe = np.where(n >= MIN_OVERLAP_PX, n, np.inf)
    num = sab - sa * sb / safe
    va, vb = saa - sa * sa / safe, sbb - sb * sb / safe
    ok = (n >= MIN_OVERLAP_PX) & (va > 4.0 * safe) & (vb > 4.0 * safe)
    ncc = np.where(ok, num / np.sqrt(np.where(ok, va * vb, 1.0)), -np.inf)
    ncc = np.where(ncc > 1.0001, -np.inf, ncc)
    iy, ix = np.unravel_index(int(np.argmax(ncc)), ncc.shape)
    dy = iy if iy < N // 2 else iy - N
    dx = ix if ix < N // 2 else ix - N
    return float(ncc[iy, ix]), float(dy * DS), float(dx * DS)


def work(job: tuple[list[int], list[int]]) -> list[tuple]:
    """Correlate each loose tile with each tile of a chunk; returns (loose, other, ncc, dy, dx) with other in loose's frame."""
    chunk, loose = job
    out = []
    for b in chunk:
        for u in loose:
            if u != b:
                out.append((u, b) + best_peak(u, b))
        _spec.pop(b, None) if b not in loose else None
    return out


def ncc_at(ta: int, tb: int, d: np.ndarray) -> float:
    """Masked NCC of tile b placed at d (full-res px) in tile a's frame; -inf without overlap."""
    if np.abs(d / DS).max() >= N // 2 - 1:
        return -np.inf
    fa, fa2, fma = spectra(ta)
    fb, fb2, fmb = spectra(tb)
    iy, ix = int(round(d[0] / DS)) % N, int(round(d[1] / DS)) % N
    inv = lambda x: float(fft.irfft2(x, (N, N))[iy, ix])
    n = max(inv(fma * np.conj(fmb)), 0.0)
    if n < MIN_OVERLAP_PX:
        return -np.inf
    sa, sb, sab = inv(fa * np.conj(fmb)), inv(fma * np.conj(fb)), inv(fa * np.conj(fb))
    va, vb = inv(fa2 * np.conj(fmb)) - sa * sa / n, inv(fma * np.conj(fb2)) - sb * sb / n
    if va <= 4.0 * n or vb <= 4.0 * n:
        return -np.inf
    return float((sab - sa * sb / n) / np.sqrt(va * vb))


def group_edge_ncc(comp: list[int], where: dict[int, np.ndarray], main: dict[int, np.ndarray]) -> float:
    """Median NCC of an island's members with the main-body tiles next to them (within 1.3 pitches)."""
    values = []
    for u in comp:
        for b, p in main.items():
            d = where[u] - p
            if np.linalg.norm(d) < 1.3 * PITCH:
                v = ncc_at(b, u, d)
                if np.isfinite(v):
                    values.append(v)
    return float(np.median(values)) if values else -np.inf


def group_columns(info: dict | None) -> list:
    """islands.tsv columns for the rigid-group placement."""
    if not info:
        return [""] * 8
    if "offset" not in info:
        return [info["members_agreeing"]] + [""] * 6 + ["no"]
    return [info["members_agreeing"], round(info["offset"][0]), round(info["offset"][1]), round(info["spread"]),
            f"{info['ncc']:.3f}", f"{info['edge_old']:.3f}", f"{info['edge_new']:.3f}", "yes" if info.get("placed") else "no"]


def write_review(layout_name: str, out_name: str, targets: dict[int, np.ndarray]) -> None:
    """Write a copy of the layout with the given tiles moved to the given origins."""
    mosaic = nornir_imageregistration.Mosaic.LoadFromMosaicFile(os.path.join(SECTION, layout_name))
    for key, tr in mosaic.ImageToTransform.items():
        t = int(key[:-4])
        if t in targets:
            p = tr.Transform(np.array([[0.0, 0.0]]))[0]
            tr.TranslateFixed(targets[t] - np.asarray(p.get() if hasattr(p, "get") else p, dtype=np.float64))
    mosaic.SaveToMosaicFile(os.path.join(SECTION, out_name))


def positions(name: str) -> dict[int, np.ndarray]:
    """Tile number to origin (Y, X) in a section mosaic."""
    out = {}
    for k, t in nornir_imageregistration.Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name)).ImageToTransform.items():
        p = t.Transform(np.array([[0.0, 0.0]]))[0]
        out[int(k[:-4])] = np.asarray(p.get() if hasattr(p, "get") else p, dtype=np.float64)
    return out


def main() -> None:
    layout_name, tsv, report, out_name, islands_tsv = sys.argv[1:6]
    workers = int(sys.argv[6]) if len(sys.argv) > 6 else 6
    pos, stage = positions(layout_name), positions("Stage.mosaic")
    rows = [{k: (float(v) if k not in ("A", "B") else int(v)) for k, v in r.items()} for r in csv.DictReader(open(tsv), delimiter="\t")]
    far = np.array([r["best_ncc"] for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) > 12000 and np.isfinite(r["best_ncc"])])
    p95, fmax = float(np.percentile(far, 95)), float(far.max())
    accept = max(0.6, p95) + MARGIN
    strong = max(0.85, fmax + MARGIN)
    near = [r for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) < 1.3 * PITCH]
    edges: dict[int, list[float]] = {}
    for r in near:
        if np.isfinite(r["ncc_at_layout"]):
            for t in (r["A"], r["B"]):
                edges.setdefault(t, []).append(r["ncc_at_layout"])
    misplaced = {t for r in near if r["best_ncc"] > 0.6 and np.hypot(r["best_dy"] - r["layout_dy"], r["best_dx"] - r["layout_dx"]) > 640
                 for t in (r["A"], r["B"])}
    m = re.search(r"unresolved \(kept in place\): \[([^\]]*)\]", open(report).read())
    loose = sorted(int(x) for x in m.group(1).split(",") if x.strip()) if m else []
    loose = [t for t in loose if t in pos]
    settled = {t for t, v in edges.items() if v and min(v) >= p95 and t not in misplaced} - set(loose)
    print(f"noise floor p95 {p95:.2f} max {fmax:.2f}; accept >= {accept:.2f}; settled {len(settled)}; unresolved {len(loose)}", flush=True)

    t0 = time.perf_counter()
    cache = islands_tsv + ".peaks.npy"  # the wide search takes ~1 h on 1034; later steps reuse it
    if os.path.exists(cache):
        peaks: list[tuple] = [(int(r[0]), int(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in np.load(cache)]
        print(f"wide search: {len(peaks)} pairs from {cache}", flush=True)
    else:
        others = sorted(pos)
        chunks = [others[i:i + 40] for i in range(0, len(others), 40)]
        peaks = []
        with ProcessPoolExecutor(workers) as pool:
            for k, res in enumerate(pool.map(work, [(c, loose) for c in chunks])):
                peaks.extend(res)
                if k % 5 == 0:
                    print(f"{k + 1}/{len(chunks)} chunks {time.perf_counter() - t0:.0f}s", flush=True)
        np.save(cache, np.array(peaks, dtype=np.float64))
        print(f"wide search: {len(peaks)} pairs in {time.perf_counter() - t0:.0f}s", flush=True)

    # 1. placement from settled tiles: b sits at +s in u's frame, so u sits at pos[b] - s
    resolved: dict[int, tuple[np.ndarray, int, float]] = {}
    for u in loose:
        est = [(pos[b] - np.array([dy, dx]), b, ncc) for (uu, b, ncc, dy, dx) in peaks if uu == u and b in settled and ncc >= accept]
        best: list = []
        for e in est:
            cl = list({c[1]: c for c in est if np.linalg.norm(c[0] - e[0]) <= TOL}.values())
            if len(cl) > len(best):
                best = cl
        if len(best) >= MIN_AGREE:
            resolved[u] = (np.mean([c[0] for c in best], axis=0), len(best), float(np.median([c[2] for c in best])))
    for u, (p, k, q) in sorted(resolved.items()):
        print(f"resolved {u}: {k} settled tiles agree (median NCC {q:.2f}), offset from layout {np.round(p - pos[u])}", flush=True)
    rest = [u for u in loose if u not in resolved]

    # 2. islands among the rest
    link: dict[tuple[int, int], tuple[float, float, float]] = {}
    for (u, b, ncc, dy, dx) in peaks:
        if b in rest and u < b and np.linalg.norm(stage[b] - stage[u]) <= RADIUS * PITCH:
            exp = stage[b] - stage[u]
            if ncc >= strong or (ncc >= accept and np.linalg.norm(np.array([dy, dx]) - exp) <= 0.5 * PITCH):
                link[(u, b)] = (ncc, dy, dx)
    parent = {u: u for u in rest}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for (u, b) in link:
        parent[find(u)] = find(b)
    comps: dict[int, list[int]] = {}
    for u in rest:
        comps.setdefault(find(u), []).append(u)
    islands = sorted((sorted(c) for c in comps.values() if len(c) > 1), key=lambda c: (-len(c), c[0]))
    singles = sorted(c[0] for c in comps.values() if len(c) == 1)

    # internal layout: maximum spanning tree from the lowest-numbered tile
    local: dict[int, np.ndarray] = {}
    inner: dict[int, list[float]] = {}
    for i, comp in enumerate(islands):
        local[comp[0]] = np.zeros(2)
        done = {comp[0]}
        cand = sorted(((v[0], a, b, v) for (a, b), v in link.items() if a in comp), reverse=True)
        while len(done) < len(comp):
            for ncc, a, b, v in cand:
                if (a in done) != (b in done):
                    s = np.array(v[1:])
                    if a in done:
                        local[b] = local[a] + s
                        done.add(b)
                    else:
                        local[a] = local[b] - s
                        done.add(a)
                    inner.setdefault(i, []).append(ncc)
                    break
            else:
                break

    main_tiles = [t for t in pos if t not in rest]
    final = {t: (resolved[t][0] if t in resolved else pos[t]) for t in main_tiles}
    lo = np.min([final[t] for t in main_tiles], axis=0)
    hi = np.max([final[t] for t in main_tiles], axis=0) + TILE_PX
    y = hi[0] + PITCH
    x = lo[1]
    row_h = 0.0
    place: dict[int, np.ndarray] = {}
    for comp in islands:
        pts = np.array([local[t] for t in comp])
        cmin, cmax = pts.min(0), pts.max(0) + TILE_PX
        if x + (cmax[1] - cmin[1]) > hi[1] and x > lo[1]:
            y, x, row_h = y + row_h + PITCH, lo[1], 0.0
        for t in comp:
            place[t] = np.array([y, x]) + local[t] - cmin
        x += cmax[1] - cmin[1] + PITCH
        row_h = max(row_h, cmax[0] - cmin[0])
    y, x = y + row_h + PITCH, lo[1]
    for t in singles:
        if x + TILE_PX > hi[1] and x > lo[1]:
            y, x = y + TILE_PX + PITCH, lo[1]
        place[t] = np.array([y, x])
        x += TILE_PX + PITCH

    write_review(layout_name, out_name, {**{t: resolved[t][0] for t in resolved}, **place})

    # 3. Each island as one rigid group: every member's match with a main-body tile (settled or placed by the wide
    # search) votes for an island offset; MIN_AGREE+ members spread over at least a pitch and agreeing within GROUP_TOL
    # place it. Group hard check: the members' median edge NCC with the main body at the new place must not be lower
    # than where the solve left them.
    firm = settled | set(resolved)
    group: dict[int, dict] = {}
    placed: dict[int, np.ndarray] = {}
    for i, comp in enumerate(islands):
        votes = [(final[b] - np.array([dy, dx]) - local[u], u, ncc) for (u, b, ncc, dy, dx) in peaks
                 if u in comp and b in firm and ncc >= accept]
        best: list = []
        for v in votes:
            cl = list({c[1]: c for c in votes if np.linalg.norm(c[0] - v[0]) <= GROUP_TOL}.values())
            if len(cl) > len(best):
                best = cl
        info: dict = {"votes": len(votes), "members_agreeing": len(best)}
        if len(best) >= MIN_AGREE:
            spread = max(float(np.linalg.norm(local[a[1]] - local[b[1]])) for a in best for b in best)
            offset = np.mean([c[0] for c in best], axis=0)
            new_pos = {u: offset + local[u] for u in comp}
            e_new = group_edge_ncc(comp, new_pos, final)
            e_old = group_edge_ncc(comp, {u: pos[u] for u in comp}, final)
            info.update(offset=offset, spread=spread, ncc=float(np.median([c[2] for c in best])), edge_new=e_new, edge_old=e_old)
            if spread >= PITCH and e_new >= e_old:
                placed.update(new_pos)
                info["placed"] = True
        group[i] = info
        print(f"island I{i + 1} ({len(comp)} tiles): " + ", ".join(f"{k} {np.round(v, 2) if isinstance(v, (float, np.ndarray)) else v}" for k, v in info.items()), flush=True)
    write_review(layout_name, out_name.replace(".mosaic", "_placed.mosaic"),
                 {**{t: resolved[t][0] for t in resolved}, **place, **placed})
    print(f"islands placed as rigid groups: {sum(1 for g in group.values() if g.get('placed'))} "
          f"({sum(len(islands[i]) for i, g in group.items() if g.get('placed'))} tiles)", flush=True)

    vs_main: dict[int, tuple] = {}
    for (u, b, ncc, dy, dx) in peaks:
        if u in rest and b not in rest and (u not in vs_main or ncc > vs_main[u][1]):
            vs_main[u] = (b, ncc, dy, dx)
    with open(islands_tsv, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["island", "tiles", "n", "internal_median_ncc", "anchor", "anchor_stage_y", "anchor_stage_x",
                    "best_main_tile", "best_main_ncc", "best_main_dy", "best_main_dx", "noise_p95", "noise_max",
                    "group_members_agreeing", "group_offset_y", "group_offset_x", "group_spread", "group_median_ncc",
                    "edge_ncc_where_left", "edge_ncc_at_group_offset", "group_placed"])
        groups = [(f"I{i + 1}", c) for i, c in enumerate(islands)] + [(f"S{t}", [t]) for t in singles]
        for gid, comp in groups:
            bm = max((vs_main[t] + (t,) for t in comp if t in vs_main), key=lambda v: v[1], default=None)
            internal = f"{np.median(inner[islands.index(comp)]):.3f}" if gid.startswith("I") and islands.index(comp) in inner else ""
            w.writerow([gid, " ".join(map(str, comp)), len(comp), internal, comp[0], round(stage[comp[0]][0]), round(stage[comp[0]][1])]
                       + ([f"{bm[4]}->{bm[0]}", f"{bm[1]:.3f}", round(bm[2]), round(bm[3])] if bm else ["", "", "", ""])
                       + [f"{p95:.2f}", f"{fmax:.2f}"]
                       + group_columns(group.get(islands.index(comp)) if gid.startswith("I") else None))
    print(f"resolved by wide search: {len(resolved)}; islands: {[len(c) for c in islands]}; singletons: {len(singles)}", flush=True)


if __name__ == "__main__":
    main()
