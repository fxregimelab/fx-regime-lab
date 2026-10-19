"""Hand-oracle tests for the AD-T09 offline feature core (spec 02 section 6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.paper.contracts import ContractError
from src.paper.features import (
    OHLCBar,
    Pool,
    Swing,
    atr14,
    build_pools,
    confirmed_swings,
    ema20_at,
    ema20_series,
    has_recent_unexplained_gap,
    require_window,
    session_allows_entry,
    structure_state,
    validate_bars,
)

T0 = datetime(2026, 10, 19, 0, tzinfo=UTC)


def bar(offset_minutes: float, *, open_: float, high: float, low: float, close: float) -> OHLCBar:
    return OHLCBar(
        timestamp=T0 + timedelta(minutes=offset_minutes),
        open=float(open_),
        high=float(high),
        low=float(low),
        close=float(close),
    )


def flat_bars(n: int, *, step: float = 60.0, price: float = 100.0) -> list[OHLCBar]:
    return [
        bar(i * step, open_=price, high=price + 1.0, low=price - 1.0, close=price)
        for i in range(n)
    ]


def test_atr14_is_mean_of_last_14_true_ranges() -> None:
    assert atr14(flat_bars(15)) == 2.0
    with pytest.raises(ContractError):
        atr14(flat_bars(14))


def test_ema20_seed_and_first_recursion_closed_form() -> None:
    bars = [
        bar(i, open_=float(i + 1), high=float(i + 1) + 0.5,
            low=float(i + 1) - 0.5, close=float(i + 1))
        for i in range(21)
    ]
    series = ema20_series(bars)
    assert series[19] == pytest.approx(10.5)  # SMA of closes 1..20
    assert series[20] == pytest.approx((2 / 21) * 21 + (19 / 21) * 10.5)  # 11.5
    assert ema20_at(bars, 0) is None
    assert ema20_at(bars, 19) == pytest.approx(10.5)


def _swing_bars(highs: list[float], lows: list[float]) -> list[OHLCBar]:
    return [
        bar(i, open_=lows[i] + 1, high=highs[i], low=lows[i], close=lows[i] + 1)
        for i in range(len(highs))
    ]


def test_confirmed_swings_emit_at_pivot_plus_two_with_strict_uniqueness() -> None:
    bars = _swing_bars([5, 5, 5, 10, 5, 5, 5], [4, 4, 4, 1, 4, 4, 4])
    swings = confirmed_swings(bars)
    kinds = {(s.kind, s.index) for s in swings}
    assert kinds == {("high", 3), ("low", 3)}
    high = next(s for s in swings if s.kind == "high")
    assert high.confirmed_at == bars[5].timestamp
    assert high.price == 10.0


def test_tied_extremes_are_not_single_swings() -> None:
    bars = _swing_bars([5, 5, 5, 10, 10, 5, 5], [4, 4, 4, 4, 4, 4, 4])
    assert confirmed_swings(bars) == []


def _swing(kind: str, index: int, price: float, confirmed_index: int) -> Swing:
    return Swing(
        kind=kind,
        index=index,
        timestamp=T0 + timedelta(hours=index),
        price=price,
        confirmed_index=confirmed_index,
        confirmed_at=T0 + timedelta(hours=confirmed_index),
    )


def test_structure_state_alignment_matrix() -> None:
    rising = [_swing("high", 10, 101.0, 12), _swing("high", 20, 102.0, 22),
              _swing("low", 11, 91.0, 13), _swing("low", 21, 92.0, 23)]
    falling = [_swing("high", 10, 102.0, 12), _swing("high", 20, 101.0, 22),
               _swing("low", 11, 92.0, 13), _swing("low", 21, 91.0, 23)]
    assert structure_state(rising, direction="long", as_of_index=30) == "aligned"
    assert structure_state(rising, direction="short", as_of_index=30) == "opposed"
    assert structure_state(falling, direction="short", as_of_index=30) == "aligned"
    mixed = [_swing("high", 10, 101.0, 12), _swing("high", 20, 102.0, 22),
             _swing("low", 11, 92.0, 13), _swing("low", 21, 91.0, 23)]
    assert structure_state(mixed, direction="long", as_of_index=30) == "neutral"
    assert structure_state(rising[:2] + rising[2:3], direction="long", as_of_index=30) == (
        "insufficient"
    )


def test_unconfirmed_swings_are_invisible_to_structure() -> None:
    pending = [_swing("high", 10, 101.0, 32), _swing("high", 20, 102.0, 33),
               _swing("low", 11, 91.0, 34), _swing("low", 21, 92.0, 35)]
    assert structure_state(pending, direction="long", as_of_index=30) == "insufficient"


def test_pools_require_two_extrema_within_tolerance_and_three_bar_separation() -> None:
    lows = [_swing("low", 5, 100.0, 7), _swing("low", 10, 100.05, 12)]
    pools = build_pools(lows, atr_value=1.0)
    assert len(pools) == 1
    assert pools[0] == Pool(kind="low", lower=100.0, upper=100.05,
                            swing_indices=(5, 10), confirmed_at=lows[1].confirmed_at)
    too_close = [_swing("low", 5, 100.0, 7), _swing("low", 6, 100.05, 8)]
    assert build_pools(too_close, atr_value=1.0) == []
    far_apart = [_swing("low", 5, 100.0, 7), _swing("low", 10, 101.5, 12)]
    assert build_pools(far_apart, atr_value=1.0) == []


def test_pools_extend_within_cluster_and_break_on_new_extreme() -> None:
    lows = [_swing("low", 5, 100.0, 7), _swing("low", 10, 100.05, 12),
            _swing("low", 15, 99.97, 17), _swing("low", 20, 98.0, 22)]
    pools = build_pools(lows, atr_value=1.0)
    assert [p.swing_indices for p in pools] == [(5, 10, 15)]
    assert pools[0].lower == 99.97 and pools[0].upper == 100.05


def test_session_window_boundaries() -> None:
    def at(day_hour: str, hour: int, minute: int) -> datetime:
        return datetime(2026, 10, int(day_hour), hour, minute, tzinfo=UTC)
    assert not session_allows_entry(at("19", 7, 14))
    assert session_allows_entry(at("19", 7, 15))
    assert session_allows_entry(at("19", 16, 14))
    assert not session_allows_entry(at("19", 16, 15))
    assert session_allows_entry(at("23", 13, 59))  # Friday
    assert not session_allows_entry(at("23", 14, 0))
    assert not session_allows_entry(at("24", 10, 0))  # Saturday


def test_gap_check_allows_weekends_and_flags_intra_week_holes() -> None:
    hourly = flat_bars(30)
    assert not has_recent_unexplained_gap(hourly, timeframe_minutes=60, lookback=20)
    holed = hourly[:-1] + [
        bar(29 * 60 + 300, open_=100, high=101, low=99, close=100)  # 5-hour hole
    ]
    assert has_recent_unexplained_gap(holed, timeframe_minutes=60, lookback=20)
    friday = datetime(2026, 10, 23, 16, tzinfo=UTC)  # Friday session
    weekend = [OHLCBar(friday + timedelta(hours=i), 100.0, 101.0, 99.0, 100.0)
               for i in range(5)]
    weekend.append(OHLCBar(datetime(2026, 10, 26, 6, tzinfo=UTC), 100.0, 101.0, 99.0, 100.0))
    assert not has_recent_unexplained_gap(weekend, timeframe_minutes=60, lookback=10)
    weekend.append(OHLCBar(datetime(2026, 10, 27, 10, tzinfo=UTC), 100.0, 101.0, 99.0, 100.0))
    assert has_recent_unexplained_gap(weekend, timeframe_minutes=60, lookback=10)


def test_bar_and_window_validation() -> None:
    with pytest.raises(ContractError):
        OHLCBar(T0.replace(tzinfo=None), 100.0, 101.0, 99.0, 100.0)
    with pytest.raises(ContractError):
        OHLCBar(T0, 100.0, 101.0, 102.0, 100.5)
    with pytest.raises(ContractError):
        OHLCBar(T0, 100.0, float("nan"), 99.0, 100.0)
    with pytest.raises(ContractError):
        OHLCBar(T0, 100.0, 101.0, 99.0, 0.0)
    dup = flat_bars(3) + [bar(120.0, open_=100, high=101, low=99, close=100)]
    with pytest.raises(ContractError):
        validate_bars(dup)
    with pytest.raises(ContractError):
        require_window(flat_bars(10), min_bars=32, max_bars=128, label="M15")
    with pytest.raises(ContractError):
        require_window(flat_bars(200), min_bars=32, max_bars=128, label="M15")
