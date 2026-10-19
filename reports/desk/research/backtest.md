# Desk strategy backtest

**Historical simulation - not live results.** Generated from completed bars only.

## Assumptions

- Entry fills at the next M15 open after the decision bar closes.
- A bar spanning both stop and target books the STOP (pessimistic).
- Costs use the canonical round-trip + slippage table in src/paper/config.py.
- Management: 50% at +1R, stop to BE, chandelier trail on completed H1 bars.
- D1 context is a price/EMA20-slope proxy, not the production regime model.
- SU2-v1 is structurally untradeable under the 1.2xATR stop floor.

## EURUSD

Sample: 2022-10-27 to 2026-10-19 (1453 days).

| Metric | Value |
|---|---|
| trades | 13 |
| win_rate | 0.462 |
| expectancy_r | +0.162 |
| avg_win_r | +0.733 |
| avg_loss_r | -0.327 |
| median_r | -0.085 |
| profit_factor | 1.920 |
| total_net_r | +2.106 |
| total_gross_r | +2.719 |
| total_costs_r | +0.612 |
| avg_bars_held | 42.800 |

### Weekly

| Metric | Value |
|---|---|
| trades_per_week | 0.060 |
| trades_per_active_week | 1.080 |
| active_weeks | 12 |
| avg_week_net_r | +0.176 |
| avg_week_net_pct | +0.176 |
| avg_winning_week_r | +0.710 |
| avg_losing_week_r | -0.359 |
| best_week_r | +1.315 |
| worst_week_r | -0.809 |
| positive_weeks | 6 |
| negative_weeks | 6 |

### Funnel

- H1 opportunities evaluated: **24752**
- Candidates passing all detector gates: **13**
- Trades taken after admission: **13**

Top detector rejections:

| Reason | Count |
|---|---|
| SU2-v1:sweep_not_beyond_pool_band | 84901 |
| SU1-v1:d1_context_mismatch | 26098 |
| SU2-v1:d1_context_mismatch | 26098 |
| SU3-v1:d1_context_mismatch | 26098 |
| SU1-v1:structure_not_aligned | 12274 |
| SU2-v1:structure_not_aligned | 12274 |
| SU3-v1:structure_not_aligned | 12274 |
| SU3-v1:breakout_close_below_margin | 8950 |
| SU1-v1:last_close_wrong_side_of_ema | 3983 |
| SU1-v1:no_ema_touch | 2538 |
| SU1-v1:trigger_close_not_beyond_prior_extreme | 1742 |
| SU2-v1:sweep_did_not_reclaim_pool | 916 |

### Active weeks

| Week | Trades | Wins | Net R | Net % |
|---|---|---|---|---|
| 2023-W01 | 1 | 0 | -0.81 | -0.81% |
| 2023-W22 | 1 | 0 | -0.17 | -0.18% |
| 2023-W36 | 1 | 1 | +0.64 | +0.64% |
| 2023-W39 | 1 | 1 | +0.47 | +0.47% |
| 2024-W38 | 1 | 0 | -0.45 | -0.45% |
| 2025-W04 | 1 | 0 | -0.50 | -0.50% |
| 2025-W09 | 1 | 1 | +0.00 | +0.00% |
| 2025-W26 | 1 | 0 | -0.09 | -0.08% |
| 2026-W07 | 1 | 1 | +0.87 | +0.87% |
| 2026-W26 | 1 | 1 | +0.96 | +0.96% |
| 2026-W32 | 2 | 1 | +1.31 | +1.32% |
| 2026-W39 | 1 | 0 | -0.13 | -0.13% |

## USDJPY

Sample: 2022-10-26 to 2026-10-19 (1453 days).

| Metric | Value |
|---|---|
| trades | 26 |
| win_rate | 0.269 |
| expectancy_r | -0.080 |
| avg_win_r | +0.630 |
| avg_loss_r | -0.341 |
| median_r | -0.078 |
| profit_factor | 0.680 |
| total_net_r | -2.076 |
| total_gross_r | -0.989 |
| total_costs_r | +1.087 |
| avg_bars_held | 38.700 |

### Weekly

