import json

import pytest

from axiomrunner.domain import ChallengeProblem, ModelMetrics
from axiomrunner.errors import ModelProtocolError
from axiomrunner.ollama import OllamaClient
from axiomrunner.reasoning import ProblemAnalysis, ReasoningEngine


def problem() -> ChallengeProblem:
    return ChallengeProblem("one", "python", "Return one.", "answer", (), 300)


class Replies:
    def __init__(self, values: list[object]) -> None:
        self.values = iter(values)

    def __call__(self, url: str, body: bytes, timeout: float) -> bytes:
        del url, body, timeout
        value = next(self.values)
        return json.dumps({"message": {"content": json.dumps(value)}}).encode()


def engine(*values: object) -> ReasoningEngine:
    client = OllamaClient("http://localhost:11434", "qwen3:8b", transport=Replies(list(values)))
    return ReasoningEngine(client)


def analysis_value() -> dict[str, object]:
    return {
        "summary": "Compute one.",
        "constraints": ["No arguments"],
        "invariants": ["Result is one"],
        "ambiguities": [],
        "traps": ["No I/O"],
        "complexity_target": "O(1)",
        "test_ideas": ["Call once"],
    }


def test_all_reasoning_roles_are_schema_constrained() -> None:
    subject = engine(
        analysis_value(),
        {
            "boundary_cases": ["No arguments"],
            "properties": ["Always one"],
            "metamorphic_relations": [],
            "oracle_plan": "Direct comparison",
        },
        {
            "strategies": [
                {
                    "strategy_id": "constant",
                    "title": "Constant",
                    "approach": "Return 1",
                    "time_complexity": "O(1)",
                    "space_complexity": "O(1)",
                    "risks": [],
                }
            ]
        },
        {"source": "def answer():\n    return 1\n", "complexity": "O(1)", "assumptions": []},
    )
    analysis = subject.analyze(problem(), 5)
    tests = subject.design_tests(problem(), 5)
    strategy = subject.strategies(problem(), analysis, 2, 5)[0]
    candidate = subject.generate(problem(), analysis, strategy, 5)
    assert analysis.complexity_target == "O(1)"
    assert tests.oracle_plan == "Direct comparison"
    assert strategy.strategy_id == "constant"
    assert candidate.source.startswith("def answer")
    assert len(candidate.candidate_id) == 16


def test_strategy_ids_must_be_unique() -> None:
    duplicate = {
        "strategy_id": "same",
        "title": "Same",
        "approach": "Same",
        "time_complexity": "O(1)",
        "space_complexity": "O(1)",
        "risks": [],
    }
    subject = engine({"strategies": [duplicate, duplicate]})
    with pytest.raises(ModelProtocolError, match="unique"):
        subject.strategies(problem(), _analysis_stub(), 2, 5)


def test_semantically_invalid_analysis_is_rejected() -> None:
    value = analysis_value()
    value["summary"] = ""
    with pytest.raises(ModelProtocolError, match="summary"):
        engine(value).analyze(problem(), 5)


def _analysis_stub() -> ProblemAnalysis:
    return ProblemAnalysis("summary", (), (), (), (), "O(1)", (), ModelMetrics(0))
