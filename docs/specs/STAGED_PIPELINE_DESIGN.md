# Staged Pipeline Design — Orchestrator Deepening

> Design for splitting `pipeline/src/scheduler/orchestrator.py` into a narrow, typed pipeline.

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Five stages** (`Ingestion → Signal → Regime → Publish → Validate`) | Maps cleanly to the existing data flow. Alerting lives inside `PublishStage` because alerts are side effects of "the world knowing about the call." |
| 2 | **Orchestrator loops over pairs** | Each of `SignalStage`, `RegimeStage`, and `PublishStage` is pair-scoped. `IngestionStage` and `ValidateStage` are date-scoped. |
| 3 | **`IngestionStage` is date-scoped** | FRED/CFTC/cross-asset fetches are shared across pairs. The orchestrator runs it once, then slices pair-specific views for `SignalStage`. |
| 4 | **Frozen dataclasses for cross-stage objects** | Consistent with existing `IngestionSnapshot` and `RegimeCall`. Gives immutability, clean Prefect result serialization, and hashability. |
| 5 | **Proceed with partial data** | A delayed COT or missing risk-reversal should not kill the daily brief. Each stage returns a `StageHealth` report listing missing/derived fields. |
| 6 | **Per-stage Prefect `@task` retries** | Retries live at stage boundaries. `writer.write_regime_call()` must be idempotent by `(date, pair)` so retry is safe. |
| 7 | **Ports/fakes for testing** | Define `FetcherPort`, `WriterPort`, and `AlertPort`. Unit tests inject fakes; one integration test uses a recorded `IngestionSnapshot` fixture. |
| 8 | **Shadow-run migration** | Build `orchestrator_v2.py` behind `USE_V2_PIPELINE`. Prove equivalence over 20 trading days (covers T+5/T+20 validation horizons), then flip the flag. |
| 9 | **Stage interfaces designed for Candidates 2/4/5** | `SignalPipelineResult` carries enough detail for a narrowed `RegimeCallBuilder`. `ValidateStage` consumes a typed `RegimeCall`. `PublishStage` uses a `WriterPort` for a future writer split. |

## Stage responsibility

| Stage | Scope | Responsibility |
|-------|-------|----------------|
| `IngestionStage` | Date | Fetch FRED, CFTC COT, spot/forward rates, risk reversals, cross-assets. Return one immutable `IngestionSnapshot`. |
| `SignalStage` | Pair | Slice pair data from `IngestionSnapshot`. Run Layer 1/2/3 math. Return `SignalPipelineResult`. |
| `RegimeStage` | Pair | Turn `SignalPipelineResult` into a `RegimeCall`. |
| `PublishStage` | Pair | Persist `RegimeCall` via `writer.py`, generate brief/desk-card artifacts, emit Slack alerts. Return `PublishOutput`. |
| `ValidateStage` | Date | Evaluate prior calls at T+5/T+20 horizons. Append results to `validation_log`. |

## Typed interfaces

```python
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
    spots: dict[str, tuple[SpotBar, ...]]
    yields: dict[str, float | None]
    cot_rows: list[CotRow]
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
    signal_row: SignalRow
    layer1: Layer1GateOutput
    layer2: Layer2DirectionalOutput
    layer3: Layer3ExecutionOutput
    health: StageHealth


@dataclass(frozen=True)
class PublishOutput:
    pair: str
    date: date
    regime_call: RegimeCall
    brief_markdown: str | None
    desk_card: dict[str, Any] | None
    alerts_sent: list[str]
    health: StageHealth
```

### Stage contracts

```python
class IngestionStage:
    async def run(self, as_of: date) -> IngestionSnapshot: ...


class SignalStage:
    def run(self, pair: str, snapshot: IngestionSnapshot) -> SignalPipelineResult: ...


class RegimeStage:
    def run(self, pair: str, signal_result: SignalPipelineResult) -> RegimeCall: ...


class PublishStage:
    async def run(self, pair: str, regime_call: RegimeCall) -> PublishOutput: ...


class ValidateStage:
    def run(self, as_of: date, pairs: list[str]) -> list[ValidationLogRow]: ...
```

## Retry / error strategy

- Each stage is a Prefect `@task` with its own retry policy.
- `IngestionStage`: non-critical fetcher failures degrade to `StageHealth.DEGRADED`; critical failures (spot, yields) fail the flow.
- `SignalStage`/`RegimeStage`: deterministic; retry on transient infra errors only.
- `PublishStage`: `write_regime_call()` must be idempotent by `(date, pair)`. If retries exhaust, the flow fails and no call is in the ledger.
- `ValidateStage`: append-only writes to `validation_log`; idempotent by `(call_date, pair, horizon)`.

## Test strategy

| Level | What | How |
|-------|------|-----|
| Unit | `SignalStage`, `RegimeStage` | Inject a minimal `IngestionSnapshot` fixture and assert exact `SignalPipelineResult`/`RegimeCall` fields. |
| Unit | `PublishStage` | Inject fake `WriterPort` and `AlertPort`; assert calls and no real Slack/Supabase traffic. |
| Integration | Full flow | Record one real `IngestionSnapshot`, run all stages with fake ports, assert outputs match recorded expectations. |
| E2E (optional) | One historical date | Run with live fetchers against cached HTTP responses; validate ledger append. |

## Migration plan

1. Create `pipeline/src/scheduler/orchestrator_v2.py` and the five stage modules under `pipeline/src/scheduler/stages/`.
2. Introduce `USE_V2_PIPELINE` env flag. Default `false`; old `run_daily` stays live.
3. Implement stages one at a time, starting with `SignalStage`/`RegimeStage` because they are deterministic and easiest to compare.
4. Shadow-run V2 for **20 trading days** (covers T+5 and T+20 validation horizons). Compare V2 outputs to live outputs.
5. Once equivalence is proven, flip `USE_V2_PIPELINE=true` for one pair (EUR/USD), then the others.
6. Remove the old orchestrator path only after 10+ successful live V2 runs.

## PRD decisions to record

> No project PRD currently exists. The following decisions should be recorded in the PRD once it is created, or in this spec until then:

1. Five-stage split and alerting ownership.
2. Date-scoped `IngestionStage` vs pair-scoped downstream stages.
3. Frozen dataclass strategy for cross-stage objects.
4. Partial-failure model via `StageHealth`.
5. Per-stage Prefect retries and idempotent writes.
6. Shadow-run migration with 20-trading-day equivalence window.
7. Stage interfaces future-proofed for Candidates 2, 4, and 5.

## CONTEXT.md updates

Added to `CONTEXT.md`:

- `SignalPipelineResult`
- `PublishOutput`
- `StageHealth`
- `IngestionStage`
- `SignalStage`
- `RegimeStage`
- `PublishStage`
- `ValidateStage`

No ADR created; the decisions are reversible enough to live in the PRD/spec for now.
