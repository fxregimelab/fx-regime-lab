"""Cross-stage domain contracts for the staged pipeline.

All objects crossing stage boundaries are frozen dataclasses so they are
immutable and safe to pass through Prefect task results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from src.types import (
    CotRow,
    Layer1GateOutput,
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    RegimeCall,
    SignalRow,
    SpotBar,
)

StageStatus = Literal["OK", "DEGRADED", "FAILED"]


@dataclass(frozen=True)
class StageHealth:
    """Health report carried by every pipeline stage.

    Indicates which inputs were missing, which fields were derived or degraded,
    and whether the stage completed fully or partially.
    """

    stage_name: str
    status: StageStatus
    missing_fields: list[str] = field(default_factory=list)
    derived_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IngestionSnapshot:
    """All fetched market and macro inputs for a single pipeline date.

    This object isolates fetcher outputs from signal logic and downstream
    regime-call assembly. It is immutable so that signal builders can depend
    on a stable contract.
    """

    date: date
    spots: dict[str, tuple[SpotBar, ...]]
    yields: dict[str, float | None]
    cot_rows: list[CotRow]
    cross_asset: dict[str, float | None]
    macro: dict[str, Any] | None = None
    dqs_score: float | None = None
    stress_level: str | None = None
    health: StageHealth = field(default_factory=lambda: StageHealth("IngestionStage", "OK"))


@dataclass(frozen=True)
class SignalPipelineResult:
    """Pair-scoped signal computation outputs.

    Carries the full deterministic outputs of Layer 1, Layer 2, and Layer 3 so
    that a narrowed ``RegimeCallBuilder`` can be dropped in later without
    changing this contract.
    """

    pair: str
    date: date
    signal_row: SignalRow
    layer1: Layer1GateOutput
    layer2: Layer2DirectionalOutput
    layer3: Layer3ExecutionOutput
    health: StageHealth = field(default_factory=lambda: StageHealth("SignalStage", "OK"))


@dataclass(frozen=True)
class PublishOutput:
    """Artifacts produced when a regime call is published.

    Captures the persisted regime call plus any brief, desk-card, and alert
    side effects so the publish stage is observable and testable.
    """

    pair: str
    date: date
    regime_call: RegimeCall
    brief_markdown: str | None
    desk_card: dict[str, Any] | None
    alerts_sent: list[str]
    health: StageHealth = field(default_factory=lambda: StageHealth("PublishStage", "OK"))
