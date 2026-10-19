# Dense walk-forward research

**Historical simulation - not live results.** Walk-forward: every trade below was
chosen by a model trained only on earlier bars. Entry at the next M15 open, stop
before target on ambiguous bars, gaps fill at the open, canonical costs included.

## Configuration (fixed a priori, not tuned per fold)

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
- `bars_per_week`: 480.0

| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |
|---|---|---|---|---|---|---|
| EURUSD | 43 | 0.207 | 32.6% | -0.386 | -16.61 | 16.57 |
| USDJPY | 346 | 1.669 | 42.8% | -0.019 | -6.58 | 92.86 |

## Selected vs unconditional

| Pair | Selected expectancy R | Unconditional R | Edge |
|---|---|---|---|
| EURUSD | -0.386 | -0.242 | -0.144 |
| USDJPY | -0.019 | -0.209 | +0.190 |

## EURUSD fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-27 to 2024-01-25 | 5 | -0.45 | -0.089 | -0.248 |
| 1 | 2024-01-25 to 2024-04-24 | 28 | -9.39 | -0.336 | -0.300 |
| 2 | 2024-04-24 to 2024-07-23 | 0 | +0.00 | +0.000 | -0.340 |
| 3 | 2024-07-23 to 2024-10-21 | 1 | -1.35 | -1.345 | -0.287 |
| 4 | 2024-10-21 to 2025-01-19 | 1 | -1.25 | -1.247 | -0.220 |
| 5 | 2025-01-19 to 2025-04-19 | 1 | -1.21 | -1.209 | -0.166 |
| 6 | 2025-04-19 to 2025-07-18 | 1 | -1.26 | -1.259 | -0.154 |
| 7 | 2025-07-18 to 2025-10-16 | 4 | +0.89 | +0.224 | -0.187 |
| 8 | 2025-10-16 to 2026-01-14 | 0 | +0.00 | +0.000 | -0.270 |
| 9 | 2026-01-14 to 2026-04-14 | 1 | -1.24 | -1.244 | -0.240 |
| 10 | 2026-04-14 to 2026-07-13 | 1 | -1.36 | -1.359 | -0.308 |
| 11 | 2026-07-13 to 2026-10-11 | 0 | +0.00 | +0.000 | -0.328 |
| 12 | 2026-10-11 to 2026-10-19 | 0 | +0.00 | +0.000 | -0.205 |

## USDJPY fold detail

| Fold | Test window | Trades | Net R | Mean R | Unconditional R |
|---|---|---|---|---|---|
| 0 | 2023-10-26 to 2024-01-24 | 23 | +4.08 | +0.177 | -0.167 |
| 1 | 2024-01-24 to 2024-04-23 | 44 | +11.73 | +0.267 | -0.293 |
| 2 | 2024-04-23 to 2024-07-22 | 56 | -0.66 | -0.012 | -0.205 |
| 3 | 2024-07-22 to 2024-10-20 | 9 | -1.33 | -0.147 | -0.113 |
| 4 | 2024-10-20 to 2025-01-18 | 12 | +3.49 | +0.291 | -0.170 |
| 5 | 2025-01-18 to 2025-04-18 | 18 | +5.50 | +0.305 | -0.159 |
| 6 | 2025-04-18 to 2025-07-17 | 43 | -22.78 | -0.530 | -0.156 |
| 7 | 2025-07-17 to 2025-10-15 | 11 | -4.58 | -0.416 | -0.222 |
| 8 | 2025-10-15 to 2026-01-13 | 21 | +6.77 | +0.322 | -0.232 |
| 9 | 2026-01-13 to 2026-04-13 | 22 | +4.72 | +0.215 | -0.217 |
| 10 | 2026-04-13 to 2026-07-12 | 62 | -11.30 | -0.182 | -0.396 |
| 11 | 2026-07-12 to 2026-10-10 | 24 | -4.06 | -0.169 | -0.225 |
| 12 | 2026-10-10 to 2026-10-16 | 1 | +1.85 | +1.849 | -0.167 |
