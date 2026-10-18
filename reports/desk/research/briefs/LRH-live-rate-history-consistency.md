# Brief — LRH: live rate-history consistency fix

**Status:** queued (dispatch when an editing slot frees; run after RF2)
**Kind:** implementer
**Files:** `pipeline/src/scheduler/orchestrator.py`, `pipeline/src/signals/rate.py`,
`pipeline/src/backfill/fred_historical.py` (config only), new
`pipeline/tests/test_rate_history_consistency.py`.

## Root cause (verified read-only 2026-10-18)

The live MAD-z of risk-adjusted carry compares **today's pair spread** against a **2520-day history
of a different quantity**:

- Today: `_rate_spread_2y_for_pair(pair, universe, yields_dict)` = `yields_dict[universe.yield_base]`
  − `yields_dict[universe.yield_quote]` (EUR: `DGS2 − ECBDFR`; JPY: `DGS2 − IRLTLT01JPM156N`;
  INR: `DGS2 − INDIRLTLT01STM`).
- History: `build_carry_history_from_rows(historical_rows)` where
  `historical_rows = writer.get_historical_signals(pair, limit=2520)` and recon era stored
  `rate_diff_2y` = **raw US 2Y yield** (DGS2 level) for every pair
  (`simulation_engine.py`: `rate_spread_2y = base_yield`).

Evidence: live-window last-2520 medians coincide (2.49) for all pairs because recon dominates;
live USDJPY `z_tactical` pins at `−1.0` → `rate_signal=BEARISH` 107/115; USDINR 73/113;
EURUSD scales accidentally coincide (US2Y ≈ US−DE) → mixed.

## Required behavior

Build both z-histories in the **same definition as the current-day inputs**, from canonical sources:

1. New pure helpers in `signals/rate.py` (names up to you), e.g.
   `build_rate_spread_histories_from_yields(yields_by_series, pair, date_grid, *, beis_series, ...)`
   returning `(carry_history, real_yield_10y_history)`:
   - Carry leg: daily pair spread = `DGS2(d) − quote(d)` where `quote(d)` is the last observation
     of `ECBDFR` / `IRLTLT01JPM156N` / `INDIRLTLT01STM` with date ≤ `d` (forward-fill, **causal only**).
     Then `carry(d) = spread(d) / realized_vol_20d(d)` using the vol values from the existing
     `historical_signals` rows keyed by date (skip dates with missing vol).
   - Structural leg: `(DGS10(d) − quote10y(d)) − T10YIE(d)` where `quote10y` ∈
     {`IRLTLT01DEM156N`, `IRLTLT01JPM156N`, `INDIRLTLT01STM`}, all from `historical_yields`,
     forward-fill causal.
   - Both trimmed to `CARRY_LOOKBACK_DAYS` most recent points, oldest-first — matching the current
     helpers' contracts.
2. `orchestrator.py`: replace the calls that build histories from `historical_rows`
   (`build_carry_history_from_rows`, `build_real_yield_10y_spread_history_from_rows` at the live
   call sites) with the new helpers fed by `historical_yields` (loaded once per run; the loader
   may be a small read-only function using the existing yield history accessor — do not add new
   DB tables). Do NOT change `normalize_rate_signal` math, weights, thresholds, or the composite.
3. `fred_historical.py`: add `"ECBDFR": {"description": "ECB Deposit Facility Rate", "start": "1999-01-01"}`
   to `SERIES_CONFIG` (config only — the coordinator runs the backfill; ECBDFR is required for EUR).
4. Graceful degradation: if a required series or vol history is missing for a pair, log a warning
   and fall back to the existing behavior for that pair only (never crash the daily run).

## Tests (no network, no DB)

- Parity: given synthetic `yields_by_series` + vols, the **last** value of the generated carry
  history equals `risk_adjusted_carry` computed from the same-day spread (same definition).
- Causality: a value dated after `d` never influences the history at `d` (add a spike after `d`,
  assert unchanged).
- Forward-fill: monthly quote legs resolve to the last observation ≤ date; no future leakage.
- Degradation path: missing quote series → fallback + warning.
- Orchestrator wiring: assert the new helpers are used at the live call sites (monkeypatch).

## Constraints

- No DB writes from this task; the implementer does NOT run the FRED backfill.
- Do not touch `simulation_engine.py` or other agents' files.
- Semantic change requires a clear report: which signal outputs change and why
  (z_tactical/z_structural values forward from the fix).
- No git commits/push/checkout/stash. GitNexus broken → manual callers list for
  `build_carry_history_from_rows`, `build_real_yield_10y_spread_history_from_rows`,
  `_rate_spread_2y_for_pair`, `normalize_rate_signal`.

## Verify (from `pipeline\`)

Focused `-m pytest tests/test_rate_history_consistency.py -q`; full `-m pytest -q`;
`-m ruff check .`; `-m mypy .`.
