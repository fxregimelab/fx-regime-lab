# Dense-trading research findings (2026-10-19)

**Historical simulation — not live results.** Every number below comes from
completed bars, with entry at the next bar's open, stop-before-target on
ambiguous bars, gaps filled at the open, and canonical costs subtracted from
every label. The harness was independently reviewed; the review found and this
revision fixes a dead-context-feature bug, a cross-fold label leak, rate
denominators that included training bars, and several smaller defects. All
numbers here are post-fix and were regenerated from the same data snapshot
(fingerprints in `dense*.json`).

## The question

The owner asked for **10–15 settled trades per week** so that selection can be
optimised on a statistically usable sample. The structural-setup path produced
**39 trades in four years (~0.19/week)**, which cannot support optimisation.

Two things had to be separated:

1. **Can the desk generate the frequency?** (mechanical)
2. **Is there an edge at that frequency?** (economic)

The answer to (1) is yes. The answer to (2), on all data and features currently
available, is **not at the mandated frequency, and not on EURUSD**.

## What was measured

| Instrument | File | What it answers |
|---|---|---|
| Dense walk-forward harness | `src/paper/backtest/dense.py` | OOS expectancy of a feature-scored selector |
| Geometry sweep | `sweep.json`, `sweep_h1.json` | Does stop/target/hold change the sign? |
| Interpretable rules | `rules.json`, `rules_h1.json` | Can a one-line rule beat the model? |
| Univariate edge scan | `edge_scan_h1.json` | Is any feature predictive at all? |
| Protocol scan | `protocol_scan.json` | Do retrain window / selectivity help? |
| Frequency curve | `frequency_curve.json` | What happens to expectancy as trades are added? |
| Structural sensitivity | `sensitivity.json` | Can relaxing setup gates reach the target frequency? |

Protocol: expanding-window walk-forward, no shuffling, fixed hyper-parameters,
training strictly before each test window. Training labels are **purged**: a
label is only used if it resolves before the test window starts. Model: ridge
on 30 causal features, one symmetric model over long and short directional
views. The rate denominator is the out-of-sample span only.

## Result 1 — frequency is achievable, and it is not where the edge is

The interpretable rules trade at the requested rate:

| Rule | Pair | Trades | Per week | Expectancy | Net R |
|---|---|---:|---:|---:|---:|
| London breakout | EURUSD | 1697 | 8.17 | −0.084R | −142.9 |
| London breakout | USDJPY | 1292 | 6.23 | −0.067R | −86.5 |
| Mean reversion | EURUSD | 1534 | 7.39 | −0.079R | −121.3 |
| Mean reversion | USDJPY | 1413 | 6.82 | −0.086R | −121.0 |
| Momentum pullback | EURUSD | 3224 | 15.53 | −0.096R | −309.9 |
| Momentum pullback | USDJPY | 2890 | 13.94 | −0.126R | −363.1 |

M15, 2022-10-27 → 2026-10-19. The two rules that actually reach 10–15/week
(momentum on both pairs) are the **worst** of the six. Frequency is not the
binding constraint; the edge is.

On H1 with the best rule geometry, one cell turns slightly positive:

| Rule | Pair | Trades | Per week | Expectancy |
|---|---|---:|---:|---:|
| London breakout | USDJPY | 832 | 3.33 | +0.029R |

That is the entire positive rule set: one pair, one rule, 3.3 trades/week,
+0.029R per trade.

## Result 2 — best dense cells are positive, but only at low frequency

M15 geometry sweep, 27 configurations, walk-forward:

| Stop / target / hold | Trades | Per week | Net R | R/week |
|---|---:|---:|---:|---:|
| 1.5 / 1.5 / 32 | 742 | 4.77 | +16.83 | +0.108 |
| 1.5 / 1.5 / 96 | 810 | 5.21 | +16.16 | +0.104 |
| 4.0 / 2.0 / 96 | 965 | 6.20 | +14.30 | +0.092 |
| 1.5 / 1.0 / 32 | 627 | 4.00 | +9.10 | +0.059 |
| 2.5 / 2.0 / 32 | 1139 | 7.30 | −57.20 | −0.370 |

