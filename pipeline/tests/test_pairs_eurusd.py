"""Comprehensive tests for EURUSD pair-specific modules."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fx_types import SpotBar
from src.pairs.eurusd.composite import EURUSDComposite
from src.pairs.eurusd.execution import (
    average_daily_range,
    compute_eurusd_position_size,
    compute_kelly_size,
    compute_stop_level,
    get_eurusd_execution_params,
    mie_proxy_points,
)
from src.pairs.eurusd.fetcher import EURUSDFetcher
from src.pairs.eurusd.regime import (
    detect_ecb_policy_regime,
    ecb_regime_adjustment_factor,
    eurusd_hysteresis_tier,
    get_eurusd_thresholds,
)

# ---------------------------------------------------------------------------
# EURUSDFetcher
# ---------------------------------------------------------------------------


class TestEURUSDFetcher:
    def test_init(self) -> None:
        fetcher = EURUSDFetcher(lookback_days=60)
        assert fetcher.pair == "EURUSD"
        assert fetcher.lookback_days == 60

    def test_method_existence(self) -> None:
        fetcher = EURUSDFetcher()
        assert hasattr(fetcher, "fetch_data")
        assert hasattr(fetcher, "fetch_all")
        assert hasattr(fetcher, "compute_signals")
        assert hasattr(fetcher, "compute_composite")
        assert hasattr(fetcher, "classify_regime")
        assert hasattr(fetcher, "compute_execution")

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    @patch("src.pairs.eurusd.fetcher._fred_latest")
    def test_fetch_all_mocks(
        self,
        mock_fred: MagicMock,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "EURUSD": [SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "de_10y": 2.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}
        mock_fred.return_value = 5000.0

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_all()
        assert "spot" in data
        assert "yields" in data
        assert "cot" in data
        assert "cross_asset" in data
        assert "ecb_balance_sheet" in data
        assert "eu_hy_oas" in data
        assert "bund_btp" in data

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    def test_compute_signals_bullish(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "EURUSD": [SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "de_10y": 2.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        assert signals["rate_signal"] == "BEARISH_EUR"
        assert signals["rate_diff"] == 2.0

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    def test_compute_signals_neutral(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "EURUSD": [SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05)]
        }
        mock_yields.return_value = {"us_10y": 3.0, "de_10y": 2.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        assert signals["rate_signal"] == "NEUTRAL"

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    def test_classify_regime(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "EURUSD": [SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05)]
        }
        mock_yields.return_value = {"us_10y": 3.0, "de_10y": 2.5}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        composite = fetcher.compute_composite(signals)
        regime = fetcher.classify_regime(composite, signals)
        assert regime in {
            "BULLISH",
            "BULLISH_WEAK",
            "BEARISH",
            "BEARISH_WEAK",
            "RANGING",
            "RANGING_VOLATILE",
            "BULLISH_VOLATILE",
            "BEARISH_VOLATILE",
        }


# ---------------------------------------------------------------------------
# EURUSDComposite
# ---------------------------------------------------------------------------


class TestEURUSDComposite:
    def test_all_none_returns_none(self) -> None:
        comp = EURUSDComposite()
        assert comp.score(None, None, None, None) is None

    def test_rate_only(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, None, None, None)
        assert result is not None
        assert result == pytest.approx(0.45)

    def test_cot_only(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(None, 0.5, None, None)
        assert result is not None
        assert result == pytest.approx(0.10)

    def test_full_inputs(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        assert result is not None
        assert result == pytest.approx(0.6175, abs=0.001)

    def test_with_special(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0, ecb_bs_trajectory=0.5, bund_btp_spread=0.5)
        assert result is not None
        assert result == pytest.approx(0.725, abs=0.001)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = EURUSDComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        trending = EURUSDComposite(vol_regime="TRENDING", rate_regime="NEUTRAL")
        high_vol = EURUSDComposite(vol_regime="HIGH_VOL", rate_regime="NEUTRAL")
        assert trending.weights["rate"] > neutral.weights["rate"]
        assert trending.weights["vol"] < neutral.weights["vol"]
        assert high_vol.weights["vol"] > neutral.weights["vol"]
        assert high_vol.weights["rate"] < neutral.weights["rate"]

    def test_carry_regime(self) -> None:
        neutral = EURUSDComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        carry = EURUSDComposite(vol_regime="NEUTRAL", rate_regime="CARRY")
        assert carry.weights["rate"] > neutral.weights["rate"]
        assert carry.weights["special"] > neutral.weights["special"]

    def test_interaction_term_effect(self) -> None:
        comp = EURUSDComposite()
        # With rate and cot, interaction adds rate_cot term
        with_rate_cot = comp.score(1.0, 1.0, None, None)
        # rate=1*0.45 + cot=1*0.20 = 0.65, but wsum=0.65, interaction=0.15, so 0.65+0.15*0.65=0.7475
        assert with_rate_cot is not None
        assert with_rate_cot > 0.65

    def test_special_rate_interaction(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(1.0, None, None, None, ecb_bs_trajectory=0.5)
        # special = 0.5, interaction special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.45 + 0.5*0.10 = 0.50
        # interaction boost = 0.05, wsum = 0.55
        # composite = 0.50 + 0.05 * 0.55 = 0.5275
        assert result is not None
        assert result == pytest.approx(0.5275, abs=0.001)

    def test_output_clipping(self) -> None:
        comp = EURUSDComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, ecb_bs_trajectory=5.0)
        assert result is not None
        assert result <= 2.0


# ---------------------------------------------------------------------------
# EURUSD Execution
# ---------------------------------------------------------------------------


def _make_bars(
    n: int, open_val: float = 1.0, high: float = 1.2, low: float = 0.8, close: float = 1.1
) -> list[SpotBar]:
    base = datetime.date(2025, 1, 1)
    bars = []
    for i in range(n):
        bars.append(
            SpotBar(
                date=base + datetime.timedelta(days=i),
                pair="EURUSD",
                open=open_val,
                high=high,
                low=low,
                close=close,
            )
        )
    return bars


class TestEURUSDExecution:
    def test_kelly_sizing_typical(self) -> None:
        size = compute_kelly_size(0.6, 30.0, 20.0)
        assert size > 0.0
        assert size <= 0.01

    def test_kelly_sizing_adr_multiplier(self) -> None:
        thresholds = get_eurusd_thresholds()
        assert thresholds["adr_multiplier"] == 1.3

    def test_stop_level_long(self) -> None:
        buf, stop = compute_stop_level(1.1000, "LONG", 0.0100, None, None)
        assert buf is not None
        assert stop == pytest.approx(1.1000 - buf)

    def test_stop_level_short(self) -> None:
        buf, stop = compute_stop_level(1.1000, "SHORT", 0.0100, None, None)
        assert buf is not None
        assert stop == pytest.approx(1.1000 + buf)

    def test_stop_level_neutral(self) -> None:
        assert compute_stop_level(1.1000, "NEUTRAL", 0.0100, None, None) == (None, None)

    def test_stop_level_none_spot(self) -> None:
        assert compute_stop_level(None, "LONG", 0.0100, None, None) == (None, None)

    def test_position_size_with_correlation(self) -> None:
        size = compute_eurusd_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={"USDJPY": 1.0},
            corr_matrix={"EURUSD": {"USDJPY": 0.8}},
        )
        assert size > 0.0
        assert size <= 100.0 * 0.01

    def test_execution_params_bundle(self) -> None:
        bars = _make_bars(25)
        params = get_eurusd_execution_params(1.1000, "LONG", bars)
        assert "adr" in params
        assert "mie_proxy" in params
        assert "atr" in params
        assert "stop_buffer" in params
        assert "stop_level" in params
        assert params["adr_multiplier"] == 1.3
        assert params["mie_multiplier"] == 1.0

    def test_average_daily_range(self) -> None:
        bars = _make_bars(5, high=1.2, low=0.8)
        adr = average_daily_range(bars)
        assert adr == pytest.approx(0.4)

    def test_mie_long(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05),
            SpotBar(datetime.date(2025, 1, 2), "EURUSD", 1.0, 1.2, 0.95, 1.1),
        ]
        mie = mie_proxy_points(bars, "LONG")
        assert mie == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# EURUSD Regime
# ---------------------------------------------------------------------------


class TestEURUSDRegime:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.35, 2),
            (0.0, 2),
            (0.46, 3),
            (1.5, 4),
        ],
    )
    def test_hysteresis_no_prior(self, composite: float, expected: int) -> None:
        assert eurusd_hysteresis_tier(composite, None) == expected

    def test_hysteresis_stays_at_four(self) -> None:
        assert eurusd_hysteresis_tier(0.90, 4) == 4
        assert eurusd_hysteresis_tier(0.80, 4) == 3

    def test_ecb_policy_qe(self) -> None:
        assert detect_ecb_policy_regime(-0.5, 3.0, 60.0) == "QE"

    def test_ecb_policy_qt(self) -> None:
        assert detect_ecb_policy_regime(2.5, -3.0, -60.0) == "QT"

    def test_ecb_policy_neutral(self) -> None:
        assert detect_ecb_policy_regime(1.0, 0.0, None) == "NEUTRAL"

    def test_ecb_adjustment_qt_negative(self) -> None:
        assert ecb_regime_adjustment_factor("QT", -1.0) == pytest.approx(1.15)
        assert ecb_regime_adjustment_factor("QT", 1.0) == pytest.approx(0.90)

    def test_ecb_adjustment_qe_positive(self) -> None:
        assert ecb_regime_adjustment_factor("QE", 1.0) == pytest.approx(1.15)
        assert ecb_regime_adjustment_factor("QE", -1.0) == pytest.approx(0.90)

    def test_thresholds(self) -> None:
        t = get_eurusd_thresholds()
        assert t["adr_multiplier"] == 1.3
        assert t["mie_multiplier"] == 1.0
        assert t["conviction_enter_min"] == 3
