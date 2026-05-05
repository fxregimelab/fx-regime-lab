# Engineering Blueprint: Round 2, Phase 2 (Layer 2 Refactoring)

## Objective
Implement the Layer 2: Directional Signal logic as defined by Chamber 1. This refactor focuses on the interaction between Layer 1/2 Rate signals and Layer 2 COT positioning to produce a weighted `conviction` and a risk-aware `directional_bias`.

## System Architecture (Xavier & Elias)

### 1. New Module Structure
- `pipeline/src/logic/layer2_directional.py`: The core Layer 2 signal logic (Positioning Percentile + Conviction Engine).
- `pipeline/src/signals/cot.py`: Refactor to use a strict 156-week (3-year) rolling window for percentiles.

### 2. Data Flow
1. **Inputs**: Layer 1 Rate scores ($z_T, z_S$), Raw COT positioning, Historical COT series.
2. **Percentile Engine**: Calculate $\pi_t$ (inclusive rank) over a 156-week window.
3. **Crowding Engine**: Identify $F_{\mathrm{crowd}}$ and calculate penalty $p_{\mathrm{crowd}}$ and veto $\chi_{\mathrm{neutral}}$.
4. **Conviction Engine**: Combine Rate composites with $m_{\pi}$ and $p_{\mathrm{crowd}}$ to produce a score $C \in [1, 5]$.
5. **Bias Logic**: Determine `Long`, `Short`, or `Neutral` following the Marcus B (Clash Veto) rule.

## Implementation Standards (Viktor & Sasha)

### 1. Mathematical Accuracy
- Ensure the 156-week window handles missing weeks by looking back at the last available report without look-ahead bias.
- Implement the crowding ramp ($\phi$) smoothly to distinguish between 90th and 100th percentiles.

### 2. Strict Typing
- Update `pipeline/src/types.py` to include `Layer2DirectionalOutput`.
- Ensure `layer2_directional.py` is 100% `mypy` strict.

### 3. Verification
- Unit tests for:
    - Positioning/Rate alignment (High conviction).
    - Positioning/Rate clash (Neutral/Low conviction).
    - Extreme crowding ($\pi > 97$) (Neutral Veto).
    - 3-year window calculation verification.

---
**Status:** Ready for Delegated Execution (Phase 4).
