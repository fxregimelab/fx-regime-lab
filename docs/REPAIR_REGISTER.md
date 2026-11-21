# FX Regime Lab repair register

## Qualification ordering: current evidence

Packets30/31 are locally accepted. The saved-read codec, original-report oracle, database layer and central writer/loader pass independent checks: 86 focused codec cases, 115 focused writer cases, all 19 original memberships, nine support-only records in the narrowed read, four changed-transport refusals, old-read replay after qualification change and a saved failure that queried no originals. The SQL parent rerun covers 65 read/retry checks, 51 expected refusals, all 11 reduced limits, transaction/cancellation controls and 58 originals validated once each. The six remaining write-entry timeout boundaries also pass real cancellation/rollback and a removed-guard control. The full pipeline receipt after writer edits passes with 2,036 collected tests. Aggregate: 199 met, six root unmet, zero abandoned; among 45 register items, five are VERIFIED LOCAL, 22 IN PROGRESS and 18 OPEN. PostgreSQL stopped after zero scratch databases/other clients. Protected execution, authenticated acquisition, deployed request setup and actual consumers still prevent closing FPI-T07 or authorizing a feature. Details: reports/REPAIR_CHECKPOINT.md.

Packet30 SQL review also reproduced excessive validation cost from repeated UTF-8 text-prefix scanning: 100 KB took 16.4 seconds in the isolated scanner control, compared with 7.3 milliseconds using byte offsets. The optimized scanner and actual large-original database cases now pass. A separate wrong-scope mutation was rejected by the exact candidate-set oracle, with unchanged positive controls before and after. Evidence and snapshot hashes are in reports/REPAIR_CHECKPOINT.md; these controls establish the administrative read layer, not trusted feature activation.

Packet 29 adds verified local timeout controls to FPI capture/artifact/parse storage and accepts docs/FPI_SAVED_READ_CONTRACT.md for implementation. Seven real database groups and an independent guard-removal control pass. Four contract vectors are checked; its 26 implementation scenarios remain unimplemented requirements. Aggregate: 187 met, six root unmet, zero abandoned. Runtime stopped; no deployment. Details: reports/repair-fpi-storage-timeouts-integration.md. Saved reads, protected execution, actual consumers and the broader register remain open.

Packet28 completes compact retained-reference construction, with all 19 original-report memberships independently checked and wrong-output controls rejected. Full pipeline passes (1835 independently collected); Ruff/MyPy226 pass. Aggregate:183 met, six root unmet, zero abandoned. This is a loader primitive; complete saved database scope, execution trust and actual consumers remain open. Details: reports/repair-fpi-read-references-integration.md.

FPI-T07 has verified local pure ordering (packet25) and durable qualification ordering (packet27). Complete saved decision reads and consumer integration remain open. Tied/decreasing clocks, scope transitions and real transaction concurrency are independently verified. The original reproduced defect was that tied timestamps across qualification scopes do not establish event order. Parent reproduced a valid accepted-member/date-resolution snapshot, then appended a membership withdrawal with the exact same timestamp as the resolution. The pure constructor rejected the later snapshot because it sorts non-date state before date resolution at that clock, losing the actual cross-scope sequence. This is conservative rejection, not silent acceptance, but it cannot represent every legitimate transaction history. The durable qualification design must provide proven event ordering or exact referenced state; caller timestamps must not become that proof. Marker: FPI_TIED_SCOPE_ORDER_GAP_REPRODUCED. Packet24 parse/artifact storage does not itself resolve this next-layer requirement.

Owner request: 27 September 2026. Base revision: `9fa150538d08ab5a2a6c587976552944f47a724d`. Working branch: `codex/frontend` (same base; shared checkout branch changed during work).

The active goal covers implementation, economic definitions, research validity, data provenance, security and operations. Completion requires evidence for each item below, not a green test count alone. New defects found during repair join this register. No claim of guaranteed profitability or permanent absence of bugs is possible.

Status vocabulary: OPEN, IN PROGRESS, VERIFIED LOCAL, VERIFIED RELEASE, EXTERNAL EVIDENCE REQUIRED. Local fixes do not repair previously published records. Original calls and evaluations must remain available; corrections need explicit versions and links to their predecessors.

## Order of work and acceptance

1. Freeze the prediction and measurement contracts; repair validation before judging a strategy.
2. Repair source timing, pair orientation and economic definitions; replay one deterministic calculation through every supported path.
3. Rebuild research around testable hypotheses, simple baselines and time-ordered evaluation. A failed hypothesis is an acceptable research result and must not be concealed by tuning.
4. Reconcile the public pages, database safeguards, deployed scheduler and monitoring with the same contracts.
5. Run the complete checks, migration rehearsals and independent review; prepare versioned historical reconciliation and release evidence.

The three-pair restriction and research-platform identity remain in force. No threshold optimization may bypass the existing live-history gates. Required live observation windows cannot be manufactured from historical replays.

