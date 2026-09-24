#!/usr/bin/env python3
"""Refine-grid fixture runner for trusted-mesh regression testing.

Runs RefineStosFile (same path as the STOS debug harness / pipeline) on the
plan fixture pairs with Grid16 production settings (cell 256, spacing 192,
10 iterations). Writes refined STOS + PASS_DIAGNOSTICS under TESTOUTPUTPATH
so the volume tree is not modified.

Trusted mesh is the production path.
"""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("NORNIR_HEADLESS", "1")
os.environ["NORNIR_REFINE_PASS_DIAGNOSTICS"] = "1"
os.environ.setdefault("NORNIR_REFINE_PHASE_TIMING", "1")

import numpy as np
import nornir_imageregistration
from nornir_imageregistration.files.stosfile import StosFile
from nornir_imageregistration.local_distortion_correction import RefineStosFile
from nornir_imageregistration.refine_shared.peak_ratio_gates import PEAK_RATIO_MIN
from nornir_imageregistration.refine_shared.phase_timer import get_phase_timer
from nornir_imageregistration.transforms.factory import LoadTransform
from nornir_shared.misc import SetupLogging

try:
    from nornir_imageregistration.stos_quality import compute_cell_zncc, compute_pair_zncc
except ImportError:
    compute_cell_zncc = None
    compute_pair_zncc = None

GRID16 = Path("/storage4/RC2/TEM/Grid16")
PAIRS: list[tuple[str, str, str]] = [
    ("605-606", "performance-baseline", "automatic-strict"),
    ("1215-1214", "challenging-band", "manual"),
    ("240-241", "challenging-coherent-residual", "manual"),
    ("241-242", "challenging-identity-bubble", "automatic"),
    ("252-254", "challenging-tear-front", "automatic"),
    ("228-229", "challenging-high-weight-outliers", "automatic"),
    ("953-952", "challenging-subpar", "automatic"),
    ("183-184", "healthy", "automatic"),
]
STEM_SUFFIX = "_ctrl-TEM_Leveled_map-TEM_Leveled.stos"
CELL_SIZE = 256
GRID_SPACING = 192
NUM_ITERATIONS = 10


