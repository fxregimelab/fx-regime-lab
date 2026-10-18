"""Bounded intraday headline coverage (AD-T08 slice).

The runtime research analyst needs affirmative, recent, independently
corroborated headline evidence before proposing an entry:

- Only registered collector transports are contacted, and only with the fixed
  theme set (central-bank, rates, inflation, intervention) for the pair's two
  currencies over the t-4h..t window.
- The two-item rule is enforced here: fewer than two headlines, or fewer than
  two distinct publisher families, is unverified coverage — the analyst
  abstains rather than trading on a single syndicated story. A schema revision
  for verified-empty coverage is future protected work; this slice keeps the
  conservative rule.
- Headlines are inert data: titles, digests and timestamps are validated and
  archived, never executed, and a hostile title passes through unchanged as
  evidence.

This module never fetches by itself; the authoritative feed entitlement is a
provisioning fact and its absence remains a blocker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from src.paper.calendar import CoverageReceipt, _aware_utc, _non_empty
from src.paper.contracts import ContractError, Coverage, Pair

_EVIDENCE_WINDOW = timedelta(hours=4)
_MAX_FETCH_AGE = timedelta(minutes=5)
_THEMES: tuple[str, ...] = ("central-bank", "rates", "inflation", "intervention")
_PAIR_CURRENCIES: dict[Pair, tuple[str, ...]] = {
    Pair.EURUSD: ("EUR", "USD"),
    Pair.USDJPY: ("USD", "JPY"),
}

_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Headline:
    """One archived headline observation with full provenance."""

    story_id: str
    publisher_family: str
    title: str
    content_digest: str
    published_at: datetime
    first_seen_at: datetime
    available_at: datetime
    retrieved_at: datetime
    revision: int = 1

    def __post_init__(self) -> None:
        _non_empty("Headline.story_id", self.story_id)
        _non_empty("Headline.publisher_family", self.publisher_family)
        _non_empty("Headline.title", self.title)
        if (
            type(self.content_digest) is not str
            or _DIGEST_RE.fullmatch(self.content_digest) is None
        ):
            raise ContractError("INVALID_SCHEMA", "Headline.content_digest: sha256 hex required")
        _aware_utc("Headline.published_at", self.published_at)
        _aware_utc("Headline.first_seen_at", self.first_seen_at)
        _aware_utc("Headline.available_at", self.available_at)
        _aware_utc("Headline.retrieved_at", self.retrieved_at)
        if type(self.revision) is not int or self.revision < 1:
            raise ContractError("INVALID_SCHEMA", "Headline.revision: positive int required")


@dataclass(frozen=True)
class NewsPayload:
    """Window result: one coverage receipt plus zero or more headlines."""

    receipt: CoverageReceipt
    headlines: tuple[Headline, ...] = ()


class NewsSource(Protocol):
    """Registered collector transport; supplies one already-fetched window."""

    source_id: str

    def read_headlines(
        self,
        start: datetime,
        end: datetime,
        currencies: tuple[str, ...],
        themes: tuple[str, ...],
    ) -> NewsPayload: ...


def _validate_headline(headline: Headline, start: datetime, decision_at: datetime) -> None:
    if headline.published_at > headline.first_seen_at:
        raise ContractError("INVALID_SCHEMA", "Headline: published after first seen")
    if headline.first_seen_at > headline.available_at:
        raise ContractError("INVALID_SCHEMA", "Headline: first seen after available")
    if headline.available_at > headline.retrieved_at:
        raise ContractError("INVALID_SCHEMA", "Headline: available after retrieved")
    if headline.retrieved_at > decision_at:
        raise ContractError("INVALID_SCHEMA", "Headline: retrieved in the future")
    if headline.available_at > decision_at:
        raise ContractError("INVALID_SCHEMA", "Headline: not yet available at decision")
    if headline.first_seen_at > decision_at:
        raise ContractError("INVALID_SCHEMA", "Headline: first seen after decision")
    if headline.published_at > decision_at:
        raise ContractError("INVALID_SCHEMA", "Headline: published after decision")
    if headline.published_at < start:
        raise ContractError("SOURCE_STALE", "Headline: older than the t-4h evidence window")


def collect_headlines(
    source: NewsSource,
    *,
    registered_sources: frozenset[str],
    pair: Pair,
    decision_at: datetime,
) -> NewsPayload:
    """Collect and validate one headline window; fail closed on weak coverage."""
    _aware_utc("decision_at", decision_at)
    source_id = getattr(source, "source_id", None)
    if type(source_id) is not str or source_id not in registered_sources:
        raise ContractError("SOURCE_INCOMPLETE", f"news source {source_id!r} is not registered")

    currencies = _PAIR_CURRENCIES[pair]
    start = decision_at - _EVIDENCE_WINDOW
    end = decision_at
    payload = source.read_headlines(start, end, currencies, _THEMES)
    if not isinstance(payload, NewsPayload):
        raise ContractError("INVALID_SCHEMA", "news source must return a NewsPayload")

    receipt = payload.receipt
    _aware_utc("CoverageReceipt.window_start", receipt.window_start)
    _aware_utc("CoverageReceipt.window_end", receipt.window_end)
    fetched_at = _aware_utc("CoverageReceipt.fetched_at", receipt.fetched_at)
    if fetched_at > decision_at:
        raise ContractError("SOURCE_STALE", "coverage receipt fetched in the future")
    if decision_at - fetched_at > _MAX_FETCH_AGE:
        raise ContractError("SOURCE_STALE", "coverage refresh older than 5 minutes")
    if receipt.source_id != source_id:
        raise ContractError("SOURCE_INCOMPLETE", "receipt/source identity mismatch")
    if receipt.currencies != currencies:
        raise ContractError("SOURCE_INCOMPLETE", "receipt currencies do not cover the pair")
    if receipt.window_start != start or receipt.window_end != end:
        raise ContractError("SOURCE_INCOMPLETE", "receipt window does not match t-4h..t")
    if receipt.status is not Coverage.verified:
        raise ContractError("SOURCE_INCOMPLETE", f"news coverage status {receipt.status!r}")

    seen: set[str] = set()
    for headline in payload.headlines:
        if not isinstance(headline, Headline):
            raise ContractError("INVALID_SCHEMA", "news payload contains a non-headline")
        _validate_headline(headline, start, decision_at)
        if headline.story_id in seen:
            raise ContractError("CONFLICT", f"duplicate story {headline.story_id!r}")
        seen.add(headline.story_id)

    families = {headline.publisher_family for headline in payload.headlines}
    if len(payload.headlines) < 2 or len(families) < 2:
        raise ContractError(
            "NEWS_UNVERIFIED",
            "entry news coverage needs at least two headlines from two publisher families",
        )
    return payload
