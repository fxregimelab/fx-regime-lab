# AD specification 03 — Admission, execution, management and recovery

**Provider contracts:** risk/execution/management. These are future runtime behaviors,
not claims about the current pure `admit()` function. Every broker write belongs to
the single fenced executor. A model cannot mint permits, edit reservations or call MT5.

## 1. Trusted readiness, not AI-authored booleans

Build a `ReadinessProof` from authenticated service observations: exact demo account,
hedging mode, authority/evaluator/build hashes, healthy journal/lease, fresh reconciliation,
verified clock/calendar/news/features/spec bundle, graduated strategy certificate,
operator restrictions, owner-stop state and management/watchdog heartbeats.

Derive legacy `AdmissionState` flags from that proof inside trusted code. Do not expose
an API accepting `management_ready=true` or `demo_account=true` from research JSON.
Proof binds source observation IDs and expiry. Broker facts are reread before dispatch.
Proof uncertainty, inconsistent snapshots or an unresolved incident means no entry.

The last **verified** broker view is not enough after a send timeout; reconciliation must
explicitly resolve that command's outcome or keep its ambiguity reservation.

## 2. Equity, cashflows and loss capacity

Units: USD account money. Broker equity includes executable MTM, actual accrued
commission/swap where available; document mid-versus-liquidation adjustment to avoid
counting spread twice. Read actual balance/equity from broker, never a model estimate.

Persist UTC day-start and Monday UTC week-start equity anchors. A restart cannot
reset them. Deposits/withdrawals are identified from broker deals, appended as cashflow
events and neutralized from performance/loss calculations. Unclassified cashflow blocks
entries; the system cannot call a top-up a trading profit or reset a kill switch with it.

Let E=current adjusted liquidation equity; A_d/A_w=adjusted anchors; O=additional loss
from current executable marks to each open stop; P=full unresolved/pending reservations;
N=proposed worst-case entry stop risk; C=incremental conservative cost/gap allowance.
All risk amounts nonnegative; hedge gains cannot cancel gross stop-risk reservations.

Bucket ownership is exact: P includes its already reserved costs; O/N contain stop loss
only; C contains future costs for OPEN/NEW exposure not already counted in equity or P.
Split C into C_open+C_new. The parent's slot budget and1%floor apply to N+C_new, and
`immutable_initial_risk_usd=N+C_new` after sizing/rounding. Every cost belongs to one
bucket; no additional fee is added merely because it appears in a second report.

```text
L_d = max(0, A_d - E)
L_w = max(0, A_w - E)
B = O + P + N + C
B <= .15 * E
L_d + B <= .10 * A_d
L_w + B <= .25 * A_w
```

Use current executable marks for O, not original entry loss plus already-counted MTM.
When broker reports current equity net of realized costs, C includes only additional
future costs. A BE stop can still have slippage/cost risk; do not force O/C to zero.
Missing SL → conservatively unbounded risk plus protective incident, not zero risk.

Keep a separate residual gap-stress scenario per pair and correlated USD move; both
the sum-of-stops bound and protected scenario loss budget must pass. Initial scenarios:
adverse 3×ATR_H1 from executable quote, doubled observed p95 spread/slippage, both pairs
moving against same-USD exposure. No diversification credit in v1. Authority must own
these constants; strategies cannot choose a more favorable risk scenario.

Daily/weekly limits are planning constraints, not guarantees against market gaps. At
E≤.90A_d or E≤.75A_w, immediately latch entries and request risk-reducing liquidation
through executor, subject to broker availability; retain reservations until verified flat.
Daily lockout clears only at next UTC day after fresh anchors/reconciliation and no higher
incident latch. Weekly loss lockout clears after the next Monday boundary plus a successful
protected full-review job. Integrity/owner/ambiguous-order latches do not clear with time.

## 3. Parent slot allocation and lot sizing

Reserve lowest free parent slot, persist it for the parent's life. First/second/third/
fourth slot ceilings .05/.04/.03/.03 are maximums, not required bets. Apply exactly once:
slot × grade × operator × setup × canary; every factor ≤1. Grade C/paused → no risk.
Actual effective initial risk below .01E → skip. Never round risk UP to satisfy the floor.
Loss capacity may reject a nominal 5% slot even when the 15% cap still has room.

Use broker-native valuation (`order_calc_profit` equivalent after verified adapter mapping)
for one lot from adverse executable entry to stop. Use correct bid/ask per side and
commission/expected swap/slippage; verify returned currency. A None/error/unavailable
conversion blocks sizing. Do not use constant $10/pip for USDJPY.

Calculate maximum total lots within risk budget, volume step/min/max, margin, gross
notional leverage and loss scenarios. Round DOWN to valid volume step. Split into two
valid child volumes; each ≥minimum lot and total ≤sized lots. If not splittable, skip;
there is no silent single-ticket fallback. Price rounding uses broker tick size.

Portfolio gross notional leverage includes existing and pending absolute currency
notionals, ≤50E; do not net opposite trades to hide leverage. Minimum post-order free
margin is .20E under base and protected stress margin estimate. Brokers' check/margin
functions must confirm exact proposed requests; “margin API unavailable” is not success.

