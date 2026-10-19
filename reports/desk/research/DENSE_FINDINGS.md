# Dense-trading research findings (2026-10-19)

**Historical simulation — not live results.** Every number comes from completed
bars with entry at the next bar's open, stop-before-target on ambiguous bars,
stop gaps filled at the open, target gaps capped at the target, and canonical
costs subtracted from every label.

This revision follows an independent adversarial review. The review found and
this revision fixes: a dead-context-feature bug, a cross-fold label leak, rate
denominators that included training bars, an unconditional benchmark that mixed
training and test rows, a one-bar-late entry timestamp, a backwards upper-wick
sign, and tests that restated the implementation instead of pinning the
contract.
All numbers below are post-fix and were regenerated from one data snapshot
(fingerprints in each report JSON).

## The question

The owner asked for **10–15 settled trades per week** so selection can be
optimised on a statistically usable sample. The structural-setup path produced
**39 trades in four years (~0.19/week)**, which cannot support optimisation.

Two questions had to be separated:

1. **Can the desk generate the frequency?** (mechanical)
2. **Is there an edge that survives out of sample at that frequency?** (economic)

The answer to (1) is yes. The answer to (2), on all data and features currently
available, is **no**.

## Protocol

- Expanding-window walk-forward; no shuffling; fixed hyper-parameters within a
  run; training strictly before each test window.
- **Label purge:** a training label is used only if its simulated exit resolves
  before the test window starts. Without this, near-boundary labels leak test
  prices into training.
- **Entry** at the next bar's open. **Stop gaps** fill at the open; **target
  gaps** are capped at the target. A bar spanning both books the stop.
- **Costs:** canonical round-trip + slippage from `src/paper/config.py`.
- **Features:** 30 causal features. The long view keeps every column; the short
  view mirrors only the directional columns, so context (session, volatility,
  clock) is never zeroed.
- **Denominators:** trades/week use the out-of-sample span only.
- **Benchmarks:** `unconditional` averages every valid bar; `matched` averages
  both sides at the bars the model actually selected, removing bar-composition
  effects. `edge vs matched` is the honest selection edge.
- **Uncertainty:** an iid trade t-test and a weekly t-test (missing weeks = 0).
  Both treat observations as independent; overlapping labels and the
  one-position constraint make them optimistic. Neither is a block bootstrap.

## Result 1 — the a-priori baseline has no EURUSD edge

`dense.json`, M15, default geometry (`stop 1.5 / target 2.0 / hold 32`,
`signal_rate 0.02`, `min_edge 0.02`, one position per pair):

| Pair | Trades | Per week | Expectancy | Net R | t (iid) | p | Matched R | Edge vs matched |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 147 | 0.95 | −0.105R | −15.44 | −1.06 | 0.29 | −0.128 | +0.023 |
| USDJPY | 448 | 2.89 | +0.067R | +30.01 | 1.03 | 0.31 | −0.111 | +0.178 |

The model selects bars whose both-side average is still negative (−0.128 /
−0.111) but materially better than the all-bar average (−0.254 / −0.213), so it
is avoiding bad bars. On EURUSD, picking the better side adds only +0.023R,
leaving −0.105R after costs. On USDJPY it adds +0.178R, enough to turn positive,
but not statistically distinguishable from zero.

## Result 2 — the best full-period cells are positive, but they are in-sample maxima

The M15 geometry sweep (27 configurations) selected
`stop 1.5 / target 1.5 / hold 32` as the best cell:

| Pair | Trades | Per week | Expectancy | Net R | t (iid) |
|---|---:|---:|---:|---:|---:|
| EURUSD | 189 | 1.22 | +0.001R | +0.09 | 0.01 |
| USDJPY | 553 | 3.56 | +0.030R | +16.73 | 0.60 |

