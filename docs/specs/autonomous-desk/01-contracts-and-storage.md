# AD specification 01 — Contracts, authority and private storage

**Status:** proposed v1; provider contract for authority/journal. Start at the
[plan index](../../plans/2026-10-18-autonomous-demo-desk.md). `MUST` means a testable
requirement. Existing dataclasses are baseline inputs, not proof these contracts exist.

## 1. Canonical types and numerical rules

Implement new shared records in `pipeline/src/paper/contracts.py`; validation lives at
deserialization, not just in Python annotations. Unknown fields/enums/schema versions
fail. Reject bool-as-int, NaN/Inf, missing currency, negative counts and naive datetimes.

- `schema_version`: literal `ad/1`; incompatible versions are rejected, not guessed.
- `Timestamp`: aware UTC ISO-8601 ending `Z`, microseconds optional; normalize before hash.
- `Digest`: lowercase SHA-256 hex, 64 characters; resolve and recompute before use.
- `Id`: lowercase UUID string except content-addressed artifact/snapshot IDs.
- `Pair`: enum `EURUSD | USDJPY`; `Side`: `long | short`.
- `Coverage`: `verified | incomplete | stale | unavailable`; only verified admits entry.
- `Alignment`: `aligned | neutral | opposed | unknown`; unknown is not neutral.
- `Mode`: `shadow | demo_canary | demo_active | paused`; no real-money enum in v1.
- `Money`: `{currency: 'USD', amount: '<decimal>'}`; no binary float serialization.
- `Price`, `Lots`, `RiskFraction`: positive finite decimal strings on the wire.
- Broker volume/price rounding uses Decimal and instrument step/tick size, not a
  fixed number of decimal places. Convert to legacy float APIs only in audited adapters.
- Deterministic features may use finite floats internally; canonical artifacts encode
  named precision (price tick size; indicators 10 decimal places) with no locale formatting.
- IDs cannot be used as arbitrary paths. Resolve artifacts beneath an allowlisted root;
  reject absolute paths, `..`, symlinks escaping it and overlong JSON documents.

`canonical_bytes(record)` normalizes timestamps/decimals, sorts mapping keys, uses UTF-8
compact JSON with `allow_nan=False`, and hashes bytes without the record's own digest.
The manifest includes a canonicalization version. Test round-trip byte identity.

### Stable reason-code vocabulary

Use exact uppercase codes in new transport records. Legacy lowercase admission reasons
map through a tested adapter; do not silently change existing persisted events.
Initial allowed codes, with additional structured diagnostic fields for context:

```text
OK, INVALID_SCHEMA, INVALID_NUMBER, UNSUPPORTED_PAIR, ACCOUNT_MISMATCH,
NON_DEMO_ACCOUNT, NETTING_UNSUPPORTED, CLOCK_UNVERIFIED, CLOCK_SKEW,
TICK_STALE, BROKER_STATE_STALE, SOURCE_INCOMPLETE, SOURCE_STALE,
CALENDAR_UNKNOWN, EVENT_BLACKOUT, NEWS_UNVERIFIED, SIGNAL_STALE,
MODEL_VERSION_MISMATCH, BAR_INCOMPLETE, BAR_GAP, SNAPSHOT_NOT_AVAILABLE,
HASH_MISMATCH, SPEC_UNACKNOWLEDGED, UNKNOWN_ALIGNMENT, OPPOSED_ALIGNMENT,
NO_CANDIDATE, SETUP_INVALID, RETEST_EXPIRED, ENTRY_CHASE, GRADE_INELIGIBLE,
CANARY_GRADE_INELIGIBLE, RISK_FLOOR, SLOT_RISK_CAP, OPEN_RISK_CAP,
DAILY_LOSS_CAPACITY, WEEKLY_LOSS_CAPACITY, PAIR_CAP, USD_EXPOSURE_CAP,
POSITION_CAP, DAILY_TRADE_CAP, LEVERAGE_CAP, MARGIN_REJECTED, LOT_SPLIT_INVALID,
STOP_INVALID, STOP_NOT_PROTECTED, OWNER_STOP, OPERATOR_PAUSED, INTEGRITY_LATCH,
JOURNAL_UNAVAILABLE, AUTHORITY_MISMATCH, NO_VALID_CHAMPION, CERTIFICATE_INVALID,
CERTIFICATE_EXPIRED, PERMIT_EXPIRED, PERMIT_REPLAY, FENCE_STALE, ORDER_UNKNOWN,
UNOWNED_POSITION, CASHFLOW_UNCLASSIFIED, BUDGET_EXHAUSTED, MODEL_UNAVAILABLE,
UNSUPPORTED_CLAIM, DEADLINE_EXCEEDED, TRIAL_BUDGET_EXHAUSTED, HOLDOUT_LEAKAGE,
INSUFFICIENT_DATA, INSUFFICIENT_PRECISION, SUPERIORITY_NOT_PROVEN, STRESS_FAILED,
DRIFT_SHUTDOWN, STALE_STATE, CAPACITY_EXHAUSTED, CONFLICT
```

