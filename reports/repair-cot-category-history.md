# COT category-history repair

Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`, with concurrent uncommitted repair work preserved.

## Result

`compute_cot_smart_spread_percentile` now uses only Asset Manager net minus Leveraged Money net. It no longer substitutes `net_long` when either category is absent.

The latest eligible report date remains the current observation. If that report lacks either category, the function returns `None` instead of moving back to an older complete report. Historical reports with incomplete category data are excluded from the reference distribution, and `min_reports` counts only complete, distinct historical reports inside the declared `window_reports` dates.

Duplicate observations for a report date are accepted only when both category fields agree. A conflicting duplicate anywhere in the active report window makes the result unavailable, so input arrival order cannot select the percentile. Equal duplicates do not change the result.

The ordinary `compute_cot_percentile` path and `normalize_cot_signal` were not changed.

## Impact

The required upstream GitNexus check classified `compute_cot_smart_spread_percentile` as **CRITICAL**: 39 impacted symbols, 34 direct dependents, seven affected processes and five affected modules. The direct behavior change is deliberate: scheduler, backfill and diagnostic consumers can now receive `None` where incomplete or conflicting category data previously produced a number from `net_long` or row order.

The regression-test helpers and test cases are new symbols. The current GitNexus index does not contain them; a lookup for `_row` returned `UNKNOWN` with zero indexed dependents. The index was not rebuilt, as required by the packet.

`gitnexus detect-changes --scope all` completed before handoff. Because this is a shared dirty checkout, it reported the combined repair branch rather than an isolated packet diff: 78 files, 513 symbols, 293 affected processes, overall critical risk. The three packet-owned paths are listed below and were checked separately with Git diff.

## Verification

- `node ../scripts/repair/verify-pytest.mjs tests/test_cot_category_history.py`: **12 passed**, `REPAIR_PYTEST_VERIFIED`.
- `python -m ruff check src/signals/cot.py tests/test_cot_category_history.py`: **passed**.
- Combined COT check: **31 passed, 1 failed**. The failure is the pre-existing `tests/test_cot_signal.py::TestComputeCotSmartSpreadPercentile::test_falls_back_to_net_long_when_breakdown_missing`, which asserts the fallback this repair contract forbids. That file is outside packet 18.2 ownership and needs parent coordination.
- Full `python -m mypy .`: **1 out-of-scope error** at `src/backfill/simulation_engine.py:492`, where concurrent work references `CotRow` without defining or importing it. The 200-file check otherwise completed.

The new tests cover mixed complete and incomplete history, all categories missing, each latest-category missing shape, the `as_of` cutoff, conflicting current and historical duplicates, duplicate arrival-order invariance, equal duplicates, the complete-history minimum, an empty reference distribution, and the report-window boundary.

## Remaining evidence

Parent integration still needs to reconcile the obsolete fallback test and the concurrent MyPy error, then run the wider pipeline gate. Release timestamps, holiday handling and complete year-boundary source history remain outside this repair, as stated in the directional input contract.

No provider, network data source, credential, database, AI, notification, long-running runtime, commit or deployment was used.
