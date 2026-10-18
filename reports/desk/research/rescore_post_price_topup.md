# Validation rescore audit — 2026-10-18

Read-only audit (`pipeline/scripts/audit_validation_rescore.py`): stored non-superseded `validation_log` rows recomputed from `historical_prices` with the canonical scorer (`src/validation/calculator.py`). No database writes were performed.

## Summary

| Metric | Value |
| --- | --- |
| Non-superseded rows loaded | 19491 |
| Scored rows checked | 19491 |
| Unscored rows skipped | 0 |
| Rows with at least one issue | 589 |

Price coverage end (max `historical_prices` date per pair):

- EURUSD: 2026-10-17
- USDINR: 2026-10-18
- USDJPY: 2026-10-16

## Category counts

| Category | Rows |
| --- | --- |
| `cross_pair_corrupt` | 15 |
| `gross_mismatch` | 519 |
| `flag_mismatch` | 92 |
| `net_mismatch` | 523 |
| `brier_mismatch` | 85 |
| `cost_mismatch` | 222 |
| `no_prices` | 68 |

## Worst 20 rows

| id | pair | call_date | prediction | categories | T+5 stored bps | T+5 recomputed bps | T+20 stored bps | T+20 recomputed bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 74117 | USDJPY | 2026-05-21 | BEARISH | cross_pair_corrupt, flag_mismatch, net_mismatch, brier_mismatch | -5033.42 | 42.71 | -49277.99 | 107.17 |
| 74115 | EURUSD | 2026-05-21 | BEARISH | cross_pair_corrupt, net_mismatch | -5033.42 | -6.39 | -49277.99 | -102.01 |
| 74116 | USDINR | 2026-05-21 | BEARISH | cross_pair_corrupt, net_mismatch | -5033.42 | -49.79 | -49277.99 | -174.46 |
| 74120 | USDJPY | 2026-05-22 | NEUTRAL | gross_mismatch, net_mismatch, cross_pair_corrupt | -13.08 | 15.83 | -44300.06 | 141.80 |
| 74118 | EURUSD | 2026-05-22 | NEUTRAL | gross_mismatch, net_mismatch, cross_pair_corrupt | -13.08 | 27.23 | -44300.06 | -140.90 |
| 74122 | USDINR | 2026-05-24 | BEARISH | cross_pair_corrupt, flag_mismatch, net_mismatch, brier_mismatch, gross_mismatch | 44127.94 | -13.08 | -159.04 | -192.54 |
| 74123 | USDJPY | 2026-05-24 | NEUTRAL | cross_pair_corrupt, net_mismatch, gross_mismatch | 44127.94 | 15.83 | -159.04 | 141.80 |
| 74119 | USDINR | 2026-05-22 | BEARISH | cross_pair_corrupt, net_mismatch | -13.08 | -13.08 | -44300.06 | -192.54 |
| 74121 | EURUSD | 2026-05-24 | NEUTRAL | cross_pair_corrupt, net_mismatch, gross_mismatch | 44127.94 | 27.23 | -159.04 | -140.90 |
| 74125 | USDINR | 2026-05-25 | BEARISH | cross_pair_corrupt, flag_mismatch, net_mismatch, brier_mismatch, gross_mismatch | 44018.52 | -75.14 | -155.37 | -146.20 |
| 74124 | EURUSD | 2026-05-25 | NEUTRAL | cross_pair_corrupt, net_mismatch | 44018.52 | 5.71 | -155.37 | -155.37 |
| 74127 | USDJPY | 2026-05-25 | NEUTRAL | cross_pair_corrupt, net_mismatch, gross_mismatch | 44018.52 | 25.57 | -155.37 | 155.26 |
| 74112 | EURUSD | 2003-12-01 | BEARISH | cross_pair_corrupt, flag_mismatch, net_mismatch, brier_mismatch | -36218.27 | 210.88 | -36004.60 | 424.55 |
| 74113 | EURUSD | 2026-05-20 | BEARISH | cross_pair_corrupt, flag_mismatch, net_mismatch, brier_mismatch, gross_mismatch | -5057.66 | 25.57 | 86.65 | 2.44 |
| 74114 | USDINR | 2026-05-20 | BEARISH | cross_pair_corrupt, net_mismatch, gross_mismatch, flag_mismatch, brier_mismatch | -5057.66 | -68.67 | 86.65 | -175.21 |
| 74061 | USDINR | 2026-05-19 | BEARISH | gross_mismatch, net_mismatch | -1071.59 | -106.24 | — | — |
| 83777 | USDINR | 2026-04-28 | BULLISH | gross_mismatch, flag_mismatch, net_mismatch, brier_mismatch | 105.63 | 105.63 | -833.21 | 104.93 |
| 75400 | EURUSD | 2008-07-30 | BEARISH | gross_mismatch, flag_mismatch, net_mismatch, brier_mismatch | -342.75 | 12.47 | -559.79 | -559.79 |
| 75386 | EURUSD | 2008-07-09 | BEARISH | gross_mismatch, net_mismatch | 54.60 | 54.60 | -446.38 | -91.17 |
| 75384 | EURUSD | 2008-07-08 | BEARISH | gross_mismatch, flag_mismatch, net_mismatch, brier_mismatch | 361.91 | 361.91 | -187.60 | 167.62 |
