# Retained administrative FPI reads — implementation contract

Packet29.1, 28 September2026. This freezes the next saved-read implementation boundary. Parent acceptance is recorded separately in the leaf ledger. It changes no code, schema, deployed consumer or published call. The prerequisite capture, complete parse, qualification-v2 and complete-reference packets are accepted locally; production deployment and the wider repair remain open.

## Meaning and authority

Implement `fpi-admin-read-v1`: an immutable record of the evidence visible to ONE database statement under the scope below. Every outcome permanently has `execution_state="UNVERIFIED"`, `acquisition_state="UNVERIFIED"`, `eligible=false` and `feature=null`. `COMPLETE` means complete within the declared scope and limits. It does not mean executable, approved, acquired through a trusted runner, historically available at a caller's chosen time, or suitable for prediction. Qualification ACCEPT remains administrative intent.

This staging preserves correctness because no selection, normalization, publication or usable feature is returned. Administrative qualification can be evaluated for inspection, labelled as such. Do not feed this type to `select_fpi` or convert it into `FpiDecisionSnapshot`. Neither hashes, a SELECTOR artifact nor a later successful recomputation can change its authority. A future eligible decision requires a NEW versioned request and NEW one-statement snapshot including actual parser-verification, release approval/revocation and capture-order observations. Do not query today's trust tables and promote an old administrative read. A retrospective experiment must disclose its later evidence and cannot claim a former live decision.

The storage server is trusted to apply its append-only protocol. A locally constructed or downloaded manifest verifies consistency only; a content hash is not proof of origin or SQL completeness. Database/service authentication and deployment checks remain necessary.

## Dependencies found in current source

| Existing dependency | What it provides; what the reader must add |
|---|---|
| Migration10 `fpi_captures` | Exact `document_json`, identity, fixed source URL, receipt times, body metadata and server `stored_at`. Capture ID binds the canonical document; stored_at is outside it. The latter is a storage observation, never commit/release time. |
| Migration11 `fpi_parse_results` | Whole canonical record, record/content hashes, capture/parser identity, definition, recorded_at, failure_reason and stored_at. Parse insertion and all its memberships are atomic. Failed parses have no dated memberships. |
| Migration11 `fpi_parsed_memberships` | membership_id, parse_id, reporting_date, value hash, complete INR document and complete source-evidence document/hash; unique `(parse_id,reporting_date)`. Parser identity comes from the parse, not this table. |
| Migration11 `fpi_implementation_artifacts` | `(kind,artifact_sha256)` identity, canonical document, body size and stored_at; only PARSER and SELECTOR, at most5MB body each. It retains bytes, not execution authority or a complete runtime. |
| Migration12 `fpi_qualification_events` | Immutable canonical v2 events, explicit unique ordinals and indexed `(scope,target,event_ordinal DESC)` heads. One qualification lock serializes appends. A sequence gap is valid; clocks do not establish order. Witnesses are inside the original event document. |
| `build_fpi_read_references` | Validates each distinct original capture and parse once, preserves ALL parse memberships and checks restoration timing/status semantics. Its references exclude database stored_at and artifacts. Those require separately bound metadata here. |
| `FpiQualificationView` | Exact candidate-universe head/absence and witness validation; no requirement to load full predecessor chains. Its canonical version/hash stays v2. |
| `fpi_selection.py` | Existing v1 policy/snapshot uses different hashes, full parse universe and timestamp-based event reconstruction. Keep it unchanged for v1 replay; it cannot consume this manifest. |

There are currently no retained policy/read tables, execution approvals, protected verification results or capture-order trust ledger. Existing date/value/parse indexes do not cover the failure stored_at range. Implement the new objects in a forward migration numbered **14 or later**;13 is reserved for timeout repair. Do not reuse the earlier proposal's `max(ordinal)+1`, array-wrapped qualification hashes or timestamp replay assumptions: actual v2 codecs/migration12 are authoritative.

Before any schema implementation, audit these sources plus writer callers, RLS/grants, current timeout repair, all original verifiers and staged/scheduler/replay consumers. This contract is not that future downstream implementation audit.

## Canonical forms and identities

All new documents are exact ASCII JSON: `ensure_ascii=True`, sorted object keys, compact separators, no duplicate/unknown/missing keys, NaN, Infinity, NUL or surrogate strings. Strings here are ASCII before serialization. Integers and booleans have exact types. IDs/digests are lowercase64-character SHA256 unless specified. Lists that represent sets are unique and lexically sorted; reject noncanonical external bytes rather than sorting them on decode. Maximum nesting32 is checked before recursive decoding. Hash `H(x)` is SHA256 of the exact canonical ASCII document bytes; the required `version` field supplies its domain. Do not wrap the document in another array or hash JSONB's rendering.

Canonical dates are valid `YYYY-MM-DD`, years1..9999. New UTC times match Python aware-UTC `datetime.isoformat()`: seconds when microseconds are zero, otherwise exactly six digits, then `+00:00`; reject `.000000`, seven-digit fractions, nonfinite values and alternate offsets. Preserve accepted original documents unchanged. Comparisons may parse times, but do not reserialize an original to hide a difference.

