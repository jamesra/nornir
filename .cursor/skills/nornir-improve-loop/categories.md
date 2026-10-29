# Where to look and what to look for

Read by the scout. Protected areas: [protected.md](protected.md); gates: [gates.md](gates.md); metadata port: [metadata-port.md](metadata-port.md).

## Where to look first

Prefer code that is both changed often and complex, not code that only looks untidy. At launch and with each daily report, rebuild `hotspots` in the ledger. Run tools as `$PY -m <tool>` (SKILL.md Environment), against Python package directories only (not `tests`, `venv`, build output, or fixtures):

- **Churn:** `git log --since="6 months ago" --name-only --format=` inside each submodule, counted per file; skip generated files.
- **Size and complexity:** line count, `radon cc -s -nc` (grade C or worse), `radon mi -s` (grade B or worse).
- **Dead code:** `vulture <pkg> --min-confidence 80`; leads, not facts (see the dynamic-reference check).
- **Duplication:** `pylint --disable=all --enable=duplicate-code <pkg>`.
- **Lint and types:** `ruff check` and `pyright` counts per file. Signal only: never run `ruff --fix` or any auto-fixer across files.
- **Debt notes:** `TODO`/`HACK`/`FIXME`/"temporary" comments.

Rank by churn times size, per package so no single package crowds out the others. Within each category, search hotspots before the rest of the scope.

## What to look for

Rotation wakes start at the category after `lastCategory` and move to the next when one has no instance; a wake is empty only after every category comes up empty. Category 15 is the port, not part of the rotation; it runs on port wakes (see SKILL.md).

**Documentation-skill compliance** is a valid reason to change code, package READMEs, or docstrings the skills cover: bring them into line with [nornir-documentation](../nornir-documentation/SKILL.md) and [Documentation-and-monodoc](../../rules/Documentation-and-monodoc.mdc). Pair it with the nearest category (often 11 for stale docs, 12 for resolvable debt, 14 when only tests are needed); it must still pass [gates.md](gates.md). Stray root-level files (`pyright_*.json`, `debug-*.log`, scratch summaries; umbrella CLAUDE.md Housekeeping) become a decision to move or delete; never delete them directly.

Refactoring:

1. **Near-duplicates.** Code differing only by a type, constant, field, or callable. Merge into one function, a parameterized helper, or a function taking a callable.
2. **Copies across packages.** The same logic in two `nornir-*` packages (known boundary findings: `.cursor/issue-handoff/package-boundary-review/`). Move it into the package both already depend on (usually `nornir-shared`) and delete the copies. Do not add an inter-package dependency to do this.
3. **Data clumps and long parameter lists.** Three or more parameters together in two or more signatures, five or more parameters, a tuple passed or returned across several functions, or attributes always set together. Introduce one type and pass it:
   - `@dataclass(frozen=True, slots=True)` or `NamedTuple` for small immutable value data;
   - a plain `@dataclass` only when the group must be mutable;
   - a `TypedDict` only when the dict shape is already a serialized contract.
   Then move behavior that only uses those values onto the new type.
4. **Primitive obsession and magic values.** A literal repeated in several places becomes a named module constant or `Enum`. A raw `int`/`float`/`str` whose validation or conversion repeats in two or more places becomes a small type or one helper owning that rule.
5. **Parallel branching and type-check chains.** Two or more `if`/`elif` chains over the same key, or `isinstance` ladders. Replace with one dict dispatch table, polymorphic method, or `match` statement.
6. **Feature envy and message chains.** A method mostly reading another class's data moves to that class. A repeated `a.b.c.d` chain becomes one method or property on the owner.
7. **Hand-rolled helpers.** Re-implementations of the standard library, numpy/scipy/cupy, `itertools`, `pathlib`, or an existing `nornir_shared` helper. Call the existing one.
8. **Over-specific APIs.** A parameter annotated with one concrete type when callers pass several. Widen to `Iterable`, `Sequence`, `Mapping`, `os.PathLike`, or a `Protocol`; check numpy/cupy duck typing against [Numpy-CuPy-compatibility](../../rules/Numpy-CuPy-compatibility.mdc) before widening array parameters.
9. **Long functions and deep nesting.** Over about 60 lines, nesting deeper than three levels, or mixing I/O, math, and plotting. **Length or a complexity grade alone is never a reason to split** (user decisions 2026-10-20 and 2026-10-29). Extract a piece only when it:
   - removes a copy: the same steps exist elsewhere, or another caller needs them (two or more real call sites after the change); or
   - makes the function easier to understand: the piece has a name that says what it does, a clear input and output, and gets its own test, ideally as a pure function.
   Guard clauses that remove nesting qualify. Never cut a function into pieces that only run one after another and pass its state between them; that moves code without making it simpler. When no extraction of either kind exists, add the function to `rejected` with that reason and move on.
