from axiomrunner.adversarial import Counterexample
from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    Evidence,
    ModelMetrics,
    SolveOptions,
    SolveStatus,
    VerificationCase,
    VerificationKind,
    VerificationSuite,
)
from axiomrunner.errors import ModelProtocolError, RuntimeUnavailableError
from axiomrunner.reasoning import PlanningBundle, ProblemAnalysis, Strategy
from axiomrunner.reasoning import TestDesign as Design
from axiomrunner.solver import SolveOrchestrator, _public_counterexamples, solve


class Clock:
    value = 0.0

    def __call__(self) -> float:
        return self.value


def problem(examples: tuple[object, ...] = ()) -> ChallengeProblem:
    return ChallengeProblem("one", "python", "Return x.", "answer", examples, 300)  # type: ignore[arg-type]


class Engine:
    def __init__(self, sources: dict[str, str] | None = None) -> None:
        self.sources = sources or {"first": "def answer(x):\n    return x\n"}
        self.repairs: list[tuple[Counterexample, ...]] = []

    def analyze(self, problem: ChallengeProblem, timeout_s: float) -> ProblemAnalysis:
        del problem
        assert timeout_s > 0
        return ProblemAnalysis("summary", (), (), (), (), "O(1)", (), ModelMetrics(0))

    def plan(
        self, problem: ChallengeProblem, strategy_limit: int, timeout_s: float
    ) -> PlanningBundle:
        analysis = self.analyze(problem, timeout_s)
        design = self.design_tests(problem, timeout_s)
        suite = self.verification_suite(problem, design, timeout_s)
        strategies = self.strategies(problem, analysis, strategy_limit, timeout_s)
        return PlanningBundle(analysis, suite, strategies)

    def design_tests(self, problem: ChallengeProblem, timeout_s: float) -> Design:
        del problem, timeout_s
        return Design(("zero",), (), (), "direct", ModelMetrics(0))

    def verification_suite(
        self, problem: ChallengeProblem, design: Design, timeout_s: float
    ) -> VerificationSuite:
        del problem, design, timeout_s
        return VerificationSuite(
            (VerificationCase("zero", VerificationKind.BOUNDARY, CallSpec((8,)), 8),)
        )

    def strategies(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        limit: int,
        timeout_s: float,
    ) -> tuple[Strategy, ...]:
        del problem, analysis, timeout_s
        return tuple(
            Strategy(name, name, name, "O(1)", "O(1)", ()) for name in tuple(self.sources)[:limit]
        )

    def generate(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        strategy: Strategy,
        timeout_s: float,
    ) -> Candidate:
        del problem, analysis, timeout_s
        return Candidate(
            strategy.strategy_id, strategy.strategy_id, self.sources[strategy.strategy_id]
        )

    def repair(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        parent: Candidate,
        counterexamples: tuple[Counterexample, ...],
        timeout_s: float,
        failures: tuple[str, ...] = (),
    ) -> Candidate:
        del problem, analysis, timeout_s, failures
        self.repairs.append(counterexamples)
        return Candidate(
            f"{parent.candidate_id}-fixed",
            parent.strategy_id,
            "def answer(x):\n    return x\n",
            revision=parent.revision + 1,
            parent_id=parent.candidate_id,
        )


class BaseVerifier:
    def verify(self, candidate: Candidate, problem: ChallengeProblem) -> Evidence:
        del problem
        return Evidence(
            candidate.candidate_id,
            (
                CheckResult("syntax", "static", CheckStatus.PASSED, 0.01),
                CheckResult("sandbox", "docker", CheckStatus.PASSED, 0.01),
            ),
        )


class Adversarial:
    def __init__(self, failing: set[str] | None = None, *, independent: bool = True) -> None:
        self.failing = failing or set()
        self.independent = independent

    def verify(
        self, candidate: Candidate, problem: ChallengeProblem, suite: VerificationSuite
    ) -> tuple[CheckResult, ...]:
        del problem
        if not self.independent:
            return (
                CheckResult(
                    "oracle_policy", "independent", CheckStatus.INCONCLUSIVE, 0, mandatory=False
                ),
            )
        failed = candidate.candidate_id in self.failing
        case = suite.cases[0]
        return (
            CheckResult(
                case.kind.value,
                f"independent:{case.case_id}",
                CheckStatus.FAILED if failed else CheckStatus.PASSED,
                0.01,
                details={
                    "case_id": case.case_id,
                    "counterexample": {
                        "args": list(case.call.args),
                        "kwargs": case.call.kwargs,
                    },
                },
            ),
        )


class Static:
    def __init__(self, status: CheckStatus = CheckStatus.PASSED) -> None:
        self.status = status

    def verify(self, candidate: Candidate, entrypoint: str) -> tuple[CheckResult, ...]:
        del candidate, entrypoint
        return (CheckResult("final_static", "static", self.status, 0.01),)


