# AD specification 07 — Verification, fault injection and graduation evidence

**Status:** acceptance contract, not a claim these tests/services already exist.
The last observed local audit baseline was478 passing tests. This documentation task
does not re-run broker or statistical experiments. Test names below are implementation
requirements in the files owned by task packets; future commands must report real exits.

## 1. Requirement-to-test ownership

- **AD-01 isolation:** T02/T12/T29; `test_ad_policy.py`, `test_ad_ai_isolation.py`,
  `test_ad_isolation.py`. Research cannot read credentials/policy keys, write protected
  files, reach raw terminal ports, issue SQL or invoke an unapproved tool. Provider retries
  never call production usage telemetry or service-role limit reads in private mode.
- **AD-02 provenance:** T05–T09/T21; snapshot, spec, broker-read, features and replay tests.
  Hashes resolve to bytes, original revisions retained, correct UTC/availability cutoff,
  future prefix cannot alter earlier features, confirmed swings appear only on time.
- **AD-03 eligibility:** T10/T11/T13/T15; detectors positive/negative long/short on both
  pairs, strict verdict schemas, neutral/opposed/unknown distinct, caps/floors enforce.
- **AD-04 parent risk:** T14/T16; sizing/reservation tests cover persistent slots, two
  children/one parent budget, pending/open/MTM/cost loss capacity and currency exposures.
- **AD-05 reconciliation:** T17/T18; executor/reconcile tests cover all ambiguous outcomes,
  client-key collisions, late deals, partial fills and stale observations.
- **AD-06 management:** T19a/T19b; manage/watchdog tests cover monotonic stops, exact
  time exits, missed heartbeats, owner/account changes and no LLM dependency.
- **AD-07 accounting:** T20; settlement and existing operator-score tests cover immutable
  net R, cost corrections, parent dedupe and safety history across identity changes.
- **AD-08 reasoning:** T13/T25; grounded cases and untrusted input tests, format/citation
  alone insufficient; deterministic fallback identity is not concealed.
- **AD-09 evaluation:** T21–T25; nonempty replay, sealed trials, paired portfolios,
  timestamp purge, endpoint/precision/multiplicity and no target-driven extra tests.
- **AD-10 evolution:** T26/T27; artifact schema/ranges, authenticated certificates,
  atomic pointer switch, pinned existing parents, rollback cannot clear latches.
- **AD-11 operations:** T28–T30; process restart/fence/budgets/deadlines/shutdown tests
  and actual host/provider/source provisioning evidence, not config-file existence.
- **AD-12 reporting:** T20/T27/T32; correct actual/target/uncertainty/cost/incident reporting,
  no fabricated PnL for abstentions, no private data in public output or version control.

All twelve IDs must have executable tests before G3/G5. A requirement has no PASS if its
only evidence is prose, a mock used as real execution, a screenshot or a task checkbox.

## 2. Golden numeric and temporal fixtures

### Risk capacity

- E=A_d=A_w=$10,000; O600/P0/N500/C10 → reject daily capacity (1,110>1,000).
- E9,400/A_d10,000; O0/P0/N470/C10 → reject (600loss+480risk>1,000).
- Existing MTM loss600 already included in E; O measures additional loss from current
  marks, not another600 entry loss. A fixture must fail if MTM is counted twice.
- P600 with O0/N500/C10 is equivalent reserved capacity, even if broker has no position yet.
- E7,400/A_w10,000 → weekly lockout and protective-close intent; restart cannot reset it.
- $1,000 deposit correctly neutralized in performance/anchors; unclassified deposit blocks
  rather than appearing as +10% return or clearing an existing daily latch.

### Sizing (synthetic contract oracles, not actual broker pip values)

- FakeEURUSD valuation: one lot stop loss100USD plus10USD cost; budget500USD,
  step.01 → total4.54lots, children2.27/2.27, initial risk499.40USD≤500.
- FakeUSDJPY valuation: one lot stop loss200USD plus10USD cost; same budget/step
  →2.38lots, children1.19/1.19, initial risk499.80USD≤500.
- A real terminal integration MUST independently verify contract valuation for actual
  price/lot/account fields; these fake values cannot be configured into runtime.
