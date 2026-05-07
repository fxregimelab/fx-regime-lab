"""Layer 3 execution HUD unit tests (strict, no I/O)."""

from __future__ import annotations

import datetime

import numpy as np
import pytest

from src.logic.layer3_execution import (
    average_daily_range,
    causal_rr_z_pair,
    mie_proxy_points,
    run_layer3_execution,
    skew_bias_alignment,
    skew_reversal_flag,
    stop_buffer_and_level,
)
from src.signals.volatility import (
    TRADING_DAYS_3Y_VOL_RANK,
    compute_realized_vol_rank_from_closes,
    empirical_cdf_rank,
    realized_vol21_series_annualized_pct,
)
from src.types import Layer2DirectionalBias, Layer2DirectionalOutput, SpotBar


def _layer2(
    *,
    bias: Layer2DirectionalBias,
    conviction: int,
    crowd_flag: bool = False,
    crowd_penalty: float = 0.0,
) -> Layer2DirectionalOutput:
    return Layer2DirectionalOutput(
        positioning_percentile=55.0,
        crowd_flag=crowd_flag,
        crowd_penalty=crowd_penalty,
        crowd_veto=False,
        conviction_multiplier=1.0,
        conviction=conviction,
        directional_bias=bias,
        rate_positioning_clash=False,
    )


def d(i: int) -> datetime.date:
    return datetime.date(2022, 6, 1) + datetime.timedelta(days=i)


def test_empirical_cdf_mid_sample() -> None:
    xs = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    assert empirical_cdf_rank(3.0, xs) == pytest.approx(0.6)


def test_realized_vol_rank_increases_after_late_spike() -> None:
    rng = np.random.default_rng(42)
    n = TRADING_DAYS_3Y_VOL_RANK + 50
    noise = rng.normal(0.0, 0.002, size=n - 40)
    base = 1.0
    drift = np.cumsum(noise)
    calm = base + drift
    # Fat-tailed daily shocks (not a smooth exp ramp — near-constant returns suppress σ).
    shock_ret = rng.normal(0.0, 0.03, size=40)
    closes_tail = calm[-1] * np.exp(np.cumsum(shock_ret))
    closes = np.concatenate([calm, closes_tail])
    q = compute_realized_vol_rank_from_closes(
        tuple(float(x) for x in closes),
        window=TRADING_DAYS_3Y_VOL_RANK,
    )
    assert q is not None
    assert 0.0 <= q <= 1.0
    # Same path but truncated before shock — rank should be materially lower.
    q_calm = compute_realized_vol_rank_from_closes(
        tuple(float(x) for x in calm),
        window=TRADING_DAYS_3Y_VOL_RANK,
    )
    assert q_calm is not None
    assert float(q) > float(q_calm)


def test_realized_vol21_series_no_lookahead() -> None:
    closes = np.exp(np.linspace(0.0, 0.5, 80))
    series = realized_vol21_series_annualized_pct(closes)
    assert np.isnan(series[:21]).all()
    assert np.isfinite(series[21:]).all()


def test_causal_rr_z_pair_requires_history() -> None:
    rng = np.random.default_rng(0)
    jittered = [0.1 + float(rng.normal(0, 0.01)) for _ in range(40)]
    z_t, z_y = causal_rr_z_pair(jittered)
    assert z_t is not None
    assert z_y is not None


def test_skew_bias_alignment_long_positive_z() -> None:
    assert skew_bias_alignment("LONG", 0.8) == 1
    assert skew_bias_alignment("LONG", -0.8) == -1
    assert skew_bias_alignment("SHORT", -0.8) == 1
    assert skew_bias_alignment("NEUTRAL", 1.0) == 0


def test_skew_reversal_flag_sign_flip() -> None:
    assert skew_reversal_flag(0.8, -0.8) is True
    assert skew_reversal_flag(0.2, -0.8) is False
    assert skew_reversal_flag(None, -0.8) is False


