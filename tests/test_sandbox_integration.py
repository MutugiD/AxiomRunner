import os

import pytest

from axiomrunner.domain import Candidate, ChallengeProblem, CheckStatus, JsonValue, SandboxLimits
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
