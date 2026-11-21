# FPI observation timing review — 27 September 2026

The current pure selector is not ready to become the durable FPI selector. It cannot represent a return to an earlier value, and its first-seen constraint conflicts with observation visibility after retrieval. Keep the raw-capture layer separate. Add capture membership and qualification evidence before connecting FPI to live, staged or replay decisions.

This is leaf22.3, a local architecture review. Its only write is this report. No application database, provider, credentials or runtime service was accessed. No source file or production setting was changed. No deployment, prediction-quality or full-goal acceptance is claimed.

## Evidence and scope

Reviewed `IDENTITY.md`, the 27 September repair amendment in `MASTERPLAN.md`, `TASK.md`, `docs/FPI_OBSERVATION_CONTRACT.md`, `docs/FPI_CAPTURE_CONTRACT.md`, the observation and HTML parser modules, and their two test files. Applied Humanscope, Codebase Design and the quality-first policy. Python is sufficient for these pure checks; Docker and heavier Hermes services are unnecessary and were not started. GitNexus query failed with database storage version 42 versus runtime version 40. No index rebuild was attempted under this report-only assignment. Supplied source files were read directly; no symbol was edited or committed.

Checkout HEAD was `9fa150538d08ab5a2a6c587976552944f47a724d`, with extensive uncommitted repair work. HEAD alone does not identify the reviewed implementation. SHA-256 fingerprints:

| File | SHA-256 |
|---|---|
| `pipeline/src/research/fpi_observation.py` | `f6769bd4411a4e8dda98a3402ac9f75a8e5bde1fb8dbc5aedced72e2efeb2a11` |
| `pipeline/src/research/fpi_parser.py` | `afe9fdc67c1fabe27f51dcf29478c73574a837ddd0b4285eba61c2ff9a94cabe` |
| `pipeline/tests/test_fpi_observation.py` | `204e9f4009696def9a43596a1d3e1c541dc33aafef0839d906e4169e5977bd09` |
| `pipeline/tests/test_fpi_parser.py` | `ecbac7acd058f26f7f06721125ee171270bb87327019b9fff12779652d7726bf` |

Ran from `pipeline` with bytecode and pytest cache writing disabled:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -B -m pytest -p no:cacheprovider tests/test_fpi_observation.py tests/test_fpi_parser.py -q
```

Result: **86 passed in 0.69 seconds**. These checks prove the current structural contract, including the problematic timestamp restriction. They do not establish durable availability. Independent reproductions below also ran successfully without I/O in the domain code.

## Findings

**P1 — Value first-seen cannot order source occurrences.** `fpi_observation.py:263–285` enforces one first-seen time per value hash and selects the largest first-seen time for each reporting date. For A at 12:00, B at 12:01 and A again at 12:02, preserving A's identity and first-seen chooses B in all six input permutations. Changing A's first-seen to 12:02 raises `FPI first-seen time changed for unchanged observation`. This is a proven representation defect if the intended policy accepts a later sequential occurrence of A. Whether that later response should be accepted as a source reversion is a separate qualification decision.

**P1 — Durable observation visibility cannot fit the timestamp invariant.** `fpi_observation.py:137` rejects `first_seen_at > retrieved_at`. A capture completed at 12:00 can first become durably visible at 12:05, or be parsed and accepted much later. Supplying 12:05 raises `FPI first_seen_at cannot follow retrieval`. Supplying 12:00 instead makes it eligible for a 12:01 decision even when the archive is imported the following day. The selector receives no import, parse, acceptance or visibility evidence to exclude it. This is a prospective integration defect, not evidence that a production call was contaminated.

**P1 — A transaction timestamp alone cannot establish past decision visibility.** The capture contract explicitly says `stored_at` is assigned inside a transaction and is not a commit or observed-read time. Consider an insert timestamped 12:00, a decision read at 12:01 that cannot see it, and completion of the write transaction at 12:02. A later replay using `stored_at <= 12:01` would include evidence the original read lacked. This is a contract-level counterexample; no database experiment was authorized or run. Adding a timestamp or monotonic ID allocated inside that same transaction does not by itself repair the missing visibility evidence.

**P2 — Endpoint disagreement is silently treated as revision order.** Two eligible values for one reporting date, A from Latest at 12:00 and B from Monthly at 12:01, select Monthly B. Reverse which new value is first seen later and the selection changes. There is no source precedence, stale-response, conflict or explicit resolution policy. A later download is not proof that its contents supersede the other endpoint. The existing same-time conflict protection does not address differing retrieval times.

**P2 — Parser output is a candidate, not accepted observation membership.** `fpi_parser.py:271` sets first-seen equal to retrieval. Two successful parses of the same authored report at different times produce the same value hash with different first-seen times; feeding both directly to the selector raises the changed-first-seen error. This agrees with the document's warning that a writer must reconcile parser candidates. A second parser implementation producing another value from the same capture at the same first-seen time raises a same-time revision error, but the module has no means to qualify a correction, retain rejected parses or reconstruct which parser was accepted at a past decision.

**P2 — No acceptance, withdrawal or model-policy state is represented.** These omissions are explicitly acknowledged in the observation contract. Consequently, a valid hash and successful parse must not be treated as model eligibility. A later withdrawal must affect future decisions while leaving the old call and its actual input manifest intact. Parser repair is not a new source occurrence. The current records cannot express those distinctions.

Severity reflects consequences of wiring the present selector into durable decision inputs. The reviewed code labels itself structural and does not claim these production guarantees.

## Executable counterexamples

Run the following in `pipeline` using `python -B -`; it uses existing authored synthetic fixtures. Times, values and assumed import timing are synthetic, not NSDL release evidence. No new test or source file is required.

```python
import runpy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import permutations
from src.research.fpi_observation import build_fpi_observation, select_fpi_history

