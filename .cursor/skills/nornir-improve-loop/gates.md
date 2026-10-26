# Gates: what a change must pass

Read by the implementer and the reviewer. Protected areas: [protected.md](protected.md). Port wakes also apply the port gates in [metadata-port.md](metadata-port.md).

Run all commands with `$PY` (SKILL.md Environment) and `NORNIR_HEADLESS=1` ([nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md)). Test artifacts go under `TESTOUTPUTPATH`, logs follow the [Unified-Logging-Convention](../../rules/Unified-Logging-Convention.mdc), scratch notes go under `.cursor/issue-handoff/`; never in the repository root.

## Accept a change only if all hold

- **Not protected.** Nothing in Protected areas is edited.
- **Real callers.** Every generalization serves two or more existing call sites; no code for hypothetical callers.
- **Net simpler.** Refactoring shortens production code, or moves a rule from several places into one. A lower complexity grade alone does not count; category 9 splits whose new helpers have a single caller are rejected (user decision 2026-10-20). Performance changes may add a little code if the measured gain is real and the code stays readable.
- **No new flags.** Do not merge functions behind a `bool` or mode parameter that picks between old bodies.
- **Structural, not cosmetic.** Renames, formatting, import sorting, quote style, and annotation-only edits are not a wake's change on their own; they may ride along with a structural change in the same lines. **Exception:** an edit required for compliance with documentation skills and rules ([nornir-documentation](../nornir-documentation/SKILL.md), [Documentation-and-monodoc](../../rules/Documentation-and-monodoc.mdc), related package README/docstring conventions) is a valid wake's change if it meets the other gates.
- **Semantics traps checked** for each caller, as applicable:
  - a generator replacing a list is lazy and single-use;
  - a dataclass gains `__eq__` and, if frozen, `__hash__` (check dict keys, sets, `==`, identity checks);
  - a mutable default or shared module-level object now shared;
  - numpy view versus copy, dtype promotion, C versus F order;
  - a NumPy/CuPy change that silently pulls arrays to the host or promotes dtype;
  - `functools.cache` on a method keeps `self` alive;
  - import-time side effects, circular imports, pickling across `nornir_pools` process pools.
- **Same behavior.** A test pins the old behavior before the edit and passes after it. Only bug fixes are exempt (see Bug fixes).
- **Output parity on stable paths.** For importers, image I/O, coordinates, and transforms, follow [Stable-path-output-parity](../../rules/Stable-path-output-parity.mdc): compare outputs before and after on real data, not just unit tests. No real data on this machine: write a proposal instead of editing.
- **Nornir rules respected.** Apply the glob-scoped rules matching the touched files (indexed in [AGENTS.md](../../../AGENTS.md)): [python-standards](../../rules/python-standards.mdc), [Numpy-CuPy-compatibility](../../rules/Numpy-CuPy-compatibility.mdc), [Pyre-host-array-boundary](../../rules/Pyre-host-array-boundary.mdc), [Streaming-and-memory-bounded-processing](../../rules/Streaming-and-memory-bounded-processing.mdc), [Serial-batched-primitives](../../rules/Serial-batched-primitives.mdc), [Refine-grid-trust-questions](../../rules/Refine-grid-trust-questions.mdc), [Pyre-STOS-rigid-transform-UI](../../rules/Pyre-STOS-rigid-transform-UI.mdc). A change that would violate a rule's `must not` or `do not` is a decision, not a commit.
- **Reviewable size.** About 300 changed lines at most. Larger work goes to `deferred` with a one-line plan; do a smaller slice now if one exists.
- **Works wherever it is used.** A change to a shared package (`nornir-shared`, `nornir-pools`, `nornir-imageregistration`) runs the covering tests of every package importing the changed names (grep first). CuPy-guarded paths must still import without CuPy.
- **Comments.** Keep comments stating a contract, threading rule, or edge case. Edited functions keep or gain PEP 257 docstrings per [python-standards](../../rules/python-standards.mdc). Never delete a correct comment; if unsure one is still correct, prefix it with `?? AI Changed Code after comment ??`.

If no candidate passes, revert and add `{ path, category, reason }` to `rejected`. Skip rejected paths later unless the code around them changed.

## Bug fixes

The loop may fix, without asking, bugs that ordinary use, real volume data, or real pipeline runs can reach (Python checklist in [categories.md](categories.md)). Bugs needing contrived input, or only in dead or test-only code, are not worth a wake; log them in `rejected`.

Procedure ([nornir-review-issue-fixing](../nornir-review-issue-fixing/SKILL.md) in short):

