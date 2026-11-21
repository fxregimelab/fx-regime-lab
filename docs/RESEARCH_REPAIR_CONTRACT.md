# Research repair contract

27 September 2026. Inspected base: `9fa150538d08ab5a2a6c587976552944f47a724d`, plus the current repair register. This is a repair specification, not evidence that the repairs or experiments have passed. It covers D01–D07, S01–S06, P02–P03 and R01–R06 in [the repair register](REPAIR_REGISTER.md), with dependencies on validation and provenance repairs. Source evidence and retrieval limits are in [the research source report](../reports/repair-research-sources.md).

The engine needs an honest measurement contract before another accuracy comparison. An economic story can justify testing a variable; it cannot supply its coefficient, forecast accuracy or probability calibration. A valid rejection is a completed experiment. No accuracy gain is promised.

## 1. Three outputs with different meanings

| Output | Quantity being estimated | Evidence that can validate it |
|---|---|---|
| Descriptive regime | State of information available at publication: rate advantage, positioning, volatility, policy pressure | Reproducible feature values, timestamps, explicit state rules, stability and transition diagnostics. A later spot move is not independent ground truth for a descriptive label. |
| Directional forecast | Direction of the quoted pair between specified entry and terminal observations, at a specified horizon | Frozen published direction, eligible future prices, fixed deadband, out-of-time comparisons and uncertainty. |
| Internal hypothetical payoff | Signed exchange-rate movement, less explicitly modeled positive costs, for a research exposure | Execution-time convention, instrument, cost coverage and exposure accounting. This is neither account performance nor an external trading recommendation. |

Store separate fields and version identifiers for all three. A regime may exist when a directional forecast is unavailable. `NEUTRAL` as an abstention is not a prediction of a flat return. If a future experiment predicts an actual flat class, give it a different target and evaluate its full probability vector.

For the current two-horizon research definition, let `S` be quote currency per unit of base currency, `r_h = 10,000 × log(S_exit / S_entry)`, and `d` be +1 for BULLISH and −1 for BEARISH. Use the canonical validation contract's strict boundary: up if `r_h > 5`, down if `r_h < −5`, flat otherwise. Directional success is `d × r_h > 5`; flat is a directional failure. Abstained, unpublished, immature, missing-price and invalid calls are excluded with distinct counts. T+5 and T+20 are different outcomes, never pooled as independent calls.

Internal net research payoff is `d × r_h − c_h`, with `c_h ≥ 0`. Accuracy does not depend on costs. Positive net payoff does not mean directional success under the deadband. Missing cost is unknown, not zero. Multiplying a log return by direction is a signed research measure; it is not automatically a financed investment's simple return. Never sum overlapping T+5/T+20 values into an equity curve. A portfolio experiment requires an explicit daily position ledger, concurrent exposure, capital, financing, rollover, cash conversion and mark-to-market prices.

## 2. Pair-up is the only directional sign convention

`positive = expected rise in the quoted pair`. Preserve the raw source orientation as metadata and transform once at the feature boundary. Do not attach a generic “USD bullish” label to a positive score.

| Pair | Rising pair means | Currency-strength input to pair-up conversion |
|---|---|---|
| EUR/USD | EUR strengthens against USD | EUR +1; USD −1 |
| USD/JPY | USD strengthens against JPY | USD +1; JPY −1 |
| USD/INR | USD strengthens against INR | USD +1; INR −1 |

Required fixtures include stronger US relative policy news giving EUR/USD a negative candidate input and USD/JPY a positive one; more long JPY futures giving a negative USD/JPY positioning input; and positive INR inflows giving a negative USD/INR pressure input. These establish units and orientation. They do not establish predictive signs. A contrarian hypothesis reverses the relevant positioning exposure explicitly and receives its own experiment ID.

