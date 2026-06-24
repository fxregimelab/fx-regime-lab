## Parent

#13

## What to build

Build all five stages and run a complete EUR/USD pipeline using fake ports. This is the first tracer bullet: a narrow but complete path through every layer.

Stages to implement:
- `IngestionStage` — date-scoped, returns `IngestionSnapshot`.
- `SignalStage` — pair-scoped, slices EUR/USD data from snapshot, runs Layer 1/2/3, returns `SignalPipelineResult`.
- `RegimeStage` — pair-scoped, turns signal result into `RegimeCall`.
- `PublishStage` — pair-scoped, uses fake `WriterPort` and `AlertPort`, returns `PublishOutput`.
- `ValidateStage` — date-scoped, evaluates prior EUR/USD calls at T+5/T+20, returns validation rows.

End-to-end test:
- Build a minimal `IngestionSnapshot` fixture for EUR/USD.
- Run all five stages in sequence with fake ports.
- Assert the final `RegimeCall` and validation rows match expectations.
- Assert no real external services were called.

## Acceptance criteria

- [ ] All five stage classes/functions exist and are independently callable.
- [ ] A test runs the full EUR/USD path end-to-end with fake ports.
- [ ] The test asserts on `RegimeCall` fields and validation row content.
- [ ] `StageHealth` is produced by each stage and propagated through the pipeline.
- [ ] Existing tests still pass.

## Blocked by

- #14

## User stories covered

1, 4, 6, 11, 13
