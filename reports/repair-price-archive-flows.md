# Price archive flow repair

## Result

Both daily publication paths now archive the provider observations before any regime call is published.

- The legacy `run_daily` path archives the fetched spot buffer before selecting signal history or entering the pair publication loop. An archive write failure propagates and leaves the publication function uncalled.
- The staged single-pair path archives before its publication stage.
- The staged multi-pair path archives one combined snapshot once, then publishes the requested pairs. It does not archive separately for each pair.
- Archive preparation gaps remain visible. Missing metadata, invalid or future observations, an empty archive, and unknown session windows make archive health `DEGRADED`.
- Archive write errors remain fatal. A flow cannot publish after a failed archive chunk.
- Validation health now comes from `ValidationRunResult` in both paths. A complete scan is `OK` only when the result is healthy. Missing mature outcomes or invalid calls are `DEGRADED` while retaining every report note, including `validation_scan_completed`. `None` or another report type is degraded and does not receive that marker.
- No archive observation is promoted into `historical_prices`.

## Archive receipt and retry behavior

The shared archive stage limits each writer call to 5,000 observations. It accepts a receipt only when counts are nonnegative integers, counts cover the whole chunk, IDs are positive integers in input order, and the claimed insert count cannot exceed the number of distinct returned IDs.

The in-memory writer uses canonical numeric comparison and returns the same durable ID for an identical retry. The production staged adapter delegates the complete payload to `src.db.writer.archive_price_observations`; it does not strip fields or fall back to an upsert.

A snapshot larger than 5,000 rows is durable one chunk at a time. If a later chunk fails, earlier successful chunks remain stored. Publication still stops because the failure propagates. This is deliberate partial durability, not snapshot-wide atomicity.

## Files covered by this leaf

- `pipeline/src/core/price_archive_stage.py`
- `pipeline/src/staged/ports.py`
- `pipeline/src/staged/adapters/writer.py`
- `pipeline/src/staged/fakes.py`
- `pipeline/src/staged/orchestrator.py`
- `pipeline/src/scheduler/orchestrator.py`
- `pipeline/tests/test_price_archive_flows.py`
- `pipeline/tests/test_staged_adapters.py`
- `pipeline/tests/test_staged_ports.py`
- `pipeline/tests/test_staged_fakes.py`
- `pipeline/tests/test_staged_orchestrator.py`
- `pipeline/tests/test_staged_multi_pair.py`
- `pipeline/tests/test_staged_eurusd_happy_path.py`
- `pipeline/tests/test_staged_publication_health.py`
- `pipeline/tests/test_daily_run_contract.py`
- `reports/repair-price-archive-flows.md`

## Verification

- Leaf G1: `93 passed in 36.36s`, followed by `REPAIR_PYTEST_VERIFIED`.
- Final focused legacy contract check after an import-only type-check fix: `17 passed in 3.65s`.
- Scoped Ruff across all owned Python source and test files: `All checks passed!`.
- Full pipeline mypy: `Success: no issues found in 183 source files`.
- GitNexus impact before editing reported `CRITICAL` for `_validate_task` (39 impacted symbols, 7 indexed processes) and `run_multi_pair_flow` (70 impacted symbols, 7 indexed processes). The new legacy finalizer and archive helper were absent from the stale index. The final repository-wide change scan reported critical risk across 67 shared changed files and 463 symbols; that result includes the other active repair leaves and is not a leaf-only diff.

The parent owns the integrated full pytest and Prefect wrapper checks, so this leaf did not duplicate them.

## Limits still open

- No live provider request was made. Provider access, entitlements, request manifests, full response identity, and final daily-boundary evidence remain unverified.
- No real PostgreSQL call ran in this leaf. Native PostgreSQL remained stopped. Database atomicity, concurrent retry behavior, role denial, immutable triggers, and exact RPC payload acceptance depend on the separate database acceptance gate.
- A stored observation is not proof of a canonical final close. The flow always records `canonical_close_unverified`; the provider-specific session and revision policy remains open under V08/P01.
- No Docker or heavier Hermes runtime was needed or started. The Hermes MCP server configuration was not changed.
- No environment variables, credentials, `_docs`, GitHub Actions, provider code, AI code, alerts, production database, commit, deployment, or historical ledger data were changed by this leaf.
