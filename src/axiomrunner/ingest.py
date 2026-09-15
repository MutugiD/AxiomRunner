"""Strict challenge JSON ingestion."""

from __future__ import annotations

import json
import keyword
import math
from pathlib import Path
from typing import Any

from axiomrunner.domain import ChallengeProblem, to_json_value
from axiomrunner.errors import InvalidChallengeError, UnsupportedLanguageError


def _required_string(document: dict[str, Any], name: str) -> str:
    value = document.get(name)
    if not isinstance(value, str) or not value.strip():
        raise InvalidChallengeError(f"{name} must be a nonempty string")
    return value


def parse_problem(document: object) -> ChallengeProblem:
    """Validate a decoded JSON challenge without mutating it."""
    if not isinstance(document, dict) or not all(isinstance(key, str) for key in document):
        raise InvalidChallengeError("challenge must be a JSON object with string keys")

    problem_id = _required_string(document, "problem_id")
    language = _required_string(document, "language")
    if language != "python":
        raise UnsupportedLanguageError(f"unsupported challenge language: {language}")

    statement = _required_string(document, "statement")
    entrypoint = _required_string(document, "entrypoint")
    if not entrypoint.isidentifier() or keyword.iskeyword(entrypoint):
        raise InvalidChallengeError("entrypoint must be a valid non-keyword Python identifier")

    examples = document.get("public_examples")
    if not isinstance(examples, list):
        raise InvalidChallengeError("public_examples must be a JSON array")
    try:
        normalized_examples = tuple(to_json_value(example) for example in examples)
    except TypeError as error:
        raise InvalidChallengeError("public_examples must contain JSON values") from error

    deadline = document.get("deadline_s")
    if isinstance(deadline, bool) or not isinstance(deadline, int | float):
        raise InvalidChallengeError("deadline_s must be a finite number")
    deadline_s = float(deadline)
    if not math.isfinite(deadline_s) or deadline_s <= 10.0:
        raise InvalidChallengeError("deadline_s must be greater than the 10 second reserve")

    return ChallengeProblem(
        problem_id=problem_id,
        language=language,
        statement=statement,
        entrypoint=entrypoint,
        public_examples=normalized_examples,
        deadline_s=deadline_s,
    )


def load_problem(path: str | Path) -> ChallengeProblem:
    """Read and validate one UTF-8 challenge JSON file."""
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InvalidChallengeError(f"cannot read challenge: {error}") from error
    return parse_problem(document)
