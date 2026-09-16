"""Sequential corpus benchmarking without retaining generated source."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from axiomrunner.domain import ChallengeProblem, SolveOptions, SolveResult, SolveStatus
from axiomrunner.errors import InvalidChallengeError, UnsupportedLanguageError
from axiomrunner.ingest import load_problem
from axiomrunner.output import atomic_write_text
from axiomrunner.solver import solve

SolveFunction = Callable[[ChallengeProblem, SolveOptions | None], SolveResult]
RecordCallback = Callable[["BenchmarkRecord"], None]


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    file: str
    problem_id: str | None
    status: str
    accepted: bool
    elapsed_s: float
    candidates: int = 0
    repairs: int = 0
    checks: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    records: tuple[BenchmarkRecord, ...]
    elapsed_s: float

    @property
    def successful(self) -> bool:
        return bool(self.records) and all(record.accepted for record in self.records)

    @property
    def solved(self) -> int:
        return sum(record.status == SolveStatus.SUCCESS.value for record in self.records)

    @property
    def rejected_unsupported(self) -> int:
        return sum(
            record.status == SolveStatus.UNSUPPORTED_LANGUAGE.value for record in self.records
        )


def benchmark_path(
    path: str | Path,
    options: SolveOptions,
    *,
    solve_function: SolveFunction = solve,
    clock: Callable[[], float] = time.monotonic,
    on_record: RecordCallback | None = None,
) -> BenchmarkResult:
    started = clock()
    records: list[BenchmarkRecord] = []
    for source in _challenge_files(Path(path)):
        item_started = clock()
        try:
            problem = load_problem(source)
        except UnsupportedLanguageError as error:
            record = BenchmarkRecord(
                source.name,
                None,
                SolveStatus.UNSUPPORTED_LANGUAGE.value,
                True,
                max(0.0, clock() - item_started),
                error=str(error),
            )
            records.append(record)
            if on_record:
                on_record(record)
            continue
        except InvalidChallengeError as error:
            record = BenchmarkRecord(
                source.name,
                None,
                SolveStatus.INVALID_INPUT.value,
                False,
                max(0.0, clock() - item_started),
                error=str(error),
            )
            records.append(record)
            if on_record:
                on_record(record)
            continue
        result = solve_function(problem, options)
        record = BenchmarkRecord(
            source.name,
            problem.problem_id,
            result.status.value,
            result.successful,
            result.elapsed_s,
            candidates=len(result.candidates),
            repairs=sum(candidate.revision > 0 for candidate in result.candidates),
            checks=sum(len(evidence.checks) for evidence in result.evidence),
            error=result.error,
        )
        records.append(record)
        if on_record:
            on_record(record)
    return BenchmarkResult(tuple(records), max(0.0, clock() - started))


def benchmark_document(result: BenchmarkResult, options: SolveOptions) -> dict[str, object]:
    return {
        "schema_version": 1,
        "successful": result.successful,
        "elapsed_s": result.elapsed_s,
        "solved": result.solved,
        "rejected_unsupported": result.rejected_unsupported,
        "model": options.model,
        "seed": options.seed,
        "records": [
            {
                "file": record.file,
                "problem_id": record.problem_id,
                "status": record.status,
                "accepted": record.accepted,
                "elapsed_s": record.elapsed_s,
                "candidates": record.candidates,
                "repairs": record.repairs,
                "checks": record.checks,
                "error": record.error,
            }
            for record in result.records
        ],
    }


def write_benchmark_report(
    path: str | Path, result: BenchmarkResult, options: SolveOptions
) -> None:
    atomic_write_text(
        path,
        json.dumps(benchmark_document(result, options), indent=2, sort_keys=True) + "\n",
    )


def _challenge_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    if path.is_dir():
        return tuple(sorted(path.glob("*.json"), key=lambda item: item.name))
    raise InvalidChallengeError(f"benchmark path does not exist: {path.name}")
