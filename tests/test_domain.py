from axiomrunner.domain import (
    CheckResult,
    CheckStatus,
    Evidence,
    SolveResult,
    SolveStatus,
    to_json_value,
)


def test_evidence_requires_all_mandatory_checks() -> None:
    passing = CheckResult("syntax", "static", CheckStatus.PASSED, 0.1)
    optional = CheckResult("property", "generated", CheckStatus.FAILED, 0.1, mandatory=False)
    assert Evidence("candidate-1", (passing, optional)).viable
    assert not Evidence(
        "candidate-1", (passing, CheckResult("compile", "static", CheckStatus.FAILED, 0.1))
    ).viable


def test_solve_result_success_property() -> None:
    assert SolveResult(SolveStatus.SUCCESS, 1.0, solution_source="pass").successful
    assert not SolveResult(SolveStatus.INVALID_INPUT, 0.0).successful


def test_to_json_value_normalizes_tuples() -> None:
    assert to_json_value({"value": (1, True, None)}) == {"value": [1, True, None]}
