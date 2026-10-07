# Gates: what a change must pass

Read by the implementer and the reviewer. Protected areas are in [protected.md](protected.md). Port wakes also follow the port gates in [metadata-port.md](metadata-port.md).

All commands run with `$PY` (see SKILL.md Environment) and `NORNIR_HEADLESS=1` (see [nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md)). Test artifacts go under `TESTOUTPUTPATH`, logs follow the [Unified-Logging-Convention](../../rules/Unified-Logging-Convention.mdc), and scratch notes go under `.cursor/issue-handoff/`; never write them in the repository root.

## Accept a change only if all hold

- **Not protected.** The change edits nothing in Protected areas.
- **Real callers.** Every generalization serves two or more existing call sites. No code for hypothetical callers.
- **Net simpler.** For refactoring, production code gets shorter, or a rule that lived in several places now lives in one. Performance changes may add a little code if the measured gain is real and the code stays readable.
- **No new flags.** Do not merge functions with a `bool` or mode parameter that picks between old bodies.
- **Structural, not cosmetic.** Renames, formatting, import sorting, quote style, and annotation-only edits do not count as a wake's change on their own. They may ride along with a structural change in the same lines.
- **Semantics traps checked.** Check each caller for the trap that applies:
  - a generator replacing a list is lazy and single-use;
  - a dataclass gains `__eq__` and, if frozen, `__hash__` (check dict keys, sets, `==`, identity checks);
  - a mutable default or shared module-level object now shared;
  - a numpy view versus copy, dtype promotion, and C versus F order;
  - a NumPy/CuPy change that silently pulls arrays to the host or promotes dtype;
  - `functools.cache` on a method keeps `self` alive;
  - import-time side effects, circular imports, and pickling across `nornir_pools` process pools.
- **Same behavior.** A test pins the old behavior before the edit and passes after it. Bug fixes are the one exception; they follow Bug fixes.
- **Output parity on stable paths.** For importers, image I/O, coordinates, and transforms, follow [Stable-path-output-parity](../../rules/Stable-path-output-parity.mdc): compare outputs before and after on real data, not just unit tests. If no real data is available on this machine, write a proposal instead of editing.
- **Nornir rules respected.** Apply the glob-scoped rules that match the files touched (indexed in [AGENTS.md](../../../AGENTS.md)): [python-standards](../../rules/python-standards.mdc), [Numpy-CuPy-compatibility](../../rules/Numpy-CuPy-compatibility.mdc), [Pyre-host-array-boundary](../../rules/Pyre-host-array-boundary.mdc), [Streaming-and-memory-bounded-processing](../../rules/Streaming-and-memory-bounded-processing.mdc), [Serial-batched-primitives](../../rules/Serial-batched-primitives.mdc), [Refine-grid-trust-questions](../../rules/Refine-grid-trust-questions.mdc), and [Pyre-STOS-rigid-transform-UI](../../rules/Pyre-STOS-rigid-transform-UI.mdc). A change that would violate a `must not` or `do not` in a rule is a decision, not a commit.
- **Reviewable size.** About 300 changed lines at most. Larger work goes to `deferred` with a one-line plan; do a smaller slice now if one exists.
- **Works wherever it is used.** A change to a shared package (`nornir-shared`, `nornir-pools`, `nornir-imageregistration`) runs the covering tests of every package that imports the changed names (grep first). Check CuPy-guarded paths still import on a machine without CuPy.
- **Comments.** Keep comments that state a contract, threading rule, or edge case. Edited functions keep or gain PEP 257 docstrings per [python-standards](../../rules/python-standards.mdc). Do not delete a correct comment; if unsure whether one is still correct, prefix it with `?? AI Changed Code after comment ??`.

If no candidate passes, revert and add `{ path, category, reason }` to `rejected`. Skip rejected paths later unless the code around them changed.

## Bug fixes

The loop may fix bugs that are likely to occur in real use, without asking first. A bug qualifies when ordinary use, real volume data, or real pipeline runs can reach it. The Python-specific checklist is in [categories.md](categories.md). Bugs that need contrived input, or that sit only in dead or test-only code, are not worth a wake; log them in `rejected`.

How to fix one (this is [nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md) in short):

