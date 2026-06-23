"""Tracer bullet: EURUSD regime call through IngestionSnapshot + RegimeCallBuilder."""

from __future__ import annotations

import datetime

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.types import (
    CotRow,
    Layer2DirectionalBias,
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


def _layer2(bias: Layer2DirectionalBias = "LONG") -> Layer2DirectionalOutput:
    return {
        "positioning_percentile": 0.75,
        "crowd_flag": False,
        "crowd_penalty": 0.0,
        "crowd_veto": False,
        "conviction_multiplier": 1.0,
        "conviction": 3,
        "directional_bias": bias,
        "rate_positioning_clash": False,
    }


def _layer3() -> Layer3ExecutionOutput:
    return {
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


def _eurusd_snapshot(
    *,
    dqs_score: float = 0.95,
    macro: dict[str, object] | None = None,
    pair: str = "EURUSD",
) -> IngestionSnapshot:
    as_of = datetime.date(2026, 1, 15)
    prev, today = _spot_bars(pair=pair, close=1.1)
    return IngestionSnapshot(
        date=as_of,
        spots={pair: (prev, today)},
        yields={},
        cot_rows=[],
        cross_asset={},
        macro=macro,
        dqs_score=dqs_score,
        stress_level="GREEN",
    )


def test_bias_mapping_long_to_bullish() -> None:
    """Layer2 LONG bias maps to predicted_direction BULLISH."""

    snapshot = _eurusd_snapshot()
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")
    call = builder.build_regime_call(
        "EURUSD",
        signal_row=signal_row,
        composite=0.5,
        confidence=0.6,
        regime="RISK_OFF_DOLLAR_BID",
        primary_driver="rate",
        layer2=_layer2("LONG"),
        layer3=_layer3(),
        rate_direction="BULLISH",
    )
    assert call.predicted_direction == "BULLISH"
    assert call.directional_bias == "LONG"


def test_bias_mapping_short_to_bearish() -> None:
    """Layer2 SHORT bias maps to predicted_direction BEARISH."""

    snapshot = _eurusd_snapshot()
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")
    call = builder.build_regime_call(
        "EURUSD",
        signal_row=signal_row,
        composite=-0.5,
        confidence=0.6,
        regime="RISK_ON_DOLLAR_OFF",
        primary_driver="rate",
        layer2=_layer2("SHORT"),
        layer3=_layer3(),
        rate_direction="BEARISH",
    )
    assert call.predicted_direction == "BEARISH"
    assert call.directional_bias == "SHORT"


def test_bias_mapping_neutral() -> None:
    """Layer2 NEUTRAL bias maps to predicted_direction NEUTRAL."""

    snapshot = _eurusd_snapshot()
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")
    call = builder.build_regime_call(
        "EURUSD",
        signal_row=signal_row,
        composite=0.0,
        confidence=0.5,
        regime="NEUTRAL",
        primary_driver="rate",
        layer2=_layer2("NEUTRAL"),
        layer3=_layer3(),
        rate_direction="NEUTRAL",
    )
    assert call.predicted_direction == "NEUTRAL"
    assert call.directional_bias == "NEUTRAL"


def test_dqs_confidence_cap() -> None:
    """Builder caps confidence according to snapshot DQS band."""

    snapshot = _eurusd_snapshot(dqs_score=0.65)
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")

    call = builder.build_regime_call(
        "EURUSD",
        signal_row=signal_row,
        composite=0.8,
        confidence=0.9,
        regime="RISK_OFF_DOLLAR_BID",
        primary_driver="rate",
        layer2=_layer2("LONG"),
        layer3=_layer3(),
        rate_direction="BULLISH",
    )
    # DQS 0.65 is in FAIR band [0.60, 0.75) → cap at 0.70
    assert call.confidence == 0.70
    assert call.data_quality_score == 0.65


def test_dqs_cap_can_be_disabled() -> None:
    """Builder allows callers to bypass DQS cap when desired."""

    snapshot = _eurusd_snapshot(dqs_score=0.65)
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")

    call = builder.build_regime_call(
        "EURUSD",
        signal_row=signal_row,
        composite=0.8,
        confidence=0.9,
        regime="RISK_OFF_DOLLAR_BID",
        primary_driver="rate",
        layer2=_layer2("LONG"),
        layer3=_layer3(),
        rate_direction="BULLISH",
        apply_dqs_cap=False,
    )
    assert call.confidence == 0.9


def test_eurusd_pair_specific_special_fields() -> None:
    """EURUSD macro fields populate ecb_balance_sheet and bund_btp_spread."""

    snapshot = _eurusd_snapshot(macro={"ecb_balance_sheet": 7000.0, "bund_btp_spread": 1.5})
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("EURUSD")

    assert signal_row.ecb_balance_sheet == 7000.0
    assert signal_row.bund_btp_spread == 1.5
    assert signal_row.boj_policy_rate is None
    assert signal_row.india_vix is None


def test_non_eurusd_macro_fields_are_none() -> None:
    """EURUSD macro fields are not populated for other pairs."""

    as_of = datetime.date(2026, 1, 15)
    eur_prev, eur_today = _spot_bars(pair="EURUSD", close=1.1)
    jpy_prev, jpy_today = _spot_bars(pair="USDJPY", close=150.0)
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": (eur_prev, eur_today), "USDJPY": (jpy_prev, jpy_today)},
        yields={},
        cot_rows=[],
        cross_asset={},
        macro={"ecb_balance_sheet": 7000.0, "bund_btp_spread": 1.5},
        dqs_score=0.95,
        stress_level="GREEN",
    )
    builder = RegimeCallBuilder(snapshot)
    signal_row = builder.build_signal_row("USDJPY")

    assert signal_row.ecb_balance_sheet is None
    assert signal_row.bund_btp_spread is None


def test_eurusd_builder_matches_inline_construction() -> None:
    """Builder output equals the pre-refactor inline SignalRow/RegimeCall."""

    from src.regime.classifier import get_regime_category
    from src.signals.volatility import compute_rvol
    from src.types import RegimeCall, SignalRow

    pair = "EURUSD"
    as_of = datetime.date(2026, 1, 15)
    prev, today = _spot_bars(pair=pair, close=1.1000)
    dqs_score = 0.82
    stress_level = "GREEN"

    yields: dict[str, float | None] = {
        "us_2y": 4.0,
        "de_2y": 2.0,
        "us_10y": 4.5,
        "de_10y": 2.5,
        "T10YIE": 2.0,
    }
    cross: dict[str, float | None] = {
        "vix": 18.0,
        "dxy": 104.0,
        "oil": 75.0,
        "gold": 2000.0,
        "copper": 4.0,
        "stoxx": 4500.0,
    }
    macro = {"ecb_balance_sheet": 7000.0, "bund_btp_spread": 1.5}

    snapshot = IngestionSnapshot(
        date=as_of,
        spots={pair: (prev, today)},
        yields=yields,
        cot_rows=[],
        cross_asset=cross,
        macro=macro,
        dqs_score=dqs_score,
        stress_level=stress_level,
    )

    rate_spread_2y = 2.0
    rate_spread_10y = 2.0
    rate_spread_10y_real = 0.0
    rate_z_tactical_val = 1.2
    rate_z_structural_val = 0.8
    rate_norm = 1.0
    cot_pct = 0.75
    cot_norm = 0.4
    rv20 = 0.08
    rv5 = 0.06
    iv = 0.09
    vol_norm = 0.2
    vol_exp = False
    oi_delta = 100
    oi_norm = 0.1
    special_signal = 0.55
    days_since_cot = 3
    cot_net_pos = 10000
    cot_asset_mgr_net = 5000
    cot_lev_money_net = -3000
    structural_instability = False
    bei = 2.0
    rr_proxy = None
    rr_source = "PENDING_REAL_DATA"
    fpi_raw = None

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

    rate_dir = "BULLISH"
    composite = 1.0
    confidence = 0.65
    regime = "RISK_OFF_DOLLAR_BID"
    driver = "rate"

    # ── Inline construction (mirrors orchestrator pre-refactor) ────────────
    day_change = today.close - prev.close
    day_chg_pct = (day_change / prev.close * 100) if prev.close else 0.0
    volumes = [b.volume for b in (prev, today) if b.volume > 0]
    rvol = compute_rvol(volumes)

    inline_signal_row = SignalRow(
        pair=pair,
        date=today.date,
        rate_diff_2y=rate_spread_2y,
        rate_diff_10y=rate_spread_10y,
        cot_percentile=cot_pct,
        realized_vol_20d=rv20,
        realized_vol_5d=rv5,
        implied_vol_30d=iv,
        spot=today.close,
        day_change=day_change,
        day_change_pct=day_chg_pct,
        cross_asset_vix=cross.get("vix"),
        cross_asset_dxy=cross.get("dxy"),
        cross_asset_oil=cross.get("oil"),
        cross_asset_us10y=yields.get("us_10y"),
        cross_asset_gold=cross.get("gold"),
        cross_asset_copper=cross.get("copper"),
        cross_asset_stoxx=cross.get("stoxx"),
        oi_delta=oi_delta,
        volume_rvol=rvol,
        structural_instability=structural_instability,
        breakeven_inflation_10y=bei,
        rate_diff_10y_real=rate_spread_10y_real,
        rate_z_tactical=rate_z_tactical_val,
        rate_z_structural=rate_z_structural_val,
        z_blended=rate_norm,
        realized_vol_rank=layer3["realized_vol_rank"],
        skew_alignment=layer3["skew_alignment"],
        risk_reversal_25d=rr_proxy,
        risk_reversal_source=rr_source,
        days_since_cot=days_since_cot,
        fpi_flow=fpi_raw.get("fpi_total_net_cr") if fpi_raw else None,
        cot_net_pos=cot_net_pos,
        cot_asset_mgr_net=cot_asset_mgr_net,
        cot_lev_money_net=cot_lev_money_net,
        ecb_balance_sheet=macro["ecb_balance_sheet"],
        bund_btp_spread=macro["bund_btp_spread"],
        boj_policy_rate=None,
        india_vix=None,
        inr_forward_premium=None,
    )

    bias = layer2["directional_bias"]
    predicted_direction = (
        "BULLISH" if bias == "LONG" else ("BEARISH" if bias == "SHORT" else "NEUTRAL")
    )
    cot_label = (
        "BULLISH"
        if cot_norm is not None and cot_norm > 0.15
        else ("BEARISH" if cot_norm is not None and cot_norm < -0.15 else "NEUTRAL")
    )
    vol_label = (
        "VOL_EXPANDING"
        if vol_exp
        else (
            "BULLISH"
            if vol_norm is not None and vol_norm > 0.15
            else ("BEARISH" if vol_norm is not None and vol_norm < -0.15 else "NEUTRAL")
        )
    )
    oi_label = (
        "BULLISH"
        if oi_norm is not None and oi_norm > 0.15
        else ("BEARISH" if oi_norm is not None and oi_norm < -0.15 else "NEUTRAL")
    )
    rr_label = (
        "BULLISH"
        if rr_proxy is not None and rr_proxy > 0.15
        else ("BEARISH" if rr_proxy is not None and rr_proxy < -0.15 else "NEUTRAL")
    )
    special_label = "Bund-BTP + ECB BS"

    inline_call = RegimeCall(
        pair=pair,
        date=today.date,
        regime=regime,
        confidence=confidence,
        signal_composite=composite,
        rate_signal=rate_dir,
        primary_driver=driver,
        entry_timing=layer3["entry_timing"],
        position_size=layer3["position_size"],
        stop_level=layer3["stop_level"],
        data_quality_score=round(dqs_score, 2),
        stress_level=stress_level,
        predicted_direction=predicted_direction,
        directional_bias=bias,
        conviction=layer2["conviction"],
        cot_signal=cot_label,
        vol_signal=vol_label,
        oi_signal=oi_label,
        rr_signal=rr_label,
        special_signal_value=special_signal,
        special_signal_label=special_label,
        regime_category=get_regime_category(regime),
        model_version="2.0-live",
    )

    # ── Builder construction ───────────────────────────────────────────────
    builder = RegimeCallBuilder(snapshot)
    builder_signal_row = builder.build_signal_row(
        pair=pair,
        rate_spread_2y=rate_spread_2y,
        rate_spread_10y=rate_spread_10y,
        rate_spread_10y_real=rate_spread_10y_real,
        rate_z_tactical=rate_z_tactical_val,
        rate_z_structural=rate_z_structural_val,
        z_blended=rate_norm,
        cot_percentile=cot_pct,
        cot_norm=cot_norm,
        realized_vol_20d=rv20,
        realized_vol_5d=rv5,
        implied_vol_30d=iv,
        vol_norm=vol_norm,
        vol_expanding=vol_exp,
        oi_delta=oi_delta,
        oi_norm=oi_norm,
        special_signal=special_signal,
        fpi_raw=fpi_raw,
        days_since_cot=days_since_cot,
        cot_net_pos=cot_net_pos,
        cot_asset_mgr_net=cot_asset_mgr_net,
        cot_lev_money_net=cot_lev_money_net,
        structural_instability=structural_instability,
        breakeven_inflation_10y=bei,
        realized_vol_rank=layer3["realized_vol_rank"],
        skew_alignment=layer3["skew_alignment"],
        risk_reversal_25d=rr_proxy,
        risk_reversal_source=rr_source,
    )
    builder_call = builder.build_regime_call(
        pair=pair,
        signal_row=builder_signal_row,
        composite=composite,
        confidence=confidence,
        regime=regime,
        primary_driver=driver,
        layer2=layer2,
        layer3=layer3,
        rate_direction=rate_dir,
        cot_norm=cot_norm,
        vol_norm=vol_norm,
        vol_expanding=vol_exp,
        oi_norm=oi_norm,
        risk_reversal_25d=rr_proxy,
        special_signal=special_signal,
        apply_dqs_cap=False,
    )

    assert builder_signal_row == inline_signal_row
    assert builder_call == inline_call
