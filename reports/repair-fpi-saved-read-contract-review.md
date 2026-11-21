# Saved-read contract review — leaf29.1

28 September2026. Deliverable: `docs/FPI_SAVED_READ_CONTRACT.md`. G1 is a self-reviewed design outcome; G2 remains pending independent parent acceptance. No saved-read RPC, schema, codec, execution authority or consumer is implemented by this leaf.

## Decision

The next layer retains administrative evidence under `fpi-admin-read-v1`. Every complete or failed read permanently carries UNVERIFIED execution/acquisition state, eligible=false and feature=null. This allows actual SQL snapshot/retry and immutable-loader work to proceed without inventing missing release/verification tables. It cannot activate FPI. A later eligible decision must use a new versioned snapshot containing the actual trust state observed at that read; current trust cannot promote an old administrative manifest.

The contract freezes policy, request, receipt and manifest fields and hashes; scoped membership plus global newest-date sentinel; complete original Monthly support without recursive candidate expansion; failure diagnostic scope; explicit heads/absence and original resolution witnesses; bounded one-statement materialization; failure/retry persistence; original-document loading; and schema/codec/central-writer responsibilities. New migrations begin at14 or later because13 is reserved for timeout repair.

## Evidence inspected

Source revision is HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`, shared branch `codex/frontend` with existing uncommitted repair work. The lease covers only the contract, this report and this leaf's G1 evidence. Other work was neither rewritten nor staged.

Read directly: IDENTITY; the repair amendment in MASTERPLAN; TASK; AGENTS; OMEGA_PROTOCOL; Humanscope; Unlazy; the quality-first orchestration policy; the earlier decision-storage proposal and execution-trust design; qualification storage/order contracts; complete read-reference contract; migrations10/11/12; actual capture/parse-reference/qualification-v2 and old selection code. A narrow memory lookup supplied earlier FPI cautions, then current source verified them. No relevant memory assertion substitutes for current schema inspection.

Actual schema findings:

- Migration10 retains source receipt data and capture stored_at. stored_at is outside the capture content hash and is not a commit timestamp.
- Migration11 retains whole parse documents and atomic memberships. Membership rows lack parser_sha256; it must be joined from the parse. Failed parses have no membership date and need a separately declared diagnostic rule. Its artifact kinds are PARSER/SELECTOR, with5MB bodies; no runtime approval is implied.
- Migration12 uses sequence-backed ordinals under one qualification advisory lock. Current heads have a target/order index and witness events retain complete canonical commands. The old proposal's maximum-plus-one allocator and alternate hashes are superseded.
- `build_fpi_read_references` validates a unique capture once and each whole parse once, preserving all membership/source-evidence IDs. It has no stored_at or artifact references; the new manifest adds separately checked projections.
- `FpiQualificationView` can represent exactly scoped candidate members plus compact current/witness events. All basis members are on the fully included candidate date, so there is no reason to recursively expand Monthly support into more qualification heads.
- There is no saved-read/policy or execution trust schema. Existing indexes need the specified failure stored_at/capture partial indexes and date/member index for bounded reads. No migration was edited here.

## Self-adversarial review

Four passes covered the complete draft, source/schema reconciliation, adversarial failure/visibility/resource cases and a final consistency/format read. These are manual design checks, not runtime proof.

| Attack or ambiguity | Resolution retained in the contract |
|---|---|
| ACCEPT or a retained selector hash becomes runtime authority | Immutable UNVERIFIED/eligible=false, no feature or v1 adapter; future trust requires a new snapshot/version |
| Reader only stores allowed/qualified winners | SQL discovers all scoped memberships, irrespective of parser, endpoint, qualification and equality |
| One Monthly result expands scope indefinitely | Complete support remains separate; only scope-date members become candidates; no support-date closure |
| Failed parse disappears because its stored_at is in the future after clock rollback | Indexed global future-failure probe retains CLOCK_INCONSISTENT; old late commits obey the explicit7-day/candidate-capture diagnostic rule |
| Outer statement clock sampled before a lock wait changes age scope | One private clock_timestamp sample in MATERIALIZED inner statement CTE after lock/retry; SR24 crosses a day boundary with real visibility evidence |
| CASE appears to guard a costly aggregate but evaluates too late | Guard the aggregate's input relation; scratch fail-if-called decoder, positive control and plan review are required |
| DISTINCT/UNION scans the entire failure archive before LIMIT | Probe each internally unique branch at2049; an oversized branch proves union overflow; otherwise deduplicate at most6144 IDs |
| Ordinal or timestamp sorting reconstructs a different historical resolution | Preserve complete v2 head/witness documents and ordinal rules, not inferred clocks or full-chain replay |
| Every candidate's shared capture is restored repeatedly | One bulk complete-reference builder call; instrument one validation per unique original, not per candidate/parse pair |
| Loader receives truncated API pages | ID batches/keyset maximum256, exact returned-set checks, missing/extra/duplicate rejection; immutable originals only |
| Overflow is reported after a timeout rolled back insertion | Distinguish measured persisted overflow from cancellation with no saved row; reconcile identical identity |
| Guard ordering promised clock precedence before metadata exists | Explicit staged first-failure hierarchy. Candidate overflow wins over uninspected candidate time; preliminary date-head byte overflow precedes possible event count overflow |
| Early witness extraction exhausts resources before full event guard | Preflight current date-head text against the qualification byte budget; only then decode bounded witnesses and complete event closure |
| Timezone/year bounds wrap or create year0 | Saturating disclosed lower bounds; canonical UTC/India representability; invalid server clock aborts, invalid referenced conversion records clock failure |
| Captured integrity hashes are treated as database-origin authentication | Pure consistency and authenticated retained storage remain separate claims |

The parent identified the staged-precedence ambiguity during drafting; it is corrected in the final contract. The parent also supplied PostgreSQL17 documentation and reports of real local clock/CASE controls. Those support the design constraints. This leaf did not run those database controls and does not count them as implementation acceptance. The actual saved-read RPC and its race/resource checks remain unimplemented.

## Checks run by this leaf

Four canonical JSON golden vectors were constructed independently with Python's sorted compact ASCII encoder and SHA256, then extracted from the saved Markdown and hashed using .NET SHA256. Both paths agree:

| Vector | ASCII bytes | SHA256 |
|---|---:|---|
| Policy |820 |005430dfbdde7fb1aacd83d75a8763fe931dbbd7de220a07be14a27dbaac5f87 |
| Request/read_id |433 |a4130c1ce37873b7b580e0e15d02cf0fd0bdbad3c656bba6b248779b8436ad27 |
| Empty references |62 |5043b6cf68a2600dc6ae8f6af32a222a8cfa63a2774f61ec2833060024a81e58 |
| Empty qualification |75 |4512d5d55af1633da699dbf2578900e14377e99a1acb26d2b6095fd667c5de19 |

Observed success marker: `FPI_SAVED_READ_GOLDEN_VECTORS_VERIFIED`. These prove document byte/hash examples only. Repeated-digit identities are explicitly synthetic codec examples, not proof of retained dependencies. Valid-original complete/failure manifest vectors and SQL comparison remain required implementation tests.

`gate-lint.mjs .unlazy/repair/gates/leaf-29.1.md` passed with three expected warnings: both G1/G2 are manual and the ledger has no runnable gate. That is appropriate for a design review, but does not turn prose acceptance into a database test. The contract specifies SR01–SR26 executable scenarios, including real barriers, overflow boundary controls and independent wrong-output tests, for the later implementation packet.

Process/service inspection found no matching Docker/Hermes/PostgreSQL processes in the Windows process query, and `com.docker.service` was Stopped. This scoped document work needed no runtime. No Docker, database or Hermes service was started, stopped or reconfigured by this leaf; Windows process absence is not a claim about every WSL/remote process. Hermes MCP configuration was unchanged. No network/provider/credential access, Git commit, deployment, code/schema edit or runtime test occurred. Python/.NET were used only for local document hashes.

## Handoff

G1 is met for the bounded implementation contract and its self-adversarial evidence. G2 remains pending parent review: one met, one unmet, zero abandoned. The lease is not released by this worker. Parent acceptance can call this contract accepted locally; it cannot call saved-read behavior implemented, FPI active or the wider repair complete.

The implementation split is explicit: pure codecs and identity tests; migration14+ and real SQL verifier; central writer/immutable loader and adversarial tests; then parent integration and source-to-runtime trust work under separately frozen contracts. Full pipeline/lint/type and consumer/release evidence must be measured for that implementation. Prior packet test totals are not rerun or claimed by this documentation leaf.
