# Historical simulation rate parity

This leaf removes unsupported rate features from both historical simulation versions. It does not repair the historical source records themselves.

## What changed

- `simulate_all_days` and `simulate_all_days_v2` now use the shared economic definitions in `rate_inputs.py`.
- The configured rate sources do not provide compatible matched two-year government yields for any of the three supported pairs. Historical `rate_diff_2y` therefore stays null.
- The stored ten-year yields remain descriptive context. Their orientation is EUR minus USD for EUR/USD, USD minus JPY for USD/JPY, and USD minus INR for USD/INR.
- A real-yield spread needs compatible inflation inputs for both currencies. Only the U.S. breakeven leg is present, so `rate_diff_10y_real` stays null.
- Both simulations leave the tactical, structural, and blended rate Z-scores null. Stored nominal ten-year history is no longer used as forecast history.
- The Layer 1 classifier receives no synthetic carry series and receives a null two-year rate differential.
- Each in-memory signal row records `rate_inputs_unqualified` and `rate_history_unavailable` in its data-quality notes.
- Historical snapshots expose the source identifiers and the same currency aliases used by the shared definitions: `us_2y`, `us_10y`, and one of `de_10y`, `jp_10y`, or `in_10y`. The ambiguous `quote_10y` alias was removed.

All other simulation families and call assembly remain in their existing paths.

## Evidence

GitNexus impact checks were run before editing:

- `simulate_all_days`: LOW risk, two direct callers, two affected processes, two affected modules.
- `_build_historical_snapshot`: LOW risk, two direct callers, two affected processes, two affected modules.
- `simulate_all_days_v2`: LOW risk, two direct callers, two affected processes, two affected modules.

The focused integration test supplies 75 mocked spot bars and complete nominal yield histories for each supported pair, then calls both real simulation functions. Each version returns 15 post-warm-up calls per pair. The test checks every generated `SignalRow` and `RegimeCall`, and spies on every Layer 1 classifier call. It proves:

- null two-year, real-yield, tactical Z, structural Z, and blended Z fields;
- the pair-correct nominal ten-year orientation;
- a neutral rate signal;
- an empty carry history reaching the classifier;
- explicit unavailable-input and unavailable-history quality notes;
- consistent source and currency aliases in the reconstructed snapshot.

Commands run from `pipeline`:

```text
node ../scripts/repair/verify-pytest.mjs tests/test_simulation_rate_contract.py
3 passed
REPAIR_PYTEST_VERIFIED

python -m pytest tests/test_simulation_engine.py -q
3 passed

python -m ruff check src/backfill/simulation_engine.py tests/test_simulation_rate_contract.py
All checks passed!

python -m mypy src/backfill/simulation_engine.py tests/test_simulation_rate_contract.py
Success: no issues found in 2 source files
```

The repository-wide GitNexus change scan saw the larger shared repair checkout: 41 changed files, 232 symbols, 54 affected processes, CRITICAL aggregate risk. That result includes work owned by other repair leaves. This leaf's three pre-edit symbol checks were LOW risk, and its file diff is limited to the assigned simulation engine, focused test, and this report.

## Remaining limits

Historical fetch vintage and observed-date provenance are not repaired here. This work does not establish research skill or forecasting profit. Any model-version change remains release-blocked until the parent repair completes its full regression, research, migration, and release checks. No database, network, runtime, deployment, or commit action was performed.
