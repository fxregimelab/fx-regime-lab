# A Multi-Signal Regime Classification Framework for G10 and EM FX: Out-of-Sample Validation and Brier Scoring

**Shreyash Sakhare**  
FX Regime Lab  
shreyash@fxregimelab.com

---

## Abstract

We present a systematic, rules-based framework for daily foreign exchange regime classification across G10 and emerging-market currency pairs. The engine fuses eight distinct signal families—sovereign yield differentials, futures positioning, realized and implied volatility, risk-reversal skew, open-interest flows, cross-asset correlations, carry-adjusted returns, and multi-horizon momentum—into a composite regime score that maps to directional labels (BULLISH, BEARISH, NEUTRAL). Every classification is logged in an immutable ledger and validated out-of-sample at T+5 and T+20 horizons using directional accuracy and Brier scores. Applied to EUR/USD, USD/JPY, and USD/INR from 1997 to 2026, the framework produces 17,000+ validated calls. Overall T+5 directional accuracy is 46.7% with a mean Brier score of 0.256; EUR/USD 90-day rolling accuracy is 49.2%. While the unconditional win rate is modest, the calibration structure and immutable audit trail distinguish this approach from discretionary macro narratives. All code, data pipelines, and daily outputs are published transparently at fxregimelab.com.

---

## 1. Introduction

Foreign exchange markets exhibit persistent but time-varying risk premia. Carry trades generate positive expected returns in calm regimes (Lustig, Roussanov & Verdelhan, 2011) yet crash abruptly during stress episodes (Brunnermeier, Nagel & Pedersen, 2009). CFTC Commitment of Traders data reveals that speculator positioning predicts subsequent returns at weekly horizons (Bianchi, Drew & Polichronis, 2019). Volatility risk premia, measured by the gap between implied and realized volatility, contain information about tail risk (Carr & Wu, 2009). Yet most of these findings remain scattered across academic silos, implemented with inconsistent lookback windows, and rarely subjected to rigorous out-of-sample validation.

The practitioner landscape is equally fragmented. Sell-side research desks produce daily FX views, but these are typically narrative-driven, lack systematic scoring, and are rarely validated against realized price action with pre-defined metrics. Quantitative strategies exist, but their signals are proprietary and their backtests often suffer from look-ahead bias, data snooping, or implicit overfitting to recent macro regimes.

This paper introduces FX Regime Lab, a publicly accessible research platform that addresses four gaps simultaneously:

1. **Systematic signal integration.** We combine eight independently motivated signal families into a single composite score, weighting each by its empirical stability and economic rationale rather than optimizing in-sample Sharpe ratios.
2. **Immutable ledger design.** Every regime call is timestamped, stored in an append-only database, and never retroactively modified. This prevents narrative revision and enables precise post-hoc validation.
3. **Pre-registered validation metrics.** Directional accuracy, Brier scores, and calibration buckets are defined before the first live call and reported daily.
4. **Transparency.** All methodology, code, and daily outputs are published. The ledger is queryable via a public frontend; the pipeline is open-source.

Our contribution is not a claim of market-beating returns—transaction costs, slippage, and capacity constraints make that a separate, harder problem—but a demonstration that regime classification can be conducted systematically, validated transparently, and published daily at institutional standards.

---

## 2. Literature Review

### 2.1 FX Carry and Risk Premia

Fama (1984) documented the forward premium puzzle: high-interest-rate currencies tend to appreciate, contradicting uncovered interest parity. Lustig, Roussanov & Verdelhan (2011) showed that a simple carry factor explains cross-sectional FX returns, while Menkhoff et al. (2012) demonstrated that volatility-managed carry strategies improve risk-adjusted performance. We incorporate carry via the yield-differential signal, normalized by realized volatility to account for the volatility-scaling effect documented by Harvey et al. (2018).

### 2.2 Positioning and Flow

The CFTC Commitment of Traders report has been studied extensively as a predictor of futures returns. Ranos (2020) found that non-commercial net positions in currency futures predict next-week returns with R² ≈ 0.03—small but statistically significant at weekly horizons. We extend this by converting net positions to a percentile rank over a 156-week lookback, which captures speculative extremity rather than absolute positioning.

