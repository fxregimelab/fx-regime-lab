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
- `max_concurrent`: 1

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 191 | 1.229 | 47.1% | +0.059 | +11.34 | 14.83 |
| USDJPY | 612 | 3.944 | 49.0% | +0.090 | +54.89 | 69.44 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | +0.059 | -0.249 | -0.092 | +0.151 | +0.747 | +0.456 |
| USDJPY | +0.090 | -0.211 | -0.092 | +0.182 | +1.876 | +0.061 |

Paired test (selected minus matched, same decision bars): EURUSD t=+2.099, p=+0.037, USDJPY t=+4.138, p=+0.000

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-27 to 2024-01-25 | 9 | -1.80 | -0.201 | -0.236 |
| 1 | 2024-01-25 to 2024-04-24 | 11 | -2.39 | -0.217 | -0.296 |
| 2 | 2024-04-24 to 2024-07-23 | 3 | -1.45 | -0.483 | -0.330 |
| 3 | 2024-07-23 to 2024-10-21 | 8 | +0.45 | +0.057 | -0.286 |
| 4 | 2024-10-21 to 2025-01-19 | 29 | +0.53 | +0.018 | -0.217 |
| 5 | 2025-01-19 to 2025-04-19 | 90 | +1.57 | +0.018 | -0.171 |
| 6 | 2025-04-19 to 2025-07-18 | 15 | -0.98 | -0.066 | -0.153 |
| 7 | 2025-07-18 to 2025-10-16 | 14 | +8.20 | +0.586 | -0.205 |
| 8 | 2025-10-16 to 2026-01-14 | 0 | +0.00 | +0.000 | -0.263 |
| 9 | 2026-01-14 to 2026-04-14 | 9 | +3.33 | +0.370 | -0.213 |
| 10 | 2026-04-14 to 2026-07-13 | 1 | +1.09 | +1.091 | -0.289 |
| 11 | 2026-07-13 to 2026-10-11 | 0 | +0.00 | +0.000 | -0.330 |
| 12 | 2026-10-11 to 2026-10-19 | 2 | +2.77 | +1.386 | -0.265 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-26 to 2024-01-24 | 62 | -5.29 | -0.085 | -0.180 |
| 1 | 2024-01-24 to 2024-04-23 | 16 | +5.51 | +0.344 | -0.279 |
| 2 | 2024-04-23 to 2024-07-22 | 70 | -3.98 | -0.057 | -0.224 |
| 3 | 2024-07-22 to 2024-10-20 | 152 | +18.58 | +0.122 | -0.121 |
| 4 | 2024-10-20 to 2025-01-18 | 34 | +17.56 | +0.517 | -0.169 |
| 5 | 2025-01-18 to 2025-04-18 | 78 | +3.48 | +0.045 | -0.158 |
| 6 | 2025-04-18 to 2025-07-17 | 55 | +0.47 | +0.009 | -0.155 |
| 7 | 2025-07-17 to 2025-10-15 | 23 | -0.56 | -0.025 | -0.216 |
| 8 | 2025-10-15 to 2026-01-13 | 13 | +3.97 | +0.306 | -0.228 |
| 9 | 2026-01-13 to 2026-04-13 | 29 | +7.01 | +0.242 | -0.199 |
| 10 | 2026-04-13 to 2026-07-12 | 34 | +2.99 | +0.088 | -0.370 |
| 11 | 2026-07-12 to 2026-10-10 | 45 | +3.79 | +0.084 | -0.241 |
| 12 | 2026-10-10 to 2026-10-16 | 1 | +1.35 | +1.349 | -0.168 |
