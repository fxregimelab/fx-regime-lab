"""LRH: live rate z-history consistency — carry/structural histories rebuilt from yields.

The live MAD-z compares the current-day pair spread against a history. Before this fix
the history came from stored ``signals`` rows whose recon era holds a different quantity
(raw US 2Y level). These tests pin the new helpers to the *same definition* as the
current-day inputs, causally forward-filled from canonical yield history.
No network, no DB.
"""

from __future__ import annotations

import datetime
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.db import writer as db_writer
from src.scheduler import orchestrator as orch
from src.signals.rate import (
    CARRY_LOOKBACK_DAYS,
    build_carry_history_from_yields,
    build_real_yield_10y_spread_history_from_yields,
    compute_risk_adjusted_carry,
    realized_vol_by_date_from_rows,
)

D = datetime.date


def _dates(start: str, n: int) -> list[datetime.date]:
    base = datetime.date.fromisoformat(start)
    return [base + datetime.timedelta(days=i) for i in range(n)]


def _carry(spread: float, vol: float) -> float:
    value = compute_risk_adjusted_carry(spread, vol, "TESTPAIR")
    assert value is not None
    return value


# ── Carry history: definition parity ─────────────────────────────────────────


def test_carry_history_last_value_matches_same_day_spread_definition() -> None:
    days = _dates("2026-01-05", 5)
    dgs2 = {d: 4.0 + 0.1 * i for i, d in enumerate(days)}
    ecb = {d: 2.0 + 0.05 * i for i, d in enumerate(days)}
    vols = {d: 10.0 + i for i, d in enumerate(days)}

    hist = build_carry_history_from_yields(
        {"DGS2": dgs2, "ECBDFR": ecb},
        base_series="DGS2",
        quote_series="ECBDFR",
        vol_by_date=vols,
    )

    assert hist is not None
    expected = [_carry(dgs2[d] - ecb[d], vols[d]) for d in days]
    assert hist == pytest.approx(expected)
    # Last point equals the same-day spread construction (EURO carry definition).
    assert hist[-1] == pytest.approx(
        _carry(dgs2[days[-1]] - ecb[days[-1]], vols[days[-1]])
    )


def test_carry_history_oldest_first_and_trimmed_to_max_points() -> None:
    days = _dates("2026-01-05", 6)
    dgs2 = {d: 4.0 + i for i, d in enumerate(days)}
    quote = {d: 1.0 for d in days}
    vols = {d: 10.0 for d in days}

    hist = build_carry_history_from_yields(
        {"DGS2": dgs2, "IRLTLT01JPM156N": quote},
        base_series="DGS2",
        quote_series="IRLTLT01JPM156N",
        vol_by_date=vols,
        max_points=3,
    )
    assert hist is not None
    assert hist == pytest.approx([(4.0 + i - 1.0) / 10.0 for i in (3, 4, 5)])

    # An explicit unsorted/duplicated grid is sorted and deduplicated (oldest-first).
    grid_hist = build_carry_history_from_yields(
        {"DGS2": dgs2, "IRLTLT01JPM156N": quote},
        base_series="DGS2",
        quote_series="IRLTLT01JPM156N",
        vol_by_date=vols,
        date_grid=[days[2], days[0], days[1], days[2]],
    )
    assert grid_hist == pytest.approx([(3.0 + i) / 10.0 for i in range(3)])


# ── Causality: no future leakage ─────────────────────────────────────────────


def test_carry_history_ignores_observations_dated_after_the_grid_date() -> None:
    days = _dates("2026-01-05", 4)
    base = {d: 4.0 for d in days}
    quote = {d: 1.0 for d in days}
    vols = {d: 10.0 for d in days}
    args: dict[str, Any] = {"base_series": "DGS2", "quote_series": "ECBDFR"}
    after = days[-1] + datetime.timedelta(days=1)

    clean = build_carry_history_from_yields(
        {"DGS2": base, "ECBDFR": quote}, vol_by_date=vols, date_grid=days, **args
    )
    assert clean is not None

    # On a fixed grid, observations dated after the last grid date never leak in.
    spiked_series = {"DGS2": {**base, after: 99.0}, "ECBDFR": {**quote, after: 50.0}}
    spiked = build_carry_history_from_yields(
        spiked_series, vol_by_date={**vols, after: 5.0}, date_grid=days, **args
    )
    assert spiked == pytest.approx(clean)

    # With the implicit base-series grid the later point is appended, but every
    # earlier point is unchanged (point-in-time semantics).
    extended = build_carry_history_from_yields(
        spiked_series, vol_by_date={**vols, after: 5.0}, **args
    )
    assert extended is not None
    assert extended[: len(clean)] == pytest.approx(clean)

    # A value dated at d2 changes only points dated d2 and later, never earlier ones.
    mid = build_carry_history_from_yields(
        {"DGS2": {**base, days[2]: 9.0}, "ECBDFR": quote},
        vol_by_date=vols,
        date_grid=days,
        **args,
    )
    assert mid is not None
    assert mid[:2] == pytest.approx(clean[:2])
    assert mid[2] > clean[2]


