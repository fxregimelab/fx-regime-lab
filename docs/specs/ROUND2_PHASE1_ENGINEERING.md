# Engineering Blueprint: Round 2, Phase 1 (Layer 1 Refactoring)

## Objective
Implement the Layer 1: Regime Gate logic as defined by Chamber 1. This involves refactoring the existing Python pipeline to handle the new deterministic classifier, statistical thresholds, and the `INVALIDATED` gate.

## System Architecture (Xavier & Elias)

### 1. New Module Structure
- `pipeline/src/logic/layer1_gate.py`: The core deterministic classifier.
- `pipeline/src/logic/math_utils.py`: Vectorized Z-score, momentum, and hysteresis calculations.
- `pipeline/src/models/regime_enums.py`: Enums for discrete regime labels per pair.

### 2. Data Flow
1. **Fetchers**: Retrieve raw data ($y^{\tau}$, policy rates, growth surprises).
2. **Calculators**: Compute $Z_t$, $M_t$, $\Delta\pi$, and $d_t$.
3. **Classifier**: Apply Dr. Aris' priority rules and Lena's hysteresis.
4. **Gate**: Apply Marcus' invalidation logic.
5. **Writer**: Commit the full state vector ($REGIME, INVALIDATED, Z_t, M_t, \pi, d_t$) to Supabase.

## Implementation Standards (Viktor & Sasha)

### 1. Strict Typing
- Use `TypedDict` for the output of each layer.
- Ensure 100% `mypy` coverage for the new logic files.
- No `Any` types allowed in the math core.

### 2. Resilience
- Implement explicit `None` handling for stale data points (Marcus' Invalidation Rule 3.3).
- Use exponential backoff for Supabase writes.

### 3. Verification
- Unit tests for each regime transition (e.g., `test_carry_to_collapse_transition`).
- Verification that the `INVALIDATED` flag correctly suppresses directional bias in the data object.

## Supabase Schema Sync
- Ensure the `signals` and `regime_calls` tables match the fields used in the logic. (Already established in Round 1).

---
**Status:** [COMPLETE]
