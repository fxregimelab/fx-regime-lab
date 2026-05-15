"""Comprehensive tests for USDINR pair-specific modules."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fx_types import SpotBar
from src.pairs.usdinr.composite import USDINRComposite, _compute_usdinr_special
from src.pairs.usdinr.execution import (
    average_daily_range,
    compute_stop_level,
    compute_usdinr_position_size,
    get_usdinr_execution_params,
    mie_proxy_points,
)
from src.pairs.usdinr.fetcher import USDINRFetcher
from src.pairs.usdinr.regime import (
    detect_fpi_flow_regime,
    detect_rbi_management_regime,
    get_usdinr_thresholds,
    usdinr_hysteresis_tier,
)

# ---------------------------------------------------------------------------
# USDINRFetcher
# ---------------------------------------------------------------------------


class TestUSDINRFetcher:
    def test_init(self) -> None:
        fetcher = USDINRFetcher(lookback_days=60)
        assert fetcher.pair == "USDINR"
        assert fetcher.lookback_days == 60

    def test_method_existence(self) -> None:
        fetcher = USDINRFetcher()
        assert hasattr(fetcher, "fetch_data")
        assert hasattr(fetcher, "fetch_all")
        assert hasattr(fetcher, "compute_signals")
        assert hasattr(fetcher, "compute_composite")
        assert hasattr(fetcher, "classify_regime")
        assert hasattr(fetcher, "compute_execution")

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_fetch_all_mocks(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDINR": [SpotBar(datetime.date(2025, 1, 1), "USDINR", 83.0, 83.5, 82.5, 83.2)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "in_10y": 7.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDINRFetcher()
        data = fetcher.fetch_all()
        assert "spot" in data
        assert "yields" in data
        assert "cot" in data
        assert "cross_asset" in data
        assert "rbi_fx_reserves" in data
        assert "fpi_flows" in data
        assert "india_vix" in data
        assert "inr_forward_premium" in data
        assert "em_stress" in data

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_compute_signals_bullish_usd(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDINR": [SpotBar(datetime.date(2025, 1, 1), "USDINR", 83.0, 83.5, 82.5, 83.2)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "in_10y": 7.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDINRFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        # US 10Y (4.5) < IN 10Y (7.5) → negative spread → BEARISH_USD
        assert signals["rate_signal"] == "BEARISH_USD"
        assert signals["rate_diff"] == -3.0

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_special_signal_multiple_components(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDINR": [SpotBar(datetime.date(2025, 1, 1), "USDINR", 83.0, 83.5, 82.5, 83.2)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "in_10y": 7.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDINRFetcher()
        data = fetcher.fetch_data()
        # Inject conditions for multiple special components
        data["india_vix"] = 25.0
        data["em_stress"] = {"composite": 75.0, "stress_level": "HIGH"}
        data["rbi_fx_reserves"] = 540.0

        signals = fetcher.compute_signals(data)
        special_val = signals["special_signal_value"]
        special_label = signals["special_signal_label"]
        assert special_val < -0.5  # india_vix(-0.3) + em_stress(-0.4) + low_reserves(-0.3)
        assert "INDIA_VOL_SPIKE" in special_label
        assert "EM_STRESS" in special_label
        assert "LOW_RESERVES" in special_label

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_em_stress_calm(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDINR": [SpotBar(datetime.date(2025, 1, 1), "USDINR", 83.0, 83.5, 82.5, 83.2)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "in_10y": 7.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDINRFetcher()
        data = fetcher.fetch_data()
        data["em_stress"] = {"composite": 30.0, "stress_level": "LOW"}

        signals = fetcher.compute_signals(data)
        assert "EM_CALM" in signals["special_signal_label"]
        assert signals["special_signal_value"] > 0.0


# ---------------------------------------------------------------------------
# USDINRComposite
# ---------------------------------------------------------------------------


class TestUSDINRComposite:
    def test_all_none_returns_none(self) -> None:
        comp = USDINRComposite()
        assert comp.score(None, None, None, None) is None

    def test_rate_only(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, None, None, None)
        assert result is not None
        # With only rate_norm=1.0 and weight=0.25, composite = 0.25
        assert result == pytest.approx(0.25)

    def test_full_inputs(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        assert result is not None
        assert result == pytest.approx(0.275)

    def test_with_multiple_special_components(self) -> None:
        comp = USDINRComposite()
        result = comp.score(1.0, None, None, None, rbi_reserves=0.5, fpi_flow=0.5, oil=0.5, dxy=0.5)
        # special = mean([0.5, 0.5, 0.5, 0.5]) = 0.5
        # interaction: special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.25 + 0.5*0.45 = 0.475
        # interaction_boost = 0.05, wsum = 0.70
        # composite = 0.475 + 0.05 * 0.70 = 0.51
        assert result is not None
        assert result == pytest.approx(0.51, abs=0.001)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = USDINRComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        carry = USDINRComposite(vol_regime="NEUTRAL", rate_regime="CARRY")
        high_vol = USDINRComposite(vol_regime="HIGH_VOL", rate_regime="NEUTRAL")
        assert carry.weights["rate"] > neutral.weights["rate"]
        assert carry.weights["vol"] < neutral.weights["vol"]
        assert high_vol.weights["vol"] > neutral.weights["vol"]

    def test_special_with_six_components(self) -> None:
        comp = USDINRComposite()
        result = comp.score(
            1.0,
            None,
            None,
            None,
            rbi_reserves=0.5,
            fpi_flow=0.5,
            oil=0.5,
            dxy=0.5,
            em_stress=0.5,
            forward_premium=0.5,
        )
        # special = mean of all six = 0.5
        assert result is not None

    def test_output_clipping(self) -> None:
        comp = USDINRComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, dxy=5.0, oil=5.0)
        assert result is not None
        assert result <= 2.0

    def test_special_computation_average(self) -> None:
        assert _compute_usdinr_special(1.0, 2.0, None, None, None, None) == pytest.approx(1.5)

    def test_special_computation_all_none(self) -> None:
        assert _compute_usdinr_special(None, None, None, None, None, None) is None


# ---------------------------------------------------------------------------
# USDINR Execution
# ---------------------------------------------------------------------------


def _make_bars(
    n: int, open_val: float = 83.0, high: float = 83.5, low: float = 82.5, close: float = 83.2
) -> list[SpotBar]:
    base = datetime.date(2025, 1, 1)
    bars = []
    for i in range(n):
        bars.append(
            SpotBar(
                date=base + datetime.timedelta(days=i),
                pair="USDINR",
                open=open_val,
                high=high,
                low=low,
                close=close,
            )
        )
    return bars


class TestUSDINRExecution:
    def test_rbi_management_discount_active(self) -> None:
        size = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="ACTIVE_DEFENCE",
        )
        size_light = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="LIGHT_TOUCH",
        )
        assert size == pytest.approx(size_light * 0.55)

    def test_rbi_management_discount_accumulation(self) -> None:
        size = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="ACCUMULATION",
        )
        size_light = compute_usdinr_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            rbi_regime="LIGHT_TOUCH",
        )
        assert size == pytest.approx(size_light * 0.85)

    def test_execution_params_detects_rbi_active(self) -> None:
        bars = _make_bars(25)
        params = get_usdinr_execution_params(83.0, "LONG", bars, reserves_mom_pct=-5.0)
        assert params["rbi_regime"] == "ACTIVE_DEFENCE"

    def test_execution_params_detects_rbi_accumulation(self) -> None:
        bars = _make_bars(25)
        params = get_usdinr_execution_params(83.0, "LONG", bars, reserves_mom_pct=3.0)
        assert params["rbi_regime"] == "ACCUMULATION"

    def test_stop_level_long(self) -> None:
        buf, stop = compute_stop_level(83.0, "LONG", 0.50, None, None)
        assert buf is not None
        assert stop == pytest.approx(83.0 - buf)

    def test_stop_level_short(self) -> None:
        buf, stop = compute_stop_level(83.0, "SHORT", 0.50, None, None)
        assert buf is not None
        assert stop == pytest.approx(83.0 + buf)

    def test_adr_computation(self) -> None:
        bars = _make_bars(5, high=83.5, low=82.5)
        adr = average_daily_range(bars)
        assert adr == pytest.approx(1.0)

    def test_mie_long(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "USDINR", 83.0, 83.5, 82.5, 83.2),
            SpotBar(datetime.date(2025, 1, 2), "USDINR", 83.0, 83.8, 82.8, 83.5),
        ]
        mie = mie_proxy_points(bars, "LONG")
        # adverse for long: max(0, open - low)
        # bar1: 83.0 - 82.5 = 0.5
        # bar2: 83.0 - 82.8 = 0.2
        assert mie == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# USDINR Regime
# ---------------------------------------------------------------------------


class TestUSDINRRegime:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.30, 2),
            (0.0, 2),
            (0.51, 3),
            (1.5, 4),
        ],
    )
    def test_hysteresis_no_prior(self, composite: float, expected: int) -> None:
        assert usdinr_hysteresis_tier(composite, None) == expected

    def test_rbi_active_defence_reserves_drop(self) -> None:
        assert detect_rbi_management_regime(-5.0, None, None) == "ACTIVE_DEFENCE"

    def test_rbi_accumulation(self) -> None:
        assert detect_rbi_management_regime(3.0, None, None) == "ACCUMULATION"

    def test_rbi_active_defence_fwd_premium(self) -> None:
        assert detect_rbi_management_regime(0.0, 2.5, None) == "ACTIVE_DEFENCE"

    def test_rbi_light_touch(self) -> None:
        assert detect_rbi_management_regime(-1.0, 1.0, None) == "LIGHT_TOUCH"

    def test_rbi_all_none(self) -> None:
        assert detect_rbi_management_regime(None, None, None) == "LIGHT_TOUCH"

    def test_fpi_strong_inflow(self) -> None:
        assert detect_fpi_flow_regime(2.0, 2.0) == "STRONG_INFLOW"

    def test_fpi_moderate_inflow(self) -> None:
        assert detect_fpi_flow_regime(1.5, 0.0) == "MODERATE_INFLOW"

    def test_fpi_neutral(self) -> None:
        assert detect_fpi_flow_regime(0.5, 0.0) == "NEUTRAL"

    def test_fpi_moderate_outflow(self) -> None:
        assert detect_fpi_flow_regime(-1.5, 0.0) == "MODERATE_OUTFLOW"

    def test_fpi_strong_outflow(self) -> None:
        assert detect_fpi_flow_regime(-2.0, -2.0) == "STRONG_OUTFLOW"

    def test_fpi_none_inputs(self) -> None:
        assert detect_fpi_flow_regime(None, None) == "NEUTRAL"

    def test_thresholds_active_defence(self) -> None:
        t = get_usdinr_thresholds("ACTIVE_DEFENCE")
        assert t["conviction_enter_min"] == 5
        assert t["vol_rank_enter_max"] == pytest.approx(0.82 * 0.80)
        assert t["adr_multiplier"] == pytest.approx(1.2 * 0.90)

    def test_thresholds_accumulation(self) -> None:
        t = get_usdinr_thresholds("ACCUMULATION")
        assert t["conviction_enter_min"] == 4
