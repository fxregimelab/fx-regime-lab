# AD implementation task packets — small-model execution order

**2026-10-19 routing:** reconcile actual source/receipts before executing this
historical backlog. Many foundation modules now exist; old status/counts below
are not today's inventory. Payoff-first audit/repair packets and the next bound
worker task are in `docs/specs/payoff-desk/README.md`. Protected AD authority,
risk, evaluator and graduation requirements remain in force.

**Status:** proposed build backlog, not tasks already executed. Each task is a reviewable
slice. All paths below are repo-relative; Python commands run from `pipeline/` unless
stated otherwise. Test/module names prefixed `test_ad_` are NEW planned files.

## Universal packet contract (apply to every task)

1. Read index, required spec sections and actual target files; inspect uncommitted work.
2. Record inputs/dependencies/expected files and run the focused baseline.
3. Add the named regression/contract tests and OBSERVE failure for the intended reason.
   Missing import is valid for a new module; an unrelated import/network failure is not.
4. Run impact analysis before changing existing symbols; inspect direct callers. If the
   graph is unavailable, record UNKNOWN and manual references for reviewer decision;
   never claim zero impact or change a broad shared symbol without reviewed scope.
5. Implement minimum complete behavior. No passing stubs, fake broker success in runtime,
   TODO-only safety checks, disabled tests or swallowed permission/budget errors.
6. Run exact focused command, Ruff on changed files and mypy; inspect diff/secrets.
7. Independent reviewer checks requirements/negative tests. Save task receipt with changed
   paths, commands, exit codes, evidence digests and next task. Commit only reviewed
   task files if repository workflow authorizes it; do not stage unrelated baseline work.

Each bullet acceptance case below is mandatory; test function names belong in that task's
test file. Minimal acceptance counts are lower bounds, never targets to game with duplicates.
Default task attempt budget: 3 fix/test iterations or45min; exhaustion→BLOCKED receipt,
not weakened assertions. Split an oversized packet into lettered subtasks retaining its gates.

Focused command template, replacing `test_ad_NAME.py` with the literal file listed:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_ad_NAME.py -q
.venv\Scripts\python.exe -m ruff check src/paper tests/test_ad_NAME.py
.venv\Scripts\python.exe -m mypy .
```

Full phase gate commands (actual repo commands, not proposed new CLI tools):

```powershell
# Working directory: pipeline
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy .
# Working directory: web
npm run lint
npm run build
```

Document an actual build failure; do not assume the historical Windows readlink problem
applies. Latest audit build passed. New code must preserve all478 baseline tests and add
the mapped cases; test count alone is not a correctness criterion.

## Build DAG

Sequential foundation: T00→T01→T02→T03→T04→T05→T06.
After T06, data T07→T08→T09→T10→T11 and AI T12→T13 can progress independently.
Risk T14→T15→T16 needs T04/T07/T09/T13. Execution T17→T18→T19a→T19b→T20 uses it.
Research T21→T22→T23→T24 plus reasoning eval T25 use frozen data/contracts; can run
in shadow parallel to fake-broker execution development. T26 requires T20/T24/T25;
T27→T28→T29→T30→T31→T32 finishes operational graduation.
No simultaneous agents edit the same shared file; serialize writer.py/chain.py changes.

## AD-T00 — Preserve baseline and freeze the implementation ledger

**Files:** create `reports/desk/research/ad_build_checkpoint.md`; read current TASK/audit.
**Depends:** none. **Read:** index sections1–3, existing audit and source status.
**Action:** record branch/HEAD, tracked+untracked paths and which preceding audit changes
are local; run full gate commands; record tool versions and whether GitNexus works.
Never reset, stash away, commit wholesale or overwrite the prior audit by assumption.
**Acceptance:** checkpoint distinguishes observed code from proposed files; no daemon,
terminal order, production pipeline run or provider call. All previous work accounted for.
**Verify:** root `git status --short`, `git diff --check`; full commands above.
**Handoff:** baseline digest/test outputs plus exact unresolved blockers. G0 not complete yet.

## AD-T01 — Strict transport contracts and canonicalization

**Files:** create `pipeline/src/paper/contracts.py`, `pipeline/tests/test_ad_contracts.py`.
**Depends:** T00. **Read:** spec01 sections1,4,7; existing Bar/AdmissionState/ResearchPacket.
**Interfaces:** typed records named in spec01; `parse_record(payload, kind)`;
`canonical_bytes(record)`; `digest_record(record)`; stable typed reason codes.
**Fail first:** `test_rejects_string_false`, `test_rejects_nan_and_unknown_schema`,
`test_normalizes_utc_and_decimal`, `test_canonical_roundtrip`, `test_unknown_field_rejected`.
**Acceptance:** ≥12 cases cover required IDs, aware dates, strict numbers, decimal-string
wire units, every enum and extra keys. Deserialize model/broker data at the boundary.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_contracts.py -q` plus universal lint/types.
**Stop if:** schema ambiguity remains; do not create unrestricted dict aliases to pass mypy.

