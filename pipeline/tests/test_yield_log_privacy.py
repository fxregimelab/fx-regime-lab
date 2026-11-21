"""Yield adapter diagnostics must not echo provider data or configured identifiers."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.fetchers import yields
from src.fetchers.async_engine import AsyncFetcher

SECRET = "synthetic-yield-secret"


def _assert_private_failure_log(caplog: pytest.LogCaptureFixture, error_name: str) -> None:
    assert error_name in caplog.text
    assert SECRET not in caplog.text


def test_sync_yfinance_exception_log_is_private_and_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    ticker = MagicMock()
    ticker.history.side_effect = RuntimeError(f"provider payload={SECRET}")
    monkeypatch.setattr(yields, "_yfinance", lambda: SimpleNamespace(Ticker=lambda _id: ticker))

    assert yields._yf_leg(f"ticker-{SECRET}", f"label-{SECRET}", "5d") is None
    _assert_private_failure_log(caplog, "RuntimeError")


def test_sync_fred_exception_log_is_private_and_fallback_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    fred = MagicMock()
    fred.get_series_latest_release.side_effect = [
        RuntimeError(f"provider payload={SECRET}"),
        pd.Series([3.25]),
    ]

    assert yields._fred_leg(fred, (f"bad-{SECRET}", "DGS2"), f"label-{SECRET}") == 3.25
    assert fred.get_series_latest_release.call_count == 2
    _assert_private_failure_log(caplog, "RuntimeError")


@pytest.mark.parametrize("failure_at", ["download", "parse"])
def test_sync_yfinance_batch_exception_logs_are_private_and_keep_none_fallbacks(
    failure_at: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    if failure_at == "download":
        download = MagicMock(side_effect=RuntimeError(f"download body={SECRET}"))
    else:
        closes = MagicMock()
        closes.__getitem__.side_effect = ValueError(f"parse value={SECRET}")
        frame = MagicMock()
        frame.empty = False
        frame.__contains__.return_value = True
        frame.__getitem__.return_value = closes
        download = MagicMock(return_value=frame)
    monkeypatch.setattr(yields, "_yfinance", lambda: SimpleNamespace(download=download))
    tickers = {f"leg-{SECRET}": f"ticker-{SECRET}", "safe-leg": "^TNX"}

    assert yields._fetch_yf_legs(tickers, "5d") == {
        f"leg-{SECRET}": None,
        "safe-leg": None,
    }
    error_name = "RuntimeError" if failure_at == "download" else "ValueError"
    _assert_private_failure_log(caplog, error_name)


def test_ecb_assets_exception_log_is_private_and_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    monkeypatch.setenv("FRED_API_KEY", f"key-{SECRET}")
    fred = MagicMock()
    fred.get_series_latest_release.side_effect = RuntimeError(f"response={SECRET}")

    assert yields.fetch_ecb_balance_sheet(fred) is None
    _assert_private_failure_log(caplog, "RuntimeError")


def test_async_yfinance_exception_log_is_private_and_returns_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    ticker = MagicMock()
    ticker.history.side_effect = RuntimeError(f"provider payload={SECRET}")
    monkeypatch.setattr(yields, "_yfinance", lambda: SimpleNamespace(Ticker=lambda _id: ticker))

    result = asyncio.run(
        yields._yahoo_yield_latest_async(f"ticker-{SECRET}", "5d", AsyncFetcher())
    )
    assert result is None
    _assert_private_failure_log(caplog, "RuntimeError")


@pytest.mark.parametrize(
    ("body", "error_name"),
    [
        (f'{{"observations": [{SECRET}'.encode(), "JSONDecodeError"),
        (f'{{"observations": [{{"value": "{SECRET}"}}]}}'.encode(), "ValueError"),
    ],
)
def test_async_fred_parse_logs_are_private_and_return_none(
    body: bytes,
    error_name: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    monkeypatch.setenv("FRED_API_KEY", f"key-{SECRET}")
    fetcher = MagicMock(fetch_with_retry=AsyncMock(return_value=(200, body)))

    result = asyncio.run(
        yields._fred_latest_async(f"series-{SECRET}", MagicMock(), fetcher)
    )
    assert result is None
    _assert_private_failure_log(caplog, error_name)


def test_gathered_leg_exception_log_is_private_and_result_stays_empty(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    monkeypatch.setattr(
        yields,
        "_fetch_yield_leg_async",
        AsyncMock(side_effect=RuntimeError(f"worker payload={SECRET}")),
    )
    universe = {
        "EURUSD": {
            "class": "FX",
            "tickers": {"yield_base": f"series-{SECRET}", "yield_quote": None},
        }
    }

    result = asyncio.run(yields.fetch_yields_async(universe, MagicMock(), fetcher=AsyncFetcher()))
    assert result == {}
    _assert_private_failure_log(caplog, "RuntimeError")


def test_async_cancellation_behavior_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    ticker = MagicMock()
    ticker.history.side_effect = asyncio.CancelledError
    monkeypatch.setattr(yields, "_yfinance", lambda: SimpleNamespace(Ticker=lambda _id: ticker))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(yields._yahoo_yield_latest_async("^TNX", "5d", AsyncFetcher()))


def test_async_fred_cancellation_behavior_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRED_API_KEY", f"key-{SECRET}")
    fetcher = MagicMock(fetch_with_retry=AsyncMock(side_effect=asyncio.CancelledError))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(yields._fred_latest_async("DGS2", MagicMock(), fetcher))


def test_us_async_leg_still_falls_back_from_fred_to_yahoo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fred = AsyncMock(return_value=None)
    yahoo = AsyncMock(return_value=4.25)
    monkeypatch.setattr(yields, "_fred_latest_async", fred)
    monkeypatch.setattr(yields, "_yahoo_yield_latest_async", yahoo)

    result = asyncio.run(
        yields._fetch_yield_leg_async("^UST2Y", MagicMock(), AsyncFetcher(), "5d")
    )

    assert result == ("^UST2Y", 4.25)
    fred.assert_awaited_once()
    yahoo.assert_awaited_once()


def test_success_values_and_source_context_are_preserved(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    monkeypatch.setenv("FRED_API_KEY", f"key-{SECRET}")
    ticker = MagicMock()
    ticker.history.return_value = pd.DataFrame({"Close": [4.5]})
    monkeypatch.setattr(yields, "_yfinance", lambda: SimpleNamespace(Ticker=lambda _id: ticker))
    fetcher = MagicMock(
        fetch_with_retry=AsyncMock(
            return_value=(200, b'{"observations": [{"value": "2.75"}]}')
        )
    )

    assert asyncio.run(yields._yahoo_yield_latest_async("^TNX", "5d", AsyncFetcher())) == 4.5
    assert asyncio.run(yields._fred_latest_async("DGS2", MagicMock(), fetcher)) == 2.75
    assert "ticker=^TNX value=4.5" in caplog.text
    assert "series_id=DGS2 value=2.75" in caplog.text


def test_unrecognized_configured_identifier_is_redacted_on_success(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=yields.__name__)
    monkeypatch.setenv("FRED_API_KEY", f"key-{SECRET}")
    fetcher = MagicMock(
        fetch_with_retry=AsyncMock(
            return_value=(200, b'{"observations": [{"value": "2.75"}]}')
        )
    )

    result = asyncio.run(
        yields._fred_latest_async(f"configured-{SECRET}", MagicMock(), fetcher)
    )

    assert result == 2.75
    assert "series_id=<unrecognized-yield-id> value=2.75" in caplog.text
    assert SECRET not in caplog.text
