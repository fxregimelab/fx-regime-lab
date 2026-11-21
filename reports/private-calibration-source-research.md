# Private calibration and portfolio replay: independent source review

Reviewed 1 October 2026 and updated after inspection of `docs/PRIVATE_CALIBRATION_PORTFOLIO_CONTRACT.md`, revision 2, `pipeline/src/private_desk/engine.py`, and the focused private-desk engine tests. This is a bounded methodological and source review. It uses first-party publications, research papers and regulator material. It does not qualify a strategy, certify a checker gate, reconstruct an account, or authorize a broker, database, runtime, commit, deployment or release action.

## Decision

Revision 2 and the inspected implementation align current qualification to the selected **policy + direction + strength bucket**. `_calibrate` receives rows already limited to the selected policy, filters those rows to the candidate direction, and then builds `matching` from that same-direction set using the candidate strength bucket. Its `len(matching) >= 20` condition is therefore an exact joint-cell floor; the separate 40-direction condition is an additional marginal floor. The original marginal-count criticism was incorrect.

The second original finding was valid for revision 1 and has been repaired. Current qualification looks up the selected policy's held-out direction and strength cell, applies `_calibration_check` to that cell, and passes that same cell's summary and sample count to `_positive_ev_for_policy`. The cell needs at least 100 matured held-out predictions, and another direction or strength bucket cannot supply its positive-return evidence.

The contract is now internally coherent as a deterministic **research replay**. Its portfolio language also makes several important limits explicit: the two-position cap, currency-occupancy rule and full-horizon occupancy are assumptions; the close-date R curve excludes unrealised losses; and no account capital or leverage is assumed. Those statements should remain.

Five research limits remain material:

- Direction conditioning reduces one known pooling problem. It does not prove a positive edge. Calibration asks whether events forecast near probability `p` occur near frequency `p`; economic value also depends on the size and timing of gains and losses, costs, selection and sampling uncertainty. A calibrated 60% win probability can still have negative expected R when losses are larger than wins. A positive held-out sample mean is evidence from this sample, not proof of a stable future premium.
- Chronological order is necessary, but it does not by itself resolve overlapping-label leakage, serial dependence or repeated policy selection. The replay must prove that every feature and full label interval used for training or calibration ends before the next cohort begins, with the declared embargo applied to actual timestamps. The existing “changed future outcomes cannot change prior selection” test is useful, but it tests one form of outcome leakage rather than all temporal dependence.
- The realised-close R curve is not an account-equity curve. It cannot establish account drawdown, margin sufficiency, liquidation survival or worst intrahorizon loss because it has no capital base, leverage, monetary position size, account currency, daily or intraday marks, financing, cash flows or broker liquidation rules.
- The held-out folds now govern whether the current candidate qualifies. They are valid out-of-training evidence, but they are no longer an untouched final evaluation once their results are used as a decision gate. Any stronger predictive claim needs a later, method-frozen evaluation period that was not used to set, repair or approve these gates.
- Positive net R remains conditional on the stated spread, slippage and holding-cost assumptions. Revision 2 expressly adds no broker-fill, source-cost or executable-price evidence. Passing the replay cannot establish executable profitability until those inputs are independently sourced and tested.

### Superseded review history

The first review of revision 1 raised two findings. The first alleged that separate direction and bucket floors did not guarantee an exact joint-cell sample. Code inspection disproved it: the bucket match is calculated only after selected-policy and direction filtering. The second found that held-out positive-return evidence could come from another strength bucket in the same direction. The coordinator accepted that finding; revision 2 and the inspected implementation now require the exact policy-direction-strength held-out cell with at least 100 matured predictions. Neither finding remains open against revision 2.

## Probability evidence: what the metrics establish

