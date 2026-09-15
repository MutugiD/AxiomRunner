"""Candidate verification coordinator."""

from __future__ import annotations

from axiomrunner.domain import Candidate, ChallengeProblem, Evidence
from axiomrunner.sandbox import DockerSandbox
from axiomrunner.static_validation import StaticVerifier


class CandidateVerifier:
    def __init__(self, static: StaticVerifier, sandbox: DockerSandbox) -> None:
        self.static = static
        self.sandbox = sandbox

    def verify(self, candidate: Candidate, problem: ChallengeProblem) -> Evidence:
        checks = self.static.verify(candidate, problem.entrypoint)
        if not all(check.status.value == "passed" for check in checks if check.mandatory):
            return Evidence(candidate.candidate_id, checks)
        dynamic = self.sandbox.verify(candidate, problem)
        return Evidence(candidate.candidate_id, (*checks, dynamic))
