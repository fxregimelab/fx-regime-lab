"""Tests for Round 4 — Historical backfill infrastructure."""

from __future__ import annotations

from datetime import date

import pytest

from src.backfill.historical_fetcher import fetch_historical_spot_yfinance
from src.backfill.orchestrator import _daterange, backfill_spots, replay_pipeline_for_date


def test_daterange_basic() -> None:
    dr = _daterange(date(2024, 1, 1), date(2024, 1, 3))
    assert dr == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]


def test_daterange_single_day() -> None:
    dr = _daterange(date(2024, 6, 15), date(2024, 6, 15))
    assert dr == [date(2024, 6, 15)]


def test_fetch_historical_spot_missing_ticker() -> None:
    with pytest.raises(ValueError, match="outside the locked universe"):
        fetch_historical_spot_yfinance("FAKEPAIR", date(2024, 1, 1), date(2024, 1, 5))


def test_archive_only_multi_pair_acquisition_propagates_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_archive(pair: str, start: date, end: date) -> int:
        calls.append(pair)
        if pair == "USDJPY":
            raise RuntimeError("archive unavailable")
        return 2

    monkeypatch.setattr("src.backfill.orchestrator.backfill_spot_for_pair", fake_archive)

    with pytest.raises(RuntimeError, match="archive unavailable"):
        backfill_spots(
            date(2024, 1, 1),
            date(2024, 1, 5),
            ["EURUSD", "USDJPY", "USDINR"],
        )

    assert calls == ["EURUSD", "USDJPY"]


def test_live_orchestrator_replay_is_retired() -> None:
    with pytest.raises(RuntimeError, match="point-in-time replay contract"):
        replay_pipeline_for_date(date(2024, 1, 2))
