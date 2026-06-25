## Parent

#13

## What to build

Extend the orchestrator to loop over all three locked pairs (EUR/USD, USD/JPY, USD/INR) and add resilience: partial failure handling and per-stage Prefect retries.

Work:
- Move the pair loop into the orchestrator `@flow`.
- Run `SignalStage`, `RegimeStage`, and `PublishStage` per pair.
- Propagate `StageHealth` so a non-critical fetcher failure degrades one pair without killing the others.
- Add `@task(retries=..., retry_delay_seconds=...)` to each stage.
- Ensure writes remain idempotent by `(date, pair)`.
- Test the multi-pair flow with a mix of healthy and degraded fetcher outputs.

## Acceptance criteria

- [ ] Orchestrator loops over all three pairs.
- [ ] Per-stage Prefect retries are configured.
- [ ] A degraded non-critical fetcher produces `StageHealth.DEGRADED` but the flow continues.
- [ ] A critical fetcher failure (e.g., missing spot prices) fails the flow.
- [ ] Multi-pair test runs without real external services.
- [ ] Existing tests still pass.

## Blocked by

- #16

## User stories covered

3, 5, 10, 12