The neighbouring cells are also positive (`1.5/1.5/64 +0.047R/wk`,
`1.5/1.5/96 +0.095R/wk`, `1.5/1.0/32 +0.059R/wk`), which is why this region
looked more credible than the isolated H1 winner. But the geometry was chosen
after seeing all 27 cells; it is a post-hoc maximum, not an a-priori rule.

The H1 sweep selected `stop 2.5 / target 2.0 / hold 48`:

| Pair | Trades | Per week | Expectancy | Net R |
|---|---:|---:|---:|---:|
| EURUSD | 246 | 1.24 | −0.026R | −6.36 |
| USDJPY | 430 | 2.17 | +0.105R | +45.23 |

Its immediate neighbours are negative (`2.5/2.0/24 −0.08R/wk`,
`2.5/1.5/48 −0.03R/wk`). That is the signature of an isolated fit, not a
stable region.

## Result 3 — frequency is achievable, and it dilutes the edge

`frequency_curve_*.json` varies only the calibration quantile, minimum predicted
edge and concurrency on the best M15 geometry (`1.5/1.5/32`). The three
concurrency levels are:

| Config | Concurrency | Trades | Per week | EURUSD R | USDJPY R | Total R | R/week |
|---|---:|---:|---:|---:|---:|---:|---:|
| c1 | 1 | 803 | 5.2 | +0.059 | +0.090 | +66.2 | +0.43 |
| c2 | 2 | 1382 | 8.9 | +0.009 | +0.049 | +53.8 | +0.35 |
| c3 | 3 | 1832 | 11.8 | −0.027 | +0.036 | +36.3 | +0.23 |

(`signal_rate 0.20`, `min_edge 0.02`.)

Three facts matter:

1. **The production limit is `max_positions_per_pair = 2` and
   `max_concurrent_positions = 4`** (`config.py:87-88`). `c3` uses 3 per pair
   (up to 6 open tickets), above the global cap, and at 5%/4%/3% slot risk it
   would exceed the 15% `max_open_risk_pct` budget. Raising only
   `max_positions_per_pair` would not make it admissible. At the
   `1.5/1.5/32` geometry, the maximum within the current limit is approximately
   **8.9 trades/week** (c2).
2. **Frequency is not the binding constraint.** Wider-stop cells at the same
   per-pair limit reach the mandate: the stable `1.5/1.5/96` cell produces
   12.8/week (EURUSD 5.03, USDJPY 7.81) and the selection winner
   `4.0/1.5/64` produces 23.5/week in the holdout. Both are negative or
   non-significant out of sample (Result 4). The 8.9/week figure is a property
   of this geometry, not of the policy.
3. **EURUSD turns negative as frequency rises** at this geometry: +0.059R at
   c1, +0.009R at c2, −0.027R at c3. The total stays positive only because
   USDJPY carries it.

Per-year, c2 (the concurrency-2 cell at the `signal_rate 0.20` calibration):

| Pair | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| EURUSD | +1.93R | −10.18R | −1.29R | +12.69R |
| USDJPY | −11.12R | +18.16R | +16.64R | +26.94R |

(Per-year R values are rounded to 0.01R and may not add exactly to the period
total.)

USDJPY is positive in 2024–2026 and negative in 2023. EURUSD is positive only in
2023 and 2026 and negative in the two middle years. Weekly t-tests (missing
weeks = 0): EURUSD 0.15 (p=0.88), USDJPY 1.16 (p=0.25). Neither is significant.

## Result 4 — the holdout destroys the selected edge

This is the decisive test. Geometry was selected using only the out-of-sample
period **2023-10-27 → 2025-01-01** (the sweep filters
`bar.timestamp < 2025-01-01`), then evaluated out of sample from the first test
window on **2024-12-31T22:15** (no 2024 P&L) through **2026-10-19** with the
same selection parameters (`signal_rate 0.20`, `min_edge 0.02`,
concurrency 2).

The selection-period winner was `stop 4.0 / target 1.5 / hold 64`:
**+87.8R (+1.42R/week) on the selection period**. On the holdout:

