---
name: AutoLevelPyramid Skip Logic
overview: Fix both merged pyramid operations to skip existing work correctly and build missing coarser levels even when level-1 is already up to date. Add a new `AutoLevelPyramid` pipeline entry matching `AdjustContrast` parameters.
todos:
  - id: fix-gpu-pyramid-early-return
    content: "AutolevelTilesGpuPyramid (~line 1074): replace `else: return` with BuildTilePyramids call + return"
    status: completed
  - id: fix-gpu-pyramid-post-pass
    content: "AutolevelTilesGpuPyramid (~line 1153): add BuildTilePyramids call after ConvertImagesInDictGpuPyramid"
    status: completed
  - id: fix-cpu-pyramid-early-return
    content: "AutolevelTilesAndBuildPyramid (~line 1237): replace `else: return` with BuildTilePyramids call + return"
    status: completed
  - id: fix-cpu-pyramid-post-pass
    content: "AutolevelTilesAndBuildPyramid (~line 1311): add BuildTilePyramids call after ConvertImagesInDictPyramid"
    status: completed
  - id: add-autolevel-pyramid-pipeline
    content: Add AutoLevelPyramid pipeline to Pipelines.xml with AdjustContrast parameters + optional Levels, calling tile.AutolevelTilesGpuPyramid
    status: completed
isProject: false
---

# AutoLevelPyramid: Skip Existing Work + New Pipeline

## Root Cause

Both `AutolevelTilesGpuPyramid` and `AutolevelTilesAndBuildPyramid` in [`tile.py`](nornir-buildmanager/nornir_buildmanager/operations/tile.py) share two gaps:

**Gap 1 — Early return ignores pyramid levels.** Around line 1074 / 1237, when `FilterPopulated` is true and the filter is not outdated, the function does `return` without ever checking whether coarser pyramid levels are missing:
```python
elif FilterPopulated:
    if nornir_buildmanager.operations.filter.RemoveTilePyramidIfOutdated(...):
        EntireTilePyramidNeedsBuilding = True
        (yield OutputFilterNode)
    else:
        return   # ← pyramid levels never checked
```

**Gap 2 — Post-pass misses tiles whose level-1 was already current.** When only some tiles are in `TilesToBuild`, tiles NOT in that list may still be missing coarser pyramid levels; the merged pass never touches them.

## Fix Strategy

Both gaps are resolved the same way: call the existing `BuildTilePyramids` function (non-generator, returns `PyramidNode | None`) at two points in each merged operation:

1. **At the early return** — before `return`, delegate to `BuildTilePyramids` using the already-populated `OutputFilterNode.TilePyramid`. `FilterNode.TilePyramid` is always safe to call (it auto-creates the node if absent per line 76 of `filternode.py`).

2. **After the merged pass** — call `BuildTilePyramids` on `OutputPyramidNode` (fully set up at that point). When the merged pass processed all tiles, this is a fast no-op (glob count matches → `continue` per line 2419 of `tile.py`).

### Changes to `AutolevelTilesGpuPyramid` (~line 1074) and `AutolevelTilesAndBuildPyramid` (~line 1237)

**At the early return** (identical edit in both functions):
```python
else:
    # Level-1 contrast tiles are current. Ensure any missing or incomplete
    # coarser pyramid levels are built before returning.
    result = BuildTilePyramids(PyramidNode=OutputFilterNode.TilePyramid, Levels=Levels)
    if result is not None:
        yield result
    return
```

**After the merged-pass call** (identical edit in both functions):
```python
nornir_imageregistration.ConvertImagesInDictGpuPyramid(...)   # or CPU variant

# Ensure any coarser levels still missing for tiles whose level-1 was already
# current are filled in. Fast no-op when the merged pass built all levels.
result = BuildTilePyramids(PyramidNode=OutputPyramidNode, Levels=Levels)
if result is not None:
    yield result

OutputPyramidNode.NumberOfTiles = len(ImageFiles)
(yield channel_node)
```

## New `AutoLevelPyramid` Pipeline

Add to [`Pipelines.xml`](nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml) after the existing `AdjustContrastAndBuildPyramid` entry. Parameters are a direct copy of `AdjustContrast` (Sections, Channels, Gamma, MinCutoff, MaxCutoff, InputFilter, OutputFilter, OutputBpp, InputTransform) plus the optional `Levels` argument already used by `AdjustContrastAndBuildPyramidGpu`:

```xml
<Pipeline Name="AutoLevelPyramid"
          Help="GPU-accelerated (CPU fallback) single-pass contrast adjustment
                and tile pyramid construction. Reads each source tile once,
                applies level/gamma/clip, chains 2x area-average downsamples
                for every pyramid level, and saves all levels concurrently.
                Skips tiles and levels that are already current. Equivalent to
                AdjustContrast + BuildTilePyramids in one step.">
    <!-- same Arguments block as AdjustContrast, plus -Levels -->
    <PythonCall Function="tile.AutolevelTilesGpuPyramid" .../>
</Pipeline>
```

`AutolevelTilesGpuPyramid` already falls back to `ConvertImagesInDictPyramid` (CPU) when CuPy is unavailable, so a single pipeline works on any system.

## Files Changed

- [`nornir-buildmanager/nornir_buildmanager/operations/tile.py`](nornir-buildmanager/nornir_buildmanager/operations/tile.py) — 4 edits (2 per function)
- [`nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml`](nornir-buildmanager/nornir_buildmanager/config/Pipelines.xml) — 1 addition
