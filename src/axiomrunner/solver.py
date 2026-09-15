"""Public solve service placeholder completed by later vertical slices."""

from __future__ import annotations

from axiomrunner.domain import ChallengeProblem, SolveOptions, SolveResult, SolveStatus


def solve(problem: ChallengeProblem, options: SolveOptions | None = None) -> SolveResult:
    """Solve a challenge through the configured local pipeline.

    The package bootstrap intentionally exposes the stable signature before the
    orchestration implementation is introduced.
    """
    del problem, options
    return SolveResult(
        status=SolveStatus.NO_VIABLE_CANDIDATE,
        elapsed_s=0.0,
        error="solve pipeline is not implemented yet",
    )
