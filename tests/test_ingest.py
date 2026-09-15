import json

import pytest

from axiomrunner.errors import InvalidChallengeError, UnsupportedLanguageError
from axiomrunner.ingest import load_problem, parse_problem


def valid_document() -> dict[str, object]:
    return {
        "problem_id": "problem-1",
        "language": "python",
        "statement": "Return the value.",
        "entrypoint": "solve_value",
        "public_examples": [{"args": [1], "expected": 1}],
        "deadline_s": 300,
    }


def test_parse_problem_normalizes_without_mutation() -> None:
    document = valid_document()
    problem = parse_problem(document)
    assert problem.problem_id == "problem-1"
    assert problem.public_examples == ({"args": [1], "expected": 1},)
    assert document["public_examples"] == [{"args": [1], "expected": 1}]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("problem_id", ""),
        ("statement", None),
        ("entrypoint", "not-valid"),
        ("entrypoint", "class"),
        ("public_examples", {}),
        ("deadline_s", True),
        ("deadline_s", 10),
        ("deadline_s", float("inf")),
    ],
)
def test_invalid_fields_are_rejected(field: str, value: object) -> None:
    document = valid_document()
    document[field] = value
    with pytest.raises(InvalidChallengeError):
        parse_problem(document)


def test_non_object_is_rejected() -> None:
    with pytest.raises(InvalidChallengeError):
        parse_problem([])


def test_non_json_example_is_rejected() -> None:
    document = valid_document()
    document["public_examples"] = [object()]
    with pytest.raises(InvalidChallengeError, match="JSON values"):
        parse_problem(document)


def test_rust_is_rejected_before_other_services() -> None:
    document = valid_document()
    document["language"] = "rust"
    with pytest.raises(UnsupportedLanguageError):
        parse_problem(document)


def test_load_problem_reads_utf8_json(tmp_path: object) -> None:
    path = tmp_path / "problem.json"  # type: ignore[operator]
    path.write_text(json.dumps(valid_document()), encoding="utf-8")
    assert load_problem(path).entrypoint == "solve_value"


def test_load_problem_wraps_decode_failure(tmp_path: object) -> None:
    path = tmp_path / "bad.json"  # type: ignore[operator]
    path.write_text("{", encoding="utf-8")
    with pytest.raises(InvalidChallengeError, match="cannot read challenge"):
        load_problem(path)
