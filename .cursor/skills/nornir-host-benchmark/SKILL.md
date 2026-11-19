---
name: nornir-host-benchmark
description: >-
  Profile a build host once (numpy vs cupy, worker counts, GPU memory, RAM, disk throughput) for the stages that have a
  GPU path, and write per-host, per-image results and a recommendation table, so agents choose the library and worker
  count consistently instead of guessing per run. Use on a new host, after an image upgrade that touches Mosaic/prewarp,
  Assemble, StosBrute, Refine or the crush import, or when asked which library or worker count to use.
---

# Host benchmark

Agents used to pick `-computational_library` and worker counts per run: `cupy` where it helped, `numpy` when the GPU ran
out of memory (RC3 grid prewarp on the 24 GB card). This skill measures once per host and image and records the answer.

Related: `nornir-debug-profiling` (PhaseProfiler, where time goes inside one run), the `Nornir-performance-envelope` rule
(NAS, RAM per core, GPU class), `Performance-evidence` (measured before/after on real data).

## What it measures

For each variant of each stage, run alone: wall time, peak RAM of the process tree, peak GPU memory growth over the idle
baseline (`nvidia-smi`), and host-wide disk throughput while it ran (an approximation; the NAS is not separated out).

## Procedure

1. Check nothing else uses the GPU or the machine (`nvidia-smi`, `docker ps`): variants run one at a time and need an idle host.
2. Pick a standard test volume on **local disk** (not the NAS) with a few sections that have tiles, a Stage mosaic and, for
   alignment stages, neighbours. Copy it to the container's scratch space; delete it afterwards.
3. Write a plan (`plan.json`; format in the script's docstring). One case per stage with a GPU path:
   - Mosaic (grid prewarp): `Prune` then `Mosaic -InputTransform Prune -OutputTransform Grid`
   - Assemble: `Assemble -Transform Grid -Downsample 8,16,32`
   - StosBrute: `-GpuWorkers` values (0 = auto, 1, 4, 8)
   - Refine: Grid32 on a few pairs
   - Crush import: `ImportMRC`/`ImportIDoc` with `-CropTo` as the volume needs (never `-CameraBpp`)
   Variants: `library` numpy/cupy and a few `workers` values (`MAX_PYTHON_THREADS`, `-GpuWorkers`).
4. Run inside the container (so the image revision is recorded):
   `python ~/.claude/skills/nornir-host-benchmark/scripts/host_benchmark.py plan.json /projects/benchmarks`
   (the image deploys the skill there; outside an image use the repo path). For a long plan use the **notify-dont-poll** skill; do not poll.
5. Results: `<out>/<host>-<image>.json` (everything, including the commands) and `<out>/<host>-<image>.md` (all runs plus
   the recommendation). Keep them in `/projects/benchmarks/` (persistent) and, on a build host, link them from the host's
   facts file.

## How the recommendation is chosen

Per stage: the fastest variant that exited 0 and peaked below 85% of GPU memory. A variant that failed (including a GPU
out-of-memory) is never recommended. Treat a recommendation as valid for that host and image revision only.

## When to rerun

After an image upgrade that touches Mosaic/prewarp, Assemble, StosBrute, Refine or the crush import; on a new host; after a
GPU or RAM change. Do not rerun for unrelated image upgrades.

## Limits

- One run per variant by default (`--repeat N` for more). Wall times on a shared NAS vary; use local scratch.
- Disk throughput is host-wide, so anything else running distorts it. Memory growth of other GPU users distorts GPU numbers.
- The plan is not shipped with defaults for any volume: choose the test volume and sections for the host.
