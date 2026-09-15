# Adversarial Verification and Repair

## PR8 objective

PR8 supplies the reliability components consumed by the solve orchestrator in
PR9. It turns independently designed examples into observed, reproducible
evidence and converts the smallest useful failures into bounded repair work.
It does not make prose emitted by a model executable and does not treat model
confidence as evidence.

## Delivery map

| Concern | Contract | Acceptance signal |
| --- | --- | --- |
| Boundary checks | JSON-only calls with expected results | Per-case sandbox evidence |
| Small oracle checks | Independently authored, statically checked reference function | Candidate and oracle agree in the sandbox |
| Properties | Candidate result compared with a JSON value by an allowlisted relation | Reproducible pass or counterexample |
| Metamorphic checks | Two calls compared by an allowlisted relation | Reproducible relational evidence |
| Failure minimization | Deterministic, evaluation-bounded JSON shrinking | Smaller input that preserves the observed failure |
| Ranking | Pure lexicographic score from check outcomes and runtime | Stable order independent of model claims |
| Repair | Parent source plus minimized counterexamples | Registered child with preserved lineage |

## Test specification

`VerificationSuite` is a bounded collection of uniquely identified cases.
Inputs, expected values, and transformations are JSON values; comparison is
restricted to equality, inequality, ordering, truthiness, or falsiness. No
arbitrary assertion expression is accepted. Metamorphic cases contain a base
and follow-up call. Oracle cases require a separate reference entrypoint.

The oracle is checked by the same AST, import, top-level-effect, and compilation
policy as candidates. Candidate and oracle then execute together in the PR7
container boundary: no network, read-only root and source mount, non-root user,
dropped capabilities, and fixed CPU, memory, process, and wall-time limits.

## Evidence and ranking

Each independent case produces its own `CheckResult`, including its kind, case
identifier, status, duration share, and failing input. Structural and executed
behavioral failures remain mandatory. An invalid oracle is inconclusive and
cannot count against a candidate.

Viability is the first ranking gate. Viable candidates are ordered by public
examples, small oracles, properties, metamorphic relations, boundary cases,
complexity fit, and lower observed runtime. Candidate ID is the stable final
tie-breaker. Missing evidence scores zero; unexecuted claims never enter the
score.

## Counterexamples and repair

The minimizer greedily shrinks integers, floats, strings, arrays, and objects.
Every proposed reduction is accepted only when a caller-supplied verifier
observes the same failure, and the evaluation count is capped. The repair
coordinator refuses work after either the configured repair count or the 90%
repair cutoff. A repair is a new immutable candidate whose parent, strategy,
and revision are validated by `CandidateRepository`.

Parent evidence is retained as provenance, while the repaired source starts
with no inherited passes and must rerun every mandatory check. This preserves
the audit trail without allowing stale success to validate changed code.

## PR8 acceptance gates

- Unit coverage for malformed suites, minimization, scoring, stable ranking,
  lineage, prompt repair, repair limits, and deadline cutoff behavior.
- Mocked sandbox coverage for per-case results and counterexamples.
- Real Docker coverage for boundary, oracle, property, and metamorphic cases.
- Ruff formatting and lint, strict mypy, at least 90% package coverage, wheel
  and source builds, dependency audit, and all repository-policy checks.