Volatility, total open interest, source freshness and intervention risk are state or risk variables by default. High volatility does not inherently imply pair-up. Every directional use needs a pair-specific interaction and a registered forecast test. Mirroring all directional inputs must mirror the composite and preserve its magnitude, confidence-score magnitude and eligibility, except for a separately documented, tested pair asymmetry.

## 3. Rates: distinguish level, change, surprise and carry

The inspected `pipeline/universe.json` sets `DGS2` against `ECBDFR`, `IRLTLT01JPM156N` and `INDIRLTLT01STM`. These are not three matched two-year sovereign spreads: DGS2 is a daily US two-year Treasury yield; ECBDFR is the ECB deposit facility rate; the Japan and India series are monthly ten-year government yields. Other fetch paths attempt local two-year yields and silently substitute ten-year proxies. A label must describe the actual path and selected series, not the desired instrument. Verify these definitions against the [DGS2](https://fred.stlouisfed.org/series/DGS2), [ECBDFR](https://fred.stlouisfed.org/series/ECBDFR), [Japan](https://fred.stlouisfed.org/series/IRLTLT01JPM156N) and [India](https://fred.stlouisfed.org/series/INDIRLTLT01STM) metadata.

Use separate candidate features:

1. **Rate level:** matched-tenor base minus quote nominal yield, in percentage points, with source dates and instrument class. It describes a relative yield state. A large level or a high historical percentile is not a policy surprise.
2. **Rate change:** change in that matched spread over a frozen trailing interval. It is observed repricing, not necessarily news or a causal policy shock. Its future explanatory value starts after publication.
3. **Policy surprise:** change in matched expected policy paths around a timestamped announcement relative to information available beforehand. This requires appropriate OIS/futures or expectation data; without it, this candidate is unavailable. Federal Reserve event-study evidence supports investigating relative policy news, while later work documents important cross-country and episode limits. Neither paper validates this engine's daily level signal. [2017 Fed note](https://www.federalreserve.gov/econres/notes/ifdp-notes/the-sensitivity-of-the-us-dollar-exchange-rate-to-changes-in-monetary-policy-expectations-20170922.htm), [2024 Fed note](https://www.federalreserve.gov/econres/notes/feds-notes/monetary-policy-and-exchange-rates-during-the-global-tightening-20240510.html).
4. **Real-rate difference:** `(i_base − expected_inflation_base) − (i_quote − expected_inflation_quote)` at compatible maturities and dates. Subtracting only US breakeven inflation from a US-minus-foreign nominal spread does not produce a bilateral real-rate differential. Breakevens also contain risk/liquidity components. Where compatible expectations are absent, disable this claim; a one-sided adjustment may survive only under an accurate proxy name and separate experiment.

Under the same pair convention, covered parity's idealized relation is `F/S = (1 + i_quote × τ)/(1 + i_base × τ)`. Under uncovered parity, expected spot depreciation offsets a higher base-currency interest rate; approximately `E[Δlog S] = (i_quote − i_base) × τ`. These are different statements. Forward points are not a guaranteed spot forecast. Cross-currency basis, market segmentation and funding constraints can break the simple covered relation. [BIS covered-parity analysis](https://www.bis.org/publ/qtrpdf/r_qt1609e.htm).

A carry hypothesis instead asks whether a higher-yield currency earns excess return despite expected depreciation; that empirical behavior is not a riskless consequence of parity. Funding stress and crowded unwinds can produce large losses. Dividing a two-year yield spread by volatility is a carry-to-volatility proxy, not a realized carry payoff or probability. Freeze whether numerator/denominator are percentages or decimals and whether volatility is annualized. [BIS carry analysis](https://www.bis.org/publ/qtrpdf/r_qt0712.pdf), [Brunnermeier, Nagel and Pedersen](https://www.journals.uchicago.edu/doi/abs/10.1086/593088).

For INR, record forward outright versus points, USD/INR orientation, tenor, day-count, settlement convention, onshore versus NDF and timestamp. Positive USD/INR forward points cannot alone establish imminent INR weakness. No forward-premium feature qualifies until those source fields are verified.

## 4. Pair-specific hypotheses and rejection paths

These are proposed tests, not new production rules. Start with a fixed, small model and one added hypothesis at a time. Shared measurement code is appropriate; a shared economic sign across all three pairs is not.

| ID | Mechanism and candidate | Forecast/state target and expected sign | Failure condition or restriction |
|---|---|---|---|
| EUR-R1 | Relative European minus US expected-rate repricing | EUR/USD forward T+5 direction; positive relative EUR news is candidate pair-up | No matched expectations source: unavailable. Daily spread changes must use a separate non-causal name. Immediate event reaction is not proof of post-publication persistence. |
| EUR-C1 | EUR futures positioning changes versus crowding | Trend continuation and extreme-position reversal are competing, separate tests | Do not choose the winning interpretation after seeing holdout results. COT is one segment of positioning, not the whole currency market. |
| EUR-S1 | Fragmentation pressure: Italy minus Germany matched ten-year spread widens | Candidate EUR/USD negative pressure, with dates aligned | Current function uses Germany minus Italy; reverse the raw spread convention or its sign exactly once. A same-day association is not a forward effect. |
| EUR-S2 | ECB balance-sheet change relative to the Fed | Descriptive relative policy state first; forward EUR/USD sign remains empirical | ECB asset level alone is not an easing surprise; valuation and composition can change it. Current fixed EUR 6,000bn mapping has no registered forecast evidence. |
| JPY-R1 | US minus Japan matched-rate level and repricing, conditioned on funding volatility | Rate advantage is a carry state; repricing can be candidate USD/JPY positive | A level z-score is not news. Separate carry payoff from spot direction. |
| JPY-C1 | Leveraged-fund short JPY exposure combined with policy tightening or stress | Candidate unwind state and USD/JPY downside/tail risk | Short JPY may persist; high short exposure alone is not an immediate reversal forecast. Condition thresholds are trained, frozen and tested. |
| JPY-I1 | Speed/extent of yen depreciation plus dated official communication | Probability of a subsequently disclosed yen-buying intervention in a fixed horizon | Requires released event labels and separate train/test periods; fixed spot 150/160 bands are uncalibrated heuristics. Event occurrence and price response are different targets. |
| INR-F1 | Released equity and debt FPI flows, normalized separately before a registered combination | Candidate INR demand pressure, hence USD/INR negative | Settlement, hedging and endogenous response can weaken/reverse association. Missing release timestamps disable historical OOS eligibility. |
| INR-O1 | Oil shock conditional on dollar and global demand conditions | Candidate USD/INR positive pressure through import demand | Oil level percentile alone cannot identify an oil shock; no unconditional causal sign is assumed. |
| INR-I1 | Released reserve/intervention information plus spot and volatility state | Descriptive intervention-pressure state; any intervention probability has its own labeled target | Suppressed volatility or a small spot move is not proof of RBI action. Daily outcome labels cannot be invented from monthly aggregates. |

**JPY authority correction proposal, requiring an explicit change to protected `IDENTITY.md`:** replace its universal assertion that yen strength triggers a BoJ response while weakness is tolerated with: “Japan's Ministry of Finance decides foreign-exchange intervention; the Bank of Japan executes as its agent. Intervention direction and response vary by episode. Yen weakness can prompt yen-buying intervention; neither a fixed exchange-rate threshold nor guaranteed intervention is assumed.” This document does not edit or override the protected identity file. The institutional responsibility is documented by [BoJ](https://www.boj.or.jp/en/intl_finance/outline/expkainyu.htm); [MoF's July 2024 record](https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2024_3Qe.html) explicitly lists dollar sales and yen purchases. That record was published on 8 November 2024, illustrating why event date and public availability must differ.

**INR limits:** RBI describes two-sided intervention aimed at orderly conditions and excessive volatility, without a fixed exchange-rate target. “RBI is the dominant driver” remains an untested project premise, not an established result for every period. A reserve change combines transactions, valuation and other effects; it is not a daily intervention measure. [RBI policy discussion](https://rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=22995), [RBI reserve/intervention explanation](https://rbi.org.in/scripts/PublicationsView.aspx?Id=18086). To test INR-I1, obtain released spot and forward-operation data with their publication schedule, choose a label frequency those data actually support, and retain an unknown state when intervention cannot be observed. Estimate conditional future returns separately; intervention is an endogenous policy response, so a predictive association cannot establish its causal effect.

## 5. What was knowable at each call

Every input snapshot must retain `source_id`, instrument/series, unit, tenor, quote orientation, observation period, `released_at`, `retrieved_at`, `vintage_id`, raw-payload hash, market timezone and transformation version. A production feature must have been released and successfully ingested by the forecast cutoff. A reconstructed information-available replay can use documented release availability, but must not pretend a present-day retrieval happened historically. Mark its provenance separately from live recorded snapshots.

No observation-date join establishes availability. Select only a version whose release/availability precedes the cutoff. When a source supplies only a release date, use a documented conservative next-session rule, or reject intraday eligibility; do not invent a release time. Include per-source freshness ceilings and carry-forward age. A fresh spot cannot refresh a stale rate. Weekly/monthly observations carried across daily calls remain one source observation, not newly observed independent information.

ALFRED records historical real-time periods, unlike a latest FRED download; coverage and date-level resolution still require checking for every series. Query the as-of vintage and preserve revisions. Without usable vintage evidence, mark historical values `reconstructed_latest_vintage`, exclude them from genuine point-in-time OOS claims, and use them only in explicitly labeled exploratory analysis. [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [ALFRED documentation](https://fred.stlouisfed.org/docs/api/fred/alfred.html).

COT needs both position/report date and actual release timestamp. Tuesday holdings normally arrive Friday at 15:30 US Eastern, with holiday exceptions; resolve daylight saving through the named timezone and use each year's actual schedule. A delayed release must remain unavailable even if three calendar days have passed. Maintain distinct report observations across year boundaries and enough history for the declared 156-report window. Never pad it with repeated weekly values. [CFTC schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm).

Keep Legacy Non-Commercial, TFF Asset Manager and TFF Leveraged Funds separate; do not splice categories or substitute net-long into an AM-minus-LM history. Category names describe trader businesses, not verified skill. Freeze futures-only versus futures-and-options-combined, contract code, unit and report type. Positive EUR futures exposure maps toward EUR/USD up; positive JPY futures exposure maps toward USD/JPY down because CME quotes yen futures in USD per yen. The contrarian switch belongs to the hypothesis, not to a silent currency inversion. USD/INR's absent COT contract remains absent. [CFTC classification notes](https://www.cftc.gov/idc/groups/public/%40commitmentsoftraders/documents/file/tfmexplanatorynotes.pdf), [CME yen contract](https://www.cmegroup.com/markets/fx/g10/japanese-yen/specs).

Price data need bar start/end, quote convention, timezone, session calendar and availability. Forecast computation may use a completed bar only after it is available. The evaluation reference price must follow the recorded publication time under one frozen rule. T+5/T+20 mean eligible market sessions from that reference, not arbitrary available-row indices or calendar days. Missing expected bars must be reported, not silently compress the horizon. Reject unreconciled offshore/onshore INR substitutions and interpolated prices as realized outcomes.

## 6. Train on forward targets, then freeze

`compute_dynamic_betas` currently relates contemporaneous changes in normalized inputs to contemporaneous spot returns, takes correlation magnitudes for weights, and has no fitted special/FPI relations. That is not forecast precision. `compute_dominance_scores` is at most a descriptive association ranking; it cannot identify a causal macro driver. Keep adaptation disabled for the repaired reference model until the following experiment passes.

Build each training row at cutoff `t` using only features available then, with the registered future `r_h` or categorical outcome as target. A training row is eligible for fitting at time `T` only if its outcome was observable before `T`. Fit normalization, imputation, feature selection, signs, coefficients, thresholds, hyperparameters and calibrators within the training process. A past-only rolling normalization is allowed if its algorithm and window are frozen; evaluation-period labels cannot update it. A negative relationship must retain its sign or cause rejection of a constrained hypothesis; absolute correlation must not turn it into positive evidence.

Use chronological expanding/rolling outer evaluation folds. Within each training fold, use earlier fit data and a later, disjoint calibration/selection interval; keep a final holdout untouched by all selection. Purge any training label interval that overlaps the validation/test interval. For overlapping horizons, the purge is determined by actual `[entry_at, outcome_available_at]`, not merely a guessed number of rows. Before advancing a fold, ensure all retained labels have matured. If a design permits later observations to train an earlier validation fold, remove that design or specify an embargo and prove the information boundary. For the preferred forward-only design there is no future training block; document this rather than adding a decorative embargo. `TimeSeriesSplit(gap=...)` can assist but does not itself prove label-interval purging or source availability. [scikit-learn split reference](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

Daily T+5 outcomes overlap, and T+20 overlap more. Report raw call count, distinct source reports, time span, and counts from non-overlapping horizon-spaced subseries. Use paired moving-block resampling of forecast-versus-baseline loss differences, keeping all pairs on common date blocks when pooling. Predeclare primary block length at least the longest evaluated horizon and longer-block sensitivity; preserve missingness and each forecast's eligible mask. Report 95% uncertainty intervals and sensitivity across all starting offsets of non-overlapping subseries. This is an inference policy for this project, not a claim that a block length removes all dependence. Too few blocks means insufficient evidence, not independent Bernoulli trials.

The baseline set is fixed before results: training-only majority direction/base-rate probability; constant 0.5 correctness probability; a declared simple trailing-momentum rule; a declared rate-only rule; and the corrected fixed-weight reference model. A no-change price forecast is useful for return error but abstains under the directional policy, so it cannot be described as 50% directional accuracy. Compare shared eligible rows, report each model's full coverage as well, and prohibit threshold tuning that improves accuracy solely by hiding difficult cases.

## 7. Probability and Brier contract

The current `0.35 + 0.40 × score` is an affine heuristic. It has no fitted outcomes and is not Platt calibration. Publish it as an internal consistency score, or leave probability unavailable. Actual sigmoid or isotonic calibration must fit paired scores and outcomes on out-of-time predictions, after the base model is fixed. Use a sigmoid as the initial low-complexity candidate; an isotonic alternative needs adequate independent calibration evidence and its own registered comparison. [Calibration documentation](https://scikit-learn.org/stable/modules/calibration.html).

For a directional call define `p_h = P(d × r_h > 5 | information at publication, issued direction)`. Then `y_h` is the same event's 0/1 realization and `BS_h = mean((p_h − y_h)^2)`. This is probability of the issued direction succeeding, not necessarily probability of pair-up. A net-positive-payoff probability has a different target and cannot reuse this score. Filter probability/outcome pairs together by immutable call and evaluation IDs; never independently drop nulls and zip the remaining arrays.

Brier's ideal lower bound is zero. A fixed 0.5 forecast always scores 0.25 for binary outcomes, but an imbalanced event may have a stronger training-estimated base-rate baseline. If probability is forcibly bounded to `[0.47, 0.71]`, the pointwise minimum loss is `0.29²` for successes and `0.47²` for failures; the cohort minimum depends on its outcomes, not a universal 0.25 floor. A score below 0.25 alone proves neither calibration nor profitability. Proper scoring rules reward accurate probabilities in expectation; inspect held-out reliability, sharpness and baseline-relative loss separately. [Gneiting and Raftery](https://doi.org/10.1198/016214506000001437).

Report Brier skill `1 − BS_model / BS_reference` only on the same rows, with the reference named and a nonzero denominator. Calibration plots require bin counts, observed success fractions, mean forecast probability and dependence-aware uncertainty; do not interpret an almost-empty bin. Report by pair and horizon first, plus direction, source/version and predeclared regime slices. Accuracy, coverage, abstentions, flat outcomes, pending outcomes and missing-cost exclusions each need their own denominator. A 55% rolling hit rate remains the identity gate; it is not a test of skill by itself and must not be converted into a guaranteed edge claim.

## 8. Experiment manifest and decision rules

Before opening evaluation results, save a machine-readable manifest with these required fields. Missing fields invalidate a confirmatory run; historical experiments without prior registration remain exploratory.

```yaml
experiment_id: REQUIRED_UNIQUE_ID
registered_at_utc: REQUIRED
code_commit: REQUIRED
dirty_patch_sha256: REQUIRED_OR_CLEAN
data_manifest_sha256: REQUIRED
feature_contract_version: REQUIRED
validation_contract_version: REQUIRED
source_cohort: REQUIRED_LIVE_OR_PIT_REPLAY_OR_EXPLORATORY
pair: REQUIRED_ONE_OF_THE_THREE
hypothesis_and_rejection: REQUIRED
target_event_and_horizon: REQUIRED
cutoff_entry_exit_calendars: REQUIRED
required_sources_missingness_freshness: REQUIRED
train_calibration_test_boundaries: REQUIRED_EXPLICIT_DATES
label_interval_purge_and_embargo: REQUIRED
normalization_and_refit_schedule: REQUIRED
candidate_models_and_total_trial_budget: REQUIRED
baselines_and_eligibility_masks: REQUIRED
primary_metric_and_minimum_effect: REQUIRED
coverage_floor_and_allowed_change: REQUIRED
uncertainty_method_block_lengths_seeds: REQUIRED
multiple_comparison_policy: REQUIRED
holdout_access_log_and_hash: REQUIRED
decision_rule_and_stop_rule: REQUIRED
```

No unresolved `REQUIRED` value may remain in an executed manifest. Select actual dates from a frozen inventory before calculating candidate holdout metrics. A reviewed interval used to design these repairs is not an untouched holdout. If no untouched historical data remain, freeze the candidate and collect a future shadow cohort; live-history gates still apply. Keep all attempted models, rejected features and failed experiments in the trial count. Selection across many backtests is itself an overfitting risk. [Bailey and colleagues](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

Default proposed acceptance for a new directional rule: a preregistered paired 95% interval for accuracy improvement over both the corrected reference and training-majority baseline has lower bound above zero on the shared holdout cohort; its full issued-call coverage meets the preregistered floor; the sign is consistent in the non-overlap sensitivity; and every integrity gate below passes. The minimum practical effect and coverage floor must be chosen before outcomes, not supplied here as invented performance forecasts. Adjust family-level claims for the registered number of comparisons, for example Holm correction, rather than selecting the best unadjusted result.

Probability promotion additionally needs held-out Brier improvement with a paired 95% interval wholly below zero versus the training-estimated base-rate forecast and the registered uncalibrated comparator, accompanied by reliability evidence. An interval crossing zero is inconclusive. A confidently worse result rejects promotion. An intervention-probability candidate also needs sufficiently many independently dated positive and negative events for a preregistered power/precision calculation; otherwise it stays an uncalibrated state score. Minimum sample requirements come from the chosen effect, event prevalence and dependence, not a round number of daily rows.

Passing integrity checks permits a truthful research result even when all candidate models fail. It does not authorize production promotion, a phase advance, a database rewrite or a public performance claim without the corresponding release and live-evidence requirements.

## 9. Repair acceptance and claims to withdraw

| Gate | Concrete evidence required |
|---|---|
| D01–D03, S01 | Source manifest with matched units/tenors or explicit proxy names; time and vintage fields; currency-inversion fixtures and stale-rate/fresh-spot rejection. |
| D04–D06 | COT Friday/holiday/DST/year-boundary fixtures; a revised macro observation unavailable before its vintage; no Tuesday leakage. |
| D07, S02, S06 | Per-pair available/missing/proxy inventory. Unsupported IV, skew and intervention inputs cannot be fabricated or called measured. |
| S03–S05 | Mirrored score fixtures; train-only forward fitting; signed relationships; held-out calibration evidence or probability unavailable. |
| P02–P03 | Identical snapshot and prior state produce identical final direction, gates, confidence score and feature values through live, staged and replay paths. Deliberately missing history must fail honestly. |
| R03–R05 | Frozen manifest, complete attempted-model ledger, baseline report, paired uncertainty, coverage/eligibility reconciliation and untouched-holdout receipt. |
| R01–R02, R06 | Source-to-claim inventory, corrected math and record-by-record bridge of old versus repaired evaluations. Public figures remain unverified until this exists. |

The following current statements require correction in their owning documents/code, not repetition as established facts:

- `TASK.md` assigns gains of +0.5–4 percentage points to individual repairs and calls some changes “Zero Overfitting.” No inspected evidence supports those forecasts; remove them or label historical speculation. `MASTERPLAN.md` calls interactions “easy alpha left on table”; replace with an untested hypothesis.
- `TASK.md` calls the same-sign penalty covariance-aware and the affine confidence rule empirical calibration. `_redundancy_penalty` counts sign agreement; it does not estimate covariance. Same-sign observations are not proof of redundancy.
- `src/signals/rate.py` calls a level z-score a detector of changes and a one-sided inflation adjustment real yield. The statistical transformations do not establish those economic meanings.
- `src/signals/cot.py` calls AM-minus-LM a “smart spread” and suggests turning-point skill without an experiment. Its fallback to net-long changes the quantity being measured. Keep the neutral category name and reject mixed-definition history.
- `src/signals/special.py` declares positive USD strength, while the final composite needs pair-up. ECB balance-sheet level, fragmentation, VIX, oil and DXY require separate mechanism and orientation records. USD/INR's nested oil/DXY blend does not add a third independent EM variable.
- `src/signals/open_interest.py` makes high total open interest bearish and low open interest positive despite describing low conviction. `src/signals/volatility.py` makes high volatility positive. Neither supplies a universal directional theory.
- `src/signals/intervention.py` labels a lower spot zone safe and an upper one intervention territory. Those are hand-set level scores, not measured probabilities or policy commitments.
- `src/backfill/simulation_engine.py` sets `rate_spread_2y = base_yield`, normalizes different rate constructions, builds a one-row smart-spread input, approximates OI from its delta sign, and feeds raw FPI flow as a normalized feature. This does not establish production-equivalent history.
- `src/diagnostics/permutation_importance.py` skips OI/FPI, lacks special histories, evaluates a ±0.1 composite rule instead of the final published layers, and supplies beta rows without their required dates/spot/raw fields. Its full-window fitting setup would also violate the proposed forward boundary if repaired without time splits. Present outputs cannot validate production feature importance. Use held-out grouped/blocked ablation of the final rule; shuffling independent daily observations destroys temporal structure and is not causal attribution.
- `docs/SSRN_PAPER_DRAFT.md` claims eight integrated families including risk reversal, 17,000+ out-of-sample calls from 1997–2026, preregistration, calibrated structure and specific accuracy/Brier figures. Inspected code and documents do not provide the frozen source/version/availability/cohort evidence required for those claims. Mark them unverified and withhold publication until reconstructed and reconciled; historical replay is never retroactively a live public forecast. Its “90 consecutive days above 55%” wording also differs from the rolling-window identity rule and needs explicit governance resolution.

These are local source findings. No live database, production cohort, deployed pipeline, licensed data coverage or new model result was verified while preparing this contract.