The `1.5 / 1.5` region is internally consistent across hold times. It is also
**USDJPY-only**:

| Pair | Trades | Per week | Expectancy | Net R |
|---|---:|---:|---:|---:|
| EURUSD | 189 | 1.22 | +0.0005R | +0.09 |
| USDJPY | 553 | 3.56 | +0.0303R | +16.73 |

EURUSD is exactly flat. USDJPY's +16.73R is not spread across years:

| Year | USDJPY net R | Trades |
|---|---:|---:|
| 2023 | −2.05 | 64 |
| 2024 | −0.62 | 180 |
| 2025 | +17.18 | 159 |
| 2026 | +2.22 | 150 |

The edge is a 2025 phenomenon. 8 of 13 folds are positive; the largest single
fold is 22.6% of positive fold profit, so it is not one-fold concentration, but
it is year-concentrated.

H1 sweep (27 configurations), best cell `2.5 / 2.0 / 48`:

| Pair | Trades | Per week | Expectancy | Net R |
|---|---:|---:|---:|---:|
| EURUSD | 248 | 1.25 | −0.029R | −7.12 |
| USDJPY | 432 | 2.18 | +0.114R | +49.09 |

USDJPY by year: 2023 +0.49, 2024 +33.75, 2025 +18.82, **2026 −3.96**. 9 of 16
folds positive. The edge is real enough to measure in 2024–2025 and is decaying
in 2026.

A longer training window and a wider selection band raise the H1 USDJPY cell
to +0.173R over 353 trades (2.42/week), but the last three folds are negative.
That is a protocol choice selected after seeing the data, so it is a hypothesis,
not a validated configuration.

## Result 3 — pushing to 10–15/week drives expectancy to zero

The frequency curve varies only the selection rate on a fixed geometry
(`frequency_curve.json`). This is the direct answer to the mandate:

| Selection rate | Total trades | Per week | Total net R | R/week | USDJPY expectancy |
|---:|---:|---:|---:|---:|---:|
| 0.02 | 742 | 4.8 | −10.8 | −0.07 | +0.008R |
| 0.05 | 969 | 6.2 | −15.3 | −0.10 | +0.003R |
| 0.10 | 1083 | 7.0 | −4.5 | −0.03 | +0.021R |
| 0.20 | 1125 | 7.2 | −3.2 | −0.02 | +0.016R |
| 0.35 | 1180 | 7.6 | −5.2 | −0.03 | +0.017R |
| 0.50 | 1180 | 7.6 | −5.2 | −0.03 | +0.017R |

Two facts matter:

1. The best measured **total** frequency with one position per pair at a time is
   **7.6/week**, still below the mandate.
2. At that frequency the total is **negative** and USDJPY is **+0.017R**, which
   is inside the cost noise. The +0.067R USDJPY cell in the a-priori baseline
   came from a much more selective threshold (2.9/week).

A positive edge that exists only where there are few trades cannot be scaled to
10–15/week by lowering the bar; the added trades are the ones the model ranked
lowest, and they are not profitable after costs.

## Result 4 — the apparent univariate signal is a risk filter, not alpha

`edge_scan_h1.json` is decisive on this point:

- `atr_pct` has the highest pooled IC (+0.42), but its **top decile is
  −0.046R** and its bottom decile is −0.118R. High volatility predicts a
  *smaller loss*, not a profit. It is a regime filter, not a directional edge.
- `hour_sin`, `session_london` and `range_exp` behave the same way: they sort
  loss magnitude, not sign.
- The genuinely directional features are unstable by year. USDJPY `dist_pdl`
  top-decile mean goes +0.183 (2022) → +0.109 (2023) → −0.041 (2024) → −0.150
  (2025) → −0.177 (2026). USDJPY `range_pos` goes +0.193 → −0.014 → +0.024 →
  −0.015 → −0.177.
- Overlapping labels mean the pooled IC overstates significance; the per-year
  table is the honest test, and it flips sign.

