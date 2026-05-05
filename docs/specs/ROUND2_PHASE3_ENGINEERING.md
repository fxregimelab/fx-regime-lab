# Engineering Blueprint: Round 2, Phase 3 (Layer 3 Refactoring)

## Objective
Implement the Layer 3: Timing & Entry logic as defined by Chamber 1. This layer provides the final "Execution HUD" outputs: Entry Recommendation, Position Sizing, and Stop Placement.

## System Architecture (Xavier & Elias)

### 1. New Module Structure
- `pipeline/src/logic/layer3_execution.py`: The core Layer 3 engine (Vol Rank, Skew Alignment, Timing/Sizing/Stop Logic).
- `pipeline/src/signals/volatility.py`: Update to support 3-year (756-day) realized vol history for ranking.

### 2. Data Flow
1. **Inputs**: Layer 2 Bias ($b$) and Conviction ($c$), Realized Volatility ($\sigma^{(21)}_t$), Risk Reversal ($RR_t$), ADR, MIE.
2. **Vol Engine**: Calculate $q^{\sigma}_t$ (empirical CDF) over a 3-year (756-day) window.
3. **Skew Engine**: Normalize $RR_t$ and calculate skew-bias alignment $A_t$ and reversal flag $R_t$.
4. **Execution HUD**: 
    - Determine `ENTER` vs `WAIT` (Marcus Rule).
    - Determine `FULL` vs `HALF` size (Lena Rule + Chen Dampener).
    - Calculate `Stop Level` (max of 1.5x ADR or MIE).

## Implementation Standards (Viktor & Sasha)

### 1. Mathematical Accuracy
- Ensure the 3-year volatility history is calculated without look-ahead bias.
- Implement the MIE (Maximum Adverse Excursion) proxy correctly for both Long and Short positions.
- Use `double precision` for all bps and price calculations.

### 2. Strict Typing
- Update `pipeline/src/types.py` to include `Layer3ExecutionOutput`.
- Ensure `layer3_execution.py` is 100% `mypy` strict.

### 3. Database Sync
- Audit `regime_calls` to ensure it can store `entry_timing`, `position_size`, and `stop_level`. (Migration needed if missing).

## Migration Plan (Elias)
- Add `entry_timing` (TEXT), `position_size` (TEXT), and `stop_level` (FLOAT) to `regime_calls`.
- Add `realized_vol_rank` (FLOAT) and `skew_alignment` (INT) to `signals`.

---
**Status:** Ready for Delegated Execution (Phase 4).