| Candidate | EURUSD holdout | USDJPY holdout | Total holdout |
|---|---:|---:|---:|
| Selection winner (`4.0/1.5/64`) | −45.12R (−0.066R) | −21.74R (−0.014R) | **−66.85R** |
| Stable-region (`1.5/1.5/96`) | −31.96R (−0.068R) | +24.62R (+0.034R) | **−7.33R** |
| Full-period winner (`1.5/1.5/32`, in-sample) | −24.13R (−0.051R) | +42.10R (+0.062R) | +17.97R |

The selection winner did not merely decay: it reversed from +87.8R to −66.9R.
The stable-region candidate is also negative in total. The full-period winner is
positive only because it was chosen using the holdout period; it is not
out-of-sample evidence.

Among the two candidates whose geometry was fixed before the holdout, the only
positive component is USDJPY on `1.5/1.5/96`: +24.62R over 730 trades
(7.8/week), +0.034R/trade, positive in both 2025 (+2.04R) and 2026 (+22.56R).
Its weekly t-statistic is **0.64 (p=0.53)**. It is not statistically
distinguishable from zero, and EURUSD's −0.068R on the same period makes the
two-pair total negative.

The selection winner is the only geometry chosen on selection-period data alone.
The stable `1.5/1.5/96` cell is a post-hoc stability pick: on the full-period
sweep the `1.5/1.5/{32,64,96}` family is uniformly positive, and on the
selection-period sweep `1.5/1.5/96` ranks third (+8.6R, +0.139R/week) with only
one immediate neighbour (`1.5/1.5/64`, +0.072R/week) positive. Because the
full-period row includes the holdout, the stable cell is not clean for geometry
either; it is shown as a falsification check, and it is negative in total. The
calibration quantile (0.20) and minimum edge (0.02) were chosen from the
full-period frequency curve, so neither candidate is clean for those two
parameters. The USDJPY cell remains non-significant after that choice.

## Result 4b — acceptance criteria check (amendment)

The amendment's criteria are the contract. The two best candidates do not pass:

| Criterion | c2 (8.9/week, `1.5/1.5/32`) | Holdout stable (12.8/week) |
|---|---:|---:|
| ≥ 8 settled trades/week | 8.9 ✅ | 12.8 ✅ |
| Net expectancy > 0 | +0.039R ✅ | −0.006R ❌ |
| Edge vs unconditional ≥ +0.05R | +0.259 / +0.260 ✅ | +0.164 / +0.256 ✅ |
| Edge vs matched ≥ +0.05R | +0.099 / +0.158 ✅ | +0.026 / +0.226 ❌ (EURUSD) |
| Profit factor ≥ 1.15 | 1.02 / 1.09 ❌ | 0.89 / 1.06 ❌ |
| No fold > 40% of net R | EURUSD 427%, USDJPY 38% ❌ | EURUSD n/a (net < 0), USDJPY 81% ❌ |
| Final-three-fold sign stable | EURUSD +,0,+; USDJPY +,+,+ ❌ | EURUSD −,+,+; USDJPY +,−,+ ❌ |
| Drawdown inside daily/weekly stops | not simulated ⚠️ | not simulated ⚠️ |

`c2` is the concurrency-2 cell at the `1.5/1.5/32` geometry and is itself an
in-sample geometry. The holdout stable cell is a post-hoc stability pick, so it
is not clean for geometry either; only the selection winner (`4.0/1.5/64`,
Result 4) is a selection-period-only geometry, and it loses 66.9R on the
holdout. Both are also conditional on the calibration parameters chosen on the
full period. Both fail the contract. The drawdown row is unverified, not passed:
the R backtest does not apply the equity-based daily −10% / weekly −25% stops or
the 5%/4% slot sizing.

