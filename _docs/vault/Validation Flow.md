# Validation Flow

## Purpose
Measure whether the model's directional calls were correct after the fact. This is the **track record** — the only thing that matters for credibility.

## T+5 / T+20 Mechanics

```
T=0: Model makes call (e.g., BULLISH USDJPY, confidence=0.65)
  ↓
T+5: Look up spot price 5 trading days later
  ↓
Compute: log_return_bps(T0, T+5)
  ↓
Compute: realized_direction(return) → UP / DOWN / NEUTRAL
  ↓
Compute: is_correct(BULLISH, UP) → True
  ↓
Compute: brier_score(0.65, True) → (0.65 - 1.0)² = 0.1225
  ↓
Write to validation_log
```

Same process for T+20.

## Metrics Computed

### Per-Call
| Metric | Formula | Purpose |
|--------|---------|---------|
| log_return_t5_bps | 10_000 * ln(S5/S0) | Return in basis points |
| correct_t5 | predicted == realized | Directional accuracy |
| brier_score_t5 | (p - y)² | Probabilistic calibration |
| actual_direction_t5 | UP/DOWN/NEUTRAL | What actually happened |

### Aggregate (Per Pair)
| Metric | Formula | Purpose |
|--------|---------|---------|
| win_rate | wins / directional_calls | Hit rate |
| mean_brier | mean(brier_scores) | Calibration quality |
| brier_skill | (0.25 - mean_brier) / 0.25 | vs random benchmark |
| sharpe_like | mean(return) / std(return) | Return per unit risk |
| max_drawdown | peak - trough in cumulative returns | Worst streak |

## Trading Day Arithmetic

```
T+5 = add_trading_days(T0, 5)  # skips weekends
T+20 = add_trading_days(T0, 20)
```

FX markets trade Mon-Fri. Weekends are skipped.

## Current Track Record

| Pair | T+5 Win Rate | T+5 Brier | T+20 Win Rate | T+20 Brier |
|------|-------------|-----------|---------------|------------|
| EURUSD | 48.2% | 0.247 | 49.7% | 0.253 |
| USDJPY | 48.3% | 0.279 | 49.4% | 0.286 |
| USDINR | 41.4% | 0.230 | 42.0% | 0.242 |
| ALL | 46.7% | 0.256 | 47.7% | 0.264 |

## Interpretation

- **Win rate ~47%:** Slightly better than random (50% would be random for directional calls with deadband). This is a solid baseline for a rate-driven model without COT in historical simulation.
- **Brier ~0.25–0.28:** Reasonably calibrated. The model knows what it doesn't know.
- **T+20 > T+5:** The signal has more time to play out. Macro edges are slow-moving.

## Connections
- **Implemented in:** [[validation_engine]], [[validation_aggregate]]
- **Backfilled by:** [[batch_validation_backfill]]
- **Displayed in:** [[Frontend]] (`/terminal/performance`)
- **Stored in:** [[Database]] (`validation_log`, `validation_stats`)
