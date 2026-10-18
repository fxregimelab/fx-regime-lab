"""Evidence-bound UTC clock; no wall-clock access or inferred display conversion."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from src.paper.contracts import ContractError


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def digest(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class TimestampEvidence:
    """Archived official contract reference, not an unverified documentation claim."""

    source: str
    content_sha256: str
    timestamp_semantics: str


@dataclass(frozen=True)
class ClockSample:
    broker_epoch: float
    computer_utc_epoch: float
    terminal_epoch: float
    terminal_offset_seconds: int
    uncertainty_seconds: float
    bar_open_epoch: float


@dataclass(frozen=True)
class ClockProfile:
    samples: tuple[ClockSample, ...]
    evidence: TimestampEvidence
    observed_bar_close: float
    valid_until: float

    def __post_init__(self) -> None:
        if (len(self.samples) < 3 or not digest(self.evidence.content_sha256)
                or not self.evidence.source.strip()
                or self.evidence.timestamp_semantics != "utc_epoch_seconds"):
            raise ContractError("CLOCK_UNVERIFIED", "three samples and official evidence required")
        if not finite(self.observed_bar_close) or not finite(self.valid_until):
            raise ContractError("CLOCK_UNVERIFIED", "invalid profile interval")
        previous = -math.inf
        offsets: set[int] = set()
        for s in self.samples:
            values = (s.broker_epoch, s.computer_utc_epoch, s.terminal_epoch,
                      s.uncertainty_seconds, s.bar_open_epoch)
            if (not all(finite(v) for v in values)
                    or type(s.terminal_offset_seconds) is not int
                    or not 0 <= s.uncertainty_seconds <= 1
                    or s.computer_utc_epoch <= previous
                    or abs(s.broker_epoch - s.computer_utc_epoch) > s.uncertainty_seconds
                    or abs(s.terminal_epoch - s.broker_epoch - s.terminal_offset_seconds)
                    > s.uncertainty_seconds):
                raise ContractError("CLOCK_SKEW", "sample chronology/offset disagreement")
            previous = s.computer_utc_epoch
            offsets.add(s.terminal_offset_seconds)
        before = [s for s in self.samples if s.computer_utc_epoch < self.observed_bar_close]
        after = [s for s in self.samples if s.computer_utc_epoch >= self.observed_bar_close]
        if (len(offsets) != 1 or not before or not after
                or any(s.bar_open_epoch >= self.observed_bar_close for s in before)
                or any(s.bar_open_epoch != self.observed_bar_close for s in after)
                or self.valid_until <= previous):
            raise ContractError("CLOCK_UNVERIFIED", "no corroborated bar-close transition")

    @classmethod
    def observe(cls, samples: tuple[ClockSample, ...], evidence: TimestampEvidence,
                observed_bar_close: float, valid_until: float) -> ClockProfile:
        return cls(samples, evidence, observed_bar_close, valid_until)

    @property
    def profile_id(self) -> str:
        return hashlib.sha256(repr(self).encode("utf-8")).hexdigest()

    @property
    def uncertainty_seconds(self) -> float:
        return max(s.uncertainty_seconds for s in self.samples)

    def to_utc_epoch(self, epoch: float, now: float) -> float:
        if (not finite(now) or not finite(epoch) or epoch < 0
                or now < self.samples[-1].computer_utc_epoch or now > self.valid_until):
            raise ContractError("CLOCK_UNVERIFIED", "invalid epoch or expired clock profile")
        # Official UTC epoch is already UTC. Terminal display offset is evidence only.
        return epoch

    def require_fresh(self, epoch: float, now: float, max_age: float, code: str) -> None:
        stamp = self.to_utc_epoch(epoch, now)
        if stamp - now > self.uncertainty_seconds or now - stamp > max_age:
            raise ContractError(code, "observation is stale or future-dated")