10. **Speculative generality and middlemen.** Abstract base classes with one subclass, pass-through wrappers, parameters every caller passes the same value for. Inline them, after the dynamic-reference check.
11. **Dead weight.** Unused functions, unread settings, environment switches with no live path, stale or repeated documentation. Run the dynamic-reference check first.
12. **Resolvable debt notes.** `TODO`/`HACK`/`FIXME` comments whose condition no longer holds or that the loop can now resolve within the gates.
13. **Bugs likely in real use.** Crashes, wrong results (including math and precision errors), leaks, and concurrency defects real data can reach. See Bug fixes and Math and precision in [gates.md](gates.md), and the Python list below.
14. **Untested code.** Production code in a hotspot or shared package with no test that would fail if it broke. Tests only; see Test coverage in [gates.md](gates.md). A missing closed-set or documented-guarantee test qualifies. Until one exists, a schema drift test is a standing candidate: `Volumes.xsd`/`Importers.xsd` names versus the `*Node` wrappers, and `Pipelines.xml` stage names versus importable callables, failing on any difference not on a named, commented allow-list. Test-only; a drift it finds is a proposal (the schemas are protected).
15. **The metadata port.** XML to SQLite, in stages from [metadata-port.md](metadata-port.md). Not part of the rotation.

Performance (hot paths first: per-tile and per-cell loops, phase correlation and registration, mesh and transform math, image assemble and pyramid building, pipeline XML load/save). Every performance change needs the evidence in [gates.md](gates.md):

16. **Copies and transfers.** Array copies in loops, host-device (`.get()`, `cupy.asnumpy`) round trips, repeated `np.array(...)` of an existing array, avoidable `astype` conversions, concatenation inside loops.
17. **Materialization and memory.** `list(...)` or comprehensions over large inputs where a generator would do, whole-volume or whole-mosaic loads, unbounded task queues ([Streaming-and-memory-bounded-processing](../../rules/Streaming-and-memory-bounded-processing.mdc)). Also dtype width: float64 where the pathway is float32 or the data is integer, and the reverse for accumulators (Math and precision in [gates.md](gates.md)).
18. **Loops and data access.** Python loops over arrays that should be vectorized, repeated `find`/`findall` or dict lookups in a loop, repeated stat/open of the same path, recomputing loop-invariant values, repeated `list()` enumeration of a generator.
19. **Algorithm and data structure.** Quadratic scans that should be a set, `dict`, sort, or spatial index (`scipy.spatial`), linear search over sorted data, recomputation that should be cached (`functools.cache`, only for hashable, bounded inputs), lock contention or blocking waits in pool code. Any other change that measurably reduces time or memory on a real path also qualifies.

## Dynamic-reference check (categories 10, 11, and any rename or removal)

Static tools flag code Nornir calls by name from data. Before deleting, renaming, or changing the signature of anything, grep the whole monorepo for the name, including:

- `Pipelines.xml` and the schema files (stages are looked up by module/function name strings);
- `importlib`, `getattr`, `__import__`, and `globals()[...]` dispatch;
- `[project.scripts]` and `[project.entry-points]` in every `pyproject.toml`, and `setup.py`;
- Sphinx autodoc under `docs/` (a public API page may reference it);
- test fixtures and `.cursor/skills`/`.cursor/rules` text quoting the name;
- Pyre menu actions and `settings.json` keys.

