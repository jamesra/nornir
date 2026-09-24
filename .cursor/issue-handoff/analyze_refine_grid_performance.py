#!/usr/bin/env python3
"""Score and compare repeated RC2 refine-grid benchmark outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence

os.environ.setdefault("NORNIR_HEADLESS", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from nornir_imageregistration.stos_quality import (
    CellZnccRecord,
    CellZnccResult,
    compare_cell_zncc,
    compute_cell_zncc,
    compute_pair_zncc,
)

CELL_SIZE = 256
GRID_SPACING = 192


def _read_json(path: Path) -> dict[str, Any]:
    """Load one JSON object."""
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    """Write deterministic indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _score_stos(stos_path: Path, score_path: Path) -> tuple[dict[str, Any], CellZnccResult]:
    """Score a STOS and persist raw full-pair and per-cell values."""
    pair = compute_pair_zncc(str(stos_path))
    cells = compute_cell_zncc(
        str(stos_path),
        cell_size=CELL_SIZE,
        grid_spacing=GRID_SPACING,
    )
    payload = {
        "stos_path": str(stos_path),
        "pair_zncc": asdict(pair),
        "cell_zncc": asdict(cells),
    }
    _write_json(score_path, payload)
    return asdict(pair), cells


def _load_or_score_output(pair_record: dict[str, Any], score_path: Path) -> tuple[dict[str, Any], CellZnccResult]:
    """Load an existing run score or compute it with the current scorer."""
    if score_path.is_file():
        payload = _read_json(score_path)
        if "pair_zncc" in payload and "cell_zncc" in payload:
            cell_payload = payload["cell_zncc"]
        else:
            quality = pair_record.get("quality") or {}
            cell_payload = _read_json(Path(quality["cell_scores_path"]))
            payload = {
                "pair_zncc": quality["pair_zncc"],
                "cell_zncc": cell_payload,
            }
    else:
        pair, cells = _score_stos(Path(pair_record["output_path"]), score_path)
        return pair, cells
    cells = [CellZnccRecord(**item) for item in cell_payload["cells"]]
    result = CellZnccResult(
        cells=cells,
        finite_count=int(cell_payload["finite_count"]),
        median_zncc=cell_payload["median_zncc"],
        min_zncc=cell_payload["min_zncc"],
        max_zncc=cell_payload["max_zncc"],
        cell_size=tuple(cell_payload["cell_size"]),
        grid_spacing=tuple(cell_payload["grid_spacing"]),
        downsample=float(cell_payload["downsample"]),
        stos_checksum=str(cell_payload["stos_checksum"]),
        scored_at=str(cell_payload["scored_at"]),
    )
    return payload["pair_zncc"], result


def _median_cells(results: Sequence[CellZnccResult]) -> CellZnccResult:
    """Collapse repeated runs to one median score per stable cell ID."""
    if not results:
        raise ValueError("At least one cell result is required")
    by_run = [
        {(cell.grid_row, cell.grid_col): cell for cell in result.cells}
        for result in results
    ]
    all_ids = sorted(set().union(*(set(run) for run in by_run)))
    cells: list[CellZnccRecord] = []
    for key in all_ids:
        present = [run[key] for run in by_run if key in run]
        scores = [cell.zncc for cell in present if cell.zncc is not None]
        exemplar = present[0]
        cells.append(replace(
            exemplar,
            valid_pixel_count=int(round(statistics.median(
                cell.valid_pixel_count for cell in present
            ))),
            exclusion_reason=None if scores else "excluded_in_all_runs",
            zncc=float(statistics.median(scores)) if scores else None,
        ))
    finite = np.asarray([cell.zncc for cell in cells if cell.zncc is not None], dtype=np.float64)
    first = results[0]
    return CellZnccResult(
        cells=cells,
        finite_count=int(finite.size),
        median_zncc=float(np.median(finite)) if finite.size else None,
        min_zncc=float(np.min(finite)) if finite.size else None,
        max_zncc=float(np.max(finite)) if finite.size else None,
        cell_size=first.cell_size,
        grid_spacing=first.grid_spacing,
        downsample=first.downsample,
        stos_checksum="median-across-runs",
    )


