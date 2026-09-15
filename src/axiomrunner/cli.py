"""Command-line surface for AxiomRunner."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from axiomrunner.config import ConfigurationError, load_options
from axiomrunner.doctor import run_doctor
from axiomrunner.errors import InvalidChallengeError, UnsupportedLanguageError
from axiomrunner.ingest import load_problem


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
        print(f"benchmark pipeline is not implemented: {args.path}")
        return 4
    try:
        problem = load_problem(args.problem)
    except UnsupportedLanguageError as error:
        print(f"unsupported: {error}")
        return 2
    except InvalidChallengeError as error:
        print(f"invalid: {error}")
        return 2
    print(f"solve pipeline is not implemented: {problem.problem_id}")
    return 4