| ID | Problem and concrete repair | Acceptance evidence | Status |
|---|---|---|---|
| V01 | Validation fetch omits published direction and falls back to rate component. Require exact published direction and call identity. | Opposing component/final-direction fixture scores final call; missing direction remains unscored. | VERIFIED LOCAL |
| V02 | Costs and shorts use inconsistent definitions. Preserve underlying return; calculate signed research payoff minus positive cost separately. | Mirrored long/short, flat, deadband and cost-boundary cases; documented distinction between accuracy and net-positive payoff. | IN PROGRESS |
| V03 | Later horizon writes can discard earlier net fields. Preserve the entire earlier evaluation. | T+5 then T+20 and repeated-run regression. | VERIFIED LOCAL |
| V04 | Pending horizons, blank directions and missing net outcomes enter denominators. Use explicit eligible cohorts per metric. | Mixed mature/pending/abstained/unknown/missing-cost fixtures with exact counts. | IN PROGRESS |
| V05 | Calibration independently filters probabilities and outcomes; neutral backfill scoring differs from live. One event definition and shared calculator. | Identical live/replay results; paired observations; invalid probability rejected. | IN PROGRESS |
| V06 | Sharpe and drawdown use raw FX returns and overlapping calls. Remove unsupported portfolio statistics; keep clearly labeled per-call descriptive returns. | Two correct short calls cannot appear as losing research payoffs; no equity claim without exposure accounting. | IN PROGRESS |
| V07 | Historical/live sources and model versions mix. Add explicit provenance and evaluation version to queries and corrections. | Cohort cannot silently include another source/version; legacy unknown remains labeled. | IN PROGRESS |
| V08 | Horizon dates, source bars and entry time may not be tradable after publication. Define availability, market calendars, delayed bars and maturity. | Publication/bar timestamp fixtures, holidays and missing prices; no pre-publication entry. | IN PROGRESS |
| D01 | Rate legs have different tenors/frequencies but are called a 2Y spread. Use matched instruments or honestly named disabled/proxy features. | Source metadata and unit/tenor checks for every pair. | IN PROGRESS |
| D02 | US inflation adjustment is called a cross-country real-rate differential. Supply both compatible expectations or remove that claim. | Formula, units and source availability verified. | IN PROGRESS |
| D03 | Rate freshness inherits spot date; scalar fetches discard source dates. Preserve observation, release, retrieval and vintage metadata. | Stale rate with fresh spot fails rate freshness. | IN PROGRESS |
| D04 | COT current-year fetch truncates required history. Join years, deduplicate and validate report count. | January/year-boundary fixtures satisfy the actual rolling lookback. | IN PROGRESS |
| D05 | Historical COT is available on report Tuesday instead of publication Friday. Use actual releases and holiday exceptions. | No report accessible before publication timestamp. | OPEN |
| D06 | FRED historical series use revised values and observation dates as availability. Add vintage/release-aware replay or label reconstruction unfit for OOS claims. | Point-in-time fixture; unavailable vintages cannot earn OOS status. | OPEN |
| D07 | IV, risk reversal and intervention inputs are absent/proxies despite stronger claims. Publish feature availability, missingness and fallback reasons. | Missing data cannot become fabricated history or a measured signal. | OPEN |
| S01 | Mixed USD/currency/pair orientation. Adopt positive = rising quoted pair, with economic provenance for every signed feature. | EUR rates/special, JPY COT, INR FPI sign fixtures and counterexamples. | IN PROGRESS |
| S02 | Volatility, open interest and intervention risk enter as arbitrary signed direction. Separate direction evidence from risk/state conditioning. | Documented estimand and ablation for each retained directional use. | IN PROGRESS |
| S03 | Positive composite gets higher conviction than equivalent negative composite. Make magnitude symmetric unless a separately evidenced pair asymmetry applies. | Mirrored inputs give mirrored direction and equal conviction/gates. | VERIFIED LOCAL |
| S04 | Dynamic weights use absolute contemporaneous correlations as precision, omit factors and claim covariance control. Disable unsupported adaptation; evaluate forward relationships only in training windows. | No negative relationship becomes positive evidence; no test-window fitting; all factor weights traceable. | IN PROGRESS |
| S05 | Confidence is a heuristic called calibrated probability. Label score honestly; fit calibration only with eligible training data and validate out of time. | Calibration manifest and held-out reliability/Brier versus baselines, or probability unavailable. | OPEN |
| S06 | Pair mechanisms, descriptive regimes and forecast targets are conflated. Define separate falsifiable hypotheses for EUR, JPY and managed INR. | Driver/state/target/horizon/expected sign/limits table; explicit unsupported mechanisms. | IN PROGRESS |
| P01 | Staged pipeline repeats one observation into fake history and drops features. Feed real snapshots or reject insufficient history. | Legacy/staged/replay parity on frozen snapshots and deliberate missing-history failures. | IN PROGRESS |
| P02 | Historical simulator uses yield level instead of spread, altered factors and incomplete state. Share production feature calculation. | End-to-end replay equivalence, with provenance differences surfaced. | IN PROGRESS |
| P03 | Diagnostics bypass layers and fit over evaluation windows. Evaluate final published rule with train-only state and dependence-aware resampling. | Time-boundary leakage tests and reproducible diagnostics manifest. | OPEN |
| R01 | Unsupported accuracy gains and completion claims appear in plans. Replace predictions of improvement with hypotheses and measured receipts. | Every numerical claim has cohort, revision, method and evidence. | OPEN |
| R02 | SSRN/methodology claims exceed actual inputs and OOS evidence. Reconcile documentation with executable definitions. | Source-to-claim inventory; unverified claims withdrawn or qualified. | OPEN |
| R03 | Small overlapping samples and 55% gate are treated as proof of skill. Keep identity gate but add uncertainty, dependence, coverage and baseline comparisons. | Non-overlapping sensitivity, block uncertainty and minimum evidence policy. | OPEN |
| R04 | Research selection, calibration and tuning lack a frozen evaluation protocol. Register hypotheses, baselines, splits, purge/embargo and untouched holdout before experiments. | Reproducible manifest with hashes, seeds, trial count and train-only selection. | OPEN |
| R05 | Accuracy alone hides abstention, imbalance and weak economics. Report coverage, counts, pair/regime breakdown, proper scores and matched cost cohorts. | Metric dictionary and one reproducible report from frozen eligible observations. | IN PROGRESS |
| R06 | Existing unmerged repair report misstates Brier floor and cannot reconcile score changes. Correct mathematics; reconcile record-by-record differences before reuse. | Hand-computable counterexample and exact old/new cohort bridge. | OPEN |
| U01 | Public stats ignore source choice, use date heuristics and cap shared rows at 200. Query explicit provenance with complete pagination and consistent counts. | UI/API fixtures across >200 observations and mixed versions/sources. | IN PROGRESS |
| U02 | Public correctness labels and net/gross cohorts conflict; neutral handling differs. Consume canonical evaluation fields and name each denominator. | Same fixture yields same row, headline, per-pair and rolling values. | IN PROGRESS |
| U03 | Cumulative raw overlapping returns are called strategy performance. Remove misleading equity/drawdown presentation. | No unsupported portfolio return visible. | IN PROGRESS |
| U04 | Audit UI infers stages and fabricates DQS/health. Display recorded stages, unknown state and actual expected sessions. | Failed/missing/stale/holiday cases never show verified integrity without evidence. | OPEN |
| O01 | Prefect entrypoint bypasses wrapper validation/aggregation/health responsibilities and staged flags. Establish one supported scheduled flow. | Entrypoint integration test invokes required stages in order with real failure propagation. | VERIFIED LOCAL |
| O02 | Validation errors are swallowed and success follows data quality. Separate ingestion/inference/publication/validation/aggregation statuses. | Injected stage failures produce failed/partial status and actionable diagnostics. | IN PROGRESS |
| L01 | Backfill disables protections and deletes pair history without safe recovery. Replace with append-only versioned replay; remove dangerous default path. | Failure injection cannot disable protections or delete original calls/evaluations. | IN PROGRESS |
| L02 | Supersession and insert are nonatomic. Make publication atomic and idempotent through writer boundary. | Concurrent/retried publication and interrupted transaction tests. | IN PROGRESS |
| L03 | Old triggers reference dropped fields; horizon schema differs from writers. Add forward corrective migrations after downstream audit. | Fresh database and upgrade-from-baseline rehearsal; immutability and FK tests. | IN PROGRESS |
| L04 | PostgreSQL connections disable certificate verification. Verify TLS and use scoped credentials where supported. | Invalid certificate rejected; deployment configuration requirements documented. | OPEN |
| A01 | Anonymous AI API spends server credentials outside central AI boundary. Remove or authenticate/rate-limit central mediated capability. | Anonymous request cannot trigger paid AI; no browser exposure of credentials. | VERIFIED LOCAL |
| A02 | Security-definer RPC privileges may permit public writes. Audit grants/search_path and restrict execution. | Anonymous/authenticated/service role permission tests in local DB. | OPEN |
| A03 | Dependencies, secrets and deployment configuration need current review. Audit lockfiles, known advisories and access boundaries. | Reproducible dependency findings, resolved exploitable paths and remaining constraints. | OPEN |
| X01 | Historical repair needs immutable original-to-corrected reconciliation. Build read-only export, checksums and versioned correction proposal. | Every changed result explained; no silent rewrite; complete provenance. | OPEN |
| X02 | Release and observation evidence remains separate from local checks. Prepare release/rollback, verify deployed schema/entrypoint/UI and required live windows. | Actual release receipts and observed health; no simulated live acceptance. | OPEN |

