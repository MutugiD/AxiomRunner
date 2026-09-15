import pytest

from axiomrunner.domain import Candidate, CheckStatus
from axiomrunner.static_validation import StaticVerifier, extract_source


def candidate(source: str) -> Candidate:
    return Candidate("one", "strategy", source)


def failed_types(source: str) -> set[str]:
    return {
        check.check_type
        for check in StaticVerifier().verify(candidate(source), "answer")
        if check.status is CheckStatus.FAILED
    }


def test_valid_standard_library_candidate_passes() -> None:
    source = (
        '"""Solution."""\n'
        "from collections import deque\n"
        "LIMIT = 4\n"
        "def answer(x):\n"
        "    return deque([x]).pop()\n"
    )
    checks = StaticVerifier().verify(candidate(source), "answer")
    assert checks
    assert all(check.status is CheckStatus.PASSED for check in checks)


def test_single_code_fence_is_extracted() -> None:
    assert extract_source("```python\ndef answer():\n    return 1\n```").startswith("def answer")


@pytest.mark.parametrize(
    "source",
    [
        "text\n```python\ndef answer(): pass\n```",
        "```python\ndef answer(): pass\n```\n```python\npass\n```",
    ],
)
def test_deceptive_fences_fail(source: str) -> None:
    assert failed_types(source) == {"source"}


def test_syntax_and_entrypoint_failures_are_distinct() -> None:
    assert failed_types("def answer(:") == {"syntax"}
    assert "entrypoint" in failed_types("def other():\n    return 1")


@pytest.mark.parametrize(
    "source",
    [
        "import requests\ndef answer(): return 1",
        "import subprocess\ndef answer(): return 1",
        "from .local import value\ndef answer(): return value",
        "def answer():\n    print('bad')",
        "import sys\ndef answer():\n    return sys.stdin.read()",
        "VALUE = sum([1, 2])\ndef answer(): return VALUE",
    ],
)
def test_policy_rejects_untrusted_capabilities(source: str) -> None:
    assert "policy" in failed_types(source)
