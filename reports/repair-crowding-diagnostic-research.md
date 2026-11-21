# Crowding diagnostics: measurement and consumer repair

27 September 2026. Read-only research against `codex/frontend`, base `9fa150538d08ab5a2a6c587976552944f47a724d`, with existing repair changes preserved. This report is the only file owned by this research leaf. No application function, database, runtime, provider acquisition, AI service, notification or ledger was changed. The protected Japan identity wording remains outside this repair. This is a proposed implementation contract, not an implemented or validated model.

The supplied data cannot measure participant pain, position cost basis, an underwater position, or squeeze probability. Preserve useful measurements as separate positioning and price descriptors. Set unsupported legacy quantities to unavailable; do not replace pain with a renamed score that still controls risk language or ranking.

## Evidence and meaning

CFTC describes open interest as outstanding contracts and reports positioning and changes between reports. Its public positioning measures do not supply participants' transaction prices. A change in net contracts is a position change, not profit or loss. Aggregate long and short open interest are equal; a category's net position is not the whole market's net exposure. These distinctions follow the [CFTC explanatory notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm).

TFF distinguishes Dealer, Asset Manager, Leveraged Funds and Other Reportables by business role. A category can hedge, speculate or hold offsetting exposures. Category names do not establish investment skill. Neither a category net nor AM-minus-LM identifies one portfolio whose entry price can be reconstructed. See the [CFTC TFF notes](https://www.cftc.gov/idc/groups/public/%40commitmentsoftraders/documents/file/tfmexplanatorynotes.pdf).

For futures profit or loss, CME requires the contract specification, current price, transaction price and position size. Even an accurate spot-market VWAP would not supply the entry prices of the outstanding futures cohort. Futures basis, expiry, rolls, closing positions and hedges remain unknown. The conclusion that this input set cannot identify participant losses follows from those missing inputs, rather than from a claim that aggregate COT is useless. See [CME profit and loss calculation](https://www.cmegroup.com/education/courses/introduction-to-futures/calculating-futures-contract-profit-or-loss).

VWAP weights traded prices by traded quantities: `sum(price_i * quantity_i) / sum(quantity_i)`, over a specified instrument, venue and interval. A mean of 40 daily closes has equal weights and no trade quantities. CME's [VWAP documentation](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457226934/MDP%2B3.0%2B-%2BVolume%2BWeighted%2BAverage%2BPrice%2Bfor%2BBrokerTec) describes trade-price and volume weighting; its [settlement rule](https://www.cmegroup.com/rulebook/CME/I/8/8.pdf) uses trades during a defined settlement period. Broker tick counts or volume from another instrument cannot turn spot closes into transaction VWAP. Forty observed dates also do not prove forty consecutive market sessions or eight calendar weeks.

COT report dates describe holdings; release dates describe availability. The normal Tuesday/Friday pattern has holiday exceptions. The official schedule itself is tentative, so a scheduled release is not evidence of actual release or local ingestion. Use the [CFTC release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm) as a source to verify, not a function that invents historical timestamps. For example, the 2026 schedule lists a delayed June 22 release; a universal Tuesday-plus-three-days rule would be wrong.

CME yen futures quote USD per JPY. A positive JPY futures net exposure therefore has negative USD/JPY orientation. EUR futures exposure has positive EUR/USD orientation. These are quote conversions, not contrarian forecast hypotheses. See [CME yen specifications](https://www.cmegroup.com/markets/fx/g10/japanese-yen/specs) and [CME FX product overview](https://www.cmegroup.com/markets/fx/fx-futures.html).

## What the inspected application actually does

`pipeline/src/analysis/asymmetry.py` infers direction from regime substrings, treats USD strength as +1 for every pair, negates every centered COT percentile, and converts their distance to pain. It selects the latest COT date without an as-of fence; a future report produces negative age and passes the stale check. It takes the last supplied spot without local ordering or cutoff validation. Its `vwap_8w` is the mean of the last 40 closes plus a two-year-spread accrual approximation. Its percentile midpoint decides `crowded_long_usd`, even though percentile is neither exposure sign nor USD orientation. Half of annualized realized volatility, a positive implied-minus-realized difference and an RVOL threshold then decide `underwater_triggered`. Missing RVOL passes that gate. None of these operations observes a participant entry price.

The scheduler currently gets its COT percentile from `compute_cot_percentile`, which uses `net_long`, not AM-minus-LM. That helper excludes the anchor from its empirical distribution but resolves conflicting same-date rows by input order. Its nominal 156-report window includes the anchor, so at most 155 earlier reports form the reference. A report-date fence is not a release-time fence.

`CotRow` has exactly `date`, `pair`, `net_long`, `open_interest`, `asset_mgr_net`, and `lev_money_net`. There is no release time, retrieval time, vintage, report type, contract code or category definition. Worse, `fetchers/cot.py:_spec_ls` builds `net_long` either from Legacy Non-Commercial long minus short, or from the sum of TFF Asset Manager, Leveraged Funds and Other Reportables. The row does not say which. Do not label this field uniformly Non-Commercial, smart money, institutional, or leveraged carry. Do not infer a missing category definition from the sign or the presence of optional fields.

The damage continues after call publication:

| Consumer | Current consequence | Required repair |
|---|---|---|
| Scheduler | Calculates carry solely to feed pain; stores null pain but false underwater on failure; passes pain into briefs and ranking | Remove this carry path; preserve independent descriptor results and reasons; unknown underwater is null; bind direction to the actual published call |
| `analysis/systemic.py` | Both provisional ordering and final score replace missing pain with zero; pain contributes 40%, confidence 40%, rank velocity 20% | Retire this unsupported Apex calculation and its active use; publish null score/rank with reason, without renormalizing or substituting a descriptor |
| `ai/client.py` fallback | Pain at least 80 becomes ELEVATED, otherwise CONTROLLED | Use deterministic descriptive text; no low-risk conclusion from unavailable or low pain |
| AI prompt | Demands squeeze risk from pain and even offers `8-WEEK VWAP BREACH` as a catalyst | Remove the pain/thesis and squeeze instructions and the VWAP example; encode only frozen, typed descriptors |
| `web/.../desk-card.tsx` | Displays PAIN INDX; null falls through to “No extreme divergence signal”; scores above 80 create an asymmetric-setup claim | Render supported descriptors and explicit unavailability; remove the threshold claim and reassuring null branch |
| Public query/types, compare/desk surfaces | Carry `pain_index`, rank, Apex and old AI squeeze text | Understand diagnostic version and missingness; never promote legacy text or fields to corrected measurements |

Scheduler diagnosis is downstream of the frozen directional call; repairing it should not change the forecast direction or historical call ledger. Correlation measurements may remain separate. With only three pairs, any “top three” basket cluster does not need an unsupported ranking first.

## Proposed deterministic contract

Use a versioned `positioning-diagnostics-v1` object, preferably inside existing desk-card telemetry so no schema change is required for this repair. It needs `pair`, `as_of_date`, `call_id`, `predicted_direction`, `diagnostic_version`, per-component values/reasons and qualification flags. Immutable forecast evidence and generated desk diagnostics are distinct records; do not imply that a later diagnostic was included in the original forecast snapshot.

### Price component

Call the existing `core.spot_history.select_spot_history` at the diagnostic boundary. It fences report dates, orders rows, collapses exact duplicates and rejects conflicting or wrong-pair bars. Validate arithmetic results too; finite inputs can overflow in a sum or ratio. Do not mutate inputs. Retain selected source/session metadata.

Let `S` be the close of the latest eligible supplied bar. Select the last 40 distinct eligible observations, including `S`; return:

- `latest_close`, `latest_close_date`, `price_observation_count` and `mean_window_start/end`.
- `mean_close_40_observations = sum(close_i / 40)` for exactly 40 observations.
- `close_vs_mean_pct = 100 * (S / mean_close_40_observations - 1)`.

Both quantities use quote currency per base currency. Positive deviation means the current supplied close is above the supplied close mean. It says nothing about anybody's profit, an entry benchmark, overvaluation or expected reversal. Preserve the signed value, not just its absolute distance. Name the UI “Close vs 40-observation mean”; only rename to “40-session mean” when a calendar proves consecutive session coverage. No claim of eight weeks. An arithmetic mean does not have exact reciprocal-pair symmetry; do not assert it.

No spot yields `missing_spot`; fewer than 40 observations yields `insufficient_price_observations` for mean/deviation while preserving latest close. Conflicting rows yield `conflicting_spot_observations`; invalid arithmetic yields `invalid_price_value`. Missing COT never suppresses a valid price component. The date fence alone is `report_date_only`, not point-in-time acceptance. Existing `SpotBar` receipt/session fields help, but do not automatically establish availability or provider finality.

### Positioning component

Only EURUSD and USDJPY have supported COT diagnostics under the current contract. USDINR yields `unsupported_cot_pair`; preserve its price component. Reject present INR positioning from use rather than treating it as zero.

For each supported pair, select rows with `row.date <= as_of_date`, then the latest distinct report. Validate dates and integer contract counts (no bools, floats silently truncated, nonfinite values or numeric strings). Collapse identical duplicates; conflicting observations for the selected measure in the declared window make that measure unavailable. Rows from other pairs do not select the anchor. Compute `report_age_days = as_of_date - report_date`; it cannot be negative. This is elapsed report age, not freshness certification. Do not hide an old report by assigning age zero on each daily carry-forward.

Preserve distinct named measures:

- `supplied_net_contracts = anchor.net_long`, with `category_status = unknown` unless evidence identifies the actual report/category. The value remains useful as a description of the supplied row, not a verified institutional net.
- `asset_manager_net_contracts = anchor.asset_mgr_net` and `leveraged_funds_net_contracts = anchor.lev_money_net`, independently nullable. Never fill one from another or from `net_long`.
- `am_minus_lm_contracts = AM - LM` only if both exist. This is a between-category difference, not the aggregate position sign.
- For a specified homogeneous measure, `net_change_contracts = x_current - x_previous` using the previous distinct supplied report; expose both dates. Do not call this profit or a daily flow.

Default the new diagnostic's derived rank to null with `category_provenance_unknown`. Keep the already published scalar percentile in its original immutable signal evidence, explicitly as an unqualified supplied input; do not join it to the newly selected anchor or certify it as this diagnostic's rank. This is the recommended bounded implementation for the present input types.

If homogeneous provenance is supplied in a future extension, an optional relative rank can preserve the existing empirical convention: select at most 156 distinct reports including the anchor, require at least eight earlier reports, and calculate `p = 100 * count(x_i <= x_anchor) / N` over those earlier reports. Emit `reference_count`, `reference_start/end`, `rank_method = prior_empirical_cdf_leq`, measure and category identity. All-tied history gives 100 under this rule, not zero position or extreme risk; disclose the convention. `insufficient_cot_history`, `conflicting_cot_observations` and `category_provenance_unknown` remain distinguishable. Named AM/LM histories avoid the known mixed-field fallback, but still lack source-format and release qualification today. No new rank calculation is needed to deliver useful raw-net and price descriptors, and this repair must not silently change the repaired directional model's inputs or select a new hypothesis.

### Direction alignment, without a pain scale

Consume the actual frozen call's `predicted_direction`: `BULLISH -> +1`, `BEARISH -> -1`. NEUTRAL is an abstention; missing/invalid direction is unavailable. Do not reconstruct it from regime text, rate labels or substrings. Preserve abstention separately from missing direction.

For raw **net contracts**, let `s = +1` for EURUSD and `s = -1` for USDJPY, and `e = sign(s * net_contracts)`. The value of `net_contracts` decides reported net-long/short/flat; historical rank never decides that sign. The exact unit of `s * net_contracts` is “pair-oriented source contracts,” not spot notional or a comparable cross-pair exposure size.

Return `call_vs_reported_net = same_direction` if `d*e = +1`, `opposite_direction` if `d*e = -1`, `reported_net_zero` if `e = 0`, `call_abstained` for NEUTRAL, otherwise unavailable with reason. Apply this separately to each named category if offered. JPY leveraged-funds alignment is useful when its actual field is present; it does not demonstrate a carry trade, leverage level or unwind probability. EUR AM and LM remain separate; do not invent an aggregate from AM-minus-LM.

If a continuous rank comparison is later required with qualified homogeneous history, the honest optional quantity is `call_vs_relative_rank_alignment = d * s * ((p - 50) / 50)`, range [-1,1], with the above measure metadata. It compares the call with historical relative position rank, not with actual net exposure. Do not map it into 0–100 pain, threshold it as risk, or use it to rank pairs. This is a future formula, not part of the recommended immediate implementation. Use the categorical raw-net comparison now; derived rank and rank alignment stay unavailable.

### Availability and prohibited claims

Today's `CotRow` cannot prove what was known at publication. Return `source_availability = unknown`, `point_in_time_eligible = false`, `qualification_reason = cot_release_metadata_missing` for its observation-only diagnostics. Provisional values may remain in research telemetry and be displayed with their report date and an explicit unverified-availability label. They may not become a historical published-time fact, a directional input newly promoted by this repair, or current risk advice. If the public surface cannot carry that qualification next to the number, show unavailable there while retaining the useful value in research telemetry.

Future accepted live diagnostics require contract/report/category/format identity, observation date, actual released-at and retrieved-at evidence, vintage/raw fingerprint and an explicit UTC cutoff, with both release and receipt no later than that cutoff. Historical information-available reconstruction must identify its different provenance and cannot fabricate historical receipt times. A date-only release needs the research contract's conservative documented policy; do not guess intraday availability. Source age policy must be explicit and separate from the existing arbitrary seven-day report-age flag. Unknown release history cannot be repaired by a hand-coded three-day lag, treating future reports as fresh, or trusting today's retrieval as a past vintage.

Always return `pain_index = null`, `participant_cost_basis = null`, `underwater_triggered = null`, with `participant_entry_positions_unavailable`. Retire `vwap_8w`, `vwap_distance_pct` and `underwater_vol_buffer_pct`; do not populate them with the new mean/deviation. Carry, implied volatility and RVOL cannot change these nulls. Existing volatility/RVOL can remain separately named source descriptors with verified units and provenance; positive implied-minus-realized volatility is not a measured squeeze, and a volume ratio is not institutional conviction. Do not invent a calibrated cutoff.

## Production migration that this contract requires

1. Replace the active calculation in `asymmetry.py`; remove `_regime_direction`, `_vwap_8w_base` and `_cumulative_swap_return_price` from the production path. A retained compatibility wrapper must delegate to the corrected descriptor result and return null legacy quantities. It must never execute the old equations. Reject unknown pairs and malformed present inputs. Use one authoritative descriptor calculation, not competing legacy/new branches.
2. Scheduler passes `call.predicted_direction` and `persisted_call_id`, stops constructing pain-only carry, and stores the versioned descriptors and reasons. Its exception path must preserve independent data where safe and mark diagnostic failure, never “underwater false” or healthy/no-risk. Both AI batch and fallback paths receive the same versioned evidence.
3. Remove unsupported Apex use, including the preliminary score and yesterday-incumbent hysteresis. Null `apex_score` and `global_rank`, with a telemetry reason. Retire or change the old callable ranking helpers so another entrypoint cannot still invoke pain-as-zero. Do not quietly make a new confidence-only target ranking or rename a positioning distance Apex. Stable pair order is presentation, not rank. Compute basket correlation from the locked pairs independently if retained.
4. Change fallback and prompt together. Prefer deterministic descriptor formatting for this small field: for example, “Reported JPY net: +100 contracts; opposite to call; availability unverified.” No ELEVATED, CONTROLLED, squeeze, institutional conviction or VWAP breach can come from these diagnostics. A new descriptive brief key needs a version and parser update. If retaining `squeeze_risk` temporarily for transport compatibility, its content must explicitly say the quantity is unavailable and the UI label must become “DIAGNOSTICS”; it must never infer safety from null.
5. Update typed telemetry, `queries.ts`, `DeskCard`, compare views, Apex/rank badges and sort paths. Remove both the pain-number panel and the null-to-no-divergence branch. Show the actual supported price/position fields with their own qualification. Legacy raw records and AI strings remain stored, but the current reader must suppress unsupported pain/squeeze/Apex claims or label them historical unvalidated output. Do not relabel a legacy pain number as a corrected diagnostic. A whitelist of versioned descriptor fields is safer than passing old free text through unchanged.
6. Remove stale tests that assert fabricated economic meaning only after replacing them with the independent cases below. Search production code, prompts, public text and methodology claims for pain, underwater, cost basis, VWAP, squeeze, Apex and ranking. Passing a new local unit test alone does not prove every consumer migrated. No history rewrite, new forecast coefficients, statistical calibration or release is implied.

## Independent counterexamples and rejection tests

These are synthetic acceptance fixtures, not live evidence.

| Case | Hand-computable expected result / rejected claim |
|---|---|
| Same net, opposite P&L | Both cohorts report net +100 and current price 100. Cohort A entered at 90, B at 110. Per-unit price P&L is +10 versus -10. Identical supplied COT/spot histories cannot identify participant pain. Always null pain/underwater. |
| High percentile, still short | Earlier nets -900,-800,-700,-600,-500,-400,-300,-200; anchor -100. `p=100`, but anchor is net short. EUR pair exposure sign is negative, JPY pair exposure sign positive. A >=50 percentile long test must fail. |
| Low percentile, still long | Earlier nets 200,300,400,500,600,700,800,900; anchor +100. `p=0`, yet actual net is long source currency. EUR sign positive, JPY negative. |
| Category difference is not aggregate sign | AM=-100, LM=-200 gives AM-minus-LM=+100 while both categories are net short. A positive difference cannot label the cohort net-long. |
| Raw-net versus rank alignment | EUR bearish `d=-1`, anchor -100 in the high-percentile example: raw-net alignment is same_direction; optional rank alignment is -1. They measure different things and must have different fields. |
| Pair conversion | Raw +100 and BULLISH call: EUR same_direction; JPY opposite_direction. Changing regime text alone must change neither. A JPY BEARISH call reverses only call alignment. |
| Neutral and missing | NEUTRAL yields call_abstained; missing yields unavailable; raw zero yields reported_net_zero. None is a measured zero-risk score. |
| Mean versus VWAP | Trades at 90 with quantity 1 and 110 with quantity 9 have arithmetic mean 100, VWAP 108. A close mean must not be labeled VWAP. For 20 closes at 90 then 20 at 110, mean=100 and latest-close deviation=+10%. |
| Spurious carry | Forty closes at 100 and a 3.65 percentage-point spread create old daily addition 0.01, total 0.40 and fake cost basis 100.40. Correct mean stays 100 and deviation zero regardless of carry inputs. |
| Missing COT | Forty valid closes still yield mean and deviation; COT and alignment alone are unavailable. This catches blanket disabling of useful diagnostics. |
| Future/ordering fence | Add later-dated COT and spot with extreme values; reverse input order. Cutoff output and latest eligible dates stay unchanged. Conflicting same-date observations reject instead of choosing input order. |
| Report versus release | A Tuesday-dated row does not become eligible on Tuesday, Thursday or an assumed Friday. Without actual release evidence every such output remains provisional. A holiday-delayed release cannot pass an ordinary Friday assumption. |
| Date-window honesty | Forty observations spread across twelve weeks still say 40 observations, not eight weeks or contiguous sessions. Thirty-nine observations keep latest close but no mean. |
| Rank convention | Eight equal earlier values and equal anchor produce p=100 under <= CDF, while raw net may be zero. No crowding-risk label may follow. Eight distinct earlier dates are needed; eight duplicate copies count once. |
| Invalid inputs | Unknown pair, bad dates, bools/nonfinite numbers, invalid contracts, conflicting source observations and arithmetic overflow cannot produce a numeric diagnostic. Independent valid components survive only with explicit per-component reasons. |
| Legacy rank leakage | Confidence=.5, velocity=0: old pain=0 gives Apex .3, pain=100 gives .7. New output is unavailable in both cases. Neither null pain nor an optional alignment value can silently enter ranking. |
| UI and AI missingness | New and legacy null/low/high pain rows cannot render “No extreme divergence,” “CONTROLLED,” “ELEVATED,” or “ASYMMETRIC SETUP DETECTED.” Verified descriptive fixtures still render their actual number and date. Prompt and fallback must agree. |

Recommended review order: parent approves this measurement contract; implementation impact checks cover the touched functions; focused descriptor/consumer tests run; independently inspect the production call-to-telemetry-to-AI-to-public path; then run the project's required regression gates. No statistical test can recover the missing participant entry book from these inputs.

Research used Agent Reach's Exa search and official CFTC/CME pages, followed by direct source inspection. GitNexus MCP is reported blocked by storage/runtime version mismatch (42/40), and CLI query by missing FTS support; this read-only leaf used direct source fallback and edited no function, so no symbol impact claim is made. No relevant FX Regime Lab memory entry was found in the quick registry search. No local or deployed acceptance is claimed.
