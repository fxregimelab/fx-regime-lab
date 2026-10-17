"""Pure independent admission policy; no broker calls and no order authorization token.

All counts represent parent trade ideas, NOT scale-out child tickets. A caller
must reconcile and reserve atomically before sending orders. This module does
not supply broker reconciliation, readiness evidence, or persistence itself.
"""

import math
from dataclasses import dataclass
from typing import Literal

from src.paper.config import AGENT_SCORE, LIMITS


@dataclass(frozen=True)
class AdmissionState:
    equity: float  # executable mark-to-market, net of accrued costs
    day_start_equity: float  # immutable UTC-day anchor, adjusted externally for cashflows
    week_start_equity: float  # immutable Monday UTC anchor
    open_stop_risk: float  # additional loss from current marks to stops, in account currency
    pending_risk: float  # outstanding order reservations, same currency
    cost_reserve: float  # incremental spread/slippage/gap stress allowance, not double-counted
    requested_risk_pct: float
    pair_positions: int
    open_positions: int
    same_usd_positions: int
    new_trades_today: int
    demo_account: bool
    reconciled: bool
    management_ready: bool
    inputs_verified: bool
    spec_verified: bool
    strategy_graduated: bool
    cooldown_clear: bool
    candidate_eligible: bool
    grade: str
    operator_mode: Literal["full", "reduced", "paused"]


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reasons: tuple[str, ...]
    planned_risk: float


def admit(state: AdmissionState) -> Admission:
    """Never exceed either remaining loss budget just because 15% open risk is allowed.

    Planning constraint, not guaranteed loss cap: broker gaps and failed execution
    can exceed reserves. Unknown readiness must be passed as False, never assumed.
    """
    flags = (
        state.demo_account, state.reconciled, state.management_ready, state.inputs_verified,
        state.spec_verified, state.strategy_graduated, state.cooldown_clear,
        state.candidate_eligible,
    )
    if any(type(flag) is not bool for flag in flags):
        raise ValueError("Readiness flags must be verified booleans, not model text")
    anchors = (state.equity, state.day_start_equity, state.week_start_equity)
    amounts = (state.open_stop_risk, state.pending_risk, state.cost_reserve)
    if any(not math.isfinite(x) or x <= 0 for x in anchors):
        raise ValueError("Equity anchors must be positive and finite")
    if any(not math.isfinite(x) or x < 0 for x in amounts):
        raise ValueError("Risk amounts must be nonnegative and finite")
    counts = (state.pair_positions, state.open_positions,
              state.same_usd_positions, state.new_trades_today)
    if any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("Position/trade counts must be nonnegative integers")
    if not math.isfinite(state.requested_risk_pct) or not 0 < state.requested_risk_pct <= 1:
        raise ValueError("Requested risk must be a positive finite fraction")
    if state.operator_mode not in ("full", "reduced", "paused"):
        raise ValueError("Unknown operator mode")

    reasons = [name for name, ready in (
        ("demo_only", state.demo_account), ("reconciliation", state.reconciled),
        ("management_not_ready", state.management_ready),
        ("unverified_inputs", state.inputs_verified), ("unverified_spec", state.spec_verified),
        ("strategy_not_graduated", state.strategy_graduated),
        ("cooldown", state.cooldown_clear), ("candidate_rejected", state.candidate_eligible),
    ) if not ready]
    if state.open_positions >= LIMITS.max_concurrent_positions:
        reasons.append("position_cap")
    if state.pair_positions >= LIMITS.max_positions_per_pair:
        reasons.append("pair_cap")
    if state.same_usd_positions >= LIMITS.max_same_usd_sign_tickets:
        reasons.append("usd_exposure_cap")
    if state.new_trades_today >= LIMITS.max_new_trades_per_day:
        reasons.append("daily_trade_cap")
    if state.operator_mode == "paused":
        reasons.append("operator_paused")
    multiplier = LIMITS.grade_multipliers.get(state.grade)
    reduced = state.operator_mode == "reduced"
    if multiplier is None or (reduced and state.grade not in AGENT_SCORE.reduced_mode_grades):
        reasons.append("operator_grade")
    elif state.open_positions < len(LIMITS.slot_risk_ceilings):
        ceiling = LIMITS.slot_risk_ceilings[state.open_positions] * multiplier
        ceiling *= AGENT_SCORE.reduced_mode_slot_mult if reduced else 1.0
        if state.requested_risk_pct > ceiling + 1e-12:
            reasons.append("slot_risk_cap")
    if state.requested_risk_pct < LIMITS.min_effective_risk_pct:
        reasons.append("risk_floor")

    planned = state.equity * state.requested_risk_pct
    remaining_risk = state.open_stop_risk + state.pending_risk + planned + state.cost_reserve
    if remaining_risk > state.equity * LIMITS.max_open_risk_pct:
        reasons.append("open_risk_cap")
    for label, anchor, stop in (
        ("daily", state.day_start_equity, LIMITS.daily_stop_pct),
        ("weekly", state.week_start_equity, LIMITS.weekly_stop_pct),
    ):
        loss = max(0.0, anchor - state.equity)
        if loss + remaining_risk > anchor * stop:
            reasons.append(label + "_loss_capacity")
    return Admission(not reasons, tuple(reasons), planned)
