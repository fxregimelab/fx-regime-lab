"""Regression tests for retired unsafe historical maintenance paths."""

from __future__ import annotations

import inspect
from datetime import date
from typing import Any

import pytest

from src.backfill import batch_validation_stats, risk_reversal_proxy


def test_batch_stats_delegates_once_and_preserves_as_of_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_date = date(2026, 9, 27)
    sentinel: list[Any] = [object()]
    calls: list[dict[str, Any]] = []

    def fake_run_aggregate_stats(**kwargs: Any) -> list[Any]:
        calls.append(kwargs)
        return sentinel

    monkeypatch.setattr(
        batch_validation_stats.aggregate,
        "run_aggregate_stats",
        fake_run_aggregate_stats,
    )

    result = batch_validation_stats.run_batch_stats(as_of_date=requested_date)

    assert result is sentinel
    assert calls == [{"as_of_date": requested_date}]


def test_batch_stats_has_no_parallel_sql_or_destructive_maintenance() -> None:
    source = inspect.getsource(batch_validation_stats).lower()

    assert "pg8000" not in source
    assert ".run(" not in source
    assert "disable trigger" not in source
    assert "delete from" not in source
    assert "insert into" not in source
    assert "_compute_horizon" not in source
    assert "_sharpe_like" not in source
    assert "_max_drawdown" not in source


def test_explicit_risk_reversal_write_is_rejected_before_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    touched_io = False

    def unexpected_read(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal touched_io
        touched_io = True
        raise AssertionError("write rejection must happen before database access")

    monkeypatch.setattr(
        risk_reversal_proxy.writer,
        "get_historical_signals",
        unexpected_read,
    )

    with pytest.raises(RuntimeError, match="versioned replay.*observed OTC"):
        risk_reversal_proxy.backfill_risk_reversal_proxy(dry_run=False)

    assert touched_io is False


def test_risk_reversal_inspection_is_bounded_and_never_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[tuple[str, int]] = []

    def fake_read(pair: str, limit: int) -> list[dict[str, str]]:
        reads.append((pair, limit))
        return [{"pair": pair}, {"pair": pair}]

    monkeypatch.setattr(
        risk_reversal_proxy.writer,
        "get_historical_signals",
        fake_read,
    )

    inspected, calls_changed = risk_reversal_proxy.backfill_risk_reversal_proxy(
        limit_per_pair=25
    )

    assert reads == [
        ("EURUSD", 25),
        ("USDJPY", 25),
        ("USDINR", 25),
    ]
    assert inspected == 6
    assert calls_changed == 0


def test_risk_reversal_module_contains_no_direct_or_destructive_sql() -> None:
    source = inspect.getsource(risk_reversal_proxy).lower()

    assert "pg8000" not in source
    assert "_create_unverified_context" not in source
    assert "disable trigger" not in source
    assert "update signals" not in source
    assert "update regime_calls" not in source
    assert ".run(" not in source
