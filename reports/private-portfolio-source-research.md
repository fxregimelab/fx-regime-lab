# Private FX portfolio controls: source research

Reviewed 1 October 2026. This is a research note for a private, paper-trading portfolio. It does not approve a strategy, provide a probability of profit, promise an entry rate, or authorise broker, database, deployment, release or credential use.

## Decision

Use eight pairs: **EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/JPY, USD/CAD, USD/CHF and EUR/GBP**. USD/JPY is expressly included. Treat 3–5 new entries per week as a planning target, never as a quota. A week with no eligible entry is valid. Keep no more than five positions open, no more than two positions in one measured correlated directional-risk group, and no more than two net one-unit exposures to the same currency.

Pair names are not enough to control concentration. A long EUR/USD position is long EUR and short USD; a long USD/JPY position is long USD and short JPY. Their USD exposures point in opposite directions even though both pair names contain USD. The portfolio therefore needs both signed currency exposure and lagged return correlation. Neither measure turns an offsetting trade into a proven hedge.

The thresholds below are proposed governance limits. The cited research supports measuring common factors, changing correlations, stress behavior, costs and selection risk; it does not establish `0.60`, 60 sessions, five positions or any other desk-specific number as universally optimal.

## Why these controls are needed

Lustig, Roussanov and Verdelhan identify common dollar and carry factors in currency returns. Their result matters here because separate bilateral pairs can load on the same common risk even when their quote conventions differ. The safe implementation is to convert each proposed BUY or SELL into signed pair returns and signed currency legs before judging concentration. [NBER Working Paper 14082, *Common Risk Factors in Currency Markets*](https://www.nber.org/papers/w14082)

The IMF's multi-country hedging study says portfolio risk depends on currency-return covariances and on cross-covariances with the other assets. It also finds that estimated currency relationships can be specific to the period and can change sharply in a crisis. A low historical correlation is evidence about a chosen window, not a permanent diversification property. [IMF Working Paper 10/151, *Currency Hedging for International Portfolios*](https://www.imf.org/external/pubs/ft/wp/2010/wp10151.pdf)

The BIS review of carry, momentum and term-spread strategies finds material tail risk and uneven performance across distress periods. This is a reason to show normal-window and stress-window dependence separately rather than allowing an average correlation to hide a bad state. [BIS Quarterly Review, *FX strategies in periods of distress*](https://www.bis.org/publications/fx-strategies-periods-distress)

Hedging has a price. The BIS finds that demand to hedge dollars and costly intermediary balance sheets can create a premium in forward markets. Its currency-momentum study also finds that transaction costs materially reduce returns and that the currencies selected for trading can be more expensive than the average currency. A hedge should be assessed after the costs of both legs, not credited from a negative gross correlation alone. [BIS Working Paper 590, *The failure of covered interest parity: FX hedging demand and costly balance sheets*](https://www.bis.org/publications/working-paper-590-failure-covered-interest-parity-fx-hedging-demand-and-costly-balance-sheets) · [BIS Working Paper 366, *Currency Momentum Strategies*](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies)

Chronology and full trial disclosure are also necessary. The official `TimeSeriesSplit` documentation warns that ordinary random cross-validation can train on the future and test on the past, and provides a gap between train and test. White defines data snooping as reusing a data set for inference or model selection and tests the best searched model against a benchmark. Novy-Marx shows that combining signed signals can produce severe overfitting even when the underlying signals are random. Harvey, Liu and Zhu show why ordinary single-test significance is inadequate after many financial tests. [scikit-learn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) · [White (2000), *A Reality Check for Data Snooping*](https://doi.org/10.1111/1468-0262.00152) · [NBER Working Paper 21329, *Backtesting Strategies Based on Multiple Signals*](https://www.nber.org/papers/w21329) · [Harvey, Liu and Zhu (2016), *… and the Cross-Section of Expected Returns*](https://doi.org/10.1093/rfs/hhv059)

## Measured portfolio controls

### 1. Freeze the return convention

Use one daily price source, one close timestamp and one missing-day rule for all eight pairs. Record the source timestamp and the observation timestamp. Calculate the pair return as the daily log change in the displayed quote, `log(close_t / close_t-1)`.

For a proposed or open position, define `q = +1` for BUY and `q = -1` for SELL. Its signed return series is `q × pair_return`. This makes positive correlation mean that two positions have tended to gain and lose together under their actual directions.

At a decision on date `t`, every estimate must end at the last fully available common close, normally `t-1`. A same-day partial bar is ineligible. Do not forward-fill a missing price. If fewer than the required aligned observations remain, return `INSUFFICIENT_HISTORY` and apply the conservative grouping rule below.

### 2. Record signed currency exposure

Give every one-unit position `+q` units in the base currency and `-q` units in the quote currency. Examples:

| Position | EUR | USD | JPY |
|---|---:|---:|---:|
| BUY EUR/USD | +1 | -1 | 0 |
| SELL EUR/USD | -1 | +1 | 0 |
| BUY USD/JPY | 0 | +1 | -1 |
| SELL USD/JPY | 0 | -1 | +1 |

Sum the eight currency legs after adding a candidate. Reject the candidate when the absolute net exposure to any single currency would exceed **2.0 one-unit positions**. Gross exposure still equals the number of open positions; offsetting currency legs do not create another slot.

This currency-leg limit and the correlation grouping rule are separate. Passing one does not waive the other.

### 3. Estimate only lagged correlations

For every candidate/open-position pair, calculate Pearson correlation of their signed daily returns over:

- the most recent 60 aligned completed sessions, requiring at least 50 observations;
- the most recent 20 aligned completed sessions, requiring at least 15 observations; and
- a stress sample from the preceding 750 aligned sessions.

For the stress sample, calculate each day's median absolute return across the eight pairs. Select the top 10% of those days using only that preceding 750-session window, then calculate Spearman correlation of the two signed position returns on the selected dates. Require at least 50 aligned stress observations. This stress definition is a fixed portfolio-wide market-movement proxy; it is not a claim that every selected day was a recognised crisis.

Put two positions in the same correlated directional-risk group when **any** available estimate is at least `+0.60`: 20-session Pearson, 60-session Pearson or stress-sample Spearman. Build an undirected graph from those pairwise links; each connected component is one group. A candidate fails if its addition would make a component contain more than **two open positions**.

If the 60-session estimate is unavailable, place the candidate in the same group as every open position that shares a non-zero currency leg in the same direction. If the stress estimate is unavailable, label stress dependence `UNQUALIFIED`; do not use missing stress evidence to grant hedge status. Show all estimates, observation counts and unavailable reasons in the decision record.

Flag instability when the 20- and 60-session Pearson correlations have opposite signs or differ by more than `0.40`. Instability is a warning, not a reason to replace the conservative maximum-correlation grouping rule.

### 4. Keep diversification and hedging distinct

Call a set **diversified in this sample** only when it passes the gross-position, currency-leg and correlated-group limits. This label means measured concentration is bounded under the declared windows. It does not mean losses are independent or capped.

Call a candidate a **research hedge** only when all of these are true:

1. The target currency or existing position to be offset was named before looking at the candidate's later return.
2. The signed 60-session and stress correlations with that target are both at or below `-0.50`, with the observation floors above.
3. A hedge ratio was fitted only on an earlier training window and then held fixed through the evaluation interval.
4. The fixed hedge reduced realised out-of-sample variance or declared tail loss after costs, compared with the same portfolio without the hedge.
5. The result remained directionally consistent in the 20-session sensitivity view.

A research hedge still consumes one of the five slots, still counts toward currency exposure and still faces the two-per-group limit. A negative correlation alone never grants capacity relief.

### 5. Charge the net cost of every leg

For every entry and exit, record the contemporaneous bid and ask, source time, spread, slippage rule and any fee. For positions held across rollover, include the actual or independently sourced financing/rollover charge for each leg and holding day. For forwards, swaps or options, include forward points, cross-currency basis where applicable, option premium and executable spread.

Evaluate a hedge as:

`net hedge benefit = change in the declared loss measure - entry/exit costs - holding costs - derivative costs`.

Costs must be applied to both the original position and the hedge at the size actually tested. If an input is absent, label the net result `UNQUALIFIED_COST`; show gross results separately and do not call the hedge effective or profitable. Do not substitute today's spread for a historical executable spread without labelling it as a sensitivity assumption.

## Portfolio admission rule

At each decision timestamp, process otherwise eligible entries in a frozen order: decision timestamp, then the existing strategy rank, then the fixed pair order shown at the start of this report. Never use later realised return to break a tie.

Admit a candidate only if all of these remain true after adding it:

- the pair belongs to the locked eight-pair universe;
- no duplicate position identity exists;
- the open-position count is at most **5**;
- every correlated directional-risk group has at most **2** positions;
- every absolute net currency exposure is at most **2.0** units;
- all required prices precede the decision and pass the missing-data rule;
- cost status is qualified for any claim made about net return or hedge benefit.

The 3–5 entries-per-week target is reported as observed throughput. It cannot override a failed admission rule, trigger weaker thresholds, or create a trade. Report weekly eligible, admitted and blocked counts with the exact block reason.

## Chronological evaluation and selection control

Use a walk-forward evaluation. For each fold, train on earlier dates, leave an embargo at least as long as the maximum holding/label horizon, and evaluate only on later dates. Every training label must have ended before the embargo begins. Correlation windows, stress thresholds, ranks, hedge ratios, costs and group membership at a decision must be reconstructed from information available then.

Before running the final evaluation, freeze:

- the eight pairs and quote conventions;
- entry and exit definitions;
- the 20/60/750-session windows and all observation floors;
- the `+0.60`, `-0.50`, five-position, two-per-group and two-currency-unit limits;
- the stress-day rule, cost model, missing-data behavior and tie order;
- the benchmark and every performance and loss measure.

Keep a trial registry containing every tested threshold, window, universe, rank, cost assumption and manual rerun, including discarded versions. The final comparison must include the unchanged portfolio logic without the new concentration controls, a no-trade reference, and all searched variants. Apply a family-aware method such as White's Reality Check or a declared false-discovery control when making a superiority claim. If dependence, sample size or implementation prevents a valid adjustment, report results as descriptive and set the superiority decision to `HOLD`.

Reserve one later period that is untouched by threshold choice, repair and approval. Once its result is used to change the method, it becomes development evidence and a new untouched period is required. Random shuffling, selecting the best full-history result, or reporting only the winning variant fails acceptance.

## Exact acceptance and limits

The portfolio-control method is acceptable for historical private research only when all of the following are evidenced:

| Gate | Acceptance condition |
|---|---|
| Universe | Exactly the eight named pairs; USD/JPY present; no additional cross or synthetic pair. |
| Throughput | Weekly eligible/admitted/blocked counts shown; 3–5 is a target only; zero forced entries. |
| Capacity | No timestamp with more than 5 open positions. |
| Group concentration | No timestamp with more than 2 positions in a connected correlated directional-risk group. |
| Currency concentration | No timestamp with absolute net exposure above 2.0 one-unit positions in any currency. |
| Timing | Every input used at `t` has an observation and availability time no later than the declared cutoff before `t`. |
| Correlation | 20-, 60-session and stress estimates, counts and missing reasons saved; conservative fallback applied when history is short. |
| Stress | Stress sample uses the frozen lagged 750-session/top-10% rule and at least 50 aligned stress observations, or is explicitly unqualified. |
| Hedge label | All five research-hedge conditions pass; otherwise use `offsetting exposure` or `unqualified`, not `hedge`. |
| Costs | Entry, exit and holding/derivative costs cover every tested leg; missing cost evidence blocks net-performance and hedge-effectiveness claims. |
| Chronology | Walk-forward folds and embargo prove that features, labels, selection and risk estimates use no future information. |
| Search disclosure | Every tried variant is in the trial registry; the final period was untouched before evaluation. |
| Statistical claim | Any superiority claim uses the full searched family and a declared dependence-aware adjustment; otherwise the result remains descriptive/HOLD. |
| Reproduction | Re-running from pinned inputs produces the same admissions, blocks, exposure vectors, groups, costs and reported metrics. |

Passing these gates means the rules were applied consistently to the pinned history. It does not establish live executability, account-level drawdown, margin safety, a stable hedge, future profitability, or a probability that the 3–5 weekly target will be met.

## Source register

| Topic | Primary source | Use here |
|---|---|---|
| Common currency factors | [Lustig, Roussanov and Verdelhan, NBER Working Paper 14082](https://www.nber.org/papers/w14082) | Supports measuring shared dollar/carry exposure rather than treating pairs as independent names. |
| Hedging, covariance and instability | [Schmittmann, IMF Working Paper 10/151](https://www.imf.org/external/pubs/ft/wp/2010/wp10151.pdf) | Separates portfolio covariance from a hedge and documents period/crisis instability. |
| Stress behavior | [BIS, *FX strategies in periods of distress*](https://www.bis.org/publications/fx-strategies-periods-distress) | Supports separate distress analysis and visible tail limits. |
| Hedging demand and forward-market premium | [BIS Working Paper 590](https://www.bis.org/publications/working-paper-590-failure-covered-interest-parity-fx-hedging-demand-and-costly-balance-sheets) | Shows that hedge demand and intermediary constraints can affect hedge price. |
| Trading costs | [BIS Working Paper 366](https://www.bis.org/publications/working-paper-366-currency-momentum-strategies) | Shows transaction costs materially affect FX strategy returns. |
| Chronological splitting | [scikit-learn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | Official basis for ordered train/test splits and a gap. |
| Data snooping | [White (2000), Econometrica](https://doi.org/10.1111/1468-0262.00152) | Requires testing the searched best model against a benchmark with reuse visible. |
| Multi-signal backtest overfitting | [Novy-Marx, NBER Working Paper 21329](https://www.nber.org/papers/w21329) | Shows severe selection bias from combinations of signed signals. |
| Multiple testing in finance | [Harvey, Liu and Zhu (2016), Review of Financial Studies](https://doi.org/10.1093/rfs/hhv059) | Supports a higher, family-aware evidence bar after many trials. |

## Research boundary and tools

Sources were found and checked on 1 October 2026. The required Agent Reach route was attempted first with `agent-reach doctor --json`, but the executable was not available on this host. Research then used the official web-search/browser tool and direct publisher, central-bank, NBER, IMF and project documentation pages. No credentials, paid or network AI service, package install, live market feed, broker data, code, tests, database, contract, ledger or release state was used or changed.
