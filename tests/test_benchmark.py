import json
from pathlib import Path

import pytest

from axiomrunner.benchmark import benchmark_document, benchmark_path, write_benchmark_report
from axiomrunner.domain import Candidate, ChallengeProblem, SolveOptions, SolveResult, SolveStatus
from axiomrunner.errors import InvalidChallengeError


def write_problem(path: Path, *, language: str = "python") -> None:
    path.write_text(
        json.dumps(
            {
                "problem_id": path.stem,
                "language": language,
                "statement": "Return one.",
                "entrypoint": "answer" if language == "python" else "main",
                "public_examples": [],
                "deadline_s": 300,
            }
        ),
        encoding="utf-8",
    )


def test_benchmark_solves_python_and_accepts_early_rust_rejection(tmp_path: Path) -> None:
    write_problem(tmp_path / "a-python.json")
    write_problem(tmp_path / "b-rust.json", language="rust")
    called: list[str] = []

    def fake_solve(problem: ChallengeProblem, options: SolveOptions | None = None) -> SolveResult:
        del options
        called.append(problem.problem_id)
        return SolveResult(
            SolveStatus.SUCCESS,
            1.0,
            candidates=(Candidate("one", "strategy", "source"),),
        )

    result = benchmark_path(tmp_path, SolveOptions(), solve_function=fake_solve)
    assert result.successful
    assert result.solved == 1
    assert result.rejected_unsupported == 1
    assert called == ["a-python"]


def test_benchmark_records_invalid_and_failed_inputs(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    write_problem(tmp_path / "python.json")

    def no_candidate(problem: ChallengeProblem, options: SolveOptions | None = None) -> SolveResult:
        del problem, options
        return SolveResult(SolveStatus.NO_VIABLE_CANDIDATE, 2.0, error="none")

    result = benchmark_path(tmp_path, SolveOptions(), solve_function=no_candidate)
    assert not result.successful
    assert [record.status for record in result.records] == [
        "invalid_input",
        "no_viable_candidate",
    ]


def test_benchmark_report_is_aggregate_only(tmp_path: Path) -> None:
    write_problem(tmp_path / "problem.json")
    result = benchmark_path(
        tmp_path,
        SolveOptions(),
        solve_function=lambda *_: SolveResult(SolveStatus.SUCCESS, 1.0),
    )
    document = benchmark_document(result, SolveOptions())
    assert "source" not in str(document).lower()
    destination = tmp_path / "summary.json"
    write_benchmark_report(destination, result, SolveOptions())
    assert '"successful": true' in destination.read_text(encoding="utf-8")


def test_benchmark_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(InvalidChallengeError, match="does not exist"):
        benchmark_path(tmp_path / "missing", SolveOptions())
