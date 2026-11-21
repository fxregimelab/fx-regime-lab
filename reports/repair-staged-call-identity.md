# Staged validation call identity repair

Date: 27 September 2026

## Result

Staged validation now reads the complete persisted call history for each pair and resolves an existing evaluation by the call's durable `call_id`. Two calls that share a date and pair are evaluated independently. A completed horizon is copied unchanged while a missing horizon is calculated and appended to the next canonical evaluation row.

A call whose due horizons are already complete exits before any price lookup. This also applies to neutral calls, whose correctness and Brier fields are deliberately null.

The production adapter uses the parent-owned writer contracts:

- `get_historical_regime_calls(pair, limit=None)` for complete paginated history
- `get_validation_log_for_call(call_id)` for one current canonical evaluation

The fake writer follows the same contracts. It does not invent an evaluation when no row exists for the requested call ID.

## Regression evidence

The staged-validation tests cover these cases:

- same date and pair, separate durable IDs, and opposite predicted directions;
- one same-date call with a completed T+5 result that remains unchanged while T+20 is added;
- another same-date call receiving both missing horizons independently;
- a mature call before 5,000 later records, proving the stage requests all history rather than the old capped tail;
- a completed neutral call exiting without a price request or another write;
- missing call IDs, mismatched call-ID lookup results, missing directions, immature calls, and missing exact price history all fail closed.

Scoped gate from `pipeline`:

```text
node ../scripts/repair/verify-pytest.mjs tests/test_staged_adapters.py tests/test_staged_fakes.py tests/test_staged_ports.py tests/test_staged_validation.py
31 passed in 4.04s
REPAIR_PYTEST_VERIFIED
```

Scoped static checks:

```text
ruff check <eight owned Python files>
All checks passed!

mypy <eight owned Python files>
Success: no issues found in 8 source files
```

GitNexus impact analysis reported LOW risk for the changed staged-port symbols: two direct test dependents and no affected execution processes. The repository-wide `detect-changes` result was CRITICAL because the shared checkout already contains a large multi-packet repair across 35 files and 28 flows. That repository-wide result is not a scoped risk rating for this leaf.

## Remaining limits

This leaf does not change scheduling or price ingestion. `ProductionFetcherPort` currently requests 120 calendar days of spot history. Calls older than the available snapshot, or calls whose exact T+5 or T+20 trading-day close is absent, remain unevaluated and are not given substitute prices. A separate historical source or backlog schedule is still required to mature every old call beyond that window.

The full repository test suite, live database behavior, Prefect scheduling, deployment, and production data were not exercised in this leaf. The parent packet owns those checks. No runtime, external service, or production access was started.
