# Continuous directional-risk source review

## Decision

For the private desk's 2–5-business-day research horizon, keep the existing lagged daily signed-correlation rule as a conservative **admission control** and add a similarly lagged **business-day holding review**. Call neither one continuous or intraday control.

The daily review may identify correlation drift, a newly oversized connected risk group, or unavailable evidence. It must not invent an executable forced exit, replacement trade, or hedge return. It may support a separate, clearly labelled daily-OHLC development counterfactual under rules and generic costs fixed before inspecting its result. Until executable intraday data, broker terms, order results, financing and two-leg hedge costs exist, actual action and executable return remain unavailable; capacity stays reserved conservatively.

This packet does not validate the exact 60-observation window, 40-match floor, 0.70 threshold, group size of two, or strategy. Those are fixed research choices that need sensitivity and out-of-sample evaluation.

## What the current method establishes

[`correlation.py`](../pipeline/src/private_desk/correlation.py) calculates exact-date daily log-return correlation using observations strictly before the signal date. It excludes a return across a missing weekday or marked gap, requires recent matched observations, returns unavailable for small, stale, invalid or constant samples, and signs raw pair correlation by both proposed trade directions:

`signed correlation = raw pair-return correlation × first trade sign × second trade sign`

That sign operation answers a narrow question: under the stored pair orientations and proposed long/short directions, did the two trades' historical daily profit-and-loss directions tend to move together? Positive signed correlation means concentration. Negative signed correlation is possible offsetting behaviour; it is not proof of a hedge.

The method joins positions when signed correlation is at least 0.70 and applies the group limit to the full connected component. That is deliberately stricter than checking only every pair against every other pair. For example, strong A–B and B–C links place all three in one group even if A–C is weak. The rule should remain explicit because no cited authority sets 0.70 as a universal FX concentration boundary.

## Why correlation must be refreshed and treated cautiously

The Federal Reserve's exchange-rate dependence study finds that currency dependence is not constant, that time-varying parameters can move well outside confidence bands around constant estimates, and that ordinary correlation can miss asymmetric upper- and lower-tail dependence. It also reports distinct yen behaviour in some recession states. This supports a rolling, pair-specific measure and separate stress diagnostics; it does not prove that a 60-day Pearson estimate predicts losses over the next five days. [Federal Reserve, *Exchange Rates Dependence: What Drives It?*](https://www.federalreserve.gov/pubs/ifdp/2009/969/ifdp969.htm)

