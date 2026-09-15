"""In-memory candidate lineage and append-only evidence storage."""

from __future__ import annotations

from axiomrunner.domain import Candidate, CheckResult, Evidence


class CandidateRepository:
    def __init__(self) -> None:
        self._candidates: dict[str, Candidate] = {}
        self._checks: dict[str, list[CheckResult]] = {}
        self._order: list[str] = []

    def add(self, candidate: Candidate) -> None:
        if candidate.candidate_id in self._candidates:
            raise ValueError(f"duplicate candidate: {candidate.candidate_id}")
        if candidate.parent_id is not None:
            parent = self._candidates.get(candidate.parent_id)
            if parent is None:
                raise ValueError(f"unknown parent candidate: {candidate.parent_id}")
            if candidate.revision != parent.revision + 1:
                raise ValueError("repair revision must immediately follow its parent")
            if candidate.strategy_id != parent.strategy_id:
                raise ValueError("repair must preserve its parent's strategy")
        elif candidate.revision != 0:
            raise ValueError("root candidate revision must be zero")
        self._candidates[candidate.candidate_id] = candidate
        self._checks[candidate.candidate_id] = []
        self._order.append(candidate.candidate_id)

    def append(self, candidate_id: str, checks: tuple[CheckResult, ...]) -> Evidence:
        if candidate_id not in self._candidates:
            raise KeyError(candidate_id)
        self._checks[candidate_id].extend(checks)
        return self.evidence(candidate_id)

    def get(self, candidate_id: str) -> Candidate:
        return self._candidates[candidate_id]

    def evidence(self, candidate_id: str) -> Evidence:
        return Evidence(candidate_id, tuple(self._checks[candidate_id]))

    def lineage(self, candidate_id: str) -> tuple[Candidate, ...]:
        lineage: list[Candidate] = []
        current = self.get(candidate_id)
        while True:
            lineage.append(current)
            if current.parent_id is None:
                break
            current = self.get(current.parent_id)
        return tuple(reversed(lineage))

    def provenance(self, candidate_id: str) -> tuple[Evidence, ...]:
        return tuple(
            self.evidence(candidate.candidate_id) for candidate in self.lineage(candidate_id)
        )

    def candidates(self) -> tuple[Candidate, ...]:
        return tuple(self._candidates[candidate_id] for candidate_id in self._order)