def _variant_summary(
        label: str,
        manifests: Sequence[Path],
        output_dir: Path,
        pair: str,
) -> tuple[dict[str, Any], CellZnccResult]:
    """Load one benchmark variant and summarize measured repetitions."""
    run_rows: list[dict[str, Any]] = []
    cell_results: list[CellZnccResult] = []
    for manifest_path in manifests:
        manifest = _read_json(manifest_path)
        pair_record = next(row for row in manifest["pairs"] if row["pair"] == pair)
        score_path = output_dir / "raw-scores" / f"{manifest_path.parent.name}.json"
        pair_score, cells = _load_or_score_output(pair_record, score_path)
        cell_results.append(cells)
        run_rows.append({
            "manifest": str(manifest_path),
            "elapsed_s": float(pair_record["elapsed_s"]),
            "pair_zncc": float(pair_score["pair_zncc"]),
            "cell_finite_count": cells.finite_count,
            "cell_median_zncc": cells.median_zncc,
            "cell_min_zncc": cells.min_zncc,
            "cell_max_zncc": cells.max_zncc,
            "phase_totals_s": pair_record.get("phase_totals_s", {}),
            "phase_work_counts": pair_record.get("phase_work_counts", {}),
            "pass_performance": pair_record.get("pass_performance", []),
            "code": manifest.get("code", {}),
        })
    median_cells = _median_cells(cell_results)
    elapsed = np.asarray([row["elapsed_s"] for row in run_rows], dtype=np.float64)
    pair_scores = np.asarray([row["pair_zncc"] for row in run_rows], dtype=np.float64)
    summary = {
        "label": label,
        "run_count": len(run_rows),
        "runtime_s": {
            "median": float(np.median(elapsed)),
            "min": float(np.min(elapsed)),
            "max": float(np.max(elapsed)),
        },
        "pair_zncc": {
            "median": float(np.median(pair_scores)),
            "min": float(np.min(pair_scores)),
            "max": float(np.max(pair_scores)),
        },
        "median_cell_zncc": {
            "finite_count": median_cells.finite_count,
            "median": median_cells.median_zncc,
            "min": median_cells.min_zncc,
            "max": median_cells.max_zncc,
        },
        "runs": run_rows,
    }
    _write_json(output_dir / f"{label}-summary.json", summary)
    _write_json(output_dir / f"{label}-median-cells.json", asdict(median_cells))
    return summary, median_cells


