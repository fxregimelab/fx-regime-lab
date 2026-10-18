"""AD-T12: attempt-budget reservation/settlement behavior of the fallback chain.

No network, no DB, no API keys: provider availability and clients are faked and
desk-style policies are local test doubles. Every test patches all four
providers explicitly so environment variables can never influence the run.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import math
import threading
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.ai.providers.chain import FallbackProviderChain
from src.ai.providers.gemini import GEMINI_PRIMARY_MODEL
from src.ai.providers.groq import GROQ_FALLBACK_MODELS, GROQ_PRIMARY_MODEL
from src.ai.providers.openrouter import OPENROUTER_FALLBACK_MODELS
from src.ai.rate_limiter import DAILY_REQUEST_LIMIT
from src.ai.telemetry import (
    AttemptContext,
    NonRetryableAttemptError,
    Outcome,
    Reservation,
    Usage,
    estimate_input_tokens,
)

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


class LedgerPolicy:
    """Desk-style test policy: records attempts, charges the reserved max on success.

    Provider failures settle with ``usage=None`` / ``Outcome.FAILED`` and cost
    nothing; canceled attempts cost nothing either. The budget check under the
    lock keeps concurrent callers from overspending.
    """

    def __init__(
        self,
        *,
        reserved_amount: float = 1.0,
        spend_limit: float | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.reserved_amount = reserved_amount
        self.spend_limit = spend_limit
        self.events: list[str] = events if events is not None else []
        self.reserve_calls: list[AttemptContext] = []
        self.reservations: list[Reservation] = []
        self.settle_calls: list[tuple[Reservation, Usage | None, Outcome]] = []
        self.spend = 0.0
        self.peak_committed = 0.0
        self._open: dict[str, AttemptContext] = {}
        self._lock = threading.Lock()

    def reserve(self, ctx: AttemptContext) -> Reservation:
        with self._lock:
            committed = self.spend + self.reserved_amount * len(self._open)
            if self.spend_limit is not None and committed + self.reserved_amount > self.spend_limit:
                raise NonRetryableAttemptError("attempt budget exhausted")
            self.peak_committed = max(self.peak_committed, committed + self.reserved_amount)
            reservation_id = f"res-{len(self.reserve_calls) + 1}"
            reservation = Reservation(
                reservation_id=reservation_id, reserved_amount=self.reserved_amount
            )
            self.reserve_calls.append(ctx)
            self.reservations.append(reservation)
            self._open[reservation_id] = ctx
            self.events.append(f"reserve:{ctx.provider}:{ctx.model}:{ctx.attempt_no}")
            return reservation

    def settle(self, reservation: Reservation, usage: Usage | None, outcome: Outcome) -> None:
        with self._lock:
            ctx = self._open.pop(reservation.reservation_id, None)
            assert ctx is not None, "settled a reservation twice or never reserved it"
            self.settle_calls.append((reservation, usage, outcome))
            self.events.append(
                f"settle:{ctx.provider}:{ctx.model}:{ctx.attempt_no}:{outcome.value}"
            )
            if outcome is Outcome.SUCCESS:
                self.spend += self.reserved_amount


class DenyPolicy:
    """Desk-style policy that denies every request before anything is sent."""

    def __init__(self) -> None:
        self.reserves = 0
        self.settles = 0

    def reserve(self, ctx: AttemptContext) -> Reservation:
        _ = ctx
        self.reserves += 1
        raise NonRetryableAttemptError("permission denied for desk policy")

    def settle(self, reservation: Reservation, usage: Usage | None, outcome: Outcome) -> None:
        self.settles += 1


def _fake_response(
    content: str = "ok",
    *,
    prompt_tokens: int | None = 12,
    completion_tokens: int | None = 4,
) -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    if prompt_tokens is None or completion_tokens is None:
        resp.usage = None
    else:
        resp.usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return resp


def _ok_create(
    content: str = "ok",
    *,
    prompt_tokens: int | None = 12,
    completion_tokens: int | None = 4,
    events: list[str] | None = None,
) -> Callable[..., Awaitable[MagicMock]]:
    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = kwargs
        if events is not None:
            events.append(f"send:{model}")
        return _fake_response(
            content, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )

    return _create


def _fail_create() -> Callable[..., Awaitable[MagicMock]]:
    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = model, kwargs
        raise RuntimeError("connection reset")

    return _create


def _fake_client(create: Callable[..., Awaitable[Any]]) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create = create
    return client


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
        client = _fake_client(create)
        monkeypatch.setattr(f"src.ai.providers.{name}.{client_attr}", lambda: client)


def _others_unavailable(monkeypatch: pytest.MonkeyPatch, *, keep: str) -> None:
    for name in _PROVIDER_API:
        if name != keep:
            _set_provider(monkeypatch, name, available=False)


async def _noop_sleep(_seconds: float) -> None:
    return None


def _patch_no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.ai.providers.chain.asyncio.sleep", _noop_sleep)


def test_reserve_before_send_settle_once_and_fallback_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    policy = LedgerPolicy(events=events)
    chain = FallbackProviderChain(budget_policy=policy)
    fallback_model = GROQ_FALLBACK_MODELS[0]

    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = kwargs
        events.append(f"send:{model}")
        if model == GROQ_PRIMARY_MODEL:
            raise RuntimeError("primary down")
        return _fake_response("from-fallback")

    _set_provider(monkeypatch, "groq", available=True, create=_create)
    _others_unavailable(monkeypatch, keep="groq")

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "from-fallback"
    assert events == [
        f"reserve:groq:{GROQ_PRIMARY_MODEL}:1",
        f"send:{GROQ_PRIMARY_MODEL}",
        f"settle:groq:{GROQ_PRIMARY_MODEL}:1:failed",
        f"reserve:groq:{fallback_model}:2",
        f"send:{fallback_model}",
        f"settle:groq:{fallback_model}:2:success",
    ]
    # Every reservation settled exactly once; fallback identity never concealed.
    assert [ctx.provider for ctx in policy.reserve_calls] == ["groq", "groq"]
    settled_ids = [res.reservation_id for res, _, _ in policy.settle_calls]
    assert settled_ids == [r.reservation_id for r in policy.reservations]
    assert len(settled_ids) == len(set(settled_ids)) == 2
    failed = policy.settle_calls[0]
    assert failed[1] is None and failed[2] is Outcome.FAILED
    success = policy.settle_calls[1]
    assert success[1] == Usage(input_tokens=12, output_tokens=4)
    assert success[2] is Outcome.SUCCESS


def test_failed_attempts_cost_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_no_sleep(monkeypatch)
    policy = LedgerPolicy(reserved_amount=2.5)
    chain = FallbackProviderChain(budget_policy=policy)
    _set_provider(monkeypatch, "groq", available=True, create=_fail_create())
    _set_provider(monkeypatch, "openrouter", available=True, create=_fail_create())
    _set_provider(monkeypatch, "gemini", available=False)
    _set_provider(monkeypatch, "nim", available=False)

    with pytest.raises(RuntimeError, match="All AI providers failed after retries"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    groq_models = [GROQ_PRIMARY_MODEL, *GROQ_FALLBACK_MODELS]
    openrouter_models = list(OPENROUTER_FALLBACK_MODELS)
    expected_models = groq_models + openrouter_models * 3
    assert [ctx.model for ctx in policy.reserve_calls] == expected_models
    assert [ctx.attempt_no for ctx in policy.reserve_calls] == list(
        range(1, len(expected_models) + 1)
    )
    assert len(policy.settle_calls) == len(expected_models)
    assert all(
        usage is None and outcome is Outcome.FAILED for _, usage, outcome in policy.settle_calls
    )
    assert policy.spend == 0.0  # failed attempts cost nothing
    assert policy.spend <= 2.5 * len(expected_models)  # and never exceed reservations


def test_missing_usage_settles_conservatively(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = LedgerPolicy()
    chain = FallbackProviderChain(budget_policy=policy)
    _set_provider(
        monkeypatch,
        "groq",
        available=True,
        create=_ok_create("done", prompt_tokens=None, completion_tokens=None),
    )
    _others_unavailable(monkeypatch, keep="groq")

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "done"
    _, usage, outcome = policy.settle_calls[0]
    assert outcome is Outcome.SUCCESS
    assert usage is not None
    assert usage.input_tokens == estimate_input_tokens(MESSAGES) > 0
    assert usage.output_tokens == MAX_TOKENS > 0  # conservative max, never zero


def test_actual_usage_is_settled_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = LedgerPolicy()
    chain = FallbackProviderChain(budget_policy=policy)
    _set_provider(
        monkeypatch,
        "groq",
        available=True,
        create=_ok_create(prompt_tokens=123, completion_tokens=45),
    )
    _others_unavailable(monkeypatch, keep="groq")

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "ok"
    assert policy.settle_calls[0][1] == Usage(input_tokens=123, output_tokens=45)


def test_estimate_input_tokens_is_conservative_and_nonzero() -> None:
    text = "x" * 300
    estimate = estimate_input_tokens([{"role": "user", "content": text}])
    assert estimate >= math.ceil(len(text) / 4)
    assert estimate > 0
    assert estimate_input_tokens([{"role": "user", "content": "short"}]) > 0


def test_cap_breach_nonretryable_after_exactly_one_read_no_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads: list[str] = []
    sends: list[str] = []

    def _count(date_str: str) -> int:
        reads.append(date_str)
        return DAILY_REQUEST_LIMIT

    monkeypatch.setattr("src.db.writer.get_ai_request_count_today", _count)
    for name in _PROVIDER_API:
        _set_provider(monkeypatch, name, available=True, create=_ok_create(events=sends))

    chain = FallbackProviderChain()  # default production policy
    with pytest.raises(NonRetryableAttemptError, match="budget exhausted"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert reads == [DATE]  # exactly one read-limit RPC for the first reserve
    assert sends == []  # never caught as a provider failure, never retried


def test_policy_denial_is_not_caught_or_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    sends: list[str] = []
    policy = DenyPolicy()
    chain = FallbackProviderChain(budget_policy=policy)
    for name in _PROVIDER_API:
        _set_provider(monkeypatch, name, available=True, create=_ok_create(events=sends))

    with pytest.raises(NonRetryableAttemptError, match="permission denied"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert policy.reserves == 1
    assert policy.settles == 0
    assert sends == []


def test_nonretryable_provider_error_settles_failed_then_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = LedgerPolicy()
    chain = FallbackProviderChain(budget_policy=policy)
    sends: list[str] = []

    async def _create(*, model: str, **kwargs: Any) -> MagicMock:
        _ = kwargs
        sends.append(model)
        raise NonRetryableAttemptError("schema violation")

    _set_provider(monkeypatch, "groq", available=True, create=_create)
    for name in ("gemini", "nim", "openrouter"):
        _set_provider(monkeypatch, name, available=True, create=_ok_create(events=sends))

    with pytest.raises(NonRetryableAttemptError, match="schema violation"):
        asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert sends == [GROQ_PRIMARY_MODEL]  # no retry, no fallthrough to other providers
    assert len(policy.reserve_calls) == 1
    assert len(policy.settle_calls) == 1
    _, usage, outcome = policy.settle_calls[0]
    assert usage is None and outcome is Outcome.FAILED


def test_provider_fallback_identity_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_no_sleep(monkeypatch)
    policy = LedgerPolicy()
    chain = FallbackProviderChain(budget_policy=policy)
    _set_provider(monkeypatch, "groq", available=True, create=_fail_create())
    _set_provider(monkeypatch, "gemini", available=True, create=_ok_create("gemini-ok"))
    _set_provider(monkeypatch, "nim", available=False)
    _set_provider(monkeypatch, "openrouter", available=False)

    result = asyncio.run(chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE))

    assert result == "gemini-ok"
    providers = [ctx.provider for ctx in policy.reserve_calls]
    assert providers == ["groq"] * (1 + len(GROQ_FALLBACK_MODELS)) + ["gemini"]
    assert [ctx.attempt_no for ctx in policy.reserve_calls] == list(range(1, len(providers) + 1))
    assert policy.reserve_calls[-1].model == GEMINI_PRIMARY_MODEL
    settled_ids = [res.reservation_id for res, _, _ in policy.settle_calls]
    assert len(settled_ids) == len(set(settled_ids)) == len(policy.reserve_calls)


def test_concurrent_attempts_never_overspend(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = LedgerPolicy(reserved_amount=1.0, spend_limit=5.0)
    chain = FallbackProviderChain(budget_policy=policy)
    _set_provider(monkeypatch, "groq", available=True, create=_ok_create("concurrent"))
    _others_unavailable(monkeypatch, keep="groq")

    def _run_one() -> str:
        return chain.call(MESSAGES, MAX_TOKENS, DATE, PURPOSE)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_run_one) for _ in range(40)]
        outcomes: list[object] = []
        for future in futures:
            try:
                outcomes.append(future.result())
            except NonRetryableAttemptError as exc:
                outcomes.append(exc)

    successes = [o for o in outcomes if isinstance(o, str)]
    denials = [o for o in outcomes if isinstance(o, NonRetryableAttemptError)]
    assert len(successes) == 5
    assert len(denials) == 35
    assert policy.spend == 5.0  # never > spend_limit, exactly the funded attempts
    assert policy.peak_committed <= 5.0
    assert len(policy.settle_calls) == 5


def test_cancellation_settles_conservatively_once(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = LedgerPolicy()
    chain = FallbackProviderChain(budget_policy=policy)

    async def _hang(*, model: str, **kwargs: Any) -> MagicMock:
        _ = model, kwargs
        await asyncio.sleep(30)
        return _fake_response("never")

    _set_provider(monkeypatch, "groq", available=True, create=_hang)
    _others_unavailable(monkeypatch, keep="groq")

    async def _call_with_deadline() -> str:
        return await asyncio.wait_for(
            chain.call_async(MESSAGES, MAX_TOKENS, DATE, PURPOSE), timeout=0.1
        )

    with pytest.raises(TimeoutError):
        asyncio.run(_call_with_deadline())

    assert len(policy.reserve_calls) == 1
    assert len(policy.settle_calls) == 1
    _, usage, outcome = policy.settle_calls[0]
    assert outcome is Outcome.CANCELED
    assert usage is not None and usage.output_tokens == MAX_TOKENS  # conservative, not zero
    assert policy.spend == 0.0
