# Dense walk-forward research (M15)

**Historical simulation - not live results.** Walk-forward: every trade below was
chosen by a model trained only on earlier bars. Entry at the next bar's open, stop
before target on ambiguous bars, stop gaps fill at the open, target gaps cap at
the target, canonical costs included.

## Configuration (fixed for this run; not re-tuned per fold)

Sweep winners are chosen after seeing the whole grid and are therefore
post-hoc maxima, not a-priori configurations.

- `stop_atr_mult`: 1.5
- `target_r`: 2.0
- `max_hold_bars`: 32
- `warmup_bars`: 120
- `train_days`: 365
- `test_days`: 90
- `calibration_fraction`: 0.25
- `ridge_shrinkage`: 0.05
- `signal_rate`: 0.02
- `min_edge_r`: 0.02
- `min_train_rows`: 5000
- `max_concurrent`: 1

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 147 | 0.946 | 36.7% | -0.105 | -15.44 | 15.24 |
| USDJPY | 448 | 2.887 | 42.9% | +0.067 | +30.01 | 62.38 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.105 | -0.254 | -0.128 | +0.023 | -1.057 | +0.292 |
| USDJPY | +0.067 | -0.213 | -0.111 | +0.178 | +1.027 | +0.305 |

Paired test (selected minus matched, same decision bars): EURUSD t=+0.259, p=+0.796, USDJPY t=+3.168, p=+0.002

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-27 to 2024-01-25 | 14 | -11.68 | -0.834 | -0.248 |
| 1 | 2024-01-25 to 2024-04-24 | 16 | -0.09 | -0.005 | -0.300 |
| 2 | 2024-04-24 to 2024-07-23 | 8 | -1.20 | -0.149 | -0.340 |
| 3 | 2024-07-23 to 2024-10-21 | 8 | +1.44 | +0.179 | -0.287 |
| 4 | 2024-10-21 to 2025-01-19 | 34 | -5.98 | -0.176 | -0.220 |
| 5 | 2025-01-19 to 2025-04-19 | 39 | -8.45 | -0.217 | -0.166 |
| 6 | 2025-04-19 to 2025-07-18 | 0 | +0.00 | +0.000 | -0.154 |
| 7 | 2025-07-18 to 2025-10-16 | 13 | +4.89 | +0.376 | -0.187 |
| 8 | 2025-10-16 to 2026-01-14 | 0 | +0.00 | +0.000 | -0.270 |
| 9 | 2026-01-14 to 2026-04-14 | 12 | +1.05 | +0.087 | -0.240 |
| 10 | 2026-04-14 to 2026-07-13 | 1 | +0.81 | +0.809 | -0.308 |
| 11 | 2026-07-13 to 2026-10-11 | 0 | +0.00 | +0.000 | -0.328 |
| 12 | 2026-10-11 to 2026-10-19 | 2 | +3.77 | +1.885 | -0.211 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-26 to 2024-01-24 | 67 | -13.81 | -0.206 | -0.167 |
| 1 | 2024-01-24 to 2024-04-23 | 13 | +3.49 | +0.268 | -0.293 |
| 2 | 2024-04-23 to 2024-07-22 | 69 | +9.14 | +0.133 | -0.205 |
| 3 | 2024-07-22 to 2024-10-20 | 26 | +2.14 | +0.082 | -0.113 |
| 4 | 2024-10-20 to 2025-01-18 | 20 | +0.65 | +0.033 | -0.170 |
| 5 | 2025-01-18 to 2025-04-18 | 86 | +11.31 | +0.132 | -0.159 |
| 6 | 2025-04-18 to 2025-07-17 | 2 | -0.37 | -0.186 | -0.156 |
| 7 | 2025-07-17 to 2025-10-15 | 18 | +1.29 | +0.072 | -0.222 |
| 8 | 2025-10-15 to 2026-01-13 | 18 | +10.75 | +0.598 | -0.232 |
| 9 | 2026-01-13 to 2026-04-13 | 33 | +4.88 | +0.148 | -0.217 |
| 10 | 2026-04-13 to 2026-07-12 | 37 | -3.17 | -0.086 | -0.396 |
| 11 | 2026-07-12 to 2026-10-10 | 58 | +1.86 | +0.032 | -0.225 |
| 12 | 2026-10-10 to 2026-10-16 | 1 | +1.85 | +1.849 | -0.171 |
