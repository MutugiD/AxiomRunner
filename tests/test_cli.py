import json
from pathlib import Path

import pytest

from axiomrunner.cli import main
from axiomrunner.config import ConfigurationError
from axiomrunner.doctor import Diagnostic
from axiomrunner.domain import SolveResult, SolveStatus
from axiomrunner.errors import OutputWriteError


def test_doctor_reports_runtime_health(monkeypatch: pytest.MonkeyPatch, capsys: object) -> None:
    monkeypatch.setattr(
        "axiomrunner.cli.run_doctor", lambda _: (Diagnostic("ollama", True, "ready"),)
    )
    assert main(["doctor"]) == 0


def test_doctor_failure_uses_runtime_exit(monkeypatch: pytest.MonkeyPatch, capsys: object) -> None:
    monkeypatch.setattr(
        "axiomrunner.cli.run_doctor", lambda _: (Diagnostic("ollama", False, "missing"),)
    )
    assert main(["doctor"]) == 3


def test_configuration_error_is_cli_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise ConfigurationError("bad configuration")

    monkeypatch.setattr("axiomrunner.cli.load_options", fail)
    with pytest.raises(SystemExit) as raised:
        main(["doctor"])
    assert raised.value.code == 2


def test_unimplemented_benchmark_returns_no_candidate(capsys: object) -> None:
    assert main(["benchmark", "samples"]) == 4


def test_solve_writes_solution_and_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    path = tmp_path / "problem.json"
    path.write_text(
        json.dumps(
            {
                "problem_id": "one",
                "language": "python",
                "statement": "Return one.",
                "entrypoint": "answer",
                "public_examples": [],
                "deadline_s": 30,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "axiomrunner.cli.solve",
        lambda *_: SolveResult(
            SolveStatus.SUCCESS,
            1.0,
            solution_source="def answer():\n    return 1\n",
            selected_candidate_id="candidate",
            run_id="run-1",
        ),
    )
    output = tmp_path / "solution.py"
    report = tmp_path / "report.json"
    assert main(["solve", str(path), "--output", str(output), "--report", str(report)]) == 0
    assert "return 1" in output.read_text(encoding="utf-8")
    assert '"status": "success"' in report.read_text(encoding="utf-8")


def test_solve_maps_no_candidate_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    path = _problem_file(tmp_path)
    monkeypatch.setattr(
        "axiomrunner.cli.solve",
        lambda *_: SolveResult(SolveStatus.NO_VIABLE_CANDIDATE, 1.0, error="none"),
    )
    assert main(["solve", str(path), "--output", str(tmp_path / "solution.py")]) == 4


def test_solve_rejects_same_output_and_report_path(tmp_path: Path, capsys: object) -> None:
    path = _problem_file(tmp_path)
    destination = tmp_path / "same"
    assert (
        main(
            [
                "solve",
                str(path),
                "--output",
                str(destination),
                "--report",
                str(destination),
            ]
        )
        == 2
    )


def test_solve_maps_atomic_output_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: object
) -> None:
    path = _problem_file(tmp_path)
    monkeypatch.setattr(
        "axiomrunner.cli.solve",
        lambda *_: SolveResult(SolveStatus.SUCCESS, 1.0, solution_source="pass"),
    )
    monkeypatch.setattr(
        "axiomrunner.cli.atomic_write_text",
        lambda *_: (_ for _ in ()).throw(OutputWriteError("denied")),
    )
    assert main(["solve", str(path), "--output", str(tmp_path / "solution.py")]) == 5


def test_solve_rejects_rust(tmp_path: Path, capsys: object) -> None:
    path = tmp_path / "problem.json"
    path.write_text(
        json.dumps(
            {
                "problem_id": "one",
                "language": "rust",
                "statement": "No.",
                "entrypoint": "main",
                "public_examples": [],
                "deadline_s": 30,
            }
        ),
        encoding="utf-8",
    )
    assert main(["solve", str(path), "--output", str(tmp_path / "solution.py")]) == 2


def _problem_file(tmp_path: Path) -> Path:
    path = tmp_path / "problem.json"
    path.write_text(
        json.dumps(
            {
                "problem_id": "one",
                "language": "python",
                "statement": "Return one.",
                "entrypoint": "answer",
                "public_examples": [],
                "deadline_s": 30,
            }
        ),
        encoding="utf-8",
    )
    return path
