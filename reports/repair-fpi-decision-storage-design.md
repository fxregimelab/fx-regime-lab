# Durable FPI qualification and decision reads — proposed next contract

27 September 2026. Leaf24.3. **Design proposal for parent adoption; no implementation or production acceptance.**

The next layer needs a versioned selection interface. Saving the current Python objects unchanged would preserve two gaps: timestamps still determine cross-scope event order, and the snapshot grows with the entire archive. Use database-ordered qualification events, explicit resolution witnesses, and a complete but declared date scope. Save the exact database read before any consumer uses it.

This report owns only this file. It does not change the frozen parse-storage contract, implementation, historical calls, project glossary, migration, credentials or runtime. Production FPI stays disabled. The parent retains contract and release authority.

## Evidence and limits of this review

Base HEAD was `9fa150538d08ab5a2a6c587976552944f47a724d`; the shared repair checkout has substantial uncommitted work. Relevant current files were read directly:

- `IDENTITY.md`, the 27 September amendment in `MASTERPLAN.md`, `TASK.md`, `CONTEXT.md`, `OMEGA_PROTOCOL.md` and the owner's quality-first policy.
- `docs/FPI_SELECTION_CONTRACT.md`, `pipeline/src/research/fpi_selection.py`, `pipeline/tests/test_fpi_selection.py` and `reports/repair-fpi-timing-review.md`.
- `docs/FPI_CAPTURE_CONTRACT.md`, `supabase/migrations/20260927000010_fpi_capture_storage.sql`, `pipeline/src/db/writer.py` and the frozen `docs/FPI_PARSE_STORAGE_CONTRACT.md`.
- The retired fetcher, FPI normalizer and source-boundary tests; consumer references in scheduler, staged and simulation paths.

GitNexus query failed with database version 42 versus runtime version 40. No index rebuild was attempted. Direct reads supplied the evidence. A narrow memory-registry search found no project/FPI entries. No network, provider, AI or credential access was used. No database, Docker or Hermes process was started: this leaf required source review and a pure synthetic probe only.

The artifact/parse/member implementation was still delegated work when reviewed. This proposal uses its frozen contract as a dependency, not as evidence that it passed. PostgreSQL behavior below is a concrete algorithm to verify against the supported local server, not a claim that this leaf ran transaction tests.

## Findings that change the next packet

**F1 — Cross-scope ordering is not representable safely in v1.** `FpiDecisionSnapshot.__post_init__` sorts events by `(recorded_at, scope == "date", predecessor_depth)`. ACCEPT member M at T1; RESOLVE date D to M at T5; then WITHDRAW M at the same T5. The snapshot containing ACCEPT and RESOLVE constructs successfully. Adding the later withdrawal rejects it with `Resolution target was not qualified at resolution time`: the sort places the withdrawal before the resolution. All input permutations canonicalize to that same rejection. This is conservative failure, but it cannot represent a legitimate committed history.

The parent supplied the counterexample; this leaf independently reproduced it with the existing authored synthetic fixture through `python -B`, without creating a fixture file. Output: `FPI_TIED_SCOPE_ORDER_GAP_REPRODUCED: Resolution target was not qualified at resolution time`. Backdating the withdrawal by one microsecond also rejects; neither caller-controlled timestamp is evidence of the actual sequence. Do not fix this by sorting hashes, adding artificial microseconds or preferring a scope.

**F2 — A caller's complete-looking tuple does not prove a complete database read.** The current constructor explicitly says so. If the reader omits a newer unqualified member, a competing parser, a parser-wide withdrawal or one side of endpoint disagreement, selection can change. SQL must discover candidates; consumers cannot submit their own winner list for certification.

**F3 — Retaining a bundle is separate from running that bundle.** The parse-storage contract deliberately permits arbitrary binary artifacts and explicitly declines to authenticate execution. A PARSER row with a matching hash does not establish that its code produced a parse, and a SELECTOR row does not establish that the live worker ran that selector. These need runner evidence before activation.

**F4 — Exact v1 replay and bounded ongoing reads are different contracts.** v1 emits exclusions for all supplied dates and diagnostics for all failed parses; it requires every supplied event's predecessor. Its 2,048 parses, 20,000 events/memberships and 64,000,000 capture-character caps make an all-archive reader eventually unavailable. A hidden SQL limit would change the result. Scoped exclusions/diagnostics and a compact event witness are explicit v2 changes.

**F5 — Actual consumer parity is still open.** Current call sites preserve `FPI_UNAVAILABLE_NOTES`; the source-boundary tests reject raw amounts and caller-provided normalized scores, including zero. The pure selector has no current scheduler/staged/replay caller found by source search. A deterministic pure test is not that integration evidence.