fx = runpy.run_path('tests/test_fpi_observation.py')['_fpi_fixture']
t0 = datetime(2026, 9, 25, 12, tzinfo=UTC)

def obs(shift, minute, source='Latest'):
    args = fx(25, shift=shift)
    args.update(retrieved_at=t0 + timedelta(minutes=minute),
                first_seen_at=t0 + timedelta(minutes=minute))
    args['source_url'] = args['source_url'].replace('Latest', source)
    return build_fpi_observation(**args)

history = [build_fpi_observation(**fx(day)) for day in range(1, 11)]

def select(items, minute=10):
    return select_fpi_history(
        history + list(items), as_of=t0 + timedelta(minutes=minute),
        max_current_age_days=3, max_history_age_days=40)

a, b = obs(0, 0), obs(1, 1)
a_again = replace(a, retrieved_at=t0 + timedelta(minutes=2))
assert [select(p).current.net_hundredths_cr
        for p in permutations([a, b, a_again])] == [39800] * 6

try:
    select([a, b, replace(a_again, first_seen_at=a_again.retrieved_at)])
except ValueError as exc:
    print('REVERSION_NEW_FIRST_SEEN:', exc)

args = fx(25)
args.update(retrieved_at=t0, first_seen_at=t0 + timedelta(minutes=5))
try:
    build_fpi_observation(**args)
except ValueError as exc:
    print('DELAYED_VISIBILITY:', exc)

# If this archive was only imported the next day, that fact cannot be supplied.
assert select([a], minute=1).status == 'AVAILABLE'
monthly = obs(1, 1, 'Monthly')
assert select([a, monthly]).current == monthly

reparse = replace(b, raw_sha256=a.raw_sha256,
                  retrieved_at=a.retrieved_at, first_seen_at=a.first_seen_at,
                  parser_version='new-parser')
try:
    select([a, reparse])
except ValueError as exc:
    print('PARSER_CHANGE:', exc)

# Using ingestion time as revision time instead also loses source ordering.
assert select([b, obs(0, 3)]).current.net_hundredths_cr == 39700

from src.research.fpi_parser import parse_nsdl_fpi_html
report = runpy.run_path('tests/test_fpi_parser.py')['_report']
p1 = parse_nsdl_fpi_html(report(25), source_url=a.source_url,
                        retrieved_at=t0)[0].observation
p2 = parse_nsdl_fpi_html(report(25), source_url=a.source_url,
                        retrieved_at=t0 + timedelta(minutes=1))[0].observation
try:
    select([p1, p2])