## Result 5 — the structural gates cannot reach 10–15/week either

From `sensitivity.json` (M15, diagnostic relaxations, production rules untouched):

| Scenario | Trades | Per week | Expectancy |
|---|---:|---:|---:|
| Baseline | 39 | 0.188 | +0.001R |
| H4 neutral allowed | 79 | 0.381 | −0.055R |
| Stop floor 0.8×ATR | 40 | 0.193 | +0.035R |
| Cost share cap 20% | 44 | 0.212 | −0.014R |
| Session window removed | 149 | 0.718 | +0.007R |

Even the most permissive relaxation reaches **0.72 trades/week**, roughly
20× short of the mandate. The setup conjunctions simply do not occur that often;
the gates are not what is suppressing frequency.

## Result 6 — costs are conservative, not the source of the result

Median broker spread in the dump is EURUSD 0.8 pips and USDJPY 1.0 pip. The
canonical table charges 1.65 and 2.55 pips round trip. The model's *selected*
entries are wider than the median (mean 1.19 pips EURUSD, 1.41 pips USDJPY),
so the canonical margin is thinner than the full-sample comparison suggests —
but it is still conservative, not optimistic. Re-pricing at the selected-entry
spread would improve the best cells by roughly 0.01–0.03R per trade. It does not
create a 2026 edge, and it does not make 10–15/week profitable.

Changing the cost model is an owner-level decision, not an agent change.

## Conclusion

- The desk **can** trade 10–15 times per week. The rules already do.
- At that frequency, with the data and features currently available, there is
  **no demonstrated positive expectancy**. The 10–15/week rules lose 0.08–0.13R
  per trade.
- The best positive configurations are **USDJPY-only, 2–4 trades/week**, and
  their edge is concentrated in 2024–2025 with 2026 flat-to-negative.
- EURUSD — the primary success metric and the pair that must lead — is flat at
  best (+0.0005R over 189 trades) and negative in most configurations.
- The maximum measured total frequency with one position per pair is 7.6/week,
  and total expectancy there is approximately zero to negative.

Promoting a dense configuration now would knowingly run a low-frequency,
single-pair, decaying-edge strategy on demo, while claiming to satisfy a
10–15/week, two-pair mandate. That would be a false claim. It is not a
profitable trading system and must not be described as one.

## Owner decision required

The measurement does not support building the full autonomous executor yet.
The honest options are:

1. **Accept a bounded demo experiment** on the USDJPY low-frequency cell
   (2–4/week, +0.03 to +0.17R/trade, 2026 flat-to-negative). This is an
   experiment with a known decaying edge, not the mandated product.
2. **Relax the one-position-per-pair constraint** and/or add concurrency to
   reach 10–15/week. The frequency curve says the added trades are ~0R, so this
   meets the frequency target but not the economic one.
3. **Invest in new data before building the executor**: an authoritative
   economic calendar (actual vs consensus, surprise-scaled) or cross-asset /
   positioning context. This is the only path with a plausible new mechanism.
4. **Change the cost model to measured broker spread** (owner decision). It
   improves the best cells slightly; it does not create an edge.

Each option is a product decision. None of them is a reason to relax the
graduation gates in
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
.\.venv\Scripts\python.exe scripts\backtest_dense.py
.\.venv\Scripts\python.exe scripts\backtest_dense.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48 --signal-rate 0.03 --min-edge 0 --tag h1_edge
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe m15
.\.venv\Scripts\python.exe scripts\backtest_dense_sweep.py --timeframe h1 --start 2022-01-01 --tag h1
.\.venv\Scripts\python.exe scripts\edge_scan.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 1.5 --hold 48 --tag edge_scan_h1
.\.venv\Scripts\python.exe scripts\backtest_rules.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 1.5 --hold 48
.\.venv\Scripts\python.exe scripts\dense_frequency_curve.py --timeframe m15 --stop 1.5 --target 2.0 --hold 32
.\.venv\Scripts\python.exe scripts\dense_protocol_scan.py --timeframe h1 --start 2022-01-01 --stop 2.5 --target 2.0 --hold 48
```