An unrecognized reason code is a schema error; raw provider/broker messages remain
redacted diagnostics, never new instructions. Preserve multiple simultaneous reasons
in precedence order; a lower-priority recovery cannot erase another reason.

## 2. Authority manifest (protected, never proposed by an LLM)

Create `pipeline/config/desk/authority.v1.json` during AD-T02, disabled by default.
Configuration contains no passwords or keys. Fields:

- `authority_version`, `schema_version`, `created_at`, `owner_directive_refs`.
- `enabled_mode`: initially shadow; demo enablement needs a readiness certificate.
- `account_identity_ref`: protected local alias resolving login/server/demo/terminal identity.
  Runtime verifies actual account type and exact login/server fingerprint before every send.
- `pair_symbol_map`: explicit EURUSD→EURUSDm, USDJPY→USDJPYm; no suffix guessing at send time.
- Owner limits mirrored from current `paper/config.py`: slots .05/.04/.03/.03,
  grade multipliers 1/.8/.6/.45, minimum effective .01, max aggregate .15,
  daily .10, weekly .25, four parents/two per pair/two same-USD direction,
  five parent entry attempts with any fill per UTC day, gross leverage 50.
- `account_currency: USD`, UTC day/week boundaries, session/event/weekend policy refs.
- `allowed_primitive_versions`, `allowed_prompt_variables`, `source_allowlist`.
- Protected evaluator/release-policy digest, allowed execution build digest, key reference,
  human-stop marker path, service identity and journal root.
- Model/tool/token/time/disk budgets and runtime freshness policy refs.

Numeric disagreement between `paper/config.py` and manifest → fail startup, not choose
the more convenient value. Keep one loader/validator; no copies in agent prompts.
Authority files read-only to research, experiment and coding-runtime identities.
The owner's development environment remains separate from the unattended runtime.

## 3. Dependency boundaries and privileges

Research process: read approved snapshots/spec bundle; write proposal artifacts through
a narrow local API; approved network fetch tools only. No raw shell, database handle,
terminal MCP, process configuration, secrets, evaluator output signing or repository writes.
Prompt text cannot change tool permissions. Deny outbound terminal ports and arbitrary
URL/IP fetching; block private/link-local/cloud-metadata addresses and redirect escapes.

Evaluator process: read sealed data/artifacts; run installed deterministic evaluation
code in a resource-bounded worker; append results through journal API. No broker writes,
no research-generated executable code and no protected-policy editing.

Control-plane issuer/executor: protected identity with journal writes and terminal-write
capability; validates evaluator attestations; cannot source instructions from news text.
Separate watchdog: read broker/journal; revoke new-entry capability and request protective
actions. It does not grant new-entry permits or promote strategies.

Use separate OS accounts/containers and filesystem/network restrictions. Running all
roles as the same unrestricted user does NOT meet AD-01. A fake-broker prototype may
simulate isolation, but demo graduation requires a real negative-access test.

## 4. Shared records (required fields)

### SnapshotManifest

`snapshot_id, schema_version, kind, source_id, pair?, fetched_at, published_at?, available_at,
valid_from, expires_at, coverage, content_digest, content_relative_path, revision_of?,
clock_profile_digest, collector_version, licensing_class`.

Kinds: `bars | tick | instrument | account | calendar | headline | signal | features | spec`.
Content must exist before manifest commit. `available_at <= decision_at`; archive original
timestamp strings and normalized clock evidence. Coverage reasons are typed, not omitted.
Revised input creates another snapshot; never rewrites the snapshot used by a past decision.

### Candidate and decision

`Candidate`: `candidate_id, created_at, decision_at, pair, side, setup_id, setup_version,
artifact_digest, feature_snapshot_id, source_snapshot_ids, source_cohort, regime,
proposed_entry, invalidation_price, expires_at, deterministic_trigger_ids`.

`ReasoningDecision`: `decision_id, candidate_id, decision_at, verdict: propose|wait|reject,
supported_claims, bull_case, bear_case, wait_case, falsifiers, evidence_ids,
spec_bundle_digest, operator_identity, latency_ms, budget_receipt_id, rejection_codes`.
Each claim: `{claim_id, text, fact_refs: [snapshot_id#/field], derived_metric_refs}`.
No naked “confidence 92%”. Optional probability uses a registered event definition and
separate `forecast_id`; grade always comes from deterministic eligibility.

`OperatorIdentity`: provider, actual responding model, model revision if reported,
prompt digest, toolset digest, renderer version, fallback status. Unreported model
revision is explicitly unknown, never a guessed provider label.

