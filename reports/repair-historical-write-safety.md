# Historical write safety repair

## Result

Two unsafe maintenance paths were retired.

`risk_reversal_proxy.py` no longer calculates a synthetic options-market value,
opens a private PostgreSQL connection, changes `signals` or `regime_calls`, or
disables database protections. Its existing Python entry point now defaults to
read-only inspection of a bounded number of signal rows for the three locked
pairs. Passing `dry_run=False` fails before any database access and explains
that observed OTC data and a new versioned replay are required.

`batch_validation_stats.py` no longer contains its own formulas, raw SQL,
trigger changes, or a delete-and-rebuild routine. `run_batch_stats` delegates
once to `src.validation.aggregate.run_aggregate_stats` and passes through the
requested as-of date. The canonical aggregator owns cohort separation, metric
definitions and persistence through the central writer.

## Intentional retirement and rebuilt path

- Retired: synthetic risk-reversal publication and revision of prior calls.
- Retained: a bounded, read-only inventory command for operational inspection.
- Retired: the parallel validation calculator and direct PostgreSQL rebuild.
- Rebuilt: the legacy batch entry as a compatibility adapter to the canonical
  cohort aggregator.

## Verification

`tests/test_historical_write_safety.py` checks that the canonical aggregator is
called once with the supplied date, write mode is rejected before I/O, read-only
inspection remains bounded, and neither module contains direct or destructive
SQL paths.

Observed checks on 27 September 2026:

- `ruff check` on the two modules and the focused test: passed.
- `node ../scripts/repair/verify-pytest.mjs tests/test_historical_write_safety.py`:
  5 passed and the repair verifier accepted the run.
- scoped `mypy` reached the three requested files without a finding in them,
  then failed on an existing type error in `src/staged/fakes.py:64`, outside
  this leaf's file ownership.

## Limits

This repair does not supply OTC risk-reversal observations, create a historical
replay, validate any risk-reversal formula, prove research validity, or run a
production database operation. The retained inspection counts fetched rows;
it does not claim that those rows contain genuine OTC observations. GitNexus
MCP could not read the current index because its storage reader was older than
the index. The matching CLI returned unrelated callers for these standalone
functions, so its reported CRITICAL blast radius was treated as unreliable;
an exact repository search found no external callers of either entry point.
The same MCP version mismatch prevented the final indexed change scan; the CLI
change scan completed without a usable report in this already-dirty worktree.
