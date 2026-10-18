"""AD-T12: production telemetry isolation for injected desk policies.

With a desk-style policy injected, the fallback chain must never touch
``writer.write_ai_request`` / ``writer.get_ai_request_count_today`` on any path
(success, fallback, OpenRouter retry rounds, hard failure). With the default
policy both functions are still used exactly as before: one read-limit call per
actual attempt and a success-only telemetry write.

No network, no DB, no API keys: providers are faked and production writer
functions are replaced with recorders/explosives.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.ai.providers.chain import FallbackProviderChain
from src.ai.providers.groq import GROQ_FALLBACK_MODELS, GROQ_PRIMARY_MODEL
from src.ai.providers.nim import NIM_FALLBACK_MODELS
from src.ai.providers.openrouter import OPENROUTER_FALLBACK_MODELS
from src.ai.telemetry import AttemptContext, Outcome, Reservation, Usage

DATE = "2026-07-01"
PURPOSE = "test"
MESSAGES = [{"role": "user", "content": "Summarize today's EUR/USD regime."}]
MAX_TOKENS = 64

_PROVIDER_API = {
    "groq": ("groq_available", "async_groq_client"),
    "gemini": ("gemini_available", "async_gemini_client"),
    "nim": ("nim_available", "async_nim_client"),
    "openrouter": ("openrouter_available", "async_openrouter_client"),
}


class _DeskPolicy:
    """Minimal desk policy double: no production side effects."""

    def __init__(self) -> None:
        self.contexts: list[AttemptContext] = []
        self.settles: list[tuple[Reservation, Usage | None, Outcome]] = []

    def reserve(self, ctx: AttemptContext) -> Reservation:
        self.contexts.append(ctx)
        return Reservation(reservation_id=f"desk-{len(self.contexts)}", reserved_amount=0.0)

    def settle(self, reservation: Reservation, usage: Usage | None, outcome: Outcome) -> None:
        self.settles.append((reservation, usage, outcome))


class _ForbiddenProductionTelemetry:
    """Records and fails loudly on any production telemetry RPC."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def write_ai_request(self, date_str: str, purpose: str, model: str) -> None:
        self.calls.append(f"write_ai_request:{date_str}:{purpose}:{model}")
        raise AssertionError("desk policy leaked into production telemetry write")

    def get_ai_request_count_today(self, date_str: str) -> int:
        self.calls.append(f"get_ai_request_count_today:{date_str}")
        raise AssertionError("desk policy leaked into production read-limit RPC")


def _block_production_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> _ForbiddenProductionTelemetry:
    forbidden = _ForbiddenProductionTelemetry()
    monkeypatch.setattr("src.db.writer.write_ai_request", forbidden.write_ai_request)
    monkeypatch.setattr(
        "src.db.writer.get_ai_request_count_today", forbidden.get_ai_request_count_today
    )
    return forbidden


def _fake_response(content: str = "ok") -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    resp.usage = MagicMock(prompt_tokens=12, completion_tokens=4)
    return resp


def _ok_create(
    content: str = "ok",
) -> Callable[..., Awaitable[MagicMock]]:
    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = model, kwargs
        return _fake_response(content)

    return _create


def _fail_create() -> Callable[..., Awaitable[MagicMock]]:
    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = model, kwargs
        raise RuntimeError("connection reset")

    return _create


def _set_provider(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    *,
    available: bool,
    create: Callable[..., Awaitable[Any]] | None = None,
) -> None:
    available_attr, client_attr = _PROVIDER_API[name]
    monkeypatch.setattr(f"src.ai.providers.{name}.{available_attr}", lambda: available)
    if available:
        assert create is not None, "available providers need a fake client"
        client = MagicMock()
        client.chat.completions.create = create
        monkeypatch.setattr(f"src.ai.providers.{name}.{client_attr}", lambda: client)


def _only_groq(
    monkeypatch: pytest.MonkeyPatch, create: Callable[..., Awaitable[Any]]
) -> None:
    _set_provider(monkeypatch, "groq", available=True, create=create)
    for name in ("gemini", "nim", "openrouter"):
        _set_provider(monkeypatch, name, available=False)


async def _noop_sleep(_seconds: float) -> None:
    return None


def _patch_no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.ai.providers.chain.asyncio.sleep", _noop_sleep)


def test_desk_policy_success_never_touches_production_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = _block_production_telemetry(monkeypatch)
    desk = _DeskPolicy()
    chain = FallbackProviderChain(budget_policy=desk)
    _only_groq(monkeypatch, _ok_create("desk-ok"))

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "desk-ok"
    assert forbidden.calls == []
    assert len(desk.contexts) == len(desk.settles) == 1


def test_desk_policy_fallback_never_touches_production_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = _block_production_telemetry(monkeypatch)
    desk = _DeskPolicy()
    chain = FallbackProviderChain(budget_policy=desk)
    fallback_model = GROQ_FALLBACK_MODELS[0]

    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = kwargs
        if model == GROQ_PRIMARY_MODEL:
            raise RuntimeError("primary down")
        return _fake_response("desk-fallback")

    _only_groq(monkeypatch, _create)

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "desk-fallback"
    assert forbidden.calls == []
    assert [ctx.model for ctx in desk.contexts] == [GROQ_PRIMARY_MODEL, fallback_model]
    assert len(desk.settles) == 2


