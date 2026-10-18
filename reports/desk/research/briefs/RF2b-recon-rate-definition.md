# Brief — RF2b: recon rate-carry definition parity (parked until RF2 lands)

**Status:** parked — refine after the RF2 implementer report (its line refs will shift).
**Kind:** implementer
**Files:** `pipeline/src/backfill/simulation_engine.py` + `pipeline/tests/test_simulation_engine.py`.

## Defect

Recon `rate_diff_2y` is **not the live quantity**:

- Sim (`simulation_engine.py`): `rate_spread_2y = base_yield` (raw `DGS2` level) for every pair;
  the z input is built from `rate_spread_10y` (US10Y − quote10Y) — neither matches live.
- Live: `_rate_spread_2y_for_pair` = `DGS2 − universe.yield_quote` (EUR `ECBDFR`, JPY
  `IRLTLT01JPM156N`, INR `INDIRLTLT01STM`) and the z input is that spread / vol.

Consequence: live z-score history mixes definitions (recon rows dominate) → `z_tactical` pinned
`−1.0`, `rate_signal=BEARISH` 107/115 (JPY) and 73/113 (INR).

(Note: the LRH brief removes the live-path dependency on recon rows, so RF2b is a **fidelity**
fix for future recon runs/backtests, not a blocker for LRH.)

## Required behavior (draft — confirm against RF2 code)

1. Compute the recon pair spread with the same definition as live wherever history exists:
   - `DGS2 − IRLTLT01JPM156N` (JPY), `DGS2 − INDIRLTLT01STM` (INR): both in `historical_yields`
     (monthly → causal forward-fill to daily grid).
   - EUR: `DGS2 − ECBDFR` — requires the ECBDFR history (added by the LRH config change, backfilled
     by the coordinator). Until it exists, fall back to the legacy definition **with a logged
     warning** and record which definition produced each row (e.g. keep using current behavior).
2. Rebuild the z input to match live: `risk-adjusted carry = spread / realized_vol_20d`
   (not the 10Y spread). Keep vol computation unchanged.
3. Keep `rate_diff_2y` written to `signals` consistent with the recomputation; keep
   `rate_diff_10y`/structural inputs as live defines them where history allows.
4. Tests: synthetic `historical_yields` fixture; assert the sim's spread for a given date equals
   the live-definition spread (forward-filled, causal, no future leak); assert fallback path when
   ECBDFR is absent.

## Out of scope

- No DB writes / no re-run of the recon (that is a gated operational step in the coordinator's
  plan: RF1 safety + ledger snapshot + explicit report first).