| Metric | Value |
|---|---|
| trades_per_week | 0.130 |
| trades_per_active_week | 1.130 |
| active_weeks | 23 |
| avg_week_net_r | -0.090 |
| avg_week_net_pct | -0.090 |
| avg_winning_week_r | +0.724 |
| avg_losing_week_r | -0.378 |
| best_week_r | +1.474 |
| worst_week_r | -1.637 |
| positive_weeks | 6 |
| negative_weeks | 17 |

### Funnel

- H1 opportunities evaluated: **24764**
- Candidates passing all detector gates: **26**
- Trades taken after admission: **26**

Top detector rejections:

| Reason | Count |
|---|---|
| SU2-v1:sweep_not_beyond_pool_band | 71489 |
| SU1-v1:d1_context_mismatch | 25774 |
| SU2-v1:d1_context_mismatch | 25774 |
| SU3-v1:d1_context_mismatch | 25774 |
| SU1-v1:structure_not_aligned | 13168 |
| SU2-v1:structure_not_aligned | 13168 |
| SU3-v1:structure_not_aligned | 13168 |
| SU3-v1:breakout_close_below_margin | 8413 |
| SU1-v1:last_close_wrong_side_of_ema | 3566 |
| SU1-v1:no_ema_touch | 2154 |
| SU1-v1:trigger_close_not_beyond_prior_extreme | 1978 |
| SU2-v1:sweep_did_not_reclaim_pool | 835 |

### Active weeks

| Week | Trades | Wins | Net R | Net % |
|---|---|---|---|---|
| 2022-W48 | 1 | 0 | -0.02 | -0.02% |
| 2023-W05 | 2 | 0 | -1.64 | -1.64% |
| 2023-W25 | 1 | 0 | -0.56 | -0.56% |
| 2023-W33 | 1 | 0 | -0.24 | -0.24% |
| 2023-W41 | 2 | 0 | -0.25 | -0.25% |
| 2024-W07 | 1 | 0 | -0.22 | -0.22% |
| 2024-W11 | 1 | 0 | -0.71 | -0.71% |
| 2024-W12 | 2 | 1 | -0.02 | -0.02% |
| 2024-W24 | 1 | 0 | -0.00 | -0.00% |
| 2024-W26 | 1 | 1 | +0.76 | +0.76% |
| 2024-W38 | 1 | 0 | -0.30 | -0.30% |
| 2024-W41 | 1 | 0 | -0.07 | -0.07% |
| 2024-W52 | 1 | 1 | +0.83 | +0.83% |
| 2025-W09 | 1 | 0 | -0.04 | -0.04% |
| 2025-W13 | 1 | 1 | +1.47 | +1.47% |
| 2025-W29 | 1 | 0 | -0.05 | -0.05% |
| 2025-W36 | 1 | 0 | -1.07 | -1.07% |
| 2025-W39 | 1 | 1 | +0.10 | +0.10% |
| 2025-W40 | 1 | 0 | -0.57 | -0.57% |
| 2025-W47 | 1 | 1 | +1.06 | +1.06% |
| 2026-W06 | 1 | 1 | +0.12 | +0.12% |
| 2026-W09 | 1 | 0 | -0.17 | -0.17% |
| 2026-W28 | 1 | 0 | -0.50 | -0.50% |

## Both pairs combined

| Metric | Value |
|---|---|
| trades | 39 |
| win_rate | 0.333 |
| expectancy_r | +0.001 |
| avg_win_r | +0.678 |
| avg_loss_r | -0.338 |
| median_r | -0.085 |
| best_r | +1.474 |
| worst_r | -1.069 |
| profit_factor | 1.000 |
| total_net_r | +0.031 |
| total_gross_r | +1.730 |
| total_costs_r | +1.699 |
| avg_bars_held | 40.100 |
| avg_mae_r | +0.476 |
| avg_mfe_r | +0.546 |
| partial_taken | 8 |

### Per setup

| Setup | Trades | Net R | Win rate | Expectancy |
|---|---|---|---|---|
| SU1-v1 | 38 | -0.44 | 31.60% | -0.012 |
| SU3-v1 | 1 | +0.47 | 100.00% | +0.472 |