## Baseline and current work

The initial audit ran the existing pipeline suite: 319 tests passed. That suite did not detect the documented scoring, source-timing or theory defects. The remote branch `origin/Shreyash3007/fix/audit-staged-v2-fixes` contains partial repairs and additional analytical/cost issues; it is reference material, not an accepted repair.

The first local packet covers parts of V01–V06, V08 and S03. See [the repair checkpoint](../reports/REPAIR_CHECKPOINT.md) for changed behavior, executed checks and the exact next work. The full pipeline suite passed 370 tests; a further cross-module regression passed separately. No issue has release acceptance yet. Docker and heavyweight Hermes services were not needed for these checks. Database acceptance requires a real local database rehearsal.

Newly exposed details remain within the existing work: V03/O02 includes the latest-30-call validation backlog limit; U04/A03 includes the build's missing `metadataBase` warning and npm peer/runtime mismatches. None is silently waived.

## Completion record requirements

Each closed item must link changed files, regression tests, executed commands/results and any deployment or research evidence. A test that merely repeats implementation arithmetic is insufficient: include cases that previously produced a wrong user-visible conclusion. Report external evidence gaps explicitly. Do not mark the goal complete while a required item is unresolved.

## Second repair packet

Staged validation now reads persisted published calls and shares the canonical calculator. Anonymous server-funded AI sharing is removed. Validation persistence now uses a versioned transaction, with rollback and concurrent-write evidence from real local PostgreSQL. See `reports/repair-staged-validation.md`, `reports/repair-public-ai.md` and `reports/repair-validation-persistence.md`. These are local checks. Full migration history, source/model cohorts, public UI integration, live observation and research performance remain open.

## Third repair packet

Source/model/evaluation groups are now separated in storage and queries; public metrics paginate the complete matching evaluation ledger. Unsupported equity, Sharpe and drawdown displays are removed from the track-record path. Python and frontend fixtures agree on eligible counts, costs and signed payoff. The actual aggregate writer payload passed real PostgreSQL rehearsal, including rolling-window columns missing from earlier migrations. See `reports/repair-cohort-queries.md`, `reports/repair-cohort-aggregation.md` and `reports/repair-performance-presentation.md`.

R05/U01/U02 remain open beyond local implementation: evaluation-only readers omit published calls with no validation row, so full publication coverage is unavailable until a call-ID join reconciles that universe. Public wording must disclose that limit. V08 still lacks timestamp/holiday proof; V07 still needs provenance audit and historical reconciliation. Passing tests do not establish forecasting skill.

## Fourth repair packet

The missing-evaluation denominator defect is repaired locally: a read-only view begins from every persisted call and joins current scoring by call ID. Missing evaluations stay visible and cannot borrow another call's result. Old and new snapshot populations have separate versions. Python/public reporting agrees, and real PostgreSQL checks cover gaps, duplicate date/pair identities, snapshot preservation and row security. See `reports/repair-published-population.md`. This supersedes the third-packet statement that published calls without evaluations are absent. Expected-session completeness, source timing/provenance and release acceptance remain open.

## Fifth repair packet

Validation now traverses complete call history and resolves current evaluations by durable call ID across legacy, replay and staged paths. The original engine processed only 30 of a 41-call fixture; the repaired engine processed all 41. Completed due horizons do not refetch prices or rewrite outcomes. See [backlog/identity evidence](../reports/repair-validation-backlog.md) and [staged identity evidence](../reports/repair-staged-call-identity.md).

V01 and V03 now have local acceptance: published-direction fixtures run across supported validation paths, and current call identity/earlier-horizon preservation passed targeted and full regression checks, in addition to the earlier real SQL rollback/concurrency rehearsal. This is not historical reconciliation or release acceptance. P01 retains the 120-day staged source-history limitation. O02 retains scheduler success-after-validation-failure behavior and needs resumable operational batching for large histories.

## Sixth repair packet

Current configured overnight/ten-year substitutes no longer enter the two-year feature. EURUSD nominal context now uses EUR minus USD. Bilateral real-rate features require both countries' inflation inputs; missing structural data no longer inherits tactical scores. Untagged rate history is excluded, and staged inference no longer invents history by repeating current values. See [rate definition evidence](../reports/repair-rate-inputs.md) and the simulation counterpart. D01/D02/S01/S02/P01 stay IN PROGRESS: matched source acquisition, timing/vintage persistence, complete history and public/release claims still need acceptance.

