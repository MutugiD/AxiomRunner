import json
from pathlib import Path

import pytest

from axiomrunner.cli import main
from axiomrunner.config import ConfigurationError
from axiomrunner.doctor import Diagnostic


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


def test_solve_validates_before_pipeline(tmp_path: Path, capsys: object) -> None:
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
    assert main(["solve", str(path), "--output", str(tmp_path / "solution.py")]) == 4


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