## AD-T02 — Protected authority loader and disabled defaults

**Files:** create `pipeline/config/desk/authority.v1.json`, `pipeline/src/paper/policy.py`,
`pipeline/tests/test_ad_policy.py`; modify `pipeline/src/paper/config.py` only for an
explicit validator/version pointer after impact review, not to alter owner limits.
**Depends:** T01. **Read:** spec01 sections2–3; index authority/budget decisions.
**Interfaces:** `load_authority(path)->AuthorityPolicy`, `verify_authority(policy, runtime)`.
**Fail first:** risk/config disagreement; demo mode not provisioned; forbidden pair; unknown
primitive; malformed hash; unpriced paid model; active mode without graduation certificate.
**Acceptance:** fixture policies contain no credentials. Default is shadow/paid budget0.
Owner risk values remain exact; the research process cannot supply a replacement policy.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_policy.py -q`; scan manifest for secrets/unsafe defaults.

## AD-T03 — Private journal facade without production side effects

**Files:** modify `pipeline/src/db/writer.py`; create
`pipeline/src/db/repositories/private_desk.py`, `pipeline/tests/test_ad_journal.py`,
`pipeline/src/paper/migrations/001_runtime.sql` (private SQLite only).
**Depends:** T01/T02. **Read:** spec01 sections5–7 and actual writer lazy-client behavior.
**Interfaces:** `open_private_desk`, `append_desk_event`, typed event read/replay methods.
**Fail first:** private open/write calls production `_client`; duplicate ID with changed
payload; corrupted head; illegal event type; failed transaction leaves half-written event.
**Acceptance:** no service-role env required; mocked production clients raise if touched;
event/head update atomic; old `paper_desk.sqlite3` bytes unchanged. Use a new temp DB in tests.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_journal.py tests/test_paper_store.py -q`.
**Stop if:** a production schema change appears necessary; escalate instead of performing it.

## AD-T04 — Durable leases, migrations and crash-safe reservations infrastructure

**Files:** modify private repository/writer facade; create
`pipeline/src/paper/migrations/002_control.sql`, `pipeline/tests/test_ad_transactions.py`.
**Depends:** T03. **Read:** spec01 sections6,8; spec03 sections4,8.
**Interfaces:** lease acquire/renew/fence, projection CAS, reservation transaction primitives.
**Fail first:** two writers both acquire authority; stale fencing write accepted; migration
half-applies; expired possible-send reservation auto-released; crash loses committed intent.
**Acceptance:** WAL/FULL settings verified; DB version mismatch fail closed; process-restart
test on real temporary SQLite (not only mocks); replay rebuilds heads/projections.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_transactions.py -q`.

## AD-T05 — Immutable snapshots and archive access isolation

**Files:** create `pipeline/src/paper/snapshots.py`, `pipeline/tests/test_ad_snapshots.py`;
modify root `.gitignore`; use writer facade for metadata mutations.
**Depends:** T03/T04. **Read:** spec01 sections1,4,8; spec02 source contracts.
**Interfaces:** `archive_snapshot(content, metadata)`, `resolve_snapshot(id, cutoff)`.
**Fail first:** hash mismatch; future available_at; symlink/path escape; revised source
overwrites old decision content; private archives show up as unignored Git files.
**Acceptance:** atomic content-then-manifest commit, collision/duplicate behavior documented;
licensed/private original content stays local; replay original bytes after cache refresh.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_snapshots.py -q`; `git check-ignore` on fixture paths.

