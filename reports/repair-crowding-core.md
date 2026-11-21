# Crowding core repair

27 September 2026. This leaf implements the frozen crowding-description contract in the calculation and systemic-analysis modules. It does not change forecasts, stored calls, validation rows, providers, databases, AI services, public readers, or release state.

## Delivered behavior

`compute_crowding_diagnostic` returns the exact `crowding-description-v1` shape. It accepts only the locked pairs, accepts the slash aliases, validates the actual frozen direction and optional positive call ID, and keeps COT and price availability independent.

For EUR/USD and USD/JPY, the COT component selects the latest distinct report at or before the cutoff. Future and other-pair rows cannot move the anchor. Exact duplicates collapse; same-date conflicts make the current component unavailable without falling back to an older report. Contract counts require a Python `int`, reject booleans, floats, strings and values outside JavaScript's safe-integer range, and preserve zero. Type-sensitive duplicate checks prevent `1`, `True`, and `1.0` from collapsing as the same report. Asset-manager and leveraged-money values remain separate and independently nullable. Positive JPY futures net has negative USD/JPY orientation. Alignment uses `predicted_direction`; it is never reconstructed from a regime label or percentile. USD/INR positioning is unsupported.

Every available COT description remains `PROVISIONAL`, with `series_definition=UNKNOWN`, `release_status=UNVERIFIED`, and `rank_percentile=null`. The row type has no category identity, release timestamp, source vintage, or historical receipt evidence.

The price component calls `select_spot_history`, so cutoff, ordering, de-duplication, pair checks, and conflicting rows use the repository's shared validator. It preserves the latest eligible close with fewer than 40 observations. Exactly 40 observations produce `sum(close_i / 40)` and the signed percentage difference from that arithmetic mean. Invalid history or non-finite arithmetic makes only the price component unavailable. No volume, carry, volatility, cost basis, pain, loss, or squeeze estimate enters the calculation.

`compute_pain_index` now raises a clear `RuntimeError` directing callers to the new API. The unsupported regime-substring direction, close-mean-as-VWAP, carry reconstruction, volatility gate, and 0-100 pain equations were removed. `compute_apex_score` always returns `None`; `assign_apex_ranking` always returns an empty list. The old velocity and hysteresis equations were removed, while the unrelated correlation helpers remain unchanged.

## Verification

- Frozen leaf check: `node ../scripts/repair/verify-pytest.mjs tests/test_crowding_diagnostic.py tests/test_systemic.py` — 21 passed; emitted `REPAIR_PYTEST_VERIFIED`.
- Scoped Ruff: `ruff check src/analysis/asymmetry.py src/analysis/systemic.py tests/test_crowding_diagnostic.py tests/test_systemic.py` — passed.
- Scoped MyPy: `mypy src/analysis/asymmetry.py src/analysis/systemic.py tests/test_crowding_diagnostic.py tests/test_systemic.py` — passed with no issues.
- Diff whitespace check for the four Python files — passed.

The tests include hand-computed EUR/JPY orientation, negative and zero net, neutral and missing calls, absent and malformed categories, future and other-pair rows, ordering, exact duplicates, type-conflicting duplicates in both input orders, conflicting latest COT, safe-integer overflow, unsupported INR, 39 versus 40 price observations, a 20-at-90 plus 20-at-110 mean/deviation example, future price fencing, price conflict isolation, arithmetic underflow, input non-mutation, invalid configuration, retired pain, and Apex invariance.

## Source hashes

SHA-256 after verification:

- `pipeline/src/analysis/asymmetry.py`: `9B0CA928C8B5223F3A435E341F58059096589618777103228FA4908231137E4A`
- `pipeline/src/analysis/systemic.py`: `88F127777CCA0D470EB11A3A8B4A068E96F25852B4A0EAD8A69CDBE0C5114A87`
- `pipeline/tests/test_crowding_diagnostic.py`: `FD85AB51C368F4A4C24DA16CAB8F5B6CCCFA76C20F88E342FAB8D4CA63BF00AA`
- `pipeline/tests/test_systemic.py`: `CD8A5B1C6307986D38C6B41AD4080C234BEC8EE56717DD37A4BBD588D43F7EB2`

## Impact and remaining boundary

Required pre-edit GitNexus calls reported `CRITICAL` for the deleted private pain helpers, `compute_pain_index`, the retired Apex functions, and even test functions. The reported direct dependants included unrelated UI, fetcher, and staged symbols, matching the known contaminated generic graph. Direct repository search found the private pain helpers only inside `compute_pain_index`, one production pain caller in `scheduler/orchestrator.py`, and the ranking callers in that scheduler. The integration leaf owns those consumer changes. New symbols correctly returned `UNKNOWN` because the stale index does not contain them. The final CLI `detect-changes` command exited 1 without a change map and printed only a shared-worktree line-ending warning; no index rebuild was attempted, as required.

This output remains a report-date-only provisional description. The source gap is unchanged: `CotRow` cannot prove category consistency, actual release time, source vintage, or what was available when a frozen call was published. No participant loss, cost basis, squeeze probability, or cross-pair investment ranking is claimed. Full pipeline and consumer integration checks remain with the parent leaf; Docker and the heavier Hermes runtime were not needed for these pure unit checks.
