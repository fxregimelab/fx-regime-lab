# Brief — RF2b: recon rate-carry definition parity (post-RF2, post-LRH)

**Status:** queued (spawn with inline copy of this brief)
**Kind:** implementer
**Files:** `pipeline/src/backfill/simulation_engine.py` + `pipeline/tests/test_simulation_engine.py`.

## Defect

Recon signals still build the rate inputs differently from live:

- sim stores `rate_diff_2y` = raw `DGS2` level (`base_yield`) for every pair, not the pair spread;
- the quantity the sim feeds into `normalize_rate_signal` is not the same as the live
  risk-adjusted carry (trace the current live wiring — post-LRH commit: `_rate_spread_2y_for_pair`,
  `compute_risk_adjusted_carry_v2`, and the orchestrator z call sites — and mirror it exactly).

Consequence: recon signals cannot be compared to live behavior 1:1; deep-backtests measure a
different decision logic than production runs.

## Required behavior

1. For each replay day and pair, compute the pair 2Y spread with the live definition:
   `DGS2 − quote` where quote ∈ {ECBDFR (EUR), IRLTLT01JPM156N (JPY), INDIRLTLT01STM (INR)},
   causally forward-filled from `historical_yields` (monthly legs FF to the daily grid, last
   observation ≤ as_of ONLY — no future leakage).
2. Feed `normalize_rate_signal` the same risk-adjusted handling live uses (confirm from the
   post-LRH live wiring and mirror exactly; if live uses spread/vol, do the same).
3. EUR until ECBDFR history exists: fall back to the legacy definition for EUR only, with a
   logged warning (deterministic, never crash).
4. Keep the stored `rate_diff_2y` in signals consistent with what was actually used.
5. Tests: synthetic `historical_yields` fixture incl. monthly series; assert per-day spread ==
   live-definition spread (causal FF, no future leak); assert the EUR fallback path; assert
   z-input parity against a live-computed reference value.

## Constraints

No DB writes; do not edit other agents' files; no commits/push/checkout/stash. If full-suite
failures appear only in files you did not touch, re-run once.

## Verify (from `pipeline\`)

Focused `-m pytest tests/test_simulation_engine.py -q` + full `-m pytest -q` (baseline 749);
`-m ruff check .`; `-m mypy .`.

## Report

Per-item resolution, test names, exact commands + results, residual risks, manual callers list
(GitNexus unavailable → risk UNKNOWN).
