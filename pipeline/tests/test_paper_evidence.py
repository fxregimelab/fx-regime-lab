"""Point-in-time reasoning contract; no external requests or AI calls."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from src.paper.evidence import Evidence, ResearchPacket, validate_packet


def packet() -> ResearchPacket:
    now = datetime(2026, 10, 19, 10, tzinfo=UTC)
    facts = (
        Evidence("e1", "https://www.ecb.europa.eu/release", "a" * 64,
                 now - timedelta(hours=1), now - timedelta(minutes=30)),
        Evidence("e2", "https://www.federalreserve.gov/release", "b" * 64,
                 now - timedelta(hours=2), now - timedelta(minutes=20)),
    )
    return ResearchPacket(
        decision_at=now, evidence=facts, calendar_verified=True,
        news_coverage_verified=True, bull_case="Rates support thesis",
        bear_case="Dollar repricing invalidates", neutral_case="Wait for retest",
        falsifiers=("H1 close below invalidation", "Adverse policy surprise", "No retest"),
        cited_ids=("e1", "e2"), feature_snapshot_hash="c" * 64,
        spec_snapshot_hash="d" * 64, operator_id="test-model/prompt-v1",
    )


def test_verified_packet_gets_reproducible_digest() -> None:
    assert validate_packet(packet()) == validate_packet(packet())
    assert len(validate_packet(packet())) == 64


def test_missing_news_is_unknown_not_clean() -> None:
    with pytest.raises(ValueError):
        validate_packet(replace(packet(), news_coverage_verified=False))


def test_future_retrieval_cannot_support_past_decision() -> None:
    p = packet()
    future = replace(p.evidence[0], retrieved_at=p.decision_at + timedelta(seconds=1))
    with pytest.raises(ValueError):
        validate_packet(replace(p, evidence=(future, p.evidence[1])))


def test_unsupported_citation_rejected() -> None:
    with pytest.raises(ValueError):
        validate_packet(replace(packet(), cited_ids=("invented-source",)))


def test_stale_headline_rejected() -> None:
    p = packet()
    stale = replace(p.evidence[0], published_at=p.decision_at - timedelta(hours=5))
    with pytest.raises(ValueError):
        validate_packet(replace(p, evidence=(stale, p.evidence[1])))


def test_multiple_links_same_domain_are_not_independent_coverage() -> None:
    p = packet()
    second = replace(p.evidence[1], url="https://www.ecb.europa.eu/other")
    with pytest.raises(ValueError):
        validate_packet(replace(p, evidence=(p.evidence[0], second)))


def test_missing_falsifier_rejected() -> None:
    with pytest.raises(ValueError):
        validate_packet(replace(packet(), falsifiers=("a", "", "b")))