def test_monthly_quote_leg_forward_fills_causally_without_future_leakage() -> None:
    grid = _dates("2026-01-10", 1) + _dates("2026-01-20", 1) + _dates("2026-01-31", 1)
    grid += _dates("2026-02-10", 1)
    base = {d: 4.0 for d in grid}
    quote = {D(2026, 1, 1): 1.0, D(2026, 2, 1): 3.0}
    vols = {d: 10.0 for d in grid}

    hist = build_carry_history_from_yields(
        {"DGS2": base, "IRLTLT01JPM156N": quote},
        base_series="DGS2",
        quote_series="IRLTLT01JPM156N",
        vol_by_date=vols,
    )
    assert hist is not None
    # January dates resolve to the last observation ≤ date (Jan 1); Feb 10 to Feb 1.
    assert hist == pytest.approx([(4.0 - 1.0) / 10.0] * 3 + [(4.0 - 3.0) / 10.0])


def test_carry_history_skips_dates_without_realized_vol() -> None:
    days = _dates("2026-01-05", 4)
    dgs2 = {d: 5.0 for d in days}
    quote = {d: 1.0 for d in days}
    vols = {days[0]: 10.0, days[2]: 20.0}  # days 1 and 3 have no vol observation

    hist = build_carry_history_from_yields(
        {"DGS2": dgs2, "INDIRLTLT01STM": quote},
        base_series="DGS2",
        quote_series="INDIRLTLT01STM",
        vol_by_date=vols,
    )
    assert hist == pytest.approx([(5.0 - 1.0) / 10.0, (5.0 - 1.0) / 20.0])


# ── Structural history: definition parity and forward-fill ───────────────────


def test_structural_history_last_value_matches_same_day_definition() -> None:
    days = _dates("2026-01-05", 5)
    dgs10 = {d: 4.0 + 0.05 * i for i, d in enumerate(days)}
    bei = {d: 2.4 for d in days}
    quote = {d: 1.5 for d in days}

    hist = build_real_yield_10y_spread_history_from_yields(
        {"DGS10": dgs10, "T10YIE": bei, "IRLTLT01DEM156N": quote},
        quote_series="IRLTLT01DEM156N",
    )
    assert hist is not None
    expected = [(dgs10[d] - 1.5) - 2.4 for d in days]
    assert hist == pytest.approx(expected)
    assert hist[-1] == pytest.approx((dgs10[days[-1]] - 1.5) - 2.4)


def test_structural_history_forward_fills_causally_without_future_leakage() -> None:
    grid = _dates("2026-01-10", 1) + _dates("2026-01-31", 1) + _dates("2026-02-10", 1)
    base = {d: 4.0 for d in grid}
    bei = {d: 2.0 for d in grid}
    quote = {D(2026, 1, 1): 1.0, D(2026, 2, 1): 3.0}

    hist = build_real_yield_10y_spread_history_from_yields(
        {"DGS10": base, "T10YIE": bei, "INDIRLTLT01STM": quote},
        quote_series="INDIRLTLT01STM",
    )
    assert hist is not None
    assert hist == pytest.approx([(4.0 - 1.0) - 2.0, (4.0 - 1.0) - 2.0, (4.0 - 3.0) - 2.0])


# ── Degradation path ─────────────────────────────────────────────────────────


def test_carry_history_none_and_warns_when_quote_series_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    days = _dates("2026-01-05", 3)
    with caplog.at_level(logging.WARNING, logger="src.signals.rate"):
        hist = build_carry_history_from_yields(
            {"DGS2": {d: 4.0 for d in days}},
            base_series="DGS2",
            quote_series="ECBDFR",
            vol_by_date={d: 10.0 for d in days},
        )
    assert hist is None
    assert "ECBDFR" in caplog.text


