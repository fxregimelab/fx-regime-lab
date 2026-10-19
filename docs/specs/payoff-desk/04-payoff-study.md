# PD controlled payoff study — exact research contract

Status: proposed offline experiment. No broker connection or model call needed
for the first slice. Register the experiment before looking at new test results.

## Keep entry and management attribution separate

First freeze a single set of causal entry opportunities and their initial stops.
Apply each management challenger to the SAME opportunities without changing
entries to favour its exit. This paired study estimates management effects,
not feasible portfolio returns. In a second study apply each policy's actual
holding/cooldown/capacity effects; opportunity sets may then differ and must be
reported. Never claim a per-trade paired result is a deployable equity curve.

Initial four research policies:

1. M0: full position, original stop, terminal target chosen for planned net >=3R.
2. M1: half at +1R, runner original stop; runner target supports net >=3R total.
3. M2: half at +1R, after confirmed partial fill runner stop at entry plus the
   registered cost buffer (mirrored for shorts); same target. Bind the buffer
   in pips, price and price-R, plus lot/stop rounding, before replay.
4. M3: M2 plus the EXISTING playbook's exact structural/ATR trailing rule.

Before M3 runs, bind ATR period/timeframe, closed-bar timing, structural
confirmation delay, stop rounding, update frequency and broker constraints.
If any is unresolved, M3 is BLOCKED, not approximated by a convenient trail.
M1 and M0 are counterfactuals; they do not replace the current management policy.
Do not add 20 variants after seeing which of these wins.
Common early/time/news/session/Friday/horizon rules must also be identical and
exactly bound across policies, so treatment differences are attributable. Their
current structural-replay mismatches block the full-management study. M2 minus
M1 measures buffered protection; M3 minus M2 measures the incremental trail.

## Event ordering and accounting

- Use completed decision bars; entry on a subsequent executable quote/open with
  correct bid/ask side and spread model. Freeze stop distance and initial cash R.
- Lot fractions must be rounded to instrument step/minimum. Partial impossible
  at minimum size => ineligible for that policy, not simulated as fractional lots.
- Stop active before target on ambiguous OHLC bars. Gaps through stops fill at
  adverse open; favourable limit gaps capped at target. Model spread/commission,
  slippage and swap consistently; negative prices/cost units are invalid.
- If partial and stop amendment order cannot be resolved, use lower-timeframe
  evidence or adverse ordering and flag ambiguity. Never retroactively protect
  a runner during the same candle merely because its high touched +1R.
- An unacknowledged stop amendment leaves the previous stop active. Duplicate
  partial receipts cannot halve the position twice. Partial fill quantities,
  failed modifications, financing, Friday gaps and forced horizon exits matter.
- Record original-risk price, cash and currency conversion. Every exit reconciles
  quantity and cash to the parent. No denominator reset at entry-stop movement.
- Keep all losses/scratches. Report excluded/ineligible/censored opportunities
  with reasons. An unresolved final trade is not a settled win or dropped loss.

## Mandatory hand-oracle cases

With initial price-risk 100 cash units, no reserve/costs unless stated, exactly divisible lots:

1. Original stop before +1R => -1R for each policy (subject to its entry).
2. Half +1R then runner -1R => 0R gross for M1.
3. Half +1R then runner 0R => +0.5R gross as a zero-buffer arithmetic oracle,
   not the actual buffered M2. With runner buffer d price-R, gross is .5+.5d.
4. Half +1R then runner +3R => +2R gross, NOT +3R.
5. Half +1R then runner +5R => +3R gross, not automatically +3R net.
6. Total cost 0.1R: previous case +2.9R net; runner +5.2R gives +3R net.
7. Partial/stop collision => adverse admissible path and ambiguity flag.
8. Gap -1.5R => loss below -1R; no clamp to nominal risk.
9. Duplicate partial/stop receipts => unchanged settled parent after replay.
10. Tiny lot, missing tick value, nonfinite price and future bar => explicit reject.
11. Changing future bars leaves earlier features/decisions unchanged.
12. Costs and quantities reconcile leg-by-leg with no double charging.
13. G=100, A=10, scenario cost=10: half at 1 price-R and runner at 5.8
    price-R yields 330 net cash / 110 initial all-in risk = 3 parent-R.
    Runner at 5.2 gives 3 price-R but only 2.72727 parent-R; admission fails.

These are acceptance cases for FUTURE implementation. Package tests checking
documentation/agent installation are not proof of this simulator's correctness.

## Structural measurement prerequisites

The older `backtest/engine.py` requires separate repairs before its portfolio
results are reused: event-time cash/stop settlement; adverse-open gap fills;
horizon-local exits using broker trading sessions; joint-pair equity/exposure;
and parity with the exact management contract. A future trade's final P&L may
not fund an earlier opportunity. A separate study must adjudicate the calendar
lookback/blackout mismatch before admission integration. See the audit and
PD-00 packets. Do not silently regenerate or replace historical report numbers.

## Statistical protocol

All 2022–2026 price data already examined by the dense study are development
data for new designs. Do not relabel the former 2025–2026 holdout as untouched.
Use nested chronological/purged development evaluations and a newly registered
forward endpoint for final evidence. Purge overlapping label horizons and account
for simultaneous/correlated EURUSD/USDJPY trades. Register all tried strategies,
prompts, policies, pair filters and failures, not just the chosen configuration.

Measure paired net-R deltas and uncertainty using predeclared time blocks,
portfolio equity/drawdown under actual sizing, tails/streaks, ambiguity sensitivity,
cost stress and no-trade periods. Do not treat overlapping labels or agent
opinions as independent observations. No repeated peeking until p<0.05.
Choose endpoint/sample plan before results; preserve existing graduation gates.
PBO/deflated metrics are useful diagnostics where their assumptions hold, not a
substitute for fresh evidence. No statistical threshold is changed in this pack.
The eventual registration must name M1-M0, M2-M1 and M3-M2 paired comparisons,
primary net-parent-R endpoint, multiplicity treatment, time-block construction,
sample/stopping plan and fresh forward dates. Use a declared common eligible-lot
cohort for the paired study and report all policy-specific exclusions. Those
bindings are not supplied by this design: until registered, no statistical PASS.

Report per pair/setup/regime and aggregate: count/span, net expectancy, realised
average win/loss, scratch fraction, profit factor, full-target rate, 1R-first rate,
conditional runner success, MAE/MFE, time held, costs, drawdown and confidence
intervals. A planned 3R payoff alone is not PASS. A small sample is COLLECTING.

## Incremental macro/AI value

After management is fixed, compare identical timestamped opportunities under:
price-only baseline; deterministic macro context; one evidence-grounded analyst;
analyst plus independent challenge. Keep data, risk, opportunity/cost definitions
and budgets matched. Include unsupported-claim rate, calibrated outcomes,
latency, abstentions and cost per accepted decision. More narrative detail is
not improvement. An agent layer that adds no measured value is removable.
