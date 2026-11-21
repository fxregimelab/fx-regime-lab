# Private bias source research

**Scope:** bounded source review for a manual private-desk bias aid covering EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY, and EUR/GBP.  
**Observed:** 2026-10-02.  
**Decision:** **PASS for a descriptive, price-first bias context; HOLD for calibrated continuation/reversal probabilities, confirmed Wyckoff accumulation/distribution, and trade recommendations.**

This review supports a first implementation that describes what the chart currently resembles. It does not establish an entry, stop, exit, position size, executable return, or qualified trade recommendation. Execution remains manual. The existing model/provider route and settings are outside this packet and should remain unchanged.

## First useful recommendation

Use Wyckoff terms only as **price-structure candidates**. Do not label a currency pair as confirmed accumulation or distribution. The authorized Wyckoff course defines the method through the relationship between price, volume, supply, and demand. But spot FX is an over-the-counter, decentralized market with fragmented and partly invisible trading. There is no consolidated total-volume tape against which the method's volume confirmation can be checked. A broker's tick count or a futures contract's volume is a named, venue-specific proxy, not total spot-FX volume.

Therefore each output should state the observed price events, the candidate phase, and `volume_confirmation: UNAVAILABLE_TOTAL_OTC_VOLUME`. It may then show `BULLISH`, `BEARISH`, `MIXED`, or `UNAVAILABLE` as manual context, with `calibrated_probability: null`.

## 1. What a Wyckoff phase label requires

### What the sources say