1. Treat the suspicion as an unproven hypothesis. Reproduce it first with a test that fails on current code, preferably a Hypothesis property test generating the triggering inputs. Not reproducible on this machine: write a proposal, leave it unfixed.
2. **The regression test must fail against the old behavior.** Verify by running it in a detached `HEAD` worktree (never `git stash`; the checkout is shared); record the count ("3 of 3 fail against the old code") in the commit message. Commit the test only after it passes with the fix.
3. Before attributing any suite failure to the change, re-run it on a `HEAD` worktree baseline and compare failure sets across repeats; several suites carry known failures and flaky tests.
4. Make the smallest fix that turns the test green; fix only the defect. If it would change user-visible behavior beyond removing the defect (UI flow, defaults, what gets saved), add it to `decisions` instead.
5. Prefer warn over raise when the degraded state still gives correct results and the defect is only silence; throttle the warning on hot calls.
6. For a bug a Pyre user could notice, add one line to `nornir-pyre/CHANGELOG.user.md` under its unreleased section in the same commit.
7. Bug in a protected area, or not reproducible outside a GUI, a GPU, or a live service: write a proposal with the evidence and likely fix.

## Math and precision

Registration, transforms, mosaics, and measurements feed research results, so a math or precision error real data can reach is a bug likely in real use. Check types against the data they hold: tile and mosaic coordinates reach hundreds of thousands of pixels, section numbers run into the thousands, and values are later converted to physical units.

Math errors to look for:

- numpy integer overflow or truncation (products of image dimensions in `uint16`/`int32`, unsigned subtraction wrap-around), and `//`, `%`, `int()` on negative coordinates where `floor` is meant;
- `round()` (banker's rounding) where away-from-zero is meant, and `np.round` versus `round` differences;
- degrees versus radians, swapped x/y or row/column order (see `nornir-imageregistration/docs/flip_flop_mosaic_coordinates.md`);
- wrong coordinate space (tile, mosaic, section, volume, screen) or a missing unit conversion (pixels to nm);
- catastrophic cancellation from subtracting nearly equal large numbers in orientation, area, or distance tests; subtract a nearby origin first;
- normalizing a zero-length vector, inverting a singular or near-singular transform, `NaN` or infinity spreading silently;
- long sums that drift (use `math.fsum`, pairwise `np.sum`, or float64 accumulation), squared distances that overflow float32;
- **precision round trips:** a value narrowed (float64 to float32, int64 to int32) for one function, then widened again by the caller or next step, losing precision for nothing and paying time plus an array copy per conversion. Match the pathway's precision instead. Narrow once, at the true boundary where lower precision is consumed (GPU upload, file write, OpenGL texture), clamping there when the value can exceed the target's range. Implicit promotion by mixed-dtype arithmetic and Python scalars counts. The serial/batched skill documents measured examples; do not reintroduce an unconditional float64 upcast.

Precision of types:

- **Under-precise:** float32 for mosaic-space coordinates, accumulated transforms, or long sums, where about 7 significant digits lose sub-pixel accuracy at real magnitudes. Use float64 for geometry and measurement; image data and GPU-bound arrays may stay float32.
- **Overly precise:** float64 for inherently coarse data (pixel intensities, tile indices). Narrow only with a measurement and a test showing results stay within the data's real resolution, and only if pathway neighbors would not cast back up.
- **Cost of changing precision:** count conversions added or removed along the whole pathway, not just the edited function; prefer fewer. When precision and speed conflict, keep precision unless real-data measurements show the gain matters and a test shows the loss stays within the data's resolution.
- **Comparisons:** a fixed absolute epsilon is wrong across magnitudes. Use `np.isclose`/`math.isclose` with a relative tolerance sized to the data; name the constant, with a comment on where the value comes from.

## Test coverage

Every change is covered by a test that would fail if the change were wrong. Follow [hypothesis-testing](../hypothesis-testing/SKILL.md).

1. **Hypothesis property tests** by default. Good properties: round trips (serialize/parse, transform/inverse), invariants (bounds contain every point, area never negative), old-versus-new equivalence on generated inputs for refactors, agreement with a slow obviously correct reference, and for numeric code, equality across chunk sizes and across NumPy/CuPy backends where CuPy is available. For numerical code:
   - build valid inputs directly (`st.builds`, `st.composite`, `hypothesis.extra.numpy`) instead of filtering with `assume`/`.filter`, which wastes the rejection budget;
   - generate values across the real magnitude range, not only small numbers;
   - include near-degenerate cases (collinear points, tiny or huge extents, near-singular transforms) and `NaN` or infinity where inputs can contain them;
   - assert with tolerances derived from the data's precision, or against a higher-precision reference (float64 for float32 code).
2. **Example tests** when a property would only restate the code, or for one known regression input; keep each regression input as a named `@example` next to the property that generalizes it.
3. **`unittest` fixtures:** `setUp` runs once per test method while `@given` runs many examples inside it; do not share directories, files, or channels across examples.
4. **CrossHair `diffbehavior`** for old-versus-new equivalence of a small pure function with typed arguments (`crosshair diffbehavior old.mod.func new.mod.func`), only where it terminates in reasonable time; a timeout is not evidence either way.

Category 14 (test-only wakes): pick untested code from hotspots and shared packages first. A test-only commit counts toward the six-commit publish only if it would have caught a real defect. Every new or changed test also goes through the Mutation check.

## Test baseline

At launch and with each daily report, run the tiers once and record failing tests in `baselineFailures`. Re-run failures once; a test passing on the re-run goes in `flaky`. "Green" = no failure outside `baselineFailures` and `flaky`. Do not fix baseline failures unless one is the wake's chosen candidate.

- **Tier A, every package, every baseline:** the A-class test list in `.github/workflows/unit-tests.yml` ("Run A-class unit tests"), from the umbrella root with an empty `TESTINPUTPATH`; read the list from the workflow at run time so it never goes stale. Also run the own `tests/` of packages that workflow skips (`nornir-pyre`, `nornir-builddashboard`, `nornir-volumemodel`, `nornir-web`) when they import here; an import failure from a missing optional dependency is `skipped: <reason>`, not a failure.
- **Tier B, only for the package a wake touches:** the workflow's B-class list plus tests needing `TESTINPUTPATH` fixtures, when the change touches pipeline, image, or transform paths. Fixtures absent: record `tierB: not run (no fixtures)` in the commit's ledger entry and treat the change as unverified on those paths; low-risk categories proceed only if the change cannot reach them, otherwise write a proposal.
- **Long suites:** the full buildmanager pipeline suite with real volumes takes hours. Never run it in a wake; run the focused tests covering the changed code and leave the full run to the user.

Known pre-existing failures belong in `baselineFailures` (current list: the known-failures table in `.cursor/skills/nornir-verify-change/SKILL.md`; `TestBasicTileAlignment` is flaky). An error value byte-identical to one recorded earlier is a known failure, not a new one.

## Mutation check

When a wake adds or changes tests, check that they would notice wrong code.

- **`mutationMode: native` (loop in the container) or `container` (loop on Windows):** run mutmut 3 where `os.fork` exists: `native` runs `$PY -m mutmut` directly; `container` runs it in the `cursor-dev` container against the bind-mounted checkout ([nornir-docker-devcontainer](../nornir-docker-devcontainer/SKILL.md)), since mutmut does not run on native Windows. Scope it to the changed production file and its covering tests with a temporary `[tool.mutmut]` config (`paths_to_mutate`, `tests_dir`, `process_isolation = "forkserver"` when tests import CuPy, OpenGL, or Qt). Never commit or leave the config or mutmut's `mutants/` output in the repo; delete them after the run. Run only on a tree with no other uncommitted changes in that package.
- **Triage every surviving mutant on a changed line:** real test gap (write a stronger test); equivalent mutant (list it in the commit message with one line of reasoning, or `# pragma: no mutate` only with a comment saying why); dead code (delete it if that passes the other gates); untestable I/O (note it).
- **Fallback, `mutationMode: manual`:** break each changed line by hand (flip a comparison, change a constant, drop a branch), confirm a test fails, restore, record `mutation: manual`. Same fail-on-old-code check as the bug-fix procedure.
- If a run passes about 15 minutes, stop it and record `mutation: not run (time)`.

## Benchmarking performance changes

No before and after numbers, no commit. State the configuration (sizes, dtype, backend, repeats, median or mean) and the cost of any added work; never call added work free. Measure the changed layer in isolation: a larger overlapping cost can hide a smaller one and make a correct fix look ineffective. First establish the noise floor by varying only the seed or repeat on unchanged code; stochastic code can differ inside its own spread.

1. **Micro-benchmarks use pyperf.** Put each accepted benchmark in `nornir-<pkg>/benchmarks/bench_<name>.py` (create the folder on first need; not a package, not installed). Run old and new code to separate JSON files (`python bench_x.py -o old.json`, then new), then `python -m pyperf compare_to old.json new.json --table`. Setup runs outside the timed function; no hand-written timing loops. Write the JSON to `TESTOUTPUTPATH`, not the repo.
2. Use realistic inputs: `TESTINPUTPATH` fixtures, captured tiles, sizes seen in real volumes (full-section tile sets, real mesh sizes); not tiny synthetic inputs that flatter the change.
3. **Accept** only if pyperf reports the change significantly faster and time improves at least 5%, or peak memory (`tracemalloc` for host allocations, the CuPy memory pool's `used_bytes`/`total_bytes` for device) drops at least 20%, with no regression on the other metric. Re-run a 5-10% result with `--processes 20`; if still marginal, do not commit.
4. **Pipeline-level changes** (phase-correlation, refine-grid, assemble, or Pyre registration paths): PhaseProfiler per [nornir-debug-profiling](../nornir-debug-profiling/SKILL.md); the serial/batched verification matrix and 100-tile sign-off per [nornir-serial-batched-primitives](../nornir-serial-batched-primitives/SKILL.md); for Pyre registration, the interactivity check in [pyre-registration-performance](../pyre-registration-performance/SKILL.md). If the sign-off rig does not apply (e.g. slice-to-slice code consumes no tiles), say so; never claim a sign-off that was not run.
5. Record the `environment` (and GPU, if CuPy was used) with every benchmark. Host and container numbers are not comparable; one change's before and after runs must come from the same environment and session. Note in the ledger whether a build, test run, or other agent was loading the machine; a result taken under load gets one re-run before acceptance.
6. **Rejected performance candidates** are appended to `.cursor/issue-handoff/optimization-loop-rejections.md` in its existing format (date, package, candidate, benchmark, baseline, candidate result, quality check, and a "do not retry unless" line). Read it before choosing a performance candidate; skip anything listed.
7. If a realistic benchmark needs a live service, a GPU frame loop, UI interaction, or more setup than fits one wake, do not edit; write a proposal (see [categories.md](categories.md)) with the suspected cost, the evidence, and the benchmark that would prove it.

## Before commit and commit

Read the full diff once as a reviewer: callers still import and behave the same, no correct comment lost, nothing outside scope or in Protected areas changed. Run `ruff check` and `pyright` on the touched files and compare with their counts before the change; add no new findings (do not fix unrelated ones). Run the covering tests, the mutation check, and for performance changes the benchmark.

Commit only when green, per [Monorepo-submodule-changes](../../rules/Monorepo-submodule-changes.mdc):

1. **Inside the owning submodule**, stage only this wake's files, by path; never `git add -A` or `git add .`. If a file the candidate needs already has uncommitted edits the loop did not make, choose a different candidate so they never land in a loop commit. A new characterization test may be its own commit just before the change it protects; the pair counts as one change.
2. The message states what improved, the category (or port stage), the line delta (plus the benchmark summary for performance changes, the regression-test failure count for bug fixes), and ends with the trailer `Improvement-Loop: <category number>` so later wakes can find loop commits (port stages: `Improvement-Loop: 15`).
3. **Bump the umbrella pointer in a second commit**, staging only that submodule path: `git add nornir-<pkg>` then `git commit -m "Update nornir-<pkg>: <why>"`, with no other staged work or unrelated pointer changes. Changes to the umbrella's own files (rules, skills, docs, scripts) are committed directly in the umbrella with the same trailer.
4. Run `git submodule status`. A `+` on the package just committed means the bump is missing. A `+` on a package the loop did not touch is the user's; leave it and mention it in the report.
5. On failure, revert and log it; the wake does not count toward publish. Reverting a loop commit that has a pointer bump reverts both.

Never push. The user pushes later, and [CI-hygiene](../../rules/CI-hygiene.mdc) requires submodule commits on their remotes before the umbrella pointer bump, otherwise CI fails with `upload-pack: not our ref`. The publish message says so.

## Publish

Count only commits this loop creates (submodule and umbrella-owned commits; a pointer bump belongs to its submodule commit and is not counted again), in one total, `countsSincePublish`.

On the 6th commit, in order, then set the count to 0:

1. Post the commits to the user, grouped by package: package, short sha, category, summary, pointer-bump sha, with the reminder to push each submodule before the umbrella.
2. If any touched `nornir-pyre` or a package the Pyre installer bundles (`nornir-imageregistration`, `nornir-shared`, `nornir-pools`): when `environment` is not `windows`, append `{date, commits, result: "skipped: not Windows"}` to `pyreBuilds` and tell the user a build is owed on the host. Otherwise build the Windows installer locally per [nornir-bump-version](../nornir-bump-version/SKILL.md): from `nornir-pyre/packaging/windows`, run `.\build-freeze.ps1`, `.\validate-frozen.ps1`, then `.\build-installer.ps1`, and record `{date, commits, result, installerPath}` in `pyreBuilds`. If a step fails, record it and tell the user; retry at most once, and do not revert over a failed build unless a commit caused it.
3. Do **not** bump any version, edit `release/package-versions.yaml` or `VERSION`, add a tag, run `release/publish_pyre_windows_release.ps1`, or push; those are the user's call. Build artifacts stay out of git; check `git status` afterwards.
4. Publish finishes before the next sleep is armed.