def test_desk_policy_openrouter_retry_never_touches_production_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_no_sleep(monkeypatch)
    forbidden = _block_production_telemetry(monkeypatch)
    desk = _DeskPolicy()
    chain = FallbackProviderChain(budget_policy=desk)
    _set_provider(monkeypatch, "groq", available=False)
    _set_provider(monkeypatch, "gemini", available=False)
    _set_provider(monkeypatch, "nim", available=False)
    _set_provider(monkeypatch, "openrouter", available=True, create=_fail_create())

    with pytest.raises(RuntimeError, match="All AI providers failed after retries"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    expected_models = list(OPENROUTER_FALLBACK_MODELS) * 3
    assert [ctx.model for ctx in desk.contexts] == expected_models
    assert [ctx.provider for ctx in desk.contexts] == ["openrouter"] * len(expected_models)
    assert [ctx.attempt_no for ctx in desk.contexts] == list(range(1, len(expected_models) + 1))
    assert len(desk.settles) == len(expected_models)
    assert all(outcome is Outcome.FAILED for _, _, outcome in desk.settles)
    assert forbidden.calls == []


def test_desk_policy_hard_failure_never_touches_production_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_no_sleep(monkeypatch)
    forbidden = _block_production_telemetry(monkeypatch)
    desk = _DeskPolicy()
    chain = FallbackProviderChain(budget_policy=desk)
    for name in _PROVIDER_API:
        _set_provider(monkeypatch, name, available=True, create=_fail_create())

    with pytest.raises(RuntimeError, match="All AI providers failed after retries"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    expected_attempts = (
        (1 + len(GROQ_FALLBACK_MODELS))
        + 2  # gemini primary + fallback
        + (1 + len(NIM_FALLBACK_MODELS))
        + 3 * len(OPENROUTER_FALLBACK_MODELS)
    )
    assert len(desk.contexts) == expected_attempts
    assert len(desk.settles) == expected_attempts
    assert forbidden.calls == []


def test_default_policy_success_uses_production_telemetry_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[str] = []
    writes: list[tuple[str, str, str]] = []

    def _read(date_str: str) -> int:
        reads.append(date_str)
        return 0

    def _write(date_str: str, purpose: str, model: str) -> None:
        writes.append((date_str, purpose, model))

    monkeypatch.setattr("src.db.writer.get_ai_request_count_today", _read)
    monkeypatch.setattr("src.db.writer.write_ai_request", _write)
    chain = FallbackProviderChain()
    _only_groq(monkeypatch, _ok_create("default-ok"))

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "default-ok"
    assert reads == [DATE]
    assert writes == [(DATE, PURPOSE, GROQ_PRIMARY_MODEL)]


def test_default_policy_fallback_reads_per_attempt_and_writes_success_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[str] = []
    writes: list[tuple[str, str, str]] = []

    def _read(date_str: str) -> int:
        reads.append(date_str)
        return 0

    def _write(date_str: str, purpose: str, model: str) -> None:
        writes.append((date_str, purpose, model))

    monkeypatch.setattr("src.db.writer.get_ai_request_count_today", _read)
    monkeypatch.setattr("src.db.writer.write_ai_request", _write)
    chain = FallbackProviderChain()
    fallback_model = GROQ_FALLBACK_MODELS[0]

    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = kwargs
        if model == GROQ_PRIMARY_MODEL:
            raise RuntimeError("primary down")
        return _fake_response("default-fallback")

    _only_groq(monkeypatch, _create)

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "default-fallback"
    assert reads == [DATE, DATE]  # one read-limit RPC per actual attempt
    assert writes == [(DATE, PURPOSE, fallback_model)]  # success-only, actual model


def test_default_policy_failure_reads_per_attempt_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_no_sleep(monkeypatch)
    reads: list[str] = []
    writes: list[tuple[str, str, str]] = []

    def _read(date_str: str) -> int:
        reads.append(date_str)
        return 0

    def _write(date_str: str, purpose: str, model: str) -> None:
        writes.append((date_str, purpose, model))

    monkeypatch.setattr("src.db.writer.get_ai_request_count_today", _read)
    monkeypatch.setattr("src.db.writer.write_ai_request", _write)
    chain = FallbackProviderChain()
    _set_provider(monkeypatch, "groq", available=True, create=_fail_create())
    _set_provider(monkeypatch, "gemini", available=False)
    _set_provider(monkeypatch, "nim", available=False)
    _set_provider(monkeypatch, "openrouter", available=True, create=_fail_create())

    with pytest.raises(RuntimeError, match="All AI providers failed after retries"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    expected_attempts = (1 + len(GROQ_FALLBACK_MODELS)) + 3 * len(OPENROUTER_FALLBACK_MODELS)
    assert reads == [DATE] * expected_attempts
    assert writes == []