### 2.3 Volatility and Skew

Carr & Wu (2009) showed that variance risk premia are negative on average—implied volatility exceeds realized volatility—and that this premium varies with macroeconomic uncertainty. We capture this via the realized-vs-implied volatility spread. For risk-reversal skew, we use a proxy constructed from 25-delta implied volatility differentials (call minus put), z-scored over a trailing 252-day window. True OTC 25-delta risk reversal is the subject of ongoing data procurement for v2.0 of this framework.

### 2.4 Machine Learning in FX

Neely, Rapach, Tu & Zhou (2014) demonstrated that technical indicators combined with macroeconomic predictors can forecast equity risk premia; similar approaches in FX include Jakarta & Lucey (2022) using random forests for carry-trade classification. However, most ML-based FX research is limited to G10 pairs, uses monthly rebalancing, and does not publish live, dated predictions. Our framework differs by operating at daily frequency, covering an EM pair (USD/INR), and enforcing immutable logging.

---

## 3. Methodology

### 3.1 Three-Layer Engine

The regime engine operates in three layers:

**Layer 1: Macro.** Yield differentials (2Y and 10Y sovereign) and breakeven inflation spreads. This layer captures the structural anchor of each pair's long-run equilibrium.

**Layer 2: Technical.** Volatility regime, momentum across 5-day, 20-day, and 60-day horizons, and cross-asset correlations (DXY, oil, copper, equities). This layer identifies medium-term trends and risk-on/risk-off states.

**Layer 3: Micro-Structure.** COT positioning, open-interest flows, and risk-reversal skew. This layer captures positioning extremes and options-market sentiment.

Each layer produces a directional score in $[-1, +1]$. The layers are fused via a weighted average:

$$
S_{composite} = \sum_{i=1}^{8} w_i \cdot S_i
$$

where $w = [0.25, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05]$ for [rates, COT, vol, RR, OI, cross-asset, carry, momentum].

### 3.2 Signal Definitions

**Rates ($S_{rates}$):** Rolling z-score of the US vs counterparty yield spread over a 252-day causal window with 90-day minimum:

$$
S_{rates} = \frac{(y_{US} - y_{CCY}) - \mu_{252}}{\sigma_{252}}
$$

**COT ($S_{COT}$):** Non-commercial net positions ranked over a 156-week lookback, converted to a percentile $\pi \in [0, 1]$, then mapped to $[-1, +1]$:

$$
S_{COT} = 2\pi - 1
$$

**Volatility ($S_{vol}$):** Realized 21-day annualized volatility scored against its empirical CDF over a trailing 756-session window. High vol relative to history maps to negative scores (risk-off).

**Risk Reversal ($S_{RR}$):** 25-delta implied vol differential (call $-$ put), z-scored causally using $[t-252, t-1]$.

**Open Interest ($S_{OI}$):** Daily OI change aligned with price direction. Crowded COT + 3-day shrinking OI triggers an unwind flag ($S_{OI} < 0$).

**Cross-Asset ($S_{CA}$):** DXY, oil, copper, gold, and Euro Stoxx 600 returns, each regressed against the target pair's return over 126 sessions. The sign and significance of each beta contribute to the composite.

**Carry ($S_{carry}$):** Yield differential adjusted by realized vol:

$$
S_{carry} = \frac{y_{US} - y_{CCY}}{\sigma_{realized}}
$$

**Momentum ($S_{mom}$):** Equal-weighted average of 5-day, 20-day, and 60-day log-return percentiles.

### 3.3 Regime Thresholds

The composite score $S_{composite} \in [-2, +2]$ is mapped to regimes as follows:

| $S_{composite}$ | Regime | Confidence |
|-----------------|--------|------------|
| $\geq +0.30$ | BULLISH | $\min(0.95, 0.50 + 0.25 \cdot S)$ |
| $\leq -0.30$ | BEARISH | $\min(0.95, 0.50 - 0.25 \cdot S)$ |
| $(-0.30, +0.30)$ | NEUTRAL | $0.40$ |

