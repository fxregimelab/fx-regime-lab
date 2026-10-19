# Dense walk-forward research (H1)

**Historical simulation - not live results.** Walk-forward: every trade below was
chosen by a model trained only on earlier bars. Entry at the next bar's open, stop
before target on ambiguous bars, stop gaps fill at the open, target gaps cap at
the target, canonical costs included.

## Configuration (fixed for this run; not re-tuned per fold)

Sweep winners are chosen after seeing the whole grid and are therefore
post-hoc maxima, not a-priori configurations.

- `stop_atr_mult`: 2.5
- `target_r`: 2.0
- `max_hold_bars`: 48
- `warmup_bars`: 120
- `train_days`: 365
- `test_days`: 90
- `calibration_fraction`: 0.25
- `ridge_shrinkage`: 0.05
- `signal_rate`: 0.03
- `min_edge_r`: 0.0
- `min_train_rows`: 5000
- `max_concurrent`: 1

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 246 | 1.243 | 41.1% | -0.026 | -6.36 | 13.20 |
| USDJPY | 430 | 2.173 | 44.0% | +0.105 | +45.23 | 25.22 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.026 | -0.047 | +0.006 | -0.032 | -0.317 | +0.752 |
| USDJPY | +0.105 | -0.051 | -0.038 | +0.143 | +1.618 | +0.106 |

Paired test (selected minus matched, same decision bars): EURUSD t=-0.423, p=+0.673, USDJPY t=+2.542, p=+0.011

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-01-02 to 2023-04-02 | 32 | +1.66 | +0.052 | +0.003 |
| 1 | 2023-04-02 to 2023-07-01 | 11 | +10.46 | +0.951 | -0.009 |
| 2 | 2023-07-01 to 2023-09-29 | 5 | +0.70 | +0.140 | -0.020 |
| 3 | 2023-09-29 to 2023-12-28 | 29 | -10.65 | -0.367 | +0.042 |
| 4 | 2023-12-28 to 2024-03-27 | 7 | +0.13 | +0.019 | -0.118 |
| 5 | 2024-03-27 to 2024-06-25 | 13 | +0.25 | +0.019 | -0.079 |
| 6 | 2024-06-25 to 2024-09-23 | 13 | -5.08 | -0.391 | -0.045 |
| 7 | 2024-09-23 to 2024-12-22 | 4 | +1.80 | +0.451 | -0.053 |
| 8 | 2024-12-22 to 2025-03-22 | 17 | -5.23 | -0.308 | -0.063 |
| 9 | 2025-03-22 to 2025-06-20 | 9 | -2.74 | -0.305 | -0.053 |
| 10 | 2025-06-20 to 2025-09-18 | 22 | -0.43 | -0.019 | -0.016 |
| 11 | 2025-09-18 to 2025-12-17 | 16 | +7.82 | +0.489 | -0.012 |
| 12 | 2025-12-17 to 2026-03-17 | 30 | -2.96 | -0.099 | +0.017 |
| 13 | 2026-03-17 to 2026-06-15 | 24 | -3.65 | -0.152 | -0.156 |
| 14 | 2026-06-15 to 2026-09-13 | 8 | -2.31 | -0.289 | -0.142 |
| 15 | 2026-09-13 to 2026-10-19 | 6 | +3.87 | +0.645 | -0.059 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-01-02 to 2023-04-02 | 17 | -0.59 | -0.035 | -0.099 |
| 1 | 2023-04-02 to 2023-07-01 | 50 | +11.58 | +0.232 | -0.040 |
| 2 | 2023-07-01 to 2023-09-29 | 31 | -4.51 | -0.145 | -0.017 |
| 3 | 2023-09-29 to 2023-12-28 | 20 | -5.99 | -0.300 | +0.037 |
| 4 | 2023-12-28 to 2024-03-27 | 40 | +18.07 | +0.452 | -0.057 |
| 5 | 2024-03-27 to 2024-06-25 | 34 | +13.57 | +0.399 | -0.098 |
| 6 | 2024-06-25 to 2024-09-23 | 16 | -5.66 | -0.354 | -0.041 |
| 7 | 2024-09-23 to 2024-12-22 | 40 | +6.10 | +0.152 | -0.065 |
| 8 | 2024-12-22 to 2025-03-22 | 27 | -7.95 | -0.295 | -0.068 |
| 9 | 2025-03-22 to 2025-06-20 | 22 | +15.19 | +0.691 | +0.039 |
| 10 | 2025-06-20 to 2025-09-18 | 24 | +2.18 | +0.091 | -0.019 |
| 11 | 2025-09-18 to 2025-12-17 | 22 | +8.26 | +0.376 | +0.022 |
| 12 | 2025-12-17 to 2026-03-17 | 18 | +0.83 | +0.046 | -0.081 |
| 13 | 2026-03-17 to 2026-06-15 | 39 | -4.12 | -0.106 | -0.149 |
| 14 | 2026-06-15 to 2026-09-13 | 23 | -6.31 | -0.275 | -0.080 |
| 15 | 2026-09-13 to 2026-10-19 | 7 | +4.58 | +0.654 | -0.207 |
