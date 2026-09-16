from pathlib import Path

from axiomrunner.domain import (
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    Evidence,
    SolveOptions,
    SolveResult,
    SolveStatus,
)
from axiomrunner.reporting import report_document, write_report


def test_report_is_redacted_and_contains_observed_evidence(tmp_path: Path) -> None:
    candidate = Candidate("candidate", "strategy", "SECRET SOURCE")
    result = SolveResult(
        SolveStatus.SUCCESS,
        1.5,
        solution_source="SECRET SOURCE",
        selected_candidate_id="candidate",
        evidence=(
            Evidence(
                "candidate",
                (CheckResult("boundary", "independent", CheckStatus.PASSED, 0.1),),
            ),
        ),
        candidates=(candidate,),
        run_id="run-1",
    )
    problem = ChallengeProblem("problem", "python", "statement", "answer", (), 300)
    document = report_document(problem, SolveOptions(), result)
    assert document["run_id"] == "run-1"
    assert document["selected_candidate_id"] == "candidate"
    assert "SECRET SOURCE" not in str(document)
    destination = tmp_path / "report.json"
    write_report(destination, problem, SolveOptions(), result)
    assert '"schema_version": 1' in destination.read_text(encoding="utf-8")
