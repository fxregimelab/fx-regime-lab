"""Unit tests for AI provider fallback chain and rate limiting."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.providers.chain import FallbackProviderChain
from src.ai.rate_limiter import DAILY_REQUEST_LIMIT, check_limit


def test_check_limit_raises_when_at_cap() -> None:
    with patch(
        "src.ai.rate_limiter.writer.get_ai_request_count_today",
        return_value=DAILY_REQUEST_LIMIT,
    ):
        with pytest.raises(RuntimeError, match="Daily AI request limit reached"):
            check_limit("2026-06-29")


def test_check_limit_allows_under_cap() -> None:
    with patch(
        "src.ai.rate_limiter.writer.get_ai_request_count_today",
        return_value=DAILY_REQUEST_LIMIT - 1,
    ):
        check_limit("2026-06-29")


def test_fallback_chain_uses_groq_first() -> None:
    chain = FallbackProviderChain()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    mock_create = AsyncMock(return_value=mock_resp)

    with patch("src.ai.providers.chain.groq.groq_available", return_value=True), patch(
        "src.ai.providers.chain.gemini.gemini_available", return_value=True
    ), patch("src.ai.providers.chain.nim.nim_available", return_value=True), patch(
        "src.ai.providers.chain.check_limit"
    ), patch(
        "src.ai.providers.chain.writer.write_ai_request"
    ) as write_req, patch(
        "src.ai.providers.chain.groq.async_groq_client"
    ) as groq_client_factory, patch(
        "src.ai.providers.chain.gemini.async_gemini_client"
    ) as gemini_client_factory:
        groq_client = MagicMock()
        groq_client.chat.completions.create = mock_create
        groq_client_factory.return_value = groq_client
        gemini_client_factory.return_value = MagicMock()

        result = asyncio.run(
            chain.call_async(
                [{"role": "user", "content": "hi"}],
                max_tokens=10,
                date_str="2026-06-29",
                purpose="test",
            )
        )

    assert result == '{"ok": true}'
    mock_create.assert_awaited_once()
    write_req.assert_called_once()


def test_fallback_chain_skips_groq_when_unavailable() -> None:
    chain = FallbackProviderChain()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="gemini-ok"))]
    mock_create = AsyncMock(return_value=mock_resp)

    with patch("src.ai.providers.chain.groq.groq_available", return_value=False), patch(
        "src.ai.providers.chain.gemini.gemini_available", return_value=True
    ), patch("src.ai.providers.chain.nim.nim_available", return_value=False), patch(
        "src.ai.providers.chain.check_limit"
    ), patch("src.ai.providers.chain.writer.write_ai_request"), patch(
        "src.ai.providers.chain.gemini.async_gemini_client"
    ) as gemini_client_factory:
        gemini_client = MagicMock()
        gemini_client.chat.completions.create = mock_create
        gemini_client_factory.return_value = gemini_client

        result = asyncio.run(
            chain.call_async(
                [{"role": "user", "content": "hi"}],
                max_tokens=10,
                date_str="2026-06-29",
                purpose="test",
            )
        )

    assert result == "gemini-ok"
    mock_create.assert_awaited_once()


def test_fallback_chain_rate_limit_skips_provider_api_calls() -> None:
    chain = FallbackProviderChain()

    with patch("src.ai.providers.chain.groq.groq_available", return_value=True), patch(
        "src.ai.providers.chain.check_limit",
        side_effect=RuntimeError("Daily AI request limit reached (180/180)"),
    ), patch("src.ai.providers.chain.groq.async_groq_client") as groq_client_factory, patch(
        "src.ai.providers.chain.gemini.gemini_available", return_value=False
    ), patch(
        "src.ai.providers.chain.nim.nim_available", return_value=False
    ), patch(
        "src.ai.providers.chain.asyncio.sleep", new_callable=AsyncMock
    ), patch(
        "src.ai.providers.chain.openrouter.async_openrouter_client"
    ) as or_client_factory:
        groq_client = MagicMock()
        groq_client.chat.completions.create = AsyncMock()
        groq_client_factory.return_value = groq_client
        or_client = MagicMock()
        or_client.chat.completions.create = AsyncMock()
        or_client_factory.return_value = or_client

        with pytest.raises(RuntimeError, match="All AI providers failed after retries"):
            asyncio.run(
                chain.call_async(
                    [{"role": "user", "content": "hi"}],
                    max_tokens=10,
                    date_str="2026-06-29",
                    purpose="test",
                )
            )

    groq_client.chat.completions.create.assert_not_awaited()
    or_client.chat.completions.create.assert_not_awaited()