def test_carry_history_none_and_warns_when_vol_history_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    days = _dates("2026-01-05", 3)
    with caplog.at_level(logging.WARNING, logger="src.signals.rate"):
        hist = build_carry_history_from_yields(
            {"DGS2": {d: 4.0 for d in days}, "ECBDFR": {d: 2.0 for d in days}},
            base_series="DGS2",
            quote_series="ECBDFR",
            vol_by_date={},
        )
    assert hist is None
    assert "vol history" in caplog.text


def test_structural_history_none_and_warns_when_breakeven_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    days = _dates("2026-01-05", 3)
    with caplog.at_level(logging.WARNING, logger="src.signals.rate"):
        hist = build_real_yield_10y_spread_history_from_yields(
            {"DGS10": {d: 4.0 for d in days}, "IRLTLT01DEM156N": {d: 1.0 for d in days}},
            quote_series="IRLTLT01DEM156N",
        )
    assert hist is None
    assert "T10YIE" in caplog.text


def test_realized_vol_by_date_from_rows_filters_invalid_rows() -> None:
    rows: list[dict[str, Any]] = [
        {"date": "2026-01-05", "realized_vol_20d": 12.5},
        {"date": "2026-01-06", "realized_vol_20d": None},
        {"date": "2026-01-07", "realized_vol_20d": 0.0},
        {"date": "not-a-date", "realized_vol_20d": 5.0},
        {"date": "2026-01-08", "realized_vol_20d": 8},
    ]
    assert realized_vol_by_date_from_rows(rows) == {
        D(2026, 1, 5): 12.5,
        D(2026, 1, 8): 8.0,
    }


# ── Orchestrator wiring (monkeypatched; no DB) ───────────────────────────────


def _fake_pair_context() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    universe: dict[str, Any] = {
        "EURUSD": {"tickers": {"yield_base": "DGS2", "yield_quote": "ECBDFR"}}
    }
    rows: list[dict[str, Any]] = [
        {"date": "2026-01-05", "realized_vol_20d": 10.0},
        {"date": "2026-01-06", "realized_vol_20d": None},
    ]
    return universe, rows


def test_pair_histories_use_canonical_yield_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, dict[str, object]] = {}

    def fake_carry(yields_by_series: object, **kwargs: object) -> list[float]:
        captured["carry"] = kwargs
        captured["carry"]["yields_by_series"] = yields_by_series
        return [0.25]

    def fake_real(yields_by_series: object, **kwargs: object) -> list[float]:
        captured["real"] = kwargs
        return [1.5]

    legacy_carry = MagicMock(return_value=[-0.1])
    legacy_real = MagicMock(return_value=[-0.2])
    monkeypatch.setattr(orch, "build_carry_history_from_yields", fake_carry)
    monkeypatch.setattr(orch, "build_real_yield_10y_spread_history_from_yields", fake_real)
    monkeypatch.setattr(orch, "build_carry_history_from_rows", legacy_carry)
    monkeypatch.setattr(orch, "build_real_yield_10y_spread_history_from_rows", legacy_real)

    universe, rows = _fake_pair_context()
    yields_by_series: dict[str, dict[datetime.date, float]] = {"DGS2": {}, "ECBDFR": {}}
    carry, real = orch._build_rate_histories_for_pair(
        "EURUSD",
        universe=universe,
        historical_rows=rows,
        yields_by_series=yields_by_series,
        max_points=100,
    )

    assert carry == [0.25]
    assert real == [1.5]
    assert captured["carry"]["base_series"] == "DGS2"
    assert captured["carry"]["quote_series"] == "ECBDFR"
    assert captured["carry"]["max_points"] == 100
    assert captured["carry"]["vol_by_date"] == {D(2026, 1, 5): 10.0}
    assert captured["carry"]["yields_by_series"] == yields_by_series
    assert captured["real"]["quote_series"] == "IRLTLT01DEM156N"
    legacy_carry.assert_not_called()
    legacy_real.assert_not_called()