Additional sixth-packet findings remain tracked: staged SignalStage degradation is lost when PublishStage returns OK, and the staged flow does not persist its signal row (P01/O02/U04). The normal writer now preserves quality notes, but that alone does not repair staged publication health or notification semantics.

## Seventh repair packet

Staged publication now writes its computed signal row, checks call identity/receipt and retains upstream degradation. FAILED input stages stop publication, validation failures stop the staged heartbeat, and skipped validation remains DEGRADED. Failure notifications preserve the original exception. The current fixtures cannot emit healthy notices while genuine rate history is missing. See [publication and flow evidence](../reports/repair-staged-publication-health.md) and [adapter evidence](../reports/repair-staged-status-adapters.md).

The full pipeline regression gate passed with 467 collected tests; focused flow and independently rerun adapter gates passed 45 and 21 tests. Ruff passed, MyPy passed 167 files. This supersedes the sixth-packet staged persistence finding, but does not close P01/O02/U04 or atomic publication L02. The outer wrapper still ignores staged health, substitutes missing DQS with 1.0, reports seven pairs, and sends an unconditional success heartbeat. Its configured Prefect entrypoint bypasses the wrapper. Those O01/O02 defects are the next bounded repair, not accepted behavior.

## Eighth repair packet

The checked-in Prefect deployment now invokes the full scheduled wrapper. Both live paths provide typed execution evidence; required validation failure reaches the scheduler. The wrapper preserves staged degradation, retains missing DQS as null, verifies actual pair counts and waits for overnight checks, dated aggregation and the health write before its final notice. Actual Prefect wrapper/staged integration covers degraded completion and aggregation failure after publication. Health storage uses one upsert; duplicate legacy publication is rejected before writing. See [scheduler evidence](../reports/repair-scheduler-health.md), [legacy evidence](../reports/repair-daily-run-contract.md), and the updated [pipeline reference](PIPELINE_REFERENCE.md).

The full pipeline gate passed with 515 collected tests; focused scheduler and independent legacy gates passed 66 and 13 tests. Ruff passed; MyPy passed 170 files. O01 is VERIFIED LOCAL, not deployed. O02/U04 remain IN PROGRESS/OPEN for complete legacy stage receipts, immutable per-attempt history and honest public health readers. The original-source negative control proved that a FAILED output with no quality score previously produced a healthy seven-pair/DQS-1.0 heartbeat.

The next L01/L02 work includes every destructive correction route, not only the main bulk writer: risk-reversal replay disables immutable-call protections, and forced date rollback can delete original calls. No such route was executed. Read-only discovery also found trigger disabling in batch aggregate replay. These remain within L01/L03/A02 scope.


## Ninth repair packet

The local writer and both production publication paths now bind call, full signal evidence and rationale in one RPC. Historical bulk replay appends explicit backtest versions; call-only writes, forced date purge and synthetic-risk-reversal writes reject before I/O. Historical batch statistics delegate to the canonical cohort aggregator. Retrospective explanations cannot overwrite existing rationale. See `docs/PUBLICATION_REPAIR_CONTRACT.md` and the packet reports.

Parent source review exposed a dependent V07/L02/P01 read-path issue: current call queries do not consistently filter live provenance or resolve multiple versions deterministically, and prior-regime queries lack an explicit decision-date cutoff. Public explanations can still read a mutable current signal projection rather than the selected call's immutable evidence. These are next-packet requirements before publication release; storage tests do not close them. L01/L02 remain IN PROGRESS. Full migration history, production reconciliation and research evidence remain open.

Ninth-packet evidence: the full pipeline gate passed with 550 tests collected; Ruff passed and MyPy checked 172 source files. Parent independently reran the writer, staged and historical safety gates (44, 69 and five tests) and twelve real PostgreSQL check groups. Unlazy records 58 met gates, six unmet root requirements and zero abandoned gates. Temporary PostgreSQL was stopped and confirmed stopped. No repair has release acceptance.


## Publication reader integration findings

Packet ten separates current/live displays and prior decision state from the complete validation population. Its reader contract is `docs/PUBLICATION_READER_CONTRACT.md`. Parent review also confirmed a consequential V08/P01 dependency for the next validation packet: `validation.engine.run_validation` still takes entry and horizon spots from mutable `signals` by pair/date. New backtest publications intentionally do not update that projection. An unscored version can therefore borrow another version's entry spot or remain unscored when no live projection exists. Exact call-ID population selection alone does not fix this. Bind each new call's entry evidence explicitly, define shared endpoint price provenance and reconcile legacy/staged/replay behavior without altering already published evaluations. Do not claim publication release readiness until this is repaired and versioned.


## Tenth repair packet acceptance

Current Python and public readers now enforce live/v2/locked-pair selection and deterministic session/version ordering. Prior inference additionally enforces an earlier session and a publication-availability cutoff. Public and AI explanations bind exact call IDs to immutable input snapshots; missing legacy inputs are explicit. The public view excludes private rationale and operational metadata and denies writes. Complete all-cohort validation reads remain intact; their mutable price selection is the separate next repair documented above.

Parent verification: 563 tests collected in the passing full pipeline gate; 64 scoped Python tests; eight public publication and ten validation query tests; four real PostgreSQL view groups; Ruff, MyPy (173 source files), TypeScript, full Biome (202 files) and production build passed. Three new test typing errors found by the parent were repaired and reverified. Unlazy: 64 gates met, six root requirements unmet, zero abandoned. Both worker leases are released, and the task-local database is confirmed stopped. No browser, deployed schema, historical reconciliation or forecasting-skill acceptance is claimed.

## Eleventh repair packet

Validation now binds entry to the exact original publication and stores exact endpoint price evidence under `publication-snapshot-v2`. Legacy, staged and both replay paths share the evaluator. Original v1 evaluations and statistics remain separate; legacy calls without original evidence remain visibly unevaluated. SQL verifies prices, dates, metrics, maturity and immutable completion. Concurrent writes, rollback, permissions and actual Python-to-SQL serialization passed local checks. See `docs/VALIDATION_PRICE_CONTRACT.md` and `reports/repair-validation-price-integration.md`.

V08/P01 remain IN PROGRESS: scheduled ingestion does not yet archive all completed historical closes, provider/session/timestamp evidence is missing from SpotBar, and publication-time tradability and market holidays remain unresolved. Exact missing endpoints stay unavailable. D03/O02 cover acquisition metadata and honest missing-outcome health; L04 still covers other unverified TLS connections although validation batch replay no longer uses one. No release or strategy-skill acceptance is implied.


