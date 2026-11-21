"""Published calls retain their meaning through validation and aggregation."""

import math
from datetime import date
from typing import Any

import pytest

from src.db import writer
from src.validation import engine
from src.validation.aggregate import _compute_horizon


def test_published_calls_flow_into_matching_gross_net_and_pending_cohorts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {
        "EURUSD": {"id": 1, "predicted_direction": "BULLISH", "rate_signal": "BEARISH"},
        "USDJPY": {"id": 2, "predicted_direction": "BEARISH", "rate_signal": "BULLISH"},
        "USDINR": {"id": 3, "predicted_direction": "NEUTRAL", "rate_signal": "BULLISH"},
    }
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(engine, "load_universe", lambda: {p: {"class": "FX"} for p in calls})
    monkeypatch.setattr(writer, "get_historical_regime_calls", lambda pair, limit: [{
        **calls[pair], "pair": pair, "date": "2026-01-02", "confidence": 0.8,
    }])
    monkeypatch.setattr(writer, "get_validation_log_for_call", lambda *args: None)
    monkeypatch.setattr(writer, "get_publication_signal_for_call", lambda call_id: {
        "pair": next(pair for pair, call in calls.items() if call["id"] == call_id),
        "date": "2026-01-02",
        "spot": 1.0,
    })
    monkeypatch.setattr(writer, "get_exact_historical_price_for_date", lambda pair, d: {
        "pair": pair,
        "date": d,
        "close": math.exp(
            (-20.0 if pair == "USDJPY" else 20.0) / 10_000.0
        ),
    })
    monkeypatch.setattr(writer, "get_signal_for_pair_date", lambda *args: pytest.fail(
        "mutable signals must not be used by repaired scoring"), raising=False)
    monkeypatch.setattr(writer, "write_validation_row", captured.append)

    engine.run_validation(as_of_date=date(2026, 1, 9))

    assert len(captured) == 3
    stats = _compute_horizon(
        captured, "T+5", "brier_score_t5", "correct_t5", "log_return_t5_bps", date(2026, 1, 9),
    )
    assert stats.total_calls == 3
    assert stats.directional_calls == stats.net_directional_calls == 2
    assert stats.win_rate == stats.net_win_rate == 1.0
    assert stats.mean_brier == pytest.approx(0.04)
    assert stats.mean_log_return_bps == pytest.approx(20.0)
    assert stats.sharpe_like is None and stats.max_drawdown_bps is None
    short = next(row for row in captured if row["pair"] == "USDJPY")
    assert short["log_return_net_bps_t5"] == pytest.approx(19.7)
    neutral = next(row for row in captured if row["pair"] == "USDINR")
    assert neutral["correct_t5"] is None
    pending = _compute_horizon(
        captured, "T+20", "brier_score_t20", "correct_t20", "log_return_t20_bps",
        date(2026, 1, 9),
    )
    assert pending.directional_calls == 0
    assert pending.win_rate is None
