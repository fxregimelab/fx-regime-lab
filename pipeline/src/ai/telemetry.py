"""Attempt-level AI telemetry and budget policy seam (AD-T12).

This module is the contract between the provider fallback chain and whatever
budget/telemetry accounting a caller wants:

- :class:`FallbackProviderChain` reserves *before* every actual provider
  request through an :class:`AttemptBudgetPolicy` and settles exactly once
  afterwards (actual usage when the response exposes it, conservative usage
  otherwise).
- :class:`DefaultProductionPolicy` preserves today's production behavior:
  the daily request cap via ``rate_limiter.check_limit`` and a success-only
  ``writer.write_ai_request`` telemetry write. No other side effects.
- Desk runtimes inject a private policy explicitly through the existing
  ``AIClient`` chain injection; the default policy must then be untouched.

Money is expressed as USD floats. Verified-free models carry an explicit
:data:`VERIFIED_FREE_PRICE`; unknown prices must never be treated as free:
a policy either denies the paid send or books its own conservative maximum
reservation. Likewise, missing usage must settle at the conservative maximum
(the reserved amount), never at zero. This module performs no DB writes by
itself; the only writer access is the default policy's telemetry write, which
is the production behavior being preserved.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from src.ai import rate_limiter
from src.db import writer

__all__ = [
    "AttemptBudgetPolicy",
    "AttemptContext",
    "DefaultProductionPolicy",
    "NonRetryableAttemptError",
    "Outcome",
    "Reservation",
    "TokenPrice",
    "Usage",
    "VERIFIED_FREE_PRICE",
    "conservative_max_cost_usd",
    "estimate_input_tokens",
]


class Outcome(StrEnum):
    """Settlement outcome of one reserved attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class NonRetryableAttemptError(Exception):
    """Budget, permission, schema or policy failure that must not be retried.

    The provider chain never converts this error into a provider failure, never
    retries it and never falls through to the next provider.
    """


@dataclass(frozen=True, slots=True)
class AttemptContext:
    """Identity of one actual provider attempt (fallback identity included)."""

    date_str: str
    purpose: str
    provider: str
    model: str
    max_tokens: int
    attempt_no: int


@dataclass(frozen=True, slots=True)
class Reservation:
    """Opaque reservation handle returned by ``AttemptBudgetPolicy.reserve``."""

    reservation_id: str
    reserved_amount: float


@dataclass(frozen=True, slots=True)
class Usage:
    """Token usage for a settled attempt; ``None`` fields mean unknown."""

    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class TokenPrice:
    """Explicit USD price for one model, per million tokens."""

    input_usd_per_mtok: float
    output_usd_per_mtok: float


VERIFIED_FREE_PRICE = TokenPrice(input_usd_per_mtok=0.0, output_usd_per_mtok=0.0)

# Deliberately below the ~4 chars/token rule of thumb for English so the
# estimate never flatters a budget: dense text (code, JSON, CJK) still lands
# inside the bound with headroom.
_CONSERVATIVE_CHARS_PER_TOKEN = 3


class AttemptBudgetPolicy(Protocol):
    """Pre-send reservation and post-send settlement for every real attempt.

    ``reserve`` must raise (``NonRetryableAttemptError``) before the provider
    request when no budget is available; the chain then has sent nothing.
    ``settle`` is called exactly once per reservation, with actual usage when
    the response exposes it and conservative usage otherwise; provider
    failures settle with ``usage=None`` and ``Outcome.FAILED``.
    """

    def reserve(self, ctx: AttemptContext) -> Reservation: ...

    def settle(self, reservation: Reservation, usage: Usage | None, outcome: Outcome) -> None: ...


def estimate_input_tokens(messages: Sequence[Mapping[str, object]]) -> int:
    """Conservative upper-bound-biased input-token estimate for budgeting.

    Unknown usage must settle at the conservative maximum; this helper is that
    bound for the input side of a request.
    """
    chars = 0
    for message in messages:
        chars += len(str(message.get("content") or ""))
        chars += len(str(message.get("role") or ""))
    return math.ceil(chars / _CONSERVATIVE_CHARS_PER_TOKEN)


def conservative_max_cost_usd(
    price: TokenPrice | None,
    *,
    input_tokens: int,
    max_output_tokens: int,
) -> float | None:
    """Worst-case USD cost of one attempt.

    Returns ``0.0`` only for an explicit verified-free price. ``None`` price
    means unknown: the caller must deny the send or apply its own conservative
    ceiling — never book zero.
    """
    if price is None:
        return None
    return (
        price.input_usd_per_mtok * max(input_tokens, 0)
        + price.output_usd_per_mtok * max(max_output_tokens, 0)
    ) / 1_000_000


class DefaultProductionPolicy:
    """Production-default policy: daily cap check + success-only telemetry write.

    Behavior is identical to the legacy provider chain and has no other side
    effects:

    - ``reserve`` runs ``rate_limiter.check_limit(ctx.date_str)``; a cap breach
      is surfaced as :class:`NonRetryableAttemptError` before anything is sent.
    - ``settle`` writes ``writer.write_ai_request(date_str, purpose, model)`` on
      ``Outcome.SUCCESS`` only; failed/canceled attempts write nothing.

    Money reservations are 0: production infrastructure is verified free-tier,
    and paid-budget enforcement belongs to desk policies.
    """

    def __init__(
        self,
        *,
        limit_checker: Callable[[str], None] | None = None,
        usage_writer: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self._limit_checker = limit_checker or rate_limiter.check_limit
        self._usage_writer = usage_writer or writer.write_ai_request
        self._open_reservations: dict[str, AttemptContext] = {}

    def reserve(self, ctx: AttemptContext) -> Reservation:
        try:
            self._limit_checker(ctx.date_str)
        except RuntimeError as exc:
            msg = f"AI request budget exhausted for {ctx.date_str}: {exc}"
            raise NonRetryableAttemptError(msg) from exc
        reservation = Reservation(reservation_id=uuid.uuid4().hex, reserved_amount=0.0)
        self._open_reservations[reservation.reservation_id] = ctx
        return reservation

    def settle(self, reservation: Reservation, usage: Usage | None, outcome: Outcome) -> None:
        _ = usage  # production telemetry is request-count based; no money side effects
        ctx = self._open_reservations.pop(reservation.reservation_id, None)
        if ctx is None:
            msg = f"unknown or already-settled reservation {reservation.reservation_id!r}"
            raise NonRetryableAttemptError(msg)
        if outcome is Outcome.SUCCESS:
            self._usage_writer(ctx.date_str, ctx.purpose, ctx.model)
