# FPI decision-snapshot selection

This pure module selects from an exact, immutable set supplied by a decision reader. It checks internal consistency. It cannot prove that the reader saw committed records, read every relevant candidate, authenticated a capture or retained the named parser artifact. Those remain required storage and acquisition checks. No FPI feature is activated by this contract.

## Interface and records

`select_fpi(snapshot: FpiDecisionSnapshot | None, policy: FpiSelectionPolicy) -> FpiSelection` is the consumer interface. A missing snapshot returns `VISIBILITY_UNPROVEN`; a timestamp alone is rejected. Live, staged and replay must eventually use this same function and the same saved inputs.

Frozen dataclasses validate construction and accept immutable tuples only. `FpiParsedDay` retains the canonical INR document and a separate source-evidence hash. Its value hash is the existing canonical INR hash; no first-seen, parser or capture time enters it. Numeric validation reuses the existing canonical builder, without retaining its synthetic validation-only metadata.

`FpiParseResult` binds a validated complete capture, immutable parser implementation SHA-256, definition version, parse recording time and the entire successful date set, or a bounded failure reason and no days. Successful reports require HTTP 200 and the canonical INR definition version. Partial HTTP 206, empty HTTP 204 and other responses may only carry failed results. Capture plus parser implementation plus definition identifies one retained parse result. Contradictory output or recording time under that identity is rejected. An exact retry retains its original recording time. A changed parser artifact is a new result, never a new source occurrence. Each dated membership has its own content identity, including separate source-evidence identity.

`FpiQualificationEvent` contains scope (membership, value, parser or date), target, action, recording time, expected prior event hash, reason and evidence reference. Full per-target chains are required in the snapshot; retries deduplicate and competing successors reject. Membership starts unqualified. ACCEPT qualifies it; WITHDRAW and QUARANTINE remove it. Value/parser ACCEPT removes a scope block; their absence does not itself block a qualified membership. A later ACCEPT explicitly reinstates its target. Qualification may follow retrieval and parsing by any delay.

Date-scope RESOLVE chooses one qualified membership and names the complete membership set it resolves. It can settle parser or endpoint disagreement. The chosen membership must already be qualified when the resolution is recorded; later qualification cannot activate an earlier invalid resolution. A later added candidate invalidates the saved resolution until reviewed again. A later withdrawal of the chosen target makes it unavailable. Resolution is policy evidence, not a source-finality claim.

`FpiDecisionSnapshot` binds decision identity/time, policy hash, exact parse results, complete qualification chains and `ordered_capture_ids`. The last field is the reader's explicit assertion that those request intervals can support local occurrence ordering. It is never a visibility or authenticity proof. Imported captures default to unordered. Construction checks references, date/time consistency, retry identity and chain completeness within the supplied set, then hashes the canonical input set. A future durable reader must establish external completeness and save this exact snapshot with the decision.

## Selection rules

For each reporting date and endpoint, group parser memberships by capture. Qualified parser alternatives that disagree conflict; unqualified alternatives cannot supersede an accepted parse. Select maximal capture occurrences under strictly non-overlapping asserted request intervals: earlier completion must precede later request start. Touching intervals do not establish that strict order. Completion order, registration time, value first-seen and hashes never establish revision order. Equal values may corroborate while preserving all membership IDs. A third non-overlapping occurrence can supersede conflicting earlier requests. A -> B -> A therefore selects the final A with a distinct occurrence identity.

A newest unqualified or blocked capture makes its date missing. WITHDRAW/QUARANTINE do not revive older occurrences under the default policy. The policy may explicitly permit older qualified fallback, and the result records that reason. A new qualified parse of the same capture can replace a withdrawn parser membership; withdrawing a value or parser applies its wider declared scope.

Latest/Monthly disagreement is a conflict by default. Explicit Latest or Monthly priority requires a policy rationale and changes the policy hash. Priority uses the preferred endpoint when present, including its missing/conflict state; when absent, it uses the remaining endpoint. An unresolved newest reporting date prevents fallback to an older current date.

Source omission and a failed parse do not identify a withdrawn reporting date. Failed results remain in the snapshot and diagnostics, produce no memberships and never become zero measurements. A complete parse-result object cannot prove that an untrusted parser included every source date. Durable registration must retain the complete result atomically and verify the parser artifact.

Current age and history age use calendar dates in India (UTC+05:30). History contains unique reporting dates strictly before current, only resolved qualified values, within the explicit decision-relative history age, with the newest `history_window` dates returned in ascending order. The preserved research floor is `10 <= minimum_history <= history_window <= 2520`; history age must be at least current age. Below the minimum, status is `INSUFFICIENT_HISTORY` and the feature remains unavailable, while the valid current value and available history remain inspectable. A zero measurement requires a validated canonical value of zero. Stale, conflicted, withdrawn and unqualified dates have no current measurement.

## Frozen identities and limits

The frozen policy binds selector version and selector implementation SHA-256, parser/definition allowlists, endpoint arbitration and rationale, withdrawal fallback, current/history ages, history window/minimum, feature/model versions, prediction horizon, timezone and missingness treatment. The implementation hash is an artifact assertion requiring future runner verification, not a mutable label or a self-authentication claim.

Results hash every returned field except the hash itself: snapshot/policy/input identities, status, current/history values and membership IDs, exclusions/reasons and parse diagnostics. Sorting hashes canonicalizes equal evidence sets; it never chooses between different values.

Limits are 31 dates per parse, 2,048 parse inputs, 20,000 qualification events, 20,000 memberships, 2,048 ordered capture references, 4,096 resolution-basis memberships and 64 entries per allowlist. The retained parse set permits at most 64,000,000 capture-document characters; each canonical INR document permits 32,768 characters. Input count limits apply before deduplication. Qualification chains use a memoized linear predecessor walk. Selection decodes capture timing once per distinct capture and finds the interval frontier in linear work per date/source.

## Verification and required later evidence

Pure tests cover structurally applicable timing-review checks: occurrence reversion, delayed qualification, saved-set stability after imports, overlap and endpoint conflict, parser corrections, scoped withdrawal/reinstatement, complete-result validation, duplicate retries and predecessor forks, complete policy/result hashes, freshness/history coverage and explicit missingness. Repeated pure calls prove deterministic repeatability; live/staged/replay integration parity remains a later check. A regression with 20 synthetic 25-date parses checks that each capture envelope is decoded once during selection.

Actual paused-writer/concurrent-reader commit-gap tests, reverse commit order, concurrent registration and transition serialization, atomic rollback, capture authenticity, parser-artifact retention, complete candidate reads and persisted snapshot replay remain required. Pure tests do not close these gates. Precision normalization for imported seven-digit receipt timestamps belongs to the import adapter; no request start may be invented to fit a capture.