## Terms used by this proposal

Existing value, occurrence, membership, qualification and decision-snapshot meanings remain those in `CONTEXT.md`.

| Proposed term | Exact meaning |
|---|---|
| Qualification command | A stable request to make one transition from a named expected predecessor. It has an identity before contacting storage. |
| Qualification event | The immutable accepted transition, including database-assigned order and recording time. |
| Head | The last accepted event for one `(scope, target)` at a particular database read. No event means a distinct explicit absent head. |
| Resolution witness | The candidate membership basis and membership/value/parser heads actually checked when a date resolution was accepted. |
| Read scope | The exact rule declaring which reporting dates and failure diagnostics belong to a decision, including the newest-date sentinel. |
| Decision read | A durable manifest of one committed database snapshot under that scope. It can exist before selection succeeds. |
| Decision result | The separately retained output of the verified selector operating on that saved read and policy. |

Record these terms in the project glossary only after parent adoption; this leaf has no lease on `CONTEXT.md`.

## Proposed module interface

Keep all database writes and service-role reads behind `pipeline/src/db/writer.py`; put codecs, canonical forms and pure selection in research modules. Callers should not manage locks, construct candidate SQL, choose qualification timestamps or recompute retry keys.

Proposed signatures, not existing functions:

```python
append_fpi_qualification(command: FpiQualificationCommand) -> QualificationReceipt
capture_fpi_decision_read(request: FpiDecisionReadRequest) -> DecisionReadReceipt
load_fpi_decision_read(read_id: str) -> VerifiedFpiDecisionRead
archive_fpi_decision_result(result: FpiDecisionResult) -> DecisionResultReceipt
```

Each append/capture call maps to exactly one transaction-owning RPC. The loader reads only the retained manifest and its immutable referenced records; it never queries today's latest heads or expands the candidate set. An orchestration helper may call read → load → select → archive, but a lost result acknowledgement must not cause a new read under the old decision identity. Storage does not execute Python artifacts.

The existing archive functions remain unchanged. New qualification requires the referenced capture, parse, member and PARSER artifact to exist already. Decision reads require the frozen policy and SELECTOR artifact to exist. Parser/selector runtime attestation is a separate required dependency described below.

### Canonical identities and receipts

Continue canonical compact sorted ASCII JSON, strict primitive types, duplicate-key rejection before JSONB conversion, exact key sets, bounded strings, canonical dates and lowercase SHA-256. All hashes below have an explicit version/domain tag. SQL and Python need byte-identical golden vectors. Never add database time to a caller's stable command identity.

| Record | Identity and immutable content |
|---|---|
| Qualification command | `command_id = H(["fpi-qualification-command-v2", request_json])`. Request includes scope, target, action, expected predecessor (nullable), bounded reason, immutable evidence reference, chosen member/basis for RESOLVE. No `recorded_at` supplied by caller. Optional claimed source time is labelled evidence only. |
| Qualification event | `event_id = H(["fpi-qualification-event-v2", command_id, event_ordinal, recorded_at, witness_json])`. Ordinal is a positive bounded integer assigned under the transaction-held qualification lock. Event stores the complete command. Witness is null for non-date actions; date witness binds exact observed heads and basis. |
| Policy | Exact versioned policy document/hash, including selector artifact, selector semantic version, date scope, failure-diagnostic scope, missingness and every existing policy field. No mutable version labels. |
| Decision-read request | Stable caller-generated `decision_id` plus exact request hash. It binds USDINR, policy hash, run/model/prediction identity and mode `LIVE_READ`. No caller-selected evidence time. A retry must reuse the same identity and bytes. |
| Read manifest | `read_sha256 = H(["fpi-decision-read-v2", manifest_json])`; `read_id` is a stable opaque identifier bound uniquely to decision_id. Manifest includes request/policy identity, server read time, scope definition/derived dates, all exact record references, head/absence witnesses, resolution witnesses and limit outcome. |
| Decision result | Unique per read and declared selector/feature implementation; exact result document/hash, input/read/policy hashes and execution-attestation reference. A conflicting output for the same identity is rejected, not retained as a retry. Research variants require new policy/decision identity. |

Qualification receipt has exactly `command_id`, `event_id`, `event_ordinal`, `recorded_at`, `inserted`. Decision-read receipt has exactly `decision_id`, `request_sha256`, `read_id`, `read_sha256`, `read_at`, `status`, `inserted`. Result receipt has exactly `read_id`, `result_sha256`, `stored_at`, `inserted`. Receipt time strings use the existing finite UTC zero-to-six-fractional-digit grammar; integers are not booleans. On retries only `inserted` may change. Verify identity/type/exact key set before accepting a receipt; return detached data. Provider errors remain bounded codes without exception chains or supplied documents.