### Policy

`FpiAdminReadPolicy` has exactly the fields below. `policy_sha256=H(policy.document_json)` is outside the document. The complete policy is retained before capture; its hash is not approval.

| Field | Exact value or constraint |
|---|---|
| version | `fpi-admin-read-policy-v1` |
| scope_version | `fpi-admin-scope-v1` |
| guardrail_version | `fpi-admin-read-limits-v1` |
| trust_mode | `ADMINISTRATIVE_UNVERIFIED` |
| selector_version | `NOT_EXECUTED` |
| selector_sha256 | Retained SELECTOR artifact identity; retained intent only |
| parser_allowlist |1..64 sorted unique PARSER artifact hashes, all retained |
| definition_allowlist | Exactly `["fpi-inr-observation-v1"]`, matching current storage |
| max_current_age_days, max_history_age_days | Exact integers0..100000; history age >= current age |
| minimum_history, history_window | Exact integers;10 <= minimum_history <= history_window <=2520 |
| diagnostic_window_days | Exact integer7 in this version |
| feature_version, model_version, prediction_horizon | Each `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}`; declared intended context, not a verified implementation |
| source_rule | `AGREEMENT`, `LATEST` or `MONTHLY` |
| source_rationale |1..1024 printable ASCII characters (U+0020..U+007E) |
| allow_withdrawal_fallback | Exact boolean |
| age_timezone, missingness | `Asia/Kolkata`, `MISSING` |

Maximum policy document32768 bytes. Carrying the existing age, endpoint, history and missingness choices prevents intent from changing on retry, but this reader does not execute them. Allowlist/endpoint settings NEVER filter saved candidates. Changed policy or increased limits means a new policy identity; changing fixed semantics requires a new version.

### Request and receipts

`FpiAdminReadRequest` document has exactly `version="fpi-admin-read-request-v1"`, `decision_id`, `run_id`, `prediction_id`, `model_sha256`, `pair="USDINR"`, `mode="ADMIN_EVIDENCE_READ"`, `policy_sha256`. decision_id and run_id are canonical lowercase RFC4122 UUIDv4 strings, generated once by the caller. prediction_id and model_sha256 are hashes asserted by the caller; there is no implied FK to a nonexistent model/prediction registry. Maximum request4096 bytes. No time, candidate list, trust flag, scope override or caller-supplied output is accepted.

`request_sha256=H(request.document_json)`; **read_id=request_sha256**. decision_id is separately unique across retained reads: changed bytes under an existing decision_id produce `READ_REQUEST_CONFLICT`. This rule prevents silently forking one intended read when its policy changes. A deliberate later read has a new decision_id.

Policy receipt has exactly `version="fpi-admin-read-policy-receipt-v1"`, `policy_sha256`, `inserted`. Read receipt has exactly `version="fpi-admin-read-receipt-v1"`, `decision_id`, `request_sha256`, `read_id`, `read_sha256`, `read_at`, `status`, `execution_state="UNVERIFIED"`, `acquisition_state="UNVERIFIED"`, `eligible=false`, `inserted`. inserted is an exact boolean. Only inserted may differ on retry; original read time/status/hash persist. Receipt is small and contains no manifest or raw originals. The writer binds every identity to its submitted request; the loader subsequently verifies the exact manifest.

### Manifest

`read_sha256=H(manifest_document_json)`; neither read_sha256 nor inserted appears inside the manifest. Exact top-level fields:

```text
version = "fpi-admin-read-v1"
read_id, request_sha256, request, policy_sha256, policy
read_at, scope, status, failure, data
execution_state = "UNVERIFIED"
acquisition_state = "UNVERIFIED"
eligible = false
feature = null
```

request and policy embed their exact parsed canonical objects, with hashes checked. status is `COMPLETE`, `READ_SCOPE_EXCEEDED` or `CLOCK_INCONSISTENT`. COMPLETE requires failure=null and complete data, including empty arrays where appropriate. Both other statuses require data=null and a bounded failure object; never retain an apparently successful partial data section. Manifest cap16000000 bytes; failure manifests cap65536 bytes. The bounded request/policy overhead must fit this failure envelope before policy acceptance.

scope has exactly `version="fpi-admin-scope-v1"`, `india_date`, `history_start_date`, `history_start_clamped`, `diagnostic_start_at`, `diagnostic_start_clamped`, `newest_reporting_date`. newest_reporting_date is null only if no successful membership exists globally in the statement snapshot. Boolean clamping fields disclose saturating the lower bound to year1; there is no nonexistent year0 date or arithmetic wraparound.

COMPLETE data has exactly these fields:

