"""Provider failures and receipt clocks must not corrupt acquisition evidence."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

from src.fetchers import fx_spot
from src.fetchers.async_engine import AsyncFetcher

RECEIPT = datetime(2026, 9, 27, 23, 59, tzinfo=UTC)
SECRET = "synthetic-provider-secret"


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"Open": [1.0], "High": [1.2], "Low": [0.9], "Close": [1.1], "Volume": [4]},
        index=pd.DatetimeIndex(["2026-09-25"], tz="UTC"),
    )


@pytest.mark.parametrize("provider", ["polygon", "alphavantage", "yahoo", "yahoo_async"])
def test_request_failure_logs_cannot_echo_secret_urls(
    provider: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    failure = requests.HTTPError(f"403 for https://provider.invalid/query?apiKey={SECRET}")
    downloader = MagicMock(side_effect=failure)
    monkeypatch.setattr(requests, "get", downloader)
    monkeypatch.setattr(fx_spot, "_yfinance", lambda: MagicMock(download=downloader))
    monkeypatch.setenv("POLYGON_API_KEY", SECRET)
    if provider == "polygon":
        assert fx_spot.fetch_fx_spot_polygon("EURUSD") is None
    elif provider == "alphavantage":
        assert fx_spot._alphavantage_fx_daily_request(
            "EURUSD", api_key=SECRET, lookback_days=30,
        ) == ([], False)
    elif provider == "yahoo":
        assert fx_spot._fetch_fx_spot_yfinance_batch(
            {"EURUSD": "EURUSD=X"}, ["EURUSD"], 30,
        ) == {"EURUSD": []}
    else:
        assert asyncio.run(fx_spot._fetch_one_spot_async(
            "EURUSD", "EURUSD=X", "30d", AsyncFetcher(),
        )) == ("EURUSD", [])
    assert downloader.call_count == 1
    assert "HTTPError" in caplog.text
    assert SECRET not in caplog.text
    assert "provider.invalid" not in caplog.text


def test_polygon_request_uses_utc_calendar_date(monkeypatch: pytest.MonkeyPatch) -> None:
    class LocalDate(date):
        @classmethod
        def today(cls) -> LocalDate:
            return cls(2026, 9, 28)

    monkeypatch.setattr(fx_spot, "date", LocalDate)
    monkeypatch.setattr(fx_spot, "_retrieval_time", lambda value: value or RECEIPT)
    get = MagicMock(return_value=MagicMock(json=lambda: {"results": []}))
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("POLYGON_API_KEY", SECRET)
    fx_spot.fetch_fx_spot_polygon("EURUSD", lookback_days=30)
    assert get.call_args.args[0].endswith("/2026-08-23/2026-09-27")


@pytest.mark.parametrize("provider", ["polygon", "alphavantage"])
def test_http_receipt_precedes_json_transformation(
    provider: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [RECEIPT]
    monkeypatch.setattr(fx_spot, "_retrieval_time", lambda value: value or clock[0])

    def payload() -> dict[str, Any]:
        clock[0] += timedelta(minutes=5)
        if provider == "polygon":
            return {"results": [{"t": 1790294400000, "o": 1, "h": 1.2, "l": 0.9, "c": 1.1}]}
        return {"Time Series FX (Daily)": {"2026-09-25": {
            "1. open": "1", "2. high": "1.2", "3. low": "0.9", "4. close": "1.1",
        }}}

    monkeypatch.setattr(requests, "get", MagicMock(return_value=MagicMock(json=payload)))
    monkeypatch.setenv("POLYGON_API_KEY", SECRET)
    if provider == "polygon":
        bars = fx_spot.fetch_fx_spot_polygon("EURUSD")
    else:
        bars, _ = fx_spot._alphavantage_fx_daily_request(
            "EURUSD", api_key=SECRET, lookback_days=30,
        )
    assert bars and bars[0].retrieved_at == RECEIPT


def test_yahoo_batch_shares_download_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = pd.concat({"EURUSD=X": frame(), "JPY=X": frame()}, axis=1)
    monkeypatch.setattr(fx_spot, "_yfinance", lambda: MagicMock(download=lambda *a, **k: raw))
    clock = [RECEIPT]
    monkeypatch.setattr(fx_spot, "_retrieval_time", lambda value: value or clock[0])
    original = fx_spot._bars_from_yf_frame

    def parse(*args: Any, **kwargs: Any) -> Any:
        clock[0] += timedelta(minutes=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(fx_spot, "_bars_from_yf_frame", parse)
    bars = fx_spot._fetch_fx_spot_yfinance_batch(
        {"EURUSD": "EURUSD=X", "USDJPY": "JPY=X"}, ["EURUSD", "USDJPY"], 30,
    )
    assert [bars[p][0].retrieved_at for p in bars] == [RECEIPT, RECEIPT]


def test_async_yahoo_captures_receipt_before_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fx_spot, "_yfinance", lambda: MagicMock(download=lambda *a, **k: frame()))
    clock = [RECEIPT]
    monkeypatch.setattr(fx_spot, "_retrieval_time", lambda value: value or clock[0])
    original = fx_spot._bars_from_yf_frame

    def parse(*args: Any, **kwargs: Any) -> Any:
        clock[0] += timedelta(minutes=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(fx_spot, "_bars_from_yf_frame", parse)
    _, bars = asyncio.run(fx_spot._fetch_one_spot_async(
        "EURUSD", "EURUSD=X", "30d", AsyncFetcher(),
    ))
    assert bars[0].retrieved_at == RECEIPT


def test_unadjusted_yahoo_evidence_is_not_labeled_adjusted() -> None:
    bars = fx_spot._bars_from_yf_frame(
        frame(), "EURUSD", "EURUSD=X", retrieved_at=RECEIPT, adjusted=False,
    )
    assert bars[0].provider_metadata["adjusted"] is False