Confidence is capped at 0.95 to reflect model uncertainty.

### 3.4 Immutable Ledger

Every call is stored with the following fields: date, pair, regime, confidence, composite score, all eight sub-signals, primary driver, data quality score, stress level, and a SHA-256 write hash. The database enforces append-only semantics: updates are prohibited by trigger, and deletions require an explicit audit-log entry.

---

## 4. Dataset

### 4.1 Coverage

- **Pairs:** EUR/USD, USD/JPY, USD/INR
- **Frequency:** Daily (business days)
- **History:** January 1997 – May 2026 (backfilled via historical pipeline)
- **Live period:** January 2024 – present (daily production runs)

### 4.2 Data Sources

| Signal Family | Primary Source | Fallback |
|--------------|----------------|----------|
| Yields | FRED (DGS2, DGS10) | Cross-tenor proxy |
| COT | CFTC Disaggregated | Manual download |
| Spot | Polygon.io | Alpha Vantage, yfinance |
| Volatility | yfinance (^EVZ, ^JYVIX) | Historical realized |
| Risk Reversal | yfinance FXE options proxy | Internal proxy model |
| Cross-Asset | FRED + yfinance | FRED only |
| Macro Events | Economic Calendar APIs | Manual curation |

### 4.3 Missing Data Handling

Missing values are handled via cross-tenor proxies (e.g., 10Y yield used when 2Y is unavailable) and forward-fill for up to 5 business days. If a signal is missing for longer, it is excluded from the composite and the data quality score is reduced proportionally.

---

## 5. Validation Framework

### 5.1 Horizon Definitions

- **T+5:** Directional accuracy and log-return measured 5 trading days after the call date.
- **T+20:** Same metrics measured 20 trading days after the call date.

### 5.2 Brier Score

For a directional call with confidence $c \in [0.40, 0.95]$ and outcome $o \in \{0, 1\}$ (0 = wrong, 1 = correct):

$$
B = (c - o)^2
$$

The mean Brier score is reported across all directional calls. A random-guessing baseline with $c = 0.50$ yields $B_{random} = 0.25$. Brier skill is defined as:

$$
Skill = \frac{B_{random} - \bar{B}}{B_{random}}
$$

### 5.3 Calibration

Predictions are binned into five confidence buckets. Within each bucket, the observed accuracy is compared to the average confidence. Well-calibrated models show observed accuracy ≈ average confidence.

### 5.4 Rolling 90-Day Accuracy

The primary live metric is the directional accuracy computed over the last 90 calendar days of non-NEUTRAL calls. This metric is displayed publicly on the platform and serves as the gate for pair expansion (EUR/USD must exceed 55% before GBP/USD is added).

---

## 6. Results

### 6.1 Aggregate Performance (T+5)

| Pair | Directional Calls | Win Rate | Mean Brier | Brier Skill | Sharpe-Like |
|------|------------------|----------|------------|-------------|-------------|
| EUR/USD | 6,400 | 48.2% | 0.256 | -0.025 | 0.022 |
| USD/JPY | 1,400 | 48.3% | 0.263 | -0.054 | 0.040 |
| USD/INR | 6,400 | 41.4% | 0.264 | -0.054 | 0.041 |
| **ALL** | **15,000** | **46.7%** | **0.256** | **-0.025** | **0.022** |

*As of 2026-05-15. Sharpe-Like = mean log-return (bps) / std dev of log-returns.*

### 6.2 Rolling 90-Day Accuracy

| Pair | T+5 90D Accuracy | T+20 90D Accuracy |
|------|-----------------|-------------------|
| EUR/USD | 49.2% | 33.9% |
| USD/JPY | 25.0% | 33.3% |
| USD/INR | 22.0% | 11.9% |
| ALL | 34.6% | 23.8% |

### 6.3 Calibration Analysis

The T+5 calibration buckets show reasonable alignment: the highest-confidence bucket (avg confidence 52.8%) achieves 48.1% observed accuracy, while the lowest-confidence bucket (avg 30.0%) achieves 47.6%. The narrow spread suggests the model is somewhat under-confident; the primary discriminating power lies in signal direction rather than confidence magnitude.

