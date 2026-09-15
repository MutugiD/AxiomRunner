import os

import pytest

from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckStatus,
    Comparison,
    JsonValue,
    SandboxLimits,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)
from axiomrunner.sandbox import DockerSandbox

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
