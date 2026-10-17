# AD specification 02 — Inputs, pre-calculations and exact setup rules

**Provider contract:** observations/features. All thresholds below are proposed initial
engineering values, not measured alpha. Freeze them in a versioned manifest before
evaluation. A missing input produces UNKNOWN/NO_CANDIDATE, not an invented fallback.

## 1. Observation source contracts

### Broker and clock

Read explicit allowlisted symbol tick/account/instrument/positions/orders/deals through
a read-only adapter; only the executor may send modifications. Record account currency,
trade mode, login/server fingerprint, hedging/netting mode and terminal identity.
The split-child architecture requires hedging mode; netting is a blocker, not an automatic
fallback. Never infer demo status from a server name containing the word “Trial”.

Clock profile: capture broker epoch, raw UTC computer epoch, terminal-reported time and
their uncertainty on at least three samples spanning a bar close. Verify an official MT5
timestamp contract against observed bars. Record conversion once in a profile; do not
blindly subtract the broker's display offset from a timestamp already in UTC. DST/offset
disagreement invalidates profile. Simulation clocks are injected, never `datetime.now()`.

Admission defaults: tick age ≤2s; account/position/order/deal reconciliation completed
≤5s ago; clock uncertainty ≤1s; conversion quote ≤2s. Any future timestamp beyond
uncertainty, unknown clock or frozen feed blocks entries. Weekend feeds can be healthy
for archives but never masquerade as an executable quote.

### Completed bars

Collect D1/H4/H1/M15 at broker position 1 or confirmed completed-bar endpoints. Persist
open/close timestamps, available_at, acquisition time, original epoch and clock profile.
At decision t, use only bars with `close_at <= t` AND `available_at <= t`.
No joining a daily close that is still in progress at an intraday decision.

Bounded decision windows: D1 260 completed bars, H4 120, H1 256, M15 128. Minimums:
D1 60, H4 40, H1 60, M15 32; below minimum → no candidate. Historical market closures
are allowed gaps using the broker session calendar; unexplained gaps inside the last
20 H1 or 32 M15 bars block the pair. Never forward-fill OHLC for signals or fills.
Snapshot bar payload is immutable even though `paper/store.py`'s cache remains refreshable.

Sanity: positive finite OHLC, low ≤ open/close ≤ high, unique ascending times, correct
pair/TF, nonnegative volumes/spreads. Cross-feed disagreement >3× last-20-bar median
spread triggers a source incident and shadow-only mode until checked; lack of second
feed is explicitly recorded, not falsely claimed cross-validation.

### Pipeline signal context

Read published `2.0-live`, `data_source=live` records for the two pairs with DQS≥.8.
Require publication/availability time and original signal/model/version fields. Use the
latest available call within two broker trading sessions; a holiday is not a fabricated
new call. Stale/contradictory versions block the affected setup. Archive the row used.
Never alter `regime_calls`/`validation_log`; private strategies cannot revise public calls.
Backfilled rows remain a separate cohort and are not called live outcomes.

### Calendar

Use a registered authoritative feed with exact aware release timestamps, currency,
impact tier, event ID, revisions, actual/forecast/prior and retrieval status. Terminal
calendar availability/entitlement must be verified by integration tests; do not invent
RPC tool names. Input coverage must cover t−15min through t+24h for USD plus pair currency.
Calendar refresh ≤5min in session; release-minute updates archived without lookahead.
Unknown impact/time/currency coverage is a blocker. The public macro-calendar's approximate
fallback schedule is research context only and never the execution-blackout authority.

No entries within ±15min of a red release or within its next 2h. No event-cohort exemption
in initial execution: source cohort S5 and SU-R1 stay research-only. Management continues
during blackouts; it does not wait for an AI opinion to honor a stop or reduce exposure.

### Headlines and source coverage

Approved collector queries both relevant currencies and central-bank/rate/inflation/
intervention themes. Persist query, source family, result status, original text/hash,
published_at, first_seen_at, retrieved_at, revisions and licensing restrictions.
Coverage has expiry ≤5min for entries; the intraday evidence window is t−4h..t.
Two independent publisher families preferred; domain count alone is insufficient because
syndication exists. Preserve primary statements even if older than 4h as macro context,
not as fresh headline coverage.

No results + verified successful feed coverage means “no qualifying new items”, not proof
no news exists. Current `ResearchPacket` requires two cited items; if that requirement
cannot be met, stand down in v1. Any later verified-empty-coverage schema extension
requires a protected contract change and tests; the model cannot fabricate two articles.
Conflicting sources retain both claims with timestamps; dedupe by normalized story IDs
but keep independent corroboration. Source text is data, never instructions to call tools.