Brier's original score is the mean squared error between a stated probability and a binary outcome. Gneiting and Raftery place the quadratic/Brier score within the class of proper scoring rules: in expectation, honest probabilities receive the best score. This makes Brier a sound forecast-comparison measure. It does not make a finite set of forecasts “calibrated” by itself, and it does not establish trading utility. [Brier (1950), *Verification of Forecasts Expressed in Terms of Probability*](https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.xml) · [Gneiting and Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*](https://doi.org/10.1198/016214506000001437)

Calibration is a joint property of issued forecasts and realised events. Gneiting, Balabdaoui and Raftery distinguish calibration from sharpness, where sharpness means issuing probabilities that differ meaningfully from an unconditional base rate. A reliability display and a proper score answer related but different questions; neither should be reduced to a single pass label. [Gneiting, Balabdaoui and Raftery (2007), *Probabilistic forecasts, calibration and sharpness*](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf)

The contract's Brier comparison should therefore retain, for every candidate:

- the exact forecast target and success definition;
- the exact joint conditioning cell: policy, BUY/SELL direction and predeclared strength bucket;
- the joint-cell sample count and its event base rate;
- candidate and reference Brier scores on the same held-out rows;
- the rule used to construct the reference forecast using information available before those rows;
- a reliability table or plot with bin boundaries, count, mean forecast and realised frequency in every bin;
- uncertainty that respects repeated and overlapping observations, rather than treating every row as independent.