A name found only in its own definition and in tests is a candidate; a name found in any of the above is not dead.

## Python-specific bug list (category 13)

In real code paths, not test-only or dead code:

- mutable default arguments;
- bare `except:` or `except Exception: pass` hiding failures; `assert` used for runtime validation;
- late-binding closures in loops (lambdas or inner functions capturing the loop variable), including tasks queued to pools;
- unclosed files, sockets, SQLite connections, or pool handles; missing `with`;
- `open()` without explicit `encoding` for text that may be non-ASCII (locale-dependent reads are invisible on a UTF-8 host);
- numpy integer overflow (products of `uint8`/`uint16`/`int32` dimensions or pixel counts) and unsigned subtraction wrap-around;
- exact `float ==`, and absolute epsilons that do not scale;
- `%` and `//` on negative coordinates; `round()` banker's rounding where away-from-zero is meant;
- row/column or x/y swaps; mixing mosaic, section, and volume coordinate spaces;
- a generator consumed twice, or `len()`/indexing on an iterator;
- `os.path` string joins that break on Windows separators; non-atomic file replace where a crash would leave a partial file;
- thread or process pool tasks queued without a bound, or without `ReleaseStagePools()` at stage boundaries;
- shared state mutated from pool workers without a lock.

## Bug patterns

Defect shapes this loop has fixed (shas from `$LOOP_ROOT/CHANGES-BY-REGION.md`). Category 13 searches these first, then `$LOOP_ROOT/BUG-PATTERNS.md` (patterns added by later sibling sweeps, gates.md Bug fixes step 8), then the list above.

- **In-place rewrite of a file another process reads:** `open(..., "w")`, `json.dump`, `.save(` on manifests, sidecars, masks, or settings a trainer, gallery, or pipeline reads. Fix: temp file plus `os.replace` (`fb679b6`, `67be3ce`, `17af738`).
- **`assert` as a runtime check** (skipped under `python -O`): `rg "^\s*assert " --glob "!**/tests/**"`. Fix: raise a real error (`1891ae7`, `249f176`, `043eda3`).
- **Connection leaked when setup after connect fails:** `sqlite3.connect(` followed by schema or pragma calls outside `with`/`try`; on Windows the bad file then cannot be deleted (`7a692df`, `5db54a9`).
- **Swallowed exception followed by a write of defaults:** a broad `except` around a load, then a save that overwrites the user's file (`caafa76`).
- **Bare `except:` hiding unexpected errors** in parsing code (`2cfbf0f`).
- **NumPy-only call on a CuPy array** (`TypeError` on device paths): `np.` helpers applied to `xp` arrays (`62ffd9f`).
- **Bare filename as an output path** crashing `os.path.dirname`-based handling (`5ca11e4`).
- **Name defined only on a rarely run branch** (`NameError`, e.g. a missing `import torch`): ruff `F821`, pyright undefined variable (`162affe`).
- **Dunder or comparison touching a missing attribute** (`cf0e068`).
- **Order reversed on every save** (`4bae68d`); **polygon holes appended to the outer ring** (`768b2ad`).

A bug needing contrived input, or living in dead or test-only code, is not worth a wake; log it in `rejected`. Findings from `.cursor/nornir-bug-review-master.md` are hypotheses: follow [nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md) and [Review-driven-bugfixing](../../rules/Review-driven-bugfixing.mdc) before editing.

## Proposals

A proposal is a short plan for work the loop may not or cannot do: protected-area changes, performance work with no feasible benchmark, port decisions, and deferred work too large for one wake. Fields: title, area, path(s), problem, evidence, proposed change, risk, how to test or benchmark it, estimated size. Add to the ledger `proposals` list; present new ones in the next report; the final report lists them all. Do not open PRs or issues for them. Investigation notes may go under `.cursor/issue-handoff/` per the Monorepo rule, never in the repository root.