## AD-T06 — Spec bundle loader and structured acknowledgment

**Files:** create `pipeline/src/paper/spec_bundle.py`, `pipeline/tests/test_ad_spec_bundle.py`.
**Depends:** T02/T05. **Read:** spec01 section8 and spec06 runtime prompt contracts.
**Interfaces:** `load_spec_bundle`, `validate_acknowledgment`, `required_excerpts_for(role)`.
**Fail first:** Markdown/config changed after digest; missing required clause; mismatched
bundle acknowledgment; oversized/unresolved bundle; model acknowledgment claims waived rule.
**Acceptance:** archive exact bundle bytes; bounded role excerpts include mandatory clauses;
record acknowledgment as evidence only, never as permission. Content pinning tests pass.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_spec_bundle.py -q`. Completes remaining G0 evidence.

## AD-T07 — Read-only broker protocol, clock and instrument snapshots

**Files:** create `pipeline/src/paper/broker.py`, `pipeline/src/paper/broker_mcp.py`,
`pipeline/src/paper/clock.py`, `pipeline/tests/test_ad_broker_read.py`.
**Depends:** T05/T06. **Read:** spec02 broker/clock/bars; actual installed MCP tool schemas.
**Interfaces:** semantic `BrokerReadPort` methods for tick/instrument/account/positions/
orders/deals; transport mapping tested against discovered server schema, not guessed names.
MCP primary; no automatic direct-Python transport fallback after ambiguous operations.
**Fail first:** real account despite “Trial” name; netting account; stale/future tick;
display-offset double conversion; wrong symbol suffix; missing tick value/stop/freeze rule.
**Acceptance:** offline fakes cover contracts; explicit opt-in read-only terminal test captures
redacted clock/symbol evidence; no terminal write method exposed to data/research workers.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_broker_read.py -q`; network access off by default.

## AD-T08 — Authoritative calendar/news collectors and coverage

**Files:** create `pipeline/src/paper/news.py`, `pipeline/src/paper/calendar.py`,
`pipeline/tests/test_ad_news.py`, `pipeline/tests/test_ad_calendar.py`.
**Depends:** T05/T07. **Read:** spec02 calendar/headlines; existing evidence.py constraints.
**Interfaces:** snapshots+CoverageReport, publisher-family dedupe, exact event-window facts.
**Fail first:** successful empty result called clean without coverage; guessed event date;
naive timezone; stale revision used; syndicated articles counted as independent; prompt injection.
**Acceptance:** collectors archive original text/query/status; no public calendar fallback;
two-item current packet rule enforced, verified-empty means abstain pending schema revision.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_news.py tests/test_ad_calendar.py -q`.
**Blocker:** missing authoritative-feed access remains BLOCKED, not replaced with scraped guesses.

## AD-T09 — Versioned features, completed-bar joins and typed alignment

**Files:** create `pipeline/src/paper/features.py`, `pipeline/tests/test_ad_features.py`;
modify `pipeline/src/paper/levels.py`/`checklist.py` only through reviewed adapters.
**Depends:** T07/T08. **Read:** spec02 sections1–2,6; current legacy feature definitions.
**Interfaces:** `compute_features(snapshot_ids, cutoff, feature_version)->FeatureSnapshot`.
**Fail first:** future confirmed swing used early; daily bar not closed; current macro row
used historically; wrong EMA seed silently reused; identical bytes give different IDs.
**Acceptance:** both pairs, timeframes, equal-level/round grids, clock profile and full
prefix-invariance oracles; no hidden full-history lookback or forward fill.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_features.py tests/test_paper_levels.py -q`.