`recorded_at`, `read_at` and `stored_at` describe server actions. None is called a source release or commit timestamp. `read_at` is captured at the beginning of the materializing database statement and governs age only. The exact visible row set establishes this decision's evidence. A wall-clock rollback must trigger a clock-consistency failure where age/future checks become impossible; do not rewrite evidence times or use the clock to order transitions.

## Qualification transaction and causal order

Use a single reserved transaction-scoped advisory lock for FPI qualification transitions in the first implementation. FPI has low expected transition volume; this simpler correctness argument is preferable to several subtly different scope locks. Do not serialize downloads, artifact storage or parsing with it. The lock is released only on commit/rollback, including cancellation. Explicitly support `READ COMMITTED`; reject unsupported isolation modes at the entry point until tested. A transaction snapshot established before waiting on the lock is not acceptable for the fresh-head check.

1. Validate bounded command syntax before expensive work. Acquire the qualification lock in its own statement. Entry points are explicitly VOLATILE PL/pgSQL functions; helpers that query evidence cannot be incorrectly declared STABLE/IMMUTABLE and reuse an earlier snapshot.
2. In a subsequent fresh statement, look up `command_id`. Identical retained command returns its original event even if the target now has a later head. Different content under the identity rejects.
3. Read the target head after lock acquisition and compare exactly with `expected_prior_event_id`, including null. Reject stale expected heads with a bounded conflict and actual head token. Never automatically replace the predecessor and retry an action.
4. Allocate `event_ordinal = max(committed ordinal) + 1` under the held lock. Enforce unique ordinal, unique command and a unique successor of `(scope,target,prior)` including the null-root case. A nullable unique constraint alone does not prevent duplicate roots; use an explicit null-root partial unique index or supported null-equal uniqueness.
5. For membership ACCEPT, verify the adopted trusted parser-run/qualification authority records against the exact retained parse; a bare caller evidence string is insufficient. For RESOLVE, materialize candidate members and chosen member's three current scope heads in **one statement snapshot after the lock**, not one read per scope. Include all retained successful memberships for that date across both endpoints, all parser/definition versions, and all qualification states. Require the command basis to equal that set exactly; chosen membership must currently be accepted and unblocked. Save the checked basis and heads in the event witness. The caller's basis is a stale-change guard, not authority over SQL's discovered set.
6. Insert the immutable event and return its exact receipt. Do not acknowledge durability before the RPC transaction commits. A direct SQL verifier receiving a function return inside an open transaction has not received a commit witness.

All qualification entry points take the same lock; direct table inserts remain denied. Append-only events remain the authority. Current heads can initially be indexed anti-joins against successors; avoid a mutable head table in the first migration. A future cache must be explicitly a rebuildable projection, never the historical ledger.

**Why the ordinal has meaning:** transition T2 cannot acquire the lock while T1 is uncommitted. After T1 commits, T2's fresh statement observes it and allocates a later ordinal; after T1 rolls back, no T1 event exists. This is a serial order among accepted qualification transitions only. It says nothing about HTTP release order, parse commit order or decision visibility. Using `nextval()` without this protocol does not prove the same property.

Tied clocks and backdated evidence do not affect this order. The v2 pure validator verifies positive unique ordinals and expected scope references, and uses resolution head witnesses rather than reconstructing cross-scope history by timestamp. Database validation remains necessary: a standalone forged ordinal is not proof of a real transaction.

### Concurrent parse arrival during a resolution

Parse storage remains independent. If parse P commits before the resolution's basis statement snapshot, P belongs in the basis. If it commits after that snapshot, it does not. The saved resolution is valid for the witnessed basis; a later decision read that sees P compares its full per-date candidate set to the basis and returns `STALE_RESOLUTION`. This is intentional even if P committed before the resolution transaction's eventual commit. A lock that excludes parse insertion is unnecessary unless the product changes the meaning to “complete at resolution commit.” Never make that unproved stronger claim.

## One exact decision read

The decision-read RPC takes a separate transaction advisory lock keyed by stable decision identity (hash collisions may cause extra waiting, never identity aliasing). It then checks for a saved identical request and returns the original read on retry. A changed request for the same decision fails. It must not take the qualification lock, so it can observe and save the committed state while a writer is paused.

