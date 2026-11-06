"""Targeted repair: keep an existing layout and re-place only the tiles the correlation says are wrong or missing.

usage:
  replace_tiles.py plus  <base layout> <prune mosaic> <out>
      Drop the base tiles the Prune mosaic lacks and add the Prune tiles the base layout lacks, at their Stage positions moved by the median (layout - stage) offset
      of the nearest placed tiles. Writes <out>; run crosscheck_pairs.py on it (stage mosaic = <out> too).
  replace_tiles.py solve <layout> <tsv> <out> [min ncc, default 0.6] [tolerance px, default 60]
      Tiles in two or more misplaced pairs (see crosscheck_summary.py), tiles whose edges correlate poorly at the layout
      (half or more of their neighbour edges at NCC <= 0.3) and tiles added by 'plus' are re-placed from the
      correlation peaks to their settled neighbours: each pair gives an estimate of the tile's position; the largest
      cluster of estimates (within the tolerance, at least two) wins; a single estimate also counts when it beats the noise
      floor's maximum by 0.05 (and is at least 0.85). Peaks below the noise floor's 95th percentile are ignored: the floor
      is the best NCC of pairs more than 12,000 px apart, which is noise by construction. Moves over a quarter pitch (~900 px) need independent agreement (2026-11-05, after
      515 and 1034, where single 0.93 peaks on fold/tear texture threw tiles thousands of px): 3+ different settled tiles
      agreeing above the floor with a margin, or two confirming the new spot from opposite sides. Settled tiles (every immediate-neighbour
      edge above the noise floor at the layout, no misplaced pair) never move; every other tile is a suspect. Coverage and
      overlap are never criteria: a tearing section can leave regions uncaptured and others captured twice (a strong match
      at a large overlap with a settled tile is a valid placement). Tiles without a cluster keep their position (with DROP_UNRESOLVED_ADDED=1 the ones 'plus' added are left out instead) and are
      reported as unresolved. Repeats until no tile changes. A move is undone when the tile's median edge NCC at the new place, measured on the images, is lower
      than at the old place. Writes <out> and <out>.report.txt.

The TSV is crosscheck_pairs.py output: best_dy/best_dx is where tile B sits relative to tile A, in full-resolution pixels.
Run with RESCUE_SECTION_DIR set to the channel folder of the isolated copy. See ../SKILL.md."""
import os
import sys

import numpy as np

import nornir_imageregistration

SECTION = os.environ["RESCUE_SECTION_DIR"]
PITCH = 3590.0
STRONG_NCC = 0.85  # a single match this strong places a tile on its own (1240's 805/806 matched at 0.93)
FAR_MOVE = 0.25 * PITCH  # ~900 px; shorter moves need only 2 agreeing edges, longer ones several independent tiles
FAR_CLUSTER = 3  # agreeing settled tiles needed for a far move
FAR_MARGIN = 0.05  # each of their peaks this far above the noise floor's p95
TILE_PX = 4080.0
CHECK_MIN_MOVE = 16.0  # px (one ds16 pixel); 515 v6: unchecked 35-70 px moves from suspect-sourced peaks added 145 poor edges
CHECK_TOL = 0.02  # NCC; ds16 rounding noise
REFINE_RANGE = 128.0  # px; the solve leaves smaller corrections to the grid refine (515 v7: 15-70 px moves from ds16 peaks made 742 edges better and 693 worse)


def load(name: str) -> nornir_imageregistration.Mosaic:
    """Load a mosaic from the section folder."""
    return nornir_imageregistration.Mosaic.LoadFromMosaicFile(os.path.join(SECTION, name))


def origin(transform) -> np.ndarray:
    """Tile origin (Y, X) in mosaic space, as a NumPy array."""
    p = transform.Transform(np.array([[0.0, 0.0]]))[0]
    return np.asarray(p.get() if hasattr(p, "get") else p, dtype=np.float64)


def positions(mosaic: nornir_imageregistration.Mosaic) -> dict[int, np.ndarray]:
    """Tile number to origin."""
    return {int(k[:-4]): origin(t) for k, t in mosaic.ImageToTransform.items()}


def base_pos_names(mosaic: nornir_imageregistration.Mosaic) -> list[int]:
    """Tile numbers in a mosaic."""
    return [int(k[:-4]) for k in mosaic.ImageToTransform]