The fixed `ECE <= 0.10` gate is not self-interpreting. Expected calibration error depends on bin count, boundaries, weighting and norm. Nixon et al. show that those choices can materially change conclusions and rankings. The report must freeze and disclose the ECE definition; it should show the underlying reliability counts and a sensitivity view rather than treat `0.10` as a universal calibration threshold. [Nixon et al. (2020), *Measuring Calibration in Deep Learning*](https://arxiv.org/abs/1904.01685)

The 100-prediction exact held-out-cell floor, 40-direction calibration floor and 20-trade exact calibration-cell floor are governance choices, not evidence that the estimator is precise enough. With overlapping 3/5-day outcomes and repeated calls, the effective information can be materially smaller than the row count. Approximate intervals that assume independent observations do not resolve that dependence. The contract already acknowledges this limit; the dashboard and report should show it next to every interval.

### Why direction conditioning still does not prove edge

Splitting BUY from SELL is a valid repair when their base rates or payoff distributions differ. It only answers whether the historical forecast frequency is more coherent within each side. It does not show that the forecast beats a usable alternative after cost, nor that the return distribution is attractive.

For candidate qualification, keep these statements separate:

1. **Probability quality:** held-out Brier score and reliability for the exact joint cell.
2. **Economic sample evidence:** net R distribution for that same joint cell, including count, mean, median, loss tail and the declared cost model.
3. **Selection evidence:** all twelve fixed trials, the training-only selection rule and every subsequent reuse of calibration or held-out results.
4. **Future claim:** none. Passing the historical gates is not a promise that the edge persists.

Testing twelve policies creates a selection problem even when each fold selects from training only. White's Reality Check was developed for the case where the best reported rule is chosen after searching many alternatives; ordinary performance comparisons can overstate evidence when selection is ignored. The contract correctly says approximate intervals do not resolve selection risk. It should also show the complete trial family and avoid describing the selected policy's unadjusted interval as selection-adjusted evidence. [White (2000), *A Reality Check for Data Snooping*](https://doi.org/10.1111/1468-0262.00152)

## Chronology, overlap and leakage

The official scikit-learn documentation says ordinary cross-validation is inappropriate for time-ordered data because it can train on future observations and evaluate on the past. Its time-series splitter also exposes a `gap` specifically to exclude observations between train and test. This supports chronological folds and an embargo, but the library does not know this desk's label intervals. [scikit-learn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

Bergmeir, Hyndman and Koo show why broad slogans about time-series cross-validation are insufficient: standard K-fold evaluation can be valid in a narrower autoregressive setting when model errors are uncorrelated. That condition should not be presumed for overlapping FX holding returns. [Bergmeir, Hyndman and Koo (2018), *A note on the validity of cross-validation for evaluating autoregressive time series prediction*](https://robjhyndman.com/publications/cv-time-series/)

For this contract, a defensible replay must prove all of the following from actual timestamps:

- no training label path overlaps calibration or held-out time;
- no calibration label path overlaps held-out time;
- selection, probability fitting, bucket assignment and benchmark estimation use only the cohort allowed for each operation;
- the embargo is at least as long as the maximum feature and label contamination window it is meant to block;
- later outcomes cannot alter earlier selection, ranking, bucket boundaries, probability estimates or eligibility;
- repeated calls whose holding paths overlap remain identified as dependent observations in uncertainty reporting.

The portfolio rule that occupies capacity for the full declared horizon is helpful for deterministic selection. It does not repair statistical overlap among the labels used to estimate calibration or expected return. These are separate issues and should have separate tests.

## Pair dependence and portfolio assumptions

The rule “at most two open positions, with no currency repeated” is a clear concentration constraint. It is not a correlation estimate, covariance model, hedge ratio or stress test. The BIS reports that the US dollar was on one side of about 90% of all FX trades in April 2022, illustrating its vehicle-currency role. In this seven-pair desk, the six USD pairs also share a visible dollar leg. That common label justifies caution; it does not tell us the sign, magnitude or stability of their return dependence. [BIS Quarterly Review (December 2022), *The global foreign exchange market in a higher-volatility environment*](https://www.bis.org/publications/qr-202212/global-foreign-exchange-market-higher-volatility-environment)

The ECB's study of more than ten years of currency data finds that correlation forecasts differ across option-implied and return-based methods, and combined forecasts performed best in its application. The practical point is modest: cross-currency dependence is an empirical, time-varying quantity that requires data and a declared estimator. A currency-name occupancy rule cannot substitute for it. [Castrén and Mazzotta (2005), *Foreign exchange option and returns based correlation forecasts: evaluation and two applications*](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp447.pdf)

The replay should label its three controls exactly:

| Rule | What it does | What it does not establish |
|---|---|---|
| Maximum two open positions | Caps simultaneous count and gross research-risk units | Optimal capacity, leverage, diversification or loss bound |
| No repeated currency | Avoids obvious same-currency stacking | Pair correlation, net factor exposure or hedge effectiveness |
| Full-horizon occupancy | Gives deterministic, conservative slot usage when intraday exit order is unknown | Actual capital release, broker margin use or opportunity cost |

Useful descriptive additions, without turning the replay into a fitted portfolio model, are: simultaneous exposure by currency, number of blocked calls by rule, pair and currency concentration, worst same-close aggregate R, and results under the predeclared zero-return same-day-exit control. Any empirical correlation or stress estimate would be a new method requiring its own frozen window, estimator and out-of-sample review.

## Realised R versus account and mark-to-market risk

The contract is correct to call its output a close-date realised R ledger. One R is an abstract research-risk unit. Without an invariant conversion from R to money and an account capital path, summing R does not create an account return series.

The CFTC's retail-FX advisory explains that OTC forex uses margin, leverage amplifies gains and losses, adverse movement can require additional funds or closure, and losses can exceed the initial deposit. The CFTC's retail-FX final rule also requires account profitability calculations to include realised and unrealised gains and losses plus fees, commissions and other charges. Both sources show why closed-trade profit alone is insufficient for account-risk claims. [CFTC, *Eight Things You Should Know Before Trading Forex*](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html) · [CFTC retail-FX final rule, 75 FR 55410](https://www.cftc.gov/LawRegulation/FederalRegister/FinalRules/2010-21729.html)

The report and authenticated dashboard must therefore avoid `portfolio drawdown` or `account drawdown` as an unqualified label. Use `realised-close R drawdown`, and keep this statement beside it:

> This curve adds closed-trade research R on each recorded close date. It excludes open-position marks, intraday adverse movement, margin, leverage, financing, cash flows and broker liquidation. It is not an account-equity drawdown or proof that an account could have carried the positions.

Summing simultaneous closes before calculating the curve removes arbitrary within-date close ordering. It still cannot reveal an intraday margin breach, the order of losses and gains during that date, or the maximum adverse excursion before close. The zero-return positive control tests one ambiguity in same-date exits; it does not reconstruct a marked account.

## Revision 2 disposition and open research

The two conditioning findings have been disposed of: the first was disproved by the explicit filtering chain, and the second was accepted and repaired. They should not block revision 2.

The remaining requirements concern the strength of any claim made from the replay:

1. Freeze and disclose the ECE formula, bins, weighting and norm; show per-bin counts and realised frequencies. Keep Brier, calibration diagnostics and economic return evidence distinct.
2. Prove feature/label interval separation and embargoes from timestamps at every training/calibration/held-out boundary. Keep overlapping observations visible when forming uncertainty intervals, and do not describe independence-based approximate intervals as dependence-adjusted.
3. Preserve a later method-frozen evaluation period that is untouched by trial selection, gate repair and candidate qualification before making a stronger out-of-sample performance claim. The present held-out cells are qualification evidence, not an untouched final test once the gates consume them.
4. Keep executable cost and fill qualification open. Positive R is conditional on the replay's assumed spreads, slippage, holding costs, next-open convention and OHLC ordering; it is not broker execution evidence.
5. Continue to label max-two, no-repeated-currency and full-horizon occupancy as fixed counterfactual assumptions. Do not call them correlations, covariance controls, diversification estimates or account rules.
6. Continue to label the curve `realised-close R drawdown` and preserve the full account-risk exclusion above. Do not infer account equity, margin survival or deployable position sizing.

## Source register

| Topic | Direct source | Material use in this review |
|---|---|---|
| Binary probability score | [Brier 1950, AMS](https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.xml) | Defines squared probability error for binary events. |
| Proper scoring rules | [Gneiting and Raftery 2007, JASA](https://doi.org/10.1198/016214506000001437) | Explains why proper scores reward honest probabilistic forecasts. |
| Calibration and sharpness | [Gneiting, Balabdaoui and Raftery 2007, JRSS B author PDF](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf) | Separates calibration from information concentration and forecast ranking. |
| ECE sensitivity | [Nixon et al. 2020, arXiv](https://arxiv.org/abs/1904.01685) | Shows dependence on class conditioning, bins, weighting and norm. |
| Ordered splitting | [scikit-learn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | Official documentation for time ordering and a train/test gap. |
| Time-series CV conditions | [Bergmeir, Hyndman and Koo 2018](https://robjhyndman.com/publications/cv-time-series/) | Shows validity depends on model and error-dependence conditions. |
| Search/selection risk | [White 2000, Econometrica](https://doi.org/10.1111/1468-0262.00152) | Establishes the data-snooping problem when comparing many rules. |
| Dollar concentration | [BIS Quarterly Review, December 2022](https://www.bis.org/publications/qr-202212/global-foreign-exchange-market-higher-volatility-environment) | Documents the dollar's vehicle role and prevalence in FX trading. |
| FX correlation estimation | [ECB Working Paper 447](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp447.pdf) | Treats cross-currency correlation as an estimated and forecast quantity. |
| Margin and open-risk consequences | [CFTC retail-FX advisory](https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html) | Explains margin, leverage, additional-funds and loss risks. |
| Realised plus unrealised account result | [CFTC retail-FX final rule, 75 FR 55410](https://www.cftc.gov/LawRegulation/FederalRegister/FinalRules/2010-21729.html) | Requires realised and unrealised results and charges in the regulator's account-profit calculation. |

## Review boundary

This report supplies evidence for the coordinator's manual leaf-1 G1 review. It does **not** mark G1 passed, does not represent automated checker certification and does not close R4 or R1-R5. The revision 2 contract, filtering and qualification code paths, and focused test definitions were inspected read-only; the tests were not executed by this reviewer. No live data, strategy output, source capture, browser dashboard or account statement was inspected.