## AD-T10 — Deterministic SU1/SU2 detectors

**Files:** create `pipeline/src/paper/strategies.py`, `pipeline/tests/test_ad_su1.py`,
`pipeline/tests/test_ad_su2.py`. Register setup IDs/versioned parameters via policy loader.
**Depends:** T09. **Read:** spec02 sections3–5 and exact SU1/SU2 rules.
**Interfaces:** `detect_candidates(features, artifact, opportunity)->list[Candidate]`.
**Fail first:** unconfirmed pool; expired retest; chase entry; opposed/unknown macro;
mirrored short uses wrong quote/stop; same opportunity emits duplicate parent proposal.
**Acceptance:** positive hand-oracle cases emit >0 candidates for BOTH pairs/directions;
each conjunction has a one-condition-negative fixture. No model field drives rule validity.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_su1.py tests/test_ad_su2.py -q`.

## AD-T11 — SU3/SU4 and setup-specific constraints

**Files:** modify strategies/checklist adapter; create `pipeline/tests/test_ad_su3.py`,
`pipeline/tests/test_ad_su4.py` (≤4files).
**Depends:** T10. **Read:** spec02 SU3/SU4 plus spec04 allowed variants.
**Fail first:** range includes current breakout bar; neutral confused with unknown;
SU4 given A/full risk; two failed same-range rotations re-enter; floor rounded upward.
**Acceptance:** exact lookbacks/expiry/edge rules; .5 SU4 risk applied once; source S5
and SU-R1 cannot execute; documented precedence/side-conflict policy tested.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_su3.py tests/test_ad_su4.py -q`.

## AD-T12 — Local AI telemetry, atomic attempt budgets and production isolation

**Files:** modify `pipeline/src/ai/providers/chain.py`; create
`pipeline/src/ai/telemetry.py`, `pipeline/tests/test_ad_ai_isolation.py`,
`pipeline/tests/test_ad_ai_budget.py`; private budget facade additions to writer.py are
a separate lettered subtask if file count/scope exceeds5.
**Depends:** T02/T04. **Read:** actual chain.py/client.py/rate_limiter.py; spec06 budgets.
**Interfaces:** injected request-budget/usage policy with production default preserved;
desk supplies private policy explicitly via existing AIClient chain injection.
**Fail first:** any fallback/retry touches production telemetry/read-limit RPC; failed
attempt costs nothing; cap exception caught as provider failure and retried; concurrent
attempts overspend; missing usage counted as zero; fallback identity concealed.
**Acceptance:** every actual attempt reserves before request, settles actual/conservative
usage; budget/permission/schema errors are nonretryable. No provider call needed in tests.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_ai_isolation.py tests/test_ad_ai_budget.py -q`
plus existing AI provider/client tests discovered by symbol references.

## AD-T13 — Structured research and independent evidence verifier

**Files:** create `pipeline/src/ai/renderers/desk_proposal.py`,
`pipeline/src/paper/reasoning.py`, `pipeline/tests/test_ad_reasoning.py`.
**Depends:** T06/T09/T10/T12. **Read:** spec01 decision records, spec06 role prompts.
**Interfaces:** `build_decision(candidate, bundle, local_ai_client)` and deterministic
claim/fact validator; route every AI call through existing `ai/client.py` facade.
**Fail first:** invented number with valid citation token; unknown source ID; model says
raise risk; schema extra tool request; unsupported thesis; timeout returns propose.
**Acceptance:** conservative WAIT on absent verified reasoning; bounded repair attempts;
no broker/write tools; actual model/fallback identity preserved; reasoned veto only lowers action.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_reasoning.py -q`.

## AD-T14 — Broker-native sizing and exposure valuation

