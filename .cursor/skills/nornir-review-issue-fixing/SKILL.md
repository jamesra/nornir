---
name: nornir-review-issue-fixing
description: >-
  End-to-end procedure for fixing a Nornir code-review finding: treat the issue text as an
  unproven hypothesis, reproduce or measure before editing, write a test that fails against the
  old code, commit in the submodule then bump the umbrella pointer, close the issue with
  evidence, and update the master list. Use when working `.cursor/nornir-bug-review-master.md`,
  a `jamesra/nornir-review` issue, a static-analysis finding, or any queue of "fix one issue at
  a time" work in this monorepo.
---

# Fixing a Nornir review finding

Paired rule: [`.cursor/rules/Review-driven-bugfixing.mdc`](../../rules/Review-driven-bugfixing.mdc).

Findings in [`.cursor/nornir-bug-review-master.md`](../../nornir-bug-review-master.md) and in the
`jamesra/nornir-review` issue tracker were produced by **reading code, not running it**. A large
fraction are correct, several are half right in ways that matter, and a few are wrong. The
procedure below exists because the expensive mistakes all came from trusting the finding's
explanation instead of its symptom.

## Loop

1. **Pick** the highest-severity open item (P0 → P3). Cross-check the master list `Status` against
   the tracker; they drift.
2. **Reproduce or measure first**, before any edit. See *Verify before fixing*.
3. **Fix** the cause you measured — not the one the finding named, if they differ.
4. **Test** so that the new test fails against the old code (verify by stashing).
5. **Verify** the surrounding suites, distinguishing pre-existing failures from yours.
6. **Commit** in the submodule, then bump the umbrella pointer.
7. **Close** the issue with a comment carrying the numbers, and set the master-list `Status`.
8. **Record** any durable lesson in the matching skill *in the same commit*.
9. **File** anything found on the way as a separate issue; do not fold it in.

## Verify before fixing

- **Execute the failing path.** A finding is a hypothesis until reproduced. If it cannot be
  reproduced on this machine, say so plainly and treat it as unproven rather than fixing blind —
  a locale-dependent read (`open(f, 'r')` labelled `utf-8`) is invisible on a UTF-8 host.
- **Follow the observation that contradicts the theory.** A theory that explains most of the
  evidence and cannot explain one piece is usually the wrong theory, not a right theory with an
  outlier. `'t' != 'K'` — two single characters no codec maps to each other — broke open #245,
  which had been filed, plausibly, as mojibake. It was Hypothesis examples leaking through a
  shared `setUp`.
- **Measure the layer you are about to change, in isolation.** When two allocations overlap, the
  larger transient hides the smaller, so fixing the hidden one first measures as *no improvement
  at all*. In #157 the zero-copy caller rewrite that the issue asked for saved nothing until
  `array.fromfile`'s own 2.06x reallocation was fixed underneath it; both layers had to change.
- **Establish the noise floor before attributing a difference to your change.** Hold the
  configuration fixed and vary only the seed. `ScoreOneAngle` is stochastic (#95): the coarse-grid
  peak deltas in #234 sat inside the seed spread of the *unchanged* code, so calling them
  decimation error would have been wrong.
- **Test the boundary, not just the reported condition.** #236 was filed as a `budget_bytes <= 0`
  branch; writing the fix as a floor instead exposed a second silent collapse at 1281 MiB free,
  *above* the reported cliff, where the ordinary path floor-divided to zero just as quietly.

## Tests

- The test must **fail against the previous behaviour**. Verify it — stash the fix and run.
  Quote the count ("9 of the 12 fail against the previous behaviour"), because a test that passes
  both ways is documentation, not a regression guard.
- **A test for a timing bug is worth checking for the same timing bug.** Setting mtimes from a
  `getmtime` float does not round-trip through `os.utime`; that test passed intermittently against
  unfixed code. Use nanoseconds.
- `unittest.setUp` runs **once per test method** while `@given` runs many examples inside it, so
  every Hypothesis example shares that fixture. Shared directories, channels, and files across
  examples produce failures that read as corruption. See also the
  [hypothesis-testing](../hypothesis-testing/SKILL.md) skill.
- Prefer asserting the **property** over a value: #236's central test sweeps free VRAM and asserts
  no adjacent level may drop the chunk by more than 4x. Value assertions go stale (two in
  `test_refine_shared.py` had been failing since #228 unnoticed).
- Assert **in both directions** when the premise could evaporate — that the old pattern really did
  cost an extra copy — so the test fails loudly rather than quietly asserting something free.
- Make fakes faithful to the real return type; a `_TagData` exposing only `tobytes()` cannot
  represent data read through the buffer protocol.

## Distinguishing your failures from the repo's

- **Stash and re-run** before blaming a diff. `tests/transforms` carries 18 pre-existing failures;
  `TestBasicTileAlignment` rotates one or two per combined run with and without local changes.
- Compare **failure sets across repeats**, not a single combined run.
- A byte-identical error value against one recorded earlier (e.g. `1085.9270565544502` for #235)
  is a known failure, not a new one.
- See [nornir-headless-unit-tests](../nornir-headless-unit-tests/SKILL.md) for `NORNIR_HEADLESS`
  and for the import-time `matplotlib.use` trap that wedges whole sessions.

## Performance claims

- Give **before/after numbers** with the configuration (size, dtype, repeats, median vs mean).
- **State the cost of work you added**, even when small: ~40µs per call against ~350µs, ~40ms per
  thousand-section volume. Do not call it free.
- Keep an existing cheap guard when it protects an expensive path. #245 kept the mtime check for
  image pyramids and added content comparison only for small notes files; replacing it globally
  would have been the tidier-looking change and the wrong one.
- Prefer **opt-in** for a speedup whose accuracy is established on one pair, and say what a
  default-on decision still needs.
- If the rig a sign-off rule requires does not apply — `stos_brute` is slice-to-slice and consumes
  no tiles, so the ≥100-tile rule cannot apply — **flag that** instead of claiming a sign-off you
  did not run.

## Scope

- File side findings **separately**, especially when the fix needs a decision rather than being
  mechanical (which encoding fallback, whether the ROI path's analogous collapse transfers).
- Do not ride a behaviour change along inside an unrelated fix.
- Prefer **warn over raise** when a run in the degraded state still produces correct results and
  the defect is that it was silent; throttle the warning if the call is hot.

## Landing the change

Commit **inside the submodule first**, then bump the umbrella pointer — see
[`.cursor/rules/Monorepo-submodule-changes.mdc`](../../rules/Monorepo-submodule-changes.mdc).

Umbrella commit message convention, as used throughout this queue:

```text
Update nornir-buildmanager: recopy notes on content change, not mtime alone (#245)
```

Then:

- Close the tracker issue with a comment containing the measurements, the test names and counts,
  and **an explicit correction when the finding's diagnosis was wrong** — that is the part a future
  reader of the master list needs most.
- Set `Status` (and the `Issue` link) in `.cursor/nornir-bug-review-master.md`.
- Working notes belong under `.cursor/issue-handoff/`, not the repository root.
