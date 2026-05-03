"""Tests for Alpha Ledger EOD MTM (pure logic + mocked writer)."""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import patch

import pytest

from src.validation import ledger as ledger_mod


def test_horizon_hit_bullish() -> None:
    assert ledger_mod._horizon_hit("BULLISH", 1.0, 1.1) == 1
    assert ledger_mod._horizon_hit("bullish", 1.0, 0.9) == 0


def test_horizon_hit_bearish() -> None:
    assert ledger_mod._horizon_hit("BEARISH", 1.0, 0.9) == 1
    assert ledger_mod._horizon_hit("BEARISH", 1.0, 1.1) == 0


def test_horizon_hit_neutral() -> None:
    assert ledger_mod._horizon_hit("NEUTRAL", 1.0, 2.0) == -1


def test_brier_t5_hit() -> None:
    assert ledger_mod._brier_t5("BULLISH", 1, 0.75) == pytest.approx(0.0625, abs=1e-9)


def test_brier_t5_miss() -> None:
    assert ledger_mod._brier_t5("BEARISH", 0, 0.6) == pytest.approx(0.36, abs=1e-9)


def test_brier_neutral_skipped() -> None:
    assert ledger_mod._brier_t5("NEUTRAL", 1, 0.99) is None


def test_mark_to_market_writes_updates() -> None:
    prices = [
        {"date": "2026-04-20", "close": 100.0, "low": 100.0, "high": 100.0},
        {"date": "2026-04-21", "close": 101.0, "low": 99.5, "high": 101.0},
        {"date": "2026-04-22", "close": 102.0, "low": 98.0, "high": 102.0},
        {"date": "2026-04-23", "close": 103.0, "low": 99.0, "high": 103.0},
        {"date": "2026-04-24", "close": 104.0, "low": 100.0, "high": 104.0},
        {"date": "2026-04-25", "close": 105.0, "low": 101.0, "high": 105.0},
    ]
    open_row: dict[str, Any] = {
        "id": "00000000-0000-4000-8000-000000000001",
        "date": "2026-04-20",
        "pair": "EURUSD",
        "regime": "R1",
        "primary_driver": "Rate",
        "direction": "BULLISH",
        "entry_close": 100.0,
        "confidence": 0.7,
        "t1_close": None,
        "t3_close": None,
        "t5_close": None,
        "t1_hit": None,
        "t3_hit": None,
        "t5_hit": None,
        "brier_score_t5": None,
        "max_pain_bps": None,
    }
    captured: list[list[dict[str, Any]]] = []

    def fake_update(rows: list[dict[str, Any]]) -> None:
        captured.append(rows)

    with (
        patch.object(ledger_mod.writer, "get_open_ledger_entries", return_value=[open_row]),
        patch.object(ledger_mod.writer, "update_ledger_entries", side_effect=fake_update),
    ):
        ledger_mod.mark_to_market_ledger(
            "EURUSD",
            prices,
            as_of_date=datetime.date(2026, 4, 25),
        )

    assert captured and len(captured[0]) == 1
    out = captured[0][0]
    assert out["t1_close"] == 101.0
    assert out["t1_hit"] == 1
    assert out["t3_close"] == 103.0
    assert out["t3_hit"] == 1
    assert out["t5_close"] == 105.0
    assert out["t5_hit"] == 1
    assert out["brier_score_t5"] is not None
    assert abs(float(out["brier_score_t5"]) - (1.0 - 0.7) ** 2) < 1e-9
    # Max adverse excursion vs entry 100: deepest low 98 on T+2 -> 200 bps
    assert out["max_pain_bps"] == pytest.approx(200.0)