The harness is a fixed-exit signal test. It also does not apply
`max_new_trades_per_day = 5`, `max_same_usd_sign_tickets = 2`,
`cooldown_after_stop_hours = 4`, the 50%-at-1R partial, the trailing stop, the
time stop, the early cut, or slot/equity sizing. The conclusion is about the
signal, not the full desk management policy; a live demo would need a separate
execution study.

### Partial final fold

The last fold is shorter than the nominal test window (8.3 days for the M15
reports, 24–35 days for the H1/holdout reports). Excluding it:

- M15 `1.5/1.5/32`: EURUSD −0.0143R over 187 trades (the full-period +0.0005R
  is carried by the final two trades); USDJPY +0.0279R over 552.
- H1 `2.5/2.0/48`: EURUSD −0.0426R over 240; USDJPY +0.0961R over 423.
- c2: EURUSD −0.0029R over 345; USDJPY +0.0477R over 1033.
- Holdout stable: EURUSD −0.0740R over 470; USDJPY +0.0336R over 728.

The partial fold does not change the sign of the conclusion, but it removes the
one positive EURUSD full-period cell.

### Multiple testing

The geometry sweep tests 27 cells and the frequency/concurrency grid adds more.
The best cells are maxima over that grid, no multiple-testing correction is
applied, and the holdout is the only protection against selection bias. The
holdout rejects the selection winner, which is what a grid maximum looks like
when the underlying edge is noise. The calibration quantile (0.20) and minimum
predicted edge (0.02) were also chosen from the full-period frequency curve, so
neither candidate is clean for those two parameters; the stable cell is not
clean for geometry either (Result 4). The holdout stable cell's USDJPY result is
non-significant (weekly p=0.53) even after those choices.

## Result 5 — the interpretable rules confirm the sign

The one-line rules reach the mandated frequency and lose money. The baselines
use the project's close-time `OHLCBar.timestamp` convention; `london_breakout`
converts to open time for the Asian range, while `mean_reversion` and
`momentum_pullback` filter on the decision bar's close time.

M15 (rules geometry `2.5/1.5/48`, full M15 span 2022-10-27 → 2026-10-19, not the dense `1.5/1.5/32`):

| Rule | Pair | Trades | Per week | Expectancy | Net R |
|---|---|---:|---:|---:|---:|
| London breakout | EURUSD | 1694 | 8.16 | −0.085R | −144.6 |
| London breakout | USDJPY | 1290 | 6.22 | −0.065R | −84.3 |
| Mean reversion | EURUSD | 1530 | 7.37 | −0.078R | −119.4 |
| Mean reversion | USDJPY | 1412 | 6.81 | −0.085R | −120.0 |
| Momentum pullback | EURUSD | 3219 | 15.51 | −0.098R | −316.0 |
| Momentum pullback | USDJPY | 2886 | 13.92 | −0.125R | −359.8 |

The two rules that actually reach 10–15/week (momentum on both pairs) are the
worst. Frequency is not the binding constraint.

H1, sweep winner (`2.5/2.0/48`):

| Rule | Pair | Trades | Per week | Expectancy |
|---|---|---:|---:|---:|
| London breakout | EURUSD | 980 | 3.92 | −0.027R |
| London breakout | USDJPY | 762 | 3.05 | +0.035R |
| Mean reversion | EURUSD | 601 | 2.40 | −0.101R |
| Mean reversion | USDJPY | 538 | 2.15 | −0.143R |
| Momentum pullback | EURUSD | 1013 | 4.05 | −0.116R |
| Momentum pullback | USDJPY | 966 | 3.86 | −0.038R |

One positive rule at 3.05/week does not satisfy the mandate.

## Result 6 — the apparent univariate signal is a risk filter

`edge_scan_h1.json` (geometry `2.5/1.5/48`):

- `atr_pct` has the highest pooled IC (EURUSD 0.42, USDJPY 0.40), but its
  **top decile is −0.046R** for EURUSD (−0.053R for USDJPY) and its bottom
  decile is −0.118R (−0.127R). High volatility predicts a *smaller loss*, not a
  profit. It is a regime filter.
