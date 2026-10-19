# Dense walk-forward research (M15)

**Historical simulation - not live results.** Walk-forward: every trade below was
chosen by a model trained only on earlier bars. Entry at the next bar's open, stop
before target on ambiguous bars, stop gaps fill at the open, target gaps cap at
the target, canonical costs included.

## Configuration (fixed for this run; not re-tuned per fold)

Sweep winners are chosen after seeing the whole grid and are therefore
post-hoc maxima, not a-priori configurations.

- `stop_atr_mult`: 4.0
- `target_r`: 1.5
- `max_hold_bars`: 64
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
| EURUSD | 681 | 7.262 | 46.1% | -0.066 | -45.12 | 33.83 |
| USDJPY | 1518 | 16.249 | 46.3% | -0.014 | -21.74 | 99.35 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.066 | -0.086 | -0.057 | -0.010 | -1.860 | +0.063 |
| USDJPY | -0.014 | -0.083 | -0.075 | +0.061 | -0.538 | +0.591 |

Paired test (selected minus matched, same decision bars): EURUSD t=-0.283, p=+0.777, USDJPY t=+2.459, p=+0.014

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 194 | -33.82 | -0.174 | -0.071 |
| 1 | 2025-03-31 to 2025-06-29 | 203 | -18.81 | -0.093 | -0.060 |
| 2 | 2025-06-29 to 2025-09-27 | 112 | +7.51 | +0.067 | -0.074 |
| 3 | 2025-09-27 to 2025-12-26 | 58 | -6.32 | -0.109 | -0.120 |
| 4 | 2025-12-26 to 2026-03-26 | 66 | -7.92 | -0.120 | -0.114 |
| 5 | 2026-03-26 to 2026-06-24 | 22 | +6.42 | +0.292 | -0.060 |
| 6 | 2026-06-24 to 2026-09-22 | 19 | +4.03 | +0.212 | -0.110 |
| 7 | 2026-09-22 to 2026-10-19 | 7 | +3.80 | +0.543 | -0.069 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 226 | -38.90 | -0.172 | -0.067 |
| 1 | 2025-03-31 to 2025-06-29 | 234 | +23.96 | +0.102 | -0.035 |
| 2 | 2025-06-29 to 2025-09-27 | 227 | +24.49 | +0.108 | -0.061 |
| 3 | 2025-09-27 to 2025-12-26 | 206 | -7.90 | -0.038 | -0.081 |
| 4 | 2025-12-26 to 2026-03-26 | 213 | -36.29 | -0.170 | -0.096 |
| 5 | 2026-03-26 to 2026-06-24 | 201 | -0.59 | -0.003 | -0.151 |
| 6 | 2026-06-24 to 2026-09-22 | 168 | +5.41 | +0.032 | -0.089 |
| 7 | 2026-09-22 to 2026-10-16 | 43 | +8.07 | +0.188 | -0.087 |
