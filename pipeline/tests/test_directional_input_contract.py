"""Offline regressions for the frozen directional reference contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from typing import Any

import pytest

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.logic.layer1_gate import prior_tier_from_regime, regime_from_composite_snapshot
from src.logic.layer2_directional import run_layer2_directional
from src.regime.composite import compute_composite
from src.signals.direction import (
    DIRECTIONAL_MODEL_VERSION,
    DIRECTIONAL_STRATEGY_VERSION,
    DirectionalInputs,
    currency_strength_to_pair,
    directional_inputs,
)
from src.signals.open_interest import compute_oi_signal
from src.types import Layer3ExecutionOutput, RegimeCall, SpotBar


@pytest.mark.parametrize(
    "pair,cot,fpi,expected",
    [
        ("EUR/USD", 0.6, None, DirectionalInputs(0.4, 0.6, -0.8, None)),
        ("USD/JPY", 0.6, None, DirectionalInputs(0.4, -0.6, 0.8, None)),
        ("USD/INR", None, 0.7, DirectionalInputs(0.4, None, 0.8, -0.7)),
    ],
)
def test_raw_orientation_is_explicit_and_does_not_mutate(
    pair: str, cot: float | None, fpi: float | None, expected: DirectionalInputs
) -> None:
    raw = {"rate": 0.4, "cot": cot, "special": 0.8, "fpi": fpi}
    before = raw.copy()
    result = directional_inputs(pair, **raw)
    assert result == expected
    assert raw == before
    with pytest.raises(FrozenInstanceError):
        setattr(result, "rate", 99.0)


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_base_and_quote_strength_have_opposite_signs(pair: str) -> None:
    assert currency_strength_to_pair(0.7, currency=pair[:3], pair=pair) == 0.7
    assert currency_strength_to_pair(0.7, currency=pair[3:], pair=pair) == -0.7
    assert currency_strength_to_pair(-0.7, currency=pair[3:], pair=pair) == 0.7


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf"), "1"])
@pytest.mark.parametrize("field", ["rate", "cot", "special", "fpi"])
def test_boundary_rejects_invalid_present_values(value: Any, field: str) -> None:
    raw: dict[str, Any] = {"rate": None, "cot": None, "special": None, "fpi": None}
    raw[field] = value
    with pytest.raises(ValueError):
        directional_inputs("USDINR" if field == "fpi" else "EURUSD", **raw)


@pytest.mark.parametrize("pair", ["GBPUSD", "", "USDEUR", "EURJPY"])
def test_unknown_pairs_are_rejected(pair: str) -> None:
    with pytest.raises(ValueError):
        directional_inputs(pair, rate=None, cot=None, special=None, fpi=None)
    with pytest.raises(ValueError):
        currency_strength_to_pair(None, currency="USD", pair=pair)


def test_unsupported_currency_and_pair_specific_families_are_rejected() -> None:
    with pytest.raises(ValueError):
        currency_strength_to_pair(None, currency="JPY", pair="EURUSD")
    with pytest.raises(ValueError):
        directional_inputs("USDINR", rate=None, cot=0.0, special=None, fpi=None)
    for pair in ("EURUSD", "USDJPY"):
        with pytest.raises(ValueError):
            directional_inputs(pair, rate=None, cot=None, special=None, fpi=0.0)


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
@pytest.mark.parametrize("state", [-2.0, 0.0, 2.0])
def test_state_only_cannot_supply_a_forecast(pair: str, state: float) -> None:
    assert compute_composite(None, None, state, state, pair=pair) is None
    assert compute_composite(0.0, None, state, state, pair=pair) == 0.0
    assert compute_composite(0.7, None, state, state, pair=pair) == pytest.approx(0.7)


def test_observed_zero_has_weight_but_missing_has_none() -> None:
    empty = directional_inputs("EURUSD", rate=None, cot=None, special=None, fpi=None)
    zero = directional_inputs("EURUSD", rate=0.0, cot=0.0, special=0.0, fpi=None)
    assert empty.rate is None and empty.cot is None and empty.special is None
    assert zero == DirectionalInputs(0.0, 0.0, 0.0, None)
    assert compute_composite(1.0, None, None, None, pair="EURUSD") == 1.0
    assert compute_composite(1.0, 0.0, None, None, pair="EURUSD") == pytest.approx(0.45 / 0.70)
    assert compute_composite(None, 1.0, None, None, pair="USDINR") is None


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_pair_up_reciprocal_sign_symmetry_and_beta_invariance(pair: str) -> None:
    # Negating every directional hypothesis must negate the result without changing magnitude.
    positive = compute_composite(0.8, -0.4, 2.0, -2.0, pair=pair, special_signal=0.3)
    negative = compute_composite(-0.8, 0.4, 2.0, -2.0, pair=pair, special_signal=-0.3)
    assert positive is not None and negative == pytest.approx(-positive)
    adapted = compute_composite(
        0.8, -0.4, -999.0, 999.0, pair=pair, special_signal=0.3,
        betas={"rate": -0.01, "cot": 900.0, "vol": 1e9, "oi": -1e9, "special": 0.5},
    )
    assert adapted == positive


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "0.2"])
def test_composite_rejects_nonfinite_or_nonnumeric_active_input(value: Any) -> None:
    with pytest.raises(ValueError):
        compute_composite(value, None, None, None, pair="EURUSD")
    # An excluded family has no effect on the numerator or denominator.
    assert compute_composite(0.2, None, value, value, pair="EURUSD") == pytest.approx(0.2)


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
def test_missing_composite_never_falls_back_to_rate(pair: str) -> None:
    out = run_layer2_directional(
        pair=pair, composite=None, z_tactical=1.0, z_structural=None,
        rate_direction="BULLISH", positioning_percentile=50.0, layer1_invalidated=False,
    )
    assert out["directional_bias"] == "NEUTRAL"


def test_jpy_clash_orients_position_without_reversing_crowding_percentile() -> None:
    args: dict[str, Any] = {
        "composite": 0.8, "z_tactical": 0.8, "z_structural": None,
        "rate_direction": "BULLISH", "positioning_percentile": 92.0,
        "layer1_invalidated": False,
    }
    eur = run_layer2_directional(pair="EURUSD", **args)
    jpy = run_layer2_directional(pair="USDJPY", **args)
    inr = run_layer2_directional(pair="USDINR", **args)
    assert eur["rate_positioning_clash"] is False
    assert jpy["rate_positioning_clash"] is True
    assert inr["rate_positioning_clash"] is False
    assert eur["directional_bias"] == "LONG"
    assert jpy["directional_bias"] == "NEUTRAL"
    for out in (eur, jpy, inr):
        assert out["positioning_percentile"] == 92.0
        assert out["crowd_penalty"] == pytest.approx(0.2)
        assert out["crowd_flag"] is True
        assert out["crowd_veto"] is False
    aligned = run_layer2_directional(pair="USDJPY", **{**args, "positioning_percentile": 25.0})
    assert aligned["rate_positioning_clash"] is False
    assert aligned["directional_bias"] == "LONG"


@pytest.mark.parametrize("pair", ["EURUSD", "USDJPY", "USDINR"])
@pytest.mark.parametrize("score,tier", [(-1.5, 0), (-0.7, 1), (0.0, 2), (0.7, 3), (1.5, 4)])
def test_every_composite_tier_roundtrips(pair: str, score: float, tier: int) -> None:
    label = regime_from_composite_snapshot(score, pair)
    assert prior_tier_from_regime(label, pair) == tier
    assert regime_from_composite_snapshot(score, pair, prior_regime_label=label) == label
    assert label not in {"RISK_OFF_DOLLAR_BID", "GROWTH_SURPRISE_USD", "RISK_ON_DOLLAR_OFF"}


@pytest.mark.parametrize("score", [-1.5, -0.7, 0.0, 0.7, 1.5])
def test_same_usd_direction_has_same_label_for_reciprocal_quote_orientation(score: float) -> None:
    assert regime_from_composite_snapshot(score, "EURUSD") == regime_from_composite_snapshot(
        -score, "USDJPY"
    )


def _published_state(vol: float | None, oi: float | None, *, expanding: bool = False) -> RegimeCall:
    day = date(2026, 9, 25)
    bar = SpotBar(date=day, pair="USDINR", open=85.0, high=85.0, low=85.0, close=85.0)
    snapshot = IngestionSnapshot(
        date=day, spots={"USDINR": (bar,)}, yields={}, cot_rows=[], cross_asset={},
    )
    builder = RegimeCallBuilder(snapshot)
    layer2 = run_layer2_directional(
        pair="USDINR", composite=0.0, z_tactical=None, z_structural=None,
        rate_direction="NEUTRAL", positioning_percentile=None, layer1_invalidated=False,
    )
    layer3: Layer3ExecutionOutput = {
        "entry_timing": "WAIT", "position_size": "HALF", "stop_level": None,
        "realized_vol_rank": None, "skew_alignment": 0, "skew_reversal_flag": False,
        "risk_reversal_z": None, "adr": None, "mie_proxy": None, "stop_buffer": None,
    }
    return builder.build_regime_call(
        "USDINR", signal_row=builder.build_signal_row("USDINR"), composite=0.0,
        confidence=0.5, regime="INR_NEUTRAL", primary_driver="Static reference",
        layer2=layer2, layer3=layer3, rate_direction="NEUTRAL",
        vol_norm=vol, oi_norm=oi, vol_expanding=expanding,
    )


@pytest.mark.parametrize(
    "vol,oi,vol_label,oi_label",
    [
        (None, None, "UNAVAILABLE", "UNAVAILABLE"),
        (0.0, 0.0, "VOL_STABLE", "OI_TYPICAL"),
        (0.8, 0.8, "VOL_EXPANDING", "OI_LOW"),
        (-0.8, -0.8, "VOL_CONTRACTING", "OI_HIGH"),
    ],
)
def test_publication_labels_describe_state_and_identify_reference_version(
    vol: float | None, oi: float | None, vol_label: str, oi_label: str
) -> None:
    call = _published_state(vol, oi)
    assert call.vol_signal == vol_label
    assert call.oi_signal == oi_label
    assert call.special_signal_label == "Oil + DXY"
    assert call.model_version == DIRECTIONAL_MODEL_VERSION == "3.0-directional-reference"
    assert call.strategy_version == DIRECTIONAL_STRATEGY_VERSION == "pair-direction-v1"
    assert call.predicted_direction == "NEUTRAL"


def test_explicit_expansion_state_remains_visible() -> None:
    assert _published_state(None, None, expanding=True).vol_signal == "VOL_EXPANDING"


@pytest.mark.parametrize(
    "percentile,label",
    [(0.0, "OI_LOW"), (50.0, "OI_TYPICAL"), (100.0, "OI_HIGH"), (None, "UNAVAILABLE")],
)
def test_oi_percentile_state_survives_publication(percentile: float | None, label: str) -> None:
    call = _published_state(None, compute_oi_signal(percentile))
    assert call.oi_signal == label
    assert call.predicted_direction == "NEUTRAL"
