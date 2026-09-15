"""Command-line surface for AxiomRunner."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from axiomrunner.config import ConfigurationError, load_options


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
        print(f"configured model: {options.model}")
        print("runtime checks are introduced in the ingestion slice")
        return 0
    if args.command == "benchmark":
        print(f"benchmark pipeline is not implemented: {args.path}")
        return 4
    print(f"solve pipeline is not implemented: {args.problem}")
    return 4