## 2. Frozen feature computation

Create `FeatureSnapshot` with schema/feature version, decision cutoff, all input hashes,
named units, validity flags and deterministic calculations. Persist before AI analysis.
Exact calculation repeated on identical bytes/build yields identical canonical output.
Future rows appended to source must not change any earlier cutoff's features.

**ATR14_H1:** mean of last 14 true ranges; TR_i=max(H−L, |H−previous close|,
|L−previous close|). Need 15 bars; no Wilder smoothing under the same feature name.
**EMA20_H1:** v2 seed is SMA of the first 20 closes of the fixed last-256-bar window;
then EMA_i=(2/21)C_i+(19/21)EMA_(i−1). Legacy `checklist.ema` seeds at the first value;
do not silently mix these definitions. A feature-v2 migration needs golden fixtures
and re-evaluation of every artifact trained on the legacy feature.

**Fractal swings:** k=2 unique high/low in the ±2-bar window. `swing_at` is the pivot
time, `confirmed_at` is the close of pivot+2; never emit earlier. Ties are not single
swings. Long structure: latest two confirmed highs and lows both increasing; short
mirror. Flat/mixed = neutral, insufficient = unknown, opposite trend = opposed.

**Pools:** confirmed H1/H4 swings, prior completed broker session H/L, major figures;
equal-high/low cluster requires ≥2 confirmed extrema within .1×ATR_H1, separated by
≥3 H1 bars. Keep cluster range and constituents, not an invented point estimate.
Major grids: EURUSD .0100, USDJPY 1.00; minor .0050/.50 are annotations, not walls alone.
Only confirmed levels within the declared lookbacks; no full-history stale-level scan.

**Execution geometry:** pip .0001 EURUSD/.01 USDJPY; tick size comes from instrument.
Stop ≥1.2×ATR_H1; stretch |entry−EMA20|≤2.5×ATR_H1; significant opposing structure
≥1.25 initial-R away. Level equal to entry is zero room, not excluded as “open air”.
Adverse pools within stop_distance+ATR_H1 require stop beyond pool by ≥.25ATR.
Round stop outward BEFORE admission; if rounding violates cost/leverage/room or broker
distance, skip. This does not permit widening stops after entry.

**Costs:** cost_bps excludes separately measured slippage. Estimate spread from current
bid/ask, commission from verified account terms/deals, expected swap if holding overnight,
and adverse-slippage p95 by pair/session from at least 100 observed quote/fill samples.
Until measured sample exists use a protected conservative stress model and remain shadow;
do not label config defaults measured. H4 gate: total round-trip cost-price / stop_distance
≤.10; convert account-dollar costs to equivalent price using broker valuation, not a
USDJPY-EURUSD shared pip-dollar assumption. Do not count commission/spread twice.

## 3. Model-independent opportunity stream

At each newly completed M15 bar during session, create a unique opportunity key
`(pair, M15_close, opportunity_rule_version)` before consulting champion/challenger.
Deterministic rule engine may emit zero or several setup candidates. Snapshot once;
models share that evidence. Registered precedence SU1, SU2, SU3, SU4 resolves same-side
duplicates at the same bar; opposite-side conflict → wait, not two offsetting entries.
Record every opportunity, including no candidates, rejected gates, model timeouts and
no-trades. Re-evaluating the same opportunity is not another independent sample.

## 4. Deterministic initial setup definitions

These close the prose ambiguity in the playbook. They are hypotheses requiring tests
and evaluation, not assertions that these patterns predict profits. Default parameters
are fixed for the initial artifact; allowed evolution ranges live in specification 04.
Prices below are confirmed completed bars. Long rules shown; short is exact sign mirror.
Require D1 aligned for SU1–SU3; no setup trades on unknown/actively opposed macro context.

### SU1-v1 — Regime-aligned pullback/reclaim

1. D1 long context; H4 rising structure. Last H1 close before trigger above EMA20_H1.
2. In last 6 completed H1 bars, at least one low touches EMA20 at that bar ±.25ATR;
   no H1 close below the latest previously confirmed H1 swing low.
3. Trigger H1 bar closes above preceding H1 high AND above its own open; its range
   ≤2ATR. M15 within next 4 bars retests trigger high ±.15ATR and closes back above it.
