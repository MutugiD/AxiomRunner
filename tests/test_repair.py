from axiomrunner.adversarial import Counterexample
from axiomrunner.budget import BudgetManager
from axiomrunner.candidates import CandidateRepository
from axiomrunner.domain import Candidate, ChallengeProblem, ModelMetrics
from axiomrunner.reasoning import ProblemAnalysis
from axiomrunner.repair import RepairCoordinator


class Clock:
    value = 0.0

    def __call__(self) -> float:
        return self.value


class RepairEngine:
    timeout = 0.0

    def repair(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        parent: Candidate,
        counterexamples: tuple[Counterexample, ...],
        timeout_s: float,
    ) -> Candidate:
        del problem, analysis, counterexamples
        self.timeout = timeout_s
        return Candidate(
            "child",
            parent.strategy_id,
            "fixed",
            revision=parent.revision + 1,
            parent_id=parent.candidate_id,
        )


def values() -> tuple[ChallengeProblem, ProblemAnalysis, Candidate]:
    return (
        ChallengeProblem("one", "python", "Return one", "answer", (), 300),
        ProblemAnalysis("summary", (), (), (), (), "O(1)", (), ModelMetrics(0)),
        Candidate("parent", "strategy", "broken"),
    )


def test_coordinator_enforces_budget_registers_repair() -> None:
    clock = Clock()
    budget = BudgetManager(300, clock)
    repository = CandidateRepository()
    problem, analysis, parent = values()
    repository.add(parent)
    engine = RepairEngine()
    coordinator = RepairCoordinator(engine, repository, budget, 2)  # type: ignore[arg-type]
    repaired = coordinator.repair(problem, analysis, parent, (Counterexample((), {}),))
    assert repaired is not None
    assert repository.lineage("child") == (parent, repaired)
    assert engine.timeout == budget.phase.repair_cutoff


def test_coordinator_declines_after_limit_or_cutoff() -> None:
    clock = Clock()
    budget = BudgetManager(300, clock)
    repository = CandidateRepository()
    problem, analysis, parent = values()
    repository.add(parent)
    coordinator = RepairCoordinator(RepairEngine(), repository, budget, 0)  # type: ignore[arg-type]
    assert coordinator.repair(problem, analysis, parent, (Counterexample((), {}),)) is None
    coordinator = RepairCoordinator(RepairEngine(), repository, budget, 2)  # type: ignore[arg-type]
    clock.value = budget.phase.repair_cutoff
    assert coordinator.repair(problem, analysis, parent, (Counterexample((), {}),)) is None
