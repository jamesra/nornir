# Nornir agent guidelines

Project-wide guidance for AI coding agents working in the Nornir umbrella repository.
These rules were migrated from `.cursor/rules/` and mirror the per-rule files in
`.aiassistant/rules/`. Sections marked **(scoped)** apply only to the file types noted;
all other sections always apply.

---

## Virtual environment

The default virtual environment for Nornir is at `D:\src\git\nornir\venv\pyre314`.

---

## Design-choice confirmation

### When to speak up

Before implementing—or when a plan embeds it—flag **material** concerns if the approach involves: security or data-safety risk; APIs or structure that are hard to revert; **violation of established rules** in these guidelines or `.aiassistant/rules/`; obvious maintenance traps; or "clever" shortcuts that trade clarity for brevity.

### What to do

Briefly name the concern, state the **main tradeoff**, and offer **one or two** reasonable alternatives when practical.

### Confirmation

**Do not** implement the questionable path until the user **explicitly confirms** they want it (for example: "yes, proceed with X despite Y"). If they already clearly chose that path **after** the warning, you may proceed.

### Non-negotiable project rules

Requirements in these guidelines (for example **must not** or **do not**) are **default non-negotiable**. Do not treat "confirm override" as permission to skip them **unless** the user **explicitly states in writing** that they accept overriding that rule for this change. Illegal or clearly unsafe requests remain out of scope for silent compliance—warn and refuse if appropriate.

### What not to do

Do not nitpick minor style preferences. Reserve this for **material** design impact.

---

## Unified Nornir logging convention

### Purpose

Ensure all Nornir Python projects write persistent logs through one shared convention managed by `nornir-shared`.

### Required behavior

- Initialize persistent logging with `nornir_shared.misc.SetupLogging`.
- Use environment variable `NORNIR_LOG_ROOT` as the root directory for file logs.
- Do not hardcode absolute log paths in project modules.
- Do not create ad hoc debug files (for example `debug-*.log`, repo-root log files, or project-specific log directories).
- Keep project identity in logger names/record content, not in per-project file names.

### Ownership boundaries

- `nornir_shared.misc` owns file log location and naming conventions.
- `nornir_shared.prettyoutput` is presentation-layer output and must not own file log sink paths.

### Session layout

When `NORNIR_LOG_ROOT` is defined, log files should follow:

- `<NORNIR_LOG_ROOT>/<YYYY-MM-DD>/nornir-session-<YYYYMMDD-HHMMSS>.log`
- `<NORNIR_LOG_ROOT>/<YYYY-MM-DD>/nornir-session-<YYYYMMDD-HHMMSS>-errors.log`

Use one parent-created session ID and reuse it across child processes in the same run.

### Multiprocessing requirements

- Use `nornir_shared.misc.StartMultiprocessLoggingListener(...)` in the parent process before creating worker processes.
- Configure workers with `nornir_shared.misc.ConfigureWorkerQueueLogging(...)` so workers emit through `QueueHandler`.
- Use `nornir_shared.misc.StopMultiprocessLoggingListener()` on shutdown.
- Do not attach direct file handlers independently in worker processes.

---

## Python standards **(scoped: `**/*.py`)**

When editing or generating Python:

- Place imports at the top of the file.
- Define class member variables on the class with type annotations before `__init__`.
- Add type annotations to all function parameters, return types, and variables where practical.
- Add a PEP 257 docstring to each non-trivial function (not one-line trivial wrappers) with a brief one-line summary of its purpose.
- Extend the docstring only when behavior, arguments, or return value are non-obvious.

Example:

```python
class VolumeLoader:
    _index: int

    def __init__(self, index: int) -> None:
        self._index = index

    def load_volume(self, url: str) -> Volume:
        """Load a volume descriptor from the given URL."""
```

---

## NumPy / CuPy compatibility **(scoped: `nornir_imageregistration`)**

### Picking the array module (`xp`)

