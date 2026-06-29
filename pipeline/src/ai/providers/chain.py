"""Multi-provider fallback chain: Groq -> Gemini -> NIM -> OpenRouter."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any, cast

from src.ai.providers import gemini, groq, nim, openrouter
from src.ai.rate_limiter import check_limit
from src.db import writer

logger = logging.getLogger(__name__)


class FallbackProviderChain:
    """Try providers in hierarchy with per-model retries."""

    async def call_async(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        date_str: str,
        purpose: str,
        *,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        """Try providers in hierarchy: Groq -> Gemini -> NIM -> OpenRouter."""
        kwargs_base: dict[str, Any] = {
            "messages": cast(Any, messages),
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        if response_format is not None:
            kwargs_base["response_format"] = cast(Any, response_format)
        if timeout_seconds is not None:
            kwargs_base["timeout"] = timeout_seconds

        if groq.groq_available():
            for model in [groq.GROQ_PRIMARY_MODEL, *groq.GROQ_FALLBACK_MODELS]:
                try:
                    check_limit(date_str)
                    logger.info("Attempting async AI call with Groq model: %s", model)
                    resp = await groq.async_groq_client().chat.completions.create(
                        model=model, **kwargs_base
                    )
                    writer.write_ai_request(date_str, purpose, model)
                    return resp.choices[0].message.content or ""
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Groq model %s failed: %s", model, exc)

        if gemini.gemini_available():
            for model in (gemini.GEMINI_PRIMARY_MODEL, gemini.GEMINI_FALLBACK_MODEL):
                try:
                    check_limit(date_str)
                    logger.info("Attempting async AI call with Gemini model: %s", model)
                    resp = await gemini.async_gemini_client().chat.completions.create(
                        model=model, **kwargs_base
                    )
                    writer.write_ai_request(date_str, purpose, model)
                    return resp.choices[0].message.content or ""
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Gemini model %s failed: %s", model, exc)

        if nim.nim_available():
            for model in [nim.NIM_PRIMARY_MODEL, *nim.NIM_FALLBACK_MODELS]:
                try:
                    check_limit(date_str)
                    logger.info("Attempting async AI call with NIM model: %s", model)
                    resp = await nim.async_nim_client().chat.completions.create(
                        model=model, **kwargs_base
                    )
                    writer.write_ai_request(date_str, purpose, model)
                    return resp.choices[0].message.content or ""
                except Exception as exc:  # noqa: BLE001
                    logger.warning("NIM model %s failed: %s", model, exc)

        for attempt in range(1, 4):
            for model in openrouter.OPENROUTER_FALLBACK_MODELS:
                try:
                    check_limit(date_str)
                    logger.info(
                        "Attempting async AI call with OpenRouter model: %s (attempt %s)",
                        model,
                        attempt,
                    )
                    resp = await openrouter.async_openrouter_client().chat.completions.create(
                        model=model, **kwargs_base
                    )
                    writer.write_ai_request(date_str, purpose, model)
                    return resp.choices[0].message.content or ""
                except Exception as exc:  # noqa: BLE001
                    logger.warning("OpenRouter model %s failed: %s", model, exc)
            if attempt < 3:
                sleep_time = 5 * attempt
                logger.warning(
                    "All OpenRouter models failed on attempt %s. Retrying in %s seconds.",
                    attempt,
                    sleep_time,
                )
                await asyncio.sleep(sleep_time)
        raise RuntimeError("All AI providers failed after retries")

    def call(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        date_str: str,
        purpose: str,
        *,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        """Sync wrapper around the async provider chain."""
        coro = self.call_async(
            messages,
            max_tokens,
            date_str,
            purpose,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()

    async def call_preferred_model_async(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        date_str: str,
        purpose: str,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        """Call the unified provider chain (model hint ignored; hierarchy rules)."""
        _ = model
        return await self.call_async(
            messages,
            max_tokens,
            date_str,
            purpose,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )

    def call_preferred_model(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        date_str: str,
        purpose: str,
        response_format: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> str:
        """Sync wrapper for preferred-model path."""
        coro = self.call_preferred_model_async(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            date_str=date_str,
            purpose=purpose,
            response_format=response_format,
            timeout_seconds=timeout_seconds,
        )
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