def plus(base_name: str, prune_name: str, out_name: str) -> None:
    """Write the base layout plus the Prune tiles it lacks."""
    base, prune = load(base_name), load(prune_name)
    base_pos, stage_pos = positions(base), positions(prune)
    for number in sorted(set(base_pos_names(base)) - set(positions(prune))):  # tiles the new Prune dropped
        del base.ImageToTransform[next(k for k in base.ImageToTransform if int(k[:-4]) == number)]
        print(f"removed tile {number} (not in the Prune mosaic)")
    base_pos = positions(base)
    stage_pos = positions(prune)
    for number in sorted(set(stage_pos) - set(base_pos)):
        near = sorted(set(base_pos) & set(stage_pos), key=lambda t: float(np.linalg.norm(stage_pos[t] - stage_pos[number])))[:8]
        offset = np.median([base_pos[t] - stage_pos[t] for t in near], axis=0)
        transform = prune.ImageToTransform[f"{number:03d}.png" if f"{number:03d}.png" in prune.ImageToTransform else f"{number}.png"]
        transform.TranslateFixed(offset)
        base.ImageToTransform[f"{number:03d}.png" if f"{number:03d}.png" in prune.ImageToTransform else f"{number}.png"] = transform
        print(f"added tile {number} at stage position + offset {offset.round(0)}")
    base.SaveToMosaicFile(os.path.join(SECTION, out_name))
    with open(os.path.join(SECTION, "added_tiles.txt"), "w") as f:  # read by 'solve'
        f.write(" ".join(str(t) for t in sorted(set(stage_pos) - set(base_pos))))


def median_edge_ncc(t: int, pos: dict[int, np.ndarray]) -> float:
    """Median masked NCC (ds16, extrema masked) of tile t with its immediate neighbours at the given positions."""
    os.environ.setdefault("CROSSCHECK_EXTREMA", "1")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import crosscheck_pairs as cc
    values = []
    for u, p in pos.items():
        d = p - pos[t]
        if u == t or np.linalg.norm(d) >= 1.3 * PITCH or np.abs(d / cc.DS).max() >= cc.N // 2 - 1:
            continue  # beyond half the FFT size the index would wrap to a different shift
        ncc, _ = cc.masked_ncc(t, u)
        v = float(ncc[int(round(d[0] / cc.DS)) % cc.N, int(round(d[1] / cc.DS)) % cc.N])
        if np.isfinite(v):
            values.append(v)
    return float(np.median(values)) if values else -np.inf


