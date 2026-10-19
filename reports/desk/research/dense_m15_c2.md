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
- `max_concurrent`: 2

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 348 | 2.238 | 44.8% | +0.009 | +3.19 | 25.36 |
| USDJPY | 1034 | 6.663 | 47.6% | +0.049 | +50.57 | 117.95 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | +0.009 | -0.249 | -0.090 | +0.099 | +0.158 | +0.875 |
| USDJPY | +0.049 | -0.211 | -0.109 | +0.158 | +1.336 | +0.182 |

Paired test (selected minus matched, same decision bars): EURUSD t=+1.871, p=+0.062, USDJPY t=+4.706, p=+0.000

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-27 to 2024-01-25 | 17 | -2.33 | -0.137 | -0.236 |
| 1 | 2024-01-25 to 2024-04-24 | 17 | -4.02 | -0.237 | -0.296 |
| 2 | 2024-04-24 to 2024-07-23 | 6 | -2.25 | -0.375 | -0.330 |
| 3 | 2024-07-23 to 2024-10-21 | 16 | +2.40 | +0.150 | -0.286 |
| 4 | 2024-10-21 to 2025-01-19 | 55 | -4.66 | -0.085 | -0.217 |
| 5 | 2025-01-19 to 2025-04-19 | 165 | -7.62 | -0.046 | -0.171 |
| 6 | 2025-04-19 to 2025-07-18 | 26 | -4.64 | -0.178 | -0.153 |
| 7 | 2025-07-18 to 2025-10-16 | 25 | +13.60 | +0.544 | -0.205 |
| 8 | 2025-10-16 to 2026-01-14 | 0 | +0.00 | +0.000 | -0.263 |
| 9 | 2026-01-14 to 2026-04-14 | 16 | +6.32 | +0.395 | -0.213 |
| 10 | 2026-04-14 to 2026-07-13 | 2 | +2.18 | +1.091 | -0.289 |
| 11 | 2026-07-13 to 2026-10-11 | 0 | +0.00 | +0.000 | -0.330 |
| 12 | 2026-10-11 to 2026-10-19 | 3 | +4.20 | +1.399 | -0.265 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-26 to 2024-01-24 | 105 | -17.50 | -0.167 | -0.180 |
| 1 | 2024-01-24 to 2024-04-23 | 29 | +9.89 | +0.341 | -0.279 |
| 2 | 2024-04-23 to 2024-07-22 | 115 | -14.62 | -0.127 | -0.224 |
| 3 | 2024-07-22 to 2024-10-20 | 272 | +19.28 | +0.071 | -0.121 |
| 4 | 2024-10-20 to 2025-01-18 | 62 | +8.21 | +0.132 | -0.169 |
| 5 | 2025-01-18 to 2025-04-18 | 139 | +8.50 | +0.061 | -0.158 |
| 6 | 2025-04-18 to 2025-07-17 | 89 | +2.59 | +0.029 | -0.155 |
| 7 | 2025-07-17 to 2025-10-15 | 37 | -0.44 | -0.012 | -0.216 |
| 8 | 2025-10-15 to 2026-01-13 | 21 | +7.74 | +0.369 | -0.228 |
| 9 | 2026-01-13 to 2026-04-13 | 45 | +14.78 | +0.328 | -0.199 |
| 10 | 2026-04-13 to 2026-07-12 | 52 | +3.77 | +0.072 | -0.370 |
| 11 | 2026-07-12 to 2026-10-10 | 67 | +7.04 | +0.105 | -0.241 |
| 12 | 2026-10-10 to 2026-10-16 | 1 | +1.35 | +1.349 | -0.168 |
