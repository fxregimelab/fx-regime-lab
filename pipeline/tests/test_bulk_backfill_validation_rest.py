"""Tests for VR1: validation REST backfill repair + rescore audit.

Covers:
- ``_bulk_backfill_validation_rest._load_prices`` pair filtering (pagination).
- ``_bulk_backfill_validation_rest._get_spot`` causal backward-only resolution.
- ``_bulk_backfill_validation_rest._build_rows`` canonical scorer wiring and
  ``as_of`` gating for future horizons.
- ``audit_validation_rescore`` pure classification against synthetic rows.

All tests use a fake Supabase client via monkeypatch — no network, no DB.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

import pytest

from scripts._bulk_backfill_validation_rest import _build_rows, _get_spot, _load_prices
from scripts.audit_validation_rescore import (
    HorizonRecompute,
    build_report,
    classify_row,
    recompute_horizons,
)
from src.db import writer
from src.validation.calculator import (
    HorizonMetrics,
    compute_horizon_metrics,
    horizon_metrics_to_payload,
)
from src.validation.calendar import add_trading_days


class FakeResult:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


def _norm(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _matches_or(expression: str, row: dict[str, Any]) -> bool:
    for term in expression.split(","):
        parts = term.strip().split(".")
        if len(parts) != 3:
            continue
        column, op, value = parts
        if op == "is" and value == "null" and row.get(column) is None:
            return True
        if op == "eq" and _norm(row.get(column)) == value:
            return True
    return False


class FakeQuery:
    def __init__(
        self, table: str, rows: list[dict[str, Any]], log: list[dict[str, Any]]
    ) -> None:
        self._table = table
        self._rows = rows
        self._log = log
        self._select: str | None = None
        self._eq: list[tuple[str, Any]] = []
        self._or: str | None = None
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None

    def select(self, columns: str) -> FakeQuery:
        self._select = columns
        return self

    def eq(self, column: str, value: Any) -> FakeQuery:
        self._eq.append((column, value))
        return self

    def or_(self, expression: str) -> FakeQuery:
        self._or = expression
        return self

    def order(self, column: str, desc: bool = False) -> FakeQuery:
        self._order = (column, desc)
        return self

    def range(self, start: int, end: int) -> FakeQuery:
        self._range = (start, end)
        return self

    def execute(self) -> FakeResult:
        self._log.append(
            {
                "table": self._table,
                "select": self._select,
                "eq": list(self._eq),
                "or": self._or,
                "order": self._order,
                "range": self._range,
            }
        )
        rows = [dict(row) for row in self._rows]
        for column, value in self._eq:
            rows = [row for row in rows if _norm(row.get(column)) == _norm(value)]
        if self._or is not None:
            rows = [row for row in rows if _matches_or(self._or, row)]
        if self._order is not None:
            column, desc = self._order
            rows.sort(key=lambda row: _norm(row.get(column)), reverse=desc)
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        return FakeResult(rows)


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict[str, Any]]]) -> None:
        self._tables = tables
        self.queries: list[dict[str, Any]] = []

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(name, self._tables.get(name, []), self.queries)


def _install_fake(
    monkeypatch: pytest.MonkeyPatch, tables: dict[str, list[dict[str, Any]]]
) -> FakeSupabase:
    fake = FakeSupabase(tables)
    monkeypatch.setattr(writer, "_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# _load_prices / _get_spot
# ---------------------------------------------------------------------------


def test_load_prices_filters_by_pair_and_paginates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = date(2024, 1, 1)
    eurusd_rows = [
        {
            "pair": "EURUSD",
            "date": (base + timedelta(days=i)).isoformat(),
            "close": 1.0 + i / 10000.0,
        }
        for i in range(1001)
    ]
    shared_date = date(2027, 1, 15)
    eurusd_rows.append({"pair": "EURUSD", "date": shared_date.isoformat(), "close": 1.5})
    usdjpy_rows = [{"pair": "USDJPY", "date": shared_date.isoformat(), "close": 150.0}]
    usdinr_rows = [{"pair": "USDINR", "date": shared_date.isoformat(), "close": 83.0}]
    fake = _install_fake(
        monkeypatch,
        {
            "historical_prices": [*eurusd_rows, *usdjpy_rows, *usdinr_rows],
        },
    )

    prices = _load_prices()

    assert len(prices["EURUSD"]) == 1002
    assert prices["EURUSD"][base] == 1.0
    assert prices["EURUSD"][base + timedelta(days=1000)] == 1.0 + 1000 / 10000.0
    # Same date, three pairs: each series must keep its own close only.
    assert prices["EURUSD"][shared_date] == 1.5
    assert prices["USDJPY"] == {shared_date: 150.0}
    assert prices["USDINR"] == {shared_date: 83.0}

    queries = [q for q in fake.queries if q["table"] == "historical_prices"]
    assert len(queries) == 4  # EURUSD 1002 rows -> 2 pages, others 1 page each
    assert {q["eq"][0][1] for q in queries} == {"EURUSD", "USDJPY", "USDINR"}
    assert all(q["eq"] == [("pair", q["eq"][0][1])] for q in queries)


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
    prices = {target - timedelta(days=30): 1.100}
    assert _get_spot(prices, target) is None


# ---------------------------------------------------------------------------
# _build_rows
# ---------------------------------------------------------------------------


def _make_call(pair: str, call_date: date, **overrides: Any) -> dict[str, Any]:
    call: dict[str, Any] = {
        "id": 7,
        "pair": pair,
        "date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
        "regime": "USD_WEAKNESS",
        "strategy_version": "v2",
        "data_source": "live",
    }
    call.update(overrides)
    return call


def test_build_rows_matches_canonical_calculator() -> None:
    call_date = date(2026, 6, 1)
    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)
    prices = {"EURUSD": {call_date: 1.1000, t5_date: 1.1050, t20_date: 1.1100}}
    calls = [_make_call("EURUSD", call_date)]

    rows = _build_rows(calls, prices, as_of=date(2026, 10, 1))

    assert len(rows) == 1
    row = rows[0]
    m5 = compute_horizon_metrics(1.1000, 1.1050, "BULLISH", 0.6, "EURUSD")
    m20 = compute_horizon_metrics(1.1000, 1.1100, "BULLISH", 0.6, "EURUSD")
    assert m5 is not None and m20 is not None
    expected = horizon_metrics_to_payload(m5, "t5")
    expected.update(horizon_metrics_to_payload(m20, "t20"))
    for key, value in expected.items():
        assert row[key] == value, key
    assert row["pair"] == "EURUSD"
    assert row["call_date"] == call_date.isoformat()
    assert row["is_superseded"] is False


def test_build_rows_keeps_t5_when_t20_not_due() -> None:
    call_date = date(2026, 6, 1)
    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)
    prices = {"EURUSD": {call_date: 1.1000, t5_date: 1.1050, t20_date: 1.1100}}
    calls = [_make_call("EURUSD", call_date)]

    rows = _build_rows(calls, prices, as_of=t5_date)

    assert len(rows) == 1
    assert "log_return_t5_bps" in rows[0]
    assert "log_return_t20_bps" not in rows[0]
    assert "brier_score_t20" not in rows[0]


def test_build_rows_omits_row_when_no_horizon_due() -> None:
    call_date = date(2026, 6, 1)
    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)
    prices = {"EURUSD": {call_date: 1.1000, t5_date: 1.1050, t20_date: 1.1100}}
    calls = [_make_call("EURUSD", call_date)]

    rows = _build_rows(calls, prices, as_of=call_date)

    assert rows == []


# ---------------------------------------------------------------------------
# classify_row / recompute_horizons (pure)
# ---------------------------------------------------------------------------


def _hm(s0: float, sh: float, predicted: str, confidence: float, pair: str) -> HorizonMetrics:
    metrics = compute_horizon_metrics(s0, sh, predicted, confidence, pair)
    assert metrics is not None
    return metrics


def _stored_row(m5: HorizonMetrics, m20: HorizonMetrics, **overrides: Any) -> dict[str, Any]:
    stored: dict[str, Any] = {
        "id": 1,
        "pair": "EURUSD",
        "call_date": "2026-06-01",
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
    }
    for horizon, metrics in (("t5", m5), ("t20", m20)):
        stored[f"log_return_{horizon}_bps"] = metrics.log_return_bps
        stored[f"correct_{horizon}"] = metrics.correct
        stored[f"brier_score_{horizon}"] = metrics.brier_score
        stored[f"log_return_net_bps_{horizon}"] = metrics.log_return_net_bps
        stored[f"correct_net_{horizon}"] = metrics.correct_net
        stored[f"cost_bps_{horizon}"] = metrics.cost_bps
    stored.update(overrides)
    return stored


def _clean_case() -> tuple[dict[str, Any], dict[str, HorizonRecompute]]:
    m5 = _hm(1.1000, 1.1050, "BULLISH", 0.6, "EURUSD")
    m20 = _hm(1.1000, 1.1100, "BULLISH", 0.6, "EURUSD")
    stored = _stored_row(m5, m20)
    recomputed = {"t5": HorizonRecompute(m5), "t20": HorizonRecompute(m20)}
    return stored, recomputed


def test_classify_row_clean_has_no_categories() -> None:
    stored, recomputed = _clean_case()
    entry = classify_row(stored, recomputed)
    assert entry.categories == ()
    assert entry.worst_abs_gross_diff_bps == 0.0


def test_classify_row_detects_cross_pair_corrupt() -> None:
    stored, recomputed = _clean_case()
    stored["log_return_t5_bps"] = -5057.66221363934
    stored["log_return_net_bps_t5"] = -5057.66221363934 - 0.2
    entry = classify_row(stored, recomputed)
    assert "cross_pair_corrupt" in entry.categories
    assert "net_mismatch" in entry.categories
    assert entry.worst_abs_gross_diff_bps > 2000.0


def test_classify_row_detects_flag_mismatch() -> None:
    stored, recomputed = _clean_case()
    stored["correct_t5"] = not cast(bool, stored["correct_t5"])
    entry = classify_row(stored, recomputed)
    assert entry.categories == ("flag_mismatch",)


def test_classify_row_detects_net_mismatch() -> None:
    stored, recomputed = _clean_case()
    stored["log_return_net_bps_t5"] = cast(float, stored["log_return_net_bps_t5"]) + 10.0
    entry = classify_row(stored, recomputed)
    assert entry.categories == ("net_mismatch",)


def test_classify_row_detects_brier_mismatch() -> None:
    stored, recomputed = _clean_case()
    stored["brier_score_t5"] = cast(float, stored["brier_score_t5"]) + 0.1
    entry = classify_row(stored, recomputed)
    assert entry.categories == ("brier_mismatch",)


def test_classify_row_detects_cost_mismatch() -> None:
    stored, recomputed = _clean_case()
    stored["cost_bps_t5"] = cast(float, stored["cost_bps_t5"]) + 1.0
    entry = classify_row(stored, recomputed)
    assert entry.categories == ("cost_mismatch",)


def test_classify_row_detects_no_prices() -> None:
    stored, _ = _clean_case()
    recomputed = {"t5": HorizonRecompute(metrics=None), "t20": HorizonRecompute(metrics=None)}
    entry = classify_row(stored, recomputed)
    assert entry.categories == ("no_prices",)


def test_classify_row_skips_not_due_horizon() -> None:
    stored, recomputed = _clean_case()
    recomputed["t20"] = HorizonRecompute(metrics=None, not_due=True)
    entry = classify_row(stored, recomputed)
    assert entry.categories == ()


def test_classify_row_skips_flags_when_prediction_missing() -> None:
    stored, recomputed = _clean_case()
    del stored["predicted_direction"]
    stored["correct_t5"] = not cast(bool, stored["correct_t5"])
    stored["brier_score_t5"] = cast(float, stored["brier_score_t5"]) + 0.2
    entry = classify_row(stored, recomputed)
    assert entry.categories == ()


def test_classify_row_ignores_unscored_horizons() -> None:
    stored: dict[str, Any] = {"id": 9, "pair": "EURUSD", "predicted_direction": "BULLISH"}
    m5 = _hm(1.1000, 1.1050, "BULLISH", 0.6, "EURUSD")
    entry = classify_row(stored, {"t5": HorizonRecompute(m5), "t20": HorizonRecompute(None)})
    assert entry.categories == ()
    assert entry.diffs == ()


def test_recompute_horizons_ignores_future_prices() -> None:
    call_date = date(2026, 6, 29)
    t5_date = add_trading_days(call_date, 5)
    prices = {call_date: 1.1, t5_date + timedelta(days=1): 1.3}
    stored: dict[str, Any] = {
        "pair": "EURUSD",
        "call_date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.5,
    }

    out = recompute_horizons(stored, prices, as_of=date(2026, 12, 1))

    metrics = out["t5"].metrics
    assert metrics is not None
    # Backward fill used the call-date spot (0 bps), not the +1-day future price.
    assert metrics.log_return_bps == 0.0
    # T+20 target is beyond both the 9-day backfill window and any observation.
    assert out["t20"].metrics is None


# ---------------------------------------------------------------------------
# audit end-to-end (fake client)
# ---------------------------------------------------------------------------


def test_audit_build_report_with_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    call_date = date(2026, 6, 1)
    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)

    m5 = _hm(1.1000, 1.1050, "BULLISH", 0.6, "EURUSD")
    m20 = _hm(1.1000, 1.1100, "BULLISH", 0.6, "EURUSD")
    clean: dict[str, Any] = {
        "id": 1,
        "pair": "EURUSD",
        "call_date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
        "is_superseded": False,
    }
    clean.update(horizon_metrics_to_payload(m5, "t5"))
    clean.update(horizon_metrics_to_payload(m20, "t20"))

    corrupt: dict[str, Any] = {
        "id": 2,
        "pair": "USDINR",
        "call_date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.5,
        "is_superseded": False,
        "log_return_t5_bps": -5057.66221363934,
        "correct_t5": True,
        "brier_score_t5": 0.25,
        "log_return_net_bps_t5": -5067.66221363934,
        "correct_net_t5": False,
        "cost_bps_t5": 10.0,
    }
    superseded: dict[str, Any] = {
        "id": 3,
        "pair": "EURUSD",
        "call_date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
        "is_superseded": True,
        "log_return_t5_bps": -5057.66221363934,
    }
    unscored: dict[str, Any] = {
        "id": 4,
        "pair": "EURUSD",
        "call_date": call_date.isoformat(),
        "predicted_direction": "BULLISH",
        "confidence": 0.6,
        "is_superseded": False,
    }

    _install_fake(
        monkeypatch,
        {
            "historical_prices": [
                {"pair": "EURUSD", "date": call_date.isoformat(), "close": 1.1000},
                {"pair": "EURUSD", "date": t5_date.isoformat(), "close": 1.1050},
                {"pair": "EURUSD", "date": t20_date.isoformat(), "close": 1.1100},
                {"pair": "USDINR", "date": call_date.isoformat(), "close": 83.0},
                {"pair": "USDINR", "date": t5_date.isoformat(), "close": 83.5},
                {"pair": "USDINR", "date": t20_date.isoformat(), "close": 84.0},
            ],
            "validation_log": [clean, corrupt, superseded, unscored],
            "regime_calls": [],
        },
    )

    report = build_report(date(2026, 10, 1))

    assert report["read_only"] is True
    assert report["rows_loaded_non_superseded"] == 3
    assert report["rows_checked_scored"] == 2
    assert report["rows_unscored"] == 1
    assert report["rows_with_issues"] == 1
    assert report["category_counts"]["cross_pair_corrupt"] == 1
    assert report["category_counts"]["net_mismatch"] == 1
    assert report["category_counts"]["flag_mismatch"] == 0
    assert report["category_counts"]["no_prices"] == 0
    assert report["worst"][0]["row_id"] == 2
    assert report["price_coverage_end"]["EURUSD"] == t20_date.isoformat()
