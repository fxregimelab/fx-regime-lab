# Signal Flow

## End-to-End Pipeline

```
[External APIs] → [Fetchers] → [Signals] → [Logic] → [Regime] → [DB] → [Frontend]
```

## Step-by-Step

### 1. Data Ingestion (Fetchers)
| Source | API | Data | Frequency |
|--------|-----|------|-----------|
| FRED | fred/series/observations | Treasury yields | Daily |
| Alpha Vantage | alphavantage.co | FX spot | Daily |
| Yahoo Finance | yfinance | Spots, vol, cross-asset | Daily |
| CFTC | cftc.gov | COT reports | Weekly (Tue) |
| CME | cmegroup.com | Open interest | Daily |
| ForexFactory | forexfactory.com | Macro calendar | Weekly |

### 2. Signal Computation
```
rate_norm    = MAD_zscore(yield_spread, 90d)
cot_norm     = percentile_rank(cot_net, 3y) * 2 - 1
vol_norm     = empirical_cdf_rank(rv20, 3y) * 2 - 1
oi_norm      = zscore(oi_delta, 90d)
special      = pair_specific_shocks()
```

### 3. Composite
```
composite = dynamic_betas(rate_norm, cot_norm, vol_norm, oi_norm, special)
```

### 4. Layer 1 — Regime Gate
```
if data_stale or vol_expanding or spot_stressed:
    regime = NEUTRAL + invalidated
else:
    regime = hysteresis_tier(composite)
```

### 5. Layer 2 — Directional
```
if not invalidated and not clash_b and not clash_c:
    bias = sign(composite) if |composite| > 0.30 else sign(rate)
    conviction = round((3.0 + composite) * conviction_multiplier)
else:
    bias = NEUTRAL
    conviction = min(conviction, 3)
```

### 6. Layer 3 — Execution
```
entry_timing = f(rvol_rank, skew_alignment)
position_size = f(rvol_rank)  # FULL/HALF/QUARTER
stop_level = spot ± max(1.5 * ATR20, 0.3%)
```

### 7. Persistence
```
writer.write_signal_row(signal_row)
writer.write_regime_call(regime_call)
```

### 8. Frontend Display
```
Supabase → React Query → Components → Terminal
```

## Critical Paths

### The Sacred Write Path
```
Any fetcher → signals/ → logic/ → regime/ → db/writer.py → Supabase
```
**Rule:** No module outside `writer.py` may call `supabase-py`.

### The Immutable Ledger Path
```
scheduler/orchestrator.py → writer.write_regime_call() → regime_calls
```
**Rule:** Append-only. Triggers block UPDATE/DELETE.

## Connections
- **Implemented in:** [[Pipeline]]
- **Displayed in:** [[Frontend]]
- **Persisted in:** [[Database]]
