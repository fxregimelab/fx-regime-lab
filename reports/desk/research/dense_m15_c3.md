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
- `max_hold_bars`: 32
- `warmup_bars`: 120
- `train_days`: 365
- `test_days`: 90
- `calibration_fraction`: 0.25
- `ridge_shrinkage`: 0.05
- `signal_rate`: 0.2
- `min_edge_r`: 0.02
- `min_train_rows`: 5000
- `max_concurrent`: 3

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 481 | 3.094 | 43.7% | -0.027 | -12.78 | 34.11 |
| USDJPY | 1351 | 8.706 | 47.7% | +0.036 | +49.08 | 153.47 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.027 | -0.249 | -0.089 | +0.062 | -0.531 | +0.596 |
| USDJPY | +0.036 | -0.211 | -0.111 | +0.148 | +1.141 | +0.254 |

Paired test (selected minus matched, same decision bars): EURUSD t=+1.365, p=+0.173, USDJPY t=+5.072, p=+0.000

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-27 to 2024-01-25 | 24 | -3.29 | -0.137 | -0.236 |
| 1 | 2024-01-25 to 2024-04-24 | 21 | -5.48 | -0.261 | -0.296 |
| 2 | 2024-04-24 to 2024-07-23 | 9 | -3.03 | -0.337 | -0.330 |
| 3 | 2024-07-23 to 2024-10-21 | 23 | +4.02 | +0.175 | -0.286 |
| 4 | 2024-10-21 to 2025-01-19 | 76 | -9.52 | -0.125 | -0.217 |
| 5 | 2025-01-19 to 2025-04-19 | 231 | -16.02 | -0.069 | -0.171 |
| 6 | 2025-04-19 to 2025-07-18 | 36 | -6.25 | -0.174 | -0.153 |
| 7 | 2025-07-18 to 2025-10-16 | 32 | +12.27 | +0.383 | -0.205 |
| 8 | 2025-10-16 to 2026-01-14 | 0 | +0.00 | +0.000 | -0.263 |
| 9 | 2026-01-14 to 2026-04-14 | 22 | +5.91 | +0.269 | -0.213 |
| 10 | 2026-04-14 to 2026-07-13 | 3 | +2.99 | +0.997 | -0.289 |
| 11 | 2026-07-13 to 2026-10-11 | 0 | +0.00 | +0.000 | -0.330 |
| 12 | 2026-10-11 to 2026-10-19 | 4 | +5.62 | +1.405 | -0.265 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-26 to 2024-01-24 | 138 | -31.40 | -0.228 | -0.180 |
| 1 | 2024-01-24 to 2024-04-23 | 35 | +8.69 | +0.248 | -0.279 |
| 2 | 2024-04-23 to 2024-07-22 | 150 | -20.00 | -0.133 | -0.224 |
| 3 | 2024-07-22 to 2024-10-20 | 357 | +22.34 | +0.063 | -0.121 |
| 4 | 2024-10-20 to 2025-01-18 | 83 | +6.44 | +0.078 | -0.169 |
| 5 | 2025-01-18 to 2025-04-18 | 186 | +9.82 | +0.053 | -0.158 |
| 6 | 2025-04-18 to 2025-07-17 | 120 | -0.54 | -0.004 | -0.155 |
| 7 | 2025-07-17 to 2025-10-15 | 47 | +1.52 | +0.032 | -0.216 |
| 8 | 2025-10-15 to 2026-01-13 | 27 | +8.89 | +0.329 | -0.228 |
| 9 | 2026-01-13 to 2026-04-13 | 57 | +21.41 | +0.376 | -0.199 |
| 10 | 2026-04-13 to 2026-07-12 | 66 | +3.31 | +0.050 | -0.370 |
| 11 | 2026-07-12 to 2026-10-10 | 84 | +17.25 | +0.205 | -0.241 |
| 12 | 2026-10-10 to 2026-10-16 | 1 | +1.35 | +1.349 | -0.168 |
