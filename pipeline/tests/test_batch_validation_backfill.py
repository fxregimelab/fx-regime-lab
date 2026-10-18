"""Tests for VQ: ``batch_validation_backfill`` causal spot resolution.

Covers:
- exact-match preference;
- no future dates ever used (the pre-fix forward-fill defect);
- staleness bound: None when nothing within ``_MAX_SPOT_BACKFILL_DAYS``;
- ``_build_validation_rows`` ignores future prices when scoring horizons.

All tests are pure — no network, no DB.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

import pytest

from src.backfill.batch_validation_backfill import (
    _MAX_SPOT_BACKFILL_DAYS,
    _build_validation_rows,
    _get_spot,
)
from src.validation.calendar import add_trading_days


def test_get_spot_prefers_exact_match() -> None:
    target = date(2026, 5, 20)
    prices = {
        target: 1.111,
        target - timedelta(days=1): 1.100,
        target + timedelta(days=1): 1.222,
    }
    assert _get_spot(prices, target) == 1.111


def test_get_spot_never_uses_future_dates() -> None:
    target = date(2026, 5, 20)
    prices = {
        target - timedelta(days=2): 1.100,
        target + timedelta(days=1): 9.999,
    }
    assert _get_spot(prices, target) == 1.100


def test_get_spot_returns_none_when_only_future_dates() -> None:
    target = date(2026, 5, 20)
    prices = {target + timedelta(days=1): 9.999}
    assert _get_spot(prices, target) is None


def test_get_spot_is_staleness_bounded() -> None:
    target = date(2026, 5, 20)
    assert _get_spot({target - timedelta(days=30): 1.100}, target) is None
    # Last observation on the bound is still usable.
    at_bound = target - timedelta(days=_MAX_SPOT_BACKFILL_DAYS)
    assert _get_spot({at_bound: 1.234}, target) == 1.234
    # A future observation must not rescue a stale series.
    stale_plus_future = {
        target - timedelta(days=30): 1.100,
        target + timedelta(days=1): 9.999,
    }
    assert _get_spot(stale_plus_future, target) is None


def _make_call(call_date: date, **overrides: Any) -> dict[str, Any]:
    call: dict[str, Any] = {
        "id": 7,
        "date": call_date,
        "pair": "EURUSD",
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
        "regime": "USD_WEAKNESS",
        "strategy_version": "v2",
        "data_source": "live",
    }
    call.update(overrides)
    return call


def test_build_validation_rows_ignores_future_prices_for_t5() -> None:
    """A price after T+5 must not be used to score T+5 (lookahead guard)."""
    call_date = date(2026, 6, 1)  # Monday
    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)

    # On/before T+5 only S0 exists; the T+5+2 price is FUTURE data the old
    # forward-fill would have consumed (log return ~4055 bps instead of 0).
    prices = {
        "EURUSD": {
            call_date: 1.1000,
            t5_date + timedelta(days=2): 1.6500,
            t20_date: 1.1100,
        }
    }
    rows = _build_validation_rows(
        [_make_call(call_date)], prices, as_of=date(2026, 10, 1), validated_keys=set()
    )

    assert len(rows) == 1
    row = rows[0]
    # S5 resolved backward to S0's observation (within the bound) → flat T+5.
    assert row["log_return_t5_bps"] == pytest.approx(0.0, abs=0.01)
    assert row["actual_direction_t5"] == "NEUTRAL"
    # T+20 still uses its exact match.
    assert row["log_return_t20_bps"] == pytest.approx(
        10_000.0 * math.log(1.1100 / 1.1000), abs=0.01
    )
    assert row["actual_direction_t20"] == "UP"
