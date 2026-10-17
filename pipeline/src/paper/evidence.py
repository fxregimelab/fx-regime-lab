"""Validate a bounded intraday-news reasoning packet, not the truth of its claims.

Collectors must supply original-content hashes, publication/retrieval times and
coverage evidence. Older macro context belongs in a separate frozen feature
snapshot. This schema does not fetch news, compute features, verify that a model
read a specification, or prove that two domains are independent publishers.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    url: str
    content_hash: str
    published_at: datetime
    retrieved_at: datetime


@dataclass(frozen=True)
class ResearchPacket:
    decision_at: datetime
    evidence: tuple[Evidence, ...]
    calendar_verified: bool
    news_coverage_verified: bool
    bull_case: str
    bear_case: str
    neutral_case: str
    falsifiers: tuple[str, str, str]  # one per bull/bear/neutral case
    cited_ids: tuple[str, ...]
    feature_snapshot_hash: str
    spec_snapshot_hash: str
    operator_id: str


def _hash_valid(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_packet(packet: ResearchPacket) -> str:
    """Return reproducible packet digest or fail closed on unverifiable coverage.

    Caller must archive hash-addressed content separately. A supplied hash is a
    reference, not proof that its content is available or has been read by an AI.
    """
    times = [packet.decision_at]
    times += [t for e in packet.evidence for t in (e.published_at, e.retrieved_at)]
    if any(t.tzinfo is None or t.utcoffset() is None for t in times):
        raise ValueError("Evidence timestamps must be timezone-aware")
    if packet.calendar_verified is not True or packet.news_coverage_verified is not True:
        raise ValueError("Missing calendar/news coverage is unknown, not clean")
    texts = (packet.operator_id, packet.bull_case, packet.bear_case, packet.neutral_case)
    if any(not value.strip() for value in (*texts, *packet.falsifiers)):
        raise ValueError("Operator, three cases and all falsifiers are mandatory")
    if len(packet.falsifiers) != 3:
        raise ValueError("Each case needs a separate falsifier")
    hashes = (packet.feature_snapshot_hash, packet.spec_snapshot_hash)
    if not all(_hash_valid(value) for value in hashes):
        raise ValueError("Frozen feature/spec SHA-256 references are required")
    ids: set[str] = set()
    domains: set[str] = set()
    for evidence in packet.evidence:
        if not evidence.evidence_id.strip() or evidence.evidence_id in ids:
            raise ValueError("Evidence IDs must be nonempty and unique")
        ids.add(evidence.evidence_id)
        parsed = urlparse(evidence.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Evidence must cite an HTTPS source")
        domains.add(parsed.hostname.lower().removeprefix("www."))
        if not _hash_valid(evidence.content_hash):
            raise ValueError("Original evidence content hash required")
        if not evidence.published_at <= evidence.retrieved_at <= packet.decision_at:
            raise ValueError("Evidence was unavailable at the decision time")
        if packet.decision_at - evidence.published_at > timedelta(hours=4):
            raise ValueError("Intraday headline coverage is stale")
    if len(domains) < 2:
        raise ValueError("At least two source domains required; independence still needs review")
    if len(set(packet.cited_ids)) < 2 or not set(packet.cited_ids) <= ids:
        raise ValueError("Reasoning must cite at least two known evidence IDs")
    payload = json.dumps(asdict(packet), default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
