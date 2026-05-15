"""Tests for Phase C fetcher enhancements (C1-C4, C6)."""

from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from src.fetchers import fx_spot, macro_calendar, polymarket, yields
from src.fetchers.async_engine import build_master_buffer
from src.fx_types import SpotBar

# ---------------------------------------------------------------------------
# C1: Polygon Treasury Yields
# ---------------------------------------------------------------------------


class TestPolygonTreasuryYields:
    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.yields.requests.get")
    def test_parse_2y_and_10y(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {
            "results": [
                {"maturity": "2_year", "yield": 4.5},
                {"maturity": "10_year", "yield": 4.2},
            ]
        }
        mock_get.return_value.raise_for_status = lambda: None
        result = yields.fetch_polygon_treasury_yields()
        assert result.get("us_2y") == pytest.approx(4.5)
        assert result.get("us_10y") == pytest.approx(4.2)

    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.yields.requests.get")
    def test_empty_results(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status = lambda: None
        assert yields.fetch_polygon_treasury_yields() == {}

    def test_no_api_key_returns_empty(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert yields.fetch_polygon_treasury_yields() == {}

    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.yields.requests.get", side_effect=RuntimeError("network"))
    def test_request_exception_returns_empty(self, mock_get: MagicMock) -> None:
        assert yields.fetch_polygon_treasury_yields() == {}


# ---------------------------------------------------------------------------
# C2: Polygon Daily Grouped FX
# ---------------------------------------------------------------------------


class TestPolygonGroupedFx:
    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.fx_spot.requests.get")
    def test_grouped_parses_tickers(self, mock_get: MagicMock) -> None:
        ts = int(date(2024, 1, 15).strftime("%s")) * 1000
        mock_get.return_value.json.return_value = {
            "status": "OK",
            "results": [
                {"T": "C:EURUSD", "o": 1.08, "h": 1.09, "l": 1.07, "c": 1.085, "v": 100, "t": ts},
                {
                    "T": "C:USDJPY", "o": 148.0, "h": 149.0, "l": 147.0,
                    "c": 148.5, "v": 200, "t": ts,
                },
            ],
        }
        mock_get.return_value.raise_for_status = lambda: None
        result = fx_spot.fetch_fx_spot_polygon_grouped(["EURUSD", "USDJPY", "USDINR"])
        assert "EURUSD" in result
        assert "USDJPY" in result
        assert "USDINR" not in result
        assert result["EURUSD"][0].close == pytest.approx(1.085)
        assert result["USDJPY"][0].close == pytest.approx(148.5)

    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    @patch("src.fetchers.fx_spot.requests.get")
    def test_grouped_error_status(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {"status": "ERROR"}
        mock_get.return_value.raise_for_status = lambda: None
        assert fx_spot.fetch_fx_spot_polygon_grouped(["EURUSD"]) == {}

    def test_grouped_no_key_returns_empty(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert fx_spot.fetch_fx_spot_polygon_grouped(["EURUSD"]) == {}


# ---------------------------------------------------------------------------
# C2 + C6: Async FX spot source tracking
# ---------------------------------------------------------------------------


class TestFxSpotAsyncSources:
    @patch.dict("os.environ", {"POLYGON_API_KEY": "poly_test_key"}, clear=False)
    def test_sources_polygon_grouped(self) -> None:
        ts = int(date(2024, 1, 15).strftime("%s")) * 1000

        def _grouped_resp(url: str, **kwargs: Any) -> Any:
            class _R:
                def json(self) -> dict[str, Any]:
                    return {
                        "status": "OK",
                        "results": [
                            {
                                "T": "C:EURUSD",
                                "o": 1.08,
                                "h": 1.09,
                                "l": 1.07,
                                "c": 1.085,
                                "v": 100,
                                "t": ts,
                            }
                        ],
                    }

                def raise_for_status(self) -> None:
                    pass

            return _R()

        with patch("src.fetchers.fx_spot.requests.get", side_effect=_grouped_resp):

            async def _run() -> tuple[dict[str, list[SpotBar]], dict[str, str]]:
                return await fx_spot.fetch_fx_spot_async(
                    {"EURUSD": {"class": "FX", "tickers": {"spot_ticker": "EURUSD=X"}}},
                    None,  # type: ignore[arg-type]
                )

            bars, sources = asyncio.run(_run())
            assert "EURUSD" in bars
            assert sources.get("EURUSD") == "polygon"

    @patch.dict(
        "os.environ",
        {"ALPHAVANTAGE_API_KEY": "av_test_key"},
        clear=False,
    )
    def test_sources_alphavantage_fallback(self) -> None:
        with patch("src.fetchers.fx_spot.fetch_fx_spot_polygon_grouped", return_value={}):
            with patch("src.fetchers.fx_spot.fetch_fx_spot_polygon", return_value=None):
                with patch(
                    "src.fetchers.fx_spot._alphavantage_fx_daily_request"
                ) as mock_av:
                    av_bars = [
                        SpotBar(
                            date=date(2024, 1, 15),
                            pair="EURUSD",
                            open=1.0,
                            high=1.1,
                            low=0.9,
                            close=1.05,
                        )
                    ]
                    mock_av.return_value = (av_bars, False)

                    async def _run() -> tuple[dict[str, list[SpotBar]], dict[str, str]]:
                        return await fx_spot.fetch_fx_spot_async(
                            {"EURUSD": {"class": "FX", "tickers": {"spot_ticker": "EURUSD=X"}}},
                            None,  # type: ignore[arg-type]
                        )

                    bars, sources = asyncio.run(_run())
                    assert sources.get("EURUSD") == "alphavantage"


# ---------------------------------------------------------------------------
# C3: Polymarket retry
# ---------------------------------------------------------------------------


class TestPolymarketRetry:
    @patch("aiohttp.ClientSession.get")
    def test_retries_then_succeeds(self, mock_get: MagicMock) -> None:
        class _Resp:
            def __init__(self, status: int, json_data: Any) -> None:
                self.status = status
                self._json = json_data

            async def json(self) -> Any:
                return self._json

            async def text(self) -> str:
                return "error"

        mock_get.side_effect = [
            MagicMock(__aenter__=lambda s: _Resp(503, None)),
            MagicMock(__aenter__=lambda s: _Resp(503, None)),
            MagicMock(__aenter__=lambda s: _Resp(200, [])),
        ]

        async def _run() -> list[dict[str, Any]]:
            async with aiohttp.ClientSession() as session:
                return await polymarket.fetch_economics_markets_async(session=session)

        result = asyncio.run(_run())
        assert result == []
        assert mock_get.call_count == 3

    @patch("aiohttp.ClientSession.get")
    def test_all_attempts_fail_returns_empty(self, mock_get: MagicMock) -> None:
        class _Resp:
            def __init__(self, status: int) -> None:
                self.status = status

            async def json(self) -> Any:
                return None

            async def text(self) -> str:
                return "error"

        mock_get.return_value = MagicMock(
            __aenter__=lambda s: _Resp(500),
            __aexit__=lambda *a: None,
        )

        async def _run() -> list[dict[str, Any]]:
            async with aiohttp.ClientSession() as session:
                return await polymarket.fetch_economics_markets_async(session=session)

        t0 = time.perf_counter()
        result = asyncio.run(_run())
        elapsed = time.perf_counter() - t0
        assert result == []
        assert mock_get.call_count == 3
        assert elapsed >= 6.0  # 2s + 4s backoff


# ---------------------------------------------------------------------------
# C4: ForexFactory retry
# ---------------------------------------------------------------------------


class TestForexFactoryRetry:
    @patch("src.fetchers.macro_calendar.requests.get")
    def test_retries_then_succeeds(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = [
            RuntimeError("network"),
            RuntimeError("network"),
            MagicMock(text="<events></events>", raise_for_status=lambda: None),
        ]
        xml = macro_calendar._fetch_forexfactory_weekly_xml()
        assert xml == "<events></events>"
        assert mock_get.call_count == 3

    @patch("src.fetchers.macro_calendar.requests.get")
    def test_all_attempts_fail_returns_none(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = RuntimeError("network")
        t0 = time.perf_counter()
        xml = macro_calendar._fetch_forexfactory_weekly_xml()
        elapsed = time.perf_counter() - t0
        assert xml is None
        assert mock_get.call_count == 3
        assert elapsed >= 6.0  # 2s + 4s backoff


# ---------------------------------------------------------------------------
# C6: Buffer source attribution
# ---------------------------------------------------------------------------


class TestBufferSources:
    @patch("src.fetchers.async_engine.aiohttp.ClientSession")
    @patch("src.fetchers.async_engine.asyncio.gather")
    @patch("src.fetchers.async_engine.load_universe", return_value={})
    def test_sources_key_present(self, mock_load: Any, mock_gather: Any, mock_session: Any) -> None:
        async def _mock_gather(*args: Any, **kwargs: Any) -> Any:
            return (
                ({"EURUSD": []}, {}),  # spots
                {},  # yields
                [],  # cot
                {"vix": 15.0, "dxy": 103.0},  # cross
                {},  # ten
                2.5,  # bei
            )

        mock_gather.side_effect = _mock_gather

        async def _run() -> dict[str, Any]:
            return await build_master_buffer()

        buffer = asyncio.run(_run())
        assert "_sources" in buffer
        src = buffer["_sources"]
        assert "fx_spot" in src
        assert "yields" in src
        assert "cross_asset" in src
        assert "cot" in src
        assert src["cot"] == "cftc"
        assert src["cross_asset"]["vix"] == "yfinance"
