# Pipeline Hub

> All Python pipeline modules. The brain of the FX Regime Lab.

## Data Ingestion (Fetchers)

These modules pull raw data from external APIs. They are **pure fetchers** — no transformation, just ingestion.

| Module | Source | Data |
|--------|--------|------|
| [[fx_spot]] | Alpha Vantage / yfinance | Daily FX closes |
| [[yields]] | FRED API | Treasury yields (US, DE, JP, IN) |
| [[cot]] | CFTC.gov | Commitment of Traders reports |
| [[volatility]] | Yahoo Finance | Realized vol, implied vol, skew |
| [[open_interest]] | CME | Futures open interest |
| [[cross_asset]] | Yahoo Finance | VIX, DXY, oil, gold, copper, equities |
| [[macro_calendar]] | ForexFactory | High-impact macro events |
| [[substack]] | RSS | Published research memos |

## Signal Computation

These modules transform raw data into normalized signals in [-1, 1] or z-scores.

| Module | Signal | Normalization |
|--------|--------|---------------|
| [[rate]] | Yield spread direction | Robust MAD Z-score |
| [[cot]] | Positioning extremity | 3-year percentile |
| [[volatility]] | Vol regime | Empirical CDF rank |
| [[open_interest]] | OI flow | Z-score of change |
| [[special]] | Pair-specific shocks | Context-dependent |

## Core Logic (The 3 Layers)

These are the most important files in the entire system.

| Module | Layer | Output |
|--------|-------|--------|
| [[layer1_gate]] | Regime Gate | NEUTRAL / BULLISH / BEARISH + invalidated flag |
| [[layer2_directional]] | Directional Signal | LONG / SHORT / NEUTRAL + conviction (1–5) |
| [[layer3_execution]] | Timing & Entry | Entry timing, stop level, position size |

## Regime Classification

| Module | Purpose |
|--------|---------|
| [[classifier]] | Maps gate output to UI metadata (colors, labels) |
| [[composite]] | Aggregates signals into composite score |
| [[confidence]] | Computes model confidence from composite alignment |

## Validation & Backtest

| Module | Purpose |
|--------|---------|
| [[validation_engine]] | Scores T+5/T+20 directional accuracy |
| [[validation_aggregate]] | Computes per-pair win rates, Brier scores |
| [[backtest]] | Historical replay engine |
| [[ledger]] | Alpha ledger tracking |

## Backfill

| Module | Purpose |
|--------|---------|
| [[simulation_engine]] | Walk-forward historical simulation (17k+ calls) |
| [[batch_validation_backfill]] | Fast batch T+5/T+20 validation |
| [[batch_validation_stats]] | Fast aggregate stats computation |
| [[fred_historical]] | Bulk FRED yield fetcher |

## Database

| Module | Purpose |
|--------|---------|
| [[writer]] | **ALL Supabase writes go through here** |

## Scheduler

| Module | Purpose |
|--------|---------|
| [[orchestrator]] | Prefect daily flow: fetch → compute → classify → write → brief |

## Shared Utilities

| Module | Purpose |
|--------|---------|
| [[math_utils]] | Robust MAD Z-score, hysteresis, empirical CDF |
| [[types]] | Central dataclasses: SignalRow, RegimeCall, etc. |
| [[calendar]] | Trading day arithmetic (skips weekends) |

## Connections
- Inputs to pipeline: external APIs (FRED, Yahoo, CFTC, CME)
- Pipeline outputs: [[Database]] tables (`signals`, `regime_calls`, `validation_log`)
- Pipeline consumes: [[Mathematics]] (Z-scores, percentiles, Brier scores)
- Pipeline tested by: 219 pytest cases