def test_mark_to_market_fences_future_horizons() -> None:
    """Do not fill T+3/T+5 when their bar dates are after as_of (chronological fence)."""
    prices = [
        {"date": "2026-04-20", "close": 100.0, "low": 100.0, "high": 100.0},
        {"date": "2026-04-21", "close": 101.0, "low": 101.0, "high": 101.0},
        {"date": "2026-04-22", "close": 102.0, "low": 102.0, "high": 102.0},
        {"date": "2026-04-23", "close": 103.0, "low": 103.0, "high": 103.0},
        {"date": "2026-04-24", "close": 104.0, "low": 104.0, "high": 104.0},
        {"date": "2026-04-25", "close": 105.0, "low": 105.0, "high": 105.0},
    ]
    open_row: dict[str, Any] = {
        "id": "00000000-0000-4000-8000-000000000002",
        "date": "2026-04-20",
        "pair": "EURUSD",
        "regime": "R1",
        "primary_driver": "Rate",
        "direction": "BULLISH",
        "entry_close": 100.0,
        "confidence": 0.7,
        "t1_close": None,
        "t3_close": None,
        "t5_close": None,
        "t1_hit": None,
        "t3_hit": None,
        "t5_hit": None,
        "brier_score_t5": None,
        "max_pain_bps": None,
    }
    captured: list[list[dict[str, Any]]] = []

    def fake_update(rows: list[dict[str, Any]]) -> None:
        captured.append(rows)

    with (
        patch.object(ledger_mod.writer, "get_open_ledger_entries", return_value=[open_row]),
        patch.object(ledger_mod.writer, "update_ledger_entries", side_effect=fake_update),
    ):
        ledger_mod.mark_to_market_ledger(
            "EURUSD",
            prices,
            as_of_date=datetime.date(2026, 4, 21),
        )

    out = captured[0][0]
    assert out["t1_close"] == 101.0
    assert out["t1_hit"] == 1
    assert out.get("t3_close") is None
    assert out.get("t5_close") is None
    # T+1 only: lows >= entry -> no adverse excursion
    assert out.get("max_pain_bps") == pytest.approx(0.0)


def test_mark_to_market_mae_bearish() -> None:
    prices = [
        {"date": "2026-04-20", "close": 100.0, "low": 100.0, "high": 100.0},
        {"date": "2026-04-21", "close": 99.0, "low": 98.5, "high": 101.5},
        {"date": "2026-04-22", "close": 98.0, "low": 97.0, "high": 102.0},
        {"date": "2026-04-23", "close": 97.0, "low": 96.0, "high": 103.0},
        {"date": "2026-04-24", "close": 96.0, "low": 95.0, "high": 104.0},
        {"date": "2026-04-25", "close": 95.0, "low": 94.0, "high": 105.0},
    ]
    open_row: dict[str, Any] = {
        "id": "00000000-0000-4000-8000-000000000003",
        "date": "2026-04-20",
        "pair": "EURUSD",
        "regime": "R1",
        "primary_driver": "Rate",
        "direction": "BEARISH",
        "entry_close": 100.0,
        "confidence": 0.7,
        "t1_close": None,
        "t3_close": None,
        "t5_close": None,
        "t1_hit": None,
        "t3_hit": None,
        "t5_hit": None,
        "brier_score_t5": None,
        "max_pain_bps": None,
    }
    captured: list[list[dict[str, Any]]] = []

    def fake_update(rows: list[dict[str, Any]]) -> None:
        captured.append(rows)

    with (
        patch.object(ledger_mod.writer, "get_open_ledger_entries", return_value=[open_row]),
        patch.object(ledger_mod.writer, "update_ledger_entries", side_effect=fake_update),
    ):
        ledger_mod.mark_to_market_ledger(
            "EURUSD",
            prices,
            as_of_date=datetime.date(2026, 4, 25),
        )

    out = captured[0][0]
    # Adverse for bearish: high vs entry; max high in window is 105 on T+5 -> 500 bps
    assert out["max_pain_bps"] == pytest.approx(500.0)


def test_log_initial_signal_merges_forward_fields() -> None:
    existing: dict[str, Any] = {
        "t1_close": 1.1,
        "t1_hit": 1,
        "t3_close": None,
        "t3_hit": None,
        "t5_close": None,
        "t5_hit": None,
        "brier_score_t5": None,
        "max_pain_bps": 42.5,
    }

    with (
        patch.object(
            ledger_mod.writer,
            "get_strategy_ledger_entry",
            return_value=existing,
        ),
        patch.object(ledger_mod.writer, "write_ledger_entry") as w,
    ):
        ledger_mod.log_initial_signal(
            "EURUSD",
            datetime.date(2026, 4, 20),
            "R1",
            "Rate",
            "BULLISH",
            1.0,
            0.65,
        )
        assert w.called
        payload = w.call_args[0][0]
        assert payload["t1_close"] == 1.1
        assert payload["t1_hit"] == 1
        assert payload["max_pain_bps"] == 42.5
