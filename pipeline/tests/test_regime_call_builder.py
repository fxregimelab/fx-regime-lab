"""Tracer bullet: EURUSD regime call through IngestionSnapshot + RegimeCallBuilder."""

from __future__ import annotations

import datetime

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.types import (
    CotRow,
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    SpotBar,
)


def _spot_bars(*, pair: str = "EURUSD", close: float = 1.1000) -> tuple[SpotBar, SpotBar]:
    d = datetime.date(2026, 1, 15)
    prev = d - datetime.timedelta(days=1)
    return (
        SpotBar(date=prev, pair=pair, open=close, high=close, low=close, close=close),
        SpotBar(date=d, pair=pair, open=close, high=close, low=close, close=close),
    )


def test_eurusd_regime_call_tracer_bullet() -> None:
    """A EURUSD call can be assembled from an IngestionSnapshot and layer outputs."""

    pair = "EURUSD"
    as_of = datetime.date(2026, 1, 15)
    prev, today = _spot_bars(pair=pair, close=1.1000)

    snapshot = IngestionSnapshot(
        date=as_of,
        spots={pair: (prev, today)},
        yields={
            "us_2y": 4.0,
            "de_2y": 2.0,
            "us_10y": 4.5,
            "de_10y": 2.5,
            "T10YIE": 2.0,
        },
        cot_rows=[
            CotRow(
                date=as_of - datetime.timedelta(days=3),
                pair=pair,
                net_long=10000,
                open_interest=20000,
                asset_mgr_net=5000,
                lev_money_net=-3000,
            ),
        ],
        cross_asset={
            "vix": 18.0,
            "dxy": 104.0,
            "oil": 75.0,
            "gold": 2000.0,
            "copper": 4.0,
            "stoxx": 4500.0,
        },
        macro={
            "ecb_balance_sheet": 7000.0,
            "bund_btp_spread": 1.5,
        },
        dqs_score=0.95,
        stress_level="GREEN",
    )

    builder = RegimeCallBuilder(snapshot)

    signal_row = builder.build_signal_row(
        pair=pair,
        rate_spread_2y=2.0,
        rate_spread_10y=2.0,
        rate_spread_10y_real=0.0,
        rate_z_tactical=1.2,
        rate_z_structural=0.8,
        z_blended=1.0,
        cot_percentile=0.75,
        cot_norm=0.4,
        realized_vol_20d=0.08,
        realized_vol_5d=0.06,
        implied_vol_30d=0.09,
        vol_norm=0.2,
        vol_expanding=False,
        oi_delta=100,
        oi_norm=0.1,
        special_signal=0.55,
        days_since_cot=3,
        cot_net_pos=10000,
        cot_asset_mgr_net=5000,
        cot_lev_money_net=-3000,
        structural_instability=False,
        breakeven_inflation_10y=2.0,
        realized_vol_rank=0.35,
        skew_alignment=1,
    )

    layer2: Layer2DirectionalOutput = {
        "positioning_percentile": 0.75,
        "crowd_flag": False,
        "crowd_penalty": 0.0,
        "crowd_veto": False,
        "conviction_multiplier": 1.0,
        "conviction": 3,
        "directional_bias": "LONG",
        "rate_positioning_clash": False,
    }

    layer3: Layer3ExecutionOutput = {
        "entry_timing": "ENTER",
        "position_size": "FULL",
        "stop_level": 1.0850,
        "realized_vol_rank": 0.35,
        "skew_alignment": 1,
        "skew_reversal_flag": False,
        "risk_reversal_z": None,
        "adr": 0.009,
        "mie_proxy": 0.005,
        "stop_buffer": 0.015,
    }

    call = builder.build_regime_call(
        pair=pair,
        signal_row=signal_row,
        composite=1.0,
        confidence=0.65,
        regime="RISK_OFF_DOLLAR_BID",
        primary_driver="rate",
        layer2=layer2,
        layer3=layer3,
        rate_direction="BULLISH",
        cot_norm=0.4,
        vol_norm=0.2,
        vol_expanding=False,
        oi_norm=0.1,
        risk_reversal_25d=None,
        special_signal=0.55,
    )

    assert call.pair == "EURUSD"
    assert call.date == as_of
    assert call.regime == "RISK_OFF_DOLLAR_BID"
    assert call.confidence == 0.65
    assert call.signal_composite == 1.0
    assert call.rate_signal == "BULLISH"
    assert call.primary_driver == "rate"
    assert call.entry_timing == "ENTER"
    assert call.position_size == "FULL"
    assert call.stop_level == 1.0850
    assert call.predicted_direction == "BULLISH"
    assert call.directional_bias == "LONG"
    assert call.conviction == 3
    assert call.data_quality_score == 0.95
    assert call.stress_level == "GREEN"
    assert call.special_signal_value == 0.55
    assert call.special_signal_label == "Bund-BTP + ECB BS"
    assert call.regime_category == "RATE_DRIVEN"
    assert call.model_version == "2.0-live"

    assert signal_row.pair == "EURUSD"
    assert signal_row.date == as_of
    assert signal_row.spot == 1.1
    assert signal_row.ecb_balance_sheet == 7000.0
    assert signal_row.bund_btp_spread == 1.5
