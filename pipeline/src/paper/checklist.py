"""Binary checklist engine — the desk's confidence gate (playbook §2, framework §6).

Pure evaluation: every input is explicit (bars, pipeline fields, session flags,
exposure state). The engine never talks to the broker. It encodes declared rules from
``docs/DESK_TRADING_PLAYBOOK.md`` §2/§4, ``docs/DESK_STRATEGY_FRAMEWORK.md``
and ``pipeline/src/paper/config.py`` (grade multipliers, slot ceilings, costs) —
and stamps ``FRAMEWORK_VERSION`` / ``PLAYBOOK_VERSION`` into every evaluation.
It does not read those documents at runtime; versions alone do not prove spec compliance.

Grade → risk: ``risk = slot_ceiling(open_tickets) × grade_multiplier``, blocked
below ``min_effective_risk_pct`` and above the 15% open-risk cap. The
operator-score envelope is applied by the session runner via ``slot_mult``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from src.paper.config import (
    COSTS,
    FRAMEWORK_VERSION,
    LIMITS,
    PLAYBOOK_VERSION,
    TRADING_PAIRS,
    TradingLimits,
)
from src.paper.levels import (
    Level,
    build_liquidity_map,
    find_swings,
    nearest_level,
    significant_only,
)
from src.paper.store import Bar

Direction = Literal["long", "short"]

GRADE_C = "C"


# --- indicator helpers (pure) ---------------------------------------------------


def atr(bars: Sequence[Bar], n: int = 14) -> float | None:
    """Average true range over the last ``n`` bars; None when insufficient."""
    if n < 1:
        raise ValueError("ATR period must be positive")
    if len(bars) < n + 1:
        return None
    true_ranges: list[float] = []
    for prev, cur in zip(bars[-n - 1 : -1], bars[-n:], strict=True):
        true_ranges.append(
            max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close))
        )
    return sum(true_ranges) / n


def ema(values: Sequence[float], n: int) -> float | None:
    """Exponential moving average (seeded at the first value); None when insufficient."""
    if n < 1:
        raise ValueError("EMA period must be positive")
    if len(values) < n:
        return None
    k = 2.0 / (n + 1.0)
    out = values[0]
    for value in values[1:]:
        out = value * k + out * (1 - k)
    return out


def structure_aligned(
    bars: Sequence[Bar], direction: Direction, k: int = 2
) -> tuple[bool, str]:
    """H4-style structure: last two swing highs and lows both rising (long) / falling (short)."""
    swings = find_swings(bars, k=k)
    highs = [s.price for s in swings if s.kind == "high"][-2:]
    lows = [s.price for s in swings if s.kind == "low"][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return False, "insufficient swing structure"
    detail = f"H {highs[0]:.6g}->{highs[1]:.6g}, L {lows[0]:.6g}->{lows[1]:.6g}"
    if direction == "long":
        return (highs[1] > highs[0] and lows[1] > lows[0]), detail
    return (highs[1] < highs[0] and lows[1] < lows[0]), detail


def cost_share_of_r(pair: str, entry: float, stop: float) -> float:
    """Round-trip cost (incl. slippage allowance) as a fraction of the 1R distance."""
    r = abs(entry - stop)
    if r <= 0:
        return math.inf
    total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
    return (entry * total_bps / 10_000.0) / r


# --- evaluation types -----------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExposureState:
    """Parent-trade exposure, not scale-out child fills.

    Legacy field names ``open_tickets``/``same_usd_sign_tickets`` count risk
    groups (parent trades). Two 50/50 child orders must consume ONE group.
    No live adapter currently constructs this state automatically.
    """

    open_tickets: int = 0
    same_usd_sign_tickets: int = 0
    open_risk_pct: float = 0.0

    def validate(self) -> None:
        counts = (self.open_tickets, self.same_usd_sign_tickets)
        if any(type(n) is not int or n < 0 for n in counts):
            raise ValueError("Exposure counts must be nonnegative integers")
        if not math.isfinite(self.open_risk_pct) or self.open_risk_pct < 0:
            raise ValueError("Open risk must be finite and nonnegative")


@dataclass(frozen=True)
class CandidateContext:
    """Everything a checklist evaluation needs; all inputs explicit and receiptable."""

    pair: str
    direction: Direction
    entry: float
    stop: float
    bars_by_tf: Mapping[str, Sequence[Bar]]
    strategy_rule_fires: bool
    dqs: float
    bars_fresh: bool
    red_event_now: bool
    red_event_within_2h: bool
    event_cohort: bool
    session_ok: bool
    spread_ok: bool
    news_conflict: bool
    bias_aligned: bool
    trigger_present: bool
    exposure: ExposureState = field(default_factory=ExposureState)


@dataclass(frozen=True)
class Evaluation:
    pair: str
    direction: Direction
    gates: tuple[CheckResult, ...]
    scored: tuple[CheckResult, ...]
    score: int                      # scored checks passed (0-9)
    grade: str                      # "A+", "A", "B+", "B" or "C" (no trade)
    trade_allowed: bool
    risk_pct: float | None          # slot- and grade-scaled; None when blocked
    slot_ceiling_pct: float | None
    framework_version: str
    playbook_version: str
    notes: tuple[str, ...] = ()


def size_risk(
    grade: str,
    exposure: ExposureState,
    limits: TradingLimits = LIMITS,
    slot_mult: float = 1.0,
) -> tuple[float | None, float | None]:
    """(risk_pct, slot_ceiling_pct); (None, None) when the grade or slots block a trade.

    ``slot_mult`` carries the operator-score envelope reduction (1.0 = full envelope;
    reduced mode uses e.g. 0.75). It can only scale risk DOWN.
    """
    exposure.validate()
    if not math.isfinite(slot_mult) or not 0 <= slot_mult <= 1:
        raise ValueError("Operator multiplier must be finite and between zero and one")
    multiplier = limits.grade_multipliers.get(grade)
    if multiplier is None:
        return None, None
    slot = exposure.open_tickets
    if (
        slot >= min(len(limits.slot_risk_ceilings), limits.max_concurrent_positions)
        or exposure.same_usd_sign_tickets >= limits.max_same_usd_sign_tickets
    ):
        return None, None
    ceiling = limits.slot_risk_ceilings[slot] * slot_mult
    if not math.isfinite(ceiling) or not 0 <= ceiling <= limits.max_open_risk_pct:
        raise ValueError("Invalid slot ceiling")
    if not math.isfinite(multiplier) or not 0 <= multiplier <= 1:
        raise ValueError("Grade multiplier must not increase risk")
    risk = ceiling * multiplier
    if risk < limits.min_effective_risk_pct:
        return None, ceiling
    if exposure.open_risk_pct + risk > limits.max_open_risk_pct:
        return None, ceiling
    return risk, ceiling


# --- checks ---------------------------------------------------------------------


def _gate_checks(ctx: CandidateContext) -> tuple[CheckResult, ...]:
    share = cost_share_of_r(ctx.pair, ctx.entry, ctx.stop)
    rule_detail = "strategy rule fires" if ctx.strategy_rule_fires else "no rule-valid setup"
    h3_detail = (
        f"red_now={ctx.red_event_now}, red_2h={ctx.red_event_within_2h}, "
        f"event_cohort={ctx.event_cohort}"
    )
    return (
        CheckResult("H1", ctx.strategy_rule_fires, rule_detail),
        CheckResult(
            "H2",
            ctx.dqs >= 0.8 and ctx.bars_fresh
            and len(ctx.bars_by_tf.get("H1", [])) >= 20
            and len(ctx.bars_by_tf.get("H4", [])) >= 5,
            f"dqs={ctx.dqs:.2f}, bars_fresh={ctx.bars_fresh}",
        ),
        CheckResult(
            "H3",
            (not ctx.red_event_now) and (ctx.event_cohort or not ctx.red_event_within_2h),
            h3_detail,
        ),
        CheckResult("H4", share <= 0.10, f"cost share of R = {share:.1%} (limit 10%)"),
        CheckResult(
            "H5",
            ctx.session_ok and ctx.spread_ok,
            f"session_ok={ctx.session_ok}, spread_ok={ctx.spread_ok}",
        ),
    )


def _score_check_s6(
    ctx: CandidateContext, liquidity: Sequence[Level], atr_h1: float | None
) -> CheckResult:
    if atr_h1 is None or atr_h1 <= 0:
        return CheckResult("S6", False, "no ATR_H1 (insufficient history)")
    r = abs(ctx.entry - ctx.stop)
    reach = r + atr_h1
    side: Literal["above", "below"] = "below" if ctx.direction == "long" else "above"
    pool = nearest_level(liquidity, ctx.entry, side)
    if pool is None:
        return CheckResult("S6", True, "no significant pool on the adverse side")
    gap = abs(ctx.entry - pool.price)
    if gap > reach:
        return CheckResult(
            "S6", True, f"nearest pool {pool.price:.6g} beyond reach ({gap:.6g} > {reach:.6g})"
        )
    buffer = 0.25 * atr_h1
    if ctx.direction == "long":
        ok = ctx.stop <= pool.price - buffer
    else:
        ok = ctx.stop >= pool.price + buffer
    detail = f"pool {pool.price:.6g} vs stop {ctx.stop:.6g} (buffer {buffer:.6g})"
    return CheckResult("S6", ok, detail)


def _score_check_s7(ctx: CandidateContext, liquidity: Sequence[Level]) -> CheckResult:
    r = abs(ctx.entry - ctx.stop)
    side: Literal["above", "below"] = "above" if ctx.direction == "long" else "below"
    opposing = nearest_level(liquidity, ctx.entry, side)
    if opposing is None:
        return CheckResult("S7", True, "no significant opposing structure")
    dist = abs(opposing.price - ctx.entry)
    need = 1.25 * r
    return CheckResult(
        "S7",
        dist >= need,
        f"nearest opposing {opposing.price:.6g} at {dist:.6g} (need >= {need:.6g})",
    )


def _score_checks(
    ctx: CandidateContext, limits: TradingLimits, atr_h1: float | None
) -> tuple[CheckResult, ...]:
    h4_bars = ctx.bars_by_tf.get("H4", [])
    structure_ok, structure_detail = structure_aligned(h4_bars, ctx.direction)
    h1_bars = ctx.bars_by_tf.get("H1", [])
    ema_h1 = ema([b.close for b in h1_bars], 20)
    stop_dist = abs(ctx.entry - ctx.stop)
    liquidity = significant_only(build_liquidity_map(ctx.bars_by_tf, ctx.pair))

    if atr_h1 is None or ema_h1 is None:
        s4: CheckResult = CheckResult("S4", False, "insufficient H1 history")
        s5: CheckResult = CheckResult("S5", False, "insufficient H1 history")
    else:
        stretch = abs(ctx.entry - ema_h1)
        s4 = CheckResult(
            "S4",
            stretch <= 2.5 * atr_h1,
            f"|entry-EMA20|={stretch:.6g} vs 2.5xATR={2.5 * atr_h1:.6g}",
        )
        s5 = CheckResult(
            "S5",
            stop_dist >= 1.2 * atr_h1,
            f"stop dist {stop_dist:.6g} vs 1.2xATR={1.2 * atr_h1:.6g}",
        )

    return (
        CheckResult(
            "S1",
            ctx.bias_aligned,
            "D1 bias aligned" if ctx.bias_aligned else "D1 bias conflicts",
        ),
        CheckResult("S2", structure_ok, structure_detail),
        CheckResult(
            "S3",
            ctx.trigger_present,
            "trigger present" if ctx.trigger_present else "no trigger",
        ),
        s4,
        s5,
        _score_check_s6(ctx, liquidity, atr_h1),
        _score_check_s7(ctx, liquidity),
        CheckResult(
            "S8",
            not ctx.news_conflict,
            "news clean" if not ctx.news_conflict else "news conflicts",
        ),
        CheckResult(
            "S9",
            ctx.exposure.same_usd_sign_tickets < limits.max_same_usd_sign_tickets
            and ctx.exposure.open_tickets < limits.max_concurrent_positions,
            f"same-sign {ctx.exposure.same_usd_sign_tickets}/{limits.max_same_usd_sign_tickets}, "
            f"open {ctx.exposure.open_tickets}/{limits.max_concurrent_positions}",
        ),
    )


def _grade_from_score(score: int) -> str:
    if score >= 9:
        return "A+"
    if score == 8:
        return "A"
    if score >= 6:
        return "B+"
    if score >= 4:
        return "B"
    return GRADE_C


def evaluate(
    ctx: CandidateContext,
    limits: TradingLimits = LIMITS,
    slot_mult: float = 1.0,
) -> Evaluation:
    """Candidate eligibility only; NOT broker execution authorization.

    Caller supplies completed, point-in-time bars. Broker reconciliation, daily
    budget, spec attestation and account-type checks are separate admission gates.
    """
    _validate_candidate(ctx)
    atr_h1 = atr(ctx.bars_by_tf.get("H1", []))
    gates = _gate_checks(ctx)
    scored = _score_checks(ctx, limits, atr_h1)
    score = sum(1 for c in scored if c.passed)
    gates_ok = all(c.passed for c in gates)
    grade = _grade_from_score(score) if gates_ok else GRADE_C
    # A failed trend agreement is not a calibrated probability. Conservative
    # implementation of the documented contradiction cap until tri-state inputs exist.
    if grade in ("A+", "A", "B+") and (not ctx.bias_aligned or not scored[1].passed):
        grade = "B"
    risk: float | None = None
    ceiling: float | None = None
    if grade != GRADE_C:
        risk, ceiling = size_risk(grade, ctx.exposure, limits, slot_mult)
    allowed = grade != GRADE_C and risk is not None
    return Evaluation(
        pair=ctx.pair,
        direction=ctx.direction,
        gates=gates,
        scored=scored,
        score=score,
        grade=grade,
        trade_allowed=allowed,
        risk_pct=risk,
        slot_ceiling_pct=ceiling,
        framework_version=FRAMEWORK_VERSION,
        playbook_version=PLAYBOOK_VERSION,
        notes=("Candidate eligibility only; independent execution admission still required.",),
    )


def _validate_candidate(ctx: CandidateContext) -> None:
    flags = (
        ctx.strategy_rule_fires, ctx.bars_fresh, ctx.red_event_now, ctx.red_event_within_2h,
        ctx.event_cohort, ctx.session_ok, ctx.spread_ok, ctx.news_conflict,
        ctx.bias_aligned, ctx.trigger_present,
    )
    if any(type(flag) is not bool for flag in flags):
        raise ValueError("Checklist flags must be booleans, not model text")
    if ctx.pair not in TRADING_PAIRS or ctx.direction not in ("long", "short"):
        raise ValueError("Unsupported execution pair or direction")
    if any(not math.isfinite(p) or p <= 0 for p in (ctx.entry, ctx.stop)):
        raise ValueError("Entry and stop must be positive finite prices")
    if (ctx.direction == "long" and ctx.stop >= ctx.entry) or (
        ctx.direction == "short" and ctx.stop <= ctx.entry
    ):
        raise ValueError("Stop must be on the loss side of entry")
    if not math.isfinite(ctx.dqs) or not 0 <= ctx.dqs <= 1:
        raise ValueError("DQS must be between zero and one")
    ctx.exposure.validate()
    for tf, bars in ctx.bars_by_tf.items():
        last_time = -1
        for bar in bars:
            prices = (bar.open, bar.high, bar.low, bar.close)
            if any(not math.isfinite(p) or p <= 0 for p in prices):
                raise ValueError("Nonfinite or nonpositive market data")
            if not bar.low <= min(bar.open, bar.close) <= max(bar.open, bar.close) <= bar.high:
                raise ValueError("Invalid OHLC envelope")
            if bar.symbol not in (ctx.pair, ctx.pair + "m") or bar.timeframe != tf:
                raise ValueError("Cross-pair or wrong-timeframe market data")
            if bar.time_srv <= last_time:
                raise ValueError("Bars must have unique increasing timestamps")
            last_time = bar.time_srv


def to_receipt(ev: Evaluation) -> dict[str, object]:
    """JSON-ready receipt payload (ledger row body)."""

    def rows(items: tuple[CheckResult, ...]) -> list[dict[str, object]]:
        return [{"id": c.check_id, "pass": c.passed, "detail": c.detail} for c in items]

    return {
        "pair": ev.pair,
        "direction": ev.direction,
        "gates": rows(ev.gates),
        "scored": rows(ev.scored),
        "score": ev.score,
        "grade": ev.grade,
        "trade_allowed": ev.trade_allowed,
        "risk_pct": ev.risk_pct,
        "slot_ceiling_pct": ev.slot_ceiling_pct,
        "framework_version": ev.framework_version,
        "playbook_version": ev.playbook_version,
        "notes": list(ev.notes),
    }