## Twelfth repair packet

Daily legacy and staged publication now preserve provider observations before publishing. The private archive is append-only and idempotent, retains source/timestamp metadata and rejects malformed payloads. It does not promote unqualified daily bars to canonical closes. Spot histories exclude future dates and conflicting duplicates; production live fetches reject historical request dates. See [the archive contract](PRICE_OBSERVATION_CONTRACT.md) and [the current checkpoint](../reports/REPAIR_CHECKPOINT.md).

Both validation paths now expose the full returned-call denominator, due/completed/missing horizons and malformed calls. Missing mature outcomes remain degraded through scheduled aggregation and durable health recording. Missing, skipped or failed validation cannot produce success; completed degraded scans are recorded without a success heartbeat. These repairs address parts of V08/P01/O02/U04, not the complete source or operations requirements.

Parent re-verification passed all seven packet leaves and the full pipeline gate (694 tests collected). Ruff, MyPy (183 files), frontend TypeScript/Biome/build and eight actual PostgreSQL archive check groups passed. Unlazy records 87 met, six root requirements unmet and zero abandoned. Temporary PostgreSQL is stopped; exact leaf leases are released. No production acceptance is claimed.

Remaining price work includes full sanitized request/response evidence, qualified daily boundaries or a separately constructed timestamped series, completion/revision/holiday rules, and executable post-publication entry evidence for any trade-performance claim. Existing transformed rows cannot establish these facts. V08/P01 remain IN PROGRESS; D03 remains open for rate observation timing. O02/U04 still require immutable attempt history and public health integration. Source acquisition, pair economics, frozen research, historical reconciliation and release/live observation remain required. No register issue is closed merely by this packet's test count.


## Packet thirteen findings and work in progress

Source review found that historical acquisition still upserts unqualified prices into the shared close table and silently drops provenance columns when the schema rejects them. The deep-history helper uses the same path. The old replay wrapper calls the live daily pipeline, so a request for today can publish live output under a historical-replay label. These remain within V08/P01/L01/L02 and are being repaired through archival-only acquisition and an explicit rejection of that unsafe replay boundary. A separate point-in-time replay implementation remains required.

The price request adapters also log raw HTTP exception messages that can include credential-bearing URLs (A03), use a host-local request date (V08), and assign retrieval time during parsing rather than at response/download receipt (D03/V08). Ten regressions reproduced these faults or their missing interface; the request-boundary repair passes its 57-test gate. This is scoped local evidence, not packet-level acceptance while the historical work and primary-source review remain in progress.


## Thirteenth repair packet acceptance

Historical provider acquisition now archives immutable observations and preserves source metadata. The central legacy close writer rejects nonempty writes before I/O; its destructive upsert and field-stripping fallback are removed. The deep-history helper shares the archive path. The old live-orchestrator replay entrypoints reject before I/O for past and current dates. Explicit archive-only acquisition remains available, with strict pair/date validation and error propagation. Qualified reference construction and genuine point-in-time replay remain required under V08/P01/L01/L02.

The price adapters use UTC request dates and explicit response/download receipts. Price and shared-ingestion diagnostic logs omit credential-bearing URL parts and raw exception messages. Scoped checks preserve retries, returned data and cancellation. Other fetcher/library logs, deployed retention and any historical exposure remain in A03. Remaining host-local scheduler default clocks must also be reconciled with the UTC live-fetch guard.

The primary-source acquisition design now requires immutable response pages, complete acquisition snapshots, deterministic fixed-UTC references and append-only acceptance events. Timestamp alone cannot identify a quote event or correction. Vendor finality remains unknown; project acceptance has an explicit version and as-of timestamp. See `reports/repair-price-acquisition-research.md` and the extended price observation contract. This design is not implemented acquisition evidence.

Parent acceptance: 72 historical, 57 request-boundary and 47 shared-logging tests; passing integrated pipeline gate with 741 tests collected; full Ruff and MyPy (186 files). Prior frontend checks remain applicable because this packet did not change frontend code. Unlazy records 95 met gates, six unmet root requirements and zero abandoned. All packet leases are released and its dispatch wave is complete.

The old CLI ignored --help during the worker's initial smoke check and made an unintended public Yahoo download before missing database credentials stopped execution. No database write occurred; the download is excluded from research and acceptance evidence. The repaired help path is now behavior-tested under an acquisition stub. The incident and prevention rule are retained in the checkpoint.

## Fourteenth repair packet acceptance

V08/P01 now have a pure, tested quote capture and daily-reference constructor. Captures bind source bytes and sanitized content to exact request/window/cursor/receipt metadata. Construction validates complete pagination and closed-day acquisition, preserves exact Decimal midpoints and nanoseconds, reports conflicting first/last quotes, and keeps occurrence counts separate from distinct retained rows. All results remain provisional and validation-ineligible; provider finality and empirical coverage are unknown. See [the contract](QUOTE_CAPTURE_CONTRACT.md), [capture report](../reports/repair-quote-capture.md) and [constructor report](../reports/repair-quote-reference.md).

Independent review exposed and fixed cursor/key overlap, timestamp-type loss through normalization, ambient Decimal context dependence and excessive arithmetic resource requirements. The source numeric envelope and completed-day rule are now explicit. Synthetic fixtures establish software behavior; they are not observed prices, accepted provider coverage or a working acquisition/storage pipeline.

Parent gates pass 25 constructor and 107 integrated tests. The full pipeline gate passes with 848 tests collected; Ruff and MyPy (190 source files) pass. Unlazy reports 99 met gates, six unmet root requirements and zero abandoned. Both exact leaf leases are released and the dispatch wave is complete. No frontend/SQL source changed; no provider request, credential read, production write, commit or deployment occurred in packet fourteen.

Required next layers remain durable append-only captures/snapshots, bounded HTTP traversal, immutable acceptance/revision events and evaluation integration. Actual provider availability, day-boundary coverage, holiday policy and corrected historical outcomes still need real evidence. V08/P01 and the remaining unaccepted register issues remain open or in progress; no issue is closed solely by the new test count.

## Fifteenth repair packet acceptance