4. Entry next available ask after that M15 closes, within .25ATR of retested level;
   otherwise expire. Invalidation = lowest low of pullback/retest minus .25ATR.
5. Apply common stop-noise/pool/room/cost checks and all portfolio gates. No chase order.

### SU2-v1 — Sweep, reclaim and held retest

1. D1/H4 long context. Pool existed and was confirmed BEFORE sweep M15 opened.
2. M15 low crosses below pool lower bound by ≥.05ATR but ≤.5ATR, then closes above
   pool upper bound; sweep-bar range ≤2ATR. A close outside is not a reclaim.
3. Within next 4 M15 bars, retest low reaches pool ±.15ATR and closes above upper
   bound without a lower low below sweep wick. Confirm only when retest bar closes.
4. Entry next ask within .25ATR of pool; stop sweep low−.25ATR. H1 trigger is the
   registered sweep/reclaim sequence, not a generic AI declaration. Expire after 4 bars.

### SU3-v1 — Confirmed breakout/retest

1. D1/H4 aligned; resistance is maximum high of previous 20 completed H1 bars,
   excluding the proposed breakout bar. Zone uses ±.1ATR.
2. Breakout H1 close exceeds resistance by ≥.1ATR, positive body ≥.5ATR and total
   range ≤2ATR. Baseline depth/volatility checks hold; exclude a red-event window.
3. Within 8 subsequent M15 bars, low retests zone and close >resistance; no completed
   H1 close falls below zone lower edge. Entry within .25ATR of zone on next ask.
4. Stop=min(retest low, zone lower edge)−.25ATR; invalidate on zone failure.

### SU4-v1 — Neutral range rotation (experimental)

1. Pipeline context explicitly neutral, H4 structure neutral; unknown is not neutral.
2. Fixed last-24-H1 range excluding trigger has width 3..8ATR. At least two confirmed
   swing touches on each edge within .2ATR, separated by ≥3 bars; no H1 close outside.
3. Long at lower edge: M15 low within .2ATR, close above edge+.2ATR, positive candle;
   next M15 holds edge and closes above prior M15 high. Entry ≤edge+.5ATR.
4. Stop below edge/sweep low−.25ATR. Opposing edge must leave ≥1.25R room. Exit by
   range midpoint if it is reached before normal management; this exit is preregistered.
5. Grade cap B AND setup risk multiplier .5, applied once after grade/slot/operator
   scaling. If resulting risk <1%, skip rather than round risk up. Two failed rotations
   in the same frozen range/session disable it until a new broker session.

SU4's neutral exception uses a typed setup policy; do not satisfy D1 alignment by lying
about the pipeline direction. Existing boolean checklist needs an explicit compatibility
adapter with cap tests. Source cohorts and execution setups remain separate tags.

## 5. Candidate constraints and veto precedence

Order: structural input validity → setup detector → data/event/session hard gates →
setup caps → checklist grade → model supported decision/veto → independent risk.
A model cannot turn a detector false into true, change stop geometry, lift a setup cap
or reinterpret missing data as neutral. An AI veto can only reduce action.

Session UTC: entries 07:15≤t<16:15; Friday t<14:00. These derive from 07:00–16:30
with first/last 15min excluded. Weekend closed; active management always runs.
Cooldown 4h after stopped parent for same pair+side; v1 allows no discretionary exemption.
Hard hold ≤T+5 broker trading days; individual artifact may impose a shorter expiry.

Checklist grade is not a probability. A+/A requires ≥2 aligned among D1/H4/H1 and no
opposed TF; any opposed relevant TF caps B, unknown required TF blocks. SU4 uses its
own neutral applicability and B cap. H1/M15 trigger evidence is a detector output.
S9 also reports concentration diagnostics, but position/currency caps are always hard vetoes.

## 6. Pre-calculation oracle and performance tests

Create hand-computable synthetic fixtures for TR/EMA seed, swing confirmation time,
range windows excluding the current bar, pip/tick rounding and each setup long/short
on both pairs. Assert candidate count >0 in positive cases and exact reason codes in
negative cases. Add prefix-invariance test: compute at cutoff, append arbitrary future
bars/revisions, recompute against original snapshot; bytes and candidate IDs unchanged.

Feature cache key includes all input digests, clock profile, feature build and parameters.
Never reuse risk/account/news validity from a feature cache hit. Cache performance tests
must run on representative bounded windows with p95 targets from the index; optimize
only after oracle parity. No synthetic data is rendered or reported as live outcomes.
