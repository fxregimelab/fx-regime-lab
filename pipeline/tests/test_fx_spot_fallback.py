"""Tests for P1-T4: 3-tier FX spot fallback chain (Polygon → AV → yfinance)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.fetchers import fx_spot
from src.types import SpotBar


class _FakeResponse:
    def __init__(self, json_data: dict[str, Any], status: int = 200) -> None:
        self._json = json_data
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._json


def _polygon_response(pair: str) -> dict[str, Any]:
    ts = int(datetime.combine(date(2024, 1, 15), datetime.min.time()).timestamp()) * 1000
    return {
        "ticker": f"C:{pair.replace('/', '')}",
        "status": "OK",
        "results": [
            {
                "o": 1.0850,
                "h": 1.0870,
                "l": 1.0830,
                "c": 1.0860,
                "v": 1000,
                "t": ts,
            }
        ],
    }


def _av_response(pair: str) -> dict[str, Any]:
    return {
        "Time Series FX (Daily)": {
            "2024-01-15": {
                "1. open": "1.0850",
                "2. high": "1.0870",
                "3. low": "1.0830",
                "4. close": "1.0860",
            }
        }
    }


class TestFetchFxSpotFallback:
    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.fx_spot.requests.get")
    @patch("src.fetchers.fx_spot._alphavantage_fx_daily_request")
    @patch("src.fetchers.fx_spot._fetch_fx_spot_yfinance_batch")
    def test_polygon_succeeds_no_fallback(
        self,
        mock_yf: MagicMock,
        mock_av: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Polygon returns data → AV and yfinance are NOT called."""
        mock_get.return_value = _FakeResponse(_polygon_response("EUR/USD"))
        mock_av.return_value = ([], False)
        mock_yf.return_value = {}

        result = fx_spot.fetch_fx_spot(lookback_days=30)

        assert "EURUSD" in result
        assert len(result["EURUSD"]) == 1
        assert result["EURUSD"][0].close == pytest.approx(1.0860, abs=1e-4)
        mock_av.assert_not_called()
        mock_yf.assert_not_called()

    @patch.dict(
        "os.environ",
        {"POLYGON_API_KEY": "poly_test_key", "ALPHAVANTAGE_API_KEY": "av_test_key"},
        clear=False,
    )
    @patch("src.fetchers.fx_spot.requests.get")
    @patch("src.fetchers.fx_spot._alphavantage_fx_daily_request")
    @patch("src.fetchers.fx_spot._fetch_fx_spot_yfinance_batch")
    def test_polygon_fails_av_succeeds(
        self,
        mock_yf: MagicMock,
        mock_av: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Polygon fails → Alpha Vantage succeeds → yfinance NOT called."""
        mock_get.return_value = _FakeResponse({"status": "ERROR"})
        bars = [
            SpotBar(date=date.today() - timedelta(days=1), pair="EURUSD", open=1.0, high=1.1, low=0.9, close=1.05)
        ]
        mock_av.return_value = (bars, False)
        mock_yf.return_value = {}

        result = fx_spot.fetch_fx_spot(lookback_days=30)

        assert "EURUSD" in result
        assert len(result["EURUSD"]) == 1
        assert result["EURUSD"][0].close == pytest.approx(1.05, abs=1e-4)
        mock_yf.assert_not_called()

    @patch.dict(
        "os.environ",
        {"POLYGON_API_KEY": "poly_test_key", "ALPHAVANTAGE_API_KEY": "av_test_key"},
        clear=False,
    )
    @patch("src.fetchers.fx_spot.requests.get")
    @patch("src.fetchers.fx_spot._alphavantage_fx_daily_request")
    @patch("src.fetchers.fx_spot._fetch_fx_spot_yfinance_batch")
    def test_polygon_av_fail_yfinance_succeeds(
        self,
        mock_yf: MagicMock,
        mock_av: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Polygon + AV both fail → yfinance succeeds."""
        mock_get.return_value = _FakeResponse({"status": "ERROR"})
        mock_av.return_value = ([], True)
        bars = [
            SpotBar(date=date(2024, 1, 15), pair="EURUSD", open=1.0, high=1.1, low=0.9, close=1.03)
        ]
        mock_yf.return_value = {"EURUSD": bars}

        result = fx_spot.fetch_fx_spot(lookback_days=30)

        assert "EURUSD" in result
        assert len(result["EURUSD"]) == 1
        assert result["EURUSD"][0].close == pytest.approx(1.03, abs=1e-4)

    @patch.dict(
        "os.environ",
        {"POLYGON_API_KEY": "poly_test_key", "ALPHAVANTAGE_API_KEY": "av_test_key"},
        clear=False,
    )
    @patch("src.fetchers.fx_spot.requests.get")
    @patch("src.fetchers.fx_spot._alphavantage_fx_daily_request")
    @patch("src.fetchers.fx_spot._fetch_fx_spot_yfinance_batch")
    def test_all_sources_fail_graceful(
        self,
        mock_yf: MagicMock,
        mock_av: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """All three sources fail → return empty bars (pipeline continues)."""
        mock_get.return_value = _FakeResponse({"status": "ERROR"})
        mock_av.return_value = ([], True)
        mock_yf.return_value = {}

        result = fx_spot.fetch_fx_spot(lookback_days=30)

        assert "EURUSD" in result
        assert result["EURUSD"] == []

    @patch.dict("os.environ", {"ALPHAVANTAGE_API_KEY": "av_test_key"}, clear=False)
    def test_no_polygon_key_skips_to_av(self) -> None:
        """Missing POLYGON_API_KEY → Polygon skipped, AV attempted."""
        with patch("src.fetchers.fx_spot._alphavantage_fx_daily_request") as mock_av:
            with patch("src.fetchers.fx_spot._fetch_fx_spot_yfinance_batch") as mock_yf:
                mock_av.return_value = ([], False)
                mock_yf.return_value = {}
                fx_spot.fetch_fx_spot(lookback_days=30)
                mock_av.assert_called()


class TestPolygonParse:
    def test_parse_polygon_aggs_basic(self) -> None:
        data = {
            "results": [
                {
                    "o": 1.0,
                    "h": 1.1,
                    "l": 0.9,
                    "c": 1.05,
                    "v": 500,
                    "t": 1705276800000,
                }
            ]
        }
        bars = fx_spot._parse_polygon_aggs("EURUSD", data)
        assert len(bars) == 1
        bar = bars[0]
        assert bar.pair == "EURUSD"
        assert bar.open == pytest.approx(1.0, abs=1e-6)
        assert bar.high == pytest.approx(1.1, abs=1e-6)
        assert bar.low == pytest.approx(0.9, abs=1e-6)
        assert bar.close == pytest.approx(1.05, abs=1e-6)
        assert bar.volume == pytest.approx(500, abs=1e-6)

    def test_parse_polygon_aggs_empty(self) -> None:
        assert fx_spot._parse_polygon_aggs("EUR/USD", {}) == []
        assert fx_spot._parse_polygon_aggs("EUR/USD", {"results": []}) == []

    def test_polygon_ticker_format(self) -> None:
        assert fx_spot._polygon_ticker("EURUSD") == "C:EURUSD"
        assert fx_spot._polygon_ticker("USDJPY") == "C:USDJPY"
        assert fx_spot._polygon_ticker("EUR/USD") == "C:EURUSD"
