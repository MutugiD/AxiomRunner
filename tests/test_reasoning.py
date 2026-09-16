import json

import pytest

from axiomrunner.adversarial import Counterexample
from axiomrunner.domain import Candidate, ChallengeProblem, ModelMetrics, VerificationKind
from axiomrunner.errors import ModelProtocolError
from axiomrunner.ollama import OllamaClient
from axiomrunner.reasoning import ProblemAnalysis, ReasoningEngine
from axiomrunner.reasoning import TestDesign as Design


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


def test_combined_planning_keeps_tests_candidate_independent() -> None:
    subject = engine(
        {
            "summary": "Compute one.",
            "invariants": ["Result is one"],
            "traps": ["No I/O"],
            "complexity_target": "O(1)",
            "cases": [
                {
                    "case_id": "constant",
                    "args": [],
                    "kwargs": {},
                    "expected_return": {"result": 1},
                }
            ],
            "strategies": [
                {
                    "strategy_id": "constant",
                    "approach": "Return one",
                    "time_complexity": "O(1)",
                }
            ],
        }
    )
    planning = subject.plan(problem(), 1, 5)
    assert planning.analysis.summary == "Compute one."
    assert planning.verification_suite.cases[0].expected == 1
    assert planning.strategies[0].strategy_id == "constant"


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


def test_repair_creates_deterministic_child_candidate() -> None:
    subject = engine(
        {"source": "def answer():\n    return 1\n", "complexity": "O(1)", "assumptions": []}
    )
    parent = Candidate("parent", "constant", "def answer():\n    return 0\n")
    repaired = subject.repair(problem(), _analysis_stub(), parent, (Counterexample((), {}),), 5)
    assert repaired.parent_id == "parent"
    assert repaired.revision == 1
    assert repaired.strategy_id == "constant"
    assert repaired.source.endswith("return 1\n")


def test_repair_requires_observed_counterexample() -> None:
    with pytest.raises(ValueError, match="counterexample"):
        engine().repair(
            problem(),
            _analysis_stub(),
            Candidate("parent", "constant", "pass"),
            (),
            5,
        )


def test_executable_verification_suite_is_structured_and_independent() -> None:
    subject = engine(
        {
            "oracle_source": "def reference():\n    return 1\n",
            "oracle_entrypoint": "reference",
            "cases": [
                {
                    "case_id": "small",
                    "kind": "oracle",
                    "args": [],
                    "kwargs": {},
                    "expected": None,
                    "comparison": "equal",
                    "followup_args": [],
                    "followup_kwargs": {},
                }
            ],
        }
    )
    design = subject.verification_suite(
        problem(),
        _design_stub(),
        5,
    )
    assert design.cases[0].kind is VerificationKind.ORACLE
    assert design.oracle_entrypoint == "reference"


def test_verification_suite_rejects_half_configured_oracle() -> None:
    subject = engine(
        {
            "oracle_source": "def reference(): return 1",
            "oracle_entrypoint": "",
            "cases": [
                {
                    "case_id": "boundary",
                    "kind": "boundary",
                    "args": [],
                    "kwargs": {},
                    "expected": 1,
                    "comparison": "equal",
                    "followup_args": [],
                    "followup_kwargs": {},
                }
            ],
        }
    )
    with pytest.raises(ModelProtocolError, match="both"):
        subject.verification_suite(problem(), _design_stub(), 5)


def _analysis_stub() -> ProblemAnalysis:
    return ProblemAnalysis("summary", (), (), (), (), "O(1)", (), ModelMetrics(0))


def _design_stub() -> Design:
    return Design(("empty",), ("constant",), (), "direct", ModelMetrics(0))