Use **one materializing SQL statement** for the read and manifest insertion. CTEs in that statement discover scope, candidate/support records, heads, witnesses, trust records and limits, and insert the manifest. Query dependencies from the same statement snapshot; do not call helpers that issue their own independent SQL reads. Earlier lock/retry statements contain no evidence used in selection. Concurrent capture/parse/qualification commits are therefore either visible to the statement or absent as whole transactions.

The manifest may store ordered typed reference rows inserted in that same statement rather than one huge JSON field. A canonical text representation and hash must be reconstructible identically. No later step fills gaps by querying current state. Exact source documents remain in their immutable parent tables. A manifest cannot refer to a partially registered parse: the prerequisite parse RPC already inserts the full result atomically.

A `REPEATABLE READ` transaction is a viable alternate implementation **only** if one owned connection begins it before all evidence reads and holds it through manifest persistence. A sequence of separate HTTP RPCs is not that transaction. Do not issue `SET TRANSACTION` after an RPC has already taken its snapshot. Prove the chosen approach in the real entry point and isolation level.

Selection occurs after the read transaction commits. Failure after the read leaves a valid unconsumed read, which the same request resumes. The result is appended separately through the central writer, with exact read/policy/runtime references. Published/research call attachment must atomically link the final result identity to the consuming run under the existing publication contract; no consumer may read newer evidence between selection and attachment. A later withdrawal does not mutate an earlier result or published call.

## Complete scope that can operate over a growing archive

Adopt `fpi-decision-scope-v2`. Let D be the India calendar date of the server's read statement, H the policy's `max_history_age_days`, and C the current-age limit, with H >= C as today.

1. **Decision dates:** every reporting date in `[D-H, D]` that has at least one committed successful parsed membership. Include all such members, regardless of parser allowlist, endpoint, value equality, qualification, withdrawal or apparent occurrence age. New unqualified/policy-excluded evidence must not disappear from current-date or conflict reasoning.
2. **Newest-date sentinel:** discover the globally maximum committed successful reporting date using the membership date index. Add that date's complete membership set even if it predates D-H. This preserves `STALE` rather than falsely claiming `NO_OBSERVATIONS` when the archive contains only old evidence. A date after D is a clock/data consistency failure, not a silently excluded current observation. Include the exact selected sentinel/date in the manifest.
3. **Complete parse support:** retain each candidate's original parse identity, record hash and complete member list. Whole parse results remain immutable. Extra dates on the same Monthly result are support evidence; they do not recursively expand the decision-date set. v2 needs explicit `candidate_membership_ids` separate from these support memberships. Otherwise a single overlapping Monthly page silently changes the stated scope.
4. **Qualification heads:** include exact current head or explicit absence for every candidate membership, distinct value, parser and date. Preserve the current per-date resolution head and its historical chosen-member/value/parser head witnesses. A witness may refer to a member outside the current candidates only as support; validate its retained parse and exact date. Never infer absence from an omitted query result without storing the declared target set.
5. **Ordering trust:** include exact observed capture-order trust head/absence and its attestation reference for every candidate capture. Derive ordered IDs from those observations. Imports default to unordered. A selector argument alone cannot confer trusted timing.
6. **Failed parses:** these have no reporting-date membership. Define diagnostics separately: all committed failures whose **database parse stored_at** lies within `[read_at - W days, read_at]`, with policy-bound W (proposed initial W=7). Include failures for any capture referenced by a candidate regardless of W. This time filter declares diagnostic relevance only; it is not a historical-visibility test. A late commit with older stored_at can be outside this diagnostic scope, and that is explicit. It never supplies a zero or a withdrawn date.

The scope includes every competing parser, not just allowed or accepted ones. Endpoint priority and allowlists apply only inside the selector after the full date set is known. Identical values from different captures retain different members. New imports can affect future decisions only through dates/captures they actually contain; insertion time never supplies occurrence order.

**Changed v2 output semantics:** `excluded_dates` describes dates inside the decision-date scope only. The manifest/result declares the excluded region `reporting_date < D-H except newest sentinel`, rather than listing every old date as `HISTORY_AGE`. Failure diagnostics follow the named W rule rather than claiming all-time coverage. These omissions are deliberate scope semantics and change the policy/result version. Maintain v1 replay for previously retained v1 inputs. Compare decision/current/history parity against full-archive v1 on bounded fixtures, allowing only the documented diagnostics/exclusions differences. Do not call the entire result byte-identical across versions.

### Bounds, long chains and reference loading

