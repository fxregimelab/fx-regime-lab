"""Comprehensive tests for USDJPY pair-specific modules."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fx_types import SpotBar
from src.pairs.usdjpy.composite import USDJPYComposite, _compute_usdjpy_special
from src.pairs.usdjpy.execution import (
    average_daily_range,
    compute_stop_level,
    compute_usdjpy_position_size,
    get_usdjpy_execution_params,
    mie_proxy_points,
)
from src.pairs.usdjpy.fetcher import USDJPYFetcher
from src.pairs.usdjpy.regime import (
    detect_boj_intervention_regime,
    get_usdjpy_thresholds,
    usdjpy_hysteresis_tier,
)

# ---------------------------------------------------------------------------
# USDJPYFetcher
# ---------------------------------------------------------------------------


class TestUSDJPYFetcher:
    def test_init(self) -> None:
        fetcher = USDJPYFetcher(lookback_days=60)
        assert fetcher.pair == "USDJPY"
        assert fetcher.lookback_days == 60

    def test_method_existence(self) -> None:
        fetcher = USDJPYFetcher()
        assert hasattr(fetcher, "fetch_data")
        assert hasattr(fetcher, "fetch_all")
        assert hasattr(fetcher, "compute_signals")
        assert hasattr(fetcher, "compute_composite")
        assert hasattr(fetcher, "classify_regime")
        assert hasattr(fetcher, "compute_execution")

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    @patch("src.pairs.usdjpy.fetcher._fred_latest")
    def test_fetch_all_mocks(
        self,
        mock_fred: MagicMock,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDJPY": [SpotBar(datetime.date(2025, 1, 1), "USDJPY", 145.0, 146.0, 144.0, 145.5)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "jp_10y": 1.0}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}
        mock_fred.return_value = 0.5

        fetcher = USDJPYFetcher()
        data = fetcher.fetch_all()
        assert "spot" in data
        assert "yields" in data
        assert "cot" in data
        assert "cross_asset" in data
        assert "boj_rate" in data
        assert "japan_cpi" in data
        assert "intervention" in data

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    def test_compute_signals_bullish_usd(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDJPY": [SpotBar(datetime.date(2025, 1, 1), "USDJPY", 145.0, 146.0, 144.0, 145.5)]
        }
        mock_yields.return_value = {"us_10y": 4.5, "jp_10y": 1.0}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDJPYFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        assert signals["rate_signal"] == "BULLISH_USD"
        assert signals["rate_diff"] == 3.5

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    def test_intervention_proximity(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "USDJPY": [SpotBar(datetime.date(2025, 1, 1), "USDJPY", 149.0, 150.0, 148.0, 149.5)]
        }
        mock_yields.return_value = {"us_10y": 3.0, "jp_10y": 1.0}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = USDJPYFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        # Spot at 149, close to 150 intervention level
        prox = signals.get("intervention_proximity")
        assert prox is not None
        assert prox > 70

    def test_intervention_proximity_score(self) -> None:
        fetcher = USDJPYFetcher()
        prox = fetcher._compute_intervention_proximity(149.0)
        assert prox["distance_from_150"] == pytest.approx(1.0)
        assert prox["proximity_score"] == pytest.approx(95.0)

    def test_intervention_proximity_far(self) -> None:
        fetcher = USDJPYFetcher()
        prox = fetcher._compute_intervention_proximity(130.0)
        assert prox["proximity_score"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# USDJPYComposite
# ---------------------------------------------------------------------------


class TestUSDJPYComposite:
    def test_all_none_returns_none(self) -> None:
        comp = USDJPYComposite()
        assert comp.score(None, None, None, None) is None

    def test_rate_only(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, None, None, None)
        assert result is not None
        assert result == pytest.approx(0.30)

    def test_full_inputs(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, 0.5, 0.0, 0.0)
        assert result is not None
        assert result == pytest.approx(0.40)

    def test_with_intervention_proximity(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, None, None, None, boj_intervention_proximity=0.5)
        assert result is not None
        assert result == pytest.approx(0.3975, abs=0.001)

    def test_regime_conditional_weight_changes(self) -> None:
        neutral = USDJPYComposite(vol_regime="NEUTRAL", rate_regime="NEUTRAL")
        high_vol = USDJPYComposite(vol_regime="HIGH_VOL", rate_regime="NEUTRAL")
        assert high_vol.weights["vol"] > neutral.weights["vol"]
        assert high_vol.weights["rate"] < neutral.weights["rate"]

    def test_interaction_special_rate(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(1.0, None, None, None, boj_intervention_proximity=0.5)
        # special = 0.5, interaction special_rate = 0.5*1.0*0.10 = 0.05
        # base = 1.0*0.30 + 0.5*0.15 = 0.375
        # interaction boost = 0.05, wsum = 0.45
        # composite = 0.375 + 0.05 * 0.45 = 0.3975
        assert result is not None
        assert result == pytest.approx(0.3975, abs=0.001)

    def test_output_clipping(self) -> None:
        comp = USDJPYComposite()
        result = comp.score(5.0, 5.0, 5.0, 5.0, vix=5.0)
        assert result is not None
        assert result <= 2.0

    def test_special_computation_average(self) -> None:
        assert _compute_usdjpy_special(1.0, 3.0, None) == pytest.approx(2.0)

    def test_special_computation_all_none(self) -> None:
        assert _compute_usdjpy_special(None, None, None) is None


# ---------------------------------------------------------------------------
# USDJPY Execution
# ---------------------------------------------------------------------------


def _make_bars(
    n: int, open_val: float = 145.0, high: float = 146.0, low: float = 144.0, close: float = 145.5
) -> list[SpotBar]:
    base = datetime.date(2025, 1, 1)
    bars = []
    for i in range(n):
        bars.append(
            SpotBar(
                date=base + datetime.timedelta(days=i),
                pair="USDJPY",
                open=open_val,
                high=high,
                low=low,
                close=close,
            )
        )
    return bars


class TestUSDJPYExecution:
    def test_intervention_aware_stop_active(self) -> None:
        buf_normal, _ = compute_stop_level(150.0, "LONG", 1.0, None, None, "DORMANT")
        buf_active, _ = compute_stop_level(150.0, "LONG", 1.0, None, None, "ACTIVE")
        assert buf_active is not None
        assert buf_normal is not None
        assert buf_active == pytest.approx(buf_normal * 1.4)

    def test_intervention_aware_stop_proximal(self) -> None:
        buf_normal, _ = compute_stop_level(150.0, "LONG", 1.0, None, None, "DORMANT")
        buf_prox, _ = compute_stop_level(150.0, "LONG", 1.0, None, None, "PROXIMAL")
        assert buf_prox is not None
        assert buf_normal is not None
        assert buf_prox == pytest.approx(buf_normal * 1.2)

    def test_intervention_discount_active(self) -> None:
        size = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="ACTIVE",
        )
        size_dormant = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="DORMANT",
        )
        assert size == pytest.approx(size_dormant * 0.60)

    def test_intervention_discount_proximal(self) -> None:
        size = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="PROXIMAL",
        )
        size_dormant = compute_usdjpy_position_size(
            base_size=100.0,
            win_rate=0.6,
            avg_win_bps=30.0,
            avg_loss_bps=20.0,
            portfolio={},
            corr_matrix={},
            boj_regime="DORMANT",
        )
        assert size == pytest.approx(size_dormant * 0.80)

    def test_execution_params_detects_boj_active(self) -> None:
        bars = _make_bars(25)
        params = get_usdjpy_execution_params(
            150.0, "LONG", bars, last_intervention_high=150.0, days_since_last_intervention=10
        )
        assert params["boj_regime"] == "ACTIVE"

    def test_execution_params_detects_boj_proximal(self) -> None:
        bars = _make_bars(25)
        params = get_usdjpy_execution_params(
            300.0, "LONG", bars, last_intervention_high=150.0, days_since_last_intervention=10
        )
        assert params["boj_regime"] == "PROXIMAL"

    def test_execution_params_boj_dormant_stale(self) -> None:
        bars = _make_bars(25)
        params = get_usdjpy_execution_params(
            150.0, "LONG", bars, last_intervention_high=150.0, days_since_last_intervention=200
        )
        assert params["boj_regime"] == "DORMANT"

    def test_adr_computation(self) -> None:
        bars = _make_bars(5, high=146.0, low=144.0)
        adr = average_daily_range(bars)
        assert adr == pytest.approx(2.0)

    def test_mie_short(self) -> None:
        bars = [
            SpotBar(datetime.date(2025, 1, 1), "USDJPY", 145.0, 146.0, 144.0, 145.5),
            SpotBar(datetime.date(2025, 1, 2), "USDJPY", 145.0, 147.0, 144.5, 146.0),
        ]
        mie = mie_proxy_points(bars, "SHORT")
        # adverse for short: max(0, high - open)
        # bar1: 146.0 - 145.0 = 1.0
        # bar2: 147.0 - 145.0 = 2.0
        assert mie == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# USDJPY Regime
# ---------------------------------------------------------------------------


class TestUSDJPYRegime:
    @pytest.mark.parametrize(
        "composite,expected",
        [
            (-2.0, 0),
            (-1.0, 1),
            (-0.40, 2),
            (0.0, 2),
            (0.41, 3),
            (1.5, 4),
        ],
    )
    def test_hysteresis_no_prior(self, composite: float, expected: int) -> None:
        assert usdjpy_hysteresis_tier(composite, None) == expected

    def test_intervention_active_near_high(self) -> None:
        assert detect_boj_intervention_regime(150.0, 150.0, None, 10) == "ACTIVE"

    def test_intervention_active_near_low(self) -> None:
        assert detect_boj_intervention_regime(140.0, None, 140.0, 10) == "ACTIVE"

    def test_intervention_proximal(self) -> None:
        assert detect_boj_intervention_regime(300.0, 150.0, None, 10) == "PROXIMAL"

    def test_intervention_dormant_far_away(self) -> None:
        assert detect_boj_intervention_regime(500.0, 150.0, None, 10) == "DORMANT"

    def test_intervention_dormant_stale(self) -> None:
        assert detect_boj_intervention_regime(150.0, 150.0, None, 200) == "DORMANT"

    def test_thresholds_active_adjustments(self) -> None:
        t = get_usdjpy_thresholds("ACTIVE")
        assert t["conviction_enter_min"] == 4
        assert t["vol_rank_enter_max"] == pytest.approx(0.90 * 0.85)
        assert t["mie_multiplier"] == pytest.approx(1.2 * 1.3)

    def test_thresholds_proximal_adjustments(self) -> None:
        t = get_usdjpy_thresholds("PROXIMAL")
        assert t["conviction_enter_min"] == 3
        assert t["vol_rank_enter_max"] == pytest.approx(0.90 * 0.92)
        assert t["mie_multiplier"] == pytest.approx(1.2 * 1.15)
