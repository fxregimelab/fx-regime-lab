"""Ingestion diagnostics must not echo transport credentials."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.fetchers import async_engine
from src.fetchers.buffer_keys import KEY_COT, KEY_FX_SPOT, KEY_YIELDS

SECRET = "synthetic-secret"


@pytest.mark.parametrize("url", [
    f"https://provider.invalid/query?api_key={SECRET}",
    f"https://provider.invalid/query?apiKey={SECRET}",
    f"https://provider.invalid/{SECRET}?TOKEN={SECRET}#{SECRET}",
    f"https://user:{SECRET}@provider.invalid/query",
])
def test_log_url_contains_only_origin(url: str) -> None:
    assert async_engine._safe_url_for_log(url) == "https://provider.invalid"


@pytest.mark.parametrize("url", ["not a URL", "https://[broken", "file:///secret"])
def test_bad_url_is_not_echoed(url: str) -> None:
    assert async_engine._safe_url_for_log(url) == "<invalid-url>"


@pytest.mark.parametrize("status", [200, 503, -1])
def test_retry_logs_are_private_and_behavior_is_preserved(
    status: int, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO, logger=async_engine.__name__)
    response = MagicMock(status=status, read=AsyncMock(return_value=b"body"))
    context = MagicMock(__aenter__=AsyncMock(return_value=response), __aexit__=AsyncMock())
    if status == -1:
        context.__aenter__.side_effect = RuntimeError(f"failed URL apiKey={SECRET}")
    session = MagicMock(get=MagicMock(return_value=context))
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)
    result = asyncio.run(async_engine.AsyncFetcher().fetch_with_retry(
        f"https://user:{SECRET}@provider.invalid/{SECRET}?apiKey={SECRET}", session, retries=2,
    ))
    assert result == (status, b"body" if status == 200 else None)
    assert session.get.call_count == (1 if status == 200 else 2)
    assert sleep.await_count == (0 if status == 200 else 1)
    assert "https://provider.invalid" in caplog.text
    assert SECRET not in caplog.text
    if status == -1:
        assert "RuntimeError" in caplog.text


def test_cancellation_still_propagates() -> None:
    context = MagicMock(__aenter__=AsyncMock(side_effect=asyncio.CancelledError))
    session = MagicMock(get=MagicMock(return_value=context))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(async_engine.AsyncFetcher().fetch_with_retry(
            "https://provider.invalid", session,
        ))
    assert session.get.call_count == 1


def test_master_buffer_does_not_echo_worker_exception_messages(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    from src.fetchers import cot, cross_asset, fx_spot, yields

    failure = RuntimeError(f"provider URL?apiKey={SECRET}")
    for module, symbol in (
        (fx_spot, "fetch_fx_spot_async"), (cot, "fetch_cot_async"),
        (cross_asset, "fetch_cross_asset_async"), (yields, "fetch_yields_async"),
        (yields, "fetch_t10yie_breakeven_async"),
    ):
        monkeypatch.setattr(module, symbol, AsyncMock(side_effect=failure))
    monkeypatch.setattr(yields, "fetch_legacy_10y_legs", MagicMock(side_effect=failure))
    monkeypatch.setattr(async_engine, "load_universe", lambda: {})
    result = asyncio.run(async_engine.build_master_buffer())
    assert result[KEY_FX_SPOT] == {}
    assert result[KEY_YIELDS] == {}
    assert result[KEY_COT] == []
    assert caplog.text.count("RuntimeError") == 6
    assert SECRET not in caplog.text
