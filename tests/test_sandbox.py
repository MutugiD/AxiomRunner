import pytest

from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckStatus,
    SandboxLimits,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)
from axiomrunner.errors import RuntimeUnavailableError
from axiomrunner.sandbox import DockerSandbox, ProcessResult, _run_process


def problem(examples: tuple[object, ...] = ()) -> ChallengeProblem:
    return ChallengeProblem("one", "python", "Return x.", "answer", examples, 300)  # type: ignore[arg-type]


def candidate() -> Candidate:
    return Candidate("one", "simple", "def answer(x=1):\n    return x\n")


def test_sandbox_command_enforces_container_controls() -> None:
    captured: list[str] = []

    def runner(command: object, timeout: float) -> ProcessResult:
        captured.extend(command)  # type: ignore[arg-type]
        assert timeout == 2.0
        return ProcessResult(0, '{"passed":1,"total":1,"failures":[]}', "")

    check = DockerSandbox(SandboxLimits(timeout_s=2.0), runner=runner).verify(
        candidate(), problem(({"args": [1], "expected": 1},))
    )
    assert check.status is CheckStatus.PASSED
    assert {"none", "--read-only", "ALL", "no-new-privileges"}.issubset(captured)
    assert any(item.endswith(":/work:ro") for item in captured)


def test_sandbox_records_candidate_failure() -> None:
    sandbox = DockerSandbox(
        SandboxLimits(), runner=lambda *_: ProcessResult(1, "", "Traceback: failure")
    )
    result = sandbox.verify(candidate(), problem())
    assert result.status is CheckStatus.FAILED
    assert result.details["returncode"] == 1


def test_sandbox_rejects_invalid_harness_output() -> None:
    sandbox = DockerSandbox(SandboxLimits(), runner=lambda *_: ProcessResult(0, "bad", ""))
    assert sandbox.verify(candidate(), problem()).status is CheckStatus.INCONCLUSIVE


def test_adversarial_suite_returns_per_case_evidence() -> None:
    output = (
        '{"results":['
        '{"passed":true,"counterexample":{"args":[0],"kwargs":{}},"actual":0,"expected":0},'
        '{"passed":false,"counterexample":{"args":[1],"kwargs":{}},"actual":1,"expected":2}'
        "]}"
    )
    sandbox = DockerSandbox(SandboxLimits(), runner=lambda *_: ProcessResult(0, output, ""))
    suite = VerificationSuite(
        (
            VerificationCase("zero", VerificationKind.BOUNDARY, CallSpec((0,)), 0),
            VerificationCase("one", VerificationKind.PROPERTY, CallSpec((1,)), 2),
        )
    )
    checks = sandbox.verify_suite(candidate(), problem(), suite)
    assert [check.check_type for check in checks] == ["boundary", "property"]
    assert [check.status for check in checks] == [CheckStatus.PASSED, CheckStatus.FAILED]
    assert checks[1].details["counterexample"] == {"args": [1], "kwargs": {}}
    assert checks[1].details["actual"] == 1
    assert checks[1].details["expected"] == 2


def test_adversarial_suite_requires_oracle_program() -> None:
    suite = VerificationSuite(
        (VerificationCase("oracle", VerificationKind.ORACLE, CallSpec((1,))),)
    )
    with pytest.raises(ValueError, match="oracle source"):
        DockerSandbox(SandboxLimits(), runner=lambda *_: ProcessResult(0, "", "")).verify_suite(
            candidate(), problem(), suite
        )


def test_default_runner_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("docker", 1)),
    )
    assert _run_process(["docker"], 1).returncode == 124


def test_default_runner_maps_missing_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("missing"))
    )
    with pytest.raises(RuntimeUnavailableError):
        _run_process(["docker"], 1)
