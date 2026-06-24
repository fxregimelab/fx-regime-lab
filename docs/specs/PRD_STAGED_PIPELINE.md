# PRD: Staged Pipeline Orchestrator Refactor

## Problem Statement

The daily FX regime pipeline is currently orchestrated by a single monolithic module that handles fetching, signal math, regime classification, persistence, brief generation, validation, and alerting. This makes the code hard to test, reason about, and extend. There are no tests covering the orchestration layer, and changes require understanding the entire module. We need to split this into a narrow pipeline of deep, typed stages while preserving the immutable ledger and the live daily brief.

## Solution

Introduce a staged pipeline architecture with five deep, typed stages: Ingestion, Signal, Regime, Publish, and Validate. The orchestrator becomes a thin Prefect flow that composes these stages, handles correlation IDs, retries, and heartbeats, and loops over the three locked pairs where appropriate. Each stage has a clear, immutable input/output contract and can be unit tested in isolation using fake external ports.

## User Stories

1. As a developer, I want the orchestrator split into discrete stages, so that I can understand and modify one concern without reading the entire pipeline.
2. As a developer, I want each stage to have a typed input/output contract, so that mistakes are caught by type checking and tests.
3. As a developer, I want the pipeline to continue running even when non-critical fetchers fail, so that a delayed COT release does not break the daily brief.
4. As an operator, I want the immutable ledger to remain append-only, so that the public track record stays auditable.
5. As a developer, I want per-stage Prefect retries, so that transient database or Slack failures do not corrupt the ledger.
6. As a developer, I want unit tests for each stage using fake fetcher/writer/alert ports, so that tests run without hitting external data sources.
7. As an operator, I want the new pipeline to run in shadow mode alongside the old one, so that we can prove equivalence before flipping the live switch.
8. As a developer, I want the stage interfaces to accommodate future refactors, so that we do not need another breaking migration.
9. As an operator, I want the daily research brief to keep publishing during migration, so that readers see no interruption.
10. As a developer, I want the pair loop to live in the orchestrator, so that each stage is pair-scoped and easy to reason about.
11. As a developer, I want the ingestion stage to be date-scoped, so that shared macro fetches are not duplicated per pair.
12. As a developer, I want partial failures to be explicit via a health report, so that silent data degradation is impossible.
13. As an operator, I want alerting tied to publishing, so that a notification means the call has actually been published.
14. As a developer, I want frozen dataclasses for cross-stage objects, so that inputs are immutable and safe to pass through Prefect task results.
15. As a tester, I want one recorded ingestion fixture to exercise the full flow, so that integration tests are deterministic and offline.

## Implementation Decisions

- **Five stages**: `IngestionStage`, `SignalStage`, `RegimeStage`, `PublishStage`, `ValidateStage`.
- **Scope**: `IngestionStage` and `ValidateStage` are date-scoped; `SignalStage`, `RegimeStage`, and `PublishStage` are pair-scoped.
- **Pair loop**: The orchestrator loops over the three locked pairs and calls pair-scoped stages per pair. This keeps each stage small and makes per-pair retries natural.
- **Cross-stage contracts**: Inputs and outputs crossing stage boundaries are frozen dataclasses. The main objects are `IngestionSnapshot`, `SignalPipelineResult`, `PublishOutput`, and a `StageHealth` report carried by every stage.
- **Partial failure**: Each stage returns a `StageHealth` report listing missing and derived fields. Non-critical fetcher failures degrade the stage to `DEGRADED` status but allow the flow to continue. Critical failures (e.g., missing spot prices) still fail the flow.
- **Alerting**: Slack alerts and success heartbeats live inside `PublishStage` because they are side effects of the call being public.
- **Retries**: Each stage is a Prefect task with its own retry policy. Writes to the immutable ledger are idempotent by `(date, pair)` so retries are safe and cannot create duplicate ledger entries.
- **External ports**: Define narrow ports for fetching, writing, and alerting. Production implements these with the existing fetchers, database writer, and Slack client. Tests inject fakes.
- **Future-proofing**: `SignalPipelineResult` carries the full Layer 1/2/3 output so a narrowed `RegimeCallBuilder` can be dropped in later. `PublishStage` writes through a `WriterPort` so a future writer split only changes the adapter. `ValidateStage` consumes typed `RegimeCall` objects so validation unification can happen underneath.

```python
# Type shape encoding the cross-stage contracts (from prototype)
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal


@dataclass(frozen=True)
class StageHealth:
    stage_name: str
    status: Literal["OK", "DEGRADED", "FAILED"]
    missing_fields: list[str] = field(default_factory=list)
    derived_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IngestionSnapshot:
    date: date
    spots: dict[str, tuple[Any, ...]]
    yields: dict[str, float | None]
    cot_rows: list[Any]
    cross_asset: dict[str, float | None]
    macro: dict[str, Any] | None = None
    dqs_score: float | None = None
    stress_level: str | None = None
    health: StageHealth = field(
        default_factory=lambda: StageHealth("IngestionStage", "OK")
    )


@dataclass(frozen=True)
class SignalPipelineResult:
    pair: str
    date: date
    signal_row: Any
    layer1: Any
    layer2: Any
    layer3: Any
    health: StageHealth


@dataclass(frozen=True)
class PublishOutput:
    pair: str
    date: date
    regime_call: Any
    brief_markdown: str | None
    desk_card: dict[str, Any] | None
    alerts_sent: list[str]
    health: StageHealth
```

## Testing Decisions

- **Primary seam**: the orchestrator flow itself, tested end-to-end with fake fetcher/writer/alert ports and a recorded ingestion fixture.
- **Secondary seams**: individual stage unit tests during extraction, using the same fake ports.
- **What makes a good test**: tests assert external behavior (stage outputs, writes, alerts) rather than internal implementation details.
- **Prior art**: existing tests for ingestion snapshots, regime call builders, Layer 1/2/3 logic, writer, alerts, and validation engine.

## Out of Scope

- Adding new currency pairs (the 3-pair lock remains).
- Changing signal math formulas or Layer 1/2/3 logic.
- Changing the immutable ledger schema or validation horizons.
- Migrating off Prefect or adding GitHub Actions.
- Front-end changes.
- Creating formal ADRs (reversible enough to live in the PRD and design spec for now).

## Further Notes

- A detailed technical design document exists alongside this PRD.
- The project glossary has been updated with the new domain terms: `SignalPipelineResult`, `PublishOutput`, `StageHealth`, and the five stage names.
- Migration plan: build the new pipeline behind a feature flag, shadow-run for 20 trading days to cover T+5/T+20 validation horizons, then flip pair by pair.
