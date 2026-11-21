# Staged atomic publication repair

Date: 27 September 2026  
Scope: leaf 9.3 staged publication boundary

## Result

The staged pipeline now sends a regime call and its exact signal row through one publication method. `PublishStage` does not issue separate call and signal writes, and it does not send a success or degraded notice until the atomic writer returns a durable call ID.

`ProductionWriterPort.publish_regime_call` delegates to `src.core.regime_persist.persist_regime_call` with the supplied signal row and correlation ID. Its legacy `write_regime_call` method fails with `Use publish_regime_call with signal evidence`, so staged production code has no call-only fallback.

The fake writer keeps the old call-only method for validation test setup. Its atomic method:

- checks the locked pair set, matching call/signal pair and date, and nonempty source, strategy and model provenance;
- keys publication identity by pair, date, data source, strategy version and model version;
- returns the original ID for an exact repeated payload, excluding correlation metadata;
- rejects different call or signal content at the same identity without adding or changing a record;
- stores detached call and signal snapshots, including the full `data_quality_notes` list;
- refuses to adopt a legacy seeded call that has no publication evidence.

The fake `signal_rows` list records the evidence supplied to atomic publications for local assertions. It is not a model of the database's live-only `signals` current projection. Live/backtest projection behavior remains owned by the database RPC and its PostgreSQL acceptance checks.

## Verification

- Repair ledger gate: `69 passed in 14.12s`, followed by `REPAIR_PYTEST_VERIFIED`.
- Scoped Ruff: all owned staged source and tests passed.
- Scoped mypy: four changed staged source files passed with no issues.
- Source check: `PublishStage` contains one call to `publish_regime_call` and no call to either legacy write method.
- `git diff --check` found no whitespace errors in the owned tracked files.

## Impact and boundaries

Pre-edit GitNexus impact reported MEDIUM risk for `WriterPort` (15 impacted symbols, 12 direct, no indexed execution flow) and LOW risk for `ProductionWriterPort`, `FakeWriterPort`, `PublishStage`, and the legacy method. The required final whole-tree `detect-changes` scan reported CRITICAL because the shared repair checkout contains 57 changed files, 374 changed symbols and 293 affected flows. That result is a repository-wide lower-signal warning, not a leaf-only risk classification; parent review is still required before commit.

No database, network, credentials, Docker, Hermes gateway, deployment, migration, historical ledger, or production data was used or changed. Real PostgreSQL rollback, concurrency, immutability, projection-history, migration-reapplication and role-permission checks remain separate release gates.