- **`xp = nornir_imageregistration.GetComputationModule()`** -- Use when there is no input array yet and code should follow the process-wide backend (numpy vs cupy), e.g. allocating scratch buffers for the active lib.
- **`xp = cp.get_array_module(x)`** -- Use when behavior must match a **specific** array `x` (or the first of several related arrays). Prefer this for helpers that transform data: keep outputs on the same kind of array as the inputs (numpy in -> numpy out; cupy in -> cupy out).

Transitioning from system memory (numpy) and gpu memory (cupy) is very expensive. Transitions should be kept to the minimum number possible.
- **Do not** use `import cupy as xp` or other aliases that steal the name `xp` from this meaning.

### Execution locality and transfer cost

- **Default to the input array's backend** and use the `xp` namespace for operations.
- **Do not move arrays between CPU and GPU unless there is a clear net benefit.** Host<->device transfers and synchronization are expensive and can dominate runtime.
- CPU fallback is acceptable when all of the following are true:
  - input data is small (use a configurable threshold, not a magic number),
  - there is little or no likely performance gain from running the operation on GPU,
  - and fallback does not create repeated CPU<->GPU ping-pong in loops or pipelines.
- A second explicit CPU fallback case is a **CuPy session without needed spatial support** (for example, missing functionality commonly available in Linux CUDA/CuPy environments). In that case, transfer only for unsupported spatial steps, then continue with CuPy for the rest of the pipeline whenever practical.
- If conversion is required, perform it at a **single explicit boundary**, document why, and keep subsequent work on that side until completion.

### Single code path with `xp`

- For operations on arrays whose backend is chosen above, call **`xp.linalg`**, **`xp.sum`**, **`xp.zeros`**, etc., not hard-coded **`np.*`** or **`cp.*`**, unless you are at an intentional boundary (see below).
- **CuPy is not a full NumPy clone.** Do not assume every `numpy` API exists on `xp`. If something is missing on CuPy, branch **only** when necessary--e.g. use NumPy for that call after a documented `.get()` / `np.asarray`, or when the NumPy path is clearly required or faster (e.g. `numpy.delete`).
- Prefer **one conversion, many operations** over repeated conversion hops.

### SciPy vs CuPyX (`cupyx.scipy`)

- When calling SciPy-family routines that have CuPyX equivalents (**ndimage**, **fft**, **spatial.distance**, etc.), resolve the implementation from the array:

  `sp = cupyx.scipy.get_array_module(array)` then e.g. `sp.ndimage.rotate`, `sp.fft.fftshift`.

- Use **CPU SciPy** only when there is **no** suitable CuPyX API, when required spatial support is unavailable in the active CuPy environment, or when the algorithm is inherently host-based. At that boundary, pass **NumPy arrays** (e.g. `np.asarray(x.get())` for CuPy `x`). Examples: **Qhull / `scipy.spatial.Delaunay`**, **`scipy.spatial.transform.Rotation`**. Do not pass CuPy arrays into those calls without converting.

### Anti-patterns

- **`cp.asarray(scipy.some_func(...))`** as a default -- avoids type errors but forces host work and sync; prefer `cupyx.scipy` when available, or a small dispatcher (e.g. cdist) that chooses GPU vs CPU explicitly.
- Repeated `.get()` / `cp.asarray()` inside iterative code paths (hidden CPU<->GPU ping-pong).
- **`UsingCupy()`** or **`GetComputationModule() == np`** to decide output type when the API receives a concrete array -- prefer **`cp.get_array_module(input_array)`** so callers on NumPy are not upgraded to CuPy (or vice versa) by global settings alone.

### Thunks

- When CuPy is unavailable, **`nornir_imageregistration.cupy_thunk`** and **`cupyx_thunk`** stand in for `cp` / `cupyx.scipy`; the same `get_array_module` patterns should still read as "numpy path" vs "cupy path" in code reviews.

---

## Streaming and memory-bounded processing **(scoped: `nornir-buildmanager`, `nornir-imageregistration`, `nornir-pools`, `nornir-shared`)**

### Core principle

