"""Regression tests for validation aggregate evidence-group isolation."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.db import writer
from src.validation import aggregate


def _row(
    *,
    pair: str,
    data_source: str | None = "live",
    strategy_version: str | None = "v2",
    model_version: str | None = "2.0-live",
    evaluation_version: str | None = "published-direction-v1",
    correct: bool = True,
    call_date: str = "2026-01-02",
) -> dict[str, Any]:
    return {
        "date": call_date,
        "pair": pair,
        "data_source": data_source,
        "strategy_version": strategy_version,
        "model_version": model_version,
        "evaluation_version": evaluation_version,
        "population_version": "published-calls-v1",
        "evaluation_present": True,
        "predicted_direction": "BULLISH",
        "confidence": 0.8,
        "log_return_t5_bps": 5.0 if correct else -5.0,
        "correct_t5": correct,
        "correct_net_t5": correct,
        "log_return_net_bps_t5": 4.5 if correct else -5.5,
        "cost_bps_t5": 0.5,
        "brier_score_t5": 0.04 if correct else 0.64,
    }


def test_mixed_sources_models_and_evaluations_never_share_an_aggregate(
    monkeypatch: Any,
) -> None:
    rows = [
        _row(pair="EURUSD", correct=True),
        _row(pair="USDJPY", correct=False),
        _row(pair="EURUSD", data_source="replay", correct=False),
        _row(pair="EURUSD", model_version="simulation-v2", correct=False),
        _row(pair="EURUSD", evaluation_version="legacy-unversioned", correct=False),
        _row(
            pair="USDINR",
            data_source=None,
            strategy_version=None,
            model_version=None,
            evaluation_version=None,
            correct=True,
        ),
    ]
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_stats",
        lambda _pair, _window, _as_of: rows,
    )

    stats = aggregate.compute_aggregate_stats(as_of_date=date(2026, 3, 1))
    identities = {
        (
            item.pair,
            item.data_source,
            item.strategy_version,
            item.model_version,
            item.evaluation_version,
        ): item
        for item in stats
    }

    live_all = identities[
        ("ALL", "live", "v2", "2.0-live", "published-direction-v1")
    ]
    assert live_all.t5.total_calls == 2
    assert live_all.t5.directional_calls == 2
    assert live_all.t5.win_rate == 0.5
    assert ("ALL", "replay", "v2", "2.0-live", "published-direction-v1") not in identities
    assert ("EURUSD", "live", "v2", "simulation-v2", "published-direction-v1") in identities
    assert ("EURUSD", "live", "v2", "2.0-live", "legacy-unversioned") in identities
    assert ("USDINR", "unknown", "unknown", "unknown", "legacy-unversioned") in identities


def test_lookback_window_is_inclusive_and_anchored_to_requested_as_of(
    monkeypatch: Any,
) -> None:
    calls: list[tuple[str | None, int | None, date | None]] = []
    rows = [
        _row(pair="EURUSD", call_date="2026-05-05"),
        _row(pair="EURUSD", call_date="2026-05-06"),
        _row(pair="EURUSD", call_date="2026-05-15"),
        _row(pair="EURUSD", call_date="2026-05-16"),
        _row(pair="EURUSD", call_date="not-a-date"),
    ]

    def fake_read(
        pair_filter: str | None,
        lookback_days: int | None,
        as_of_date: date | None,
    ) -> list[dict[str, Any]]:
        calls.append((pair_filter, lookback_days, as_of_date))
        return rows

    monkeypatch.setattr(writer, "get_validation_log_for_stats", fake_read)

    stats = aggregate.compute_aggregate_stats(
        pair_filter="EURUSD",
        as_of_date=date(2026, 5, 15),
        lookback_days=10,
    )

    assert calls == [("EURUSD", 10, date(2026, 5, 15))]
    assert len(stats) == 1
    assert stats[0].window_days == 10
    assert stats[0].t5.total_calls == 2


def test_payload_persists_cohort_denominators_and_gross_signed_mean(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        writer,
        "get_validation_log_for_stats",
        lambda _pair, _window, _as_of: [_row(pair="EURUSD")],
    )
    stats = aggregate.compute_aggregate_stats(
        pair_filter="EURUSD",
        as_of_date=date(2026, 3, 1),
    )[0]

    payload = aggregate._stats_to_payload(stats)

    assert payload["data_source"] == "live"
    assert payload["strategy_version"] == "v2"
    assert payload["model_version"] == "2.0-live"
    assert payload["evaluation_version"] == "published-direction-v1"
    assert payload["window_days"] == 0
    assert payload["t5_net_directional_calls"] == 1
    assert payload["t5_pending_calls"] == 0
    assert payload["t5_unknown_direction_calls"] == 0
    assert payload["t5_probability_score_calls"] == 1
    assert payload["t5_mean_signed_gross_return_bps"] == 5.0
    assert "t5_sharpe_like" not in payload
    assert "t5_max_drawdown_bps" not in payload


def test_missing_evaluations_remain_in_population_separate_from_maturity(monkeypatch: Any) -> None:
    evaluated = _row(pair="EURUSD")
    missing = {**evaluated, "evaluation_present": False,
               "correct_t5": None, "log_return_t5_bps": None}
    pending = {**missing, "date": "2026-08-31"}
    monkeypatch.setattr(writer, "get_validation_log_for_stats",
                        lambda _pair, _window, _as_of: [evaluated, missing, pending])
    stats = aggregate.compute_aggregate_stats("EURUSD", date(2026, 9, 1))[0]
    assert stats.t5.total_calls == 3
    assert stats.t5.evaluation_calls == 1
    assert stats.t5.missing_evaluation_calls == 2
    assert stats.t5.pending_calls == 1
    assert stats.t5.missing_outcome_calls == 1
    assert stats.t5.directional_calls == 1
    payload = aggregate._stats_to_payload(stats)
    assert payload["population_version"] == "published-calls-v1"
    assert payload["t5_missing_evaluation_calls"] == 2
