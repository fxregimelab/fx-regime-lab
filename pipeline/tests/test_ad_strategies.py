"""Spec 02 section 6 oracle tests for the SU1/SU2/SU3 detectors.

Positive fixtures are hand-constructed bars where every conjunction is
satisfiable; each negative mutates exactly one condition. The SU2 tests also
document a frozen-spec interaction: a textbook sweep/reclaim/retest cannot
reach the 1.2xATR stop floor, so SU2-v1 produces no tradeable candidate under
the shipped geometry gate (the spy test proves the detection chain itself is
correct). SU4 stays research-only and is not implemented for execution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.paper.contracts import ContractError
from src.paper.features import OHLCBar, Swing
from src.paper.strategies import (
    R_D1_CONTEXT,
    R_TRIGGER_CLOSE,
    Rejection,
    SetupCandidate,
    _cost_share,
    _entry_ok,
    detect_su1,
    detect_su2,
    detect_su3,
    resolve_conflicts,
)

MONDAY = datetime(2026, 10, 19, 0, tzinfo=UTC)


def mk(ts: datetime, o: float, h: float, low: float, c: float) -> OHLCBar:
    """Bar helper that clamps high/low around the body (avoids schema noise)."""
    return OHLCBar(
        timestamp=ts,
        open=o,
        high=max(h, o, c),
        low=min(low, o, c),
        close=c,
        volume=1000.0,
    )


def h4_rising(start: datetime = MONDAY) -> list[Swing]:
    def at(hours: int) -> datetime:
        return start + timedelta(hours=hours)

    return [
        Swing("high", 0, at(4), 105.0, 2, at(6)),
        Swing("high", 4, at(8), 105.5, 6, at(10)),
        Swing("low", 2, at(6), 100.0, 4, at(8)),
        Swing("low", 6, at(10), 100.5, 8, at(12)),
    ]


# --- SU1 fixtures ---------------------------------------------------------------


def su1_h1(
    start: datetime = MONDAY,
    *,
    touch_pad: float = 0.05,
    broke: bool = False,
    trigger_close: float = 103.55,
    trigger_open: float = 102.8,
    trigger_high: float = 103.65,
    prev_high: float | None = None,
) -> list[OHLCBar]:
    """Rising trend, EMA-touching pullback (bars 30-34), then a bullish trigger.

    The pullback lows sit ``touch_pad * ATR`` above the EMA20 value at that bar,
    so ``touch_pad`` alone controls the "touched the EMA" conjunct.
    """
    bars: list[OHLCBar] = []
    for i in range(36):
        ts = start + timedelta(hours=i)
        if i < 20:
            close = 95.0 + 0.45 * i
        elif i < 30:
            close = 103.6
        elif i < 35:
            close = 102.6
        else:
            close = trigger_close
        bars.append(mk(ts, close - 0.05, close + 0.35, close - 0.5, close))

    from src.paper.features import atr14, ema20_series

    ema = ema20_series(bars)
    atr = atr14(bars[21:36])
    for i in range(30, 35):
        bars[i] = mk(bars[i].timestamp, bars[i].open, bars[i].high, ema[i] - touch_pad * atr,
                     bars[i].close)
    if broke:
        b = bars[33]
        bars[33] = mk(b.timestamp, b.open, b.high, 101.0, 101.0)
    if prev_high is not None:
        b = bars[34]
        bars[34] = mk(b.timestamp, b.open, prev_high, b.low, b.close)
    b = bars[35]
    bars[35] = mk(b.timestamp, trigger_open, trigger_high, 102.7, trigger_close)
    return bars


def su1_m15(
    start: datetime = MONDAY,
    *,
    retest_low: float = 103.55,
    retest_close: float = 103.7,
    entry_open: float = 103.62,
    delay: int = 0,
    hold_above: bool = False,
) -> list[OHLCBar]:
    """M15 bars after the trigger close (35h). Bar 1 is the retest by default."""
    trigger_close = start + timedelta(hours=35)
    out: list[OHLCBar] = []
    for k in range(1, 7):
        ts = trigger_close + timedelta(minutes=15 * k)
        if k <= delay or (hold_above and k > 1):
            out.append(mk(ts, 103.9, 104.0, 103.9, 103.95))  # never returns to the level
        elif k == delay + 1:
            out.append(mk(ts, 103.62, 103.8, retest_low, retest_close))
        elif k == delay + 2:
            out.append(mk(ts, entry_open, entry_open + 0.3, entry_open - 0.3, entry_open))
        else:
            out.append(mk(ts, 103.65, 103.8, 103.4, 103.7))
    return out


def test_su1_long_positive_candidate() -> None:
    candidates = detect_su1(
        su1_h1(), h4_rising(), su1_m15(), pair="EURUSD", d1_context="long", direction="long"
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.setup_id == "SU1-v1" and cand.side == "long"
    assert cand.trigger_at == MONDAY + timedelta(hours=35)
    assert cand.decision_at == MONDAY + timedelta(hours=35, minutes=15)
    assert cand.entry_at == cand.decision_at
    assert cand.entry_price == pytest.approx(103.62)
    # stop = min(pullback low, retest low) - 0.25*ATR; pullback low is the
    # EMA-touching bar 30 low.
    assert cand.stop_price == pytest.approx(102.02 - 0.25 * cand.atr_h1, abs=0.02)
    assert cand.entry_price - cand.stop_price >= 1.2 * cand.atr_h1
    assert cand.target_a_price == pytest.approx(
        cand.entry_price + (cand.entry_price - cand.stop_price)
    )
    assert cand.expires_at == MONDAY + timedelta(hours=36)
    assert cand.trigger_ids == ("su1-pullback-ema-touch", "su1-trigger-close", "su1-m15-retest")


@pytest.mark.parametrize(
    "mutation",
    [
        {"d1_context": "neutral"},
        {"prev_high": 103.8},  # trigger close no longer clears the prior high
        {"trigger_open": 103.7, "trigger_close": 103.55, "trigger_high": 103.8},  # bearish bar
        {"touch_pad": 0.6},  # pullback never touches the EMA
        {"broke": True},  # pullback closes through the last confirmed swing low
        {"retest_low": 104.2, "hold_above": True},  # retest never returns to the level
        {"retest_close": 103.6, "hold_above": True},  # retest fails to close back above
        {"entry_open": 104.4},  # entry outside the 0.25*ATR band
        {"delay": 5},  # retest arrives after the 4-bar window
    ],
)
def test_su1_single_condition_negatives(mutation: dict[str, Any]) -> None:
    h1_keys = {"prev_high", "trigger_open", "trigger_close", "trigger_high", "touch_pad", "broke"}
    m15_keys = {"retest_low", "retest_close", "entry_open", "delay", "hold_above"}
    h1 = su1_h1(**{k: v for k, v in mutation.items() if k in h1_keys})
    m15 = su1_m15(**{k: v for k, v in mutation.items() if k in m15_keys})
    candidates = detect_su1(
        h1,
        h4_rising(),
        m15,
        pair="EURUSD",
        d1_context=mutation.get("d1_context", "long"),
        direction="long",
    )
    assert candidates == []


def test_su1_short_is_exact_mirror() -> None:
    def mirror(bars: list[OHLCBar]) -> list[OHLCBar]:
        return [
            OHLCBar(b.timestamp, 200.0 - b.open, 200.0 - b.low, 200.0 - b.high, 200.0 - b.close)
            for b in bars
        ]

    mirrored_swings = [
        Swing(
            "low" if s.kind == "high" else "high",
            s.index,
            s.timestamp,
            200.0 - s.price,
            s.confirmed_index,
            s.confirmed_at,
        )
        for s in h4_rising()
    ]
    candidates = detect_su1(
        mirror(su1_h1()),
        mirrored_swings,
        mirror(su1_m15()),
        pair="EURUSD",
        d1_context="short",
        direction="short",
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.side == "short"
    assert cand.entry_price == pytest.approx(200.0 - 103.62)
    assert cand.stop_price == pytest.approx(200.0 - (102.02 - 0.25 * cand.atr_h1), abs=0.02)
    assert cand.target_a_price < cand.entry_price


# --- SU3 fixtures ---------------------------------------------------------------


def su3_h1(
    start: datetime = MONDAY, *, breakout: tuple[float, float] | None = None
) -> list[OHLCBar]:
    bars: list[OHLCBar] = []
    for i in range(36):
        ts = start + timedelta(hours=i)
        if i == 35:
            o, c = breakout if breakout is not None else (99.8, 100.5)
            bars.append(mk(ts, o, c + 0.5, o - 0.1, c))
        else:
            c = 99.3 + 0.25 * (1.0 if (i // 2) % 2 == 0 else -1.0)
            bars.append(mk(ts, c - 0.1, c + 0.5, c - 0.5, c))
    return bars


def su3_m15(
    start: datetime = MONDAY,
    *,
    retest_low: float = 98.9,
    retest_close: float = 100.3,
    delay: int = 0,
) -> list[OHLCBar]:
    trigger_close = start + timedelta(hours=35)
    out: list[OHLCBar] = []
    for k in range(1, 11):
        ts = trigger_close + timedelta(minutes=15 * k)
        if k <= delay:
            out.append(mk(ts, 100.25, 100.8, 100.2, 100.3))  # no dip into the zone
        elif k == delay + 1:
            out.append(mk(ts, 100.1, 100.4, retest_low, retest_close))
        elif k == delay + 2:
            out.append(mk(ts, 100.3, 100.6, 100.1, 100.3))
        else:
            out.append(mk(ts, 100.4, 100.7, 100.2, 100.4))
    return out


def test_su3_long_positive_deep_retest_passes_geometry() -> None:
    candidates = detect_su3(
        su3_h1(), h4_rising(), su3_m15(), pair="EURUSD", d1_context="long", direction="long"
    )
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.setup_id == "SU3-v1"
    assert cand.entry_price == pytest.approx(100.3)
    # level = max(high) over the prior 20 H1 bars = 100.05, ATR = 1.06786;
    # zone_lower = 100.05 - 0.1*ATR; stop = min(retest low, zone_lower) - 0.25*ATR.
    assert cand.stop_price == pytest.approx(98.6330, abs=0.001)
    assert abs(cand.entry_price - cand.stop_price) >= 1.2 * cand.atr_h1
    assert cand.expires_at == MONDAY + timedelta(hours=37)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"breakout": (99.4, 100.12)},  # close below the +0.1*ATR margin
        {"breakout": (99.85, 100.2)},  # body 0.35 < 0.5*ATR
        {"retest_close": 100.0},  # retest never closes back above the level
        {"delay": 8},  # retest arrives after the 8-bar window
    ],
)
def test_su3_single_condition_negatives(kwargs: dict[str, Any]) -> None:
    breakout = kwargs.pop("breakout", None)
    candidates = detect_su3(
        su3_h1(breakout=breakout),
        h4_rising(),
        su3_m15(start=MONDAY, **kwargs),
        pair="EURUSD",
        d1_context="long",
        direction="long",
    )
    assert candidates == []


# --- SU2: detection correct, frozen geometry gate rejects -----------------------


def su2_h1(start: datetime = MONDAY) -> list[OHLCBar]:
    bars: list[OHLCBar] = []
    for i in range(40):
        ts = start + timedelta(hours=i)
        if i == 20:
            c = 100.5
        elif i == 26:
            c = 100.55
        else:
            c = 100.6
        bars.append(mk(ts, c - 0.05, c + 0.5, c - 0.5, c))
    return bars


def su2_m15(start: datetime = MONDAY, *, sweep_low: float = 99.8) -> list[OHLCBar]:
    """Sweep, held retest, then the entry bar; padded past the 10-bar minimum."""
    anchor = start + timedelta(hours=33)  # Tuesday 09:00 close
    out = [
        mk(anchor + timedelta(minutes=15), 100.25, 100.35, sweep_low, 100.3),  # sweep 09:15
        mk(anchor + timedelta(minutes=30), 100.1, 100.35, 100.1, 100.3),  # retest 09:30
        mk(anchor + timedelta(minutes=45), 100.1, 100.5, 100.0, 100.3),  # entry bar 09:45
    ]
    for k in range(4, 13):
        out.append(mk(anchor + timedelta(minutes=15 * k), 100.3, 100.5, 100.2, 100.4))
    return out


def test_su2_textbook_chain_is_rejected_by_frozen_stop_floor() -> None:
    """Spec 02 section 2 requires stop >= 1.2*ATR; a spec-exact SU2 stop is
    structurally ~0.55*ATR here, so SU2-v1 cannot trade as written. Documented,
    not waived: this needs an owner spec amendment."""
    candidates = detect_su2(
        su2_h1(), h4_rising(), su2_m15(), pair="EURUSD", d1_context="long", direction="long"
    )
    assert candidates == []


def test_su2_detection_chain_forms_and_is_geometrically_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[float, float, float]] = []

    def spy(pair: str, entry: float, stop: float, atr: float) -> bool:
        seen.append((entry, stop, atr))
        return True

    monkeypatch.setattr("src.paper.strategies._entry_ok", spy)
    candidates = detect_su2(
        su2_h1(), h4_rising(), su2_m15(), pair="EURUSD", d1_context="long", direction="long"
    )
    assert len(seen) == 1
    entry, stop, atr = seen[0]
    assert entry == pytest.approx(100.1)
    assert stop == pytest.approx(99.55, abs=0.01)
    assert entry - stop < 1.2 * atr  # the frozen floor is what rejects it
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.setup_id == "SU2-v1"
    assert cand.trigger_at == MONDAY + timedelta(hours=33, minutes=15)
    assert cand.decision_at == MONDAY + timedelta(hours=33, minutes=30)


def test_su2_rejects_sweep_beyond_half_atr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.paper.strategies._entry_ok", lambda p, e, s, a: True)
    candidates = detect_su2(
        su2_h1(),
        h4_rising(),
        su2_m15(sweep_low=99.4),
        pair="EURUSD",
        d1_context="long",
        direction="long",
    )
    assert candidates == []


# --- Gates and conflict resolution ------------------------------------------------


def test_entry_gates_stop_floor_and_cost_share() -> None:
    assert not _entry_ok("EURUSD", 100.0, 100.0 - 1.19, 1.0)
    assert _entry_ok("EURUSD", 100.0, 100.0 - 1.21, 1.0)
    assert _cost_share("EURUSD", 100.0, 100.0 - 1.21) <= 0.10
    assert _cost_share("EURUSD", 100.0, 100.0 - 0.01) > 0.10


def _cand(setup_id: str, side: str, at: datetime) -> SetupCandidate:
    return SetupCandidate(
        setup_id=setup_id,
        side=side,
        trigger_at=at,
        decision_at=at,
        entry_at=at,
        entry_price=100.0,
        stop_price=98.0,
        target_a_price=102.0,
        atr_h1=1.0,
        expires_at=at + timedelta(minutes=60),
        trigger_ids=(),
    )


def test_conflict_resolution_precedence_and_opposite_side_wait() -> None:
    at = MONDAY + timedelta(hours=40)
    su1_long = _cand("SU1-v1", "long", at)
    su3_long = _cand("SU3-v1", "long", at)
    assert resolve_conflicts([su1_long, su3_long]) == [su1_long]
    assert resolve_conflicts([su1_long, _cand("SU1-v1", "short", at)]) == []
    later = _cand("SU2-v1", "long", at + timedelta(minutes=15))
    assert resolve_conflicts([su1_long, later]) == [su1_long, later]


# --- Rejection tracing and single-bar evaluation ---------------------------------


def test_rejections_record_the_first_failing_gate() -> None:
    sink: list[Rejection] = []
    found = detect_su1(
        su1_h1(),
        h4_rising(),
        su1_m15(),
        pair="EURUSD",
        d1_context="short",
        direction="long",
        rejections=sink,
    )
    assert found == []
    assert [(r.setup_id, r.reason) for r in sink] == [("SU1-v1", R_D1_CONTEXT)]


def test_rejection_sink_does_not_change_emitted_candidates() -> None:
    baseline = detect_su1(
        su1_h1(), h4_rising(), su1_m15(), pair="EURUSD",
        d1_context="long", direction="long",
    )
    sink: list[Rejection] = []
    with_sink = detect_su1(
        su1_h1(), h4_rising(), su1_m15(), pair="EURUSD",
        d1_context="long", direction="long", rejections=sink,
    )
    assert baseline == with_sink
    # Every evaluated non-candidate bar is recorded; the candidate is not.
    candidate_times = {c.trigger_at for c in baseline}
    assert sink
    assert all(r.at not in candidate_times for r in sink)


def test_only_index_evaluates_exactly_one_trigger_bar() -> None:
    h1 = su1_h1()
    m15 = su1_m15()
    last = len(h1) - 1

    found = detect_su1(
        h1, h4_rising(), m15, pair="EURUSD", d1_context="long",
        direction="long", only_index=last,
    )
    assert len(found) == 1

    sink: list[Rejection] = []
    missed = detect_su1(
        h1, h4_rising(), m15, pair="EURUSD", d1_context="long",
        direction="long", only_index=last - 1, rejections=sink,
    )
    assert missed == []
    assert [r.reason for r in sink] == [R_TRIGGER_CLOSE]


def test_only_index_outside_the_evaluable_range_raises() -> None:
    with pytest.raises(ContractError):
        detect_su1(
            su1_h1(), h4_rising(), su1_m15(), pair="EURUSD",
            d1_context="long", direction="long", only_index=999,
        )
