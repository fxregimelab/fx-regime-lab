# Crowding description contract

27 September 2026. Packet19 repairs the economic meaning and consumers of the old pain index. CFTC position counts and a mean of closes do not identify participant cost basis, profit/loss or squeeze probability. This contract replaces those claims with separate provisional descriptions. It does not change frozen forecasts or rewrite original publications.

## Pure calculation

Add `compute_crowding_diagnostic(*, pair, as_of_date, predicted_direction, cot_rows, spot_bars, call_id=None) -> dict[str, Any]` in `pipeline/src/analysis/asymmetry.py`. Accept only locked pairs (slash aliases may normalize). `predicted_direction` is the actual frozen call value BULLISH, BEARISH, NEUTRAL or None; never derive it from a descriptive regime label. Reject invalid pair/date/direction configuration. Optional call_id must be a positive JavaScript-safe Python integer (not bool) or None; preserve it in output to bind the descriptor to its frozen call. Missing direction is not neutral.

Output exactly these named components, retaining keys with null values:

- `version`: `crowding-description-v1`; `pair`; `call_id`; `as_of_date` ISO date; `predicted_direction`.
- `cot`: `status` PROVISIONAL or UNAVAILABLE; `report_date` ISO or null; `report_age_days`; `net_long`; `asset_mgr_net`; `lev_money_net`; `pair_direction` (-1,0,+1 or null); `alignment` ALIGNED, OPPOSED, ABSTAINED, FLAT_REPORTED_NET or UNAVAILABLE; `series_definition` UNKNOWN; `release_status` UNVERIFIED; `rank_percentile` null; `reasons` string list.
- `price`: `status` PROVISIONAL or UNAVAILABLE; `latest_date`; `spot`; `mean_close_40`; `observation_count`; `relative_to_mean_pct`; `reasons` string list.
- `participant_loss_estimate`: null; `squeeze_probability`: null; `point_in_time_qualified`: false.

For EURUSD and USDJPY, select the latest distinct supplied COT report date at or before as_of. Ignore future/other-pair reports. Exact duplicate reports collapse; conflicting latest reports make that component unavailable without silently selecting an older report. Missing/invalid current net data must not fall back to older data. Validate net integers (booleans, strings, non-integral values and values outside JavaScript safe integer range reject); preserve observed zero. Keep AM and LM separate; their missing/invalid values remain null with explicit reasons. `net_long` is called supplied reported net: the parser can populate it from different categories, so do not label it Non-Commercial, institutional, skilled, or leveraged. Positive EUR futures net maps to positive EURUSD; positive JPY futures net maps to negative USDJPY. Alignment compares that signed direction with the actual frozen forecast; neutral is ABSTAINED. USDINR has no supported COT feature and remains unavailable even if supplied rows claim otherwise.

Do not recompute or certify a category-consistent percentile from legacy rows whose report/category/vintage identity is missing. `rank_percentile` remains null with CATEGORY_PROVENANCE_UNAVAILABLE; supplied legacy percentile remains in original signal evidence elsewhere. Report age is descriptive calendar days, not a fabricated release date or a fresh/stale trading rule. Even a recent valid report is provisional because CotRow has no released-at/source-vintage metadata.

Price calculation is independent of COT availability. Use the real `select_spot_history` validator to order/de-duplicate/filter as_of; invalid price history makes only the price component unavailable. Preserve latest eligible price and date. `observation_count` is the number of observations in the last at most40; require40 for `mean_close_40 = sum(close_i / 40)` and `relative_to_mean_pct = 100 * (spot / mean_close_40 - 1)`. Validate finite arithmetic. These are40 supplied observations, not necessarily40 trading sessions or8 calendar weeks. This is an arithmetic mean, never VWAP or participants' entry price. No yield-spread carry adjustment, volume gate or IV/RV gate enters this price description. Missing COT must not erase valid price descriptors; missing price history must not erase valid supplied positioning.

Retire `compute_pain_index` explicitly with a clear RuntimeError directing callers to the new API; delete its unsupported scoring, VWAP/carry helpers and label-derived direction logic after impact checks. No replacement0-100 risk number is introduced. New schema versions and declared data limits carry meaning; tests are not economic calibration.

## Immediate consumers

Scheduler calls the new API with `call.predicted_direction`, adds the complete payload as `telemetry_audit.crowding_diagnostic`, and sets legacy `pain_index` and `underwater_triggered` to null. Remove the diagnostic-only carry reconstruction. Diagnostic failures preserve explicit unavailable status. Do not make failure imply no extreme divergence. No original call or validation row changes.

Retire the unsupported composite Apex ranking functions: `compute_apex_score` returns None and `assign_apex_ranking` returns an empty list, with explicit retired documentation and invariance tests against pain/confidence/previous rank. Remove production rank-history reads and target-ranking logs. New desk cards store null global_rank/apex_score and telemetry `ranking_status=UNAVAILABLE_UNVALIDATED_MODEL`; a missing pain value must not become a zero ranking input. Do not invent a new confidence-only investment ranking. Existing descriptive correlation helpers are outside this change; absent rank-based cluster computation must be recorded unknown rather than asserted absent.

AI brief API keeps compatibility arguments but does not send the unsupported pain number as evidence, label risk controlled/elevated, or infer participant loss from positioning. Deterministic fallback uses `Participant losses and squeeze probability unavailable`. Enforce that exact factual boundary on the returned `squeeze_risk` field even when a mocked model supplies invented risk text. Do not suppress valid bias/catalyst fields or call paid AI during tests.

Public desk cards display the new provisional reported-position alignment and signed price-to40-observation-mean deviation where available. Missing/malformed/legacy payloads show unavailable, never no-risk reassurance. Do not display old pain/apex/rank-jump numbers as current verified metrics. Do not rewrite stored historical rows; current presentation must clearly avoid treating legacy unsupported estimates as accepted research. Ignore old squeeze-risk assertions when rendering the corresponding brief field; retain other valid fields. Preserve layout/style identity and avoid unrelated redesign.

## Required independent checks

Positive EUR net and positive JPY net have opposite pair orientation regardless of regime strings. A negative raw net remains negative even if an old percentile would be high. Actual forecast disagreement is OPPOSED, not estimated loss. Neutral, missing forecast, zero net, missing category values, future reports, same-date conflicts, invalid numeric types, INR unsupported COT and missing releases are separate cases. Price mean/deviation is hand-computed, independent of trade volume/carry, sorted and fenced; conflicting rows reject only price. Future data cannot improve freshness or shift means. Source objects are not mutated.

Cross-consumer tests must exercise actual scheduler diagnostic integration, null persisted legacy quantities, rank invariance/retirement, actual fallback/model-response enforcement and rendered public output with legacy high pain/apex, malformed payload, valid signed descriptions and missing inputs. Required regression checks include pipeline pytest/Ruff/MyPy and frontend tests, TypeScript, Biome and build. No network data acquisition, credentials, production writes, paid AI, external messages, commits or release are needed.

Parent consumer audit addition: unused sync/async Apex LinkedIn AI entrypoints must reject before model access. The existing deterministic published-regime share note remains available. No shared or posted message is sent in this repair.

Arithmetic failure retains the latest validated price/date and count with price status UNAVAILABLE, null mean/deviation, and INVALID_PRICE_ARITHMETIC. Readers must preserve the independent COT component for this shape.