Freeze `immutable_initial_risk_usd` as the sized initial stop-loss amount plus its declared
entry cost/reserve basis, not an unused larger ceiling. Keep ceiling/reserved amount
separate. Broker fills may be worse than expected: reduce unfilled volume or flatten
if actual risk exceeds permission; do not rewrite initial risk to make net R look better.
Every child has price-R target math based on the plan's initial stop distance.

Compatibility warning: legacy `AdmissionState.requested_risk_pct` is a simplified float
interface. Do not pass an all-in plan fraction AND the same proposed costs into its separate
`cost_reserve` field. T15 must add a typed RiskBreakdown-based trusted admission path,
with all-in floor/slot checks and the bucket formula above, while retaining legacy tests.
An adapter is not allowed to silently double-count fees or omit them to reuse the old API.

## 4. Reserve/permit/dispatch transaction

1. Research submits immutable plan proposal and references; no order parameters can
   be edited after digesting it without generating a superseding proposal.
2. Trusted risk validates readiness, selects a free slot and computes exact size.
3. Under SQLite `BEGIN IMMEDIATE`, read current equity/exposure/projection versions,
   reject stale observations, reserve both child budgets and consume daily/pair capacity.
   Persist `risk_reserved`; bind reservation to fence/account/plan/slot. Commit durable.
4. Issue 5s permit for exact child operations. On dispatch, verify current account and
   quotes, consume permit nonce and append send intent BEFORE external side effects.
5. Reconcile observed fills, attached stops, pending orders and actual margins. A
   broker response retcode alone is not an observed protected position.

Never release a reservation merely because its TTL expired if a request may have left
the process. Pre-dispatch expiration is releasable only with proof no send intent exists.
Post-intent ambiguity retains the full worst-case amount until broker reconciliation.
At account-level simultaneous proposals, at most one transaction can reserve the last
available capacity; the other receives typed `STALE_STATE`/`CAPACITY_EXHAUSTED`.

Initial entry-attempt daily count consumes one parent after any child receives a fill;
an unfilled rejection consumes no trade count but is logged and subject to retry budget.
Unknown outcomes conservatively consume a slot/trade reservation until resolved.

## 5. Order and parent state machines

Child states and allowed forward paths:

```text
PLANNED -> RESERVED -> PREPARED -> DISPATCHING
DISPATCHING -> ACK_PENDING | PART_FILLED | FILLED | REJECTED | UNKNOWN
ACK_PENDING/PART_FILLED -> FILLED | CANCEL_PENDING | UNKNOWN
FILLED -> PROTECTED -> CLOSE_PENDING -> CLOSED
CANCEL_PENDING -> CANCELLED | PART_FILLED | FILLED | UNKNOWN
UNKNOWN -> observed prior/forward state via reconciliation only
```

`PROTECTED` requires broker-observed SL meeting authority. Partial fills carry filled
and outstanding quantities independently; cancel remainder if its permit/price is stale.
Order status events do not substitute for position protection checks.

Parent: `PROPOSED -> REJECTED | RESERVED -> OPENING -> OPEN | DEGRADED_OPEN ->
CLOSING -> SETTLED`; `OPENING` can also settle a failed first/second leg after verified
cleanup. `SETTLED` only when all child exposure/pending volume is zero and deals/costs
reconcile. Zero-fill cancel records `ABORTED`, not a profit/loss settlement.

Store expected version for every transition; illegal backward transition or changed
account/plan is a typed conflict. Late deals are new observations, not silent history edits.
Protective exits may execute without a valid new-entry certificate but still require exact
account ownership, authenticated predefined operation and durable intent best effort.

## 6. Two-child execution and ambiguous outcomes

Send A with attached SL/TP first. Send B only after A's fill and broker-side protection
are observed. Recompute remaining permitted B volume against actual A fill/cost/exposure;
reduce only, with a new bounded child intent linked to the same reservation. If B cannot
be sent within the original entry freshness envelope, cancel unsent B and close A under
the degraded-entry policy; do not opportunistically keep an untested half strategy.

Each command has persistent `client_order_key`, parent/child IDs, magic/comment mapping
validated for the broker. Broker comments/client IDs may truncate or lack uniqueness;
they are reconciliation hints, not broker-enforced exactly-once guarantees.

After any timeout/crash during DISPATCHING: state UNKNOWN; query active orders, positions
AND deal history with overlap window; wait for consistent observations. An empty first
lookup is not proof of no execution. If unresolved after 60s, latch account entries;
owner review is required for permanent ambiguity. Never blind-resend the same intent.

Protection not confirmed within 5s of a fill: request emergency flatten through the
single executor, preserve full reservation and open a critical incident. If terminal
unavailable, retain existing broker-native stops, alert and keep trying bounded protective
reconciliation; no local code can guarantee closure of an unreachable broker position.

## 7. Deterministic management (independent of the LLM)

Loop every 5s with broker-native SL on both children. Entry/exit checks occur after
reconciliation; strategy model outages do not stop protection, horizon or time exits.
Management artifact is pinned per parent at entry; promotion affects only new parents.