### ParentTradePlan

`parent_id, candidate_id, decision_id, pair, side, artifact_digest, management_policy_digest,
signal_model_version, source_cohort, entry_snapshot_id, stop_price, target_a_price,
requested_risk_fraction, immutable_initial_risk_usd, initial_stop_distance,
child_specs, expiry_at, falsifiers, grade, operator_identity, spec_bundle_digest`.

Exactly two initial children `{child_id, role:A|B, lots, initial_sl, initial_tp?}`.
A TP at exactly 1 initial price-R after broker tick rounding with deviation recorded;
B has no initial TP. Both have an attached protective SL. Sum of child worst-case entry
risk and incremental reserve must not exceed reserved parent risk; reject invalid splits.

Plan is immutable after permit. Adjusted quantities/prices require a superseding plan,
new admission and new permit; do not reuse an old signed plan with changed JSON.
Management events may tighten stops/close children but cannot change initial R or thesis.

`RiskBreakdown`: `open_residual_stop_usd, pending_all_in_usd, proposed_stop_usd,
open_future_cost_usd, proposed_future_cost_usd, proposed_all_in_usd,
slot_budget_usd, immutable_initial_risk_usd, valuation_snapshot_ids`.
Proposed all-in = proposed stop + proposed future cost. Pending all-in already includes
its own reserved future costs; do not add them again in open/proposed cost buckets.
Plan risk fraction and floor/slot checks use proposed all-in/equity, never just stop loss.

### ExecutionPermit

`permit_id, parent_id, plan_digest, authority_digest, evaluator_certificate_id,
broker_state_digest, reservation_id, issued_at, expires_at, allowed_operations,
max_child_volume, consumed_sequence, issuer_key_id, signature`.

Initial default TTL 5s. Executor rechecks account/tick/stop/margin/risk before send.
Permits are locally single-use with durable consumption; a consumed permit plus unknown
broker response is reconciled, not automatically reissued. Signed changes do not waive
freshness or current exposure. Use protected HMAC-SHA256 keys for local v1 services;
research cannot read the shared issuer/verifier key. Key rotation records revocation;
persist key IDs without leaking keys. A file hash without protected authentication is
not a trade permit.

### Experiment and certificate

`Experiment`: hypothesis, parent artifact, changed fields, registration time, epoch/trial
IDs, input cohort, training/validation/holdout partition IDs, metric definitions,
cost model, random seed, stop rule, trial budget and invalidation rule.

`EvaluationCertificate`: artifact digest, experiment ID, all input/partition digests,
evaluator build and policy digests, evaluation cutoff, sample/block counts, metrics,
PASS|REJECT|COLLECTING|INVALID, reason codes, expires_at, issuer identity/signature.
No LLM-written “PASS” is consumable. Certificates expire after 7 calendar days for new
activation; active artifacts also require current runtime health/drift status.

## 5. Private persistence and the existing writer rule

All new DB mutation entry points MUST be under `pipeline/src/db/writer.py`.
Extend its facade with explicitly private operations backed by
`pipeline/src/db/repositories/private_desk.py`. Private calls accept a required local
store handle and MUST NOT call `_client()`, production telemetry or a Supabase RPC.
Existing `paper/store.py` remains the legacy cache/hash-chain implementation; AD-T03
routes new runtime writes through the facade without rewriting old ledger rows.

Proposed facade interfaces (not existing APIs):

```python
open_private_desk(path: Path) -> PrivateDeskHandle
append_desk_event(handle, event: DeskEvent, expected_head: str) -> StoredEvent
reserve_desk_plan(handle, request: ReservationRequest) -> ReservationDecision
transition_desk_order(handle, command: TransitionCommand) -> StoredEvent
record_desk_observation(handle, observation: BrokerObservation) -> StoredEvent
activate_desk_artifact(handle, command: ActivationCommand) -> StoredEvent
```

No generic model-facing SQL endpoint. Broker reservations/transitions use domain-specific
commands, not `append(kind='approved')` from a model. All service calls authenticate role.
Shared writer changes require impact analysis and production regression tests; private
calls must pass when service-role credentials are absent and production clients are mocked
to raise. Lazy imports must not create a production client while opening private SQLite.

## 6. SQLite schema and invariants (new private schema, no production migration)

Create versioned local migrations only after downstream audit, against a new runtime
database `data/desk/runtime.sqlite3`; leave `paper_desk.sqlite3` intact. Migrations are
transactional, version checked and tested on a copy/fixture; no automatic destructive rebuild.

- `events`: seq PK, event_id UNIQUE, aggregate_id, expected_aggregate_version, kind,
  happened_at, recorded_at, canonical_payload, prev_hash, row_hash, actor_id.
  Hash includes actor and both timestamps. UPDATE/DELETE forbidden to runtime API.
