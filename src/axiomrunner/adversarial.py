"""Independent behavioral verification, minimization, and evidence ranking."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from axiomrunner.domain import (
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    Evidence,
    JsonValue,
    VerificationKind,
    VerificationSuite,
    to_json_value,
)
from axiomrunner.sandbox import DockerSandbox
from axiomrunner.static_validation import StaticVerifier

MAX_CASES = 256
SCORED_TYPES = ("sandbox", "oracle", "property", "metamorphic", "boundary")


@dataclass(frozen=True, slots=True)
class Counterexample:
    args: tuple[JsonValue, ...]
    kwargs: dict[str, JsonValue]


@dataclass(frozen=True, slots=True, order=True)
class EvidenceScore:
    viable: bool
    public_rate: float
    oracle_rate: float
    property_rate: float
    metamorphic_rate: float
    boundary_rate: float
    complexity_fit: bool
    negative_runtime_s: float


class AdversarialVerifier:
    """Validate independent test material before executing it with a candidate."""

    def __init__(self, static: StaticVerifier, sandbox: DockerSandbox) -> None:
        self.static = static
        self.sandbox = sandbox

    def verify(
        self,
        candidate: Candidate,
        problem: ChallengeProblem,
        suite: VerificationSuite,
    ) -> tuple[CheckResult, ...]:
        validate_suite(suite)
        if suite.oracle_source and suite.oracle_entrypoint:
            oracle = Candidate("oracle", "independent-oracle", suite.oracle_source)
            oracle_checks = self.static.verify(oracle, suite.oracle_entrypoint)
            failures = tuple(
                check for check in oracle_checks if check.status is not CheckStatus.PASSED
            )
            if failures:
                return (
                    CheckResult(
                        "oracle_policy",
                        "independent",
                        CheckStatus.INCONCLUSIVE,
                        sum(check.duration_s for check in oracle_checks),
                        mandatory=False,
                        details={
                            "failures": [
                                {"check": check.check_type, "details": check.details}
                                for check in failures
                            ]
                        },
                    ),
                )
        return self.sandbox.verify_suite(candidate, problem, suite)


def validate_suite(suite: VerificationSuite) -> None:
    if not suite.cases:
        raise ValueError("verification suite must contain at least one case")
    if len(suite.cases) > MAX_CASES:
        raise ValueError(f"verification suite exceeds {MAX_CASES} cases")
    identifiers = [case.case_id for case in suite.cases]
    if any(not identifier.strip() for identifier in identifiers):
        raise ValueError("case identifiers must be nonempty")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("case identifiers must be unique")
    has_oracle = any(case.kind is VerificationKind.ORACLE for case in suite.cases)
    if has_oracle and not (suite.oracle_source and suite.oracle_entrypoint):
        raise ValueError("oracle cases require oracle source and entrypoint")
    for case in suite.cases:
        if case.kind is VerificationKind.METAMORPHIC and case.followup is None:
            raise ValueError(f"metamorphic case {case.case_id} requires a followup call")
        if case.kind is not VerificationKind.METAMORPHIC and case.followup is not None:
            raise ValueError(f"non-metamorphic case {case.case_id} cannot have a followup call")
        to_json_value(case.call.args)
        to_json_value(case.call.kwargs)
        to_json_value(case.expected)
        if case.followup:
            to_json_value(case.followup.args)
            to_json_value(case.followup.kwargs)


def minimize_counterexample(
    counterexample: Counterexample,
    still_fails: Callable[[Counterexample], bool],
    *,
    max_evaluations: int = 64,
) -> Counterexample:
    """Greedily shrink JSON data while preserving the caller-observed failure."""
    if max_evaluations < 1:
        return counterexample
    current = counterexample
    evaluations = 0
    while evaluations < max_evaluations:
        replacement = _first_reduction(current, still_fails, max_evaluations - evaluations)
        evaluations += replacement[1]
        if replacement[0] == current:
            break
        current = replacement[0]
    return current


def counterexamples_from_evidence(evidence: Evidence) -> tuple[Counterexample, ...]:
    """Extract well-formed observed failures without trusting arbitrary detail fields."""
    found: list[Counterexample] = []
    for check in evidence.checks:
        if check.status is not CheckStatus.FAILED:
            continue
        raw = check.details.get("counterexample")
        if not isinstance(raw, dict):
            continue
        args = raw.get("args")
        kwargs = raw.get("kwargs")
        if not isinstance(args, list) or not isinstance(kwargs, dict):
            continue
        try:
            normalized_args = tuple(to_json_value(item) for item in args)
            normalized_kwargs = to_json_value(kwargs)
        except TypeError:
            continue
        if not isinstance(normalized_kwargs, dict):
            continue
        item = Counterexample(normalized_args, normalized_kwargs)
        if item not in found:
            found.append(item)
    return tuple(found)


def _first_reduction(
    current: Counterexample,
    still_fails: Callable[[Counterexample], bool],
    remaining: int,
) -> tuple[Counterexample, int]:
    evaluated = 0
    for index, value in enumerate(current.args):
        for reduced in _reductions(value):
            args = (*current.args[:index], reduced, *current.args[index + 1 :])
            trial = replace(current, args=args)
            evaluated += 1
            if still_fails(trial):
                return trial, evaluated
            if evaluated >= remaining:
                return current, evaluated
    for key in sorted(current.kwargs):
        for reduced in _reductions(current.kwargs[key]):
            kwargs = dict(current.kwargs)
            kwargs[key] = reduced
            trial = replace(current, kwargs=kwargs)
            evaluated += 1
            if still_fails(trial):
                return trial, evaluated
            if evaluated >= remaining:
                return current, evaluated
    return current, evaluated


def _reductions(value: JsonValue) -> Iterable[JsonValue]:
    if isinstance(value, bool) or value is None:
        return ()
    if isinstance(value, int):
        sign = 1 if value > 0 else -1
        integer_options = (0, sign, int(value / 2))
        return tuple(
            dict.fromkeys(
                item for item in integer_options if item != value and abs(item) < abs(value)
            )
        )
    if isinstance(value, float):
        sign_float = 1.0 if value > 0 else -1.0
        float_options = (0.0, sign_float, value / 2)
        return tuple(
            dict.fromkeys(
                item for item in float_options if item != value and abs(item) < abs(value)
            )
        )
    if isinstance(value, str):
        return tuple(
            dict.fromkeys(item for item in ("", value[: len(value) // 2]) if item != value)
        )
    if isinstance(value, list):
        list_options: list[JsonValue] = [
            [],
            value[: len(value) // 2],
            value[len(value) // 2 :],
        ]
        for index, item in enumerate(value):
            for reduced in _reductions(item):
                list_options.append([*value[:index], reduced, *value[index + 1 :]])
        return _unique_json(list_options, value)
    if isinstance(value, dict):
        mapping_options: list[JsonValue] = [
            {key: item for key, item in value.items() if key != removed} for removed in value
        ]
        return _unique_json(mapping_options, value)
    return ()


def _unique_json(values: Iterable[JsonValue], original: JsonValue) -> tuple[JsonValue, ...]:
    unique: list[JsonValue] = []
    for value in values:
        if value != original and value not in unique:
            unique.append(value)
    return tuple(unique)


def score_evidence(evidence: Evidence, *, complexity_fit: bool = False) -> EvidenceScore:
    rates = {check_type: _pass_rate(evidence.checks, check_type) for check_type in SCORED_TYPES}
    runtime = sum(check.duration_s for check in evidence.checks)
    return EvidenceScore(
        evidence.viable,
        rates["sandbox"],
        rates["oracle"],
        rates["property"],
        rates["metamorphic"],
        rates["boundary"],
        complexity_fit,
        -runtime,
    )


def rank_candidates(
    candidates: Iterable[tuple[Candidate, Evidence, bool]],
) -> tuple[Candidate, ...]:
    """Order by observed evidence, with candidate ID as a stable final tie-breaker."""
    scored = list(candidates)
    scored.sort(key=lambda item: item[0].candidate_id)
    scored.sort(key=lambda item: score_evidence(item[1], complexity_fit=item[2]), reverse=True)
    return tuple(candidate for candidate, _, _ in scored)


def _pass_rate(checks: tuple[CheckResult, ...], check_type: str) -> float:
    relevant = [check for check in checks if check.check_type == check_type]
    if not relevant:
        return 0.0
    return sum(check.status is CheckStatus.PASSED for check in relevant) / len(relevant)