Continue the existing candidate guardrails initially: 2,048 distinct parses/captures, 20,000 candidate/support memberships, 4,096 members in a resolution basis, 64 allowlist entries. Proposed head/witness cap is 100,000 distinct referenced event records because 20,000 members can require more than 20,000 distinct member/value/date heads. Bound the compact manifest to 16,000,000 encoded bytes and the full reconstructed selection data to 64,000,000 bytes; benchmark and freeze these numbers before implementation. Count and size checks occur before aggregate allocation, with a capped `limit+1` probe used only to detect overflow, never to select a winning subset. Set statement/lock timeouts and recursive/document limits as in the prerequisite storage contracts.

The complete declared scope can still exceed finite limits after unusually dense capture or adversarial input. Save a small immutable `READ_SCOPE_EXCEEDED` record with request/policy/scope and overflow dimension, then return no usable snapshot or feature. Do not truncate, reduce history, discard unqualified candidates or pretend the failure is `NO_OBSERVATIONS`. Operational retention/rate policies can bound new evidence volume, but must never delete evidence referenced by a saved decision. Increasing a cap is a new reader/policy version with resource verification.

**Do not embed full event chains in every v2 snapshot.** An indefinitely long parser withdrawal/reinstatement chain would defeat any date window. The database retains/enforces every predecessor and rejects forks on append. A saved read contains observed heads and each relevant resolution's explicit historical head witnesses; its claim is what the authoritative transaction read, not a self-authenticating reconstruction of the whole ledger. Pure v2 validates the small witness graph, scope/target consistency and ordinals; it does not demand every predecessor be included. Historical full-chain audit follows immutable predecessor references independently. Never re-query those predecessors to decide current state.

Raw capture and artifact bytes likewise stay behind immutable references. Resolve each distinct capture/parse once per verification pass; hash the exact retained original, validate the full complete parse by the accepted restore codec, derive the compact typed selection input, then release large raw bytes. A streaming loader is an optimization, not permission to skip checking bytes. Retain complete parse member identities in the manifest and canonical INR/source record references for members used by the result. Do not accept a hand-assembled partial parse as a replacement for the retained original. Persist capture timing/source metadata in the compact manifest with its parent hash and verify them against that parent.

The new v2 pure input therefore needs a validated compact capture/parse reference type. It cannot pretend that the existing `FpiParseResult(capture=full_bytes)` and full-predecessor `FpiDecisionSnapshot` have already acquired these properties. The distinction between candidate and support membership is required in construction, hashes and selection.

## Artifact retention, source timing and executed-code trust

Storage must not import or execute a supplied artifact. A trusted runner executes an approved locally installed implementation, independently fingerprints its reproducible bundle and dependency/configuration manifest, and binds the run to capture, parse record, entry point and output hash. Save that execution attestation immutably. Hashing only one `.py` file while imports/configuration vary is insufficient.

Likewise the selection runner binds its executed selector/feature bundle, policy, read hash and result hash. The expected bundle comes from release/configuration authority; comparing two caller-supplied hashes proves nothing. Missing/mismatched runtime evidence produces `EXECUTION_UNVERIFIED` and prevents activation/consumption. Offline storage/replay inspection may still examine those records as unqualified evidence.

Capture-order trust requires acquisition evidence: a known runner observed those request intervals, retained the receipt/attempt identities and did not fabricate imported starts. A trustworthy capture interval orders our non-overlapping observations only. It never proves NSDL publication revision or finality. Imported private captures need a separately labelled reviewed attestation; any interval normalization must enclose the original interval and retain its original receipt hash. Absent start evidence stays absent/unordered.

The exact attestation schema and authenticated runner authority are **unimplemented dependencies**. Proposed append-only attestation and trust-transition tables must have their own bounded contract and central writer operation before the decision layer can set ordered-capture trust or permit a qualified parser. Until then, proposed storage can be tested with clearly authored synthetic attestations under the isolated test role only; production eligibility remains false. Never accept synthetic fixture attestations through a production trust path.

## State changes and replay

Membership ACCEPT starts/reinstates that member only. Value/parser WITHDRAW or QUARANTINE blocks all applicable candidates; a value/parser ACCEPT clears that scope block without accepting previously unqualified memberships. A later membership ACCEPT cannot clear a parser/value block. No action deletes an earlier event or creates measured zero.

Date RESOLVE remains a policy decision choosing an already qualified member from a complete same-date basis. Its witness records exactly which heads made the choice qualified. A later candidate changes the basis and returns `STALE_RESOLUTION`; adding even a currently unqualified or policy-excluded membership cannot silently preserve an old resolution. A chosen target later withdrawn yields unavailable. Proposed compatibility with current semantics: explicit reinstatement can make the chosen target usable again when the candidate basis is unchanged. If the parent wants every withdrawal to invalidate a resolution permanently, that is an additional model-policy change and must be versioned separately.