| Field | Exact content |
|---|---|
| candidate_membership_ids | All scoped members, sorted by membership_id |
| candidate_dates | All distinct candidate reporting dates, ascending |
| diagnostic_parse_ids | All scoped failed parse IDs, sorted |
| references, reference_sha256 | Exact `fpi-read-references-v1` object and hash from the accepted reference contract; every supporting parse's complete membership list |
| storage_times | Exact object with captures and parses arrays; entries respectively `{capture_sha256,stored_at}` and `{parse_id,stored_at}`, sorted by ID, covering references exactly |
| artifacts | Sorted `(kind,artifact_sha256)` entries with exactly kind, artifact_sha256, document_size, body_size, stored_at; full documents retained in the original table |
| qualification, qualification_sha256 | Exact canonical `fpi-qualification-view-v2` object (members, heads, events, version) and its existing view_sha256; candidate members only |

Artifact set is exactly every parser used by a reference parse UNION policy parser allowlist UNION the policy SELECTOR artifact. No artifact body enters this manifest. Qualification events embed complete canonical event objects, including commands and resolution witnesses. No duplicated standalone witness list, guessed defaults, selected IDs, normalized amount or execution-attestation placeholder belongs here.

failure has exactly `code`, `dimension`, `limit`, `observed`, `measurement`, `witness`. For scope overflow: code=`READ_SCOPE_EXCEEDED`, dimension from the ordered limits below, limit=that exact integer, observed=exact measurement or limit+1, measurement=`EXACT` or `AT_LEAST`, witness=null. A capped probe reports AT_LEAST; never call it a total. For clock failure: code=`CLOCK_INCONSISTENT`, dimension=`NEWEST_DATE`/`FUTURE_FAILURE_STORAGE`/`REFERENCED_TIME`/`INDIA_TIME_RANGE`, limit/observed/measurement=null; witness has exactly kind, id, field, value. kind is MEMBERSHIP_DATE/CAPTURE/PARSE/ARTIFACT/EVENT; id is null only for MEMBERSHIP_DATE, otherwise the retained identity; field names the offending date/time field and value retains its exact canonical string. Resolve multiple offending rows deterministically by `(kind,id,field)`, except the indexed global future-failure probe picks largest `(stored_at,parse_id)`. No supplied bodies or free-form exception text enters failure.

### Byte-level golden vectors

The following four lines are complete canonical documents, without a trailing newline. Hash/length pairs are respectively policy `005430dfbdde7fb1aacd83d75a8763fe931dbbd7de220a07be14a27dbaac5f87`/820, request (and read_id) `a4130c1ce37873b7b580e0e15d02cf0fd0bdbad3c656bba6b248779b8436ad27`/433, empty references `5043b6cf68a2600dc6ae8f6af32a222a8cfa63a2774f61ec2833060024a81e58`/62, and empty qualification `4512d5d55af1633da699dbf2578900e14377e99a1acb26d2b6095fd667c5de19`/75. Repeated-digit artifact/model identities are authored codec examples, not retained artifacts or trusted releases. SQL fixtures must use real synthetic originals when checking dependency acceptance. Implementation adds complete/overflow manifest vectors from those valid originals and pins their independent expected bytes/hashes.

```json
{"age_timezone":"Asia/Kolkata","allow_withdrawal_fallback":false,"definition_allowlist":["fpi-inr-observation-v1"],"diagnostic_window_days":7,"feature_version":"fixture-feature-v1","guardrail_version":"fpi-admin-read-limits-v1","history_window":60,"max_current_age_days":7,"max_history_age_days":365,"minimum_history":10,"missingness":"MISSING","model_version":"fixture-model-v1","parser_allowlist":["2222222222222222222222222222222222222222222222222222222222222222"],"prediction_horizon":"T5","scope_version":"fpi-admin-scope-v1","selector_sha256":"1111111111111111111111111111111111111111111111111111111111111111","selector_version":"NOT_EXECUTED","source_rationale":"Neither endpoint establishes source finality","source_rule":"AGREEMENT","trust_mode":"ADMINISTRATIVE_UNVERIFIED","version":"fpi-admin-read-policy-v1"}
```

```json
{"decision_id":"11111111-1111-4111-8111-111111111111","mode":"ADMIN_EVIDENCE_READ","model_sha256":"4444444444444444444444444444444444444444444444444444444444444444","pair":"USDINR","policy_sha256":"005430dfbdde7fb1aacd83d75a8763fe931dbbd7de220a07be14a27dbaac5f87","prediction_id":"3333333333333333333333333333333333333333333333333333333333333333","run_id":"22222222-2222-4222-8222-222222222222","version":"fpi-admin-read-request-v1"}
```

```json
{"captures":[],"parses":[],"version":"fpi-read-references-v1"}
```

```json
{"events":[],"heads":[],"members":[],"version":"fpi-qualification-view-v2"}
```

## Complete scope and clock rules