def test_pair_histories_fall_back_to_rows_when_canonical_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(orch, "build_carry_history_from_yields", lambda *a, **k: None)
    monkeypatch.setattr(
        orch, "build_real_yield_10y_spread_history_from_yields", lambda *a, **k: None
    )
    legacy_carry = MagicMock(return_value=[-0.1])
    legacy_real = MagicMock(return_value=[-0.2])
    monkeypatch.setattr(orch, "build_carry_history_from_rows", legacy_carry)
    monkeypatch.setattr(orch, "build_real_yield_10y_spread_history_from_rows", legacy_real)

    universe, rows = _fake_pair_context()
    with caplog.at_level(logging.WARNING, logger="src.scheduler.orchestrator"):
        carry, real = orch._build_rate_histories_for_pair(
            "EURUSD",
            universe=universe,
            historical_rows=rows,
            yields_by_series={},
            max_points=2520,
        )

    assert carry == [-0.1]
    assert real == [-0.2]
    legacy_carry.assert_called_once_with(rows, max_points=2520)
    legacy_real.assert_called_once_with(rows, max_points=2520)
    assert "falling back to stored signal rows" in caplog.text


def test_pair_histories_fall_back_when_universe_tickers_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_carry = MagicMock(return_value=[0.25])
    monkeypatch.setattr(orch, "build_carry_history_from_yields", canonical_carry)
    monkeypatch.setattr(
        orch, "build_real_yield_10y_spread_history_from_yields", lambda *a, **k: [1.5]
    )
    legacy_carry = MagicMock(return_value=[-0.1])
    monkeypatch.setattr(orch, "build_carry_history_from_rows", legacy_carry)

    _, rows = _fake_pair_context()
    carry, _ = orch._build_rate_histories_for_pair(
        "EURUSD",
        universe={},  # universe row missing → no 2Y tickers
        historical_rows=rows,
        yields_by_series={},
        max_points=2520,
    )

    assert carry == [-0.1]
    canonical_carry.assert_not_called()
    legacy_carry.assert_called_once_with(rows, max_points=2520)


def test_load_rate_history_yields_parses_rows_and_ignores_invalid_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {"series_id": "DGS2", "date": "2026-01-05", "value": 4.25},
        {"series_id": "DGS2", "date": "2026-01-06", "value": None},
        {"series_id": "ECBDFR", "date": "not-a-date", "value": 1.0},
        {"series_id": None, "date": "2026-01-07", "value": 2.0},
    ]
    client = MagicMock()
    select = client.table.return_value.select.return_value
    chain = select.gte.return_value
    chain.order.return_value.order.return_value.range.return_value.execute.return_value = (
        SimpleNamespace(data=rows)
    )
    monkeypatch.setattr(db_writer, "_client", lambda: client)

    out = orch._load_rate_history_yields(start=D(2014, 1, 1))

    assert out == {"DGS2": {D(2026, 1, 5): 4.25}}
    client.table.assert_called_once_with("historical_yields")
    select.gte.assert_called_once_with("date", "2014-01-01")
    chain.order.return_value.order.return_value.range.assert_called_once_with(0, 999)


def test_load_rate_history_yields_paginates_until_short_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_day = D(2026, 1, 1)
    page_one = [
        {
            "series_id": "DGS2",
            "date": (first_day + datetime.timedelta(days=i)).isoformat(),
            "value": float(i),
        }
        for i in range(1000)
    ]
    page_two = [{"series_id": "DGS2", "date": "2030-01-01", "value": 7.0}]
    client = MagicMock()
    execute = (
        client.table.return_value.select.return_value.order.return_value.order.return_value.range
        .return_value.execute
    )
    execute.side_effect = [SimpleNamespace(data=page_one), SimpleNamespace(data=page_two)]
    monkeypatch.setattr(db_writer, "_client", lambda: client)

    out = orch._load_rate_history_yields()

    assert out["DGS2"][first_day] == 0.0
    assert out["DGS2"][D(2030, 1, 1)] == 7.0
    ranges = (
        client.table.return_value.select.return_value.order.return_value.order.return_value.range
    )
    assert [c.args for c in ranges.call_args_list] == [(0, 999), (1000, 1999)]


def test_load_rate_history_yields_degrades_on_read_failure(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _boom() -> object:
        raise RuntimeError("no supabase in this environment")

    monkeypatch.setattr(db_writer, "_client", _boom)
    with caplog.at_level(logging.WARNING, logger="src.scheduler.orchestrator"):
        out = orch._load_rate_history_yields()
    assert out == {}
    assert "read failed" in caplog.text


def test_carry_lookback_contract_unchanged() -> None:
    """History contracts still trim to the same lookback used by normalize_rate_signal."""

    assert CARRY_LOOKBACK_DAYS == 2520