Parser correction is a new parse under its own retained PARSER artifact; the old parse stays. Qualify its members deliberately. A failed parse or an omitted date does not constitute withdrawal. A repeated value A after B is a distinct ordered capture occurrence, so A → B → A works without modifying a value's first-seen identity.

Legacy timestamp replay refuses `select_at(timestamp)` without a retained read. It returns `VISIBILITY_UNPROVEN`; neither imported timestamps nor current database rows manufacture a former read. A corrected retrospective experiment uses a new research decision ID and explicitly records later-known evidence. Saved-read replay never incorporates later imports, withdrawals, source re-downloads or today's policy.

## Failure reconciliation

| Failure | Required recovery |
|---|---|
| Timeout after qualification submission | Read/retry the same command ID. Return the retained event if committed; otherwise retry the identical command. Do not allocate a new identity or predecessor. |
| Expected predecessor conflict | Return conflict and observed head. Reconcile intent against that head; any revised action is a new command with a new explicit expected predecessor. |
| Resolution basis conflict | Return bounded stale-basis code and basis digest; do not silently expand the caller's approved basis. Review the new candidate set. |
| Timeout after decision-read submission | Retry the same decision/request. If committed, return precisely that manifest even if newer records now exist. If the whole transaction rolled back, a retry can take a new read because no prior read existed; its server read time is retained. |
| Failure loading a retained dependency | No selector/result. Record bounded integrity/unavailable failure; preserve the manifest for diagnosis. Never replace the dependency with a fresh download. |
| Crash after read, before result | Reload the committed read and execute the verified artifact. No fresh current-state query. |
| Timeout after result submission | Reconcile by read/result identity and exact hash. Conflicting output fails; it must not overwrite the first result. |
| Timeout/cancel during locks or statement | Rollback leaves no partial events/manifests. A timeout is not interpreted as absence until identity reconciliation succeeds. |

Sanitize conflicts and logs; raw capture/source documents, private evidence bodies and credentials never appear in exceptions. Grant application roles SELECT/approved entry-point EXECUTE only. Apply RLS and owner-level UPDATE/DELETE/TRUNCATE refusal to all new evidence tables. Functions have fixed search paths and private helpers. Operational manifests/read-failure records also remain immutable.

## Executable acceptance scenarios for the next packet

These are proposed tests, not results claimed by this leaf. Use the existing socket-only isolated PostgreSQL harness with two or more independent connections, service-role RPC calls through the real Python writer, explicit transaction barriers and bounded waits. Do not simulate commit visibility by sorting Python timestamps. Each concurrency test must prove the intended pause barrier was reached before asserting the read. Equal/backward clock tests require an isolated test-only database clock fixture at the clock helper seam; they must not change the host clock or expose caller time overrides through the production RPC.