- `aggregate_heads`: aggregate_id PK, version, last_seq; transactionally compare-and-swap.
  Rebuildable projection; editing it cannot alter authoritative events.
- `reservations`: reservation_id PK, parent_id UNIQUE, status, amount_usd, expires_at,
  broker_pending flag, owner_fencing_token, last_event_seq.
- `orders`: child_id PK, client_order_key UNIQUE, parent_id, intended_digest, broker IDs,
  state, cumulative_filled_lots, last_observation_seq; never infer fill from send success.
- `artifacts`: digest PK, type, content path, registered_at, parent_digest, lifecycle state.
- `active_versions`: scope PK, artifact_digest, activation_seq, effective_after;
  one global champion v1, no independent pair champions with hidden shared USD risk.
- `snapshots`: snapshot_id PK, manifest digest, content digest/path, availability/expiry.
- `experiments`: experiment_id PK, epoch_id, ordinal UNIQUE within epoch, sealed spec digest.
- `job_runs`: idempotency key UNIQUE, lease owner/fence, state, deadlines, attempt count.
- `budget_reservations`: id PK, provider attempt ID UNIQUE, tokens/dollars reserved,
  actual usage, status, daily epoch. Unknown response retains reservation conservatively.

`BEGIN IMMEDIATE` + recompute current projections inside the transaction for reservation.
One worker owns the write lease; monotonically increasing fencing token on takeover.
Expired lease alone cannot release an order reservation with a possibly sent broker request.
Read-only evaluator connections cannot mutate tables. Numeric money stored as decimal
strings or integer micro-USD consistently; integer sums/overflow checked.

## 7. Event vocabulary and state-proof rules

Minimum events: `spec_loaded`, `snapshot_archived`, `candidate_detected`, `decision_recorded`,
`proposal_rejected`, `risk_reserved`, `permit_issued`, `permit_consumed`, `order_send_intent`,
`broker_observed`, `child_state_changed`, `parent_state_changed`, `stop_change_intent`,
`stop_change_observed`, `parent_settled`, `score_updated`, `experiment_registered`,
`evaluation_completed`, `artifact_activated`, `artifact_revoked`, `incident_opened`,
`incident_resolved`, `owner_stop`, `owner_release`, `heartbeat`, `cashflow_observed`.

Unique business key per settlement `(account_fingerprint,parent_id,'settlement-v1')`.
One proposal/decision event per candidate+operator artifact; retry returns original
event only if digest matches, else conflict. Correction means a supersession event;
never retroactively overwrite a bad fill, score or forecast.

Verify chain on startup and before risky transitions. Persist externally witnessed head
hashes in a protected append-only location; a chain alone cannot detect tail truncation
or an attacker who rewrites the entire DB and every local witness. Restore on a trusted
copy, reconcile broker state and require review after integrity failure.

## 8. Artifacts, spec acknowledgment and initial risk slots

Paths: private runtime under `data/desk/`; synthetic fixtures under tests; secrets outside
repo and research mounts. Reports under `reports/desk/` are redacted; runtime snapshots
may contain broker/account/private licensed content and MUST remain gitignored.
Tests must assert ignore rules for new runtime paths before collectors write data.

`SpecBundle` lists exact document/config digests, required clause IDs, allowed mode and
expiry. Runtime loader verifies content, supplies bounded excerpts to the model and
records an acknowledgment `{bundle_digest, understood_clause_ids, unresolved_conflicts}`.
Deterministic gates enforce clauses; acknowledgment alone does not prove comprehension.

Assign each parent a persistent slot 0..3 at reservation. Use the lowest free slot,
never the current count as an index once gaps exist. Reservations occupy slots.
Two children share their parent's slot. Releasing a slot requires reconciled zero
exposure and no pending send/close; another parent cannot reuse an ambiguous slot.
Legacy `size_risk(open_tickets=count)` needs an explicit-slot adapter in AD-T16.

## 9. Mandatory examples for contract tests

- A JSON string `"false"` for demo/account coverage is invalid, not truthy success.
- USDJPY stop 158.1 on short entry 158.0 is valid-side; 157.9 is wrong-side.
- Children .6 and .4 lots belong to ONE parent; neither receives the whole parent risk.
- Same `client_order_key` with changed volume is conflict, not an idempotent retry.
- A headline fetched tomorrow cannot support yesterday's candidate even if published earlier.
- Same artifact contents under another filename has the same digest/trial identity.
- A certificate signed under a revoked key or old evaluator digest cannot activate.
- Parent slot 0 closes while slots 1/2 remain: choose free slot 0 and recheck all budgets;
  do not index slot 2 and accidentally duplicate slot ownership.