except ValueError as exc:
    print('REPEATED_PARSE:', exc)
```

Observed exception messages, in order:

```text
REVERSION_NEW_FIRST_SEEN: FPI first-seen time changed for unchanged observation
DELAYED_VISIBILITY: FPI first_seen_at cannot follow retrieval
PARSER_CHANGE: Conflicting FPI revisions at the same availability time
REPEATED_PARSE: FPI first-seen time changed for unchanged observation
```

The out-of-order example proves that changing the timestamp meaning is insufficient; it does not assert that either A or B is the true source revision.

## Proposed minimal domain contract

The following is an implementation proposal. It does not amend the accepted source definition or assert source release times, revision numbers or finality. Preserve full INR components and the existing value hash definition.

| Record | Identity and required meaning |
|---|---|
| Value | Existing canonical dated INR document and `observation_sha256`. No retrieval, parser, acceptance or occurrence order in this identity. Value first-seen may be descriptive metadata; it never determines which occurrence wins. |
| Capture occurrence | Existing `capture_sha256`, complete bytes and source endpoint, request start and retrieval completion. A retry retains this identity; a new request has a new occurrence even if raw bytes match. Raw-body hash alone is insufficient. Bind future trusted acquisition to an attempt/runner receipt; imported caller timestamps remain assertions. |
| Parse result and membership | An append-only parse record keyed by capture identity plus immutable parser implementation identity and definition version. It contains either a bounded failure reason or the complete successful set of dated memberships. Each membership links the capture, value hash and separately preserved source-evidence hash. Replaying the same parser/capture must yield the same full result; a mismatch is a conflict, not an overwrite. |
| Qualification event | An append-only event targeting a membership or a declared scope: accept, quarantine, withdraw or explicitly resolve/supersede. Record policy version, reason/evidence references, expected prior event identity and recorded time. Use membership scope by default so an invalid parse of one capture does not disqualify all occurrences of the same value. A value-wide or parser-wide withdrawal needs explicit scope. |
| Decision evidence snapshot | Exact committed membership IDs, qualification event IDs, complete relevant per-date/source candidates and exclusion reasons read for the decision, plus policy hash, input-set hash, read evidence and decision identity. This supplies actual replay membership. A timestamp or `MAX(id)` alone cannot stand in for this set. Record retained capture references needed to reproduce parsing. |
| Frozen selection/model policy | Immutable selector implementation identity; parser/definition accept list; source conflict and supersession rules; import/visibility requirements; withdrawal/fallback semantics; India calendar-day freshness limits; history window/minimum; feature version, missingness treatment, strategy/model version and prediction horizon. Content hash the complete policy. |

Parser labels such as `v1` must map to immutable implementation evidence, including the code artifact and relevant parsing dependencies/configuration. A later implementation using the same label must not silently reinterpret prior membership. Preserve unsuccessful parses without turning them into observations. A changed USD source-evidence document with unchanged INR value remains distinct capture/parse evidence; it need not alter the INR value hash.

Keep this behaviour behind one deep selection module: an interface such as `select_fpi(snapshot, policy) -> FpiSelection`. The result carries current/history membership identities, status and reasons. Live, staged and replay callers use that same interface. A central writer operation in `pipeline/src/db/writer.py` registers complete parse results and qualification events atomically; pure validation runs before persistence. Raw capture storage remains usable when parsing fails. Do not spread endpoint arbitration, timestamp reconciliation or acceptance rules across fetchers and consumers.

### Occurrence order and acceptance are separate

Recommended conservative initial policy, still requiring explicit adoption:

1. For each reporting date, determine eligible accepted occurrences within each endpoint using the saved snapshot. An observation can be known without being accepted. Its reporting date does not establish when it was known.
2. A trusted non-overlapping request sequence on one endpoint may supply a local supersession order: the next request starts after the earlier request completed. This orders our observations, not the source's publication revisions. A newly accepted A after B may therefore point to the same value identity as the old A while being a distinct occurrence.
3. Overlapping requests with conflicting values, unresolved equal ordering, or untrusted imported timing create an explicit conflict. Do not use download completion, insertion order, capture hash or an allocated sequence as an invented source revision. Equal-value responses can corroborate a value while retaining all memberships.
4. Compare accepted per-endpoint states. If Latest and Monthly disagree on the same reporting date, mark that date conflicted until a declared policy or explicit resolution event resolves it. Do not silently assume Monthly is final or Latest is fresher. If a precedence rule is later adopted, version it and record its rationale. It remains a model policy, not a verified release fact.
5. Apply withdrawal/resolution state as present in the decision snapshot. A withdrawal must not automatically resurrect an older value unless the frozen policy explicitly allows that fallback. A fresh acceptance or resolution can reinstate an occurrence without erasing the withdrawal event.
6. Select reporting dates only after resolving per-date occurrence state. A newly downloaded old date must never replace a newer eligible date merely because its capture is newer. Define whether a conflict on the newest observed date makes the whole feature unavailable; recommended initial rule is to make it unavailable rather than silently step back. History exclusions and resulting insufficiency must be explicit.

A date disappearing from a rolling Latest/Monthly page is not proof of withdrawal. Source omission, invalid parsing, a failed request and an explicit qualification withdrawal are different events.

### Visibility, imports and replay

Keep `requested_at`, `retrieved_at`, archive `stored_at`, parse recording time, acceptance recording time and observed decision-read membership separate. None is an NSDL release timestamp. Durable acceptance can follow retrieval by any delay. Do not force it earlier to satisfy the existing constructor.

An old capture imported today may support future decisions after it is qualified and observed in their input snapshot. It cannot establish that yesterday's process knew it. It also must not win over an already accepted newer occurrence merely because import completed later. Preserve original claimed capture order and import evidence, and require an explicit source-order resolution when trust or order is insufficient. Never backdate qualification from the reporting date.

Correction following the parent's direct inspection of the private receipt keys and timestamps: both original receipts contain `started_at`. The earlier statement that they lacked request-start evidence was incorrect and is withdrawn. This reviewer did not inspect the private files. The parent verified these intervals:

| Receipt | Original start (UTC) | Original completion (UTC) |
|---|---|---|
| `latest-direct.receipt.json` | `2026-09-27T12:32:48.7205078Z` | `2026-09-27T12:32:50.1044666Z` |
| `monthly-direct.receipt.json` | `2026-09-27T12:32:31.1566957Z` | `2026-09-27T12:32:32.0884114Z` |

These seven-digit fractional seconds require conservative interval-preserving normalization for the six-digit capture timestamps: floor the start and ceil completion, while retaining the original receipt and its hash. Latest therefore becomes `[12:32:48.720507, 12:32:50.104467]` UTC and Monthly becomes `[12:32:31.156695, 12:32:32.088412]` UTC on the same date. These are enclosing intervals, not claims that the original timestamps had exactly six-digit precision. Test both conversion directions, including carry into the next second/day. The receipt metadata remains a research-capture assertion; it does not establish historical durable visibility, qualification, source release order or source finality.

For any other imported evidence that actually lacks request start, the new capture envelope's `requested_at` must not be invented or copied from `retrieved_at`. Preserve such files and receipt hashes under a separately typed import-evidence contract with unknown request start, or leave them outside the transport table until that contract exists. A fresh download supplies a new request interval; it cannot repair a missing historical interval. Add a conditional missing-metadata test that refuses fabricated request-start data and does not infer non-overlapping occurrence order from incomplete evidence.

For exact replay, use the immutable evidence snapshot attached to the original decision. Later imports, parser corrections and withdrawals do not alter that snapshot or published call. A corrected retrospective analysis creates a new research version and labels its knowledge/qualification basis. It is not the original live decision.

For a requested historical cutoff without a saved snapshot or independently established visibility evidence, report `VISIBILITY_UNPROVEN` (proposed status) rather than manufacture membership from `stored_at`. The system may also offer explicitly labelled counterfactual research using later-known data; such output cannot count as historical point-in-time acceptance.

An implementation may record a trusted post-commit read witness as a conservative upper bound on when a record was observed visible. A wall-clock field written before its own transaction commits remains insufficient. If the witness is persisted later, do not assume a consumer saw that witness earlier. The minimum safe implementation uses exact committed evidence seen by each decision, not a recursive attempt to turn every transaction timestamp into a global availability clock. A monotonic stream can simplify replay only if its commit visibility and publication rules are separately proved; sequence allocation alone is not that proof.

The transaction-gap acceptance test must use an actual paused writer transaction and a concurrent reader during implementation. It is not covered by the present 86 pure tests.

### Concurrent captures and retry identity

Registering identical capture/parse membership concurrently must yield one retained result and stable receipts. Distinct captures with the same bytes retain distinct occurrence memberships. Distinct captures with conflicting values never use winner-of-insert order as source truth.

Qualification transitions for the same target need an expected prior event token or equivalent serialization rule. Two contradictory transitions from the same predecessor must not both become an unqualified current state. The losing transition returns an explicit conflict and must be reconciled before retry. A retry with the same event identity and contents is idempotent; changed contents under that identity are rejected. Transaction rollback leaves no accepted partial parse set or half-recorded selection input.

## Exact next implementation tests

Implement the value/membership/qualification records and pure selection tests before integrating acquisition or model use. Required assertions:

1. **A → B → A:** three sequential qualified capture memberships select A, B and A at their respective snapshots. First and third memberships have the same value hash and different capture IDs. All input permutations agree. A retry adds no membership or new first-seen claim.
2. **Visibility after retrieval:** a capture at 12:00, parse at 12:03 and qualification only visible in a 12:05 snapshot is absent from the 12:01 snapshot and present only after qualification. No timestamp is rewritten earlier. Reuse the current numeric fixture to isolate timing.
3. **Commit gap:** hold the archive/qualification transaction open after assigning internal timestamps; the concurrent decision reader excludes it. After commit, a new snapshot includes it. Replay of the earlier snapshot still excludes it. Repeat with concurrent transactions committing in the reverse of allocated ID order.
4. **Late import:** import an old capture after a saved decision. That decision's replay is byte-for-byte unchanged. A future decision may use it after qualification, but the import cannot automatically supersede a causally newer accepted occurrence.
5. **Out-of-order responses:** request R1 starts, request R2 starts, R2 completes with B, then R1 completes with A. Different writer arrival orders produce the same unresolved-conflict result under the proposed conservative policy. A third non-overlapping accepted response or explicit resolution event supplies the declared resolution, without claiming source finality.
6. **Endpoint disagreement:** Latest A and Monthly B remain a conflict regardless of arrival time and input permutation. Agreement on A can corroborate it; any priority policy produces a different policy hash and recorded reason. If the latest reporting date conflicts, assert the chosen no-silent-fallback rule.
7. **Parser implementation change:** parse one retained capture with P1 and P2; both results remain, including failures. Before P2 is qualified the decision uses P1 or is unavailable according to policy. After qualification it can use P2; the previous decision stays unchanged. Reusing P1's identity for different output fails.
8. **Withdrawal scope:** withdraw one membership while retaining another capture of the same value. Verify exact target scope, no implicit resurrection, explicit reinstatement, and unchanged prior replay. A value-wide withdrawal and parser-wide withdrawal exercise their declared scope separately.
9. **Whole-result atomicity:** Monthly with several dates either registers its complete validated parse-result set or none. Failure in one membership must not create a partially accepted page. Parse failures preserve raw capture evidence and never become zero values.
10. **Concurrent retry and transition conflicts:** duplicate registration returns one identity; distinct captures remain distinct; contradictory qualification events with the same prior token produce one accepted transition plus an explicit conflict. Interrupted responses are reconciled using the same identity before retry.
11. **Frozen policy and consumer parity:** live, staged and replay given the same snapshot/policy yield identical value hashes, membership IDs, histories and exclusion reasons. Change history age, source priority, parser allow list, withdrawal fallback or feature version and assert a different policy hash. No current observation enters its own history.
12. **Unproven replay and missingness:** a bare timestamp cutoff without visibility evidence returns unavailable; failed, partial, stale, conflicted and withdrawn observations never become measured zero. Removing a required historical date changes coverage and can make history insufficient.

The bounded next packet is the append-only normalized membership and qualification contract plus its pure selector tests, followed by a real transaction-visibility verifier. Do not connect the legacy first-seen selector directly to the raw archive or claim that the raw-capture acceptance gate closes FPI readiness.