**Bound peak memory by design.** Treat full-dataset loads as the exception. Prefer pipelines where a producer emits work units (paths, tiles, slabs, records) and consumers process them with bounded in-flight buffers.

### Required behavior

- **Stream work, don't hoard it.** Use generators/iterators (`yield`, `yield from`, `Iterator`) to enumerate files, tiles, sections, or records. Buildmanager stages return generators saved incrementally by `PipelineManager._SaveNodes`. Prefer per-item processing over `list(...)` / list comprehensions over large inputs unless size is provably small.
- **Chunk large arrays and images.** Process in tiles or slabs (`ImageToTilesGenerator`, tile loops in `TransformImage`, chunked transforms). Expose chunk/tile size as a parameter or derive from available memory (`EstimateMaxTempImageArea`).
- **Spill to disk when outputs are large.** Use `np.memmap`, temp files, or `memmap_metadata` for buffers that would exceed RAM. Pass **paths or metadata** across process boundaries; avoid pickling large arrays (`npArrayToSharedArray` falls back to file-backed memmap when shared memory is too small).
- **Parallelize I/O with bounded concurrency.** Use `nornir_pools` thread pools for I/O-bound work; process pools for CPU-bound stages. Apply **backpressure** when queueing—do not enqueue unbounded tasks (gate on queue depth or wait per row/column). Call `ReleaseStagePools()` at stage boundaries.
- **Overlap I/O and compute.** Prefetch or copy inputs locally for network paths before many small reads. Queue the next read/transform while the current unit is processed.

### When full in-memory load is acceptable

Document the reason:

- Input is **provably small** (metadata, config, single tile)—use a configurable threshold, not a magic number.
- Algorithm requires a global pass with no practical streaming alternative (rare; call out in review).
- Prototype/debug code (must not ship to production pipelines without revisiting).

### Anti-patterns

- `read()` or `np.array(...)` of an entire volume, mosaic, or file list when sequential access suffices.
- Accumulating all results in a list/dict before writing any output.
- Unbounded `pool.add_task` loops without queue-depth or row/column gates.
- Repeated `.get()` / host copies inside loops (see NumPy/CuPy rule).
- Loading remote datasets entirely into RAM to avoid temp/cache dirs when level-based temp dirs are the established pattern.

### Examples

```python
# Good — generator pipeline stage
def ExportTiles(...):
    for tile_path in iter_tile_paths(source_dir):
        write_tile(tile_path)
        yield volume_node

# Bad — load everything first
all_tiles = [load_tile(p) for p in glob.glob(f"{dir}/*.png")]
for tile in all_tiles:
    process(tile)
```

---

## Documentation and monodoc **(scoped: `docs/**`, `**/README.md`, `nornir-pyre/README.rst`)**

### Monodoc layout

- Narrative and API documentation for the whole Nornir umbrella live under **`docs/`** with a single root **`index.rst`** and one coherent toctree.
- **Do not** edit the built HTML in the separate **`nornir.github.io`** repository by hand; that repo receives **deploy output** from CI (see **`docs/development/publishing_documentation.rst`**).

### reStructuredText vs Markdown

- Prefer **`.rst`** for new manual pages (directives, toctrees, cross-references).
- Use **`.md`** when content is short or requires no special formatting; enable via **`myst_parser`** (see **`docs/conf.py`**). Example: **`docs/development/markdown_in_sphinx.md`**.

### Package `README.md` (or `README.rst`)

- Each **`nornir-*`** package keeps a **short** landing file: what the package does, links to **https://nornir.github.io/**, links to that package's section and **API** pages.
- **Do not** duplicate long guides or hand-maintained API listings in READMEs; link to Sphinx autodoc instead.

### Publishing

- Cross-repo deploy uses **`NORNIR_GITHUB_IO_DEPLOY_TOKEN`** (see publishing doc). Never commit tokens.

---

## PowerShell scripts **(scoped: `**/*.ps1`)**

If a PowerShell script is generated as the response: start the script documentation following PowerShell's standard comment-based help format. Include the purpose of the script and the problem it was generated to solve, which may be the same.
