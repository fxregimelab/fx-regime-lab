"""Tests for src/signals/cot.py COT positioning signals."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.signals.cot import (
    compute_cot_percentile,
    compute_cot_smart_spread_percentile,
    normalize_cot_signal,
)
from src.types import CotRow


def _cot_rows(
    pair: str = "EURUSD",
    n: int = 20,
    net_long_start: int = 100,
    net_long_step: int = 10,
    with_breakdown: bool = True,
) -> list[CotRow]:
    rows: list[CotRow] = []
    base = date(2020, 1, 3)
    for i in range(n):
        net_long = net_long_start + i * net_long_step
        am = net_long + 20
        lm = net_long - 20
        rows.append(
            CotRow(
                date=base + timedelta(weeks=i),
                pair=pair,
                net_long=net_long,
                open_interest=1000 + i * 10,
                asset_mgr_net=am if with_breakdown else None,
                lev_money_net=lm if with_breakdown else None,
            )
        )
    return rows


class TestComputeCotPercentile:
    def test_empty_rows_returns_none(self) -> None:
        assert compute_cot_percentile([], "EURUSD") is None

    def test_wrong_pair_returns_none(self) -> None:
        rows = _cot_rows(pair="USDJPY")
        assert compute_cot_percentile(rows, "EURUSD") is None

    def test_insufficient_history_returns_none(self) -> None:
        rows = _cot_rows(n=5)
        assert compute_cot_percentile(rows, "EURUSD") is None

    def test_minimum_history_computes_percentile(self) -> None:
        rows = _cot_rows(n=9)  # 8 historical + 1 current = min_reports + 1
        result = compute_cot_percentile(rows, "EURUSD")
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_latest_is_maximum_returns_100(self) -> None:
        rows = _cot_rows(n=20, net_long_start=0, net_long_step=10)
        result = compute_cot_percentile(rows, "EURUSD")
        assert result == 100.0

    def test_latest_is_minimum_returns_0(self) -> None:
        rows = _cot_rows(n=20, net_long_start=200, net_long_step=-10)
        result = compute_cot_percentile(rows, "EURUSD")
        assert result == 0.0

    def test_as_of_filters_future_rows(self) -> None:
        rows = _cot_rows(n=20)
        as_of = rows[10].date
        result = compute_cot_percentile(rows, "EURUSD", as_of=as_of)
        assert result is not None

    def test_as_of_before_min_history_returns_none(self) -> None:
        rows = _cot_rows(n=20)
        as_of = rows[2].date
        assert compute_cot_percentile(rows, "EURUSD", as_of=as_of) is None

    def test_duplicate_dates_last_write_wins(self) -> None:
        rows = _cot_rows(n=12)
        duplicate = CotRow(
            date=rows[-1].date,
            pair="EURUSD",
            net_long=999,
            open_interest=1000,
        )
        result = compute_cot_percentile(rows + [duplicate], "EURUSD")
        assert result is not None
        # Duplicate with net_long=999 should be the current observation
        assert result == 100.0

    def test_window_limits_history_used(self) -> None:
        rows = _cot_rows(n=200)
        result = compute_cot_percentile(rows, "EURUSD", window_reports=50)
        assert result is not None


class TestComputeCotSmartSpreadPercentile:
    def test_empty_rows_returns_none(self) -> None:
        assert compute_cot_smart_spread_percentile([], "EURUSD") is None

    def test_falls_back_to_net_long_when_breakdown_missing(self) -> None:
        rows = _cot_rows(n=20, with_breakdown=False)
        result = compute_cot_smart_spread_percentile(rows, "EURUSD")
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_uses_smart_spread_when_breakdown_present(self) -> None:
        rows = _cot_rows(n=20)
        result = compute_cot_smart_spread_percentile(rows, "EURUSD")
        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_insufficient_history_returns_none(self) -> None:
        rows = _cot_rows(n=5)
        assert compute_cot_smart_spread_percentile(rows, "EURUSD") is None

    def test_as_of_filters_rows(self) -> None:
        rows = _cot_rows(n=20)
        as_of = rows[10].date
        result = compute_cot_smart_spread_percentile(rows, "EURUSD", as_of=as_of)
        assert result is not None


class TestNormalizeCotSignal:
    def test_none_returns_none(self) -> None:
        assert normalize_cot_signal(None) is None

    def test_median_returns_zero(self) -> None:
        assert normalize_cot_signal(50.0) == 0.0

    def test_100th_returns_one(self) -> None:
        assert normalize_cot_signal(100.0) == 1.0

    def test_0th_returns_minus_one(self) -> None:
        assert normalize_cot_signal(0.0) == -1.0

    def test_75th_returns_half(self) -> None:
        assert normalize_cot_signal(75.0) == pytest.approx(0.5)