1. Treat the suspicion as an unproven hypothesis. Reproduce it first with a test that fails on the current code. Prefer a Hypothesis property test that generates the triggering inputs. If it cannot be reproduced on this machine, write a proposal and leave it unfixed.
2. **The regression test must fail against the old behavior.** Verify by stashing the fix or reverting the production lines, and record the count ("3 of 3 fail against the old code") in the commit message. Commit the test only after it passes with the fix.
3. Before attributing any suite failure to the change, re-run it on a stashed baseline. Compare failure sets across repeats; several suites carry known failures and flaky tests.
4. Make the smallest fix that turns the test green. Fix only the defect. If the fix would change user-visible behavior beyond removing the defect (UI flow, defaults, what gets saved), add it to `decisions` instead.
5. Prefer warn over raise when a run in the degraded state still produces correct results and the defect is that it was silent; throttle the warning if the call is hot.
6. For a bug a Pyre user could notice, add one line to `nornir-pyre/CHANGELOG.user.md` under its unreleased section in the same commit.
7. If the bug is in a protected area, or cannot be reproduced outside a GUI, a GPU, or a live service, write a proposal with the evidence and the likely fix.

## Math and precision

This is scientific code: registration, transforms, mosaics, and measurements feed research results. A math or precision error counts as a bug likely in real use whenever real data can reach it. Check types against the data they hold: tile and mosaic coordinates reach the hundreds of thousands of pixels, section numbers run into the thousands, and values are later converted to physical units.

Math errors to look for:

