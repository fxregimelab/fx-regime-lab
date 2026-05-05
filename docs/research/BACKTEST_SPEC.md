# BACKTEST_SPEC.md

## Objective
To prove that Layer 1 Regime Gating materially improves Layer 2 directional accuracy.

## Scope
- **Timeframe:** 2018 – Present.
- **Universe:** EUR/USD, USD/JPY, USD/INR.
- **Data Source:** FRED (Rates), CFTC (COT), yfinance (Price).

## Methodology
1.  **Reconstruction:** Rebuild daily signals for the last 7 years using historical look-backs for percentiles and Z-scores.
2.  **Un-gated Baseline:** Calculate directional accuracy of Layer 2 signals (Rates + COT) without Layer 1 filters.
3.  **Gated Strategy:** Apply Layer 1 Regime filters (e.g., "Only go Long if Regime == Carry").
4.  **Comparison:** Measure Delta in Win Rate, Sharpe Ratio, and Maximum Drawdown.

## Verification
- **Adversarial Audit:** Lena (Quant Researcher) must verify the look-ahead bias is zero.
- **System Audit:** Elias (Data Architect) must verify data point consistency between backtest and live pipeline.