def _stos_path(pair: str, source: str) -> Path:
    name = f"{pair}{STEM_SUFFIX}"
    if source == "manual":
        path = GRID16 / "Manual" / name
    elif source == "automatic-strict":
        path = GRID16 / "Automatic" / name
    elif source == "automatic":
        path = GRID16 / "Automatic" / name
        if not path.is_file():
            path = GRID16 / name
    else:
        path = GRID16 / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _sha256(path: Path) -> str:
    """Return the SHA-256 checksum of a file without loading it whole."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _code_metadata() -> dict:
    """Record the imported package path and exact Git state."""
    package_root = Path(nornir_imageregistration.__file__).resolve().parent.parent

    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(package_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    try:
        sha = git("rev-parse", "HEAD")
        status = git("status", "--short")
        diff = subprocess.run(
            ["git", "-C", str(package_root), "diff", "--binary", "HEAD"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"package_root": str(package_root), "git_available": False}
    return {
        "package_root": str(package_root),
        "git_available": True,
        "git_sha": sha,
        "git_dirty": bool(status),
        "git_status": status.splitlines(),
        "git_diff_sha256": hashlib.sha256(diff).hexdigest() if diff else None,
    }


def _score_output(output_path: Path, pair_dir: Path) -> dict | None:
    """Persist full-pair and fixed-lattice cell quality for one output."""
    if compute_cell_zncc is None or compute_pair_zncc is None:
        return None
    pair_result = compute_pair_zncc(str(output_path))
    cell_result = compute_cell_zncc(
        str(output_path),
        cell_size=CELL_SIZE,
        grid_spacing=GRID_SPACING,
    )
    cell_payload = asdict(cell_result)
    cells_path = pair_dir / "cell_zncc.json"
    cells_path.write_text(json.dumps(cell_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "pair_zncc": asdict(pair_result),
        "cell_zncc": {
            key: value
            for key, value in cell_payload.items()
            if key != "cells"
        },
        "cell_scores_path": str(cells_path),
    }


def _summarize_npz(diag_dir: Path) -> list[dict]:
    passes: list[dict] = []
    for npz_path in sorted(diag_dir.glob("refine_pass*_diagnostics.npz")):
        data = np.load(npz_path)
        n = int(data["locked"].shape[0])
        locked = int(np.count_nonzero(data["locked"]))
        ratios = np.asarray(data["peak_ratio"], dtype=np.float64)
        unique = int(np.count_nonzero(np.isfinite(ratios) & (ratios >= PEAK_RATIO_MIN)))
        unlocked = n - locked
        unique_among_unlocked = None
        if unlocked > 0:
            unlocked_mask = ~data["locked"]
            unique_among_unlocked = float(
                np.count_nonzero(
                    unlocked_mask & np.isfinite(ratios) & (ratios >= PEAK_RATIO_MIN)
                )
                / unlocked
            )
        passes.append({
            "file": npz_path.name,
            "n_grid": n,
            "locked": locked,
            "lock_fraction": locked / n if n else None,
            "unique": unique,
            "unique_fraction": unique / n if n else None,
            "unique_fraction_among_unlocked": unique_among_unlocked,
            "mesh_included": int(np.count_nonzero(data["mesh_included"])),
            "travel_dropped": int(np.count_nonzero(data["travel_dropped"])),
            "discontinuity": int(np.count_nonzero(data["discontinuity"])),
            "lock_candidate": int(np.count_nonzero(data["lock_candidate"])),
        })
    return passes


def _control_point_delta(input_stos: Path, output_stos: Path) -> dict:
    inp = StosFile.Load(str(input_stos))
    out = StosFile.Load(str(output_stos))
    tin = LoadTransform(inp.Transform)
    tout = LoadTransform(out.Transform)
    src = nornir_imageregistration.EnsureNumpyArray(tout.SourcePoints)
    t_in = nornir_imageregistration.EnsureNumpyArray(tin.Transform(src))
    t_out = nornir_imageregistration.EnsureNumpyArray(tout.Transform(src))
    delta = t_out - t_in
    dist = np.linalg.norm(delta, axis=1)
    return {
        "n_output_points": int(src.shape[0]),
        "rms_px": float(np.sqrt(np.mean(dist ** 2))) if dist.size else None,
        "median_px": float(np.median(dist)) if dist.size else None,
        "max_px": float(np.max(dist)) if dist.size else None,
        "p95_px": float(np.percentile(dist, 95)) if dist.size else None,
    }


def main() -> int:
    SetupLogging(LogToFile=True)
    variant = os.environ.get(
        "NORNIR_REFINE_BASELINE_VARIANT",
        "trusted_mesh",
    )
    out_root = Path(os.environ.get("TESTOUTPUTPATH", "/tmp/nornir-test-output"))
    out_root = out_root / f"refine_grid_baseline_{variant}"
    out_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "trusted_mesh": True,
        "cell_size": CELL_SIZE,
        "grid_spacing": GRID_SPACING,
        "num_iterations": NUM_ITERATIONS,
        "peak_ratio_min": PEAK_RATIO_MIN,
        "code": _code_metadata(),
        "run_kind": os.environ.get("NORNIR_REFINE_BENCHMARK_RUN_KIND", "unspecified"),
        "repetition": int(os.environ.get("NORNIR_REFINE_BENCHMARK_REPETITION", "0")),
        "finalized_recheck_mode": os.environ.get("NORNIR_REFINE_FINALIZED_RECHECK_MODE", "all"),
        "pairs": [],
    }
    selected_pairs = {
        value.strip()
        for value in os.environ.get("NORNIR_REFINE_BASELINE_PAIRS", "").split(",")
        if value.strip()
    }
    pairs = [
        item for item in PAIRS
        if not selected_pairs or item[0] in selected_pairs
    ]
    for pair, role, source in pairs:
        pair_dir = out_root / pair
        pair_dir.mkdir(parents=True, exist_ok=True)
        input_path = _stos_path(pair, source)
        output_path = pair_dir / f"{pair}_refined.stos"
        summary_path = pair_dir / "summary.json"
        print(f"=== {pair} ({role}) input={input_path}", flush=True)
        started = time.perf_counter()
        record: dict = {
            "pair": pair,
            "role": role,
            "input_kind": source,
            "input_path": str(input_path),
            "input_sha256": _sha256(input_path),
            "output_path": str(output_path),
        }
        try:
            RefineStosFile(
                str(input_path),
                str(output_path),
                num_iterations=NUM_ITERATIONS,
                cell_size=CELL_SIZE,
                grid_spacing=GRID_SPACING,
                SavePlots=False,
                SaveImages=False,
            )
            elapsed = time.perf_counter() - started
            diag_dir = pair_dir / "refine_diagnostics" / output_path.stem
            timer = get_phase_timer()
            score = _score_output(output_path, pair_dir)
            record.update({
                "ok": True,
                "elapsed_s": elapsed,
                "output_sha256": _sha256(output_path),
                "quality_flag": (pair_dir / f"{pair}_refined.quality_flag").is_file(),
                "passes": _summarize_npz(diag_dir),
                "pass_performance": list(getattr(timer, "pass_summaries", [])),
                "phase_totals_s": dict(timer.totals),
                "phase_section_counts": dict(timer.counts),
                "phase_work_counts": dict(getattr(timer, "work_counts", {})),
                "control_point_delta": _control_point_delta(input_path, output_path),
                "quality": score,
            })
            print(f"    done {elapsed:.1f}s quality_flag={record['quality_flag']}", flush=True)
        except Exception as exc:
            record.update({
                "ok": False,
                "elapsed_s": time.perf_counter() - started,
                "error": f"{type(exc).__name__}: {exc}",
            })
            print(f"    FAILED {record['error']}", flush=True)
        summary_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        manifest["pairs"].append(record)
        (out_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_root / 'manifest.json'}", flush=True)
    return 0 if all(p.get("ok") for p in manifest["pairs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