Sample read_at once in a MATERIALIZED clock CTE inside the materializing statement, after the decision lock and retry check, through a private helper returning `clock_timestamp()`. Do not use `statement_timestamp()`: inside an RPC it can still describe the outer client command before the lock wait. PostgreSQL distinguishes the [command-start and actual-current clocks](https://www.postgresql.org/docs/17/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT); verify this at the actual RPC entry point. D is read_at's date at fixed UTC+05:30, matching accepted codecs; H is policy max_history_age_days. Compute history_start_date as max(0001-01-01,D-H), clamping with integer date ordinals before subtraction. Compute diagnostic_start_at as max(0001-01-01T00:00:00+00:00,read_at-7days), similarly before subtraction. UTC and India conversion must both remain within years1..9999. An unrepresentable server read_at cannot form a canonical receipt: abort with `READ_CLOCK_RANGE` and no row. This is distinct from a retained evidence clock inconsistency.

1. Find the global maximum committed membership reporting_date using the date index. Discover every membership with reporting_date in `[history_start_date,D]`, plus EVERY member on the newest date if that date is outside the interval. Include all retained endpoints, parsers, values and qualification states. This single sentinel preserves evidence that the archive contains only stale observations. It does not prove archive completeness before acquisition began.
2. If newest_reporting_date>D, persist CLOCK_INCONSISTENT/NEWEST_DATE instead of excluding it. Older future dates cannot hide behind the maximum. Unsupported date ranges in authoritative storage are an integrity error, not a truncated valid date.
3. Candidate parses are the successful parses owning those members. Save ALL of each such original parse's memberships as support in references. Support-only dates neither acquire candidate heads nor cause other parses on those dates to be pulled in. They never recursively expand scope. Membership IDs distinguish same-value occurrences from different captures/parsers.
4. Candidate capture IDs are the fixed capture set from candidate parses. Diagnostics are the set UNION of all failed parses with stored_at in `[diagnostic_start_at,read_at]` and all failed parses for candidate captures, regardless of stored_at. The diagnostic branch does not filter parser/endpoint and never creates zero, withdrawal or a dated observation. Failure-only captures do not recursively seed more failures. Save whole failed records and their original captures too.
5. Before accepting that time window, run an indexed global probe for a failed parse with stored_at>read_at. If found, persist CLOCK_INCONSISTENT/FUTURE_FAILURE_STORAGE, even if its capture is otherwise outside scope. This prevents a backward clock from silently dropping a failure. A late-committed failure with old stored_at outside W and no candidate capture is deliberately outside this diagnostic scope. Its storage clock cannot establish commit visibility.
6. For all referenced captures, parses, artifacts and compact qualification events, reject future times relative to read_at with retained CLOCK_INCONSISTENT/REFERENCED_TIME. Capture checks cover requested_at/retrieved_at/stored_at; parse covers recorded_at/stored_at; artifact covers stored_at; event covers recorded_at. Validate stored_at>=retrieved_at/recorded_at where the existing schema requires it. `build_fpi_read_references` also requires parse>=retrieval and each reporting date<=receipt's India date; keep these checks. Receipt/parse conversion outside the accepted UTC/India year bounds produces CLOCK_INCONSISTENT/INDIA_TIME_RANGE before loading. Other malformed retained originals produce a bounded integrity error, not a usable read.

No absence of these anomalies proves clock accuracy. Equal/decreasing qualification times are valid order evidence when ordinals/witnesses agree; a read later than all referenced times may be COMPLETE. If rollback places a referenced time in the future, the saved read fails for that reason without rearranging qualification events. read_at describes the reader's sampled wall clock, not the MVCC snapshot's acquisition instant, commit time, source finality or a historical visibility cutoff. Never select visible rows by `recorded_at<=read_at` or `stored_at<=read_at` except the expressly declared failure diagnostic window and anomaly tests.

## Qualification closure

Construct the required target set from CANDIDATES ONLY: each member ID, distinct value hash, parser hash and reporting date. For every target store exactly one head record `{scope,target,event_id}`; event_id=null explicitly records absence. Fetch the highest visible ordinal per target using the target/order index. Do not take the qualification append lock.

The event set is exactly non-null current heads plus non-null historical membership/value/parser heads referenced by each current date RESOLVE event's witness. Historical witness events are non-date and do not recurse. Every resolution basis ID and chosen ID must belong to the complete candidates on its date. Because all members on a scoped date are present and memberships are immutable, there is no legitimate outside-candidate basis to fetch or invent. A new same-date member makes the old basis a proper subset and yields STALE_RESOLUTION in the administrative v2 evaluation. A missing basis member signals integrity failure.

Rebuild and evaluate the existing `FpiQualificationView` once. Its exact target set, event-set equality, ordinal, duplicate, witness and available-predecessor consistency rules apply. Do not load full predecessor chains, derive order from times, or reconstruct the full view once per candidate. Empty candidates require empty qualification members/heads/events, even when diagnostics include failed parses and parser artifacts. Administrative evaluation is optional read-only inspection and never sets eligible.

## Bounded materialization and persistence

New private append-only tables:

- `fpi_admin_read_policies(policy_sha256 PK, document_json, selector_kind CHECK SELECTOR, selector_sha256, UNIQUE(policy_sha256,selector_sha256))`, with artifact FK `(selector_kind,selector_sha256)`. Retain canonical original policy text. Policy append validates every allowlist artifact against immutable originals; missing artifact rejects. No time field is required for policy semantics.
- `fpi_admin_reads(read_id PK, decision_id UNIQUE, request_sha256 UNIQUE, request_document_json, policy_sha256 FK, read_sha256, manifest_document_json, read_at timestamptz, status)`. Enforce read_id=request_sha256 and all stored projections against the canonical document in the only insertion RPC. Parsed JSONB, if retained for queries, is a checked projection, never the hash authority. There is no mutable eligibility or status-update column.

RPCs: `append_fpi_admin_read_policy(p_policy_sha256 text,p_document_json text)` and `capture_fpi_admin_read(p_request_sha256 text,p_document_json text)`. Fixed search_path, SECURITY DEFINER, VOLATILE; READ COMMITTED only. Validate strict bounded canonical inputs before expensive reads. No caller-supplied manifest RPC exists. New functions must use the final inherited top-level timeout contract from migration13;1..30000ms before the top-level call, private10s lock timeout, real cancellation verification. Function-local statement_timeout is not a timer. No timer or evidence-time override is exposed to application callers.

Capture acquires a transaction advisory lock in a namespace separate from `(946027,1)`, keyed by decision_id. Freeze namespace integer946029 plus signed32-bit prefix of SHA256(decision_id ASCII); collisions only serialize unrelated reads. In a fresh post-lock statement, look up decision_id: identical request bytes/hash return original receipt before policy/dependency rechecks; changed content rejects. Hold lock until transaction end. This is retry serialization, not serialization against evidence writers.

For a new request, **ONE materializing SQL statement** discovers the policy, sampled clock, scope, candidates, support, diagnostics, originals' metadata, artifact references, current/absence heads, witness events, guard results and INSERTs either the complete or failure manifest. Use explicit MATERIALIZED CTEs with dependency guards. Helpers called there may be pure canonical/hash functions or the single clock sample; none may issue its own evidence queries under a separate snapshot. Original metadata projections are derived from immutable authoritative rows within that statement. No preliminary policy lookup or post-statement head fetch becomes evidence. No later SQL statement patches missing manifest fields. The transaction returns a receipt only after its insertion; only a committed RPC acknowledgement is durable evidence.

Failure precedence is staged and deterministic. First reject an unrepresentable server clock without a row. Next test NEWEST_DATE, then FUTURE_FAILURE_STORAGE. Then run count guards CANDIDATES through HEADS in table order. Next apply the preliminary date-head QUALIFICATION_BYTES guard described below, then complete witness closure and EVENTS. Only now inspect all bounded referenced metadata for INDIA_TIME_RANGE followed by REFERENCED_TIME; ties within each use the witness ordering above. Then apply ORIGINAL_BYTES, REFERENCE_BYTES, final QUALIFICATION_BYTES and MANIFEST_BYTES in order. Stop at the first failure; do not inspect later stages to produce a supposedly more important reason. Thus candidate overflow wins over an as-yet uninspected future candidate time, and preliminary date-head bytes win over a possible later event-count overflow. Failure payloads contain only scope/request/policy and the declared failure object. Malformed authoritative metadata/dependencies abort with READ_INTEGRITY_ERROR whenever encountered; they are not an alternative successful subset.

| Ordered dimension | Limit | Required bounded probe |
|---|---:|---|
| CANDIDATES |20000 | Materialize at most20001 membership IDs from disjoint window/sentinel branches |
| PARSES |2048 | At most2049 distinct union IDs of candidate and diagnostic parses |
| CAPTURES |2048 | At most2049 distinct captures required by the bounded parse set |
| SUPPORT_MEMBERSHIPS |20000 | At most20001 total members of those whole parses |
| ARTIFACTS |2113 | At most2114 distinct references (2048 parse parsers +64 policy parsers +1 selector) |
| HEADS |100000 | At most100001 required candidate target tuples |
| EVENTS |100000 | At most100001 distinct current/witness event IDs |
| ORIGINAL_BYTES |64000000 | Exact sum of unique capture/parse/artifact canonical document lengths, before fetching/decoding/aggregating bodies |
| REFERENCE_BYTES |16000000 | Exact encoded reference fragments + canonical envelope/comma overhead before concatenation |
| QUALIFICATION_BYTES |16000000 | Exact encoded view fragments + canonical envelope/comma overhead before concatenation |
| MANIFEST_BYTES |16000000 | Exact complete canonical fragments + envelope/comma overhead before final concatenation |

Individual document caps remain capture7000000, parse4000000, artifact7000000, qualification event400000 ASCII bytes. Check individual lengths before decoding them. Their corruption is `READ_INTEGRITY_ERROR`, not a policy override. Exact sums use wide integers and count each typed identity once; SQL must match the reference builder's unique-original accounting for captures/parses. Identical canonical documents across different valid kinds/IDs cannot occur under these versioned identity rules. The stronger combined ORIGINAL_BYTES guard includes artifacts so the loader remains bounded; do not silently omit artifact validation to fit.

LIMIT+1 is ONLY an overflow probe: an accepted set contains every matching row. Use set UNION before its probe for diagnostic overlap and distinct dependencies; never count duplicates as excess. Do not sort or aggregate the whole unbounded archive before the probe. Raw document bodies/JSON expansion and fragment aggregation are downstream of count and length guards. Reading length metadata can inspect TOAST storage; it is not permission to transmit/decode the body. Fragment sizes must be computed before constructing a large aggregate; qualification event text is already canonical and can be accounted from length without reparsing an unbounded collection. Bound command/witness parsing by its per-event cap and proven aggregate budget.

Do not implement that UNION as an unbounded hash aggregate over the full failure archive. Use this concrete PARSES algorithm: candidate parse IDs come from at most20000 candidate rows and are distinct-probed at2049. If within limit, derive their bounded candidate capture seed. Probe unique failed parse IDs separately from (a) the indexed time range and (b) the candidate-capture join, each at2049. Each branch has no internal duplicates because parse_id is unique and the seed capture IDs are unique. Any branch alone exceeding2048 proves the union exceeds2048 and returns PARSES/AT_LEAST2049. Otherwise materialize at most6144 IDs from the three complete branches, deduplicate only that bounded collection, then test the distinct union count. This final measured union count is EXACT. Branch evaluation order is candidate, time range, capture join. No per-capture all-history aggregate is permitted. Similar bounded sources apply before other DISTINCT operations; artifacts, targets and witness IDs originate only from already bounded collections.

`CASE WHEN bounds_ok THEN jsonb_agg(...) END` is insufficient: PostgreSQL may evaluate the aggregate before the surrounding CASE. Feed decoding/aggregation only from an explicitly guarded input relation with the proven bound predicate and materialization barrier. See PostgreSQL's [expression evaluation rules](https://www.postgresql.org/docs/17/sql-expressions.html#SYNTAX-EXPRESS-EVAL). Test a fail-if-called scratch decoder on deliberately excessive input, inspect plans and measure behavior; syntax that looks guarded is not evidence of bounded execution.

Required index additions: `(reporting_date,membership_id)` for range/sentinel reads; partial failed-parse indexes `(stored_at,parse_id) WHERE failure_reason IS NOT NULL` and `(capture_sha256,parse_id) WHERE failure_reason IS NOT NULL`. Existing membership `(parse_id,reporting_date)` and qualification head indexes support dependency/head lookups. Index-only existence/range probes, bounded DISTINCT/UNION plans and actual EXPLAIN/resource measurements belong to acceptance. Large diagnostics sharing candidate captures must stop at the distinct parse limit; do not scan all matches merely to count them. Individual table scans may still time out under storage pressure; no finite memory guard promises bounded wall time.

Do not allocate the complete qualification view merely to discover that its event text exceeds16MB. Once IDs are bounded, preflight the sum of original event lengths plus member/head/envelope size, then parse only those bounded events needed for witness closure. For date-head witnesses, preflight date-head text separately against the final qualification budget before extracting witness IDs; if already exceeded, return QUALIFICATION_BYTES without expanding it. This necessary early date-head byte guard precedes EVENTS and is the explicit exception to the table order. Its observed lower bound includes exact checked head fragments, with measurement=AT_LEAST, because full closure was not assembled. Do not claim a count overflow if the guard actually measured bytes. Full event closure and final size remain checked afterward.

If a measured bound is exceeded, the same materializing statement INSERTs a small immutable READ_SCOPE_EXCEEDED record. A query timeout, connection failure, deadlock or cancellation can instead roll back the entire statement: there may be NO read to retain. Never promise a saved overflow record for work that the server cancelled before insertion. Retry the same identity to reconcile. A committed overflow remains overflow on retry even if limits later change; new policy/version and decision identity are required.

All new tables use RLS, private SELECT grants to service_role, approved RPC EXECUTE only, and UPDATE/DELETE/TRUNCATE refusal including owner attempts. Deny PUBLIC/anon/authenticated reads and direct application INSERT/UPDATE/DELETE; revoke private helper access. Do not weaken prior grants. Reapplication preserves every original/read/policy and index/constraint meaning. Existing immutable dependency tables prevent normal deletion; append RPC and loader enforce embedded reference integrity. No fresh mutable cache or copied partial original replaces them.

## Central writer, pure codec and loader

Pure `pipeline/src/research/fpi_saved_read.py` owns new frozen policy/request/manifest/receipt types, exact codecs, bounds and consistency checks. It performs no I/O, parsing of NSDL HTML, artifact execution or feature normalization. Never edit existing v1 meanings to accommodate this type. Reconstruct nested dataclasses at public boundaries; a frozen object/cache is not authenticity.

Only `pipeline/src/db/writer.py` adds policy append, capture and load operations. Local input validation happens before client acquisition. Each append/capture uses exactly ONE RPC and never uploads dependencies or invents retry identities. Static bounded errors omit source bodies, submitted JSON, credentials and exception chains; preserve cancellation/base exceptions. Receipt verification checks exact key sets/types, all bound IDs, canonical time, allowed status and permanent trust constants; return detached values. capture does not pretend it validated the whole manifest when it checked only the receipt.

`load_fpi_admin_read(read_id)` follows only the immutable saved row and its manifest-named originals. It may use several bounded queries because those originals cannot change; it must not re-query current membership scope, latest qualification heads, current policy aliases, trust states or provider endpoints. All list reads use an explicitly documented maximum page size256 and keyset/requested-ID batching; compare exact returned identity sets to requested sets. A provider's default row limit must cause missing-dependency failure, never silent acceptance. Reject duplicates, extra IDs, changed projections and totals before proceeding. One singleton manifest query first verifies the declared16MB bound; document transport must support that bound or fail, never truncate.

Loader sequence:

1. Recompute manifest, request and policy identities from original canonical text; check read row projections, permanent authority fields and status-specific exact schema. Failed reads return a detached nonusable outcome; no dependency loading or fabricated empty view. For COMPLETE, check all declared count/byte limits and set relations before fetching originals.
2. Read each distinct capture, whole parse and artifact once, in bounded ID batches. Check each original's actual length before JSON parsing/hashing and combined64MB total; do not trust stored length metadata without comparison. Retain detached primitive copies. Require all and only the manifest references. Validate each artifact with `validate_fpi_artifact` once, including kind/body/hash; never import it. Compare artifact body_size, document_size and stored_at.
3. Call `build_fpi_read_references(captures=...,records=...)` ONCE over unique originals and compare both full canonical reference document and reference_sha256. This preserves all restore checks, complete Monthly support, failed parse metadata and source-evidence identities. Do not loop over `restore_fpi_parse_record` and repeatedly hash one shared capture. One capture validation per distinct capture, one `_record_parts` per distinct parse, independent of parser multiplicity, are measured requirements. SQL projection/reference bytes must match this authoritative rebuilding boundary.
4. Compare database stored_at and all metadata against storage_times/artifacts; derive candidate IDs from the saved full references using the saved window/sentinel and verify exact equality. This checks internal scope consistency; the pure loader cannot prove that SQL did not omit an entirely unreferenced parse. Verify diagnostics against saved stored_at and fixed candidate capture set, including every saved failed parse and no stray successes; SQL owns proof that no matching database failure was omitted.
5. Fetch every named qualification event by ID, bounded and once; compare original canonical text to the embedded event object exactly. Rebuild candidate members from checked parse references, rebuild the v2 view once, compare its full document/hash and run one bulk evaluation if requested. Do not demand absent historical predecessors or use today's event head. Check saved clock rules again, without changing saved read_at.

No numeric feature is returned. Later research inspection may explicitly derive amounts from the validated immutable originals; it remains UNVERIFIED administrative evidence. This packet does not implement result archival, protected execution or consumer publication.

## Retry and replay

Concurrent identical submissions produce one retained read and identical receipt values except inserted. Lost acknowledgement retries reuse the exact decision/request. If committed, return the original even after new parses, withdrawals or policies appear. If rolled back, retry may observe a new snapshot; no prior retained read existed. An open SQL transaction's function return is not a commit acknowledgement.

Loading always reproduces the original scope, heads, witnesses and failure outcome. Missing/corrupt original yields `READ_DEPENDENCY_MISSING`/`READ_INTEGRITY_ERROR`; never redownload, substitute a parser, shrink a set or refresh heads. Historical `select_at(timestamp)` without an existing saved read returns `VISIBILITY_UNPROVEN`. The old v1 replay API remains separate and its inputs do not acquire saved-read authority retroactively.

## Implementation acceptance matrix

These are executable scenarios for the implementation packet, **not tests run by this documentation leaf**. Use real isolated PostgreSQL, genuine complete synthetic originals through accepted writers, two independent connections, actual RPC roles and observed barriers (`pg_locks` or scratch triggers). Parent starts/stops any runtime and independently challenges results. No production providers, credentials or deployment.

| ID | Setup/action | Required assertion |
|---|---|---|
| SR01 | Independently encode fixed policy/request, empty reference/view and complete/overflow manifests in Python and SQL; zero/nonzero microseconds and escaping controls | Byte-identical canonical JSON and SHA256; golden hashes pinned in tests, not produced by the function under test as expected output |
| SR02 | Empty archive with retained policy artifacts | COMPLETE empty candidates/references/view, sentinel null; UNVERIFIED, eligible=false, feature=null |
| SR03 | Only old data, then fresh data, then global newest>D | Old sentinel's full members preserved; new scoped date included; future-date read persists CLOCK_INCONSISTENT |
| SR04 | Same-date unqualified, disallowed-parser, other-endpoint and same-value alternate occurrences | Every member retained; policy filters cannot certify a smaller set |
| SR05 | Monthly result straddles lower bound; unrelated alternative only on support date | Whole Monthly parse verified; support stays outside candidates/heads and does not pull in alternative |
| SR06 | Failures at both W boundaries, outside W, old failure sharing candidate capture, failure-only capture with another old failure | Exact closed interval plus fixed capture union; no recursive failure expansion or synthetic zero |
| SR07 | Hold old-stored_at failure uncommitted beyond W, save read, commit, save another | First excludes invisible transaction; second includes only if declared diagnostic rule matches, with no timestamp visibility claim |
| SR08 | Backward clock, future stored_at failure on unrelated capture, future candidate/parse/artifact/event time | Global failure cannot disappear; exact clock failure persisted; no evidence row excluded to obtain COMPLETE |
| SR09 | read_at near year1 and UTC/India year9999 edge; receipt/parse India conversion overflow | Lower bound clamped/disclosed; unrepresentable server clock aborts with no row; supported read with unrepresentable referenced time persists clock failure |
| SR10 | Pause withdrawal after INSERT before commit; save read without qualification lock, then commit and save new identity | First read completes with old head; second sees new head; original replay unchanged |
| SR11 | Commit ACCEPT->RESOLVE->WITHDRAW at equal and decreasing times, read later than all; repeat rollback placing event in future | Correct ordinal/witness administrative states; future-clock case fails for time without rewriting history |
| SR12 | RESOLVE basis A,B; commit C just before/after materializing read barrier | Read contains one whole coherent candidate/head state; C makes old basis stale; no mixed snapshots |
| SR13 | Pause complete parse insertion before commit; read, commit, read again; force middle-member rollback | No partial parse/members; second read complete; rollback leaves no partial saved dependencies |
| SR14 | Many reinstatements on one parser; only latest current/witness IDs required | Constant-size historical closure; no unbounded predecessor walk; explicit absent heads remain present |
| SR15 | Concurrent same request; changed request/policy under same decision; dropped acknowledgement | One retained original, conflict for changed bytes, no fresh read on identical committed retry |
| SR16 | Every count/byte bound at limit and limit+1 using test-owned configurable small harness bounds plus actual individual-document limits | COMPLETE only at valid bound; small immutable failure with correct dimension, exact/lower-bound distinction and no partial data |
| SR17 | Oversized candidate/failure archive, shared captures, large date-head witnesses, shared original bodies | Guards precede raw decode/aggregate; query plan/resources bounded; distinct union avoids false overflow; counts show one validation per original |
| SR18 | Actual timeout while waiting/reading; rollback, then identical retry | Cancellation observed, no claimed persisted overflow; prior commit reconciles or new complete transaction succeeds |
| SR19 | Omit one absent head, member, event, witness or supporting date; alter retained metadata/hash; duplicate/extra returned rows; provider page truncation | Loader rejects, static error contains no fixture secret; originals unchanged |
| SR20 | Return forged frozen types, boolean integer, duplicate key, unknown key, wrong version/time/hash, altered trust constants | Rejection before I/O for input errors; malformed receipt/manifest cannot become usable |
| SR21 | Populate/reapply migration; owner mutation/truncate; anon/authenticated reads; service direct writes; helper calls | Evidence preserved and every forbidden action denied; permitted RPC/read remains functional |
| SR22 | Save COMPLETE then add approval-shaped caller evidence/ACCEPT or hypothetical later trust; invoke existing consumer entry points | Original stays UNVERIFIED/ineligible; no adapter supplies a feature; future trust requires new version and snapshot |
| SR23 | Parent independently reconstructs expected row sets/docs, then removes full-date scope guard or changes returned reference in scratch-only code | Positive controls pass and deliberate wrong-output/control fails; a marker alone is insufficient |
| SR24 | Hold decision lock before RPC starts materialization; cross an India day/age boundary using a private scratch clock seam, then release; establish actual visibility with an independent committed row | read_at/scope use the one post-wait materialization sample, not outer command time; retained membership visibility follows the one statement snapshot |
| SR25 | Excessive input and a scratch decode helper that throws if invoked; compare CASE-only aggregate to guarded input relation | Oversize outcome persists without decoder invocation; positive under-limit control really calls decoder; EXPLAIN and real execution support the guard |
| SR26 | Simultaneously exceed candidate count and include a future candidate time; separately exceed preliminary date-head bytes and eventual event count | First failure follows staged precedence exactly; no uninspected count/clock claim is fabricated |

Required checks for implementation: focused codec/writer tests, real database harness, independent parent negative controls, complete pipeline regression, configured Ruff/MyPy and integration with the final timeout contract. Frontend/build checks apply if later consumer work changes frontend code. Record query plans, actual limits and runtime evidence; do not copy earlier packet counts into new success claims. FPI activation and release remain blocked by protected execution, acquisition trust, actual consumer parity and the broader repair gates.