**Files:** create `pipeline/src/paper/sizing.py`, `pipeline/tests/test_ad_sizing.py`.
**Depends:** T07/T09/T11. **Read:** spec03 sections2–3 and instrument contracts.
**Interfaces:** `size_parent(plan_request, broker_view, policy)->SizedPlan|Rejection`.
**Fail first:** USDJPY treated as constant $10/pip; volume rounded up; unsplittable min lot;
negative costs; missing conversion;50× gross cap bypassed by netting; margin-check error passes.
**Acceptance:** hand-oracle EURUSD/USDJPY long/short; each child valid lot/SL; risk floor
uses actual sized amount; original R and unused ceiling separated; protected stress checks.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_sizing.py -q`.

## AD-T15 — Trusted readiness facts and independent admission adapter

**Files:** create `pipeline/src/paper/readiness.py`, `pipeline/tests/test_ad_readiness.py`;
modify `pipeline/src/paper/admission.py` with validated fact adapter only as needed.
**Depends:** T06/T08/T13/T14. **Read:** spec03 sections1–3; spec07 G1/G2 checks.
**Interfaces:** `derive_readiness(service_observations)`; `evaluate_proposal(plan, broker_view, readiness, policy)`.
**Fail first:** research JSON injects readiness booleans; expired account/spec/news;
missing heartbeat; persistent owner stop; cashflow interpreted as profit; current loss counted twice.
**Acceptance:** source-backed expiry/reason codes, every legacy bool derived from trusted
facts, typed RiskBreakdown path with all-in floor/slot checks, all daily/weekly/open-cap
examples, no duplicated proposed/pending fees, and precedence tested. Preserve the old
AdmissionState API/tests; do not map all-in risk plus repeated cost into its old fields.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_readiness.py tests/test_paper_admission.py -q`.

## AD-T16 — Atomic parent slots and complete risk reservations

**Files:** create `pipeline/src/paper/reservations.py`, `pipeline/tests/test_ad_reservations.py`;
modify private repository/facade only if schema contract requires it (serialize edits).
**Depends:** T04/T14/T15. **Read:** spec01 persistent slots; spec03 section4.
**Interfaces:** `reserve_parent(sized_plan, expected_state_version)->ReservationDecision`.
**Fail first:** concurrent proposals both get last capacity; freed lower slot counted wrong;
childB gets a second full parent budget; expired post-send reservation released.
**Acceptance:** real temporary SQLite concurrency/restart tests, full pending risk included,
idempotency conflict on changed plan, parent count distinct from child/order count.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_reservations.py -q`.

## AD-T17 — Permit issuer and fake-broker executor

**Files:** create `pipeline/src/paper/executor.py`, `pipeline/src/paper/permits.py`,
`pipeline/tests/test_ad_executor.py`, `pipeline/tests/ad_fake_broker.py`.
**Depends:** T16. **Read:** spec01 permit contract; spec03 sections4–6.
**Interfaces:** protected `issue_permit`, `consume_permit`, `execute_reserved_parent`.
**Fail first:** changed/signed-old plan, replayed nonce, old fence, wrong account, expired
permit, send not preceded by durable intent, second leg unprotected, unknown send retry.
**Acceptance:** instrumented fake transport records every side effect; A observed protected
before B; no real broker writes or raw model callbacks in this task.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_executor.py -q`. Broker-write adapter remains disabled.

## AD-T18 — Reconciliation and order-state recovery

**Files:** create `pipeline/src/paper/reconcile.py`, `pipeline/tests/test_ad_reconcile.py`;
extend fake broker and executor transitions (≤4files).
**Depends:** T17. **Read:** spec03 sections5–6,8–10.
**Fail first:** history lag interpreted as no-fill; partially filled canceled order ignored;
unowned position treated as free capacity; duplicate deals settle twice; stale client comment reused.
**Acceptance:** active orders+positions+deals convergence,60s ambiguity latch, no blind
resend, late observation/cost events, projection rebuild and restart test.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_reconcile.py tests/test_ad_executor.py -q`.

## AD-T19a — Deterministic management policy

**Files:** create `pipeline/src/paper/manage.py`, `pipeline/tests/test_ad_manage.py`.
**Depends:** T18. **Read:** exact spec03 section7, playbook and protected management manifest.
**Interfaces:** `management_actions(parent, observations, clock)->tuple[ProtectiveCommand]`.
**Fail first:** early TP inferred from missing position; short BE direction wrong; trail
widens due to round buffer; AI outage disables horizon exit; promotion edits open parent.
**Acceptance:** every early-cut/time/trail/weekend condition with frozen clock, monotonic
SL and duplicate-bar idempotency, broker freeze rejection keeps due action unresolved.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_manage.py -q`.

