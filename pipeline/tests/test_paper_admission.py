"""Independent pre-order loss capacity and operational-readiness gates."""

import json
from dataclasses import replace

import pytest

from src.paper.admission import AdmissionState, admit


def ready() -> AdmissionState:
    return AdmissionState(
        equity=10000, day_start_equity=10000, week_start_equity=10000,
        open_stop_risk=0, pending_risk=0, cost_reserve=10,
        requested_risk_pct=0.05, pair_positions=0, open_positions=0,
        same_usd_positions=0, new_trades_today=0,
        demo_account=True, reconciled=True, management_ready=True,
        inputs_verified=True, spec_verified=True, strategy_graduated=True,
        cooldown_clear=True, candidate_eligible=True,
        grade="A+", operator_mode="full",
    )


def test_unattended_execution_defaults_to_blocked() -> None:
    assert not admit(replace(ready(), management_ready=False)).allowed


def test_existing_risk_cannot_spend_remaining_daily_capacity_twice() -> None:
    state = replace(ready(), open_stop_risk=600)
    result = admit(state)
    assert not result.allowed
    assert "daily_loss_capacity" in result.reasons


def test_drawdown_reduces_capacity_using_start_of_day_equity() -> None:
    state = replace(ready(), equity=9400)
    assert not admit(state).allowed  # 600 lost + 470 planned + costs > 1000.


def test_pending_orders_reserve_risk() -> None:
    assert not admit(replace(ready(), pending_risk=600)).allowed


def test_weekly_stop_and_live_account_are_hard_blocks() -> None:
    assert not admit(replace(ready(), equity=7400)).allowed
    assert not admit(replace(ready(), demo_account=False)).allowed


def test_pair_and_currency_caps_are_not_grade_discounts() -> None:
    assert not admit(replace(ready(), pair_positions=2)).allowed
    assert not admit(replace(ready(), same_usd_positions=2)).allowed


def test_ready_state_can_pass_without_changing_limits() -> None:
    result = admit(ready())
    assert result.allowed
    assert result.planned_risk == 500


def test_reduced_operator_cannot_submit_b_grade_or_full_size() -> None:
    assert not admit(replace(ready(), operator_mode="reduced", grade="B")).allowed
    assert not admit(replace(ready(), operator_mode="reduced")).allowed
    assert admit(replace(ready(), operator_mode="reduced", requested_risk_pct=0.0375)).allowed


@pytest.mark.parametrize("amount", [-1.0, float("nan"), float("inf")])
def test_corrupt_risk_rejected(amount: float) -> None:
    with pytest.raises(ValueError):
        admit(replace(ready(), open_stop_risk=amount))


def test_string_false_cannot_impersonate_demo_verification() -> None:
    with pytest.raises(ValueError):
        admit(replace(ready(), **json.loads('{"demo_account":"false"}')))
