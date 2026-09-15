import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from axiomrunner.doctor import Diagnostic, _docker, _ollama, is_loopback_url, run_doctor
from axiomrunner.domain import SolveOptions


def test_loopback_policy() -> None:
    assert is_loopback_url("http://127.0.0.1:11434")
    assert is_loopback_url("http://localhost:11434")
    assert not is_loopback_url("https://ollama.example.com")
    assert not is_loopback_url("http://192.168.1.2:11434")


def test_doctor_aggregates_checks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import axiomrunner.doctor as doctor

    monkeypatch.setattr(doctor, "_ollama", lambda _: Diagnostic("ollama", True, "ok"))
    monkeypatch.setattr(doctor, "_docker", lambda: Diagnostic("docker", True, "ok"))
    checks = run_doctor(SolveOptions(), tmp_path)
    assert [check.name for check in checks] == ["ollama", "docker", "output"]
    assert all(check.ok for check in checks)


def test_ollama_rejects_remote_endpoint_without_request() -> None:
    result = _ollama(SolveOptions(ollama_host="https://ollama.example.com"))
    assert not result.ok


def test_ollama_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    import axiomrunner.doctor as doctor

    monkeypatch.setattr(doctor, "urlopen", Mock(side_effect=OSError("offline")))
    result = _ollama(SolveOptions())
    assert not result.ok
    assert "unavailable" in result.detail


def test_docker_reports_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr(shutil, "which", lambda _: None)
    assert not _docker().ok


def test_docker_reports_server_version(monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr(shutil, "which", lambda _: "docker")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "29.0", ""),
    )
    result = _docker()
    assert result.ok
    assert "29.0" in result.detail