def orchestrator(
    engine: Engine,
    adversarial: Adversarial,
    *,
    static: Static | None = None,
    clock: Clock | None = None,
) -> SolveOrchestrator:
    return SolveOrchestrator(
        engine,  # type: ignore[arg-type]
        BaseVerifier(),  # type: ignore[arg-type]
        adversarial,  # type: ignore[arg-type]
        static or Static(),  # type: ignore[arg-type]
        clock=clock or Clock(),
        run_id_factory=lambda: "run-1",
    )


def test_selects_best_viable_candidate_after_multiple_strategies() -> None:
    engine = Engine(
        {
            "first": "def answer(x):\n    return 0\n",
            "second": "def answer(x):\n    return x\n",
        }
    )
    result = orchestrator(engine, Adversarial({"first"})).solve(
        problem(), SolveOptions(candidate_limit=2, repair_limit=0)
    )
    assert result.status is SolveStatus.SUCCESS
    assert result.selected_candidate_id == "second"
    assert len(result.candidates) == 2
    assert result.run_id == "run-1"


def test_repairs_from_minimized_counterexample_and_preserves_lineage() -> None:
    engine = Engine()
    result = orchestrator(engine, Adversarial({"first"})).solve(
        problem(), SolveOptions(candidate_limit=1, repair_limit=1)
    )
    assert result.status is SolveStatus.SUCCESS
    assert result.selected_candidate_id == "first-fixed"
    assert result.candidates[1].parent_id == "first"
    assert engine.repairs == [(Counterexample((0,), {}),)]


def test_final_static_recheck_can_reject_otherwise_viable_candidate() -> None:
    result = orchestrator(Engine(), Adversarial(), static=Static(CheckStatus.FAILED)).solve(
        problem(), SolveOptions(candidate_limit=1, repair_limit=0)
    )
    assert result.status is SolveStatus.NO_VIABLE_CANDIDATE


def test_candidate_without_independent_pass_is_not_selectable() -> None:
    result = orchestrator(Engine(), Adversarial(independent=False)).solve(
        problem(), SolveOptions(candidate_limit=1, repair_limit=0)
    )
    assert result.status is SolveStatus.NO_VIABLE_CANDIDATE


class ProtocolFailureEngine(Engine):
    calls = 0

    def analyze(self, problem: ChallengeProblem, timeout_s: float) -> ProblemAnalysis:
        del problem, timeout_s
        self.calls += 1
        raise ModelProtocolError("bad model reply")


class RuntimeFailureEngine(Engine):
    def analyze(self, problem: ChallengeProblem, timeout_s: float) -> ProblemAnalysis:
        del problem, timeout_s
        raise RuntimeUnavailableError("offline")


def test_model_protocol_failure_retries_once_then_returns_runtime_status() -> None:
    engine = ProtocolFailureEngine()
    result = orchestrator(engine, Adversarial()).solve(problem(), SolveOptions())
    assert result.status is SolveStatus.RUNTIME_UNAVAILABLE
    assert engine.calls == 2


def test_runtime_failure_returns_partial_auditable_result() -> None:
    result = orchestrator(RuntimeFailureEngine(), Adversarial()).solve(problem(), SolveOptions())
    assert result.status is SolveStatus.RUNTIME_UNAVAILABLE
    assert result.run_id == "run-1"


class CutoffEngine(Engine):
    def __init__(self, clock: Clock) -> None:
        super().__init__()
        self.clock = clock

    def strategies(
        self,
        problem: ChallengeProblem,
        analysis: ProblemAnalysis,
        limit: int,
        timeout_s: float,
    ) -> tuple[Strategy, ...]:
        result = super().strategies(problem, analysis, limit, timeout_s)
        self.clock.value = 229
        return result


def test_candidate_cutoff_prevents_new_generation() -> None:
    clock = Clock()
    result = orchestrator(CutoffEngine(clock), Adversarial(), clock=clock).solve(
        problem(), SolveOptions()
    )
    assert result.status is SolveStatus.NO_VIABLE_CANDIDATE
    assert result.cutoffs == ("candidate",)


def test_public_example_failures_become_repair_counterexamples() -> None:
    challenge = problem(({"args": [4], "kwargs": {"flag": True}, "expected": 4},))
    evidence = Evidence(
        "candidate",
        (
            CheckResult(
                "sandbox",
                "docker",
                CheckStatus.FAILED,
                0,
                details={"failures": [{"index": 0}, {"index": 99}, {"bad": "shape"}]},
            ),
        ),
    )
    assert _public_counterexamples(challenge, evidence) == (Counterexample((4,), {"flag": True}),)


def test_public_solve_rejects_non_loopback_runtime_configuration() -> None:
    result = solve(problem(), SolveOptions(ollama_host="https://example.com"))
    assert result.status is SolveStatus.RUNTIME_UNAVAILABLE
    assert result.run_id is not None
