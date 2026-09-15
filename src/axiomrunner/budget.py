"""Monotonic deadline allocation and phase guards."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class PhaseBudget:
    started_at: float
    overall_deadline: float
    candidate_cutoff: float
    repair_cutoff: float
    finalization_at: float
    reserve_s: float


class BudgetManager:
    """Own absolute monotonic cutoffs for one solve."""

    def __init__(self, deadline_s: float, clock: Clock = time.monotonic) -> None:
        if deadline_s <= 10.0:
            raise ValueError("deadline must exceed the finalization reserve")
        self._clock = clock
        start = clock()
        reserve = min(20.0, max(10.0, 0.05 * deadline_s))
        usable = deadline_s - reserve
        self.phase = PhaseBudget(
            started_at=start,
            overall_deadline=start + deadline_s,
            candidate_cutoff=start + 0.80 * usable,
            repair_cutoff=start + 0.90 * usable,
            finalization_at=start + usable,
            reserve_s=reserve,
        )

    def elapsed(self) -> float:
        return max(0.0, self._clock() - self.phase.started_at)

    def remaining(self) -> float:
        return max(0.0, self.phase.overall_deadline - self._clock())

    def request_timeout(self, phase_deadline: float) -> float:
        return max(0.0, min(phase_deadline, self.phase.finalization_at) - self._clock())

    def can_start_candidate(self) -> bool:
        return self._clock() < self.phase.candidate_cutoff

    def can_start_repair(self) -> bool:
        return self._clock() < self.phase.repair_cutoff

    def must_finalize(self) -> bool:
        return self._clock() >= self.phase.finalization_at

    def expired(self) -> bool:
        return self._clock() >= self.phase.overall_deadline
