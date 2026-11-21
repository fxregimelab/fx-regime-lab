# Leaf 3.2 — Honest public performance presentation

## Outcome

The public track record now computes live and historical replay metrics from one exact set of matching `validation_log` evaluation records. Live selection is fixed to strategy `v2`, model `2.0-live`, evaluation `published-direction-v1`, and source `live`. Historical replay selection uses the requested model version and source `backtest`; an empty version catalog stays unavailable rather than inventing a fallback.

This source does not contain published calls that lack any evaluation row. Public totals are therefore labeled as evaluation records, and coverage is labeled as the scored share of evaluation records. Full publication coverage remains unavailable until publication records are reconciled against the validation ledger; no missing calls are fabricated here.

The page no longer presents cumulative overlapping call returns as an equity curve or derives drawdown, Sharpe, Sortino, or total P&L from those calls. Legacy sizing simulations are described as quarantined exploratory output pending reconciliation, with their unsupported metrics hidden.

## Metric contract

- T+5 and T+20 outcomes require an exact pair match, a parseable call date no later than the stated UTC as-of date, weekday maturity, a published `BULLISH` or `BEARISH` direction, a boolean-derived `CORRECT` or `WRONG` outcome, and a finite raw market return.
- Published `NEUTRAL` is an abstention. A mature directional deadband move remains `WRONG` as supplied by the canonical outcome mapper.
- Brier scores use only eligible directional observations with a finite value in `[0, 1]`.
- Gross mean signed payoff mirrors bearish raw returns and never falls back to the net-return field.
- Net win rate has its own denominator and requires an explicit boolean net outcome, finite net payoff, and finite non-negative cost.
- Total evaluation records, mature records, pending maturity, directional records, net records, Brier records, mature abstentions, mature missing outcomes, unknown directions, and the scored share of evaluation records are shown separately.
- The calculator rejects mixed source/version/evaluation/window metadata instead of labeling a mixed cohort from its first row. Missing metadata is normalized to `unknown` for this check.
- Impossible calendar dates do not mature, and an invalid supplied as-of date fails closed rather than falling back to today.
- `sharpeLike` is always unavailable. Rolling 90-day accuracy is anchored to the requested as-of date, not the last stored row.

## Verification

- `cd web && node --experimental-strip-types --test tests/track-record.test.ts` — PASS, 9 tests, 0 failures.
- `cd web && npx biome check src/lib/track-record.ts src/app/track-record/page.tsx src/app/track-record/components/BacktestTabClient.tsx src/app/api/backtest/route.ts src/components/performance/PairBreakdownTable.tsx src/components/performance/PairAccuracyCards.tsx tests/track-record.test.ts` — PASS.
- `git diff --check` on all leaf-owned source and test files — PASS.
- `cd web && npx tsc --noEmit` — PASS after the parent query interface landed.
- Structural scan confirms a single `computeStatsFromLog` implementation in `web/src/lib/track-record.ts`; both the page and backtest route import it. Live and backtest calls use `limit=null`, and backtest passes the requested model version as the fourth argument.

## GitNexus limit

Pre-edit symbol impact, `/api/backtest` API impact, and post-edit change detection were attempted. All failed because the rebuilt index uses LadybugDB storage version 42 while the running GitNexus MCP supports storage version 40. Risk therefore remains `UNKNOWN`; it was not treated as low. Direct `rg` inspection found the calculator consumers only in the track-record page and backtest route, and the route consumer only in `BacktestTabClient`.

No Docker or Hermes runtime was required or started. No browser, deployment, or production acceptance is claimed.