The [Wyckoff Stock Market Institute course page](https://wyckoffstockmarketinstitute.com/course/) describes the original method as a technical study of price and volume and their relationship to supply and demand. It is an official teaching source for the method, not an empirical validation of returns in modern OTC FX.

The [Wyckoff Analytics method guide](https://www.wyckoffanalytics.com/wp-content/uploads/2022/06/Wyckoff-Method-Wyckoff-Analytics-English-V2.pdf) supplies the commonly used phase vocabulary:

- **Phase A:** evidence that the prior trend is stopping; preliminary support/supply, a selling climax or buying climax, an automatic reaction, and secondary tests define a prospective range.
- **Phase B:** repeated movement and testing within the range, described by the method as building a cause.
- **Phase C:** a possible terminal test such as a spring/shakeout or an upthrust after distribution. The guide says this event can be absent, so it must not be mechanically required.
- **Phase D:** directional progress within and out of the range, such as signs of strength/weakness and last points of support/supply.
- **Phase E:** sustained movement away from the range into markup or markdown.

The guide repeatedly uses price spread and volume behavior to interpret these events. Its diagrams and labels are educational descriptions, not a demonstrated probability model for the eight requested currency pairs.

The Federal Reserve Bank of St. Louis paper [*Technical Analysis in the Foreign Exchange Market*](https://fraser.stlouisfed.org/docs/publications/frbsl_wp/2011-001.pdf), section 2.1, explains the FX-specific problem: FX is decentralized and comprehensive daily volume is not available. Researchers and practitioners substitute futures volume, tick counts, or proprietary dealer data. The paper also warns that apparent technical-rule performance is vulnerable to data snooping and publication bias.

BIS describes the same market structure. [*FX trade execution: complex and highly fragmented*](https://www.bis.org/publications/qr-201912/fx-trade-execution-complex-and-highly-fragmented) says spot and most FX derivatives trade OTC in a decentralized market whose execution is spread across many venues. [BIS Working Paper 1094](https://www.bis.org/publications/working-paper-1094-foreign-exchange-market) says OTC trading leaves FX opaque and that the main inter-dealer electronic brokers now represent only a small fraction of global spot volume. The BIS [2025 execution landscape review](https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey) adds that substantial customer and inter-dealer activity is invisible to the wider market and that dealers internalize much customer flow. The [BIS Triennial Survey commentary](https://www.bis.org/publications/202509-commentary-otc-derivatives) measures activity reported by participating dealer sales desks during a survey month; it is not a continuous consolidated tape.

### Bounded recommendation

Apply a fixed, past-only price checklist. Do not force an A-E label when the prerequisite event sequence is absent.

| Candidate label | Minimum price evidence | Required limitation |
|---|---|---|
| `RANGE_FORMATION_A_CANDIDATE` | prior directional move loses progress; reaction and retest form identifiable range bounds | no claim that professional accumulation/distribution caused it |
| `RANGE_BUILDING_B_CANDIDATE` | repeated past-only tests within already identified bounds | “cause” is Wyckoff vocabulary, not a measured causal variable |
| `TERMINAL_TEST_C_CANDIDATE` | false break beyond a bound, close/re-entry, and subsequent test under predeclared rules | phase C may be absent; no hindsight relabel after outcome |
| `DIRECTIONAL_PROGRESS_D_CANDIDATE` | repeated progress toward/through one range bound and hold/retest behavior | price-only candidate unless a named volume proxy is separately supplied |
| `MARKUP_E_CANDIDATE` / `MARKDOWN_E_CANDIDATE` | sustained closes beyond the prior range under a fixed rule | descriptive state, not an entry or continuation probability |
| `UNAVAILABLE` | insufficient history, gaps, or no coherent sequence | do not backfill from future bars |

The output should retain the actual observed events and dates so a person can challenge the label. A venue-specific volume series, if later admitted, needs its own identity, market hours, contract/venue, timestamp, revision policy, and coverage. It must be labelled `TICK_VOLUME_PROXY`, `FUTURES_VOLUME_PROXY`, or another exact identity. It cannot silently upgrade a price-only candidate to confirmed market-wide accumulation or distribution.

## 2. Trend, momentum, and reversal over two to five business days

### What the sources say

The BIS working paper [*Currency Momentum Strategies*](https://www.bis.org/publ/work366.pdf) studies cross-sectional winner-minus-loser portfolios across currencies. Its formation and holding periods begin at one month and extend to 12 months. That is evidence about ranked currency portfolios at monthly horizons. It is not evidence that one named pair will continue over the next two to five business days, and it does not supply a pair-level continuation probability.

The paper [*Is There Momentum or Reversal in Weekly Currency Returns?*](https://doi.org/10.1016/j.jimonfin.2014.02.009) studies cross-sectional weekly currency portfolios over one-to-four-week formation and holding periods. Its result is closer in clock time, but a weekly cross-sectional portfolio result still does not identify a daily signal, a given pair's direction, or the conditional probability after a particular chart pattern.

Reversal evidence is also conditional. [*Weekend gaps and subsequent return reversals in the foreign exchange market*](https://irep.ntu.ac.uk/id/eprint/35555/) reports reversal after unusually large Friday-close to Monday-open gaps in its sample. It supports testing a defined weekend-gap condition; it does not justify a generic “FX mean reverts over a week” rule.

The Federal Reserve paper [*Order Flow and Exchange Rate Dynamics in Electronic Brokerage System Data*](https://www.federalreserve.gov/econres/ifdp/order-flow-and-exchange-rate-dynamics-in-electronic-brokerage-system-data.htm) finds substantial relationships between order flow and EUR/USD and USD/JPY returns from short intervals through a week, with relationships weakening at lower frequencies. That result depends on EBS order flow. A daily OHLC pattern without the same order-flow variable is a different information set.

The St. Louis Fed review above documents that technical-rule profitability varies across rules, currencies, sample periods, and transaction costs. It also describes reduced or disappearing profitability in later samples for some once-profitable rules. This is a direct reason to separate a chart description from a forecast claim.

### Bounded recommendation

For the first implementation, use price history to produce only:

- `price_phase`: `TREND_UP`, `TREND_DOWN`, `RANGE`, `TRANSITION`, or `UNAVAILABLE`;
- `technical_bias`: `BULLISH`, `BEARISH`, `MIXED`, or `UNAVAILABLE`;
- the past-only observations and dates that support the classification;
- `calibrated_probability: null`.

Do not translate “trend,” a Wyckoff candidate, monthly currency momentum, or a conditional weekend-gap finding into “X% likely to continue for 2-5 days.” A later probability claim would require a predeclared pair orientation and event definition, a fixed two-day or five-day outcome, realistic timing and costs, chronological held-out evaluation, calibration assessment, and enough independent observations. It must be evaluated without using the result to retune the same label thresholds.

## 3. Positive skew and power-law claims

### What the sources say

The NIST handbook page [*Measures of Skewness and Kurtosis*](https://itl.nist.gov/div898/handbook/eda/section3/eda35b.htm) defines skewness as asymmetry: positive skew means a longer right tail and negative skew a longer left tail. Skewness is not the same property as tail thickness, and neither property by itself establishes a power law.

Cont's primary review [*Empirical properties of asset returns: stylized facts and statistical issues*](https://doi.org/10.1080/713665670) describes heavy tails and volatility clustering across financial returns, including foreign exchange. It also explains that measured properties depend on sampling scale and that the exact tail form is difficult to establish. A general financial-market stylized fact cannot be assigned automatically to every pair, horizon, or signed strategy return.

Clauset, Shalizi, and Newman, [*Power-Law Distributions in Empirical Data*](https://epubs.siam.org/doi/10.1137/070710111), show why a straight line on a log-log plot is not adequate evidence. Their procedure estimates the lower tail threshold and exponent, tests goodness of fit with resampling, and compares a power law with alternatives such as a lognormal or exponential distribution. Even then, the defensible result is that data are or are not consistent with a model, not proof that a power law generated them.

### Bounded recommendation

Do not show a “power law” badge in the first bias output. Do not use a large winning observation to claim positive skew.

If tail description is later added, freeze these choices before looking at pair outcomes:

1. Define the return exactly: pair orientation, signed two-day and five-day close-to-close result, exit treatment, costs, sample dates, missing-bar rule, and whether overlapping observations are allowed.
2. Report the sample count, median, mean, a preselected skew estimator with a block/bootstrap uncertainty interval, fixed tail quantiles, and extreme observations. Keep signed-return skew separate from the tail behavior of absolute returns or losses.
3. Treat positive skew as unsupported when its sign is unstable across sensible fixed windows, its uncertainty interval includes zero, or one observation controls the result.
4. Test a power-law tail only with a predeclared minimum sample requirement, maximum-likelihood tail fit, fitted threshold, resampled goodness-of-fit, and comparison with plausible alternatives. Fit positive and negative tails separately when the claim concerns direction.
5. Preserve the null result. Do not select the window, threshold, horizon, or exclusion rule after seeing which choice produces the desired tail label.

These measurements would describe a historical distribution. They would not qualify the current bias, execution, or expected return.

## 4. Expected fundamentals, surprises, and source vintage

### What the sources say

The Federal Reserve note [*The Sensitivity of the U.S. Dollar Exchange Rate to Changes in Monetary Policy Expectations*](https://www.federalreserve.gov/econres/notes/ifdp-notes/the-sensitivity-of-the-us-dollar-exchange-rate-to-changes-in-monetary-policy-expectations-20170922.htm) explains the central distinction: an expected policy move should already be reflected in market prices, while an unexpected change in the expected domestic-versus-foreign rate path can move exchange rates. The measured sensitivity varies by currency, period, and expectation measure.

The Federal Reserve note [*Monetary Policy Surprises and Monetary Policy Uncertainty*](https://www.federalreserve.gov/econres/notes/feds-notes/monetary-policy-surprises-and-monetary-policy-uncertainty-20180518.html) uses a narrow announcement window and changes in a market yield as a surprise measure. The paper [*Do Actions Speak Louder Than Words? The Response of Asset Prices to Monetary Policy Actions and Statements*](https://www.federalreserve.gov/econres/feds/do-actions-speak-louder-than-words-the-response-of-asset-prices-to-monetary-policy-actions-and-statements.htm) separates a current target-rate factor from a future-policy-path factor. Together they show why “actual minus previous” is not a monetary-policy surprise and why a statement cannot be reduced to its announced rate alone.

For macroeconomic releases, the official [ALFRED help page](https://alfred.stlouisfed.org/help) explains that vintages preserve values available on earlier dates and that observations can be revised. It also says releases are generally added as soon as possible, typically within one business day. The [FRED real-time period documentation](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) shows that an ordinary request defaults to today's real-time period. Thus a current FRED value is not evidence of the value known before a past FX decision, and an ALFRED date-level vintage does not by itself prove the exact intraday receipt time.

### Bounded recommendation

Keep fundamental context separate from the technical classification:

- `fundamental_bias`: `BULLISH`, `BEARISH`, `MIXED`, or `UNAVAILABLE` for the displayed pair;
- `fundamental_relation`: `SUPPORTS`, `CONTRADICTS`, `MIXED`, or `UNAVAILABLE` relative to the technical bias;
- source URL, value identity, observation/reference period, publication timestamp when stated, captured-at timestamp, and vintage status for every input;
- `expectation_value`, `surprise_value`, and `surprise_unit` as null unless a pre-release consensus or a defined market-price expectation was actually captured before the release.

Compute direction from both currency legs. A development convention must state whether a source signal strengthens the base currency or the quote currency before mapping it to the displayed pair. EUR/GBP requires relative EUR-versus-GBP evidence; a USD factor cannot be copied into it.

A current central-bank page or current FRED observation may support a clearly dated current-context statement. It cannot reconstruct what was known before a historical release. A policy-rate change from one complete captured announcement to the next is an announced change, not a market surprise. Missing predecessor, expectation, publication clock, or vintage evidence must remain null; do not bridge through failed captures.

## First-implementation output contract

For every one of the eight pairs, the bounded output should contain:

| Field | Permitted first value |
|---|---|
| `pair` | one of the eight fixed pairs |
| `as_of` | exact source/bar cutoff with timezone |
| `price_phase` | `TREND_UP`, `TREND_DOWN`, `RANGE`, `TRANSITION`, `UNAVAILABLE` |
| `wyckoff_candidate` | nullable phase candidate; never confirmed accumulation/distribution |
| `observed_price_events` | dated, past-only facts used by the label |
| `volume_basis` | `UNAVAILABLE_TOTAL_OTC_VOLUME` or an exact source-specific proxy identity |
| `technical_bias` | `BULLISH`, `BEARISH`, `MIXED`, `UNAVAILABLE` |
| `fundamental_bias` | separately derived `BULLISH`, `BEARISH`, `MIXED`, `UNAVAILABLE` |
| `fundamental_relation` | `SUPPORTS`, `CONTRADICTS`, `MIXED`, `UNAVAILABLE` |
| `calibrated_probability` | `null` |
| `execution` | `MANUAL` |

The reader-facing wording should say “price structure resembles,” “technical context is,” and “fundamental context supports/contradicts.” It should not say “institutions are accumulating,” “smart money confirms,” “power-law edge,” “X% continuation probability,” or “take this trade.”

## Evidence still required for stronger claims

The following remain unavailable from this source review:

- consolidated market-wide OTC FX volume;
- empirical validation of the chosen Wyckoff event detector on the exact eight-pair, two-to-five-business-day task;
- a predeclared and untouched chronological evaluation set large enough for pair/horizon calibration;
- complete executable spreads, slippage, rollover, gap and partial-exit treatment for return claims;
- point-in-time pre-release expectations and exact historical receipt clocks for every fundamental observation;
- evidence that current-source or revised macro values reproduce the information set available at each historical decision;
- evidence that a fitted heavy tail is a power law rather than a plausible alternative;
- evidence qualifying a current trade, mandatory execution level, or account outcome.

These gaps do not prevent a manual descriptive bias aid. They require its forecast probability to remain null and its execution status to remain manual.
