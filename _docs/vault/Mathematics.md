# Mathematics Hub

> Every formula used in the FX Regime Lab, why it was chosen, and where it is applied.

## Normalization & Statistical Methods

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[Z-Score]] | Standardize signals to common scale | [[rate]], [[volatility]], [[math_utils]] |
| [[MAD Normalization]] | Outlier-resistant alternative to std dev | [[math_utils]], [[rate]] |
| [[Empirical CDF Rank]] | Percentile ranking without distribution assumptions | [[volatility]] |

## Signal Aggregation

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[Composite Score]] | Weighted combination of all signals | [[composite]] |
| [[Dynamic Betas]] | Adapt weights to recent signal performance | [[composite]] |

## Regime Classification

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[Hysteresis Tiers]] | Prevents regime flickering near thresholds | [[layer1_gate]] |
| [[Rolling Z-Score]] | Detects regime changes vs static level bias | [[layer1_gate]] |

## Directional Scoring

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[Conviction Multiplier]] | Penalizes crowding and misalignment | [[layer2_directional]] |
| [[Marcus Invalidation]] | Vetoes signals with fundamental clashes | [[layer1_gate]], [[layer2_directional]] |
| [[COT Percentile]] | Measures positioning extremity | [[cot]] |

## Execution & Risk

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[RVOL Rank]] | Realized volatility percentile for sizing | [[volatility]], [[layer3_execution]] |
| [[MIE Proxy]] | Maximum Intraday Excursion for stop levels | [[layer3_execution]] |

## Validation Metrics

| Concept | Why It Matters | Used In |
|---------|---------------|---------|
| [[Brier Score]] | Probabilistic calibration metric | [[validation_engine]], [[validation_aggregate]] |
| [[Sharpe-Like Ratio]] | Return per unit risk from log-returns | [[validation_aggregate]] |
| [[Max Drawdown]] | Peak-to-trough loss in basis points | [[validation_aggregate]] |

## Why These Methods Only

The model uses **deterministic arithmetic transformations only**. No ML, no neural nets, no black boxes.

**Rationale:**
1. **Explainability:** Every signal can be traced to a macro variable. A PM can ask "Why LONG?" and get a precise answer: "Rate z-score is +1.2, COT is at 97th percentile short, vol is compressing."
2. **No overfitting:** Arithmetic transformations don't memorize noise. They measure real macro relationships.
3. **Institutional credibility:** Discretionary macro funds use these exact methods. The model speaks their language.
4. **SSRN-ready:** Every formula is publishable. No proprietary ML architecture to explain.

## Connection to Academic Rigor

| Method | Academic Foundation |
|--------|---------------------|
| Robust MAD Z-score | Huber (1981), robust statistics |
| Hysteresis classification | Schmitt trigger analogy, control theory |
| Brier score | Brier (1950), probabilistic forecasting |
| Empirical CDF | Non-parametric statistics, no distribution assumptions |
| Log-return in bps | Standard quant finance convention |