## AD-T19b — Independent watchdog and fenced protective commands

**Files:** create `pipeline/src/paper/watchdog.py`, `pipeline/tests/test_ad_watchdog.py`;
extend executor protective command handling if needed.
**Depends:** T19a/T04. **Read:** spec03 sections8,10.
**Fail first:** two writers after failover;15s stale health permits entry; missing SL waits
for model; emergency close marks flat without broker proof; disk failure drops incident.
**Acceptance:** no second terminal-write route, predefined reduce-only commands, takeover
requires old process termination+reconciliation, protected emergency receipt handling.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_watchdog.py -q`. Completes fake-broker G2 candidate.

## AD-T20 — Net settlement and durable reward/penalty projections

**Files:** create `pipeline/src/paper/settlement.py`, `pipeline/tests/test_ad_settlement.py`;
modify operator_score.py only through explicit event/correction adapter contract.
**Depends:** T18/T19b. **Read:** spec03 section9; spec04 sections2,10.
**Fail first:** reward childA before runner closes; stop widening changes R; commission
omitted; late correction gives second win; model change resets safety history.
**Acceptance:** immutable denominator, observed net currency amounts, parent business-key
dedupe, correction/supersession replay, per-model view separated from global latches.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_settlement.py tests/test_paper_operator_score.py -q`.

## AD-T21 — Private replay from frozen records, not known-broken backfill outputs

**Files:** create `pipeline/src/paper/replay.py`, `pipeline/tests/test_ad_replay.py`.
**Depends:** T05/T09/T11/T19a. **Read:** audit replay defects; spec04 sections3–4.
**Interfaces:** `replay_artifact(artifact, sealed_snapshot_stream, policy)->ReplayResult`.
**Fail first:** source becomes available after decision; full-series feature lookahead;
same-bar stop/target chooses best path; stale macro row joined; both outputs empty passes.
**Acceptance:** golden forward-prefix parity, pessimistic OHLC ambiguity, correct partial
cost accounting and explicit nonempty baselines. Use frozen published calls where valid;
unavailable historical live signals mean insufficient evidence, not today’s model substituted.
**Scope:** existing shared simulation/calendar/eval defects remain quarantined; repair of
public pipeline modules is a separately impact-reviewed workstream, not runtime evolution.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_replay.py -q`.

## AD-T22 — Common opportunities and paired reference portfolios

**Files:** create `pipeline/src/paper/opportunities.py`, `pipeline/src/paper/benchmarks.py`,
`pipeline/tests/test_ad_benchmarks.py`; extend replay port if necessary.
**Depends:** T21/T13/T14. **Read:** spec02 section3; spec04 section5.
**Fail first:** candidate filters losing/timeout opportunities; children counted as samples;
denominator contains executed trades only; reference portfolio violates same-USD cap.
**Acceptance:**1% reference-risk portfolios, cash baseline, same fixed inputs/opportunity
keys, explicit zero/no-trade rows, paired daily returns and nonempty opportunity counts.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_benchmarks.py -q`.

## AD-T23 — Immutable trial registry and protected partitions

