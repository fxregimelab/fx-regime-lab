# Validation price database repair — packet 11.3

The forward migration and isolated PostgreSQL checks pass. New evaluations bind the return to the original publication signal and the exact stored historical close. Existing v1 evaluations and statistics retain their values and version.

Checked against working files based on `9fa150538d08ab5a2a6c587976552944f47a724d`, on 27 September 2026. No commit, deployment, production query, credentials, or `.env` access was performed.

## Changes

`supabase/migrations/20260927000006_validation_price_evidence.sql` adds the three immutable JSON evidence columns. It keeps the original v1 function as a private helper and dispatches explicitly versioned v1 requests to that unchanged implementation. The public RPC accepts the new `publication-snapshot-v2` contract. Direct ledger mutations and helper execution are denied to application roles.

For v2, entry evidence must exactly match the original `publication_evidence.signal_payload` spot, pair, date and call ID. Endpoint evidence must have the frozen keys, storage source, pair and weekday-horizon date. On the first completion, its price must exactly equal the stored close. The historical row is locked against a concurrent correction until the transaction finishes. Missing, nonfinite, nonpositive, wrong-date and future-horizon inputs fail. Completed horizons use their retained evidence without rereading mutable historical prices.

The RPC checks direction, confidence, realized direction, correctness, Brier score, signed net return, costs, and optional legacy aliases. Numeric calculations allow an absolute difference of at most `1e-9` for ordinary floating-point arithmetic; fixed costs and evidence values require exact JSON numeric equality. T+5/T+20 dates use the frozen weekday-only calendar, not a market-holiday calendar.

The existing parent-call lock serializes concurrent revisions. Completed metrics and evidence cannot change; duplicate retries return the same row; a failed insertion rolls back supersession. The current `validation_observations` view requests only v2 but retains every published call, including calls without an evaluation. Its caller-based row permissions remain enabled.

`scripts/repair/verify-validation-db.py` now explicitly freezes `published-direction-v1` and no longer depends on the current batch producer. Its original historical RPC, population, aggregate, permission, concurrency and rollback checks still run. `scripts/repair/test-validation-db.sql` already explicitly targets v1 and needed no change.

## Observed checks

- `python scripts/repair/verify-validation-price-db.py` returned `VALIDATION_PRICE_DB_VERIFIED` after the final SQL changes.
- `python scripts/repair/verify-validation-db.py` returned `VALIDATION_DATABASE_VERIFIED` with the historical verifier decoupled from the current producer.
- `python -m ruff check scripts/repair/verify-validation-price-db.py scripts/repair/verify-validation-db.py` returned `All checks passed!`.

The new verifier uses actual PostgreSQL 17 on the parent-started task-local WSL socket and a fresh randomly named database, which it drops in `finally`. It exercises:

- Applying the migration twice while preserving old rows and statistics; continued v1 dispatch; v1 excluded from the current population.
- Two same-date publications with different entry prices and contradictory mutable signals; separate positive/negative outcomes from their own entries.
- Missing original evidence, cross-call entry substitution, unsupported version, metadata changes, wrong endpoint dates/pairs/sources, extra evidence keys, nearest-earlier-only storage, boolean/string/overflow/NaN/zero/negative prices and fabricated endpoints.
- Altered canonical metrics, costs and aliases; all three pairs; bearish payoff; neutral abstention; Python/SQL agreement around both five-basis-point deadband boundaries.
- Completed retry after endpoint deletion; changed evidence or metrics rejected; T+20 revision preserves T+5; injected insertion failure leaves the ledger unchanged.
- Simultaneous horizons and simultaneous duplicate retries; only one current row and no lost horizon.
- Anonymous/authenticated RPC denial, service-role RPC access, private-helper denial, ledger mutation/truncation denial, and caller-scoped population visibility.
- Raw SQL rejection of a future horizon despite an existing future price row.
- Actual `evaluate_call` output through `writer.write_validation_row`, redirecting only its RPC transport to the local database. This includes metadata and aliases, partial completion after T+5 storage changes, and a completed retry that reads no price evidence.

## Review limits

GitNexus MCP impact requests failed with storage version 42 versus reader version 40. The CLI did not index the SQL RPC. Its file-qualified `main` and `payload` reports returned CRITICAL risk with unrelated frontend/pipeline symbols, so those counts are not accepted as a reliable call graph for these verifier functions. The warning was reported; direct source inspection identified the actual RPC writer, aggregate population reader and frontend view readers. Parent integration review remains required.

This fixture combines the existing publication and validation schema fixtures and exercises the relevant forward migrations. It is not a rehearsal of the full historical production migration chain. No live database acceptance or observed research result is claimed.

Historical-close acquisition remains a separate dependency: current daily paths do not yet guarantee that all required completed bars are archived. Missing closes stay missing. Stored endpoint evidence identifies `historical_prices.close`; it does not invent a provider identity, release timestamp, executable trade, market-holiday treatment or observed transaction cost. Docker and heavier Hermes services were not required or started. Runtime shutdown belongs to the parent after its remaining checks.
