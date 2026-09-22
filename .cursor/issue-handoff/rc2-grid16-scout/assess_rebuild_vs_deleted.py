#!/usr/bin/env python3
"""Compare rebuilt Grid16 group-root STOS files to scout baselines of the deleted files."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault('NORNIR_HEADLESS', '1')

from nornir_imageregistration.refine_assessment.group_scout import (
    DENSE_256,
    RefineSchedule,
    build_schedule_metrics,
)
from nornir_imageregistration.stos_quality import CellZnccRecord, compute_cell_zncc, compute_pair_zncc

PAIRS = json.loads(
    Path('/workspace/.cursor/issue-handoff/rc2-grid16-scout/config.json').read_text()
)['screen_pairs']
GROUP = Path('/storage4/RC2/TEM/Grid16')
SCOUT = Path('/tmp/nornir-test-output/refine_group_scout/Grid16/pairs')
OUT = Path(os.environ.get('TESTOUTPUTPATH', '/tmp/nornir-test-output')) / 'refine_group_scout' / 'Grid16' / 'rebuild_vs_deleted'
STEM = '_ctrl-TEM_Leveled_map-TEM_Leveled.stos'
DUMMY_SCHEDULE = RefineSchedule('rebuild', DENSE_256.cell_size, DENSE_256.grid_spacing)


def _cells(payload: list[dict]) -> list[CellZnccRecord]:
    return [CellZnccRecord(**item) for item in payload]


def _status(pair: str) -> tuple[str, Path | None]:
    rebuilt = GROUP / f'{pair}{STEM}'
    unrefined = GROUP / f'{pair}_ctrl-TEM_Leveled_map-TEM_Leveled.unrefined.stos'
    if rebuilt.is_file():
        return 'rebuilt', rebuilt
    if unrefined.is_file():
        return 'refine_failed', None
    return 'missing', None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for index, pair in enumerate(PAIRS, start=1):
        checkpoint = OUT / f'{pair}.json'
        status, path = _status(pair)
        baseline_path = SCOUT / pair / 'baseline.json'
        print(f'[{index}/{len(PAIRS)}] {pair} {status}', flush=True)
        if checkpoint.is_file():
            results.append(json.loads(checkpoint.read_text()))
            continue
        row: dict = {'pair': pair, 'status': status}
        if status != 'rebuilt' or path is None:
            checkpoint.write_text(json.dumps(row, indent=2) + '\n')
            results.append(row)
            continue
        if not baseline_path.is_file():
            row['status'] = 'missing_baseline'
            checkpoint.write_text(json.dumps(row, indent=2) + '\n')
            results.append(row)
            continue
        baseline = json.loads(baseline_path.read_text())
        pair_in = float(baseline['pair_zncc'])
        cells_in = _cells(baseline['cells'])
        pair_out = float(compute_pair_zncc(str(path)).pair_zncc)
        cells_out = list(compute_cell_zncc(
            str(path),
            cell_size=128,
            grid_spacing=128,
            max_side=None,
        ).cells)
        quality_flag = path.with_suffix('.quality_flag').is_file()
        metrics = build_schedule_metrics(
            pair=pair,
            schedule=DUMMY_SCHEDULE,
            pair_zncc_in=pair_in,
            pair_zncc_out=pair_out,
            baseline_cells=cells_in,
            output_cells=cells_out,
            quality_flag=quality_flag,
            wall_s=None,
            output_stos=str(path),
            error=None,
        )
        row.update(asdict(metrics))
        row['status'] = 'rebuilt'
        row['old_checksum'] = baseline.get('stos_checksum')
        checkpoint.write_text(json.dumps(row, indent=2) + '\n')
        results.append(row)
        print(
            f'    pair {pair_in:.4f}->{pair_out:.4f} d={metrics.pair_zncc_delta} '
            f'net={metrics.net_improved} repaired={metrics.repaired_clusters} '
            f'flag={quality_flag}',
            flush=True,
        )

    rebuilt = [r for r in results if r.get('status') == 'rebuilt' and 'net_improved' in r]
    rebuilt.sort(key=lambda item: (
        -(item.get('repaired_clusters') or 0),
        -(item.get('net_improved') or 0),
        -(item.get('delta_p05') if item.get('delta_p05') is not None else float('-inf')),
        -(item.get('pair_zncc_delta') if item.get('pair_zncc_delta') is not None else float('-inf')),
        item['pair'],
    ))
    fields = [
        'pair', 'status', 'accepted', 'reject_reason', 'quality_flag',
        'pair_zncc_in', 'pair_zncc_out', 'pair_zncc_delta',
        'median_cell_in', 'median_cell_out', 'delta_median', 'delta_p05',
        'improved_count', 'worse_count', 'net_improved',
        'repaired_clusters', 'baseline_weak_clusters',
    ]
    csv_path = OUT / 'comparison.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rebuilt)
        writer.writerows([r for r in results if r not in rebuilt])
    summary = {
        'rebuilt_scored': len(rebuilt),
        'refine_failed': [r['pair'] for r in results if r.get('status') == 'refine_failed'],
        'missing': [r['pair'] for r in results if r.get('status') == 'missing'],
        'improved_pair_zncc': sum(1 for r in rebuilt if (r.get('pair_zncc_delta') or 0) > 0),
        'worse_pair_zncc': sum(1 for r in rebuilt if (r.get('pair_zncc_delta') or 0) < 0),
        'net_cells_positive': sum(1 for r in rebuilt if (r.get('net_improved') or 0) > 0),
        'net_cells_negative': sum(1 for r in rebuilt if (r.get('net_improved') or 0) < 0),
        'median_pair_delta': None,
        'median_cell_delta_median': None,
        'rows': rebuilt,
    }
    if rebuilt:
        import numpy as np
        summary['median_pair_delta'] = float(np.median([r['pair_zncc_delta'] for r in rebuilt]))
        summary['median_cell_delta_median'] = float(np.median([
            r['delta_median'] for r in rebuilt if r.get('delta_median') is not None
        ]))
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'Wrote {csv_path}')
    print(f'Wrote {OUT / "summary.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