def solve(layout_name: str, tsv: str, out_name: str, min_ncc: float, tol: float, added: set[int]) -> None:
    """Re-place the suspect tiles from correlation peaks to their settled neighbours."""
    import csv
    mosaic = load(layout_name)
    pos = positions(mosaic)
    rows = [{k: (float(v) if k not in ("A", "B") else int(v)) for k, v in r.items()} for r in csv.DictReader(open(tsv), delimiter="\t")]
    near = [r for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) < 1.3 * PITCH]
    # Noise floor: the best peak of pairs far apart (over 12,000 px) is noise. Repeating textures (11's cell pattern) push
    # it to 0.8+, so the acceptance thresholds come from this section's own floor, not fixed numbers.
    far = np.array([r["best_ncc"] for r in rows if np.hypot(r["layout_dy"], r["layout_dx"]) > 12000 and np.isfinite(r["best_ncc"])])
    if far.size >= 50:
        min_ncc = max(min_ncc, float(np.percentile(far, 95)))
        strong = max(STRONG_NCC, float(far.max()) + 0.05)
    else:
        strong = STRONG_NCC
    print(f"noise floor: {far.size} far pairs, p95 {np.percentile(far, 95) if far.size else float('nan'):.2f}, max {far.max() if far.size else float('nan'):.2f};"
          f" accepting peaks >= {min_ncc:.2f} in clusters of 2+, single peaks >= {strong:.2f}")
    misplaced = [r for r in near if r["best_ncc"] > 0.6 and np.hypot(r["best_dy"] - r["layout_dy"], r["best_dx"] - r["layout_dx"]) > 640]
    count: dict[int, int] = {}
    for r in misplaced:
        for t in (r["A"], r["B"]):
            count[t] = count.get(t, 0) + 1
    # Tiles whose edges correlate poorly where the layout puts them (at least half of their scoreable neighbour edges
    # at NCC 0.3 or below) are searched against every tile in the TSV's radius too: that is how 1240's 805/806 was found.
    edges: dict[int, list[float]] = {}
    for r in near:
        if np.isfinite(r["ncc_at_layout"]):
            for t in (r["A"], r["B"]):
                edges.setdefault(t, []).append(r["ncc_at_layout"])
    poor = {t for t, v in edges.items() if sum(x <= 0.3 for x in v) >= max(1, len(v) / 2)}
    # Settled (James, 2026-11-05): a tile whose edges with its immediate neighbours all correlate above the section's noise
    # floor at the layout, and which is in no misplaced pair, is aligned with its neighbours. It is never a suspect and
    # never moves, whatever a far peak says. Every other tile is a suspect (poor edges, misplaced pairs, or not placed).
    in_misplaced = {t for r in misplaced for t in (r["A"], r["B"])}
    settled = {t for t, v in edges.items() if v and min(v) >= min_ncc and t not in in_misplaced} - added
    print("tiles with poorly correlated edges:", sorted(poor))
    # Tiles overlapping a neighbour by more than half a tile at the layout are probably misplaced (1034's L-shaped hole sat
    # beside a stack of such tiles), so they are searched too.
    stacked: set[int] = set()
    ids = sorted(pos)
    arr = np.array([pos[t] for t in ids])
    for i, t in enumerate(ids):
        d = np.abs(arr - arr[i])
        frac = np.clip(TILE_PX - d[:, 0], 0, None) * np.clip(TILE_PX - d[:, 1], 0, None) / TILE_PX ** 2
        frac[i] = 0
        if frac.max() > 0.5:
            stacked.add(t)
    print("tiles overlapping a neighbour by more than 50%:", sorted(stacked))
    suspects = (set(pos) - settled) | added
    print(f"settled tiles: {len(settled)} of {len(pos)}")
    print("suspect tiles:", sorted(suspects))

    def far_move_supported(t: int, cluster: list[tuple[np.ndarray, float, int]]) -> bool:
        """Evidence rule for moves over FAR_MOVE (James, 2026-11-05): tearing sections really do leave holes and duplicate
        tissue, so coverage never decides; independent agreement does. Accept when FAR_CLUSTER or more different settled
        tiles agree (each peak at least FAR_MARGIN above the floor's p95; tiles confirmed earlier in the same solve count), or when two agreeing tiles confirm the new spot
        from opposite sides. A large overlap with the agreeing tiles is allowed: a torn section can be captured twice
        (duplicate tissue), so overlap is not a fault."""
        good = [c for c in cluster if c[1] >= min_ncc + FAR_MARGIN]
        if len(good) >= FAR_CLUSTER:
            return True
        if len(good) < 2:
            return False
        new = np.mean([c[0] for c in good], axis=0)
        for i, a in enumerate(good):
            for b in good[i + 1:]:
                va, vb = pos[a[2]] - new, pos[b[2]] - new
                if np.dot(va, vb) < -0.5 * np.linalg.norm(va) * np.linalg.norm(vb):  # sources on opposite sides
                    return True
        return False

    moved: dict[int, np.ndarray] = {}
    unresolved: list[int] = []
    for _ in range(10):
        changed = False
        for t in sorted(suspects):
            # (position estimate, NCC, source tile); 'firm' sources are settled or already confirmed in this solve
            est: list[tuple[np.ndarray, float, int]] = []
            firm: list[tuple[np.ndarray, float, int]] = []
            for r in rows:
                if r["best_ncc"] < min_ncc:
                    continue
                if r["B"] == t:
                    e = (pos[r["A"]] + np.array([r["best_dy"], r["best_dx"]]), r["best_ncc"], r["A"])
                elif r["A"] == t:
                    e = (pos[r["B"]] - np.array([r["best_dy"], r["best_dx"]]), r["best_ncc"], r["B"])
                else:
                    continue
                est.append(e)
                if e[2] not in suspects:
                    firm.append(e)

            def largest_cluster(cands: list[tuple[np.ndarray, float, int]]) -> list[tuple[np.ndarray, float, int]]:
                """Largest set of estimates within the tolerance of one another, one vote per source tile."""
                top: list[tuple[np.ndarray, float, int]] = []
                for e in cands:
                    cluster = list({c[2]: c for c in cands if np.linalg.norm(c[0] - e[0]) <= tol}.values())
                    if len(cluster) > len(top):
                        top = cluster
                return top

            def shift(cluster: list[tuple[np.ndarray, float, int]]) -> float:
                return float(np.linalg.norm(np.mean([c[0] for c in cluster], axis=0) - pos[t]))

            best = largest_cluster(firm)
            if len(best) >= 2 and shift(best) > FAR_MOVE and not far_move_supported(t, best):
                best = []
            if len(best) < 2:
                # Rule (a): a short move needs only two neighbours' edges agreeing on the new place, whether or not those
                # neighbours are themselves suspects (515's 1688: 1687 and 1730 agree on 706 px, but 1687 never settled)
                short = largest_cluster(est)
                best = short if len(short) >= 2 and shift(short) <= FAR_MOVE else []
            if len(best) < 2 and est:  # one very strong match is enough for a short move (a tear-edge tile may have one neighbour)
                k = max(range(len(est)), key=lambda i: est[i][1])
                if est[k][1] >= strong and np.linalg.norm(est[k][0] - pos[t]) <= FAR_MOVE:
                    best = [est[k], est[k]]
            if len(best) >= 2:
                new = np.mean([b[0] for b in best], axis=0)
                if np.linalg.norm(new - pos[t]) > REFINE_RANGE:  # smaller corrections are left to the grid refine
                    moved[t] = new - pos[t] + moved.get(t, 0)
                    pos[t] = new
                    changed = True
                if t in unresolved:
                    unresolved.remove(t)
                suspects.discard(t)  # confirmed: supports its neighbours' placement later in this same pass
            elif t not in unresolved:
                unresolved.append(t)
        # a settled tile can unlock its neighbours: treat resolved suspects as settled for the next pass
        suspects -= {t for t in suspects if t not in unresolved}
        if not changed or not suspects:
            break
    # Hard check (2026-11-05, 515's tile 975: median edge NCC 0.72 -> -0.15 after a far move): a move is undone when the
    # tile's median edge NCC at the new place, measured on the images, is lower than at the old place. Repeated because
    # undoing one move changes its neighbours' edges.
    original = positions(mosaic)
    undone: list[str] = []
    for _ in range(3):
        back = []
        for t in sorted(moved):
            if np.linalg.norm(pos[t] - original[t]) <= CHECK_MIN_MOVE:
                continue  # a few-pixel correction cannot be measured at ds16; the grid refine settles those
            old = float(np.median(edges[t])) if edges.get(t) else -np.inf
            new = median_edge_ncc(t, pos)
            if new < old - CHECK_TOL:
                back.append(t)
                undone.append(f"  tile {t}: move undone, median edge NCC {old:.2f} at the old place, {new:.2f} at the new")
        for t in back:
            pos[t] = original[t]
            del moved[t]
            if t in added and t not in unresolved:
                unresolved.append(t)
        if not back:
            break
    lines = [f"layout {layout_name}; suspects re-placed: {sorted(moved)}; unresolved (kept in place): {sorted(unresolved)}"]
    lines += undone
    for number, delta in sorted(moved.items()):
        key = f"{number:03d}.png" if f"{number:03d}.png" in mosaic.ImageToTransform else f"{number}.png"
        shift = pos[number] - origin(mosaic.ImageToTransform[key])
        mosaic.ImageToTransform[key].TranslateFixed(shift)
        lines.append(f"  tile {number}: moved by {shift.round(0)} px")
    if os.environ.get("DROP_UNRESOLVED_ADDED") == "1":  # tiles 'plus' added that no correlation confirmed are left out
        for number in sorted(set(unresolved) & added):
            del mosaic.ImageToTransform[next(k for k in mosaic.ImageToTransform if int(k[:-4]) == number)]
            lines.append(f"  tile {number}: added but unresolved, left out")
    mosaic.SaveToMosaicFile(os.path.join(SECTION, out_name))
    open(os.path.join(SECTION, out_name + ".report.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "plus":
        plus(*sys.argv[2:5])
    else:
        base_added = set()
        if os.path.exists(os.path.join(SECTION, "added_tiles.txt")):
            base_added = {int(x) for x in open(os.path.join(SECTION, "added_tiles.txt")).read().split()}
        solve(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 0.6,
              float(sys.argv[6]) if len(sys.argv) > 6 else 60.0, base_added)