- Total lots below twice the minimum valid child volume→skip, not an invalid split.
- Rounded risk below1%E→skip; no rounding/clamping upward to force eligibility.
- EURUSD-long and USDJPY-short are both shortUSD; two such parents block a third.
- Parent slot0 freed while1/2 remain: reserve slot0; no count-based duplicate slot2.

### Time and data

- Pivot i needs bars i+1/i+2 closed; at their earlier timestamps no confirmed swing.
- Bar close10:00Z, available10:00:02Z cannot support decision10:00:01Z.
- News published09:00/fetched10:01 cannot support10:00 decision.
- Model sees a revised source tomorrow; yesterday's frozen snapshot and result unchanged.
- Broker epoch already UTC with displayUTC+3: test must prevent subtracting3h twice.
- Day/week DST/holiday boundaries follow verified UTC anchors and broker sessions.
- Friday short SL below entry+fees is protected; a generic long comparison is wrong.

### Scores, forecasts and corrections

- Settled−1R then+1R starting100 →94 then98; netR0, not a calibrated success probability.
- p=.8 with outcomes0 and1 → meanBrier .34; no outcomes→None with n0, notBrier0.
- Profitable process breach still latches restrictions; model swap does not start anew.
- Same settlement imported twice→one score event; late cost correction supersedes net PnL
  transparently without awarding another positive trade reward.
- A1R half-close earns no parent settlement until runner/pending exposure/deals resolve.

## 3. Fault matrix F01–F20 (all mandatory)

Each fault fixture asserts journal events, pending risk, mode, broker side-effect count
and final ownership—not merely an exception. Default broker fake exposes configurable
delays, partial fills, retcodes, frozen prices and out-of-order history.

- **F01 crash before intent commit:** no broker call; reservation safely releasable only
  after durable proof intent never existed. Restart does not invent a fill.
- **F02 crash after intent before send result:** UNKNOWN, full risk retained; reconciliation
  determines outcome; no duplicate submit.
- **F03 broker accepts but network times out:** delayed deal/position eventually found;
  exactly one observed fill, no guaranteed exactly-once delivery claim.
- **F04 empty first history lookup:** stays UNKNOWN; missing comment/clientID not proof
  of failure. After60s unresolved→account latch/owner review.
- **F05 childA protected, childB rejected:** DEGRADED_OPEN, bounded cleanup/closeA;
  no replacement child at a stale price or extra parent budget.
- **F06 partial fill then cancel races full fill:** observed filled+pending quantities
  conserve lots; reservation not released prematurely.
- **F07 fill with missing/incorrect SL:** protective flatten request within5s; no model
  dependence; incident latch survives successful profitable closure.
- **F08 broker freeze rejects BE/trail:** old SL retained, action still due, monotonic
  rule never widens stop to get a success response.
- **F09 duplicate/reordered deal import:** stable parent accounting and exactly-once local
  settlement; corrected observations append rather than overwrite.
- **F10 terminal disconnect/host sleep:** stop new entries; server stops remain existing
  protection; overdue exits unresolved until actual broker observation.
- **F11 two supervisors after lease expiry:** fencing rejects stale writer/permit; watchdog
  cannot accidentally become another terminal-write process.
- **F12 disk full/journal write failure:** no fresh risk; protective best-effort path logs
  emergency actions separately and leaves integrity latch, not false SETTLED.
- **F13 tail truncation/hash corruption:** external witness discrepancy blocks startup;
  replay on an altered DB is not silently trusted.
- **F14 owner/account/server/demo-mode switch:** permits invalidated immediately; no
  raw order on a real or unexpected account even with a previously valid certificate.
- **F15 unknown/manual position discovered:** quarantine/no new capacity; no automatic
  flattening of unowned trades; owner-visible incident.
- **F16 clock rollback/future input/timezone change:** freshness invalidated, no new entry;
  simulation clock replay remains deterministic.
- **F17 stale/incomplete/guessed calendar or news:** no qualifying entry; public fallback
  does not satisfy authoritative coverage. Existing management continues.
- **F18 prompt injection/forged certificate/artifact mutation:** no policy/tool escalation;
  digest/signature mismatch rejects activation or order permission.
