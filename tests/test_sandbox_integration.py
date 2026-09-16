import os

import pytest

from axiomrunner.adversarial import AdversarialVerifier, Counterexample
from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckStatus,
    Comparison,
    JsonValue,
    ModelMetrics,
    SandboxLimits,
    SolveOptions,
    SolveStatus,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)
from axiomrunner.reasoning import ProblemAnalysis, Strategy
from axiomrunner.reasoning import TestDesign as Design
from axiomrunner.sandbox import DockerSandbox
from axiomrunner.solver import SolveOrchestrator
from axiomrunner.static_validation import StaticVerifier
from axiomrunner.verification import CandidateVerifier

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        os.environ.get("AXIOMRUNNER_DOCKER_TEST") != "1",
        reason="set AXIOMRUNNER_DOCKER_TEST=1 to run container integration checks",
    ),
]


def verify(
    source: str, *, args: list[JsonValue], expected: JsonValue, timeout: float = 5.0
) -> CheckStatus:
    candidate = Candidate("integration", "sandbox", source)
    problem = ChallengeProblem(
        "integration",
        "python",
        "Sandbox integration fixture.",
        "answer",
        ({"args": args, "expected": expected},),
        30,
    )
    return DockerSandbox(SandboxLimits(timeout_s=timeout)).verify(candidate, problem).status


def test_real_container_executes_valid_candidate() -> None:
    assert verify("def answer(x):\n    return x + 1\n", args=[1], expected=2) is CheckStatus.PASSED


def test_real_container_blocks_work_mount_writes() -> None:
    source = "def answer():\n    open('/work/created', 'w').write('bad')\n    return 1\n"
    assert verify(source, args=[], expected=1) is CheckStatus.FAILED


def test_real_container_has_no_network() -> None:
    source = (
        "def answer():\n"
        "    import socket\n"
        "    connection = socket.socket()\n"
        "    connection.settimeout(0.5)\n"
        "    return connection.connect_ex(('1.1.1.1', 80))\n"
    )
    assert verify(source, args=[], expected=0) is CheckStatus.FAILED


def test_real_container_enforces_host_timeout() -> None:
    source = "def answer():\n    while True:\n        pass\n"
    assert verify(source, args=[], expected=None, timeout=1.0) is CheckStatus.FAILED


def test_real_container_executes_all_independent_check_kinds() -> None:
    candidate = Candidate("suite", "square", "def answer(x):\n    return x * x\n")
    problem = ChallengeProblem("suite", "python", "Square x.", "answer", (), 30)
    suite = VerificationSuite(
        (
            VerificationCase("zero", VerificationKind.BOUNDARY, CallSpec((0,)), 0),
            VerificationCase("small", VerificationKind.ORACLE, CallSpec((3,))),
            VerificationCase(
                "nonnegative",
                VerificationKind.PROPERTY,
                CallSpec((-2,)),
                0,
                Comparison.GREATER_EQUAL,
            ),
            VerificationCase(
                "sign",
                VerificationKind.METAMORPHIC,
                CallSpec((2,)),
                followup=CallSpec((-2,)),
            ),
        ),
        oracle_source="def reference(x):\n    return x * x\n",
        oracle_entrypoint="reference",
    )
    checks = DockerSandbox(SandboxLimits()).verify_suite(candidate, problem, suite)
    assert len(checks) == 4
    assert all(check.status is CheckStatus.PASSED for check in checks)


class IntegrationEngine:
    def analyze(self, problem: ChallengeProblem, timeout_s: float) -> ProblemAnalysis:
        del problem, timeout_s
        return ProblemAnalysis("square", (), (), (), (), "O(1)", (), ModelMetrics(0))

    def design_tests(self, problem: ChallengeProblem, timeout_s: float) -> Design:
        del problem, timeout_s
        return Design(("two",), (), (), "direct", ModelMetrics(0))

    def verification_suite(
        self, problem: ChallengeProblem, design: Design, timeout_s: float
    ) -> VerificationSuite:
        del problem, design, timeout_s
        return VerificationSuite(
            (VerificationCase("two", VerificationKind.BOUNDARY, CallSpec((2,)), 4),)
        )

    def strategies(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        limit: int,
        timeout_s: float,
    ) -> tuple[Strategy, ...]:
        del problem, analysis, limit, timeout_s
        return (Strategy("square", "Square", "multiply", "O(1)", "O(1)", ()),)

    def generate(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        strategy: Strategy,
        timeout_s: float,
    ) -> Candidate:
        del problem, analysis, strategy, timeout_s
        return Candidate("candidate", "square", "def square(x):\n    return x * x\n")

    def repair(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        parent: Candidate,
        counterexamples: tuple[Counterexample, ...],
        timeout_s: float,
        failures: tuple[str, ...] = (),
    ) -> Candidate:
        del problem, analysis, parent, counterexamples, timeout_s, failures
        raise AssertionError("valid fixture must not repair")


def test_real_end_to_end_orchestrator_uses_docker_evidence() -> None:
    static = StaticVerifier()
    sandbox = DockerSandbox(SandboxLimits())
    orchestrator = SolveOrchestrator(
        IntegrationEngine(),  # type: ignore[arg-type]
        CandidateVerifier(static, sandbox),
        AdversarialVerifier(static, sandbox),
        static,
        run_id_factory=lambda: "docker-run",
    )
    challenge = ChallengeProblem("square", "python", "Square x.", "square", (), 30)
    result = orchestrator.solve(challenge, SolveOptions(candidate_limit=1, repair_limit=0))
    assert result.status is SolveStatus.SUCCESS
    assert result.solution_source == "def square(x):\n    return x * x\n"
