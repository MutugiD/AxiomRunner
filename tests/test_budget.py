import pytest

from axiomrunner.budget import BudgetManager


class FakeClock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_budget_uses_absolute_monotonic_cutoffs() -> None:
    clock = FakeClock()
    budget = BudgetManager(300.0, clock)
    assert budget.phase.reserve_s == 15.0
    assert budget.phase.finalization_at == 385.0
    assert budget.can_start_candidate()
    clock.value = budget.phase.candidate_cutoff
    assert not budget.can_start_candidate()
    assert budget.can_start_repair()
    clock.value = budget.phase.repair_cutoff
    assert not budget.can_start_repair()
    clock.value = budget.phase.finalization_at
    assert budget.must_finalize()
    assert not budget.expired()
    clock.value = budget.phase.overall_deadline
    assert budget.expired()
    assert budget.remaining() == 0.0


def test_short_deadline_uses_ten_second_reserve() -> None:
    clock = FakeClock(0.0)
    budget = BudgetManager(20.0, clock)
    assert budget.phase.reserve_s == 10.0
    clock.value = 2.5
    assert budget.elapsed() == 2.5


def test_long_deadline_caps_reserve() -> None:
    budget = BudgetManager(1000.0, FakeClock(0.0))
    assert budget.phase.reserve_s == 20.0


def test_timeout_never_crosses_finalization() -> None:
    clock = FakeClock(5.0)
    budget = BudgetManager(100.0, clock)
    assert budget.request_timeout(budget.phase.overall_deadline) == 90.0
    clock.value = 200.0
    assert budget.request_timeout(budget.phase.repair_cutoff) == 0.0


def test_impossible_deadline_is_rejected() -> None:
    with pytest.raises(ValueError):
        BudgetManager(10.0)
