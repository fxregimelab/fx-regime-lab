# Leaf 8.2 — legacy daily run contract

## Result

The legacy `run_daily` flow now returns a frozen `DailyRunOutput` instead of returning `None`. The result identifies only regime calls confirmed during that invocation, carries the DQS value, and exposes ordered stage-health evidence for signal quality, data quality, publication, and validation.

Validation is required. `run_validation(as_of_date=run_as_of)` now runs in the finalization helper and its exception is allowed to fail the daily run. A successful result includes `StageHealth("ValidateStage", "OK")`.

The lower-level daily flow no longer sends a success heartbeat. The outer scheduler wrapper owns the final completion notice.

## Publication evidence

`_persist_daily_regime_call` checks the regime call and signal row identities before writing. It also checks the fixed three-pair universe, the requested run date, and duplicate publication attempts before calling the writer. A pair is added to `published_pairs` only after `persist_regime_call` returns a nonempty, positive durable row ID. Missing pairs and stress withholding produce degraded publication health. Extra or duplicate published pairs are rejected.

Signal quality notes written by the existing rate repair are retained in `SignalQuality` health. Unqualified current rate inputs or missing qualified rate history therefore prevent a healthy result. Missing, non-finite, out-of-range, or low DQS values also produce degraded health.

## Verification

- Required scoped gate: `node ../scripts/repair/verify-pytest.mjs tests/test_daily_run_contract.py` from `pipeline` — `13 passed`, `REPAIR_PYTEST_VERIFIED`. This includes a zero-writer-call duplicate regression and a structural check against `run_daily.fn` proving that the actual flow calls both contract helpers and does not place finalization inside an exception-swallowing block.
- Scoped Ruff: `python -m ruff check src/scheduler/contracts.py src/scheduler/orchestrator.py tests/test_daily_run_contract.py` — passed.
- Scoped MyPy: `python -m mypy src/scheduler/contracts.py src/scheduler/orchestrator.py tests/test_daily_run_contract.py` — passed with no issues.
- Python runtime: 3.14.5.
- `git diff --check` — passed. Its only output was a line-ending warning for an unrelated pre-existing `pipeline/tests/test_writer.py` change.
- GitNexus impact before editing `run_daily`: CRITICAL, 38 upstream impacts across seven indexed processes and five modules. The result included unrelated UI paths, but confirmed scheduler and backfill callers in the blast radius.
- GitNexus change detection for the shared checkout: critical, 53 files and 333 symbols across all current repair work. This is a shared-checkout result, not a claim that leaf 8.2 changed that full scope.

## Boundary

This packet used mocks and scoped static checks. It did not start Docker, Hermes gateway services, schedulers, or external runtimes. It did not access credentials, write to the live database, send notifications, run the full pipeline suite, or prove a complete forecast. The existing uncommitted rate-input repairs in `orchestrator.py` were preserved.