- `hour_sin`, `session_london` and `range_exp` sort loss magnitude, not sign.
- The directional features are unstable by year. USDJPY `dist_pdl` top-decile
  mean: +0.183 (2022) → +0.110 (2023) → −0.042 (2024) → −0.151 (2025) →
  −0.177 (2026). USDJPY `range_pos`: +0.194 → −0.012 → +0.025 → −0.016 →
  −0.174.
- `upper_wick` is the most stable directional column for USDJPY (top-decile mean
  −0.160R; per-year −0.166, −0.163, −0.172, −0.064, −0.269), which is
  consistent with a rejection signal — but the *bottom* decile is +0.052R, so
  the spread is a loss-avoidance effect, not a reliable long signal.
- Overlapping labels mean the pooled IC overstates significance. The per-year
  table is the honest test, and it flips sign.

## Result 7 — the structural gates cannot reach 10–15/week

From `sensitivity.json` (selected diagnostic relaxations; production rules untouched):

| Scenario | Trades | Per week | Expectancy |
|---|---:|---:|---:|
| Baseline | 39 | 0.188 | +0.001R |
| H4 neutral allowed | 79 | 0.381 | −0.055R |
| Stop floor 0.8×ATR | 40 | 0.193 | +0.035R |
| Cost share cap 20% | 44 | 0.212 | −0.014R |
| Session window removed | 149 | 0.718 | +0.007R |

Even the most permissive relaxation reaches 0.72 trades/week, 14–21× short of
the 10–15 mandate. The setup conjunctions do not occur often enough; the gates
are not the only constraint, and removing the session window still leaves under
one trade per week.

## Result 8 — costs are conservative, not the source of the result

Median broker spread in the dump is EURUSD 0.8 pips and USDJPY 1.0 pip. The
canonical table charges 1.0 bp round-trip spread + 0.5 bp slippage for EURUSD
(1.65 pips at current prices) and 1.2 + 0.5 bp for USDJPY (2.55 pips). The
model's selected-entry spread averages 1.00 pip EURUSD and 1.51 pips USDJPY
(selected-entry medians 0.9 and 1.0). For EURUSD the canonical spread component
already matches the selected mean; for USDJPY the canonical spread (1.8 pips) is
wider than the selected mean (1.5). Re-pricing only the spread component at the
selected mean would change expectancy by less than 0.02R per trade. It does not
create a holdout edge, and the slippage allowance remains an unmeasured
assumption. Changing the cost model is an owner-level decision.

## Conclusion

- The desk **can** generate 10–15 entries per week without changing risk policy:
  the stable `1.5/1.5/96` cell reaches 12.8/week and the selection candidate
  `4.0/1.5/64` reaches 23.5/week in the holdout, all at
  `max_positions_per_pair = 2`. Frequency is not the binding constraint;
  profitability is.
- **No configuration produces a stable, out-of-sample positive edge at the
  mandated frequency.** The full-period positive cells are geometry maxima
  selected on the same data. When geometry is chosen on 2023–2024 and tested on
  2025–2026, the winner loses 66.9R and the stable-region candidate loses 7.3R.
- **EURUSD — the primary success metric — is negative out of sample in every
  held-out geometry** (−0.05 to −0.068R per trade). USDJPY has a weak positive
  holdout cell (+0.034R, 7.8/week) that is not statistically significant
  (weekly p=0.53) and does not offset EURUSD.
- **`c3`'s 11.8/week is not admissible**: it uses three concurrent positions per
  pair (six total), above `max_concurrent_positions = 4`, and at 5%/4%/3% slot
  risk it would exceed the 15% open-risk cap. Raising only the per-pair limit
  would not deliver it.
- The best honest description of the current system is: **mechanically capable,
  economically unproven, and negative on the pair that must lead.**

