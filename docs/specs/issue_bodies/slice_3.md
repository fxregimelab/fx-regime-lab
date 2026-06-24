## Parent

#13

## What to build

Wire the five stages to production adapters and run them inside a thin Prefect `@flow` for a single pair (EUR/USD). This proves the real-world wiring works before adding multi-pair orchestration.

Work:
- Implement production `FetcherPort` using existing fetchers.
- Implement production `WriterPort` using the existing database writer.
- Implement production `AlertPort` using existing Slack alerting.
- Build the thin orchestrator `@flow` that composes the stages for one pair.
- Record one real `IngestionSnapshot` fixture (or use an existing cached one).
- Run the flow against the recorded fixture and assert outputs match recorded expectations.

## Acceptance criteria

- [ ] Production adapters for fetcher, writer, and alert ports exist.
- [ ] A Prefect `@flow` composes the stages for EUR/USD.
- [ ] The flow runs successfully against a recorded fixture without hitting live FRED/CFTC.
- [ ] Writes use the production writer but can be pointed at a test environment or dry-run mode.
- [ ] Existing tests still pass.

## Blocked by

- #15

## User stories covered

6, 15