V08/P01 now include locally verified durable quote captures, provisional snapshots and ordered membership. The central writer preserves exact input fingerprints and checks exact receipts. Private SQL RPCs enforce schema, lineage, size and privilege contracts. Identical and concurrent retries are stable; injected membership failure rolls back the complete snapshot transaction. No promotion into historical_prices or evaluation records exists. See [the storage contract](QUOTE_STORAGE_CONTRACT.md), [SQL proof](../reports/repair-quote-storage-db.md) and [writer report](../reports/repair-quote-storage-writer.md).

Actual integration found PostgreSQL text/JSON incompatibilities for NUL/lone-surrogate source strings and keys. Explicit sanitation, collision rejection and text_storage_escaped diagnosis preserve numeric values and original byte identity without calling transformed strings lossless or qualified. Binary UTF-8 verifier pipes repaired Windows newline conversion; exact hash validation was retained. These are now exercised in actual database checks.

Parent re-verification passed 148 integrated Python tests and six real PostgreSQL groups, including 10,000 ordered memberships, direct-write/COPY denial, private helpers/RLS, owner mutation refusal and fresh/populated reapplication with preserved original-table sentinels. Full pipeline gate passes with 889 tests collected; Ruff and MyPy (191 files) pass. Unlazy records 105 met, six root unmet, zero abandoned. Exact leases released; dispatch complete. Temporary PostgreSQL was stopped after zero scratch databases/concurrent clients were confirmed.

V08/P01 remain IN PROGRESS. Bounded provider acquisition, zero-response attempt evidence, actual runtime provenance, acceptance/revision policy, qualified prices and versioned evaluation/reconciliation remain required. The local storage proof does not establish the complete migration chain, production permissions, provider access, research skill or release acceptance. No provider call, production write, commit or deployment occurred in this packet.

## Sixteenth repair packet acceptance

V08/P01 now include bounded quote acquisition with durable started/page_saved/finished events, including zero-response failures. SQL binds immutable identity, predecessor hashes, temporal ordering, observed byte budgets and the exact acknowledged snapshot. HTTP uses fixed-host pagination, verified receipts, source/dependency manifests, explicit limits and cancellation-safe cleanup. These are private provisional retrieval records; they do not qualify a price or establish provider finality. See [the contract](QUOTE_ACQUISITION_CONTRACT.md), [HTTP report](../reports/repair-quote-acquisition.md), [SQL proof](../reports/repair-quote-acquisition-db.md) and [writer report](../reports/repair-quote-attempt-writer.md).

Parent review found and fixed temporal lineage and byte-budget gaps, timeout misclassification, receipt/source timing defects, uncertain persistence handling and cancellation/clock-cleanup defects. Independent gates passed 39 transport tests and 110 attempt/storage-writer tests. The real PostgreSQL verifier passed 174 malformed/inconsistent rejection cases, concurrency, rollback, permissions, reapplication and full synthetic HTTP-to-writer-to-SQL ordering. Full pipeline gate passes with 1003 tests collected; Ruff and MyPy195 pass. GitNexus reported critical aggregate risk across the accumulated shared repair diff; this packet does not certify a release of that complete diff.

Unlazy records 111 met gates, six unmet root requirements and zero abandoned gates. Exact packet leases released; dispatch complete. The task-local PostgreSQL runtime was stopped after zero scratch databases/other clients. No provider request, production write, commit or deployment occurred. V08/P01 remain IN PROGRESS: append-only qualification/revision policy, actual pair-specific provider evidence, qualified references and versioned evaluation/reconciliation remain required. The wider theory, research, operational and release requirements remain active.

## Seventeenth repair packet acceptance

V08/P01 now include pure quote-snapshot reconciliation: exact stored-text integrity, typed reference reconstruction, complete retained-row multiset changes, separate reference-price effects, actual-text resource limits and incomplete-acquisition safeguards. The central-writer integration test confirms exact envelopes and retries for all three locked pairs. This is local software evidence; reconciliation persistence, acceptance policy, actual provider coverage and versioned evaluation remain required. See [the revision contract](QUOTE_REVISION_CONTRACT.md) and [parent proof](../reports/repair-quote-revision-integration.md).

S02/S06 and the research work now have [17 concrete economic regression cases](../reports/repair-pair-economic-actions.md), traced to current code and primary-source definitions. The audit confirms state-only VOL/OI direction, inconsistent currency orientation, COT category mixing, rate-state/news confusion and unsupported intervention assumptions. It preserves repaired rate/ECB-unit behavior and does not assert missing EURUSD DXY logic already exists. These are implementation actions and research boundaries, not completed strategy repairs or measured accuracy gains.

Independent parent gates passed the 22-case comparison leaf and 138-case integration set. Full pipeline gate passes (1028 tests collected), Ruff and MyPy198 pass. Unlazy: 117 met, six root unmet, zero abandoned. All packet leases released; repair-17 dispatch complete. No provider acquisition, production write, runtime startup, commit or deployment. No issue is closed solely because tests increased. The next strategy packet must implement the shared direction/state/orientation contract with cross-path regressions and new model versions; quote qualification and broader research/release work remain open.

## Eighteenth repair packet acceptance

S01/S02/S04/S06 and P01/P02 now include a shared pair-up boundary for raw positioning, USD special factors and normalized INR-demand deviations. VOL/OI no longer supply direction or denominator weight; unsupported contemporaneous beta weighting and the directional intervention ramp are disabled. Positive EURUSD correctly receives dollar-weakness labels, with pair-aware hysteresis reconstruction. Descriptive state labels do not claim an identified policy/growth shock. New calls use `3.0-directional-reference` and `pair-direction-v1`; originals remain unchanged.

Homogeneous AM-minus-LM COT history no longer mixes missing categories with net-long. Latest missing reports remain unavailable; conflicting duplicates reject. Replay no longer invents OI percentiles or uses raw FPI cash as a normalized signal. Scheduler, staged, replay and diagnostic paths have shared sign conversion. Missing directional inputs cannot be replaced by a zero or volatility vote.

Parent review caught and repaired physical OI-label inversion, dropped cross-asset history at the production snapshot boundary, scalar/history integer overflow and invalid FPI clipping. Actual core-buffer-to-staged-adapter-to-signal tests now carry validated special-factor history. Invalid history rejects a whole leg and preserves missing-data health. FPI checks distinguish cash-flow sign from deviation around a prior median and reject invalid numbers/configuration. See [directional integration](../reports/repair-directional-integration.md), [snapshot bridge](../reports/repair-cross-asset-history-bridge.md) and [FPI numeric proof](../reports/repair-fpi-numeric-contract.md).