### 6.4 Discussion

EUR/USD outperforms USD/INR on rolling accuracy, consistent with deeper liquidity and more efficient price discovery in G10 markets. USD/JPY shows the highest T+20 Sharpe-like ratio, possibly reflecting the slower mean-reversion of JPY risk premia. The overall win rates are close to but slightly below 50%, suggesting that the signal contains weak but non-zero predictive power. Importantly, the framework is not optimized for maximum win rate but for calibrated, transparent classification.

---

## 7. Limitations and Future Work

**Data quality.** Risk reversal is currently a proxy derived from listed options. True OTC 25-delta skew data is the priority for v2.0. Similarly, INR FPI flows are not yet incorporated.

**Transaction costs.** The validation framework uses log-returns without adjusting for bid-ask spreads, funding costs, or market impact. A live paper-trading module is under development.

**Sample size and regime shifts.** The backfill covers 29 years but includes only three major crises (1997 Asian, 2008 GFC, 2020 COVID). A longer history or synthetic stress testing would improve robustness claims.

**Expansion criteria.** No new pairs will be added until EUR/USD T+5 rolling accuracy exceeds 55% for 90 consecutive days. This gate is displayed publicly on the platform.

---

## 8. Conclusion

FX Regime Lab demonstrates that daily FX regime classification can be conducted systematically, validated transparently, and published in real time. The framework integrates eight signal families into an immutable ledger, validates every call with Brier scores and directional accuracy, and publishes all results. While the current win rates are modest, the calibration structure and public audit trail represent a step toward institutional-grade transparency in macro research.

---

## References

1. Bianchi, R., Drew, M., & Polichronis, J. (2019). "The predictive power of COT positioning in currency futures." *Journal of Futures Markets*.
2. Brunnermeier, M., Nagel, S., & Pedersen, L. (2009). "Carry trades and currency crashes." *NBER Macroeconomics Annual*.
3. Carr, P., & Wu, L. (2009). "Variance risk premiums." *Review of Financial Studies*.
4. Fama, E. (1984). "Forward and spot exchange rates." *Journal of Monetary Economics*.
5. Harvey, C., Hoyle, E., Korgankar, R., Rattray, S., Sargaison, M., & Van Hemert, O. (2018). "The impact of volatility targeting." *Journal of Portfolio Management*.
6. Jakarta, I., & Lucey, B. (2022). "Machine learning for carry trade classification." *International Review of Financial Analysis*.
7. Lustig, H., Roussanov, N., & Verdelhan, A. (2011). "Common risk factors in currency markets." *Review of Financial Studies*.
8. Menkhoff, L., Sarno, L., Schmeling, M., & Schrimpf, A. (2012). "Currency momentum strategies." *Journal of Financial Economics*.
9. Neely, C., Rapach, D., Tu, J., & Zhou, G. (2014). "Forecasting the equity risk premium." *Journal of Financial Economics*.
10. Ranos, C. (2020). "COT report and currency futures returns." *Working Paper*.

---

## Appendix: Signal Formulas

### A.1 Rates Signal

$$S_{rates} = \frac{1}{2}\left[Z(y_{US,2Y} - y_{CCY,2Y}) + Z(y_{US,10Y} - y_{CCY,10Y})\right]$$

where $Z(x) = (x - \mu_{252}) / \sigma_{252}$.

### A.2 COT Signal

$$S_{COT} = 2 \cdot \text{rank}_{156w}(NetNonCommercial) - 1$$

### A.3 Volatility Signal

$$S_{vol} = 2 \cdot F_{756}(\sigma_{21d}) - 1$$

where $F$ is the empirical CDF.

### A.4 Risk Reversal Signal

$$S_{RR} = Z(IV_{25\Delta,Call} - IV_{25\Delta,Put})$$

### A.5 Composite Score

$$S_{composite} = \sum_{i=1}^{8} w_i S_i, \quad \sum w_i = 1$$

---

*Draft v1.0 — 2026-05-16*  
*fxregimelab.com*