def test_stop_long_uses_max_buffer() -> None:
    buf, stop = stop_buffer_and_level(100.0, "LONG", adr=1.0, mie=2.0)
    assert buf == pytest.approx(2.0)
    assert stop == pytest.approx(98.0)


def test_stop_short_adds_buffer() -> None:
    buf, stop = stop_buffer_and_level(100.0, "SHORT", adr=2.0, mie=1.0)
    assert buf == pytest.approx(3.0)
    assert stop == pytest.approx(103.0)


def test_enter_wait_marcus_vol_rank() -> None:
    bars = [
        SpotBar(d(i), "EURUSD", 1.0, 1.002, 0.998, 1.001, 1e6)
        for i in range(25)
    ]
    l2 = _layer2(bias="LONG", conviction=4)
    out = run_layer3_execution(
        layer2=l2,
        spot=1.1,
        spot_bars=bars,
        realized_vol_rank=0.99,
        risk_reversal_series_bps=(),
    )
    assert out["entry_timing"] == "WAIT"
    assert out["position_size"] == "HALF"


def test_full_size_lena_chen() -> None:
    bars = [
        SpotBar(d(i), "EURUSD", 1.0, 1.002, 0.998, 1.001, 1e6)
        for i in range(25)
    ]
    rr = tuple(0.01 * float(i) for i in range(45))
    l2 = _layer2(
        bias="LONG",
        conviction=5,
        crowd_flag=False,
        crowd_penalty=0.0,
    )
    out = run_layer3_execution(
        layer2=l2,
        spot=1.1,
        spot_bars=bars,
        realized_vol_rank=0.55,
        risk_reversal_series_bps=rr,
    )
    assert out["entry_timing"] == "ENTER"
    assert out["skew_alignment"] == 1
    assert out["position_size"] == "FULL"


def test_chen_dampener_halves_from_crowding() -> None:
    bars = [
        SpotBar(d(i), "EURUSD", 1.0, 1.002, 0.998, 1.001, 1e6)
        for i in range(25)
    ]
    rr = [0.05 * np.sin(i / 12.0) for i in range(45)]
    l2 = _layer2(
        bias="LONG",
        conviction=5,
        crowd_flag=True,
        crowd_penalty=0.0,
    )
    out = run_layer3_execution(
        layer2=l2,
        spot=1.1,
        spot_bars=bars,
        realized_vol_rank=0.45,
        risk_reversal_series_bps=tuple(float(x) for x in rr),
    )
    assert out["entry_timing"] == "ENTER"
    assert out["position_size"] == "HALF"


def test_strong_skew_contradiction_waits_with_mid_conviction() -> None:
    bars = [
        SpotBar(d(i), "EURUSD", 1.0, 1.002, 0.998, 1.001, 1e6)
        for i in range(25)
    ]
    rr_neg_trend = tuple(-0.01 * float(i) for i in range(45))
    l2 = _layer2(bias="LONG", conviction=3)
    out = run_layer3_execution(
        layer2=l2,
        spot=1.1,
        spot_bars=bars,
        realized_vol_rank=0.5,
        risk_reversal_series_bps=rr_neg_trend,
    )
    assert out["skew_alignment"] == -1
    assert out["entry_timing"] == "WAIT"


    bars = [
        SpotBar(d(0), "EURUSD", 1.0, 1.01, 0.99, 1.005),
        SpotBar(d(1), "EURUSD", 1.005, 1.02, 0.995, 1.01),
        SpotBar(d(2), "EURUSD", 1.01, 1.03, 1.0, 1.02),
    ]
    adr = average_daily_range(bars, 20)
    assert adr is not None
    assert adr > 0
    mie_l = mie_proxy_points(bars, "LONG", 20)
    assert mie_l is not None
    mie_s = mie_proxy_points(bars, "SHORT", 20)
    assert mie_s is not None
