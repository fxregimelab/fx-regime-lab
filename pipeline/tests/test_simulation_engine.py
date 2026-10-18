"""Fidelity tests for the v2 walk-forward simulation engine (RF2).

The v2 replay must mirror the live orchestrator's signal construction:

- COT percentile and smart-spread percentile are computed from canonical
  ``historical_cot`` rows on the causal slice (``date <= as_of``).
- Open-interest percentile / delta are computed from those same COT rows.
- Dynamic betas are fed raw ``writer.get_historical_signals``-shaped dicts
  with real ``date`` and ``spot`` values — no pre-normalized families and no
  invented ``special`` family.

Fixtures use business-day-spaced synthetic bars long enough (>=130 sessions)
that ``simulate_all_days_v2`` produces calls instead of skipping every day.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

from src.backfill import simulation_engine
from src.backfill.simulation_engine import (
    simulate_all_days,
    simulate_all_days_v2,
)
from src.fetchers.open_interest import (
    compute_oi_delta_from_cot,
    compute_oi_from_cot,
)
from src.regime.composite import compute_dynamic_betas
from src.signals.cot import (
    compute_cot_percentile,
    compute_cot_smart_spread_percentile,
)
from src.types import CotRow, SpotBar

START = date(2024, 1, 1)
N_BARS = 150
# `simulate_all_days_v2` skips every bar with full_idx < 60.
START_INDEX = 60


def _business_days(start: date, n: int) -> list[date]:
    days: list[date] = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _make_spot_bars(days: list[date]) -> dict[date, SpotBar]:
    """Deterministic wave-shaped synthetic path (always positive)."""
    out: dict[date, SpotBar] = {}
    for i, d in enumerate(days):
        price = 100.0 + 8.0 * math.sin(i / 9.0) + 0.02 * i
        out[d] = SpotBar(
            date=d,
            pair="EURUSD",
            open=price - 0.05,
            high=price + 0.05,
            low=price - 0.05,
            close=price,
            volume=1000.0,
        )
    return out


def _make_yields(days: list[date]) -> dict[str, dict[date, float]]:
    """Slightly drifting yield curves so MAD normalization is well-defined."""
    yields: dict[str, dict[date, float]] = {
        "DGS2": {},
        "DGS10": {},
        "IRLTLT01DEM156N": {},
        "T10YIE": {},
    }
    for i, d in enumerate(days):
        yields["DGS2"][d] = 4.0 + 0.002 * i
        yields["DGS10"][d] = 4.5 + 0.002 * i
        yields["IRLTLT01DEM156N"][d] = 2.5 - 0.001 * i
        yields["T10YIE"][d] = 2.0 + 0.0005 * i
    return yields


def _make_signals(days: list[date]) -> dict[date, dict[str, Any]]:
    out: dict[date, dict[str, Any]] = {}
    for i, d in enumerate(days):
        out[d] = {
            "rate_diff_2y": 1.0 + 0.001 * i,
            "cot_percentile": 55.0,
            "realized_vol_5d": 8.0 + float(i % 3),
            "realized_vol_20d": 8.5,
            "implied_vol_30d": 10.0,
            "oi_delta": 100 + (i % 7),
            "rate_z_tactical": 0.3,
            "rate_z_structural": 0.2,
            "cross_asset_vix": 15.0,
            "cross_asset_dxy": 100.0,
            "cross_asset_oil": 70.0,
            "cross_asset_gold": 1800.0,
            "cross_asset_copper": 4.0,
            "cross_asset_stoxx": 4000.0,
            "bund_btp_spread": -1.5,
            "ecb_balance_sheet": 7000.0,
        }
    return out


def _make_cot_reports(days: list[date]) -> dict[str, list[CotRow]]:
    """Known EURUSD COT reports: one every 5th business day, ascending."""
    rows = [
        CotRow(
            date=d,
            pair="EURUSD",
            net_long=10_000 + 400 * i,
            open_interest=200_000 + 2_000 * i,
            asset_mgr_net=8_000 + 300 * i,
            lev_money_net=-3_000 + 500 * i,
        )
        for i, d in enumerate(days[::5])
    ]
    return {"EURUSD": rows}


def test_simulation_v2_exact_count_and_provenance() -> None:
    """The v2 run covers every non-skipped bar and stamps M.3 provenance."""
    days = _business_days(START, N_BARS)
    spots = _make_spot_bars(days)
    yields = _make_yields(days)
    signals = _make_signals(days)
    cot_reports = _make_cot_reports(days)

    with (
        patch.object(simulation_engine, "_load_all_spot_bars", return_value=spots),
        patch.object(simulation_engine, "_load_signals_for_pair", return_value=signals),
        patch.object(simulation_engine, "_load_historical_cot", return_value=cot_reports),
    ):
        results = simulate_all_days_v2("EURUSD", days[0], days[-1], yields)

    assert len(results) == N_BARS - START_INDEX
    assert [signal_row.date for signal_row, _call in results] == days[START_INDEX:]
    for signal_row, call in results:
        assert call.date == signal_row.date
        assert call.model_version == "2.1-m3"
        assert call.data_source == "backtest"
        assert call.regime_category is not None and call.regime_category != ""


def test_simulation_v2_cot_and_oi_come_from_historical_cot_rows() -> None:
    """COT/OI are recomputed from the canonical COT rows on the causal slice."""
    days = _business_days(START, N_BARS)
    spots = _make_spot_bars(days)
    yields = _make_yields(days)
    signals = _make_signals(days)
    cot_reports = _make_cot_reports(days)
    known_rows = cot_reports["EURUSD"]
    known_ids = {id(row) for row in known_rows}

    with (
        patch.object(simulation_engine, "_load_all_spot_bars", return_value=spots),
        patch.object(simulation_engine, "_load_signals_for_pair", return_value=signals),
        patch.object(simulation_engine, "_load_historical_cot", return_value=cot_reports),
        patch(
            "src.backfill.simulation_engine.compute_cot_smart_spread_percentile",
            wraps=compute_cot_smart_spread_percentile,
        ) as smart_spy,
        patch(
            "src.backfill.simulation_engine.compute_oi_from_cot",
            wraps=compute_oi_from_cot,
        ) as oi_pct_spy,
        patch(
            "src.backfill.simulation_engine.compute_oi_delta_from_cot",
            wraps=compute_oi_delta_from_cot,
        ) as oi_delta_spy,
    ):
        results = simulate_all_days_v2("EURUSD", days[0], days[-1], yields)

    assert len(results) == N_BARS - START_INDEX

    # 1) Smart-spread path runs on >=2 causal reports with as_of set.
    assert smart_spy.call_count == len(results)
    assert any(
        len(call.args[0]) >= 2 and call.kwargs.get("as_of") is not None
        for call in smart_spy.call_args_list
    )
    for (signal_row, _call), spy_call in zip(results, smart_spy.call_args_list, strict=True):
        rows = spy_call.args[0]
        assert spy_call.args[1] == "EURUSD"
        assert spy_call.kwargs["as_of"] == signal_row.date
        assert all(row.date <= signal_row.date for row in rows)

    # 2) OI helpers receive the real (identity-checked) COT rows, causally sliced.
    assert oi_pct_spy.call_count == len(results)
    assert oi_delta_spy.call_count == len(results)
    for spy in (oi_pct_spy, oi_delta_spy):
        for spy_call in spy.call_args_list:
            rows = spy_call.args[0]
            assert rows
            assert spy_call.args[1] == "EURUSD"
            assert all(id(row) in known_ids for row in rows)
    for (signal_row, _call), spy_call in zip(results, oi_pct_spy.call_args_list, strict=True):
        assert all(row.date <= signal_row.date for row in spy_call.args[0])
    assert any(len(call.args[0]) >= 4 for call in oi_pct_spy.call_args_list)

    # 3) Recomputed COT/OI values are stored on the produced signal rows.
    assert all(signal_row.cot_percentile is not None for signal_row, _call in results)
    assert all(signal_row.oi_delta is not None for signal_row, _call in results)
    last_signal = results[-1][0]
    assert last_signal.cot_percentile == compute_cot_percentile(
        known_rows, "EURUSD", as_of=days[-1]
    )
    assert last_signal.oi_delta == (
        known_rows[-1].open_interest - known_rows[-2].open_interest
    )


def test_simulation_v2_betas_receive_raw_rows_with_date_and_spot() -> None:
    """Betas get raw signal-shaped rows: real date/spot, no invented families."""
    days = _business_days(START, N_BARS)
    spots = _make_spot_bars(days)
    yields = _make_yields(days)
    signals = _make_signals(days)
    cot_reports = _make_cot_reports(days)

    with (
        patch.object(simulation_engine, "_load_all_spot_bars", return_value=spots),
        patch.object(simulation_engine, "_load_signals_for_pair", return_value=signals),
        patch.object(simulation_engine, "_load_historical_cot", return_value=cot_reports),
        patch(
            "src.backfill.simulation_engine.compute_dynamic_betas",
            wraps=compute_dynamic_betas,
        ) as betas_spy,
    ):
        results = simulate_all_days_v2("EURUSD", days[0], days[-1], yields)

    assert len(results) == N_BARS - START_INDEX
    assert betas_spy.call_count == len(results)

    expected_keys = {
        "date",
        "spot",
        "rate_diff_2y",
        "cot_percentile",
        "realized_vol_5d",
        "realized_vol_20d",
        "oi_delta",
    }
    for spy_call in betas_spy.call_args_list:
        rows = spy_call.args[0]
        assert len(rows) >= 30
        for row in rows:
            assert row["date"] is not None
            assert row["spot"] is not None
            assert row["spot"] == spots[row["date"]].close
            # Exact key set: no pre-normalized families, no "special" family.
            assert set(row) == expected_keys

    # Family inputs flow from the raw signal dicts (not pre-normalized values).
    last_rows = betas_spy.call_args_list[-1].args[0]
    assert all(row["rate_diff_2y"] is not None for row in last_rows)
    assert all(row["cot_percentile"] is not None for row in last_rows)
    assert all(row["realized_vol_5d"] is not None for row in last_rows)
    assert all(row["realized_vol_20d"] is not None for row in last_rows)
    assert all(row["oi_delta"] is not None for row in last_rows)


def test_simulation_v1_and_v2_share_coverage_and_output_ranges() -> None:
    """Explicit invariants replacing the old v1-vs-v2 dispersion/accuracy compares.

    Both engines must cover exactly the same simulated dates on identical input,
    and every v2 call must stay inside the documented output ranges.  The old
    tests asserted directionally-comparative outcomes (wider v2 dispersion,
    more v2 directional calls) that no synthetic fixture can guarantee.
    """
    days = _business_days(START, N_BARS)
    spots = _make_spot_bars(days)
    yields = _make_yields(days)
    signals = _make_signals(days)
    cot_reports = _make_cot_reports(days)

    with (
        patch.object(simulation_engine, "_load_all_spot_bars", return_value=spots),
        patch.object(simulation_engine, "_load_signals_for_pair", return_value=signals),
        patch.object(simulation_engine, "_load_historical_cot", return_value=cot_reports),
    ):
        v1_results = simulate_all_days("EURUSD", days[0], days[-1], yields)
        v2_results = simulate_all_days_v2("EURUSD", days[0], days[-1], yields)

    v1_dates = [call.date for _signal_row, call in v1_results]
    v2_dates = [call.date for _signal_row, call in v2_results]
    assert v1_dates == days[START_INDEX:]
    assert v2_dates == days[START_INDEX:]

    for _signal_row, call in v2_results:
        assert call.signal_composite is not None
        assert -2.0 <= float(call.signal_composite) <= 2.0
        assert 0.0 <= float(call.confidence) <= 1.0
        assert call.predicted_direction in {"BULLISH", "BEARISH", "NEUTRAL"}
