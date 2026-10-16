"""DQS-driven confidence cap policy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


def dqs_confidence_cap(dqs: float | None) -> float | None:
    """DQS-driven confidence upper bound; returns ``None`` when no cap applies."""

    if dqs is None:
        return None
    if dqs >= 0.90:
        return None
    if dqs >= 0.75:
        return 0.85
    if dqs >= 0.60:
        return 0.70
    if dqs >= 0.50:
        return 0.55
    return None


@runtime_checkable
class ConfidenceCap(Protocol):
    """Apply a confidence upper bound from data quality score."""

    def cap(self, dqs: float | None) -> float | None: ...


class DqsConfidenceCap:
    """DQS ladder confidence cap (canonical engine behavior)."""

    def cap(self, dqs: float | None) -> float | None:
        return dqs_confidence_cap(dqs)
