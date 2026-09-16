"""Deadline-aware end-to-end solve orchestration."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from axiomrunner.adversarial import (
    AdversarialVerifier,
    Counterexample,
    counterexamples_from_evidence,
    minimize_counterexample,
    rank_candidates,
)
from axiomrunner.budget import BudgetManager, Clock
from axiomrunner.candidates import CandidateRepository
from axiomrunner.domain import (
    CallSpec,
    Candidate,
    ChallengeProblem,
    CheckResult,
    CheckStatus,
    Evidence,
    SolveOptions,
    SolveResult,
    SolveStatus,
    VerificationCase,
    VerificationSuite,
)
from axiomrunner.errors import ModelProtocolError, RuntimeUnavailableError
from axiomrunner.ollama import OllamaClient
from axiomrunner.reasoning import ReasoningEngine, Strategy
from axiomrunner.repair import RepairCoordinator
from axiomrunner.sandbox import DockerSandbox
from axiomrunner.static_validation import StaticVerifier, extract_source
from axiomrunner.verification import CandidateVerifier

T = TypeVar("T")
RunIdFactory = Callable[[], str]


class _ModelPhaseDeadline(RuntimeError):
    pass


class SolveOrchestrator:
    """Coordinate model roles and observed verification under one budget."""

    def __init__(
        self,
        engine: ReasoningEngine,
        verifier: CandidateVerifier,
        adversarial: AdversarialVerifier,
        static: StaticVerifier,
        *,
        clock: Clock = time.monotonic,
        run_id_factory: RunIdFactory = lambda: uuid.uuid4().hex,
    ) -> None:
        self.engine = engine
        self.verifier = verifier
        self.adversarial = adversarial
        self.static = static
        self.clock = clock
        self.run_id_factory = run_id_factory

    def solve(self, problem: ChallengeProblem, options: SolveOptions) -> SolveResult:
        budget = BudgetManager(problem.deadline_s, self.clock)
        repository = CandidateRepository()
        cutoffs: list[str] = []
        run_id = self.run_id_factory()
        try:
            planning = self._model_call(
                lambda timeout: self.engine.plan(problem, options.candidate_limit, timeout),
                budget,
            )
            analysis = planning.analysis
            suite = planning.verification_suite
            strategies = planning.strategies
            repair = RepairCoordinator(self.engine, repository, budget, options.repair_limit)
            for strategy in strategies[: options.candidate_limit]:
                if not budget.can_start_candidate():
                    _record_cutoff(cutoffs, "candidate")
                    break

                def generate(timeout: float, selected: Strategy = strategy) -> Candidate:
                    return self.engine.generate(problem, analysis, selected, timeout)

                candidate = self._model_call(generate, budget)
                repository.add(candidate)
                self._verify_candidate(candidate, problem, suite, repository, budget)
                current = candidate
                while not repository.evidence(current.candidate_id).viable:
                    if not budget.can_start_repair():
                        _record_cutoff(cutoffs, "repair")
                        break
                    evidence = repository.evidence(current.candidate_id)
                    counterexamples = self._counterexamples(
                        current, problem, suite, evidence, budget
                    )
                    failures = _failure_summaries(evidence)
                    if not counterexamples and not failures:
                        break
                    repaired = repair.repair(
                        problem,
                        analysis,
                        current,
                        counterexamples,
                        failures,
                    )
                    if repaired is None:
                        if not budget.can_start_repair():
                            _record_cutoff(cutoffs, "repair")
                        break
                    current = repaired
                    self._verify_candidate(current, problem, suite, repository, budget)
        except _ModelPhaseDeadline as error:
            _record_cutoff(cutoffs, "candidate")
            return self._result(
                SolveStatus.NO_VIABLE_CANDIDATE,
                budget,
                repository,
                run_id,
                cutoffs,
                error=str(error),
            )
        except (RuntimeUnavailableError, ModelProtocolError) as error:
            return self._result(
                SolveStatus.RUNTIME_UNAVAILABLE,
                budget,
                repository,
                run_id,
                cutoffs,
                error=str(error),
            )

        viable = tuple(
            (candidate, repository.evidence(candidate.candidate_id), False)
            for candidate in repository.candidates()
            if _selection_viable(repository.evidence(candidate.candidate_id))
        )
        for candidate in rank_candidates(viable):
            final_checks = self.static.verify(candidate, problem.entrypoint)
            final_evidence = repository.append(candidate.candidate_id, final_checks)
            if final_evidence.viable:
                return self._result(
                    SolveStatus.SUCCESS,
                    budget,
                    repository,
                    run_id,
                    cutoffs,
                    solution_source=extract_source(candidate.source),
                    selected_candidate_id=candidate.candidate_id,
                )
        if budget.must_finalize():
            _record_cutoff(cutoffs, "finalization")
        return self._result(
            SolveStatus.NO_VIABLE_CANDIDATE,
            budget,
            repository,
            run_id,
            cutoffs,
            error="no candidate passed every mandatory verification gate",
        )

    def _model_call(
        self,
        operation: Callable[[float], T],
        budget: BudgetManager,
    ) -> T:
        last_error: ModelProtocolError | None = None
        for _ in range(2):
            timeout = budget.request_timeout(budget.phase.candidate_cutoff)
            if timeout <= 0:
                raise _ModelPhaseDeadline("model phase deadline exhausted")
            try:
                return operation(timeout)
            except ModelProtocolError as error:
                last_error = error
        assert last_error is not None
        raise last_error

    def _verify_candidate(
        self,
        candidate: Candidate,
        problem: ChallengeProblem,
        suite: VerificationSuite,
        repository: CandidateRepository,
        budget: BudgetManager,
    ) -> Evidence:
        base = self.verifier.verify(candidate, problem)
        evidence = repository.append(candidate.candidate_id, base.checks)
        if not evidence.viable:
            return evidence
        if budget.must_finalize():
            return repository.append(
                candidate.candidate_id,
                (
                    CheckResult(
                        "deadline",
                        "orchestrator",
                        CheckStatus.INCONCLUSIVE,
                        0.0,
                        details={"error": "finalization cutoff reached before adversarial checks"},
                    ),
                ),
            )
        checks = self.adversarial.verify(candidate, problem, suite)
        return repository.append(candidate.candidate_id, checks)

    def _counterexamples(
        self,
        candidate: Candidate,
        problem: ChallengeProblem,
        suite: VerificationSuite,
        evidence: Evidence,
        budget: BudgetManager,
    ) -> tuple[Counterexample, ...]:
        observed = list(counterexamples_from_evidence(evidence))
        observed.extend(_public_counterexamples(problem, evidence))
        minimized: list[Counterexample] = []
        for counterexample in observed:
            case = _matching_case(suite, evidence, counterexample)
            if case is None or not budget.can_start_repair():
                minimized.append(counterexample)
                continue

            def still_fails(trial: Counterexample, selected_case: VerificationCase = case) -> bool:
                if not budget.can_start_repair():
                    return False
                trial_case = replace(selected_case, call=CallSpec(trial.args, trial.kwargs))
                trial_suite = VerificationSuite(
                    (trial_case,), suite.oracle_source, suite.oracle_entrypoint
                )
                checks = self.adversarial.verify(candidate, problem, trial_suite)
                return any(check.status is CheckStatus.FAILED for check in checks)

            minimized.append(
                minimize_counterexample(counterexample, still_fails, max_evaluations=8)
            )
        return tuple(_deduplicate(minimized))

    @staticmethod
    def _result(
        status: SolveStatus,
        budget: BudgetManager,
        repository: CandidateRepository,
        run_id: str,
        cutoffs: list[str],
        *,
        solution_source: str | None = None,
        selected_candidate_id: str | None = None,
        error: str | None = None,
    ) -> SolveResult:
        candidates = repository.candidates()
        return SolveResult(
            status=status,
            elapsed_s=budget.elapsed(),
            solution_source=solution_source,
            selected_candidate_id=selected_candidate_id,
            evidence=tuple(repository.evidence(item.candidate_id) for item in candidates),
            error=error,
            cutoffs=tuple(cutoffs),
            candidates=candidates,
            run_id=run_id,
        )


def solve(problem: ChallengeProblem, options: SolveOptions | None = None) -> SolveResult:
    """Solve one validated Python challenge using local Ollama and Docker."""
    selected = options or SolveOptions()
    static = StaticVerifier()
    sandbox = DockerSandbox(selected.sandbox)
    try:
        client = OllamaClient(selected.ollama_host, selected.model, seed=selected.seed)
    except ValueError as error:
        return SolveResult(
            SolveStatus.RUNTIME_UNAVAILABLE,
            0.0,
            error=str(error),
            run_id=uuid.uuid4().hex,
        )
    engine = ReasoningEngine(client)
    orchestrator = SolveOrchestrator(
        engine,
        CandidateVerifier(static, sandbox),
        AdversarialVerifier(static, sandbox),
        static,
    )
    return orchestrator.solve(problem, selected)


def _failure_summaries(evidence: Evidence) -> tuple[str, ...]:
    summaries: list[str] = []
    for check in evidence.checks:
        if check.status is not CheckStatus.FAILED:
            continue
        detail = json.dumps(check.details, ensure_ascii=False, sort_keys=True)
        summaries.append(f"{check.check_type} from {check.origin}: {detail[:1000]}")
    return tuple(summaries)


def _public_counterexamples(
    problem: ChallengeProblem, evidence: Evidence
) -> tuple[Counterexample, ...]:
    result: list[Counterexample] = []
    for check in evidence.checks:
        if check.check_type != "sandbox" or check.status is not CheckStatus.FAILED:
            continue
        failures = check.details.get("failures")
        if not isinstance(failures, list):
            continue
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            raw_index = failure.get("index")
            if (
                isinstance(raw_index, bool)
                or not isinstance(raw_index, int)
                or not 0 <= raw_index < len(problem.public_examples)
            ):
                continue
            index = raw_index
            example = problem.public_examples[index]
            if not isinstance(example, dict):
                continue
            args = example.get("args", [])
            kwargs = example.get("kwargs", {})
            if isinstance(args, list) and isinstance(kwargs, dict):
                result.append(Counterexample(tuple(args), kwargs))
    return tuple(result)


def _matching_case(
    suite: VerificationSuite,
    evidence: Evidence,
    counterexample: Counterexample,
) -> VerificationCase | None:
    for check in evidence.checks:
        if check.status is not CheckStatus.FAILED:
            continue
        raw = check.details.get("counterexample")
        if not isinstance(raw, dict):
            continue
        if (
            raw.get("args") != list(counterexample.args)
            or raw.get("kwargs") != counterexample.kwargs
        ):
            continue
        case_id = check.details.get("case_id")
        return next((case for case in suite.cases if case.case_id == case_id), None)
    return None


def _deduplicate(values: list[Counterexample]) -> list[Counterexample]:
    unique: list[Counterexample] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _record_cutoff(cutoffs: list[str], name: str) -> None:
    if name not in cutoffs:
        cutoffs.append(name)


def _selection_viable(evidence: Evidence) -> bool:
    independent = {"boundary", "oracle", "property", "metamorphic"}
    return evidence.viable and any(
        check.check_type in independent and check.status is CheckStatus.PASSED
        for check in evidence.checks
    )
