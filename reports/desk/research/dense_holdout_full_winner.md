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
| EURUSD | 476 | 5.076 | 43.7% | -0.051 | -24.13 | 32.83 |
| USDJPY | 676 | 7.236 | 49.9% | +0.062 | +42.10 | 100.41 |

## Selected vs benchmarks

All-bar unconditional averages every bar; matched averages both sides at the bars the model actually selected, removing bar-composition effects.

| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |
|---|---|---|---|---|---|---|
| EURUSD | -0.051 | -0.232 | -0.071 | +0.020 | -0.986 | +0.325 |
| USDJPY | +0.062 | -0.222 | -0.186 | +0.249 | +1.331 | +0.184 |

Paired test (selected minus matched, same decision bars): EURUSD t=+0.420, p=+0.674, USDJPY t=+6.034, p=+0.000

The t-test treats trades as independent; overlapping labels and the one-position constraint make it optimistic. Use it as a rough screen.

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 140 | -3.32 | -0.024 | -0.188 |
| 1 | 2025-03-31 to 2025-06-29 | 230 | -25.97 | -0.113 | -0.140 |
| 2 | 2025-06-29 to 2025-09-27 | 43 | +5.95 | +0.138 | -0.198 |
| 3 | 2025-09-27 to 2025-12-26 | 4 | +2.09 | +0.522 | -0.253 |
| 4 | 2025-12-26 to 2026-03-26 | 41 | -5.69 | -0.139 | -0.214 |
| 5 | 2026-03-26 to 2026-06-24 | 9 | -5.04 | -0.560 | -0.286 |
| 6 | 2026-06-24 to 2026-09-22 | 6 | +3.67 | +0.612 | -0.332 |
| 7 | 2026-09-22 to 2026-10-19 | 3 | +4.18 | +1.393 | -0.260 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2024-12-31 to 2025-03-31 | 90 | -16.37 | -0.182 | -0.174 |
| 1 | 2025-03-31 to 2025-06-29 | 203 | +33.49 | +0.165 | -0.140 |
| 2 | 2025-06-29 to 2025-09-27 | 91 | -5.51 | -0.061 | -0.191 |
| 3 | 2025-09-27 to 2025-12-26 | 64 | +12.55 | +0.196 | -0.234 |
| 4 | 2025-12-26 to 2026-03-26 | 67 | +17.01 | +0.254 | -0.202 |
| 5 | 2026-03-26 to 2026-06-24 | 50 | +9.84 | +0.197 | -0.348 |
| 6 | 2026-06-24 to 2026-09-22 | 109 | -9.04 | -0.083 | -0.277 |
| 7 | 2026-09-22 to 2026-10-16 | 2 | +0.14 | +0.069 | -0.177 |
