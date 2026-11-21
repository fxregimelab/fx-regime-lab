# Historical observation acquisition repair

## Result

Historical Yahoo downloads now enter the append-only `price_observations` archive. They no longer upsert `historical_prices`, drop unsupported schema fields, or call the live daily scheduler under a replay label. Counts are logged as provisional provider observations because archival does not establish a canonical close.

The acquisition path retains the configured Yahoo instrument, the `yahoo` provider label, a UTC receipt captured after download, the Yahoo index timezone where supplied, and `adjusted=false`. It uses the shared strict Yahoo parser, rejects invalid OHLC rows instead of creating values from the close, enforces inclusive calendar-date bounds, and archives through the central writer in batches of at most 5,000 rows.

## Safety boundaries

- `writer.write_historical_prices([])` remains a no-op for compatibility. Any nonempty call fails before database client access with the required source-qualification and migration message.
- `backfill_spots` is the explicit archive-only multi-pair helper. Acquisition and archive failures propagate to the caller.
- `replay_pipeline_for_date` and `run_backfill_range` fail before scheduler imports or acquisition. The dedicated simulation engine was not changed.
- `fetch_max_history` validates `years_back` and delegates to the same archive path from 1 January of the requested start year through the current UTC date.
- The population script now parses its CLI arguments correctly and states that archived observations are not qualified validation closes.

## Verification

- Scoped repair gate: 72 passed; `REPAIR_PYTEST_VERIFIED`.
- Scoped Ruff: clean.
- Full pipeline MyPy: clean across 186 source files.
- CLI help: imports successfully and exits before acquisition.
- GitNexus pre-edit impact checks reported CRITICAL reach for the changed legacy boundaries. The shared checkout change scan also reports CRITICAL because it includes 73 dirty files from the wider repair, not just this leaf. The leaf regressions cover direct writer rejection, parser metadata, invalid rows, date and pair bounds, 5,000-row chunking, error propagation, the retired replay boundary, UTC span delegation, and CLI wording.

During the first CLI smoke check, the old script ignored `--help` and made one Yahoo request before failing at the missing database credentials. It returned 147 EUR/USD bars in memory. No database write occurred, the result was not saved, and it is not used as acceptance evidence. The CLI parser was then fixed and the help check re-run without acquisition.

## Limits still open

This repair does not qualify Yahoo daily bars as final market closes, establish a canonical FX session, preserve full raw response envelopes or request manifests, or make these observations eligible for validation and replay. Source qualification, a canonical-close migration, actual archive database acceptance, and release observation remain open. No production database, provider credential, deployment, alert, AI call, or research-acceptance claim was used for this leaf.
