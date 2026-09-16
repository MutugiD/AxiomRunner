"""Public API for AxiomRunner."""

from axiomrunner.adversarial import (
    AdversarialVerifier,
    Counterexample,
    EvidenceScore,
    counterexamples_from_evidence,
    minimize_counterexample,
    rank_candidates,
    score_evidence,
)
from axiomrunner.budget import BudgetManager
from axiomrunner.candidates import CandidateRepository
from axiomrunner.domain import (
    CallSpec,
    ChallengeProblem,
    Comparison,
    SolveOptions,
    SolveResult,
    SolveStatus,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)
from axiomrunner.ingest import load_problem, parse_problem
from axiomrunner.ollama import OllamaClient
from axiomrunner.reasoning import (
    PlanningBundle,
    ProblemAnalysis,
    ReasoningEngine,
    Strategy,
    TestDesign,
)
from axiomrunner.repair import RepairCoordinator
from axiomrunner.sandbox import DockerSandbox
from axiomrunner.solver import solve
from axiomrunner.static_validation import StaticVerifier
from axiomrunner.verification import CandidateVerifier

__all__ = [
    "AdversarialVerifier",
    "BudgetManager",
    "CallSpec",
    "CandidateRepository",
    "CandidateVerifier",
    "ChallengeProblem",
    "Comparison",
    "Counterexample",
    "DockerSandbox",
    "EvidenceScore",
    "OllamaClient",
    "PlanningBundle",
    "ProblemAnalysis",
    "ReasoningEngine",
    "RepairCoordinator",
    "SolveOptions",
    "SolveResult",
    "SolveStatus",
    "StaticVerifier",
    "Strategy",
    "TestDesign",
    "VerificationCase",
    "VerificationKind",
    "VerificationSuite",
    "counterexamples_from_evidence",
    "load_problem",
    "minimize_counterexample",
    "parse_problem",
    "rank_candidates",
    "score_evidence",
    "solve",
]
