"""Tests for pair-specific data fetchers with mocked external calls."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fx_types import SpotBar
from src.pairs.eurusd.fetcher import EURUSDFetcher
from src.pairs.usdinr.fetcher import USDINRFetcher
from src.pairs.usdjpy.fetcher import USDJPYFetcher

# ---------------------------------------------------------------------------
# EURUSDFetcher
# ---------------------------------------------------------------------------


class TestEURUSDFetcher:
    def test_init(self) -> None:
        fetcher = EURUSDFetcher(lookback_days=60)
        assert fetcher.pair == "EURUSD"
        assert fetcher.lookback_days == 60

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    @patch("src.pairs.eurusd.fetcher._fred_latest")
    def test_fetch_all_returns_expected_keys(
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
        assert data["spot"] == pytest.approx(1.05)

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    def test_fetch_data_adds_metadata(
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
        assert data["pair"] == "EURUSD"
        assert "data_quality_score" in data
        assert "date" in data

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    def test_compute_signals_bullish_eur(
        self,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {
            "EURUSD": [SpotBar(datetime.date(2025, 1, 1), "EURUSD", 1.0, 1.1, 0.9, 1.05)]
        }
        mock_yields.return_value = {"us_10y": 3.0, "de_10y": 2.7}
        mock_cot.return_value = []
        mock_cross.return_value = {"vix": 20.0}

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_data()
        signals = fetcher.compute_signals(data)
        assert signals["rate_signal"] == "BULLISH_EUR"
        assert signals["rate_diff"] == pytest.approx(0.3)

    @patch("src.pairs.eurusd.fetcher.fetch_fx_spot")
    @patch("src.pairs.eurusd.fetcher.fetch_yields")
    @patch("src.pairs.eurusd.fetcher.fetch_cot")
    @patch("src.pairs.eurusd.fetcher.fetch_cross_asset")
    @patch("src.pairs.eurusd.fetcher._yf_latest")
    def test_error_handling_fallback(
        self,
        mock_yf: MagicMock,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {}
        mock_yf.return_value = None
        mock_yields.return_value = {}
        mock_cot.return_value = []
        mock_cross.return_value = {}

        fetcher = EURUSDFetcher()
        data = fetcher.fetch_all()
        assert data["spot"] is None
        assert data["yields"] == {}
        assert data["cot"] == {"net_long": None, "open_interest": None, "percentile": None}
        assert data["cross_asset"] == {}


# ---------------------------------------------------------------------------
# USDJPYFetcher
# ---------------------------------------------------------------------------


class TestUSDJPYFetcher:
    def test_init(self) -> None:
        fetcher = USDJPYFetcher(lookback_days=60)
        assert fetcher.pair == "USDJPY"
        assert fetcher.lookback_days == 60

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    @patch("src.pairs.usdjpy.fetcher._fred_latest")
    def test_fetch_all_returns_expected_keys(
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
        assert data["spot"] == pytest.approx(145.5)

    def test_intervention_proximity_computation_near_150(self) -> None:
        fetcher = USDJPYFetcher()
        prox = fetcher._compute_intervention_proximity(149.0)
        assert prox["distance_from_150"] == pytest.approx(1.0)
        assert prox["proximity_score"] == pytest.approx(95.0)

    def test_intervention_proximity_computation_far(self) -> None:
        fetcher = USDJPYFetcher()
        prox = fetcher._compute_intervention_proximity(130.0)
        assert prox["proximity_score"] == pytest.approx(0.0)

    def test_intervention_proximity_none_spot(self) -> None:
        fetcher = USDJPYFetcher()
        prox = fetcher._compute_intervention_proximity(None)
        assert prox["spot"] is None
        assert prox["distance_from_150"] is None
        assert prox["proximity_score"] is None

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    def test_intervention_proximity_in_signals(
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
        prox = signals.get("intervention_proximity")
        assert prox is not None
        assert prox > 70

    @patch("src.pairs.usdjpy.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdjpy.fetcher.fetch_yields")
    @patch("src.pairs.usdjpy.fetcher.fetch_cot")
    @patch("src.pairs.usdjpy.fetcher.fetch_cross_asset")
    @patch("src.pairs.usdjpy.fetcher._yf_latest")
    def test_error_handling_fallback(
        self,
        mock_yf: MagicMock,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {}
        mock_yf.return_value = None
        mock_yields.return_value = {}
        mock_cot.return_value = []
        mock_cross.return_value = {}

        fetcher = USDJPYFetcher()
        data = fetcher.fetch_all()
        assert data["spot"] is None
        assert data["yields"] == {}
        assert data["cot"] == {"net_long": None, "open_interest": None, "percentile": None}
        assert data["cross_asset"] == {}


# ---------------------------------------------------------------------------
# USDINRFetcher
# ---------------------------------------------------------------------------


class TestUSDINRFetcher:
    def test_init(self) -> None:
        fetcher = USDINRFetcher(lookback_days=60)
        assert fetcher.pair == "USDINR"
        assert fetcher.lookback_days == 60

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_fetch_all_returns_expected_keys(
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
        assert data["spot"] == pytest.approx(83.2)

    @patch("src.pairs.usdinr.fetcher._yf_history")
    def test_em_stress_index_computation_high(self, mock_yf_history: MagicMock) -> None:
        import pandas as pd

        mock_yf_history.return_value = pd.DataFrame(
            {"Close": [5.0, 5.5]}, index=pd.date_range("2025-01-01", periods=2)
        )

        fetcher = USDINRFetcher()
        em_stress = fetcher._fetch_em_stress_index()
        assert em_stress["composite"] is not None
        assert em_stress["stress_level"] == "HIGH"
        assert em_stress["components"]["BRL"] is not None

    @patch("src.pairs.usdinr.fetcher._yf_history")
    def test_em_stress_index_computation_low(self, mock_yf_history: MagicMock) -> None:
        import pandas as pd

        mock_yf_history.return_value = pd.DataFrame(
            {"Close": [5.0, 4.9]}, index=pd.date_range("2025-01-01", periods=2)
        )

        fetcher = USDINRFetcher()
        em_stress = fetcher._fetch_em_stress_index()
        assert em_stress["composite"] is not None
        assert em_stress["stress_level"] == "LOW"

    @patch("src.pairs.usdinr.fetcher._yf_history")
    def test_em_stress_index_no_data(self, mock_yf_history: MagicMock) -> None:
        mock_yf_history.return_value = None

        fetcher = USDINRFetcher()
        em_stress = fetcher._fetch_em_stress_index()
        assert em_stress["composite"] is None
        assert em_stress["stress_level"] == "UNKNOWN"

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    def test_em_stress_in_signals(
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
        data["em_stress"] = {"composite": 75.0, "stress_level": "HIGH"}

        signals = fetcher.compute_signals(data)
        assert "EM_STRESS" in signals["special_signal_label"]
        assert signals["special_signal_value"] < 0.0

    @patch("src.pairs.usdinr.fetcher.fetch_fx_spot")
    @patch("src.pairs.usdinr.fetcher.fetch_yields")
    @patch("src.pairs.usdinr.fetcher.fetch_cot")
    @patch("src.pairs.usdinr.fetcher.fetch_cross_asset")
    @patch("src.pairs.usdinr.fetcher._yf_latest")
    def test_error_handling_fallback(
        self,
        mock_yf: MagicMock,
        mock_cross: MagicMock,
        mock_cot: MagicMock,
        mock_yields: MagicMock,
        mock_spot: MagicMock,
    ) -> None:
        mock_spot.return_value = {}
        mock_yf.return_value = None
        mock_yields.return_value = {}
        mock_cot.return_value = []
        mock_cross.return_value = {}

        fetcher = USDINRFetcher()
        data = fetcher.fetch_all()
        assert data["spot"] is None
        assert data["yields"] == {}
        assert data["cot"] == {"net_long": None, "open_interest": None, "percentile": None}
        assert data["cross_asset"] == {}