| ID | Setup and action | Required assertion |
|---|---|---|
| Q01 | Commit ACCEPT M. Pause a WITHDRAW transaction after event insertion; capture a decision read on connection B; then commit withdrawal and capture another read. | B completes without waiting on qualification lock; first read contains ACCEPT head, second contains withdrawal. Replay of first remains unchanged. |
| Q02 | Hold transition T1 after ordinal allocation; start T2 on a distinct scope; inspect blocked state; rollback T1, then retry with commit. | T2 cannot allocate/commit while T1 holds the lock. No retained event for rollback; committed ordinals are unique and ordered. Distinct parse transactions remain free to commit in reverse allocation order. |
| Q03 | ACCEPT M; RESOLVE D; WITHDRAW M with an injected equal database clock for all relevant actions. Repeat with clock stepping backward. | Equal time succeeds with ordinal/witness chronology, later decision is withdrawn, prior read unchanged. Clock rollback either preserves explicit age semantics or yields the declared clock error; never reorders events. |
| Q04 | Supply caller `recorded_at`, forged ordinal, unknown fields, altered command content/hash, boolean ordinal and noncanonical timestamp through direct SQL. | Rejected before any event insertion. A claimed source time cannot determine event order or eligibility. |
| Q05 | Submit two contradictory actions with identical expected predecessor; use independent connections and barriers. Repeat two null-root commands. | Exactly one new successor; loser gets conflict. Same identical command submitted concurrently returns one event, same time/ordinal; changed payload under same identity fails. |
| Q06 | Save RESOLVE basis {A,B}; append same-date member C before or after resolution basis statement, including commit during paused resolution. | Before statement requires C in basis. After statement preserves exact witness but a future read with C returns `STALE_RESOLUTION`. No silently expanded resolution. |
| Q07 | Resolve chosen A, then withdraw/reinstate at membership, value and parser scopes individually and in combinations. | Scope blocks compose correctly; clearing one leaves others; no older occurrence revives by default; explicit fallback policy has distinct hash/reason; old read unchanged. |
| Q08 | Pause parse transaction with complete month inserted; decision read; commit; second read. Force middle-member constraint failure separately. | First sees no parse or members; second sees complete result. Failed transaction leaves none. Reverse commits for distinct parses do not infer occurrence order. |
| Q09 | In fixed scope, add newer unqualified member, disallowed parser member, opposite endpoint value and a wide-scope withdrawal separately. | Each is retained in the read and affects state under declared rules. Reader cannot choose only accepted or policy-allowed rows. |
| Q10 | One Monthly parse straddles D-H. Add another parse only for a support date outside horizon. | Complete original parse is retained/verified, but support date does not recursively enter candidates. Current/history match declared scope; newly introduced support-only alternative does not change decision semantics. |
| Q11 | Archive contains only older-than-H data, then a fresh conflicting date; separately empty archive. | Newest sentinel produces STALE in first case; fresh conflict is unavailable without fallback; empty archive is NO_OBSERVATIONS. |
| Q12 | Add failures inside/outside W, and an old failure sharing a candidate capture. Commit a paused old-stored_at failure late. | Exactly named diagnostic scope applies, no synthetic dates/zeros. Retained read unchanged. Omitted all-time diagnostics are declared, not presented as all-time completeness. |
| Q13 | Repeated parser qualification chain exceeds old 20k events, while scoped candidate set is small. | Compact heads and resolution witnesses remain bounded; full chain is still retained/auditable; v2 does not load every predecessor. Removing a required witness is rejected. |
| Q14 | Reach each count/byte limit then add one required record; include a 4,097-member resolution basis and oversize canonical documents. | Limit case behaves as specified; overflow saves READ_SCOPE_EXCEEDED, no selector/result or partial winner. No huge aggregate is built before bounded checks. |
| Q15 | Same capture used by several parses, several date rows and historical witness references. | Loader verifies each distinct original once; wrong hash/missing referenced bytes fails; no current-state fallback. Selector inputs retain exact source/INR identities. |
| Q16 | Lost acknowledgement after read/result commit, then late import/withdrawal before retry. | Same identities return exact original receipt/read/result. Different policy under same decision ID conflicts. Aborted original transaction leaves no phantom saved read. |
| Q17 | Retain arbitrary artifact bytes; submit parse claiming its hash without execution evidence; then run trusted fixture harness with exact/mismatched dependency bundle. | Storage retention succeeds where valid, but qualification/consumption stays EXECUTION_UNVERIFIED without matching trusted execution; storage never executes bytes. |
| Q18 | Import old A after saved B decision. Test trusted sequential interval, overlap, missing start and A→B→A. | Saved B unchanged; future ordering follows declared trusted intervals only. Incomplete/overlapping order conflicts; newest reporting date rule remains independent of import order. |
| Q19 | Ask historical cutoff without read ID; change today's policy/artifact after a saved read. | VISIBILITY_UNPROVEN for bare time; saved read replays with its exact original policy/artifact or reports missing executable dependency, never silently upgrades. |
| Q20 | Run actual scheduler, staged and replay paths with injected same retained read and verified fixture runner; then missing/conflicted/withdrawn/zero/insufficient-history variants. | Same current/history membership IDs, read/policy/result hashes, normalizer window and quality reasons. Non-AVAILABLE result cannot become raw/normalized zero. No forbidden fetcher/network/AI path runs. |
| Q21 | Alter result, source document, witness scope/ordinal, selector code or capture-order attestation; attempt direct writes and owner UPDATE/DELETE/TRUNCATE; reapply migration. | Every integrity/permission negative control fails; populated evidence and unrelated permissions survive reapplication; errors do not leak raw data. |

Q20 must include the real FPI feature normalization, not only selection: INR hundredths-to-crores conversion occurs once, history is chronological and excludes current, policy window is passed explicitly, degenerate MAD remains missing. Pin/hash the feature implementation too. Current pure policy stores a feature version label but does not prove which normalizer ran; v2 result execution evidence must close that gap.

## Proposed migration and ownership sequence

