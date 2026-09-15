from axiomrunner.domain import Candidate, ChallengeProblem, CheckResult, CheckStatus
from axiomrunner.verification import CandidateVerifier


class StaticStub:
    def __init__(self, status: CheckStatus) -> None:
        self.status = status

    def verify(self, candidate: Candidate, entrypoint: str) -> tuple[CheckResult, ...]:
        del candidate, entrypoint
        return (CheckResult("static", "test", self.status, 0),)


class SandboxStub:
    called = False

    def verify(self, candidate: Candidate, problem: ChallengeProblem) -> CheckResult:
        del candidate, problem
        self.called = True
        return CheckResult("sandbox", "test", CheckStatus.PASSED, 0)


def values() -> tuple[Candidate, ChallengeProblem]:
    return Candidate("one", "strategy", "def answer(): return 1"), ChallengeProblem(
        "one", "python", "Return one.", "answer", (), 300
    )


def test_static_failure_short_circuits_sandbox() -> None:
    dynamic = SandboxStub()
    verifier = CandidateVerifier(StaticStub(CheckStatus.FAILED), dynamic)  # type: ignore[arg-type]
    evidence = verifier.verify(*values())
    assert not evidence.viable
    assert not dynamic.called


def test_static_success_adds_sandbox_evidence() -> None:
    dynamic = SandboxStub()
    verifier = CandidateVerifier(StaticStub(CheckStatus.PASSED), dynamic)  # type: ignore[arg-type]
    evidence = verifier.verify(*values())
    assert evidence.viable
    assert dynamic.called
    assert len(evidence.checks) == 2
