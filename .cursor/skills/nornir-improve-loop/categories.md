# Where to look and what to look for

Read by the scout. Protected areas are in [protected.md](protected.md); the rules a change must pass are in [gates.md](gates.md); the metadata port is in [metadata-port.md](metadata-port.md).

## Where to look first

Prefer code that is both changed often and complex, not code that only looks untidy. At launch and with each daily report, rebuild `hotspots` in the ledger. Run the tools with `$PY -m <tool>` (see SKILL.md Environment), and run each against the Python package directories only (not `tests`, `venv`, build output, or fixtures):

- **Churn:** `git log --since="6 months ago" --name-only --format=` run inside each submodule, counted per file. Skip generated files.
- **Size and complexity:** line count, `radon cc -s -nc` (grade C or worse), and `radon mi -s` (grade B or worse).
- **Dead code:** `vulture <pkg> --min-confidence 80`. Treat results as leads, not facts; see the dynamic-reference check below.
- **Duplication:** `pylint --disable=all --enable=duplicate-code <pkg>`.
- **Lint and types:** `ruff check` and `pyright` counts per file. Never run `ruff --fix` or any auto-fixer across files; these tools are signal only.
- **Debt notes:** `TODO`/`HACK`/`FIXME`/"temporary" comments.

Rank by churn times size. Within each category, search hotspots before the rest of the scope. Hotspots are per package so no single package crowds out the others.

## What to look for

On a rotation wake, start at the category after `lastCategory` and search for an instance. If a category has none, move to the next. A wake is empty only after every category comes up empty. Category 15 is not part of the rotation; it is the port and runs on port wakes (see SKILL.md).

Refactoring:

1. **Near-duplicates.** Code that differs only by a type, constant, field, or callable. Merge into one function, parameterized helper, or a function that takes a callable.
2. **Copies across packages.** The same logic in two `nornir-*` packages (see `.cursor/issue-handoff/package-boundary-review/` for known boundary findings). Move it into the package both already depend on (usually `nornir-shared`) and delete the copies. Do not introduce a new inter-package dependency to do this.
3. **Data clumps and long parameter lists.** The same three or more parameters appear together in two or more signatures, a function takes five or more parameters, a tuple is passed or returned across several functions, or a group of attributes is always set together. Introduce one type and pass it instead:
   - `@dataclass(frozen=True, slots=True)` or `NamedTuple` for small immutable value data;
   - a plain `@dataclass` only when the group must be mutable;
   - a `TypedDict` only when the dict shape is already a serialized contract.
   Then move behavior that only uses those values onto the new type.
4. **Primitive obsession and magic values.** The same literal in several places becomes a named module constant or `Enum`. A raw `int`/`float`/`str` whose validation or conversion is repeated in two or more places becomes a small type or one helper that owns that rule.
5. **Parallel branching and type-check chains.** Two or more `if`/`elif` chains over the same key, or `isinstance` ladders. Replace with one dict dispatch table, polymorphic method, or one `match` statement.
6. **Feature envy and message chains.** A method that mostly reads another class's data moves to that class. A repeated `a.b.c.d` chain becomes one method or property on the owner.
7. **Hand-rolled helpers.** Re-implementations of the standard library, numpy/scipy/cupy, `itertools`, `pathlib`, or an existing `nornir_shared` helper. Call the existing one.
8. **Over-specific APIs.** A parameter annotated with one concrete type when callers pass several. Widen to `Iterable`, `Sequence`, `Mapping`, `os.PathLike`, or a `Protocol`. Check numpy/cupy duck typing against [Numpy-CuPy-compatibility](../../rules/Numpy-CuPy-compatibility.mdc) before widening array parameters.
9. **Long functions and deep nesting.** Functions over about 60 lines, nesting deeper than three levels, or functions mixing I/O, math, and plotting. Use guard clauses and extract the reusable piece into a pure, tested function.
10. **Speculative generality and middlemen.** Abstract base classes with one subclass, pass-through wrappers, and parameters every caller passes the same value for. Inline them. Run the dynamic-reference check first.
11. **Dead weight.** Unused functions, unread settings, environment switches with no live path, stale or repeated documentation. Run the dynamic-reference check first.
12. **Resolvable debt notes.** `TODO`/`HACK`/`FIXME` comments whose condition no longer holds or that the loop can now resolve within the gates.
13. **Bugs likely in real use.** Crashes, wrong results (including math and precision errors), leaks, and concurrency defects that real data can reach. See Bug fixes and Math and precision in [gates.md](gates.md). The Python-specific list is below.
14. **Untested code.** Production code in a hotspot or shared package with no test that would fail if it broke. Add tests only; see Test coverage in [gates.md](gates.md).
15. **The metadata port.** XML to SQLite, run as stages from [metadata-port.md](metadata-port.md). Not part of the rotation.

