# Engineering Blueprint: Round 3 (Validation Engine)

## Objective
Implement the Round 3 Validation Engine to prove the 3-Layer Signal Framework's efficacy using immutable out-of-sample data. This system will track basis point (bps) movement and Brier Scores at T+5 and T+20 horizons.

## System Architecture (Xavier & Elias)

### 1. New Module Structure
- `pipeline/src/validation/engine.py`: Core validation logic (Log returns, Brier scores).
- `pipeline/src/validation/ledger.py`: Append-only interaction with Supabase `validation_log`.
- `pipeline/src/validation/calendar.py`: Trading day logic (T+5/T+20) to handle weekends and holidays.

### 2. Data Flow
1. **Trigger**: Runs daily at 23:00 UTC.
2. **Scanner**: Identify `regime_calls` from D-5 and D-20 that haven't been validated yet.
3. **Pricer**: Fetch NY close spot prices for $S_0$ and $S_h$ from `signals` or `yfinance`.
4. **Calculator**:
    - Compute Log Return: $bps = 10,000 \times \ln(S_h/S_0)$.
    - Map Bias to probability $\mathbf{p}$ (using one-hot 1.0 for now, or L2 continuous score).
    - Determine realized class based on $\epsilon = 5$ bps threshold.
    - Calculate Brier Score.
5. **Ledger**: Append the result to `validation_log`.

## Implementation Standards (Viktor & Sasha)

### 1. Mathematical Rigor
- Use log returns for all bps calculations.
- Ensure "No Look-ahead Bias": Validation must only use data available *after* the horizon has passed.

### 2. Integrity (Ms. Wong Mandate)
- The `validation_log` table will have a unique constraint on `(call_id, validation_date)` to prevent duplicates.
- Implement a `is_superseded` flag rather than deleting or updating existing rows if a correction is needed.

### 3. Pipeline Integration
- Add the validation step to the end of `pipeline/run_daily.sh`.

---
**Status:** Ready for Delegated Execution (Phase 4).
