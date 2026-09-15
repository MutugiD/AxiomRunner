"""Public API for AxiomRunner."""

from axiomrunner.budget import BudgetManager
from axiomrunner.domain import ChallengeProblem, SolveOptions, SolveResult, SolveStatus
from axiomrunner.ingest import load_problem, parse_problem
from axiomrunner.ollama import OllamaClient
from axiomrunner.reasoning import ProblemAnalysis, ReasoningEngine, Strategy, TestDesign
from axiomrunner.solver import solve

__all__ = [
    "BudgetManager",
    "ChallengeProblem",
    "OllamaClient",
    "ProblemAnalysis",
    "ReasoningEngine",
    "SolveOptions",
    "SolveResult",
    "SolveStatus",
    "Strategy",
    "TestDesign",
    "load_problem",
    "parse_problem",
    "solve",
]
