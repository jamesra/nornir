"""Profile a build host once so agents choose numpy vs cupy and worker counts from data, not guesses.

Runs every variant of every case in a plan file, one at a time, and records wall time, peak RAM of the whole process
tree, peak GPU memory (nvidia-smi, growth over the idle baseline), and host-wide disk throughput while it ran. Writes
``<out>/<host>-<image>.json`` and a recommendation table (``<out>/<host>-<image>.md``).

Usage::

    python host_benchmark.py PLAN.json OUT_DIR [--repeat N] [--only STAGE ...]

Plan file (JSON)::

    {
      "volume": "/workspace/bench/RC3",
      "cases": [
        {"stage": "Mosaic",
         "command": ["nornir-build", "{volume}", "Mosaic", "-computational_library", "{library}", "-Sections", "516"],
         "env": {"MAX_PYTHON_THREADS": "{workers}"},
         "variants": [{"library": "numpy", "workers": "16"}, {"library": "cupy", "workers": "16"}]}
      ]
    }

``{volume}`` and every key of a variant are substituted into the command and env values. A variant that exits non-zero
or runs out of GPU memory is recorded as failed and never recommended.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import threading
import time
from typing import Any

import psutil

GPU_HEADROOM = 0.85  # a variant is only recommended when it peaks below this fraction of GPU memory


def gpu_memory_mib() -> tuple[int, int] | None:
    """(used, total) MiB of GPU 0 from nvidia-smi, or None when there is no NVIDIA GPU."""
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                             capture_output=True, text=True, timeout=10, check=True).stdout.splitlines()[0]
        used, total = (int(v) for v in out.split(','))
        return used, total
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def image_revision() -> str:
    """The nornir image revision from /etc/nornir-image-info, or 'dev' outside an image."""
    try:
        with open('/etc/nornir-image-info', encoding='utf-8') as f:
            for line in f:
                if line.startswith('revision='):
                    return line.split('=', 1)[1].strip()[:7]
    except OSError:
        pass
    return 'dev'


def tree_rss(proc: psutil.Process) -> int:
    """Resident bytes of a process and all its descendants."""
    total = 0
    try:
        for p in [proc, *proc.children(recursive=True)]:
            try:
                total += p.memory_info().rss
            except psutil.Error:
                continue
    except psutil.Error:
        pass
    return total


def run_variant(command: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run one command, sampling memory and disk every 0.5 s."""
    baseline_gpu = gpu_memory_mib()
    disk0 = psutil.disk_io_counters()
    start = time.perf_counter()
    proc = subprocess.Popen(command, env={**os.environ, **env}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ps = psutil.Process(proc.pid)
    peak_rss = 0
    peak_gpu = 0
    stop = threading.Event()

    def sample() -> None:
        nonlocal peak_rss, peak_gpu
        while not stop.is_set():
            peak_rss = max(peak_rss, tree_rss(ps))
            gpu = gpu_memory_mib()
            if gpu is not None and baseline_gpu is not None:
                peak_gpu = max(peak_gpu, gpu[0] - baseline_gpu[0])
            stop.wait(0.5)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    code = proc.wait()
    wall = time.perf_counter() - start
    stop.set()
    sampler.join()
    disk1 = psutil.disk_io_counters()
    moved = ((disk1.read_bytes - disk0.read_bytes) + (disk1.write_bytes - disk0.write_bytes)) if disk0 and disk1 else 0
    return {
        'exit_code': code,
        'wall_s': round(wall, 2),
        'peak_rss_gib': round(peak_rss / 2 ** 30, 2),
        'peak_gpu_mib': peak_gpu if baseline_gpu is not None else None,
        'gpu_total_mib': baseline_gpu[1] if baseline_gpu is not None else None,
        'host_disk_mb_s': round(moved / 1e6 / wall, 1) if wall > 0 else 0.0,
    }


def recommend(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per stage, the fastest successful variant that stays under the GPU headroom."""
    best: dict[str, dict[str, Any]] = {}
    for r in results:
        if r['exit_code'] != 0:
            continue
        total, used = r.get('gpu_total_mib'), r.get('peak_gpu_mib')
        if total and used is not None and used > GPU_HEADROOM * total:
            continue
        current = best.get(r['stage'])
        if current is None or r['wall_s'] < current['wall_s']:
            best[r['stage']] = r
    return best


def markdown(host: str, image: str, results: list[dict[str, Any]]) -> str:
    """All runs plus the recommendation table."""
    lines = [f'# Benchmark: {host} / {image}', '', '| stage | variant | exit | wall s | peak RAM GiB | peak GPU MiB | disk MB/s |',
             '|---|---|---|---|---|---|---|']
    for r in results:
        lines.append(f"| {r['stage']} | {r['variant']} | {r['exit_code']} | {r['wall_s']} | {r['peak_rss_gib']} | "
                     f"{r['peak_gpu_mib']} | {r['host_disk_mb_s']} |")
    lines += ['', '## Recommendation', '', '| stage | variant | wall s | peak RAM GiB | peak GPU MiB |', '|---|---|---|---|---|']
    for stage, r in sorted(recommend(results).items()):
        lines.append(f"| {stage} | {r['variant']} | {r['wall_s']} | {r['peak_rss_gib']} | {r['peak_gpu_mib']} |")
    return '\n'.join(lines) + '\n'


def main() -> int:
    """Run the plan."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan')
    ap.add_argument('out')
    ap.add_argument('--repeat', type=int, default=1)
    ap.add_argument('--only', nargs='*', default=None)
    args = ap.parse_args()

    with open(args.plan, encoding='utf-8') as f:
        plan = json.load(f)
    results: list[dict[str, Any]] = []
    for case in plan['cases']:
        if args.only and case['stage'] not in args.only:
            continue
        for variant in case['variants']:
            values = {'volume': plan.get('volume', ''), **{k: str(v) for k, v in variant.items()}}
            command = [c.format(**values) for c in case['command']]
            env = {k: v.format(**values) for k, v in case.get('env', {}).items()}
            label = ' '.join(f'{k}={v}' for k, v in variant.items())
            for _ in range(args.repeat):
                print(f"{case['stage']} [{label}] ...", flush=True)
                results.append({'stage': case['stage'], 'variant': label, 'command': command, **run_variant(command, env)})
                print(f"  {results[-1]['wall_s']} s, exit {results[-1]['exit_code']}", flush=True)

    host, image = platform.node(), image_revision()
    os.makedirs(args.out, exist_ok=True)
    stem = os.path.join(args.out, f'{host}-{image}')
    with open(stem + '.json', 'w', encoding='utf-8') as f:
        json.dump({'host': host, 'image': image, 'cpus': os.cpu_count(), 'ram_gib': round(psutil.virtual_memory().total / 2 ** 30),
                   'gpu': gpu_memory_mib(), 'results': results, 'recommended': recommend(results)}, f, indent=2)
    with open(stem + '.md', 'w', encoding='utf-8') as f:
        f.write(markdown(host, image, results))
    print('wrote', stem + '.json', stem + '.md')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
