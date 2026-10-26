---
name: hypothesis-testing
description: >-
  Guides pytest unit tests toward Hypothesis property-based testing when inputs
  are variable, structured, combinatorial, or numerical; pairs property tests
  with explicit examples for regressions and known edges. Use when writing or
  reviewing tests, serialization or round-trips, ndarray or numerical code, or
  when deciding between @given and parametrization. 
---

# Hypothesis testing

## When to use Hypothesis

- Use `@given` and strategies when inputs are high-dimensional, combinatorial, structured (nested dicts, trees, records) or hard to enumerate without missing cases.
- Use it for data structures when invariants, round-trips (encode/decode, serialize/parse) or validity constraints matter more than a fixed list of instances.
- Prefer plain `pytest.mark.parametrize` (or a tiny hand-written table) for few discrete cases, where properties would add noise or slow CI without meaningful coverage.

## Mathematical and numerical code

- Prefer Hypothesis when behavior depends on ranges of reals, several coupled parameters, array shape or dtype, or known algebraic/analytic identities you can assert as properties.
- Use tolerance-based assertions where appropriate; restrict strategies to the function's domain (e.g. positive arguments where required) and set `allow_nan` / `allow_infinity` to match defined behavior.
- Use `hypothesis.extra.numpy` array strategies for vectorized/ndarray code; constrain shape, dtype and value ranges so tests stay fast and failures are interpretable.

## Pairing with explicit examples

- Keep a small set of `@example(...)` and/or `@pytest.mark.parametrize` cases for documented regressions, known edge cases (including canonical scalars: 0, 1, -1, small integers, π where relevant) and API contracts you want visible in the test body.
- Do not duplicate a scenario in both Hypothesis and parametrization unless one documents intent and the other explores the space.

## Engineering hygiene

- Tune `settings` (`max_examples`, `deadline`); use `suppress_health_check` only with a short comment saying why (e.g. unavoidable heavy setup).
- Rely on shrinking for minimal failures. For reproducibility of flaky failures: `@reproduce_failure`, the Hypothesis example database / CI artifacts.

## Anti-patterns

- Over-broad strategies that make tests slow or flaky without tightening invariants.
- Property tests with no clear property or oracle (only random smoke).