Performance (hot paths first: per-tile and per-cell loops, phase correlation and registration, mesh and transform math, image assemble and pyramid building, pipeline XML load/save). Every performance change needs the evidence in [gates.md](gates.md):

16. **Copies and transfers.** Array copies in loops, host to device (`.get()`, `cupy.asnumpy`) round trips, repeated `np.array(...)` of an array that is already one, avoidable `astype` conversions, concatenation inside loops.
17. **Materialization and memory.** `list(...)` or comprehensions over large inputs where a generator would do, whole-volume or whole-mosaic loads, unbounded task queues (see [Streaming-and-memory-bounded-processing](../../rules/Streaming-and-memory-bounded-processing.mdc)). Also dtype width: float64 where the pathway is float32 or the data is integer, and the reverse for accumulators (see Math and precision in [gates.md](gates.md)).
18. **Loops and data access.** Python loops over arrays that should be vectorized, repeated `find`/`findall` or dict lookups inside a loop, repeated file stat/open of the same path, re-computation of values constant across iterations, repeated enumeration of a generator via `list()`.
19. **Algorithm and data structure.** Quadratic scans that should be a set, `dict`, sort, or spatial index (`scipy.spatial`), linear search over sorted data, repeated recomputation that should be cached (`functools.cache`, only for hashable, bounded inputs), and lock contention or blocking waits in pool code. Any other change that measurably reduces time or memory on a real path qualifies here.

## Dynamic-reference check (categories 10, 11, and any rename or removal)

Static tools flag code that Nornir calls by name from data. Before deleting, renaming, or changing the signature of anything, grep the whole monorepo for the name, including:

- `Pipelines.xml` and the schema files (stages are looked up by module/function name strings);
- `importlib`, `getattr`, `__import__`, and `globals()[...]` dispatch;
- `[project.scripts]` and `[project.entry-points]` in every `pyproject.toml`, and `setup.py`;
- Sphinx autodoc under `docs/` (a public API page may reference it);
- test fixtures and `.cursor/skills`/`.cursor/rules` text that quotes the name;
- Pyre menu actions and `settings.json` keys.

A name that appears only in its own definition and in tests is a candidate; a name that appears in any of the above is not dead.

## Python-specific bug list (category 13)

Look for these in real code paths, not in test-only or dead code:

- mutable default arguments;
- bare `except:` or `except Exception: pass` that hides failures, and `assert` used for runtime validation;
- late-binding closures in loops (lambdas or inner functions capturing the loop variable), including tasks queued to pools;
- unclosed files, sockets, SQLite connections, or pool handles; missing `with`;
- `open()` without an explicit `encoding` where the data is text and non-ASCII data is possible (locale-dependent reads are invisible on a UTF-8 host);
- numpy integer overflow, for example products of `uint8`/`uint16`/`int32` dimensions or pixel counts, and unsigned subtraction wrap-around;
- exact `float ==`, and absolute epsilons that do not scale;
- `%` and `//` on negative coordinates, and `round()` banker's rounding where away-from-zero is meant;
- row/column or x/y swaps, and mixing mosaic, section, and volume coordinate spaces;
- a generator consumed twice, or `len()`/indexing on an iterator;
- `os.path` string joins that break on Windows separators, and non-atomic file replace where a crash would leave a partial file;
- thread or process pool tasks queued without a bound, or without `ReleaseStagePools()` at stage boundaries;
- shared state mutated from pool workers without a lock.

A bug that needs contrived input, or that lives in dead or test-only code, is not worth a wake; log it in `rejected`. Findings from `.cursor/nornir-bug-review-master.md` are hypotheses: follow [nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md) and [Review-driven-bugfixing](../../rules/Review-driven-bugfixing.mdc) before editing.

## Proposals

A proposal is a short plan for work the loop may not or cannot do: protected-area changes, performance work with no feasible benchmark, port decisions, and deferred work too large for one wake. Each entry has: title, area, path(s), problem, evidence, proposed change, risk, how to test or benchmark it, and estimated size. Add proposals to the ledger `proposals` list. Present new proposals in the next report; the final report lists them all. Do not open PRs or issues for them. Investigation notes may go under `.cursor/issue-handoff/` per the Monorepo rule, never in the repository root.
