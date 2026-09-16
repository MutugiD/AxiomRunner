"""Command-line surface for AxiomRunner."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from axiomrunner.benchmark import BenchmarkRecord, benchmark_path, write_benchmark_report
from axiomrunner.config import ConfigurationError, load_options
from axiomrunner.doctor import run_doctor
from axiomrunner.domain import SolveStatus
from axiomrunner.errors import InvalidChallengeError, OutputWriteError, UnsupportedLanguageError
from axiomrunner.ingest import load_problem
from axiomrunner.output import atomic_write_text
from axiomrunner.reporting import write_report
from axiomrunner.solver import solve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axiomrunner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="solve one challenge JSON file")
    solve_parser.add_argument("problem")
    solve_parser.add_argument("--output", required=True)
    solve_parser.add_argument("--report")

    subparsers.add_parser("doctor", help="check local runtime prerequisites")
    benchmark_parser = subparsers.add_parser("benchmark", help="solve a file or directory corpus")
    benchmark_parser.add_argument("path")
    benchmark_parser.add_argument("--report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        options = load_options()
    except ConfigurationError as error:
        parser.error(str(error))

    if args.command == "doctor":
        diagnostics = run_doctor(options)
        for diagnostic in diagnostics:
            label = "PASS" if diagnostic.ok else "FAIL"
            print(f"{label} {diagnostic.name}: {diagnostic.detail}")
        return 0 if all(item.ok for item in diagnostics) else 3
    if args.command == "benchmark":
        try:
            benchmark = benchmark_path(args.path, options, on_record=_print_benchmark_record)
        except InvalidChallengeError as error:
            print(f"invalid: {error}")
            return 2
        print(
            f"benchmark: solved={benchmark.solved} "
            f"unsupported={benchmark.rejected_unsupported} elapsed={benchmark.elapsed_s:.2f}s"
        )
        if args.report:
            try:
                write_benchmark_report(args.report, benchmark, options)
            except OutputWriteError as error:
                print(f"output failure: {error}")
                return 5
        return 0 if benchmark.successful else 4
    try:
        problem = load_problem(args.problem)
    except UnsupportedLanguageError as error:
        print(f"unsupported: {error}")
        return 2
    except InvalidChallengeError as error:
        print(f"invalid: {error}")
        return 2
    if args.report and Path(args.output).resolve() == Path(args.report).resolve():
        print("invalid: output and report paths must be different")
        return 2
    result = solve(problem, options)
    if result.successful:
        if result.solution_source is None:
            result = replace(
                result,
                status=SolveStatus.OUTPUT_FAILURE,
                error="successful solve did not contain source",
            )
        else:
            try:
                atomic_write_text(args.output, result.solution_source)
            except OutputWriteError as error:
                result = replace(result, status=SolveStatus.OUTPUT_FAILURE, error=str(error))
    if args.report:
        try:
            write_report(args.report, problem, options, result)
        except OutputWriteError as error:
            print(f"output failure: {error}")
            return 5
    if result.successful:
        print(
            f"solved {problem.problem_id} with {result.selected_candidate_id} "
            f"in {result.elapsed_s:.2f}s"
        )
    else:
        print(f"{result.status.value}: {result.error or 'solve failed'}")
    return _exit_code(result.status)


def _exit_code(status: SolveStatus) -> int:
    return {
        SolveStatus.SUCCESS: 0,
        SolveStatus.INVALID_INPUT: 2,
        SolveStatus.UNSUPPORTED_LANGUAGE: 2,
        SolveStatus.RUNTIME_UNAVAILABLE: 3,
        SolveStatus.NO_VIABLE_CANDIDATE: 4,
        SolveStatus.OUTPUT_FAILURE: 5,
    }[status]


def _print_benchmark_record(record: BenchmarkRecord) -> None:
    print(
        f"{record.status:22} {record.file} "
        f"{record.elapsed_s:.2f}s candidates={record.candidates} repairs={record.repairs}",
        flush=True,
    )
