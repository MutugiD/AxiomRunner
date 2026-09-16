"""Immutable contracts shared by the solver's components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class SolveStatus(StrEnum):
    SUCCESS = "success"
    INVALID_INPUT = "invalid_input"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"
    NO_VIABLE_CANDIDATE = "no_viable_candidate"
    OUTPUT_FAILURE = "output_failure"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class VerificationKind(StrEnum):
    BOUNDARY = "boundary"
    ORACLE = "oracle"
    PROPERTY = "property"
    METAMORPHIC = "metamorphic"


class Comparison(StrEnum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    LESS_EQUAL = "less_equal"
    GREATER_EQUAL = "greater_equal"
    TRUTHY = "truthy"
    FALSY = "falsy"


@dataclass(frozen=True, slots=True)
class ChallengeProblem:
    problem_id: str
    language: str
    statement: str
    entrypoint: str
    public_examples: tuple[JsonValue, ...]
    deadline_s: float


@dataclass(frozen=True, slots=True)
class SandboxLimits:
    memory_mb: int = 256
    cpus: float = 1.0
    processes: int = 64
    timeout_s: float = 5.0


@dataclass(frozen=True, slots=True)
class SolveOptions:
    model: str = "qwen3:8b"
    ollama_host: str = "http://127.0.0.1:11434"
    seed: int = 7
    candidate_limit: int = 3
    repair_limit: int = 2
    sandbox: SandboxLimits = field(default_factory=SandboxLimits)
    verbose: bool = False


@dataclass(frozen=True, slots=True)
class ModelMetrics:
    duration_s: float
    prompt_tokens: int = 0
    response_tokens: int = 0


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    strategy_id: str
    source: str
    revision: int = 0
    parent_id: str | None = None
    metrics: ModelMetrics | None = None


@dataclass(frozen=True, slots=True)
class CallSpec:
    args: tuple[JsonValue, ...] = ()
    kwargs: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerificationCase:
    case_id: str
    kind: VerificationKind
    call: CallSpec
    expected: JsonValue = None
    comparison: Comparison = Comparison.EQUAL
    followup: CallSpec | None = None


@dataclass(frozen=True, slots=True)
class VerificationSuite:
    cases: tuple[VerificationCase, ...]
    oracle_source: str | None = None
    oracle_entrypoint: str | None = None


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_type: str
    origin: str
    status: CheckStatus
    duration_s: float
    mandatory: bool = True
    details: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Evidence:
    candidate_id: str
    checks: tuple[CheckResult, ...] = ()

    @property
    def viable(self) -> bool:
        return all(
            not check.mandatory or check.status is CheckStatus.PASSED for check in self.checks
        )


@dataclass(frozen=True, slots=True)
class SolveResult:
    status: SolveStatus
    elapsed_s: float
    solution_source: str | None = None
    selected_candidate_id: str | None = None
    evidence: tuple[Evidence, ...] = ()
    error: str | None = None
    cutoffs: tuple[str, ...] = ()
    candidates: tuple[Candidate, ...] = ()
    run_id: str | None = None

    @property
    def successful(self) -> bool:
        return self.status is SolveStatus.SUCCESS


def to_json_value(value: Any) -> JsonValue:
    """Narrow a recursively JSON-compatible value for typed report code."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, tuple | list):
        return [to_json_value(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: to_json_value(item) for key, item in value.items()}
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")