All six leaves passed parent review and runnable re-verification. Full pipeline gate passes; independent final collection reports 1168 tests. Full Ruff and MyPy204 pass. Unlazy records 129 met, six root unmet, zero abandoned. Dispatch complete; exact leases released. No provider acquisition, credential read, production write, runtime startup, commit, push or deployment occurred.

These repairs do not close the economic/research items. Full released-input parity, actual COT releases/vintages, qualified local rates, dated cross-asset history and frozen experiments remain required. The central reader still omits FPI history, returns descending rows and lacks usable release qualification; adding a column alone is insufficient. The asymmetry diagnostic still needs quotation-aware crowding logic. Public config/inspector weights still reflect the older model and must be reconciled by version. The proposed protected Japan intervention wording is pending the owner's earlier decision. Durable quote acceptance/reconciliation, security/operations, full migration rehearsal and real release/live evidence remain open.

## Nineteenth repair packet

S06/R02 and public diagnostic consumers now have a coherent local correction: unsupported pain, participant-loss/squeeze claims and Apex ranking are retired. A versioned description preserves supplied net positions, actual frozen-call alignment and signed deviation from the 40-observation arithmetic mean, with release/category/timing limitations. Original records remain intact; current readers suppress unsupported legacy estimates. AI cannot repopulate the retired squeeze field, and unused Apex sharing functions reject before model access.

Parent acceptance includes 21 core/ranking cases, 55 consumer cases, 10 React render cases and 243 actual Python-to-TypeScript payloads. The full pipeline gate passes (1196 collected), Ruff/MyPy (206 files) pass, all 43 frontend tests pass, and TypeScript/Biome (204 files)/local production build pass. See [the integration receipt](../reports/repair-crowding-integration.md). Missing source qualification, historical reconciliation, other public-methodology claims, calibrated research and deployed observation remain open. Unlazy: 137 met, six root unmet, zero abandoned. No whole-register or forecasting-skill completion is claimed.

Packet20 discovered a test isolation defect within A03/R7: test_fetch_fpi_flows_smoke performs an unmocked SEBI request and accepts missing data as success. Earlier full-suite no-provider-request claims are withdrawn; exact response evidence is unknown. The parent reproduced the outbound boundary under a fail-if-called stub. A default guard and deterministic replacement are in progress; no source data is accepted from these test runs.

## Twentieth repair packet

The FPI source review disproved the assumptions behind the old SEBI adapter: the verified report is NSDL investment activity by reporting date and seven category groups, with no established fixed release hour or first-release archive. Both old fetch APIs now reject before I/O. New signal assembly rejects raw/normalized FPI without qualified dated evidence; live, staged and both replay versions report missing source/history. Legacy scalars are not republished. Effectively zero prior MAD returns unavailable. Source definitions and the remaining parser/archive/selector/activation requirements are frozen in [the FPI observation contract](FPI_OBSERVATION_CONTRACT.md).

The test isolation defect is repaired with a default Python DNS/socket guard and deterministic retired-fetch tests. Earlier complete-run no-provider-request claims remain withdrawn. The guard has explicit import, fixture-scope, subprocess/native and late-worker limits; it is not an OS sandbox. Source research used intentional public page reads.

Parent acceptance: 63 focused FPI cases, eight network controls, final full R2 passed with 1216 collected, full Ruff and MyPy209 passed. One stale exact warning-list expectation was corrected after an actual full-suite failure; both replay paths now agree. Unlazy: 143 met, six root unmet, zero abandoned. Reports: [source research](../reports/repair-fpi-source-research.md), [boundary repair](../reports/repair-fpi-source-boundary.md), [test isolation](../reports/repair-test-network-isolation.md). No full FPI repair, forecasting edge, production migration or deployed acceptance is claimed.

## Twenty-first repair packet

The FPI replacement now has a real source parser and pure dated observation layer. Original NSDL HTML and the official note were captured privately and independently inspected. The note includes non-cash corporate actions, so the aggregate is not pure cross-border cash flow. The strict parser handles all seven groups, actual cell spans and malformed footer, reconciles INR and separately retained USD figures, and rejects missing/ambiguous data, wrong units, nested tables and malformed numbers.

Observation identity includes all INR components; the selector preserves revisions, rejects contradictory first-seen evidence, excludes later captures and uses unique earlier reporting dates. First-seen values supplied by the parser are candidates, not durable database proof. Original source and receipt hashes have a reproducible offline verifier; tampered-body and receipt controls reject. Submicrosecond completion is conservatively rounded up.

Parent acceptance: 86 focused cases, 19 actual date blocks, final full R2 passed (1302 collected), Ruff passed and MyPy214 passed. A full-project script namespace collision was fixed rather than weakening type checks. Unlazy: 150 met, six root unmet, zero abandoned. See [original source](../reports/repair-fpi-original-source.md), [parser](../reports/repair-fpi-parser.md), [observation](../reports/repair-fpi-observation.md) and [contract](FPI_OBSERVATION_CONTRACT.md).

Durable private capture/observation storage, atomic first-seen assignment, acceptance/withdrawal policy, bounded acquisition with attempt evidence, shared live/staged/replay integration and frozen feature evaluation remain required. FPI is not active in production calls. No production schema or data was changed. This is additional accepted local implementation, not closure of the FPI research or whole repair goal.


## Packet 22 timing discoveries

FPI durable storage review reproduced two defects in the new, still inactive observation selector. A captured revision sequence A -> B -> A selects B because ordering uses each value identity's immutable first-seen time. The builder also refuses a durable observation time after HTTP retrieval. Packet 21's tests proved its declared narrow properties, not a complete temporal model; its causal-selection claim is superseded for these cases. Both defects remain open under the existing FPI/source-time repair requirements, with concrete implementation and regression requirements being reviewed in reports/repair-fpi-timing-review.md. Production FPI remains unavailable.

Private raw capture storage is now implemented and independently verified before normalized observation persistence. It preserves exact complete HTTP response bytes and explicit transport metadata, including malformed/error responses. Database stored_at is not a commit or read-visibility timestamp. No source release time, cash-flow interpretation or feature eligibility follows from storage.


## Twenty-second repair packet

