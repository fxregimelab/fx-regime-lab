# DATA_DICTIONARY.md

## Overview
This document defines the mathematical and logical meaning of every field in the FX Regime Lab database.

## Table: `signals`
| Field | Type | Layer | Description |
|-------|------|-------|-------------|
| `date` | Date | - | Observation date. |
| `pair` | String | - | EURUSD, USDJPY, USDINR. |
| `rate_diff_2y` | Float | 2 | 2Y Yield Spread or Policy Rate Spread. |
| `rate_diff_mom` | Float | 2 | 4-week momentum of `rate_diff_2y`. |
| `cot_net_pos` | Int | 2 | NonCommercial Net Positioning (Contracts). |
| `cot_percentile` | Float | 2 | Net positioning relative to 3-year rolling window. |
| `realized_vol_21` | Float | 3 | 21-day annualized price volatility. |
| `risk_reversal_25d` | Float | 3 | 25-delta risk reversal (Put vs Call premium). |
| `spot` | Float | - | End-of-day spot price. |

## Table: `regime_calls`
| Field | Type | Description |
|-------|------|-------------|
| `date` | Date | Date the call was generated. |
| `pair` | String | EURUSD, USDJPY, USDINR. |
| `regime` | String | The Layer 1 classification (e.g., Carry Collapse). |
| `directional_bias` | String | Long, Short, Neutral (Layer 2). |
| `conviction` | Int | 1 to 5 scale (Layer 2). |
| `confidence` | Float | 0.0 to 1.0 internal model confidence score. |
| `signal_composite` | Float | Combined normalized value of all Layer 2 signals. |

## Table: `validation_log`
| Field | Type | Description |
|-------|------|-------------|
| `call_id` | UUID | Immutable reference to `regime_calls`. |
| `validation_date` | Date | T+5 or T+20 observation date. |
| `is_correct` | Boolean | True if directional bias matched price movement. |
| `pnl_bps` | Float | Price movement in basis points since call. |
| `outcome` | String | Legacy text outcome ('correct'/'incorrect'). |