BIS research adds an important caution: an observed rise in sample correlation during volatile periods can partly be a mechanical consequence of changed volatility, even without a structural change in the underlying relationship. A short-window change should therefore trigger a diagnostic, not a causal claim. [BIS, *Evaluating correlation breakdowns during periods of market volatility*](https://www.bis.org/publ/confer08k.pdf)

A recent BIS review gives a concrete failure of a presumed natural hedge: in April 2025, the historical relationship between the US dollar and risky assets reversed, prompting investors to buy explicit FX hedges. The same review notes that hedging costs had affected hedge ratios. This supports monitoring sign changes and keeping correlation-based offsets separate from actual hedges. [BIS, *Global FX markets when hedging takes centre stage*](https://www.bis.org/publications/qr-202512/global-fx-markets-when-hedging-takes-centre-stage)

The Basel Committee says market-risk stress tests should cover concentrated positions, illiquidity and price gaps, one-way markets, and significant shifts in correlations. It also says shocks should reflect the time needed to hedge or manage risk in severe conditions. This supports stress tests beyond a rolling mean correlation. It is a banking standard, not a direct rule for this private research account. [Basel Framework, SRP20.17–20.22](https://www.bis.org/committees/bcbs/basel-framework/standard/srp/20/inforce/2019-12-15/published/2019-12-15)

## Bounded daily control

Use one declared daily decision clock and the same pair orientation, price field, market calendar and source-vintage rules for every pair. At each checkpoint:

1. Identify positions whose planned horizons still include that business day. Do not use an eventual realised exit to decide whether they were active earlier.
2. Recompute every active pair-to-pair correlation using only matched returns available before the checkpoint. A return labelled with that day is usable only if its common close and receipt were already witnessed before the decision time.
3. Apply the stored trade signs, rebuild connected components, and record every raw correlation, signed correlation, sample count, last matched date, source cut-off and status.
4. Classify the observation as `WITHIN_LIMIT`, `GROUP_BREACH`, or `UNAVAILABLE`. Keep unavailable distinct from a low correlation.
5. If evidence is unavailable, reserve existing capacity and block a new admission whose safety depends on the missing edge. Do not assume independence, substitute an older correlation without a stated stale-data rule, or turn a missing value into zero.
6. If a held group newly exceeds two, report a holding-period breach. Do not rewrite the original admission decision, retrospectively choose the best exit, or release capacity for a replacement call. A separately labelled development counterfactual may model the predeclared response described below.

The current daily audit is a useful diagnostic. A stricter forward control still needs a predeclared response policy. Until exit execution is qualified, the live/action state is `BREACH_OBSERVED_ACTION_UNQUALIFIED`, not “forced exit avoided loss.” A modelled sensitivity is a separate development result and cannot change that state.

Basel's modellability rules are useful as a conservative analogy: they require representative, verifiable real-price observations, recognize reporting lags and treat sparse evidence as non-modellable. They do not directly govern this research account, but they support keeping stale, sparse or unverified inputs unavailable rather than forward-filling them. [Basel Framework, MAR31](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/31/inforce/2023-01-01/published/2020-03-27)

### Daily is not continuous

Basel requires daily limit reporting and separately calls for intraday limit-use and breach reports when a bank is actively trading intraday. The FX Global Code likewise calls for accurate, timely risk monitoring and describes real-time credit and permission controls in prime brokerage. These sources make the distinction clear: an end-of-day or once-per-business-day recomputation cannot establish uninterrupted limit compliance. [Basel Framework, MAR12.5](https://www.bis.org/baselframework/BaselFramework.pdf) [FX Global Code, Principles 26, 27, 30 and 41](https://www.globalfxc.org/uploads/fx_global.pdf)

For this 2–5-day method, label the result `DAILY_LAGGED_HOLDING_REVIEW`. A future `CONTINUOUS` or `INTRADAY` label would require, at minimum, synchronized intraday executable bid/ask observations for all active pairs, witnessed receipt times, a defined update frequency and maximum staleness, market-hours and outage rules, live position/notional state, atomic limit evaluation around order events, and durable breach/action receipts. Daily candles cannot supply that evidence.

Bank of England studies of the October 2016 sterling flash event and the January 2015 Swiss-franc shock show why that distinction matters: depth, spreads, price impact and the ability to execute can deteriorate within minutes, and the result depends on trade size. A daily closing observation cannot reconstruct that path. [Bank of England, *The October 2016 sterling flash episode*](https://www.bankofengland.co.uk/-/media/boe/files/working-paper/2017/the-october-2016-sterling-flash-episode.pdf) [Bank of England, *OTC microstructure in a period of stress*](https://www.bankofengland.co.uk/-/media/boe/files/working-paper/2019/otc-microstructure-in-a-period-of-stress-a-multi-layered-network-approach.pdf)

### Permitted daily-OHLC development counterfactual

The cited sources do not oppose a bounded simulation. CFA Institute describes rolling-window backtesting as an approximation of the investment process and requires attention to look-ahead bias, structural breaks and tail behaviour. The BOE event studies and execution sources instead set the claim boundary: daily bars and generic costs cannot establish the price or feasibility of an actual forced fill.

A development study may therefore ask: **under this rule fixed in advance, what would the saved daily-OHLC path show if a breach or unavailable edge requested an exit at that business day's modelled open?** It is admissible only when all of the following remain true:

- The review uses returns strictly before the review/exit day. The day's high, low and close do not select the action, retained position, cost scenario or ranking.
- The simulator evaluates the modelled open before that candle's high, low or close and preserves prior partial exits, remaining quantity, stop changes and opening-gap priority.
- Existing generic spread, two-sided slippage and calendar-day financing assumptions remain fixed. Additional exit-slippage sensitivities of 0, 1 and 3 pips per remaining unit are declared before results; the displayed 1-pip case is not selected because it performs best.
- The output is named `MODELLED_DAILY_OHLC_AFTER_ASSUMED_COSTS` or equally explicit wording. It is never described as executable, filled, realised, live, account-level, continuous or intraday.
- The study reports all fixed cost sensitivities and does not use their returns to change admission ranking, choose which held position exits, tune 60/40/0.70 settings, fill a weekly target or promote the strategy.
- Capacity and pair occupancy remain reserved through the original planned horizon, so an assumed early exit cannot create a hindsight-selected replacement.
- `executable_forced_exit_return` and `hedge_return` remain null. No modelled exit establishes a hedge or current action.

This distinction permits the optional development simulator in `docs/PRIVATE_DAILY_RISK_CONTRACT.md` and `pipeline/src/private_desk/risk_control.py` without weakening the evidence requirements below. The reported examined mean of `-0.040386R` is a development counterfactual on an already examined cohort, not realised or account return and not strategy qualification. No current trade is qualified by it.

## Capacity reservation

Continue reserving one slot through the full planned horizon in historical replay. Releasing a slot at an early realised exit and then choosing a historical replacement uses information that was not available when the replacement decision would have been made. CFA Institute's backtesting guidance identifies look-ahead bias as a core problem and describes walk-forward testing as an approximation of the real investment process. [CFA Institute, *Backtesting & Simulation*](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/backtesting-and-simulation)

This reservation is conservative bookkeeping, not an estimate of economic exposure. In a future live-forward record, capacity could be released after a witnessed actual close if the rule was declared beforehand and the close, costs and account state were captured. That live rule must not be retrofitted into the saved replay.

When a daily review is unavailable or breached, do not release capacity merely because a proposed negative-correlation leg appears to offset it. Reserve the original slots through the planned horizon unless a separately qualified, predeclared action creates a verified close.

## Signed concentration is not a hedge

A negative signed correlation describes historical co-movement. A hedge requires a named instrument, direction, size or hedge ratio, rebalance rule, execution clock, full two-leg path and net comparison with the unhedged position. The Federal Reserve's trading manual notes that imperfectly correlated offsetting positions create basis risk and that imperfect correlations across currencies and international interest-rate markets challenge FX hedge effectiveness. [Federal Reserve, *Trading and Capital-Markets Activities Manual*, Market Risk section](https://www.federalreserve.gov/boarddocs/supmanual/trading/200704/0704trading.pdf)

Accordingly:

- A negatively signed edge may remain visible as a diversification diagnostic.
- It must not increase the five-position cap, cancel a positive connected-component breach, or be reported as protection.
- A reverse trade is a second position unless a separate hedge protocol qualifies it.
- Hedge research must compare the complete net path, downside and costs of the declared two-leg rule against the same unhedged call, with ratios estimated only from information then available.

## Currency-leg counts are not account notionals

`currency_legs()` counts directions. A long EURUSD trade adds one long-EUR and one short-USD count, whatever the trade's size. Two EUR-long counts can represent very different monetary exposures; opposing counts can be unequal and leave a large net position.

The Basel FX framework measures actual currency exposure by summing the net spot, forward and other positions in each currency, then converts each currency's nominal amount or net present value at spot rates into the reporting currency. This is materially different from counting long and short labels. [Basel Framework, MAR40.53–40.61](https://www.bis.org/committees/bcbs/basel-framework/standard/mar?allChapters=true)

The BIS Triennial Survey instructions make a related counting distinction: an FX deal is counted once for turnover, while currency breakdowns allocate both legs and may sum to 200%. Gross turnover also ignores netting. This supports separate trade counts, signed currency exposures, gross notional and account-capital use. [BIS, 2025 Triennial Survey reporting guidelines](https://www.bis.org/statistics/triennialrep/2025survey_guidelinesturnover.pdf)

Keep counts as a plain concentration display only. An account exposure view still needs witnessed position units or contract notionals, pair orientation, current conversion rates to the account currency, entry and current prices, leverage and margin terms, stop distance and loss-at-stop, and account equity. Equal stop-risk units do not imply equal base-currency units, quote-currency units, account-currency notional, margin use, or sensitivity to a one-percent move.

## Costs required before an executable or realised exit or hedge return exists

The BIS Markets Committee says execution algorithms shift execution risk from dealers to users and that fragmented electronic markets complicate liquidity measurement. The FX Global Code's examples explicitly recognize slippage on stop-loss execution, mark-up, market impact and transaction-cost analysis. The FCA's rolling-spot-FX/CFD review separately identifies bid/offer spreads, commissions and overnight funding charges, including continuing charges on offsetting long and short positions. [BIS, *FX execution algorithms and market functioning*](https://www.bis.org/publications/fx-execution-algorithms-and-market-functioning) [FX Global Code](https://www.globalfxc.org/uploads/fx_global.pdf) [FCA, *CFD providers' provision of price and value*](https://www.fca.org.uk/publications/multi-firm-reviews/contracts-difference-providers-provision-price-and-value)

Basel's prudent-valuation framework separately lists close-out and early-termination costs, investing and funding costs, bid/offer uncertainty, hedge-out time, quote availability, stressed trading volume and concentration. It does not provide a universal cost constant; it reinforces that costs depend on position size and market state. [Basel Framework, CAP50](https://www.bis.org/committees/bcbs/basel-framework/standard/cap/50/inforce/2019-12-15/published/2019-12-15)

Before reporting an executable or realised forced-exit or hedge return, the record therefore needs:

- executable bid/ask at each entry and exit, with the correct side applied;
- commission, dealer mark-up and any account or conversion charge;
- stop-trigger and fill rules, slippage, gaps, latency, rejection, partial-fill and market-impact treatment;
- position size and fill quantity, including any residual exposure after a partial fill;
- overnight financing or rollover for every held leg and value date, including provider calendar and rate vintage;
- for a hedge, both legs' spreads, slippage, financing, timing and legging risk, plus the lagged hedge ratio and rebalancing costs;
- account-currency conversion at each cash-flow time; and
- an auditable close or order receipt if the result is described as realised rather than simulated.

A daily-OHLC path with fixed generic costs may support the bounded development sensitivity above. It cannot prove a forced-exit fill. A gross reduction in one leg's loss cannot prove that a hedge improved net return.

## Required tests and output states

The next implementation may be bounded to deterministic controls:

- future-return poisoning and same-day unavailable-at-cutoff tests;
- exact-date intersection, gaps, stale last observation, invalid/constant series and 39/40-match boundary tests;
- pair orientation and all four trade-sign combinations;
- threshold tests immediately below, equal to and above 0.70;
- transitive A–B–C connected-component tests;
- sign-flip and short-window/long-window disagreement diagnostics;
- an unavailable active edge that freezes admission and retains capacity;
- a holding-period breach that records no invented executable exit, hedge or replacement, while any daily-open sensitivity remains explicitly modelled;
- planned-horizon reservation despite an early realised outcome in historical data;
- currency counts unchanged while notionals differ, proving the count is not exposure;
- explicit rejection of `CONTINUOUS`, `REAL_TIME`, `HEDGED_RETURN` and `FORCED_EXIT_RETURN` labels without their required evidence.

Recommended state names are `ADMISSION_HELD_CORRELATION_UNAVAILABLE`, `DAILY_WITHIN_LIMIT`, `DAILY_GROUP_BREACH_ACTION_UNQUALIFIED`, and `DAILY_CORRELATION_UNAVAILABLE_CAPACITY_RESERVED`. Preserve the original observation and decision receipt; later data may append a new state but must not rewrite the earlier one.

## Limits that remain

This design controls one narrow form of historical linear co-movement. It does not measure tail dependence, nonlinear exposure, liquidity, gap risk, leverage, margin calls, account survival, settlement risk or broker execution. It does not establish that five positions are safe, that two positions per connected component is optimal, or that the weekly entry target is achievable.

All cited institutional standards describe broader or differently regulated settings. They support conservative measurement principles and the distinction between daily and intraday control; they do not qualify this private strategy. The historical cohort is already examined development evidence. Threshold/window sensitivity, stress-period evaluation, fresh forward observations, full account notionals and verified executable costs remain required before any executable, realised, account-level, hedge or current forced-exit performance claim.
