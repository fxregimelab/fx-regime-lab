"""Multi-provider fallback chain: Groq -> Gemini -> NIM -> OpenRouter.

Every actual provider attempt is wrapped by an :class:`AttemptBudgetPolicy`:
the policy reserves budget *before* the request is sent and settles exactly
once afterwards (actual usage when the response exposes it, conservative usage
otherwise). Budget/permission/schema/policy errors are non-retryable and
propagate immediately. The default policy preserves the legacy production
behavior (daily request cap + success-only telemetry write); the desk injects
its own private policy through the constructor.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from collections.abc import Callable
from typing import Any, cast

from src.ai.providers import gemini, groq, nim, openrouter
from src.ai.rate_limiter import check_limit
from src.ai.telemetry import (
    AttemptBudgetPolicy,
    AttemptContext,
    DefaultProductionPolicy,
    NonRetryableAttemptError,
    Outcome,
    Reservation,
    Usage,
    estimate_input_tokens,
)
from src.db import writer

logger = logging.getLogger(__name__)


def _default_budget_policy() -> DefaultProductionPolicy:
    """Production-default policy wired to this module's live bindings.

    The late-bound lookups keep the historical override points of this module
    (``src.ai.providers.chain.check_limit`` and
    ``...chain.writer.write_ai_request``) effective for existing callers while
    behavior stays identical to a plain :class:`DefaultProductionPolicy`.
    """
    return DefaultProductionPolicy(
        limit_checker=lambda date_str: check_limit(date_str),
        usage_writer=lambda date_str, purpose, model: writer.write_ai_request(
            date_str, purpose, model
        ),
    )


def _token_field(usage: Any, key: str) -> int | None:
    value = getattr(usage, key, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _extract_usage(resp: Any) -> Usage | None:
    """Actual token usage when the provider response exposes it, else None."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None
    input_tokens = _token_field(usage, "prompt_tokens")
    output_tokens = _token_field(usage, "completion_tokens")
    if input_tokens is None or output_tokens is None:
        return None
    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)


class FallbackProviderChain:
    """Try providers in hierarchy with per-model retries."""

    def __init__(self, budget_policy: AttemptBudgetPolicy | None = None) -> None:
        self._budget_policy: AttemptBudgetPolicy = (
            budget_policy if budget_policy is not None else _default_budget_policy()
        )

    async def _reserved_attempt(
        self,
        *,
        attempt_no: int,
        provider: str,
        model: str,
        client_factory: Callable[[], Any],
        messages: list[dict[str, str]],
        max_tokens: int,
        date_str: str,
        purpose: str,
        kwargs: dict[str, Any],
    ) -> str | None:
        """One reserved provider attempt.

        Returns the response content (possibly empty) on success, or ``None``
        when the provider failed after settling the reservation as failed.
        Non-retryable errors escape immediately, after settling the
        reservation as failed, and are never offered to the fallback chain.
        """
        policy = self._budget_policy
        ctx = AttemptContext(
            date_str=date_str,
            purpose=purpose,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            attempt_no=attempt_no,
        )
        reservation: Reservation = policy.reserve(ctx)  # raises before send when exhausted
        try:
            logger.info("Attempting async AI call with %s model: %s", provider, model)
            client = client_factory()
            resp = await client.chat.completions.create(model=model, **kwargs)
        except asyncio.CancelledError:
            # Cancellation releases only proven-unused reservations, so settle
            # at the conservative maximum: the request may already be in flight.
            policy.settle(
                reservation,
                Usage(input_tokens=estimate_input_tokens(messages), output_tokens=max_tokens),
                Outcome.CANCELED,
            )
            raise
        except NonRetryableAttemptError:
            policy.settle(reservation, None, Outcome.FAILED)
            raise
        except Exception as exc:  # noqa: BLE001 — settle and continue the fallback chain
            policy.settle(reservation, None, Outcome.FAILED)
            logger.warning("%s model %s failed: %s", provider, model, exc)
            return None
        usage = _extract_usage(resp)
        if usage is None:
            # Unknown usage must settle at the conservative maximum, never zero.
            usage = Usage(input_tokens=estimate_input_tokens(messages), output_tokens=max_tokens)
        policy.settle(reservation, usage, Outcome.SUCCESS)
        return resp.choices[0].message.content or ""

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

        attempt_no = 0

        def next_attempt_no() -> int:
            nonlocal attempt_no
            attempt_no += 1
            return attempt_no

        if groq.groq_available():
            for model in [groq.GROQ_PRIMARY_MODEL, *groq.GROQ_FALLBACK_MODELS]:
                content = await self._reserved_attempt(
                    attempt_no=next_attempt_no(),
                    provider="groq",
                    model=model,
                    client_factory=groq.async_groq_client,
                    messages=messages,
                    max_tokens=max_tokens,
                    date_str=date_str,
                    purpose=purpose,
                    kwargs=kwargs_base,
                )
                if content is not None:
                    return content

        if gemini.gemini_available():
            for model in (gemini.GEMINI_PRIMARY_MODEL, gemini.GEMINI_FALLBACK_MODEL):
                content = await self._reserved_attempt(
                    attempt_no=next_attempt_no(),
                    provider="gemini",
                    model=model,
                    client_factory=gemini.async_gemini_client,
                    messages=messages,
                    max_tokens=max_tokens,
                    date_str=date_str,
                    purpose=purpose,
                    kwargs=kwargs_base,
                )
                if content is not None:
                    return content

        if nim.nim_available():
            for model in [nim.NIM_PRIMARY_MODEL, *nim.NIM_FALLBACK_MODELS]:
                content = await self._reserved_attempt(
                    attempt_no=next_attempt_no(),
                    provider="nim",
                    model=model,
                    client_factory=nim.async_nim_client,
                    messages=messages,
                    max_tokens=max_tokens,
                    date_str=date_str,
                    purpose=purpose,
                    kwargs=kwargs_base,
                )
                if content is not None:
                    return content

        for attempt in range(1, 4):
            for model in openrouter.OPENROUTER_FALLBACK_MODELS:
                content = await self._reserved_attempt(
                    attempt_no=next_attempt_no(),
                    provider="openrouter",
                    model=model,
                    client_factory=openrouter.async_openrouter_client,
                    messages=messages,
                    max_tokens=max_tokens,
                    date_str=date_str,
                    purpose=purpose,
                    kwargs=kwargs_base,
                )
                if content is not None:
                    return content
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
