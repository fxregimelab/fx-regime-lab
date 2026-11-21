# Cohort aggregation repair

Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`

## Result

Validation snapshots now keep `data_source`, `strategy_version`, `model_version`, `evaluation_version` and `window_days` as part of one evidence group. Pair statistics are computed inside that group. `ALL` combines pairs only when they share the complete group.

Missing source, strategy or model metadata is stored as `unknown`. Missing evaluation metadata is stored as `legacy-unversioned`. No missing value is relabeled as live, `v2` or `2.0-live`.

The stored horizon fields now include the distinct directional, complete net-payoff, maturity, pending, abstention, unknown-direction, missing-outcome, probability-score and calibration counts. A row enters the net cohort only when its net correctness is boolean, its net payoff is finite and its cost is finite and nonnegative. Average cost uses that same cohort. The explicit `mean_signed_gross_return_bps` field is the mean market return signed by the published direction. Sharpe-like and drawdown fields are not written because overlapping call outcomes do not define a portfolio.

Positive lookback windows use calendar days, include the as-of date and start at `as_of_date - (window_days - 1)`. `window_days=0` means all available history through the as-of date.

## Checks

- `node ../scripts/repair/verify-pytest.mjs tests/test_validation_aggregate.py tests/test_validation_cohorts.py` — 15 passed; `REPAIR_PYTEST_VERIFIED`
- `ruff check src/validation/aggregate.py tests/test_validation_aggregate.py tests/test_validation_cohorts.py` — passed
- `mypy src/validation/aggregate.py tests/test_validation_aggregate.py tests/test_validation_cohorts.py` — passed with no issues
- `git diff --check` for the four leaf-owned paths — passed

The regressions cover mixed live/replay sources, model versions, old/new evaluation versions, missing metadata, within-group `ALL`, separate horizon denominators, incomplete net payoff/cost rows, pending and unknown directions, and an as-of date that differs from the machine date.

## Impact and limits

The matching GitNexus CLI rated `_compute_horizon` HIGH risk: four direct callers, 15 affected symbols and the scheduled `run_pipeline` flow. The focused regression suite passed after the change. Other edited aggregation symbols were rated LOW. The MCP process could not read the rebuilt index because its storage reader was older; the CLI used the matching index format.

Repository-wide `gitnexus detect-changes` reported CRITICAL risk across 29 files and 154 symbols in the shared repair checkout. That result includes other repair leaves and is not a leaf-only risk rating.

These are local code and fixture checks. They do not prove the migration on a real database, deployed query behavior, historical record reconciliation, audited source vintages, release health or future/live research performance. The production reader intentionally selects the current canonical evaluation; mixed-evaluation isolation is a defensive contract verified with supplied rows.