- integer overflow or truncation in numpy (products of image dimensions in `uint16`/`int32`, unsigned subtraction wrap-around), and `//`, `%`, and `int()` on negative coordinates where `floor` is meant;
- `round()` (banker's rounding) where away-from-zero is meant, and `np.round` versus `round` differences;
- degrees versus radians, and swapped x/y or row/column order (see `nornir-imageregistration/docs/flip_flop_mosaic_coordinates.md`);
- wrong coordinate space (tile, mosaic, section, volume, screen) or a missing unit conversion (pixels to nm);
- catastrophic cancellation: subtracting nearly equal large numbers in orientation, area, or distance tests; subtract a nearby origin first;
- normalizing a zero-length vector, inverting a singular or near-singular transform, and `NaN` or infinity spreading silently;
- long sums that drift (use `math.fsum`, pairwise `np.sum`, or accumulate in float64), and squared distances that overflow float32;
- **precision round trips:** a value narrowed (float64 to float32, int64 to int32) to fit one function, then widened again by the caller or the next step. The precision is lost for nothing, and every conversion costs time plus an array copy. Match the pathway's precision instead of narrowing the data. Narrow once, at the true boundary where lower precision is consumed (GPU upload, file write, OpenGL texture), and clamp there when the value can exceed the target's range. This includes implicit promotion by mixed-dtype arithmetic and by Python scalars. The serial/batched skill documents measured examples; do not reintroduce an unconditional float64 upcast.

Precision of types:

- **Under-precise:** float32 holding mosaic-space coordinates, accumulated transforms, or long sums, where about 7 significant digits lose sub-pixel accuracy at real magnitudes. Use float64 for geometry and measurement. Image data and GPU-bound arrays may stay float32.
- **Overly precise:** float64 for data that is inherently coarse, such as pixel intensities or tile indices. Narrow only with a measurement and a test showing results stay within the data's real resolution, and only if neighbors in the pathway would not cast back up.
- **Cost of changing precision:** count the conversions the change adds or removes along the whole pathway, not just at the edited function. Prefer the option with fewer conversions. When precision and speed conflict, keep precision unless real-data measurements show the gain matters and a test shows the loss stays within the data's resolution.
- **Comparisons:** a fixed absolute epsilon is wrong across magnitudes. Use `np.isclose`/`math.isclose` with a relative tolerance sized to the data, and name the constant with a comment on where the value comes from.

## Test coverage

Every change is covered by a test that would fail if the change were wrong. Follow [hypothesis-testing](../hypothesis-testing/SKILL.md).

1. **Hypothesis property tests**, the default. Good properties: round trips (serialize then parse, transform then inverse), invariants (bounds contain every point, area is never negative), old-versus-new equivalence for refactors on generated inputs, agreement with a slow obviously correct reference, and for numeric code, equality across chunk sizes and across NumPy/CuPy backends where CuPy is available. For numerical code:
   - build valid inputs directly (`st.builds`, `st.composite`, `hypothesis.extra.numpy`) instead of filtering with `assume`/`.filter`, which wastes the rejection budget;
   - generate values across the real magnitude range, not only small numbers;
   - include near-degenerate cases (collinear points, tiny or huge extents, near-singular transforms) and `NaN` or infinity where the input can contain them;
   - assert with tolerances derived from the data's precision, or against a higher-precision reference (float64 for float32 code).
2. **Example tests** when a property would only restate the code, or for one known regression input. Keep each regression input as a named example next to the property that generalizes it (`@example`).
3. **`unittest` fixtures:** `setUp` runs once per test method while `@given` runs many examples inside it. Do not share directories, files, or channels across examples.
4. **CrossHair `diffbehavior`** for old-versus-new equivalence on a small pure function with typed arguments (`crosshair diffbehavior old.mod.func new.mod.func`). Use it only where it terminates in reasonable time; a timeout is not evidence either way.

For category 14 (test-only wakes), pick untested code from hotspots and shared packages first. A test-only commit counts toward the six-commit publish only if it would have caught a real defect. Every new or changed test also goes through the Mutation check.

## Test baseline

At launch and with each daily report, run the tiers once and record failing tests in `baselineFailures`. Re-run failures once; a test that passes on the re-run goes in `flaky`. "Green" means no failure outside `baselineFailures` and `flaky`. Do not fix baseline failures unless one is the wake's chosen candidate.

- **Tier A, every package, every baseline:** the A-class test list in `.github/workflows/unit-tests.yml` ("Run A-class unit tests"), run from the umbrella root with an empty `TESTINPUTPATH`. Read the list from the workflow at run time so it never goes stale. Also run each package's own `tests/` for packages that workflow does not cover (`nornir-pyre`, `nornir-builddashboard`, `nornir-volumemodel`, `nornir-web`) when they can import in this environment; an import failure from a missing optional dependency is recorded as `skipped: <reason>`, not as a failure.
- **Tier B, only for the package a wake touches:** the B-class list from the same workflow, and tests that need `TESTINPUTPATH` fixtures, run when the change touches pipeline, image, or transform paths. If the fixtures are absent, record `tierB: not run (no fixtures)` in the commit's ledger entry and treat the change as unverified on those paths: low-risk categories may proceed only if the change cannot reach them, otherwise write a proposal.
- **Long suites:** the full buildmanager pipeline suite with real volumes is hours-scale. Never run it inside a wake; run the focused tests that cover the changed code and leave the full run to the user.

Known pre-existing failures are expected to appear in `baselineFailures` (for example `nornir-imageregistration/tests/transforms` carries known failures, and `TestBasicTileAlignment` is flaky). A byte-identical error value against one recorded earlier is a known failure, not a new one.

## Mutation check

When a wake adds or changes tests, check that the tests would notice wrong code.

- **`mutationMode: native` (loop running in the container) or `container` (loop on Windows):** run mutmut 3 where `os.fork` exists. `native` runs `$PY -m mutmut` directly. `container` runs the same command in the `cursor-dev` container against the bind-mounted checkout (see [nornir-docker-devcontainer](../nornir-docker-devcontainer/SKILL.md)); mutmut does not run on native Windows. Either way scope it to the changed production file and its covering tests with a temporary `[tool.mutmut]` config (`paths_to_mutate`, `tests_dir`, `process_isolation = "forkserver"` when the tests import CuPy, OpenGL, or Qt). The config and mutmut's `mutants/` output are never committed or left in the repo; delete them after the run. Run it only on a tree with no other uncommitted changes in that package.
- **Triage every surviving mutant on a changed line:** real test gap (write a stronger test), equivalent mutant (list it in the commit message with one line of reasoning, or mark `# pragma: no mutate` only with a comment saying why), dead code (delete it if it passes the other gates), or untestable I/O (note it).
- **Fallback, `mutationMode: manual`:** break each changed line by hand (flip a comparison, change a constant, drop a branch), confirm a test fails, restore, and record `mutation: manual`. This is the same stash-and-rerun check the bug-fix procedure uses.
- If a run passes about 15 minutes, stop it and record `mutation: not run (time)`.

## Benchmarking performance changes

Every performance change needs before and after numbers. Without them, do not commit it. State the configuration (sizes, dtype, backend, repeats, median or mean) and the cost of any work the change adds; never call added work free. Measure the layer you change in isolation, because a larger overlapping cost can hide a smaller one and make a correct fix look ineffective. Establish the noise floor first by varying only the seed or repeat on unchanged code; stochastic code can show differences inside its own spread.

1. **Micro-benchmarks use pyperf.** Put each accepted benchmark in `nornir-<pkg>/benchmarks/bench_<name>.py` (create the folder on first need; it is not a package and not installed). Run the old code and the new code to separate JSON files (`python bench_x.py -o old.json`, then new), then `python -m pyperf compare_to old.json new.json --table`. Setup runs outside the timed function, and no hand-written timing loops. Write the JSON to `TESTOUTPUTPATH`, not the repo.
2. Use realistic inputs: fixtures from `TESTINPUTPATH`, captured tiles, and sizes seen in real volumes (full-section tile sets, real mesh sizes). Do not use tiny synthetic inputs that make a change look better than it is in practice.
3. **Accept** only if pyperf reports the change significantly faster and the time improves by at least 5%, or peak memory (measured with `tracemalloc` for host allocations, or the CuPy memory pool's `used_bytes`/`total_bytes` for device allocations) drops by at least 20%, with no regression on the other metric. Re-run a 5-10% result with more processes (`--processes 20`); if it stays marginal, do not commit.
4. **Pipeline-level changes** (anything on the phase-correlation, refine-grid, assemble, or Pyre registration paths): use PhaseProfiler per [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md), the serial/batched verification matrix and the 100-tile sign-off per [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md), and for Pyre registration the interactivity check in [pyre-registration-performance](../pyre-registration-performance/SKILL.md). If the sign-off rig does not apply to the change (for example slice-to-slice code consumes no tiles), say so instead of claiming a sign-off that was not run.
5. Record the `environment` (and the GPU, if CuPy was used) with every benchmark. Numbers from the Windows host and from the container are not comparable; the before and after runs of one change must come from the same environment and the same session. Note in the ledger whether a build, test run, or other agent was loading the machine during the run. A result taken under load gets one re-run before acceptance.
6. **Rejected performance candidates** are appended to `.cursor/issue-handoff/optimization-loop-rejections.md` in its existing format (date, package, candidate, benchmark, baseline, candidate result, quality check, and a "do not retry unless" line). Read it before choosing a performance candidate and skip anything listed.
7. If a realistic benchmark needs a live service, a GPU frame loop, UI interaction, or more setup than fits one wake, do not edit. Write a proposal (see [categories.md](categories.md)) with the suspected cost, the evidence, and the benchmark that would prove it.

## Before commit and commit

Read the full diff once as a reviewer: callers still import and behave the same, no correct comment lost, nothing outside scope or in Protected areas changed. Run `ruff check` and `pyright` on the touched files and compare against their count before the change; a change must not add new findings (do not fix unrelated ones). Run the covering tests, the mutation check, and for performance changes, the benchmark.

Commit only when green, following [Monorepo-submodule-changes](../../rules/Monorepo-submodule-changes.mdc):

1. **Inside the owning submodule**, stage only the files this wake changed, by path; never `git add -A` or `git add .`. If a file the candidate needs already has uncommitted edits the loop did not make, choose a different candidate so those edits never land in a loop commit. A new characterization test may be its own commit just before the change it protects; the pair counts as one change.
2. The commit message states what improved, the category (or port stage), and the line delta (and the benchmark summary for performance changes, and the regression-test failure count for bug fixes), and ends with the trailer `Improvement-Loop: <category number>` so later wakes can find loop commits (for port stages use `Improvement-Loop: 15`).
3. **Bump the umbrella pointer in a second commit**, staging only that submodule path: `git add nornir-<pkg>` then `git commit -m "Update nornir-<pkg>: <why>"`. Do not include other staged work or unrelated pointer changes in it. Changes to the umbrella's own files (rules, skills, docs, scripts) are committed directly in the umbrella with the same trailer.
4. Run `git submodule status`. A `+` prefix on the package just committed means the bump is missing. A `+` on a package the loop did not touch belongs to the user; leave it alone and mention it in the report.
5. On failure, revert and log it; the wake does not count toward publish. A revert of a loop commit that already has a pointer bump reverts both.

Never push. Because the user will push later, the order matters: [CI-hygiene](../../rules/CI-hygiene.mdc) requires submodule commits to be pushed to their remotes before the umbrella pointer bump, otherwise CI fails with `upload-pack: not our ref`. The publish message says so.

## Publish

Count only commits this loop creates (submodule commits and umbrella-owned commits; a pointer bump belongs to its submodule commit and is not counted again). There is one total count, `countsSincePublish`.

On the 6th commit, in this order, then set the count to 0:

1. Post the list of commits to the user: package, short sha, category, summary, and the pointer-bump sha, grouped by package, with the reminder to push each submodule before the umbrella.
2. If any of those commits touched `nornir-pyre` or a package the Pyre installer bundles (`nornir-imageregistration`, `nornir-shared`, `nornir-pools`): when `environment` is not `windows`, append `{date, commits, result: "skipped: not Windows"}` to `pyreBuilds` and tell the user a build is owed on the host; otherwise build the Windows installer locally, following [nornir-bump-version](../nornir-bump-version/SKILL.md): from `nornir-pyre/packaging/windows`, run `.\build-freeze.ps1`, `.\validate-frozen.ps1`, then `.\build-installer.ps1`. Record `{date, commits, result, installerPath}` in `pyreBuilds`. If a step fails, record the failure and tell the user; do not retry more than once, and do not treat a failed build as a reason to revert unless a commit caused it.
3. Do **not** bump any version, edit `release/package-versions.yaml` or `VERSION`, add a tag, run `release/publish_pyre_windows_release.ps1`, or push. Those are the user's call. Build artifacts stay out of git; check `git status` afterwards.
4. Publish finishes before the next sleep is armed.
