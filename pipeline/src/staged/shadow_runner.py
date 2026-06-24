"""Shadow-run harness for the staged v2 pipeline.

Runs v2 alongside the legacy v1 pipeline without writing to the live ledger,
then compares RegimeCall fields and brief artifacts pair by pair.
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from prefect import flow

from src.staged.contracts import PublishOutput
from src.staged.fakes import FakeAlertPort, FakeWriterPort
from src.staged.orchestrator import run_multi_pair_flow
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.types import RegimeCall

# Fields that are allowed to differ within a small tolerance because v1 and v2
# may take slightly different floating-point paths for the same underlying math.
_NUMERIC_TOLERANCE: dict[str, float] = {
    "confidence": 0.01,
    "signal_composite": 0.01,
    "special_signal_value": 0.01,
}

# RegimeCall fields that participate in equivalence.
_COMPARE_FIELDS: tuple[str, ...] = (
    "pair",
    "date",
    "regime",
    "confidence",
    "signal_composite",
    "rate_signal",
    "primary_driver",
    "entry_timing",
    "position_size",
    "stop_level",
    "data_quality_score",
    "stress_level",
    "predicted_direction",
    "directional_bias",
    "conviction",
    "cot_signal",
    "vol_signal",
    "oi_signal",
    "rr_signal",
    "special_signal_value",
    "special_signal_label",
    "regime_category",
    "model_version",
)


@dataclass(frozen=True)
class FieldDiff:
    """A single mismatched field between v1 and v2 outputs."""

    field: str
    v1: Any
    v2: Any


@dataclass(frozen=True)
class ShadowComparison:
    """Comparison result for one pair on one date."""

    pair: str
    date: datetime.date
    equivalent: bool
    regime_call_diffs: tuple[FieldDiff, ...]
    brief_match: bool | None
    desk_card_match: bool | None


@dataclass(frozen=True)
class ShadowRunResult:
    """Aggregated shadow-run result for all pairs on one date."""

    date: datetime.date
    comparisons: dict[str, ShadowComparison]
    equivalent: bool
    v2_outputs: dict[str, PublishOutput] = field(repr=False)


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def compare_regime_calls(
    v1: RegimeCall | None,
    v2: RegimeCall | None,
) -> tuple[FieldDiff, ...]:
    """Return a tuple of field-level differences between two regime calls.

    ``None`` inputs are treated as a single missing-field diff.
    """

    if v1 is None and v2 is None:
        return ()
    if v1 is None or v2 is None:
        return (FieldDiff("regime_call", v1, v2),)

    diffs: list[FieldDiff] = []
    for field_name in _COMPARE_FIELDS:
        v1_val = getattr(v1, field_name)
        v2_val = getattr(v2, field_name)

        if field_name in _NUMERIC_TOLERANCE:
            if v1_val is None and v2_val is None:
                continue
            if v1_val is None or v2_val is None:
                diffs.append(FieldDiff(field_name, v1_val, v2_val))
                continue
            try:
                if not math.isclose(
                    float(v1_val),
                    float(v2_val),
                    abs_tol=_NUMERIC_TOLERANCE[field_name],
                ):
                    diffs.append(FieldDiff(field_name, v1_val, v2_val))
            except (TypeError, ValueError):
                diffs.append(FieldDiff(field_name, v1_val, v2_val))
            continue

        if v1_val != v2_val:
            diffs.append(FieldDiff(field_name, v1_val, v2_val))

    return tuple(diffs)


def compare_briefs(
    v1_brief: str | None,
    v2_brief: str | None,
) -> bool:
    """Compare v1 and v2 brief markdown, ignoring whitespace differences."""

    return _normalize_text(v1_brief) == _normalize_text(v2_brief)


def compare_desk_cards(
    v1_card: dict[str, Any] | None,
    v2_card: dict[str, Any] | None,
) -> bool:
    """Compare desk-card payloads, ignoring whitespace in string values."""

    if v1_card is None and v2_card is None:
        return True
    if v1_card is None or v2_card is None:
        return False
    if set(v1_card.keys()) != set(v2_card.keys()):
        return False
    for key in v1_card:
        v1_val = v1_card[key]
        v2_val = v2_card[key]
        if isinstance(v1_val, str) and isinstance(v2_val, str):
            if _normalize_text(v1_val) != _normalize_text(v2_val):
                return False
        elif v1_val != v2_val:
            return False
    return True


def make_comparison(
    pair: str,
    as_of: datetime.date,
    *,
    v1_call: RegimeCall | None,
    v2_call: RegimeCall | None,
    v1_brief: str | None,
    v2_brief: str | None,
    v1_desk_card: dict[str, Any] | None,
    v2_desk_card: dict[str, Any] | None,
) -> ShadowComparison:
    """Compare v1 and v2 artifacts for one pair."""

    regime_call_diffs = compare_regime_calls(v1_call, v2_call)
    brief_match = (
        None
        if v1_brief is None and v2_brief is None
        else compare_briefs(v1_brief, v2_brief)
    )
    desk_card_match = (
        None
        if v1_desk_card is None and v2_desk_card is None
        else compare_desk_cards(v1_desk_card, v2_desk_card)
    )
    equivalent = (
        not regime_call_diffs
        and (brief_match is None or brief_match)
        and (desk_card_match is None or desk_card_match)
    )

    return ShadowComparison(
        pair=pair,
        date=as_of,
        equivalent=equivalent,
        regime_call_diffs=regime_call_diffs,
        brief_match=brief_match,
        desk_card_match=desk_card_match,
    )


@flow(name="shadow-run-v2-comparison")
async def run_shadow_comparison(
    as_of: datetime.date,
    *,
    v1_calls: Mapping[str, RegimeCall],
    v1_briefs: Mapping[str, str | None],
    v1_desk_cards: Mapping[str, dict[str, Any] | None] | None = None,
    fetcher: FetcherPort,
    shadow_writer: WriterPort | None = None,
    shadow_alert: AlertPort | None = None,
    pairs: Sequence[str] | None = None,
    correlation_id: str | None = None,
    run_validation: bool = False,
) -> ShadowRunResult:
    """Run v2 in shadow mode and compare its outputs to the provided v1 outputs.

    No live ledger writes occur: the injected fetcher is shared with v1 logic,
    but v2 persistence and alerting go through shadow ports that only capture
    results in memory.
    """

    if shadow_writer is None:
        shadow_writer = FakeWriterPort()
    if shadow_alert is None:
        shadow_alert = FakeAlertPort()

    v1_desk_cards = v1_desk_cards or {}

    v2_output = await run_multi_pair_flow(
        as_of,
        fetcher=fetcher,
        writer=shadow_writer,
        alert=shadow_alert,
        pairs=pairs,
        correlation_id=correlation_id,
        run_validation=run_validation,
    )

    comparisons: dict[str, ShadowComparison] = {}
    requested_pairs = pairs if pairs is not None else list(v2_output.outputs.keys())
    for pair in requested_pairs:
        v2_publish = v2_output.outputs[pair]
        comparisons[pair] = make_comparison(
            pair=pair,
            as_of=as_of,
            v1_call=v1_calls.get(pair),
            v2_call=v2_publish.regime_call,
            v1_brief=v1_briefs.get(pair),
            v2_brief=v2_publish.brief_markdown,
            v1_desk_card=v1_desk_cards.get(pair),
            v2_desk_card=v2_publish.desk_card,
        )

    return ShadowRunResult(
        date=as_of,
        comparisons=comparisons,
        equivalent=all(c.equivalent for c in comparisons.values()),
        v2_outputs=v2_output.outputs,
    )


def count_consecutive_equivalent_days(
    history: Sequence[ShadowRunResult],
    pair: str,
) -> int:
    """Count the most recent consecutive equivalent days for ``pair``.

    The count is used to decide whether a pair has satisfied the configured
    20-trading-day equivalence window before flipping to live v2.
    """

    count = 0
    for result in reversed(history):
        comparison = result.comparisons.get(pair)
        if comparison is None or not comparison.equivalent:
            break
        count += 1
    return count