**Files:** create `pipeline/src/paper/experiments.py`, `pipeline/tests/test_ad_experiments.py`;
extend private writer repository transaction for registration/partition leases as needed.
**Depends:** T22/T04. **Read:** spec04 sections3–7; contracts/certificates in spec01.
**Fail first:** rename artifact resets budget; failed variants not counted; data/metric
changed after registration; model reads final holdout; restart resets epoch/error spending.
**Acceptance:**20variant/28day budget, one challenger final job, sealed windows and lineage,
timestamp purge/embargo, one fixed endpoint/test per artifact and lifetime epoch counter.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_experiments.py -q`.

## AD-T24 — Deterministic uncertainty-aware evaluator

**Files:** create `pipeline/src/paper/evaluation.py`, `pipeline/tests/test_ad_evaluation.py`.
**Depends:** T23. **Read:** ALL spec04 sections4–7; spec07 statistical fixtures.
**Interfaces:** `evaluate_trial(sealed_trial)->EvaluationResult` with exact reason codes.
**Fail first:** tiny n yields PASS; fake independent blocks; multiple looks ignored;
inadequate bootstrap tail resolution; superiority over losing baseline is sufficient;
failed frozen endpoint extends sample; stress scenario selected after seeing results.
**Acceptance:** seeded block resampling preserves pairing, finite/reproducible outputs,
all gates separately inspectable, INVALID/COLLECTING/REJECT/PASS never conflated.
Use small injectable test policies only in unit tests; production protected constants
must be asserted unchanged and final release tests exercise the real policy.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_evaluation.py -q`; benchmark chunked evaluation
resume without exposing interim results or changing the sealed replicate plan.

## AD-T25 — Grounded reasoning evaluation, not citation-token scoring

**Files:** create `pipeline/src/paper/reasoning_eval.py`,
`pipeline/tests/test_ad_reasoning_eval.py`, `pipeline/tests/fixtures/ad_reasoning_cases.json`.
**Depends:** T13/T23. **Read:** spec04 section8, actual existing reader-eval limitations.
**Fail first:** invented claim with matching token passes; judge rewrites answer labels;
fallback reported as primary model; prompt injection tool command accepted; null Brier called0.
**Acceptance:**≥100 labelled cases/category minimums, critical violations0, protected ground
truth, cost/latency metrics and forecast coverage, no production provider calls in tests.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_reasoning_eval.py -q`.

## AD-T26 — Signed evaluation certificates and atomic activation

**Files:** create `pipeline/src/paper/certificates.py`, `pipeline/src/paper/activation.py`,
`pipeline/tests/test_ad_activation.py`; private writer activation transaction if needed.
**Depends:** T20/T24/T25. **Read:** spec01 certificates; spec04 section9.
**Fail first:** researcher forges PASS; artifact changes a byte; revoked signing key;
expired cert; evaluator version mismatch; racing activation; old parent management mutated.
**Acceptance:** signed hashes/resolvable artifacts, expected-champion CAS, one active global
pointer, immutable activation event, rollback only to valid nonrevoked compatible certificate.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_activation.py -q`.

## AD-T27 — Bounded evolution coordinator and verified memory

**Files:** create `pipeline/src/paper/evolution.py`, `pipeline/src/paper/memory.py`,
`pipeline/tests/test_ad_evolution.py`.
**Depends:** T26. **Read:** spec04 sections1–3,9–10 and spec06 scientist/postmortem prompts.
**Fail first:** proposed Python accepted as DSL; out-of-range threshold; self-issued
owner release; profit target changes reward; unverified lesson stored as fact; trial cap reset.
**Acceptance:** proposals only allowlisted fields, one challenger, outcome-independent
registration, trusted promotion route, referenced facts/hypotheses separated, no write tools
or arbitrary retrieval destinations. Drift triggers reduction/rollback, never forced new strategy.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_evolution.py -q`.

## AD-T28 — Persistent local services and Prefect workflow wrapper

**Files:** create `pipeline/scripts/desk_worker.py`, `pipeline/src/paper/supervisor.py`,
`pipeline/tests/test_ad_supervisor.py`, `pipeline/src/paper/flow.py`.
**Depends:** T19b/T27. **Read:** spec06 complete runbook; spec03 startup/recovery.
**Interfaces:** command contracts in spec06; Prefect schedules research/review jobs while
local manager/watchdog run independently. No GitHub Actions, ad-hoc hidden cron or browser
session as supervisor. Provision services separately; writing Python is not installing them.
**Fail first:** reconnect replays missed entries; overlap jobs both acquire lease; cancellation
loses reservations; paused model kills management; worker env leaks credentials to research.
**Acceptance:** idempotent job runs, budget/deadline enforcement, durable health, defaultshadow,
fake clock long-run simulation and graceful shutdown that preserves protection.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_supervisor.py -q`; new CLI `--help` after creation.