Private raw FPI capture persistence now has an exact-byte constructor, central writer and forward migration 20260927000010. The complete SQL gate proves strict direct-input validation, retries/concurrency, immutable rows, private access, RLS and fresh/populated reapplication against an isolated fixture. Parent verification additionally round-tripped both pinned original reports and all 19 parsed date blocks. A mutation removing document-hash verification made the actual SQL verifier fail. Original ledger tables and production state were not modified.

The full pipeline gate passes (1,349 collected); Ruff and MyPy216 pass. Unlazy records155 met, six root unmet and zero abandoned. Three packet22 leaves are verified, dispatch complete and exact leases released. The temporary PostgreSQL instance was stopped after confirming zero scratch databases/other clients. This does not prove the full production migration chain or operational source quality.

Open FPI temporal defects are tracked in the [timing review](../reports/repair-fpi-timing-review.md): FPI-T01 value reversion, FPI-T02 post-retrieval visibility, FPI-T03 transaction visibility and exact replay membership, FPI-T04 endpoint/source-order conflicts, FPI-T05 parser correction identity, and FPI-T06 qualification/withdrawal/frozen-policy state. The review defines twelve required implementation checks. Its diagnosis is complete; these defects remain unresolved. The original receipts do contain started_at: a parent assumption to the contrary was checked and withdrawn before acceptance. No historical source release or first-seen evidence is inferred from the storage receipt. FPI remains inactive in production calls.

## Twenty-third repair packet

The unsafe first-seen selector now rejects. Its replacement takes an exact supplied decision snapshot and frozen policy, keeping values, source occurrences, parser memberships and qualification events separate. Pure regressions cover value reversion, delayed qualification, overlap/endpoint conflict, parser correction, withdrawal scopes, frozen replay, history coverage and missingness. Full result and selector-artifact identities are bound. Domain vocabulary now distinguishes parser correction from a new source occurrence.

Parent acceptance: 79 selector cases, 164 combined FPI cases, original-source verification,200 independent interval/order comparisons and a wrong-winner negative control. Full R2 passes with 1412 collected; full Ruff/MyPy (218 files) pass. Unlazy: 160 met, six root unmet, zero abandoned. See [selection contract](FPI_SELECTION_CONTRACT.md) and [parent evidence](../reports/repair-fpi-selection-integration.md).

FPI-T01/T02/T04/T05/T06 now have accepted pure behavior, not complete durable or operational acceptance. FPI-T03 actual transaction visibility remains open. All six still require the relevant storage/reader/acquisition integration: atomic complete parse registration, artifact retention, serialized qualification, exact committed candidate reads, saved decision snapshots, paused-writer/reverse-commit proof and real consumer parity. FPI remains inactive and no empirical edge is claimed. No production write or release occurred.

## Twenty-fourth repair packet

Private implementation artifacts, complete parse results and all dated INR/USD memberships now persist atomically through the central writer. Parent independently reverified 70 focused cases, nine real PostgreSQL check groups and both pinned original reports (19 dates). Direct-SQL validation covers canonical text, hashes, reconciliation, dependencies, retries/conflicts, rollback, permissions and immutability. A real paused transaction is invisible before commit and complete afterward. Removing only USD-total reconciliation in a disposable in-memory migration makes the same verifier fail at its rehashed invalid-total assertion; the real migration remains unchanged.

Full pipeline R2 passes with 1,482 collected, Ruff passes and MyPy220 passes. Unlazy: 167 met, six root unmet, zero abandoned. All packet24 leaves are reviewed, waves complete and exact leases released. Temporary PostgreSQL was stopped after zero scratch databases/other clients. No production migration or FPI activation follows from these local results.

FPI-T07 remains open. The reviewed next-layer design addresses equal clocks with explicit event order and historical resolution witnesses, defines complete scoped reads with no silent truncation, and separates retained artifacts from trusted execution. Its v2 contract and implementation remain required. Source qualification, acquisition, actual live/staged/replay parity and frozen feature evaluation also remain open. See [integration evidence](../reports/repair-fpi-parse-integration.md) and [decision design](../reports/repair-fpi-decision-storage-design.md). No broad register issue is closed solely by this storage packet.

## Packets25/26 accepted locally — 28 September 2026

Pure ordered qualification, historical resolution witnesses and bounded batch evaluation pass independent sequential comparisons and three intentionally wrong evaluators. Yield-adapter raw error logging is repaired with actual baseline leak controls; wider A03 remains open. Trusted execution is a reviewed approved-release recomputation design, not provisioned authority. Durable order/read and consumer eligibility remain open; FPI remains inactive.

Parent evidence: 215 qualification cases, 49 privacy/rate cases, full R2 (1632 collected), Ruff and MyPy224 pass. Unlazy:175 met, six root unmet, zero abandoned. No whole-register or release acceptance follows. See reports/repair-fpi-qualification-integration.md.

### Packet27 runtime-bound finding

O02/L04 remain open: function-local statement_timeout does not enforce a fresh outer command timer on PostgreSQL17. A real temporary-function positive/negative probe reproduced this. Packet27 corrected new qualification storage to require pre-request timeout configuration and proved actual cancellation. Packet29 locally verified the same inherited-timeout and lock-timeout boundary for FPI capture/artifact/parse functions. Packet31 extended actual timer, rollback, unchanged-state, permission and removed-guard checks to append_validation_evaluation, append_regime_publication, append_price_observations, append_quote_capture, append_quote_snapshot and append_quote_acquisition_event. Their deployed PostgREST connection/request timer settings remain unverified. Lock timeouts, bounded inputs and client subprocess timeouts are separate controls. No earlier data-integrity test is withdrawn.

## Packet27 accepted locally — 28 September2026

Durable qualification ordering and strict central-writer receipts pass285 Python cases and eight real database groups. Parent wrong-command receipt and predecessor-guard-removal controls fail as intended. Full R2 passes with1781 collected; Ruff/MyPy225 and standalone verifier checks pass.179 gates met, six root unmet, zero abandoned. Runtime stopped after verified scratch cleanup. No production change or activation.

ACCEPT remains administrative intent pending protected verification. Complete saved reads, approved-release execution, actual consumers and empirical FPI usefulness are still unproven. Source qualification for rates/COT/prices and all other register work remain in scope. Earlier SQL timeout assumptions need the newly recorded audit. See reports/repair-fpi-qualification-storage-integration.md.