- **F19 AI auth/rate-limit/usage unknown/budget cap:** no infinite provider retry or
  production telemetry fallback; uncertainty reserves cost; management still operates.
- **F20 owner stop/scorepause/loss lockout during promotion/restart:** stop precedence
  wins; new champion cannot clear higher latch; missed candidates never replay as orders.

## 4. Statistical evaluator failure fixtures

- Empty output, one parent,20children from one parent or correlated overlapping trades
  cannot satisfy sample/block requirements.
- A lookahead strategy wins only when future rows are available→INVALID, not champion.
- Artifact rename/abandoned variant/fallback model change counts under protected budget.
- Development folds used for tuning never accepted as pristine final holdout.
- 10,000replicates at first-epoch alpha.00125 fail Monte Carlo precision requirement.
- Same seed/partition/input bytes produce same metrics, quantiles and verdict.
- Candidate improves over losing baseline but remains negative after costs→REJECT.
- Point estimate positive but lower bound≤δ→REJECT at completed endpoint.
- Missing labels/source entitlement or unresolved broker data→COLLECTING/INVALID as defined,
  never interpreting missing labels as favorable outcomes.
- After seeing failed endpoint, adding one favorable day/re-registering same bytes cannot
  reuse budget or original final-test certificate.
- Extreme-tail job paused/resumed keeps fixed data/seed/replicate count and no interim PASS.
- A profitable outcome cannot repair a critical reasoning permission/grounding violation.

## 5. Mutation and invariant testing

At least one deliberate mutation of each critical family must be detected during review:
same-USD `>=` boundary; risk multiplier cap; demo identity; snapshot cutoff; reservation
idempotency; stop monotonicity; certificate signature; final-endpoint test limit.
Record mutated condition, failing named test, and restored original behavior. Use surgical
patches/copies of this task's own work, never broad git reset/checkout of user changes.

Use seeded state-machine sequence tests over send/cancel/observe/restart events. Invariants:
nonnegative reconciled volumes; one active writer; reserved worst-case risk not silently
shrinking; no newly authorized trade under a latch; terminal side effects require a prior
authenticated durable intent; settled parent has no residual exposure/pending commands.
Do not add a test dependency without approval; standard pytest parameterization and
seeded generators are sufficient for the initial suite.

## 6. Graduation evidence by gate

**G0:** baseline accounted for; contract/policy/chain tests, protected file/tool boundaries,
spec bundle digests and task receipts. No demo readiness inferred from unit tests.

**G1:** actual source access/clock mapping/read-only broker evidence, archived point-in-time
samples, exact calendar coverage, measured/certified cost basis and AI no-production-write
tests. Feed absence remains a blocker even when collector code tests pass.

**G2:** all F01–F20 on fake broker, exact sizing/risk/management/settlement oracles,
restart real SQLite tests and worker-budget/isolation tests. No fake fills called demo fills.

**G3:** ≥14calendar days covering≥10trading sessions of observed shadow health; host/service/
permissions readback; restart/reconciliation drill; protected strategy evaluation PASS with
sealed forward evidence and actual statistical minimums (potentially150+trading days).
This is an evidence conjunction: the two-week health soak cannot replace statistical gates.

**G4:** .25canary, A/A+ and all effective-risk floors/limits; ≥10settled demo parents over
≥5sessions, no critical safety incidents, reconciled net costs and notifications. Absent
qualifying signals means stay collecting; never fabricate trades to finish the checklist.

**G5:** actual authorized promotion and rollback/stand-down semantics; no rewrite of open
parents or latches; all12requirements mapped to tests and observed operational evidence;
owner knows how to stop, inspect and recover. Return performance reported honestly.

## 7. Evidence quality and release record

Release receipt includes Git commit/dirty-state hashes, built code/policy/spec/evaluator
digests, dependency versions, test commands/exits, source availability, simulation versus
actual observation labels, certificate lineage, unresolved risks and owner permissions.
Secrets and full account identifiers are redacted; protected witnesses/keys remain private.

Run full repo checks from task05 after implementation phases. Do not claim green CI or
successful deployment from a local test. No network required for unit suite; environmental
tests explicitly opt in and can BLOCK graduation rather than be skipped-as-PASS.
No target-return test exists: tests verify behavior and measurement, not a promised profit.