def _write_comparison(
        reference_label: str,
        candidate_label: str,
        reference: CellZnccResult,
        candidate: CellZnccResult,
        output_dir: Path,
) -> dict[str, Any]:
    """Persist paired deltas, histogram/ECDF, and spatial heatmap."""
    comparison = compare_cell_zncc(reference.cells, candidate.cells)
    stem = f"{reference_label}-to-{candidate_label}"
    csv_path = output_dir / f"{stem}-cell-deltas.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(asdict(comparison.cells[0]).keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(asdict(cell) for cell in comparison.cells)

    values = np.asarray([cell.delta_zncc for cell in comparison.cells], dtype=np.float64)
    limit = max(1e-4, float(np.max(np.abs(values)))) if values.size else 1e-4
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].hist(values, bins=np.linspace(-limit, limit, 61), color="#4c78a8")
    axes[0].axvline(0.0, color="black", linewidth=1)
    axes[0].set_title(f"{reference_label} → {candidate_label} cell ΔZNCC")
    axes[0].set_xlabel("candidate − reference")
    axes[0].set_ylabel("cells")
    sorted_values = np.sort(values)
    ecdf = np.arange(1, sorted_values.size + 1) / max(1, sorted_values.size)
    axes[1].plot(sorted_values, ecdf, color="#f58518")
    axes[1].axvline(0.0, color="black", linewidth=1)
    axes[1].set_title("Empirical CDF")
    axes[1].set_xlabel("candidate − reference")
    axes[1].set_ylabel("fraction ≤ Δ")
    fig.tight_layout()
    distribution_path = output_dir / f"{stem}-distribution.png"
    fig.savefig(distribution_path, dpi=160)
    plt.close(fig)

    max_row = max((cell.grid_row for cell in comparison.cells), default=-1)
    max_col = max((cell.grid_col for cell in comparison.cells), default=-1)
    heatmap = np.full((max_row + 1, max_col + 1), np.nan, dtype=np.float64)
    for cell in comparison.cells:
        heatmap[cell.grid_row, cell.grid_col] = cell.delta_zncc
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(heatmap, cmap="coolwarm", vmin=-limit, vmax=limit, origin="upper")
    ax.set_title(f"{reference_label} → {candidate_label} spatial cell ΔZNCC")
    ax.set_xlabel("grid column")
    ax.set_ylabel("grid row")
    fig.colorbar(image, ax=ax, label="candidate − reference")
    fig.tight_layout()
    heatmap_path = output_dir / f"{stem}-heatmap.png"
    fig.savefig(heatmap_path, dpi=160)
    plt.close(fig)

    payload = {
        key: value
        for key, value in asdict(comparison).items()
        if key != "cells"
    }
    paired_count = len(comparison.cells)
    payload.update({
        "paired_count": paired_count,
        "improved_fraction": comparison.improved_count / paired_count if paired_count else None,
        "worse_fraction": comparison.worse_count / paired_count if paired_count else None,
        "unchanged_fraction": comparison.unchanged_count / paired_count if paired_count else None,
        "cell_deltas_csv": str(csv_path),
        "distribution_png": str(distribution_path),
        "heatmap_png": str(heatmap_path),
    })
    _write_json(output_dir / f"{stem}-comparison.json", payload)
    return payload


def _parse_group(value: str) -> tuple[str, str]:
    """Parse LABEL=GLOB group syntax."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("group must be LABEL=GLOB")
    label, pattern = value.split("=", 1)
    if not label or not pattern:
        raise argparse.ArgumentTypeError("group must be LABEL=GLOB")
    return label, pattern


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--production-stos", type=Path, required=True)
    parser.add_argument("--pair", default="605-606")
    parser.add_argument("--group", action="append", type=_parse_group, default=[])
    parser.add_argument("--compare", action="append", default=[])
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    production_pair, production_cells = _score_stos(
        args.production_stos,
        args.output_dir / "production-score.json",
    )
    summaries: dict[str, Any] = {
        "production": {
            "pair_zncc": production_pair,
            "cell_zncc": {
                key: value
                for key, value in asdict(production_cells).items()
                if key != "cells"
            },
        }
    }
    cells_by_label = {"production": production_cells}
    for label, pattern in args.group:
        manifests = sorted(args.benchmark_root.glob(f"{pattern}/manifest.json"))
        if not manifests:
            raise FileNotFoundError(f"No manifests matched {pattern!r}")
        summary, cells = _variant_summary(
            label,
            manifests,
            args.output_dir,
            args.pair,
        )
        summaries[label] = summary
        cells_by_label[label] = cells

    comparisons: dict[str, Any] = {}
    for value in args.compare:
        reference_label, candidate_label = value.split(":", 1)
        comparisons[f"{reference_label}-to-{candidate_label}"] = _write_comparison(
            reference_label,
            candidate_label,
            cells_by_label[reference_label],
            cells_by_label[candidate_label],
            args.output_dir,
        )
    report = {
        "pair": args.pair,
        "cell_size": CELL_SIZE,
        "grid_spacing": GRID_SPACING,
        "variants": summaries,
        "comparisons": comparisons,
    }
    _write_json(args.output_dir / "report.json", report)
    print(args.output_dir / "report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
