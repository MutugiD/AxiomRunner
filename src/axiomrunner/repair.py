"""Deadline- and count-bounded counterexample-led repair coordination."""

from __future__ import annotations

from axiomrunner.adversarial import Counterexample
from axiomrunner.budget import BudgetManager
from axiomrunner.candidates import CandidateRepository
from axiomrunner.domain import Candidate, ChallengeProblem
from axiomrunner.reasoning import ProblemAnalysis, ReasoningEngine


class RepairCoordinator:
    def __init__(
        self,
        engine: ReasoningEngine,
        repository: CandidateRepository,
        budget: BudgetManager,
        repair_limit: int,
    ) -> None:
        if repair_limit < 0:
            raise ValueError("repair limit cannot be negative")
        self.engine = engine
        self.repository = repository
        self.budget = budget
        self.repair_limit = repair_limit

    def repair(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        parent: Candidate,
        counterexamples: tuple[Counterexample, ...],
    ) -> Candidate | None:
        """Create and register one repair, or decline when a hard gate is closed."""
        if parent.revision >= self.repair_limit or not self.budget.can_start_repair():
            return None
        timeout_s = self.budget.request_timeout(self.budget.phase.repair_cutoff)
        if timeout_s <= 0:
            return None
        repaired = self.engine.repair(problem, analysis, parent, counterexamples, timeout_s)
        self.repository.add(repaired)
        return repaired
