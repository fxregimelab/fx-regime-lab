## Parent

#13

## What to build

Define the cross-stage domain contracts and external ports that all later slices depend on. This is pure prefactoring: no stage logic, no real adapters, no orchestrator wiring.

Contracts to define (frozen dataclasses):
- `StageHealth` — status, missing fields, derived fields, notes.
- `IngestionSnapshot` — date-scoped raw fetch outputs.
- `SignalPipelineResult` — pair-scoped signal row plus Layer 1/2/3 outputs.
- `PublishOutput` — persisted regime call plus brief/desk-card/alert artifacts.

Ports to define (protocols or abstract interfaces):
- `FetcherPort` — returns an `IngestionSnapshot` for a date.
- `WriterPort` — persists a `RegimeCall` and validation rows.
- `AlertPort` — emits Slack success/heartbeat/low-DQS alerts.

These contracts must be expressive enough to support future Candidate 2 (RegimeCallBuilder narrowing), Candidate 4 (validation unification), and Candidate 5 (writer split) without breaking changes.

## Acceptance criteria

- [ ] All four cross-stage dataclasses exist as frozen dataclasses with sensible defaults.
- [ ] All three ports are defined with narrow methods.
- [ ] A fake implementation of each port exists and is usable in tests.
- [ ] Existing tests still pass.
- [ ] `CONTEXT.md` glossary terms are updated if any contract names change during implementation.

## Blocked by

None — can start immediately.

## User stories covered

2, 8, 14