Promoting a configuration now would run a known in-sample maximum on demo and
describe it as a validated 10–15/week strategy. That would be false. It is not
a profitable trading system and must not be presented as one.

## Owner decision required

The measurement does not support building the autonomous executor yet. The
honest options are:

1. **Accept a bounded USDJPY-only demo experiment** on the `1.5/1.5/96`
   holdout cell (7.8/week, +0.034R/trade, 2025 +2.04R, 2026 +22.56R, weekly
   p=0.53). This is a single-pair experiment with a non-significant edge, not
   the mandated two-pair product. The cell is a post-hoc stability pick and the
   calibration parameters were chosen on the full period, so this is not clean
   out of sample.
2. **Run a two-pair stable-cell demo at 12.8/week within the current per-pair
   limit** (`1.5/1.5/96`), accepting that the holdout total is −7.3R and EURUSD
   is −0.068R. This satisfies the frequency mandate without a policy change, but
   the point estimate is negative; it is an execution/cost experiment, not an
   edge claim. The cell is a post-hoc stability pick, so it is not clean out of
   sample.
3. **Keep the two-pair mandate and do not trade**: EURUSD has no out-of-sample
   edge, and the two-pair total is negative.
4. **Invest in new data before building the executor**: an authoritative
   economic calendar (actual vs consensus, surprise-scaled) or cross-asset /
   positioning context. This is the only path with a plausible new mechanism.

None of these is a reason to relax the graduation gates in
`docs/specs/autonomous-desk/AMENDMENT_2026-10-19_HF_MANDATE.md`.

## What was not done

- No order was placed, modified or closed. The demo account has not been traded.
- No production detector, risk limit or acceptance criterion was relaxed.
- No credential was rotated or exposed. No new pair was added.
- No executor was built for a strategy with no validated edge.

## Reproduction

```powershell
cd pipeline
$env:PYTHONPATH="."

# A-priori baseline
.\.venv\Scripts\python.exe scripts\backtest_dense.py

# Best full-period M15 cell (post-hoc)
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe m15 --stop 1.5 --target 1.5 --hold 32 --signal-rate 0.20 --min-edge 0.02 --concurrency 2 --tag m15_c2
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe m15 --stop 1.5 --target 1.5 --hold 32 --signal-rate 0.20 --min-edge 0.02 --concurrency 1 --tag m15_c1
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe m15 --stop 1.5 --target 1.5 --hold 32 --signal-rate 0.20 --min-edge 0.02 --concurrency 3 --tag m15_c3

# H1 sweep winner, single configuration
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48 --signal-rate 0.03 --min-edge 0 --tag h1_edge

# Geometry selection on 2023-10..2025-01, then holdout evaluation
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe m15 --start 2022-10-27 --end 2025-01-01 --min-edge 0.02 --signal-rate 0.20 --concurrency 2 --tag m15_holdout_select
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe m15 --start 2024-01-01 --stop 4.0 --target 1.5 --hold 64 --signal-rate 0.20 --min-edge 0.02 --concurrency 2 --tag holdout_select_winner
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe m15 --start 2024-01-01 --stop 1.5 --target 1.5 --hold 96 --signal-rate 0.20 --min-edge 0.02 --concurrency 2 --tag holdout_stable

# Frequency / concurrency curve
.\.venv\Scripts\python.exe scripts\dense_frequency_curve.py --stop 1.5 --target 1.5 --hold 32 --min-edge 0.02 --concurrency 2 --tag conc2

# Rules, edge scan, protocol scan, sweeps
.\.venv\Scripts\python.exe scripts\backtest_rules.py --timeframe m15
.\.venv\Scripts\python.exe scripts\backtest_rules.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48
.\.venv\Scripts\python.exe scripts\edge_scan.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 1.5 --hold 48 --tag edge_scan_h1
.\.venv\Scripts\python.exe scripts\dense_protocol_scan.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe m15
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe h1 --start 2022-01-01 --tag h1
```
