import pytest

from axiomrunner.adversarial import (
    AdversarialVerifier,
    Counterexample,
    counterexamples_from_evidence,
    minimize_counterexample,
    rank_candidates,
    score_evidence,
    validate_suite,
)
from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    Evidence,
    JsonValue,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)


def case(kind: VerificationKind = VerificationKind.BOUNDARY) -> VerificationCase:
    followup = CallSpec((2,)) if kind is VerificationKind.METAMORPHIC else None
    return VerificationCase("edge", kind, CallSpec((1,)), 1, followup=followup)


def test_suite_requires_unique_well_formed_cases() -> None:
    with pytest.raises(ValueError, match="unique"):
        validate_suite(VerificationSuite((case(), case())))
    with pytest.raises(ValueError, match="followup"):
        validate_suite(
            VerificationSuite(
                (VerificationCase("relation", VerificationKind.METAMORPHIC, CallSpec()),)
            )
        )
    with pytest.raises(ValueError, match="oracle source"):
        validate_suite(VerificationSuite((case(VerificationKind.ORACLE),)))


def test_counterexample_minimization_preserves_failure() -> None:
    original = Counterexample((100,), {})
    minimized = minimize_counterexample(
        original,
        lambda item: isinstance(item.args[0], int) and item.args[0] >= 10,
    )
    assert minimized.args == (12,)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(8.0, 0.0), ("abcdef", ""), ([1, 2, 3], []), ({"a": 1, "b": 2}, {})],
)
def test_counterexample_minimization_handles_json_shapes(
    value: JsonValue, expected: JsonValue
) -> None:
    minimized = minimize_counterexample(Counterexample((), {"value": value}), lambda _: True)
    assert minimized.kwargs["value"] == expected


def test_counterexample_minimization_honors_zero_evaluation_budget() -> None:
    original = Counterexample((100,), {})
    assert minimize_counterexample(original, lambda _: True, max_evaluations=0) == original


def test_evidence_score_uses_observed_checks_and_stable_ranking() -> None:
    fast = Candidate("a", "one", "pass")
    slow = Candidate("b", "two", "pass")
    fast_evidence = Evidence(
        "a",
        (
            CheckResult("sandbox", "docker", CheckStatus.PASSED, 0.1),
            CheckResult("oracle", "independent", CheckStatus.PASSED, 0.1),
        ),
    )
    slow_evidence = Evidence(
        "b",
        (
            CheckResult("sandbox", "docker", CheckStatus.PASSED, 0.5),
            CheckResult("oracle", "independent", CheckStatus.PASSED, 0.5),
        ),
    )
    assert score_evidence(fast_evidence) > score_evidence(slow_evidence)
    assert rank_candidates(((slow, slow_evidence, False), (fast, fast_evidence, False))) == (
        fast,
        slow,
    )


def test_counterexamples_are_extracted_only_from_observed_failures() -> None:
    evidence = Evidence(
        "candidate",
        (
            CheckResult(
                "boundary",
                "independent",
                CheckStatus.FAILED,
                0,
                details={"counterexample": {"args": [3], "kwargs": {"flag": True}}},
            ),
            CheckResult(
                "boundary",
                "independent",
                CheckStatus.PASSED,
                0,
                details={"counterexample": {"args": [9], "kwargs": {}}},
            ),
            CheckResult(
                "property",
                "independent",
                CheckStatus.FAILED,
                0,
                details={"counterexample": "invalid"},
            ),
        ),
    )
    assert counterexamples_from_evidence(evidence) == (Counterexample((3,), {"flag": True}),)


class FailingStatic:
    def verify(self, candidate: Candidate, entrypoint: str) -> tuple[CheckResult, ...]:
        del candidate, entrypoint
        return (CheckResult("policy", "static", CheckStatus.FAILED, 0.1),)


class UnusedSandbox:
    def verify_suite(
        self, candidate: Candidate, problem: ChallengeProblem, suite: VerificationSuite
    ) -> tuple[CheckResult, ...]:
        del candidate, problem, suite
        raise AssertionError("unsafe oracle must not execute")


class PassingStatic:
    def verify(self, candidate: Candidate, entrypoint: str) -> tuple[CheckResult, ...]:
        del candidate, entrypoint
        return (CheckResult("policy", "static", CheckStatus.PASSED, 0.1),)


class PassingSandbox:
    def verify_suite(
        self, candidate: Candidate, problem: ChallengeProblem, suite: VerificationSuite
    ) -> tuple[CheckResult, ...]:
        del candidate, problem, suite
        return (CheckResult("oracle", "independent", CheckStatus.PASSED, 0.1),)


def test_invalid_independent_oracle_is_inconclusive_not_candidate_failure() -> None:
    suite = VerificationSuite(
        (case(VerificationKind.ORACLE),),
        oracle_source="def reference(x): return x",
        oracle_entrypoint="reference",
    )
    verifier = AdversarialVerifier(FailingStatic(), UnusedSandbox())  # type: ignore[arg-type]
    checks = verifier.verify(
        Candidate("one", "strategy", "def answer(x): return x"),
        ChallengeProblem("one", "python", "identity", "answer", (), 300),
        suite,
    )
    assert checks[0].status is CheckStatus.INCONCLUSIVE
    assert not checks[0].mandatory


def test_valid_independent_oracle_reaches_sandbox() -> None:
    suite = VerificationSuite(
        (case(VerificationKind.ORACLE),),
        oracle_source="def reference(x): return x",
        oracle_entrypoint="reference",
    )
    verifier = AdversarialVerifier(PassingStatic(), PassingSandbox())  # type: ignore[arg-type]
    checks = verifier.verify(
        Candidate("one", "strategy", "def answer(x): return x"),
        ChallengeProblem("one", "python", "identity", "answer", (), 300),
        suite,
    )
    assert checks[0].status is CheckStatus.PASSED


def test_invalid_oracle_does_not_discard_safe_boundary_cases() -> None:
    suite = VerificationSuite(
        (
            case(VerificationKind.ORACLE),
            VerificationCase("boundary", VerificationKind.BOUNDARY, CallSpec((1,)), 1),
        ),
        oracle_source="def reference(x): return x",
        oracle_entrypoint="reference",
    )
    verifier = AdversarialVerifier(FailingStatic(), PassingSandbox())  # type: ignore[arg-type]
    checks = verifier.verify(
        Candidate("one", "strategy", "def answer(x): return x"),
        ChallengeProblem("one", "python", "identity", "answer", (), 300),
        suite,
    )
    assert [check.status for check in checks] == [
        CheckStatus.INCONCLUSIVE,
        CheckStatus.PASSED,
    ]


def test_suite_rejects_empty_too_large_and_unexpected_followup() -> None:
    with pytest.raises(ValueError, match="at least one"):
        validate_suite(VerificationSuite(()))
    with pytest.raises(ValueError, match="exceeds"):
        validate_suite(
            VerificationSuite(
                tuple(
                    VerificationCase(str(index), VerificationKind.BOUNDARY, CallSpec())
                    for index in range(257)
                )
            )
        )
    with pytest.raises(ValueError, match="cannot have"):
        validate_suite(
            VerificationSuite(
                (
                    VerificationCase(
                        "boundary",
                        VerificationKind.BOUNDARY,
                        CallSpec(),
                        followup=CallSpec(),
                    ),
                )
            )
        )
