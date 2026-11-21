"""Economic counterexamples that previously produced a usable but false feature."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.db import writer
from src.fetchers import yields as fetcher
from src.scheduler.orchestrator import _rate_spread_2y_for_pair, _rate_spread_10y_legacy
from src.signals.rate import (
    build_carry_history_from_rows,
    build_real_yield_10y_spread_history_from_rows,
    normalize_rate_signal,
)
from src.signals.rate_inputs import (
    RateInstrument,
    current_real_yield_spread,
    nominal_ten_year_context,
    qualify_rate_history,
    real_yield_spread,
    two_year_spread,
)
from src.staged.stages.signal_stage import (
    SignalStage,
    _normalize_rate_signal,
    _rate_spread_2y,
    _rate_spread_10y,
)
from tests.test_staged_eurusd_happy_path import _make_eurusd_snapshot


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_configured_incompatible_sources_are_unavailable_in_both_paths(pair: str) -> None:
    universe = json.loads((Path(__file__).parents[1] / "universe.json").read_text())
    values: dict[str, float | None] = {
        "DGS2": 4.0,
        "ECBDFR": 2.0,
        "IRLTLT01JPM156N": 1.0,
        "INDIRLTLT01STM": 7.0,
    }
    assert _rate_spread_2y_for_pair(pair, universe, values) is None
    assert _rate_spread_2y(pair, values) is None


def test_valid_matched_rates_and_orientation() -> None:
    definitions = {
        "de": RateInstrument("EUR", 2, "government_yield", "daily"),
        "us": RateInstrument("USD", 2, "government_yield", "daily"),
    }
    assert (
        two_year_spread("EURUSD", {"de": 2, "us": 4}, ("de", "us"), definitions=definitions) == -2
    )
    assert (
        two_year_spread("EURUSD", {"de": 2, "us": 4}, ("us", "de"), definitions=definitions) is None
    )


@pytest.mark.parametrize(
    "foreign",
    [
        RateInstrument("EUR", 10, "government_yield", "daily"),
        RateInstrument("EUR", 2, "government_yield", "monthly"),
        RateInstrument("EUR", 2, "deposit_facility", "daily"),
        RateInstrument("EUR", 2, "government_yield", "daily", "basis_points"),
    ],
)
def test_mixed_instruments_rejected(foreign: RateInstrument) -> None:
    definitions = {"de": foreign, "us": RateInstrument("USD", 2, "government_yield", "daily")}
    assert (
        two_year_spread("EURUSD", {"de": 2, "us": 4}, ("de", "us"), definitions=definitions) is None
    )


@pytest.mark.parametrize("bad", [None, True, float("inf"), float("nan")])
def test_invalid_real_spread_inputs_cannot_produce_a_score(bad: float | None) -> None:
    assert real_yield_spread(2, bad, 1) is None
    assert real_yield_spread(bad, 2, 1) is None


def test_real_spread_needs_both_countries_and_preserves_zero() -> None:
    # EUR 2%, US 4%; EUR inflation 1%, US inflation 3% => both real rates 1%.
    assert real_yield_spread(-2, 1, 3) == 0
    assert real_yield_spread(0, 0, 0) == 0
    assert real_yield_spread(-2, None, 3) is None
    for pair in ("EURUSD", "USDJPY", "USDINR"):
        assert current_real_yield_spread(pair, -2, {"T10YIE": 3}) is None


@pytest.mark.parametrize("pair,expected", [("EURUSD", -2), ("USDJPY", 3), ("USDINR", -3)])
def test_nominal_context_orientation_agrees_across_paths(pair: str, expected: float) -> None:
    values: dict[str, float | None] = {"us_10y": 4.0, "de_10y": 2.0, "jp_10y": 1.0, "in_10y": 7.0}
    assert nominal_ten_year_context(pair, values) == expected
    assert _rate_spread_10y_legacy(pair, values) == expected
    assert _rate_spread_10y(pair, values) == expected


def test_unqualified_history_and_missing_structural_series_stay_unavailable() -> None:
    rows = [
        {"date": "2026-01-01", "rate_diff_10y": 2, "breakeven_inflation_10y": 3},
        {"date": "2026-01-02", "rate_diff_10y": 2},
    ]
    assert build_real_yield_10y_spread_history_from_rows(rows) == []
    normalized = normalize_rate_signal(
        3, "EURUSD", [1, 2, 3], spread_structural=2, historical_structural=[float("nan")]
    )
    assert normalized.z_tactical is not None
    assert normalized.z_structural is None
    assert normalized.z_blended == normalized.z_tactical
    staged = _normalize_rate_signal("EURUSD", 2, 3)
    assert staged.z_tactical is None and staged.z_structural is None


def test_qualified_history_is_distinct_from_legacy_values() -> None:
    legacy = {"date": "2026-01-01", "rate_diff_2y": 2, "realized_vol_20d": 10}
    assert build_carry_history_from_rows([legacy]) == []
    assert build_carry_history_from_rows([legacy | {"rate_input_contract": "pair-2y-v1"}]) == [0.2]
    real = {
        "date": "2026-01-01",
        "rate_diff_10y": -2,
        "breakeven_base_10y": 1,
        "breakeven_quote_10y": 3,
    }
    assert build_real_yield_10y_spread_history_from_rows([real]) == []
    assert build_real_yield_10y_spread_history_from_rows(
        [real | {"real_rate_contract": "pair-real10y-v1"}]
    ) == [0]


def test_history_exclusion_prevents_legacy_rates_reaching_other_consumers() -> None:
    original = {"date": "2026-01-01", "rate_diff_2y": 2, "cot_percentile": 75}
    qualified = original | {"rate_input_contract": "pair-2y-v1"}
    rows = qualify_rate_history([original, qualified])
    assert rows[0]["rate_diff_2y"] is None
    assert rows[0]["cot_percentile"] == 75
    assert rows[1]["rate_diff_2y"] == 2
    assert original["rate_diff_2y"] == 2


def test_valid_structural_history_can_be_scored_without_tactical_history() -> None:
    result = normalize_rate_signal(
        0, "EURUSD", [], spread_structural=3, historical_structural=[0, 1, 2]
    )
    assert result.z_tactical is None
    assert result.z_structural is not None
    assert result.z_blended == result.z_structural


def test_actual_staged_signal_exposes_missing_rate_history() -> None:
    result = SignalStage().run("EURUSD", _make_eurusd_snapshot())
    assert result.rate_spread_2y is None
    assert result.rate_spread_10y == -2
    assert result.rate_spread_10y_real is None
    assert result.rate_z_tactical is None and result.rate_z_structural is None
    assert result.rate_direction == "NEUTRAL"
    assert result.health.status == "DEGRADED"
    assert "rate_history_unavailable" in result.health.notes


def test_writer_preserves_rate_availability_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SignalStage().run("EURUSD", _make_eurusd_snapshot())
    client = MagicMock()
    monkeypatch.setattr(writer, "_client", lambda: client)
    writer.write_signal_row(result.signal_row)
    payload = client.table.return_value.upsert.call_args.args[0]
    assert "rate_history_unavailable" in payload["data_quality_notes"]
    assert payload["rate_diff_2y"] is None
    assert payload["rate_diff_10y_real"] is None


def test_sync_fetcher_does_not_relabel_ten_year_yields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.setattr(
        fetcher,
        "_fetch_yf_legs",
        lambda *a: {"de_2y": None, "jp_2y": None, "in_2y": None},
    )
    monkeypatch.setattr(fetcher, "fetch_legacy_10y_legs", lambda *a: {"de_10y": 2, "in_10y": 7})
    monkeypatch.setattr(fetcher, "_fred_leg", lambda *a: None)
    monkeypatch.setattr(fetcher, "_yf_leg", lambda *a: 4)
    monkeypatch.setattr("src.fetchers.yields.time.sleep", lambda *a: None)
    values = fetcher.fetch_yields()
    assert values["de_2y"] is None and values["in_2y"] is None
    assert values["us_2y"] == 4
    assert values["de_10y"] == 2 and values["in_10y"] == 7
