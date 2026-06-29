"""Tests for RateHistoryProvider implementations."""

from __future__ import annotations

import datetime

from src.staged.contracts import IngestionSnapshot
from src.staged.signals.rate_history import (
    SinglePointFallbackProvider,
    SnapshotRateHistoryProvider,
)
from src.types import SpotBar


def _bar(d: datetime.date, close: float) -> SpotBar:
    return SpotBar(date=d, pair="EURUSD", open=close, high=close, low=close, close=close)


def test_single_point_fallback_repeats_spread_five_times() -> None:
    provider = SinglePointFallbackProvider()
    history = provider.spread_history("EURUSD", 2.0)
    assert history == [2.0, 2.0, 2.0, 2.0, 2.0]


def test_single_point_fallback_structural_history() -> None:
    provider = SinglePointFallbackProvider()
    assert provider.structural_history(None) is None
    assert provider.structural_history(1.5) == [1.5] * 5


def test_single_point_fallback_carry_and_bei_series() -> None:
    provider = SinglePointFallbackProvider()
    carry = provider.carry_series(1.25, min_length=30)
    assert len(carry) == 30
    assert all(v == 1.25 for v in carry)
    assert provider.carry_series(None, min_length=30) == ()

    bei = provider.bei_series(2.0, min_length=10)
    assert bei is not None
    assert len(bei) == 10
    assert all(v == 2.0 for v in bei)
    assert provider.bei_series(None, min_length=10) is None


def test_snapshot_provider_uses_spot_length_for_carry() -> None:
    as_of = datetime.date(2026, 1, 15)
    bars = tuple(_bar(as_of - datetime.timedelta(days=i), 1.1) for i in range(40))
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": bars},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    provider = SnapshotRateHistoryProvider(snapshot)
    carry = provider.carry_series(0.5, min_length=30)
    assert len(carry) == 40
    bei = provider.bei_series(2.0, min_length=30)
    assert bei is not None
    assert len(bei) == 40
