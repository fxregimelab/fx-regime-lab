# Dense walk-forward research (M15)

**Historical simulation - not live results.** Walk-forward: every trade below was
chosen by a model trained only on earlier bars. Entry at the next bar's open, stop
before target on ambiguous bars, stop gaps fill at the open, target gaps cap at
the target, canonical costs included.

## Configuration (fixed for this run; not re-tuned per fold)

Sweep winners are chosen after seeing the whole grid and are therefore
post-hoc maxima, not a-priori configurations.

- `stop_atr_mult`: 1.5
- `target_r`: 1.5
- `max_hold_bars`: 96
- `warmup_bars`: 120
- `train_days`: 365
- `test_days`: 90
- `calibration_fraction`: 0.25
- `ridge_shrinkage`: 0.05
- `signal_rate`: 0.2
- `min_edge_r`: 0.02
- `min_train_rows`: 5000
- `max_concurrent`: 2

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 472 | 5.033 | 40.9% | -0.068 | -31.96 | 32.70 |
| USDJPY | 730 | 7.814 | 48.1% | +0.034 | +24.62 | 107.04 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.068 | -0.232 | -0.094 | +0.026 | -1.216 | +0.224 |
| USDJPY | +0.034 | -0.222 | -0.193 | +0.226 | +0.710 | +0.478 |

Paired test (selected minus matched, same decision bars): EURUSD t=+0.511, p=+0.609, USDJPY t=+5.523, p=+0.000

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 127 | -21.66 | -0.171 | -0.188 |
| 1 | 2025-03-31 to 2025-06-29 | 225 | -21.40 | -0.095 | -0.146 |
| 2 | 2025-06-29 to 2025-09-27 | 50 | +21.54 | +0.431 | -0.197 |
| 3 | 2025-09-27 to 2025-12-26 | 3 | +1.77 | +0.588 | -0.256 |
| 4 | 2025-12-26 to 2026-03-26 | 46 | -5.56 | -0.121 | -0.214 |
| 5 | 2026-03-26 to 2026-06-24 | 13 | -11.74 | -0.903 | -0.280 |
| 6 | 2026-06-24 to 2026-09-22 | 6 | +2.27 | +0.379 | -0.338 |
| 7 | 2026-09-22 to 2026-10-19 | 2 | +2.82 | +1.411 | -0.239 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 105 | -18.75 | -0.179 | -0.174 |
| 1 | 2025-03-31 to 2025-06-29 | 210 | +20.05 | +0.096 | -0.139 |
| 2 | 2025-06-29 to 2025-09-27 | 106 | -5.62 | -0.053 | -0.193 |
| 3 | 2025-09-27 to 2025-12-26 | 74 | +6.38 | +0.086 | -0.231 |
| 4 | 2025-12-26 to 2026-03-26 | 73 | +14.61 | +0.200 | -0.203 |
| 5 | 2026-03-26 to 2026-06-24 | 50 | +8.00 | +0.160 | -0.350 |
| 6 | 2026-06-24 to 2026-09-22 | 110 | -0.18 | -0.002 | -0.279 |
| 7 | 2026-09-22 to 2026-10-16 | 2 | +0.14 | +0.069 | -0.178 |
