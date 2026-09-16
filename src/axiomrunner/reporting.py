"""Redacted, machine-readable solve evidence reports."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from axiomrunner.adversarial import score_evidence
from axiomrunner.domain import ChallengeProblem, Evidence, SolveOptions, SolveResult, to_json_value
from axiomrunner.output import atomic_write_text

REPORT_SCHEMA_VERSION = 1


def report_document(
    problem: ChallengeProblem,
    options: SolveOptions,
    result: SolveResult,
) -> dict[str, object]:
    evidence_by_id = {item.candidate_id: item for item in result.evidence}
    candidates = []
    for candidate in result.candidates:
        evidence = evidence_by_id.get(candidate.candidate_id, Evidence(candidate.candidate_id))
        candidates.append(
            {
                "candidate_id": candidate.candidate_id,
                "strategy_id": candidate.strategy_id,
                "parent_id": candidate.parent_id,
                "revision": candidate.revision,
                "model_metrics": None
                if candidate.metrics is None
                else {
                    "duration_s": candidate.metrics.duration_s,
                    "prompt_tokens": candidate.metrics.prompt_tokens,
                    "response_tokens": candidate.metrics.response_tokens,
                },
                "score": to_json_value(asdict(score_evidence(evidence))),
                "viable": evidence.viable,
                "checks": [
                    {
                        "check_type": check.check_type,
                        "origin": check.origin,
                        "status": check.status.value,
                        "duration_s": check.duration_s,
                        "mandatory": check.mandatory,
                        "details": check.details,
                    }
                    for check in evidence.checks
                ],
            }
        )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "run_id": result.run_id,
        "problem_id": problem.problem_id,
        "status": result.status.value,
        "elapsed_s": result.elapsed_s,
        "error": result.error,
        "selected_candidate_id": result.selected_candidate_id,
        "cutoffs": list(result.cutoffs),
        "options": {
            "model": options.model,
            "seed": options.seed,
            "candidate_limit": options.candidate_limit,
            "repair_limit": options.repair_limit,
            "sandbox": {
                "memory_mb": options.sandbox.memory_mb,
                "cpus": options.sandbox.cpus,
                "processes": options.sandbox.processes,
                "timeout_s": options.sandbox.timeout_s,
            },
        },
        "candidates": candidates,
    }


def write_report(
    path: str | Path,
    problem: ChallengeProblem,
    options: SolveOptions,
    result: SolveResult,
) -> None:
    document = report_document(problem, options, result)
    atomic_write_text(path, json.dumps(document, indent=2, sort_keys=True) + "\n")