1. **Parent freezes semantics first:** adopt or revise v2 event order/witnesses, complete date scope, diagnostic W, candidate/support distinction, caps, execution trust and explicit reinstatement behavior. Update contracts and acceptance register. Keep leaf24.1/24.2 artifact/parse work frozen until independently accepted. This is a new next packet, not scope expansion into their files.
2. **Pure/codec owner:** own a new qualification/read codec and scoped v2 selector module plus tests. Preserve v1 reader behavior for old snapshots. Repair the tied-clock model with versioned types; do not silently reinterpret v1 event hashes. Obtain GitNexus impact evidence or the parent-authorized fallback before symbol edits.
3. **SQL owner:** next unused forward migration, proposed `20260927000012_fpi_qualification_decisions.sql` only after numbering is confirmed. Add append-only qualification commands/events, immutable policies, decision reads/reference rows and results. Add indexed scope/target/predecessor/ordinal, reporting-date and parse stored-time lookup. Bind to accepted parse tables; no changes to published ledgers. SQL also needs the adopted attestation/trust contract before granting eligibility.
4. **Writer owner:** make serial central-writer additions after leaf24.1 releases its lease on `writer.py`. Validate exact request/receipt codecs and reconcilable retry behavior. Do not let separate workers edit this shared file concurrently.
5. **Database verifier owner:** own a separate verifier for Q01–Q19/Q21 with actual paused transactions, isolation/lock introspection, rollback, reverse parse commit order and direct-SQL adversarial inputs. Run only the existing authorized local runtime after its health check; parent owns lifecycle.
6. **Integration owner after storage acceptance:** design the trusted acquisition/parser/selector runner attestations and feed the one retained read/result through actual consumers. Add Q20 and publication-link tests without activating production. Wire FPI only after source authenticity, full history coverage, approved model/feature version and all repair/release gates are separately met.
7. **Parent independent acceptance:** adversarially validate contracts, original-source round-trip, all relevant regressions, real transaction evidence and actual consumer negative controls. Update handoff/checkpoint. No release or predictive-skill claim follows merely from storage passing.

The precise durable execution-attestation schema is a remaining design dependency, not something a writer can invent through `evidence_ref`. Keep eligibility disabled if that dependency is deferred.

## Why the tempting alternatives fail

| Alternative | Failure or trade-off |
|---|---|
| Timestamp cutoff over stored_at/recorded_at | A paused transaction can already have an early time but be invisible; later commit changes the apparent historical set. Caller backdating and tied clocks add ambiguity. |
| Sequence alone as availability | IDs allocate before commit and can commit in reverse order. The proposed ordinal is justified only for qualifications by the held-lock/fresh-read protocol, never source order. |
| Same-target lock only | Prevents that chain's fork but does not make a date resolution's membership/value/parser reads coherent against simultaneous independent-scope changes. Requires a carefully ordered full lock set or one-statement witness; global qualification lock is simpler here. |
| Per-date lock only | Parser/value withdrawals span many dates. Incomplete lock coverage allows resolution under stale broad-scope state; complete coverage adds lock-order/deadlock work. |
| Several READ COMMITTED evidence queries | Can combine a before-withdrawal membership read and an after-withdrawal resolution read that never coexisted. One materializing statement avoids that split. |
| REPEATABLE READ across separate RPC calls | Each request owns a separate transaction; a name in the wrapper does not preserve an MVCC snapshot. Use one owned transaction or the single-statement RPC. |
| Serializable alone | Useful isolation, but still needs command identity, predicate completeness, retry reconciliation and publication linkage. It does not authenticate artifact execution or reconstruct historical reads from timestamps. |
| Client submits a snapshot to an append RPC | Can omit adverse/unqualified candidates; validating supplied hashes cannot prove completeness. Discovery and persistence belong to the authoritative reader. |
| All archive forever | Initially simple and faithful to v1, but bytes/events grow without bound. It is a transitional proof path only, not the final operating design. |
| Newest N rows / accepted rows only | Can drop newest unqualified dates, competing endpoint/parser values and scope withdrawals; receipt success would conceal selection bias. Overflow must fail explicitly. |
| Delete old evidence to stay under caps | Breaks exact old-read replay and audit. Use compact references and explicit scoped semantics; retain referenced originals. |
| Full historical chains in every scoped snapshot | Date scoping does not bound repeatedly changed parser/value chains. Save authoritative observed heads and explicit historical resolution witnesses instead. |
| Store artifact hash and trust caller execution | Allows a parser/selector to claim an unrelated retained bundle. Execution must be verified by a separately trusted runner. |

The next acceptance target is a saved, complete scoped read that survives real concurrent commits and replays through the same verified consumer logic. This report does not close that target; it makes the required contract changes and tests concrete.