## AD-T29 — Fault-injection and isolation suite

**Files:** create `pipeline/tests/test_ad_faults.py`, `pipeline/tests/test_ad_isolation.py`;
extend fake broker only; no production dependencies.
**Depends:** T28. **Read:** ALL spec07 failure matrix and spec03 state machines.
**Acceptance:** every fault ID F01–F20 in spec07 has an executable test and proof of no
extra unauthorized exposure. Actual OS/container permission test separately verifies denied
raw MT5, secrets, policy writes and model shell execution before demo graduation.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_faults.py tests/test_ad_isolation.py -q`;
mutate one hard veto and prove a test fails; restore via surgical patch before final run.

## AD-T30 — Operational readiness certificate and shadow-only soak

**Files:** create `pipeline/src/paper/graduation.py`, `pipeline/tests/test_ad_graduation.py`;
write redacted evidence in `reports/desk/research/ad_readiness_<date>.md`.
**Depends:** T29. **Read:** spec07 graduation; all external provisioning dependencies.
**Fail first:** fake-broker pass treated as real read-only terminal proof; skipped fault
test; missing source entitlement; host sleep; expired spec or zero shadow observations.
**Acceptance:**≥14 consecutive calendar days of healthy observed shadow operation
covering≥10 broker trading sessions, one verified restart/reconciliation drill and all
named failure scenarios, plus actual forward statistical gates (which may take much longer).
Human-visible evidence validates credentials/host provisioning; no new demo trades yet.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_graduation.py -q`; actual observed soak receipts.

## AD-T31 — Controlled demo canary (environmental integration task)

**Files:** tests `pipeline/tests/test_ad_canary.py`; redacted canary report only; modify
authority enablement through protected control process, never an LLM filesystem write.
**Depends:** T30 AND valid strategy certificate from T26 AND broker demo identity proof.
**Read:** spec04 section9 and complete spec03.
**Action:** enable certified demo_canary only, .25 scaling/A-A+ grade restriction; default
runner still denies real accounts. Record actual observed fills/stops/costs/management.
**Acceptance:**≥10fully settled parents across≥5trading sessions, no integrity/protection
incidents, no forced entries to meet n, all risk and outcome receipts reconcile. If signals
do not qualify, canary remains collecting. Market closure is not successful live validation.
**Verify:** `.venv\Scripts\python.exe -m pytest tests/test_ad_canary.py -q` + actual broker receipts. Unit tests
alone cannot satisfy this task. No personal/account secrets in committed reports.

## AD-T32 — Autonomous champion/challenger operation and final handoff

**Files:** create `pipeline/tests/test_ad_full_cycle.py`; update TASK/CONTEXT and redacted
`reports/desk/research/ad_acceptance_<date>.md`; no protected-rule modifications.
**Depends:** T31. **Read:** all requirement IDs/test matrix, operations/owner-stop behavior.
**Acceptance:** demonstrate one entire candidate→registered experiment→sealed evaluation→
certified promotion→demo canary→activation→settlement→score/review cycle, plus a rejected
challenger and rollback/stand-down. State which cycles are synthetic tests versus actual
forward/demo observations. Owner receives current active artifact, unresolved incidents,
budgets, restart/stop commands and honest target/actual results.
**Verify:** full commands above plus `.venv\Scripts\python.exe -m pytest tests/test_ad_full_cycle.py -q`;
GitNexus detect_changes before any commit, actual scope/secrets review and signed release
manifest. No public deployment, main merge, real-money enablement or pair expansion.

## Stop/acceptance discipline for all models

If a task requires a tool/provider/feed/credential not available, write the precise blocker
and dependency. Do not invent a tool response or implement a runtime “success” fallback.
Expected failures belong in tests/fakes only. Verified non-action is a successful safe
runtime result, but a missing implementation is not a completed build task.
