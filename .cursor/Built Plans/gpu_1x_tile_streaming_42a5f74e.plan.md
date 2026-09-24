---
name: GPU 1x tile streaming
overview: "Switch ConvertImagesInDictGpu from chunk-based batching to per-tile streaming. Two root causes explain the 0.54× result at 1x: a 2 GB pinned-memory allocation that the chunk loop requires, and 64 MB numpy arrays being pickled across process boundaries into the save pool. Fixing both narrows the gap with the CPU path significantly."
todos:
  - id: streaming-rewrite
    content: Replace chunk loop in ConvertImagesInDictGpu with per-tile streaming + single-tile pinned buffer + np.copyto(casting=unsafe) copy chain
    status: completed
  - id: save-thread-pool
    content: Switch save_pool from GetMultithreadingPool to GetThreadPool to eliminate 64 MB/tile pickle overhead
    status: completed
  - id: benchmark-verify
    content: Re-run bench_adjust_contrast.py on 4x (128 tiles) and 1x (32 tiles) to verify no regression and improved 1x performance
    status: completed
isProject: false
---

# GPU 1× Tile Streaming

## Why 1× tiles are slower with the current implementation

For 32 × 4096² tiles the current path does:

```
chunk_size = 31          → allocate 31×67 MB = 2 GB pinned buffer
                         → for each tile: arr.astype(float32)*scale  (2×67 MB temps)
                                          np.copyto → pinned  (3rd copy)
                         → H→D 2 GB  (~125 ms)
                         → GPU compute
                         → D→H 2 GB  (~125 ms)
save_pool = GetMultithreadingPool  → 32×67 MB arrays pickled into subprocesses
wait save_pool
```

Two specific killers:

1. **2 GB pinned allocation** — OS must physically lock 2 GB of RAM. Allocation latency alone is hundreds of milliseconds. Also forces 2 GB × 3 copy-chain host operations before the first tile touches the GPU.

2. **64 MB pickle per save tile** — `GetMultithreadingPool` is a process pool. Every `save_pool.add_task(out_path, SaveImage, out_path, tile_result)` serialises a 64 MB numpy array into a pipe. For 32 tiles that is 2 GB of IPC serialisation. The CPU path avoids this entirely — `_ConvertSingleImageToFile` workers load, convert, and save *inside* the subprocess; nothing large crosses the process boundary.

## Proposed fix — two targeted changes

### Change 1: Per-tile streaming (replaces chunk loop)

Submit all N load tasks upfront as before (process pool, no CuPy in workers → no fork hazard). Then instead of accumulating a chunk window, process each tile individually as it arrives:

```python
# single-tile pinned buffer — 67 MB, not 2 GB
tile_elems = int(np.prod(tile_shape))
pinned = cp.cuda.alloc_pinned_memory(tile_elems * 4)
pinned_buf = np.frombuffer(pinned, dtype=np.float32,
                           count=tile_elems).reshape(tile_shape)

for i in range(n_tiles):
    arr = all_load_tasks[i].wait_return()     # likely already loaded (pool is ahead)
    np.copyto(pinned_buf, arr, casting='unsafe')  # uint16→float32, zero temps
    pinned_buf *= scale                           # in-place scale, zero temps

    tile_gpu = cp.asarray(pinned_buf)         # H→D ~4 ms for 67 MB
    tile_gpu = _apply_contrast_gpu(tile_gpu, ...)  # <1 ms
    tile_gpu = tile_gpu.astype(original_dtype)
    result = cp.asnumpy(tile_gpu)             # D→H ~4 ms
    del tile_gpu

    save_pool.add_task(out_path, SaveImage, out_path, result, ...)
```

Why this works:
- All 32 NFS reads run in parallel from t=0. By the time the GPU loop reaches tile N, it is almost always already loaded.
- GPU loop processes 32 tiles × ~9 ms overhead each = ~290 ms total (near-zero wait).
- The chunk barrier (wait for 31 tiles before first GPU work) disappears.

PCIe bandwidth cost does not change: whether batched (1×2 GB) or streaming (32×67 MB), total data moved = 2 GB in each direction.

### Change 2: Thread pool for saves (eliminates the 2 GB IPC cost)

```python
# Before:
save_pool = nornir_pools.GetMultithreadingPool(...)   # process pool → pickle

# After:
save_pool = nornir_pools.GetThreadPool(...)            # thread pool → shared memory
```

PNG encoding is dominated by zlib (a C extension that releases the GIL), and NFS writes release the GIL for I/O. Thread-pool workers are genuinely parallel for both operations. No large arrays are serialised.

## Expected timeline (32 × 4096² tiles)

```
t=0        submit 32 load tasks to process pool (parallel NFS reads)
t≈0.5s    tile 0 ready → GPU processes in ~9 ms → save dispatched to thread pool
t≈0.51s   tile 1 ready (loading in parallel since t=0) → GPU...
...
t≈0.8s    all 32 tiles processed by GPU
t=0..0.8s  saves run in parallel via thread pool (overlapping entirely)
t≈1.5s    wait_completion: 32 parallel NFS writes complete

Total: ~1.5s  vs CPU 3.0s  →  ~2× improvement
```

Compare current GPU path: 5.6s. Compare old chunked path: also ~5.6s.

## File to change

[`nornir-imageregistration/nornir_imageregistration/core/_core.py`](nornir-imageregistration/nornir_imageregistration/core/_core.py) — `ConvertImagesInDictGpu` only (lines ~676–895). The helpers `_gpu_chunk_size` and `_apply_contrast_gpu` are unchanged. No changes to `tile.py`, `Pipelines.xml`, or `.vscode/launch.json`.

## What stays the same

- All load tasks are still submitted upfront (max NFS concurrency).
- `_apply_contrast_gpu` is called identically.
- Shape-consistency check and fallback to `_ConvertSingleImage` still exist.
- `_gpu_chunk_size` stays (useful for callers that may want batch sizing in future).

## Benchmark plan

Re-run `bench_adjust_contrast.py` on both tile levels:

- `--tile-dir .../TilePyramid/004` (4×, 128 tiles, 1024²)  — verify no regression
- `--tile-dir .../TilePyramid/001` (1×, 32 tiles, 4096²)  — verify improvement
