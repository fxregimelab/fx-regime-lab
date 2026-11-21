# Aggregate validation repair report

Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`  
Branch: `repair/evidence-contracts`  
Scope: `pipeline/src/validation/aggregate.py` and its focused tests  
Runtime: no Docker, Hermes gateway, database, or production service was required or started.

## What changed

V04 now uses an explicit gross directional cohort. A row is scored only when:

- `predicted_direction` is exactly `BULLISH` or `BEARISH` after normalization;
- the horizon correctness value is a Boolean;
- the requested horizon return is present and finite;
- the call has a parseable date; and
- that date has reached the requested T+5 or T+20 trading-day horizon by `as_of_date`.

Neutral, blank, unknown, pending, undated, malformed-date, missing-outcome, and missing-return rows do not enter accuracy denominators. Future-dated calls are excluded from the raw as-of count as well as every scored metric. The rolling 90-day cohort is bounded on both sides: `as_of_date - 90 days <= call date <= as_of_date`.

The net win rate uses its own subset of the mature gross cohort. Only rows with a Boolean net outcome enter its denominator. The internal `net_directional_calls` value records that denominator, but it is deliberately not added to the database payload until the schema and public metric contract are coordinated.

The V05 calibration repair builds each probability/outcome observation as a pair. Probabilities must be finite and within `[0, 1]`; outcomes must be Boolean. Missing or invalid values remove the whole observation instead of allowing the probability and outcome arrays to drift apart.

V06 now converts the underlying pair return to a descriptive per-call signed payoff: `+1 * return` for BULLISH and `-1 * return` for BEARISH. Thus a correct bearish call on a negative underlying return is positive. The existing `mean_log_return_bps` and `return_std_bps` payload column names remain for schema compatibility. Their values now describe signed call payoffs. The legacy Sharpe-like and maximum-drawdown columns remain in the payload but are always `None`; overlapping forecast calls do not define exposures or an equity curve.

## Verification

GitNexus pre-edit impact reports were LOW risk. `_compute_horizon` had four direct callers and one production flow through `compute_aggregate_stats` and `run_pipeline`. `_calibration_buckets`, `_sharpe_like`, and `_max_drawdown_bps` were confined to aggregate code and focused tests.

Executed from `pipeline/`:

```text
pytest tests/test_validation_aggregate.py -q
11 passed in 2.01s

ruff check src/validation/aggregate.py tests/test_validation_aggregate.py
All checks passed!

mypy src/validation/aggregate.py
Success: no issues found in 1 source file
```

The regression cases cover mixed pending and mature rows, neutral and blank calls, missing gross outcomes and returns, missing net outcomes, future dates, both rolling-window boundaries, T+20 maturity, correct short calls, missing and invalid calibration probabilities, missing and malformed legacy dates, and `datetime` normalization.

## Remaining evidence limits

This patch does not infer provenance that the ledger does not carry. Undated and malformed-date legacy rows remain visible in `total_calls` but cannot enter scored cohorts because their maturity and as-of eligibility cannot be proved. The aggregate fetch still mixes any sources or evaluation versions returned by the writer; V07 requires explicit provenance/version fields and coordinated query changes.

The stored Brier values are still consumed after finite `[0, 1]` validation. Event-definition parity between live and replay calculators is outside this aggregate-only packet. The calibration pairing portion of V05 is repaired here; the shared upstream scoring calculator and record-by-record historical reconciliation remain separate work.

No database schema, persisted records, public page, deployment, or production behavior was exercised. Local checks establish the aggregate calculation contract only; they do not provide release evidence or repair previously published statistics.