- A: broker TP at +1 initial price-R. A's confirmed close at TP (not just absence from
  position list) triggers B SL→entry+1.5pips long / entry−1.5pips short, subject to broker
  stop/freeze rules. “Risk-free” wording is prohibited: costs/gaps can still lose money.
- B chandelier on new completed H1: long max(current_SL, observed_best_bid−1.2ATR);
  short min(current_SL, observed_best_ask+1.2ATR). Best quote since entry comes from
  archived executable ticks. Never use future H1 high/low to simulate an intrabar exit.
- Structure/round buffer .15ATR beyond a significant level; a 3–5pip round-number
  adjustment is permitted only if it still tightens the current stop. If geometric buffer
  and monotonic tightening conflict, retain the current protective stop and record why.
- Early adverse cut: before age2h, two completed M15 closes at or worse than −.5 price-R
  since first excursion, with no intervening close reclaiming entry → close remaining.
- Invalidation cut: two consecutive completed H1 closes beyond frozen invalidation → close.
- Time stop: at age4h, executable net progress <+.2 price-R → close remaining (not an
  arbitrary model choice of reduce/hold). Costs are reported separately and in settlement.
- Artifact expiry/hard T+5: close remaining at first executable opportunity. T+5 counted
  using verified broker trading sessions; never add five calendar days blindly.
- Session-end: if runner ≤+1R and registered alignment lost, close; hold overnight only
  under validated artifact rules, still within horizon, swap risk and calendar coverage.
- Friday19:00 UTC: close unprotected-loss parents. “SL beyond BE” is directional:
  long SL≥entry+cost buffer, short SL≤entry−cost buffer. A skipped/rejected close stays
  CLOSING, not falsely flat. Certified artifact may impose an earlier weekend exit.

News-thesis break in v1 requires a registered deterministic event-to-falsifier mapping
with archived authoritative release facts. Unsupported model alarm is advisory; it may
block new entries but cannot invent a management rule retrospectively. Never widen an SL,
average into a loser, remove protection or add a child under the same parent budget.

## 8. Watchdog, leases and safe failover

Supervisor and watchdog are separate local services; neither is an LLM agent. Watchdog
checks heartbeat every5s; three missed heartbeats/health>15s revoke entries immediately.
Only one process owns terminal-write lease. Watchdog submits predefined protective
commands; failover can acquire a newer fencing token only after old process termination
and fresh account reconciliation. Refusing an uncertain failover is correct.

SQLite WAL + `synchronous=FULL`, local disk, transactional transitions. Disk<2GB,
failed durable write, clock rollback, journal corruption or unexpected account/symbol
change revoke entries. Emergency reduce-only operations may proceed best effort when
journal unavailable; write a protected secondary emergency log and reconcile it later,
never fabricate earlier authorization. Such operation leaves an integrity latch.

Startup: no new entries until full order/position/deal reconciliation, chain/witness check,
cashflow/anchor validation, authority/spec checks and active artifact validation complete.
Unknown broker positions remain unmanaged-by-strategy; quarantine account, record them,
and request owner action. Do not close manual/unowned positions merely because a bot
does not recognize them. Missing ownership can never be treated as spare risk capacity.

## 9. Settlement and idempotent scoring

Collect broker deals for both children, commission, swap, currency conversions and partial
fills; compute parent net USD PnL once all exposure/pending fills reconcile. Preserve gross
PnL, each cost component, FX rate source/time, initial risk, holding duration and MAE/MFE.
`net_R = net_parent_pnl_usd / immutable_initial_risk_usd`; not divided by runner risk or
remaining size. A half-profit at1R is .5 initial price-R gross before runner/costs.

Append settlement and score-update business keys atomically/idempotently. Same parent
from two deal imports yields one settlement. Late fee/correction appends a correction
and recomputes derived score projection transparently without rewarding the parent again.
MAE/MFE use observed executable prices at recorded sampling resolution; insufficient
ticks produce a flagged estimate, not an exact intrabar path invented from OHLC.

## 10. Recovery classes

- Feed/model/transient network outage: entries pause, manage existing; automatic recovery
  after three healthy complete reconciliations spanning ≥60s and fresh input coverage.
- Daily/weekly loss lockout: period rules in section2; restart does not clear it.
- Invalid/revoked artifact or drift: atomically choose last still-certified artifact for NEW
  trades; otherwise shadow. Existing parents retain pinned management or protective exit.
- Scorepause/process breach, unresolved order, integrity/security or owner stop: latched;
  only authenticated owner remediation/release may lift the corresponding restriction.
  Research models may propose remediation reports, not issue releases.
- Broker outage/market closed: protect using existing server stops, alert, reconcile when
  possible; never replay missed entry signals. Time-based exits remain due until observed.

Safety-stop precedence: owner/integrity → ambiguity/protection → account/loss capacity →
operator restriction → artifact validity → input coverage → ordinary eligibility.
Recovery of a lower-priority condition cannot clear a higher-priority latch.
