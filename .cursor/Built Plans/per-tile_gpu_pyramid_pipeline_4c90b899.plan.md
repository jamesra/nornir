---
name: Per-tile GPU Pyramid Pipeline
overview: Redesign `ConvertImagesInDictGpuPyramid` from a chunk-based GPU loop into a true per-tile streaming pipeline. Each tile is fully processed (contrast + full pyramid chain) as soon as it arrives from the NFS loader, and all level saves are dispatched immediately — eliminating chunk assembly latency and enabling true 3-way load/GPU/save overlap.
todos:
  - id: per-tile-gpu-pyramid
    content: "Replace the chunk loop in ConvertImagesInDictGpuPyramid with a per-tile streaming loop: single-tile pinned buffer, per-tile H→D, contrast, pyramid chain, immediate per-level save dispatch, and repurpose batch_bytes as prefetch worker count"
    status: completed
isProject: false
---

# Per-tile GPU Pyramid Pipeline

## Current Bottlenecks

`ConvertImagesInDictGpuPyramid` in [`_core.py`](nornir-imageregistration/nornir_imageregistration/core/_core.py) uses a **chunk loop** (lines 1243–1336):

- GPU waits for all `chunk_size` tiles to load before starting any GPU work
- All pyramid levels for the whole chunk are computed before any saves are dispatched
- Result: GPU idles waiting for the slowest tile per chunk; saves lag by one full chunk

## Proposed Pipeline

Replace the chunk loop with a per-tile streaming loop. The three stages overlap naturally:

```
NFS loader threads  ──▶  load_queue  ──▶  GPU (main thread)  ──▶  save_pool threads
  tile 1 loading                           contrast(tile 1)         save L1/L2/... tile 0
  tile 2 loading                           pyramid(tile 1)          save L1/L2/... tile 0 cont.
  tile 3 loading          tile 2 ready     contrast(tile 2)         save L1/L2/... tile 1
  ...                                      pyramid(tile 2)          ...
```

While the GPU processes tile N, tiles N+1 through N+k are already loading, and tile N-1's levels are being saved in parallel.

## Key Implementation Changes (all in `ConvertImagesInDictGpuPyramid`)

**1. Single-tile pinned buffer** (replaces chunk-sized slab)

```python
# Before: chunk_size * tile_float32_bytes
pinned = cp.cuda.alloc_pinned_memory(tile_float32_bytes)  # one tile
pinned_buf = np.frombuffer(pinned, dtype=np.float32,
                            count=tile_float32_elems).reshape(tile_shape)
```

**2. Per-tile GPU loop** (replaces `for chunk_idx in range(n_chunks):`)

```python
for i, (in_path, out_path) in enumerate(zip(input_paths, output_paths)):
    arr = first_array if i == 0 else all_load_tasks[i].wait_return()
    if arr is None:
        continue
    if arr.shape != tile_shape:
        # per-tile CPU fallback (same logic as existing chunk fallback)
        ...
        continue

    # Single-pass cast + scale into pinned buffer (no intermediate alloc)
    np.multiply(arr, scale, out=pinned_buf, casting='unsafe')

    # H→D: single-tile DMA
    gpu_tile = cp.asarray(pinned_buf)          # (H, W) float32

    # GPU: contrast (works on (H, W) via ... indexing)
    gpu_tile = _apply_contrast_gpu(gpu_tile, min_val, max_val, gamma_val,
                                    max_int_val if is_int else None)

    # Level 1: D→H + dispatch save immediately
    result_l1 = cp.asnumpy(gpu_tile.astype(original_dtype))
    save_pool.add_task(f"save {out_path}", SaveImage,
                        out_path, result_l1, bpp=OutputBpp, optimize=is_png(out_path))

    # Pyramid levels: chain in float32 on GPU, D→H + save each level immediately
    prev = gpu_tile
    for pyr_output_dict in PyramidOutputDicts:
        prev = _downsample2x_gpu(prev)         # (H, W) → (H//2, W//2)
        pyr_out = pyr_output_dict.get(in_path)
        if pyr_out is None:
            continue
        result_pyr = cp.asnumpy(prev.astype(original_dtype))
        save_pool.add_task(f"save {pyr_out}", SaveImage,
                            pyr_out, result_pyr, bpp=OutputBpp, optimize=is_png(pyr_out))
    del gpu_tile, prev
```

**3. Repurpose `batch_bytes` as prefetch-worker count**

The number of NFS loader workers now controls how many tiles load concurrently while GPU is busy:

```python
prefetch_count = max(1, batch_bytes // tile_float32_bytes)
num_load_workers = min(prefetch_count, n_tiles)
load_pool = nornir_pools.GetThreadPool("..._load", num_load_workers)
```

For a 64 MB budget: 64 MB / 16 MB per 1× 4K tile = 4 parallel loaders, or 64 MB / 4 MB per 4× tile = 16 loaders. This scales naturally with tile size.

**4. CPU fallback path** updated to per-tile (existing chunk fallback logic ported directly).

## What Does NOT Change

- `_apply_contrast_gpu` and `_downsample2x_gpu`: both use `...` trailing-dimension indexing so they work unchanged on `(H, W)` single tiles.
- File staleness / skip logic: remains in `AutolevelTilesGpuPyramid` in [`tile.py`](nornir-buildmanager/nornir_buildmanager/operations/tile.py). `ConvertImagesInDictGpuPyramid` receives pre-filtered input dicts — no change there.
- `ConvertImagesInDictGpu` (non-pyramid, contrast-only): kept as-is. Its GPU work per tile is tiny so chunking remains the right strategy there.
- All callers of `ConvertImagesInDictGpuPyramid`: signature unchanged (`batch_bytes` is still accepted, just reinterpreted).

## File Changed

- [`nornir-imageregistration/nornir_imageregistration/core/_core.py`](nornir-imageregistration/nornir_imageregistration/core/_core.py) — replace chunk loop in `ConvertImagesInDictGpuPyramid` with per-tile loop (~90 lines changed, ~same size)
