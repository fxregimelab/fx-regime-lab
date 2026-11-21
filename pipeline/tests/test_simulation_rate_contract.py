"""Historical simulations must not manufacture unavailable rate features."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from unittest.mock import patch

import pytest

from src.backfill.simulation_engine import (
    _build_historical_snapshot,
    simulate_all_days,
    simulate_all_days_v2,
)
from src.regime.classifier import classify_regime_layer1 as actual_classifier
from src.types import SpotBar


def _spot_bars(pair: str, start: date, count: int) -> dict[date, SpotBar]:
    bars: dict[date, SpotBar] = {}
    for index in range(count):
        as_of = start + timedelta(days=index)
        close = 100.0 + index * 0.1 + (index % 5) * 0.02
        bars[as_of] = SpotBar(
            date=as_of,
            pair=pair,
            open=close - 0.05,
            high=close + 0.1,
            low=close - 0.1,
            close=close,
            volume=1_000.0 + index,
        )
    return bars


def _yield_history(dates: list[date]) -> dict[str, dict[date, float]]:
    levels = {
        "DGS2": 4.0,
        "ECBDFR": 2.0,
        "DGS10": 4.0,
        "IRLTLT01DEM156N": 2.0,
        "IRLTLT01JPM156N": 1.0,
        "INDIRLTLT01STM": 7.0,
        "T10YIE": 2.5,
    }
    return {series: {as_of: value for as_of in dates} for series, value in levels.items()}


@pytest.mark.parametrize(
    ("pair", "foreign_alias", "foreign_yield", "expected_nominal"),
    [("EURUSD", "de_10y", 2.0, -2.0), ("USDJPY", "jp_10y", 1.0, 3.0),
     ("USDINR", "in_10y", 7.0, -3.0)],
)
def test_both_simulations_expose_only_supported_historical_rate_context(
    pair: str,
    foreign_alias: str,
    foreign_yield: float,
    expected_nominal: float,
) -> None:
    start = date(2026, 1, 1)
    bars = _spot_bars(pair, start, 75)
    dates = list(bars)
    yields = _yield_history(dates)
    signals: dict[date, dict[str, Any]] = {as_of: {} for as_of in dates}

    with (
        patch(
            "src.backfill.simulation_engine._load_all_spot_bars",
            return_value=bars,
        ),
        patch(
            "src.backfill.simulation_engine._load_signals_for_pair",
            return_value=signals,
        ) as load_signals,
        patch("src.backfill.simulation_engine.compute_special_signal", return_value=0.4),
        patch(
            "src.backfill.simulation_engine.classify_regime_layer1",
            wraps=actual_classifier,
        ) as classifier,
    ):
        v1 = simulate_all_days(pair, start, dates[-1], yields)
        v2 = simulate_all_days_v2(pair, start, dates[-1], yields)

    assert len(v1) == len(v2) == 15
    assert load_signals.call_count == 1
    for results in (v1, v2):
        for signal, call in results:
            assert signal.rate_diff_2y is None
            assert signal.rate_diff_10y == expected_nominal
            assert signal.rate_diff_10y_real is None
            assert signal.rate_z_tactical is None
            assert signal.rate_z_structural is None
            assert signal.z_blended is None
            expected_notes = ["rate_inputs_unqualified", "rate_history_unavailable"]
            if pair == "USDINR":
                expected_notes.extend(["fpi_source_unqualified", "fpi_history_unavailable"])
            assert signal.data_quality_notes == expected_notes
            assert signal.fpi_flow is None
            assert call.rate_signal == "NEUTRAL"

    assert classifier.call_count == len(v1) + len(v2)
    for invocation in classifier.call_args_list:
        context = invocation.args[0]
        assert context.rate_diff_2y is None
        assert context.carry_risk_adjusted_chronological == ()

    snapshot = _build_historical_snapshot(
        pair,
        dates[-1],
        len(dates) - 1,
        dates,
        bars,
        yields,
        {},
    )
    assert snapshot.yields["us_2y"] == snapshot.yields["DGS2"] == 4.0
    assert snapshot.yields["us_10y"] == 4.0
    assert snapshot.yields[foreign_alias] == foreign_yield
    assert "quote_10y" not in snapshot.yields
