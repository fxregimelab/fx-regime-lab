"""Check session timing and missing-hour exclusion independently of the UI."""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.private_desk.sessions import session_study


def hourly_bars() -> list[dict[str, Any]]:
    start = datetime(2025, 1, 6, tzinfo=UTC)
    return [
        {
            "time": (start + timedelta(hours=i)).isoformat(),
            "open": 1.0 + i * 0.001,
            "high": 1.002 + i * 0.001,
            "low": 0.999 + i * 0.001,
            "close": 1.001 + i * 0.001,
        }
        for i in range(2200)
    ]


def test_session_clock_and_chronological_labels() -> None:
    report = session_study("EURUSD", hourly_bars())
    assert report["probability"] is None
    for trial in report["comparisons"]:
        zone = ZoneInfo(trial["timezone"])
        for cohort in trial["trades"].values():
            for trade in cohort:
                entry = datetime.fromisoformat(trade["entry_time"]).astimezone(zone)
                assert entry.hour == 8 and entry.weekday() < 5
                assert trade["signal_time"] < trade["entry_time"] <= trade["exit_time"]
        train = trial["trades"]["train"]
        test = trial["trades"]["test"]
        assert train and test
        assert train[-1]["exit_time"] < test[0]["signal_time"]


def test_missing_open_hour_excludes_feature_and_label_windows() -> None:
    bars = hourly_bars()
    baseline = session_study("EURUSD", bars)
    # Monday morning, an open-market hour inside potential test windows.
    del bars[1513]
    result = session_study("EURUSD", bars)
    assert sum(t["excluded_missing_hour_windows"] for t in result["comparisons"]) > 0
    assert sum(t["test"]["trade_count"] for t in result["comparisons"]) <= sum(
        t["test"]["trade_count"] for t in baseline["comparisons"]
    )


def test_session_history_threshold_is_explicit() -> None:
    result = session_study("EURUSD", hourly_bars()[:900])
    assert result["status"] == "UNAVAILABLE"
    assert "1,000" in result["reason"]
