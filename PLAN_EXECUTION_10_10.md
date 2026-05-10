# PLAN_EXECUTION_10_10.md — From 4.5/10 to 10/10 and Beyond

> **Canonical execution plan.** This document maps every task required to transform FX Regime Lab from its current 4.5/10 state into an institutionally credible 10/10 quantamental research operation, with the path to 10+ over 24 months.
>
> **Governance:** Every phase must pass through the Triple-Chamber Council (OMEGA_PROTOCOL.md) before delegation.
> **Decision authority:** Kimi = strategy, architecture, and council simulation. Cursor = code execution. Subagents = parallel research, audit, and exploration.

---

## THE SCORECARD TARGETS

| Dimension | Current | Phase 3 Target | Phase 5 Target | 10/10 Target | Beyond 10 |
|-----------|---------|----------------|----------------|--------------|-----------|
| Signal Framework | 5/10 | 7/10 | 8/10 | 9/10 | 9.5/10 |
| Validation & Track Record | **2/10** | 6/10 | 8/10 | 9/10 | 9.5/10 |
| Data Quality | 5/10 | 6/10 | 7/10 | 8/10 | 9/10 |
| Code Quality | 6/10 | 7/10 | 8/10 | 9/10 | 9/10 |
| Database & Schema | 7/10 | 8/10 | 8.5/10 | 9/10 | 9/10 |
| UI Visual Design | 4/10 | 6/10 | 8/10 | 9/10 | 9/10 |
| Copy & Identity Tone | 4/10 | 7/10 | 8.5/10 | 9/10 | 9/10 |
| Infrastructure & Ops | 5/10 | 6/10 | 8/10 | 9/10 | 9.5/10 |
| Monitoring | **3/10** | 6/10 | 8/10 | 9/10 | 9.5/10 |
| **OVERALL** | **4.5/10** | **6.5/10** | **8/10** | **9/10** | **9.5/10** |

**10/10 definition:** A PM at Brevan Howard or CIO at a macro fund could review this in 30 minutes and conclude it is a genuine, production-grade research operation run by a credible practitioner. The framework is mathematically defensible, the track record is audited and immutable, the UI is indistinguishable from an institutional terminal, and the operational layer is hardened.

**Beyond 10 definition:** Published SSRN paper. 2+ year track record with institutional data (Bloomberg/Reuters). Referenced by practitioners. Cited in MFE syllabi.

---

## EXECUTION PHILOSOPHY

### The EV Stack Rank

Every task is scored on two axes:
1. **Credibility Impact** — How much does this move the needle with NTU MFE admissions or HF recruiters?
2. **Execution Risk** — How likely is this to break something or consume disproportionate time?

**Priority = Credibility Impact / Execution Risk.** Highest ratio first.

### The Three Gaps

All tasks map to one of three gaps identified in the master audit:

| Gap | Description | Fix Strategy |
|-----|-------------|--------------|
| **Execution Integrity** | Validation engine dead. Ledger not immutable. Track record unverified. | Make it real. Wire the engine. Enforce append-only. |
| **Identity Signaling** | UI pulses, ghost whispers, undergrad bio, student disclaimers. | Make it anonymous. Strip theatricality. Peer tone everywhere. |
| **Operational Maturity** | No alerting, no backups, no CI/CD, stale docs. | Make it boring. Production hardening. Runbooks. |

### Delegation Matrix

| Owner | Role | What They Do |
|-------|------|--------------|
| **Kimi** | Strategy & Architecture | Council simulation, spec writing, task prioritization, copy review, macro context calibration |
| **Cursor** | Code Execution | All file modifications, test writing, schema changes, frontend builds, deployment commands |
| **Subagent (explore)** | Research & Audit | Parallel codebase exploration, competitive analysis, literature review, pre-implementation audit |
| **Subagent (coder)** | Isolated Implementation | Complex multi-file refactors that need dedicated context, historical backfill operations |

### The 14/10 Protocol

Each phase has 14 steps (the 6-phase OMEGA loop expanded with granular checkpoints):

```
1. Chamber 1 Convene — Strategy audit
2. Chamber 2 Convene — Engineering blueprint
3. Chamber 3 Convene — Perception check
4. Spec Writing — Kimi produces Cursor-ready spec
5. Spec Validation — Cross-check against locked decisions
6. Delegation — Cursor executes
7. Parallel Audit — Subagent verifies against requirements
8. Test Execution — pytest + build + lint
9. Regression Check — No broken existing functionality
10. Documentation Sync — CONTEXT.md, HANDOVER.md, TASK.md updated
11. Council Re-convene — Post-implementation review
12. Zeta-Verification — Final audit for logic/data/UI regressions
13. Deploy Gate — Human approval for Tier 2/3/4 changes
14. Monitor — Post-deploy observability
```

---

## PHASE 0: EMERGENCY TRIAGE
**Duration:** 3 days  
**Goal:** Stop the credibility bleeding. Fix the three kill shots before anything else.  
**Council Mandate:** All chambers emergency session. No feature work. No UI polish. Only truth.

### P0-T1: Wire the Validation Engine (CRITICAL — Execution Integrity)

**Chamber 1:** Marcus (PM) demands this first. Lena (Quant) confirms Brier math. Dr. Aris confirms T+5/T+20 horizons align with macro tradability.  
**Chamber 2:** Elias designs the schema change. Viktor enforces type safety. Sasha ensures the orchestrator won't fail.  
**Chamber 3:** Peer Reviewer confirms this satisfies MFE rigor. Coach Silas confirms this is highest-EV career move.

**Task:**
- Replace deprecated `validate_call` in orchestrator with `run_validation()` from `src/validation/engine.py`
- Fix T+20 overwriting T+5 columns — add separate columns `actual_return_20d`, `correct_20d`, `brier_20d`
- Ensure `run_validation()` runs AFTER the daily pipeline completes and AFTER `regime_calls` is written
- Add integration test: mock fetchers → run pipeline → assert one validation row exists with correct math

**Owner:** Cursor  
**Subagent Support:** explore agent pre-audit of orchestrator flow to map exact insertion point  
**EV:** Critical (infinity — without this, nothing else matters)  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] `grep -n "run_validation" src/scheduler/orchestrator.py` returns a match
- [ ] Daily run produces rows in `validation_log` with `brier_5d` populated
- [ ] T+5 and T+20 values do not overwrite each other
- [ ] Integration test passes
- [ ] pytest 186/186 passes

**Cursor Spec Template:**
```
Implement P0-T1: Wire Validation Engine into Production Pipeline

Files to modify:
- src/scheduler/orchestrator.py — replace deprecated validate_call with run_validation()
- src/db/writer.py — add write_validation_engine_row() for T+5/T+20 separate columns
- supabase/migrations/ — add columns actual_return_20d, correct_20d, brier_20d to validation_log
- src/validation/engine.py — ensure T+5 and T+20 write to separate columns, no overwrites
- tests/ — add test_validation_engine_integration.py

Acceptance criteria:
1. orchestrator calls run_validation() after regime_calls write
2. T+5 and T+20 data coexist in same row without overwriting
3. Integration test with mocked fetchers produces exactly 1 validation row
4. All 186 tests pass
5. ruff clean, mypy clean on modified files

Do NOT modify signal logic. Do NOT modify regime classification. Surgical change only.
```

### P0-T2: Enforce Immutable Ledger (CRITICAL — Execution Integrity)

**Chamber 1:** Marcus declares: if the ledger is editable, it's not a ledger.  
**Chamber 2:** Elias designs the trigger. Sasha ensures pipeline re-runs don't crash. Viktor adds type safety.  
**Chamber 3:** Peer Reviewer confirms this satisfies academic immutability standards.

**Task:**
- Apply migration `20260505000000` trigger `protect_immutable_calls()` to production
- Fix FK type mismatch: `validation_log.call_id` must match `regime_calls.id` type (UUID)
- Replace `upsert` with `INSERT + ON CONFLICT DO NOTHING` for `regime_calls` and `validation_log`
- Gate `delete_pipeline_data_for_date()` behind a `--force` flag or remove it entirely
- Add `is_superseded` write logic or remove the filter from aggregate queries

**Owner:** Cursor  
**EV:** Critical  
**Dependencies:** P0-T1 (validation engine must write correctly before we lock it)  
**Acceptance Criteria:**
- [ ] Trigger is active in Supabase
- [ ] Attempted UPDATE on historical `regime_calls` row fails
- [ ] `INSERT OR IGNORE` semantics work for re-runs
- [ ] FK type mismatch resolved
- [ ] `delete_pipeline_data_for_date()` cannot be called accidentally

### P0-T3: Pipeline Failure Alerting (CRITICAL — Operational Maturity)

**Chamber 1:** Marcus demands: if the system fails and nobody knows, it's not a system.  
**Chamber 2:** Sasha designs the alert path. Xavier ensures it's minimal and reliable.  
**Chamber 3:** Elena confirms alert fatigue won't occur. Claire ensures alert text is professional.

**Task:**
- Add Slack webhook alert when Prefect flow state = FAILED
- Add email alert when DQS drops below threshold (e.g., <0.7)
- Add daily success heartbeat (so silence = problem)
- Document alert endpoints in `.env.example`

**Owner:** Cursor  
**EV:** Critical  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Failed Prefect run triggers Slack message within 60 seconds
- [ ] DQS < 0.7 triggers email
- [ ] Daily success message posts at 23:30 UTC if run completes
- [ ] No alerts fire on successful runs

---

## PHASE 1: TRUTH & IMMUTABILITY
**Duration:** 2 weeks  
**Goal:** The track record is real, verifiable, and defensible. No aspirational claims. Only operational facts.  
**Council Mandate:** Chamber 1 leads. This phase is about mathematical and engineering truth.

### P1-T1: Validation Backfill (Historical Proof)

**Chamber 1:** Lena designs the backfill methodology. Marcus defines the minimum viable history.  
**Chamber 2:** Elias designs the backfill schema. Viktor writes the type-safe backfill engine.  
**Chamber 3:** Peer Reviewer audits for look-ahead bias. Coach Silas confirms this strengthens the MFE application.

**Task:**
- Backfill `validation_log` for all existing `regime_calls` using historical spot prices
- Compute T+5 and T+20 outcomes retroactively (this is NOT look-ahead bias — we're evaluating past calls with future data that was unknown at call time)
- Generate aggregate stats: win rate by regime, Brier score by pair, calibration buckets
- Write results to `validation_stats` table

**Owner:** Cursor  
**Subagent Support:** coder subagent for the backfill computation (isolated, data-heavy task)  
**EV:** Very High  
**Dependencies:** P0-T1, P0-T2  
**Acceptance Criteria:**
- [ ] Every `regime_calls` row has corresponding `validation_log` rows
- [ ] Aggregate stats show overall accuracy (target: >55% directional at T+5)
- [ ] Brier scores computed and stored
- [ ] No look-ahead bias in backfill logic

### P1-T2: Parameter Derivation Documentation (Mathematical Rigor)

**Chamber 1:** Lena demands sensitivity analysis. Dr. Aris provides literature citations.  
**Chamber 2:** Viktor writes the calibration notebook. Xavier ensures it's reproducible.  
**Chamber 3:** Peer Reviewer confirms it satisfies SSRN standards. Hugo ensures the notebook is visually professional.

**Task:**
- Create `research/calibration.ipynb` documenting:
  - Why 0.72 alignment penalty (literature citation or sensitivity sweep)
  - Why 0.48 crowding coefficient (COT extreme empirical analysis)
  - Hysteresis threshold derivation (Schmitt trigger theory + empirical fit)
  - MAD Z-score vs standard Z-score justification
- Add walk-forward sensitivity analysis for each parameter
- Export key charts as PNG for the Methodology page

**Owner:** Kimi (content + math review) + Cursor (notebook implementation)  
**Subagent Support:** explore agent for literature search on COT crowding penalties and Schmitt trigger applications in regime detection  
**EV:** Very High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Every magic number in layer1/layer2/layer3 has a documented derivation
- [ ] Sensitivity analysis shows framework is robust to ±10% parameter variation
- [ ] Notebook renders without errors
- [ ] Key figures are web-ready for Methodology page

### P1-T3: True Append-Only Audit Trail (Engineering Truth)

**Chamber 1:** Marcus defines what "immutable" means in practice.  
**Chamber 2:** Elias designs the audit schema. Sasha ensures it doesn't slow down writes.  
**Chamber 3:** Peer Reviewer confirms academic standards met.

**Task:**
- Add `audit_log` table: operation, table, row_id, old_value, new_value, timestamp, correlation_id
- Add `created_by` and `write_hash` to `regime_calls` and `validation_log`
- Remove `delete_pipeline_data_for_date()` entirely
- Add `pipeline_errors` table (referenced in docs but missing from schema)
- Document the immutability guarantee in `docs/IMMUTABILITY.md`

**Owner:** Cursor  
**EV:** High  
**Dependencies:** P0-T2  
**Acceptance Criteria:**
- [ ] `audit_log` captures every write to `regime_calls`
- [ ] `pipeline_errors` table exists and receives errors
- [ ] No DELETE path exists for historical data
- [ ] Schema documented with immutability guarantees

### P1-T4: Data Source Upgrade (Data Quality)

**Chamber 1:** Dr. Aris identifies FRED + CFTC as acceptable primary sources. Marcus identifies yfinance weakness.  
**Chamber 2:** Sasha evaluates Twelve Data vs Polygon vs Alpha Vantage. Viktor implements the swap.  
**Chamber 3:** Elena ensures data quality is visible on the terminal.

**Task:**
- Upgrade FX spot primary source from Alpha Vantage to Polygon.io (already has API key)
- Keep yfinance as tertiary fallback (after Alpha Vantage)
- Add data lineage logging: source, fetch_timestamp, raw_value, transformation for every signal input
- Add PIT (point-in-time) note: document that FRED revisions are accepted as-is (standard practice for this tier)

**Owner:** Cursor  
**EV:** Medium-High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Polygon.io is primary for FX spot
- [ ] Data lineage visible in `signals` table or adjacent metadata table
- [ ] Pipeline still works if Polygon fails (falls back to Alpha Vantage → yfinance)
- [ ] No regression in test suite

---

## PHASE 2: IDENTITY SANITIZATION
**Duration:** 2 weeks (parallel with Phase 1)  
**Goal:** Zero student signals. Anonymous, peer-tone, institutional everywhere.  
**Council Mandate:** Chamber 3 leads. Hugo (Design Psychologist) and Claire (Substack Editor) drive.

### P2-T1: About Page Rewrite (Identity Kill Shot)

**Chamber 3:** Hugo demands anonymity. Elena demands information density. Claire writes the copy.

**Task:**
- Remove: name, age, university, degree, "studying," "learning," "project," "journey," "built this to"
- Remove: "This is not a student project" (if you have to say it, you've already lost)
- Add: Independent macro researcher. Live since [date]. Framework documentation. Data sources. Contact.
- Tone: Peer practitioner. Not applicant. Not student.

**Owner:** Kimi (copy) + Cursor (implementation)  
**EV:** Critical  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Zero student-identifying language
- [ ] Zero permission-asking language
- [ ] Reads like a boutique research shop's about page
- [ ] Mobile-responsive

**Copy Template:**
```
FX Regime Lab is an independent quantamental macro research operation.

We generate systematic regime classifications for G10 FX using a three-layer
signal framework: macro gating, directional bias, and execution timing.

The framework combines rate differentials, institutional positioning,
volatility regimes, and cross-asset confirmation into a single,
probabilistic call — updated daily at 23:00 UTC.

All regime calls are timestamped and immutable. Out-of-sample validation
is conducted at T+5 and T+20 horizons using Brier scores and log-return
analysis.

Data: FRED, CFTC COT, Polygon.io, CME.
Contact: [email]
```

### P2-T2: UI Theatricality Purge (Visual Identity)

**Chamber 3:** Hugo defines what "boring" means. Elena maximizes density.

**Task:**
- Remove: pulses, ghost whispers, "Apex Desk" card, "LinkedIn Alpha" button, `[ ∫ ]` toggle
- Rename: "Trader's TL;DR" → "DESK BRIEF"
- Rename: "Ghost Whisper" → remove entirely
- Rename: "Apex Desk" → "PRIMARY PAIR"
- Remove: grayscale hover effects, dimming, theatrical transitions
- Ensure: every page loads in <1 second. No animation delays.

**Owner:** Cursor  
**EV:** Very High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] No decorative animations except the cinematic landing intro (if kept)
- [ ] Terminal loads all data in one render — no staged reveals
- [ ] All pair cards visible simultaneously
- [ ] `npm run build` passes

### P2-T3: Methodology Page Hardening (Research Transparency)

**Chamber 1:** Dr. Aris ensures macro rigor. Lena ensures statistical correctness.  
**Chamber 3:** Peer Reviewer demands full formula transparency. Hugo ensures KaTeX is crisp.

**Task:**
- Add all formulas from `docs/SIGNAL_DEFINITIONS.md` as rendered KaTeX
- Add parameter derivation section referencing `research/calibration.ipynb`
- Add "Limitations" section (shows intellectual honesty): yfinance fallback, no PIT for FRED revisions, OI signal is experimental
- Add "Validation Methodology" section: T+5/T+20 horizons, Marcus dead-band, Brier score definition

**Owner:** Kimi (content) + Cursor (KaTeX implementation)  
**EV:** High  
**Dependencies:** P1-T2 (parameter derivation notebook)  
**Acceptance Criteria:**
- [ ] Every formula in SIGNAL_DEFINITIONS.md is rendered on the page
- [ ] Limitations section exists and is honest
- [ ] Page loads without KaTeX errors
- [ ] Mobile-readable

### P2-T4: Copy Audit Across All Surfaces (Tone Consistency)

**Chamber 3:** Claire audits every word. Coach Silas ensures no student framing.

**Task:**
- Audit all `page.tsx` files for student language
- Audit all component labels for retail trading language ("trader," "pips," "setup")
- Audit generated briefs for hedging language ("might," "could," "perhaps")
- Audit code comments for apologetic language ("hacky," "temporary," "not sure")
- Create `.cursor/rules/Copy-Tone.mdc` enforcing institutional voice

**Owner:** Subagent (explore) for comprehensive sweep + Kimi (review)  
**EV:** High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Zero instances of "I," "my," "we're trying to," "aspiring," "hope to"
- [ ] Zero instances of "hacky," "temporary," "TODO" in production code comments
- [ ] Briefs use declarative language with invalidation points
- [ ] `.cursor/rules/Copy-Tone.mdc` exists and is auto-applied

### P2-T5: Disclaimers & Legal Sanitization (Perception)

**Chamber 3:** Peer Reviewer ensures disclaimers don't undermine credibility.

**Task:**
- Remove: "This is for educational purposes only," "I am not a financial advisor," "Past performance does not guarantee future results" (everyone says this — it signals amateur)
- Add: "FX Regime Lab publishes research observations, not investment recommendations. Regime calls are generated by a systematic framework and validated out-of-sample. Readers are responsible for their own execution decisions."
- Tone: Confident, not defensive.

**Owner:** Kimi (copy)  
**EV:** Medium  
**Dependencies:** None

---

## PHASE 3: SIGNAL HARDENING
**Duration:** 4 weeks  
**Goal:** The math is defensible, the parameters are calibrated, the signals are institutional-grade.  
**Council Mandate:** Chamber 1 leads. Dr. Aris, Lena, and Marcus drive.

### P3-T1: OI Signal Replacement or Removal (Signal Quality)

**Chamber 1:** Marcus declares the OI signal has no macroeconomic interpretation. Dr. Aris agrees.  
**Chamber 2:** Viktor removes it cleanly. Elias handles schema migration.

**Task:**
- Option A: Remove OI from composite weighting (set weight to 0, document as experimental)
- Option B: Replace with actual macro interpretation (e.g., OI expansion as liquidity proxy with literature backing)
- Recommendation: **Option A** — remove until evidence exists

**Owner:** Cursor  
**EV:** High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] OI no longer contributes to composite score
- [ ] Tests updated to reflect removal
- [ ] Schema migration if OI column removed from `signals`
- [ ] No regression in other signals

### P3-T2: Special Signals Hardening (Data Quality)

**Chamber 1:** Dr. Aris flags copper-as-iron-ore as a kludge.  
**Chamber 2:** Sasha finds better data sources. Viktor implements.

**Task:**
- Remove copper-as-iron-ore proxy from AUDUSD special signal
- Either find real iron ore data or remove the special signal for AUDUSD
- Add DXY as a confirmed cross-asset signal (it already exists in cross_asset.py — formalize it)
- Document cross-asset correlation assumptions

**Owner:** Cursor  
**EV:** Medium  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] No proxy kludges in special signals
- [ ] DXY is formally integrated as a signal input
- [ ] Correlation assumptions documented

### P3-T3: Execution Layer Hardening (Risk Management)

**Chamber 1:** Marcus demands vol-adjusted stops. "1.5 × ADR is retail."  
**Chamber 2:** Viktor implements. Sasha ensures backward compatibility.

**Task:**
- Replace ADR-based stops with realized vol-adjusted stops: `stop = spot ± (1.5 × σ_20d × spot)`
- Document the vol-adjustment methodology
- Add position sizing as function of vol (Kelly fraction or half-Kelly)
- Keep ADR as fallback display metric

**Owner:** Cursor  
**EV:** Medium-High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Stops are vol-adjusted
- [ ] Position sizing formula documented
- [ ] Terminal displays both vol-adjusted stop and ADR
- [ ] Tests pass

### P3-T4: Layer 1 Tier Mapping Fix (Dead Code Removal)

**Chamber 1:** Dr. Aris notes that tier 0 and tier 1 both map to `RISK_ON_DOLLAR_OFF`, collapsing 5 tiers to 4.

**Task:**
- Fix `logic/layer1_gate.py` tier mapping so all 5 tiers are reachable
- Or: simplify to 4 explicit tiers and remove unreachable enum variants
- Document the tier logic with a decision tree

**Owner:** Cursor  
**EV:** Medium  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] All regime tiers are reachable or removed
- [ ] Decision tree documented in Methodology page
- [ ] No dead enum variants

### P3-T5: Integration Test Suite (Code Quality)

**Chamber 2:** Viktor demands end-to-end testing. Sasha ensures CI-readiness.

**Task:**
- Write `tests/integration/test_full_pipeline.py`:
  - Mock all fetchers with synthetic data
  - Run full orchestrator
  - Assert: signals written, regime call written, validation row written
- Write `tests/integration/test_idempotency.py`:
  - Run pipeline twice with same mocked data
  - Assert: no duplicate regime_calls rows, no duplicate validation rows

**Owner:** Cursor  
**EV:** High  
**Dependencies:** P0-T1, P0-T2  
**Acceptance Criteria:**
- [ ] Integration test runs in <10 seconds
- [ ] Full pipeline end-to-end verified
- [ ] Idempotency verified
- [ ] pytest passes

---

## PHASE 4: OPERATIONAL MATURITY
**Duration:** 6 weeks  
**Goal:** The system is production-hardened. It runs itself. It alerts on failure. It backs itself up.  
**Council Mandate:** Chamber 2 leads. Sasha (SRE) drives.

### P4-T1: CI/CD Pipeline (GitHub Actions for PRs)

**Chamber 2:** Sasha designs the PR gate. Xavier ensures it matches the existing stack.

**Task:**
- Add `.github/workflows/pr-check.yml`:
  - Run pytest on Python changes
  - Run `npm run build` on frontend changes
  - Run ruff + biome
  - Block merge on failure
- Note: This is for PR validation only. Deployment remains Prefect Cloud + Vercel manual.

**Owner:** Cursor  
**EV:** High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] PRs run tests automatically
- [ ] Failed tests block merge
- [ ] No deployment automation (Prefect deploy remains manual)

### P4-T2: Database Backup & Disaster Recovery

**Chamber 2:** Elias designs backup strategy. Sasha automates it.

**Task:**
- Add nightly `pg_dump` script to S3 or local storage
- Document Supabase PITR (Point-in-Time Recovery) setup
- Add `scripts/backup.sh` with cron schedule
- Test restore procedure on a separate Supabase project

**Owner:** Cursor  
**EV:** High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Nightly backups run without error
- [ ] Restore procedure documented and tested
- [ ] Backup retention policy defined (e.g., 30 days)

### P4-T3: Structured Logging & Observability

**Chamber 2:** Sasha designs the log schema. Xavier ensures minimal overhead.

**Task:**
- Replace `logger.info` with JSON-structured logs: `{timestamp, level, correlation_id, step, pair, metric, value}`
- Add correlation ID across all 13 pipeline steps
- Create real `pipeline_errors` table with: correlation_id, step, error_type, message, timestamp
- Add Cloudflare Worker analytics dashboard

**Owner:** Cursor  
**EV:** Medium-High  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] All pipeline steps emit JSON logs
- [ ] Correlation ID traces a single run end-to-end
- [ ] `pipeline_errors` table exists and is populated
- [ ] Cloudflare Worker analytics visible

### P4-T4: Documentation Accuracy Sweep

**Chamber 3:** Peer Reviewer demands doc consistency.

**Task:**
- Update TASK.md: 186 tests (not 121)
- Update HANDOVER.md: Prefect Cloud scheduler (not GitHub Actions)
- Update .agent/index.json: 156 files (not 148), 186 tests
- Update all stale references
- Add `docs/CHANGELOG.md` tracking major framework versions

**Owner:** Kimi (review) + Cursor (mechanical updates)  
**EV:** Medium  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] All documentation numbers match reality
- [ ] No conflicting scheduler claims
- [ ] CHANGELOG.md exists with dated entries

### P4-T5: Runbook & Incident Response

**Chamber 2:** Sasha writes the runbook. Xavier ensures it's actionable at 2 AM.

**Task:**
- Create `docs/RUNBOOK.md`:
  - "Pipeline failed at 23:05 UTC — what do I do?"
  - "Supabase is down — what do I do?"
  - "Data source (FRED/CFTC) is delayed — what do I do?"
  - "Validation engine returns NaN — what do I do?"
- Add escalation contacts and fallback procedures

**Owner:** Kimi (content)  
**EV:** Medium  
**Dependencies:** P4-T1, P4-T3  
**Acceptance Criteria:**
- [ ] Runbook covers 5 most common failure modes
- [ ] Each failure mode has: symptom, diagnosis, fix, fallback
- [ ] Runbook is accessible offline

### P4-T6: Performance Optimization

**Chamber 2:** Viktor profiles. Sasha ensures daily run stays under 2 minutes.

**Task:**
- Profile `orchestrator.py` — identify slow fetchers
- Add async fetching where safe (cross-asset data can be fetched in parallel)
- Keep sequential execution for signal logic (no look-ahead risk)
- Target: daily run <90 seconds end-to-end

**Owner:** Cursor  
**EV:** Low-Medium  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Daily run completes in <90 seconds
- [ ] No signal logic parallelized (fetchers only)
- [ ] Profile report saved to `research/performance_profile.md`

---

## PHASE 5: INSTITUTIONAL POLISH
**Duration:** 3 months  
**Goal:** MFE application package assembled. Performance page public. SSRN paper drafted.  
**Council Mandate:** All chambers. Coach Silas drives prioritization.

### P5-T1: Public Performance Page (Live Accuracy Metrics)

**Chamber 1:** Lena designs the metrics. Marcus defines what PMs want to see.  
**Chamber 3:** Elena designs the layout. Hugo ensures it's dense and monochrome.

**Task:**
- Build `/terminal/performance` page with:
  - Overall directional accuracy (T+5, T+20)
  - Brier score by pair
  - Win rate by regime type
  - Calibration chart (predicted probability vs actual frequency)
  - Sharpe-like ratio by pair
  - Max drawdown proxy
  - Number of observations (must be >100 for statistical relevance)
- All numbers update automatically from `validation_stats`

**Owner:** Cursor  
**EV:** Critical  
**Dependencies:** P1-T1 (backfill complete), P1-T2 (parameters documented)  
**Acceptance Criteria:**
- [ ] All metrics auto-update from Supabase
- [ ] >100 observations visible
- [ ] Calibration chart renders correctly
- [ ] Page loads in <2 seconds

### P5-T2: Regime History Strip (Visual Credibility)

**Chamber 3:** Hugo designs the timeline. Elena ensures density.

**Task:**
- Add horizontal regime history strip for each pair
- Show last 90 days of regime calls with color coding
- Hover/click shows: date, regime, conviction, T+5 outcome
- Exportable as PNG for LinkedIn/Substack

**Owner:** Cursor  
**EV:** High  
**Dependencies:** P1-T1  
**Acceptance Criteria:**
- [ ] 90-day strip visible per pair
- [ ] Color-coded by regime
- [ ] Outcome indicator (hit/miss/neutral) visible
- [ ] Exportable PNG

### P5-T3: SSRN Methodology Paper (Academic Credibility)

**Chamber 1:** Dr. Aris structures the paper. Lena handles statistical exposition.  
**Chamber 3:** Peer Reviewer ensures it passes academic standards.

**Task:**
- Draft paper: "A Three-Layer Signal Framework for G10 FX Regime Classification"
- Sections: Abstract, Literature Review, Framework (Layer 1/2/3), Data, Validation Methodology, Results, Limitations, Conclusion
- Include: Brier scores, calibration charts, regime-specific hit rates
- Target: 15 pages, LaTeX format
- Submit to SSRN

**Owner:** Kimi (drafting) + Subagent (explore for literature review)  
**EV:** Very High (for MFE admissions)  
**Dependencies:** P1-T2 (parameter derivation), P5-T1 (performance metrics)  
**Acceptance Criteria:**
- [ ] Paper is 15+ pages
- [ ] All formulas are LaTeX-rendered
- [ ] Results section includes real out-of-sample stats
- [ ] Submitted to SSRN

### P5-T4: Event Calendar Integration (Macro Context)

**Chamber 1:** Dr. Aris identifies high-impact events. Marcus notes tradability.

**Task:**
- Build `/terminal/calendar` page with:
  - Central bank meetings (Fed, ECB, BoJ, RBI)
  - CPI, payrolls, GDP releases
  - Impact scoring (high/medium/low)
  - Regime implication notes (e.g., "Fed pause → USD weakness continuation")

**Owner:** Cursor  
**EV:** Medium  
**Dependencies:** None  
**Acceptance Criteria:**
- [ ] Calendar shows next 30 days
- [ ] High-impact events highlighted
- [ ] Regime implications added manually or via AI (ON HOLD)

### P5-T5: GBP/USD Addition (Pair Expansion)

**Chamber 1:** Dr. Aris evaluates BoE dynamics. Marcus assesses tradability.  
**Chamber 2:** Elias designs schema migration. Viktor implements signals.

**Task:**
- Add GBP/USD as fourth pair (breaking 3-pair lock — this is a Tier 3 decision requiring human approval)
- Add BoE rate fetcher
- Add GBP COT mapping
- Update composite weights
- Update UI

**Owner:** Cursor  
**EV:** Medium  
**Dependencies:** Human approval (Tier 3)  
**Acceptance Criteria:**
- [ ] GBP/USD signals generate correctly
- [ ] COT percentiles computed for GBP
- [ ] UI updated for 4 pairs
- [ ] Tests pass

### P5-T6: MFE Application Package Assembly

**Chamber 3:** Coach Silas drives. Peer Reviewer audits.

**Task:**
- Compile application materials:
  - CV: lead with FX Regime Lab, not FinTree or university
  - Statement of Purpose: 500 words on the framework, validation methodology, and research goals
  - Portfolio link: fxregimelab.com/terminal/performance
  - Recommendation: request from FinTree CEO (operational relationship)
  - CFA L1 score report
- Target: NTU MFE Round 1 (if applicable) or Round 2

**Owner:** Kimi (strategy + copy review)  
**EV:** Critical  
**Dependencies:** P5-T1, P5-T3  
**Acceptance Criteria:**
- [ ] CV leads with research operation
- [ ] SOP is framework-first, not motivation-first
- [ ] All links are live and functional
- [ ] Submitted before deadline

---

## PHASE 6: BEYOND 10/10
**Duration:** 18 months  
**Goal:** Cited by practitioners. Referenced in MFE syllabi. Institutional data feeds.  
**Council Mandate:** Chamber 1 leads. Long-term research roadmap.

### P6-T1: Institutional Data Feed Upgrade

**Chamber 1:** Dr. Aris identifies Bloomberg Terminal or Refinitiv as gold standard.  
**Chamber 2:** Xavier evaluates API options. Sasha ensures reliability.

**Task:**
- Replace yfinance/Alpha Vantage with Bloomberg API (if accessible) or Refinitiv Eikon
- Add ICE futures data for OI
- Add CLS FX flow data
- Cost: $$$ — evaluate post-MFE or post-internship

**Owner:** Cursor  
**EV:** High (long-term)  
**Dependencies:** Funding / institutional access  
**Timeline:** Post-NTU MFE or post-first internship

### P6-T2: C++ Execution Engine (Latency)

**Chamber 2:** Viktor designs. Xavier architects.

**Task:**
- Rewrite signal computation core in C++ with Python bindings
- Target: sub-millisecond signal generation
- This is explicitly excluded per locked decisions until post-MFE

**Owner:** Cursor / external contractor  
**EV:** Medium (for credibility, not necessity)  
**Dependencies:** Post-MFE  
**Timeline:** Post-NTU MFE

### P6-T3: Expanded Universe (EM FX, Commodities)

**Chamber 1:** Dr. Aris evaluates EM FX regime logic. Marcus assesses AUM scalability.

**Task:**
- Add AUD/USD, NZD/USD, USD/CAD, USD/CHF
- Add EM pairs: USD/CNH, USD/BRL, USD/MXN
- Add commodity proxies: Brent, gold, copper
- Each pair needs: rate differential, COT equivalent, vol regime

**Owner:** Cursor  
**EV:** Medium  
**Dependencies:** Post-MFE funding  
**Timeline:** Months 12-18

### P6-T4: Published Peer Review

**Chamber 1:** Dr. Aris targets Journal of Financial Data Science or similar.

**Task:**
- Extend SSRN paper with 2+ years of data
- Add peer review feedback
- Submit to academic journal

**Owner:** Kimi (drafting) + academic collaborators  
**EV:** Very High (for fund launch credibility)  
**Dependencies:** P5-T3, 2+ year track record  
**Timeline:** Months 18-24

### P6-T5: Fund Structure Preparation

**Chamber 3:** Coach Silas drives. Claire ensures regulatory language is correct.

**Task:**
- Evaluate Singapore VCC (Variable Capital Company) structure
- Evaluate Dubai DIFC licensing
- Prepare track record audit by third party
- Prepare pitch deck for seed investors

**Owner:** Kimi (strategy) + legal counsel  
**EV:** Critical (for long-term goal)  
**Dependencies:** 2+ year track record, MFE completion, internship experience  
**Timeline:** Months 18-24

---

## CROSS-CUTTING CONCERNS

### Documentation Sync Protocol

After EVERY task completion:
1. Update `TASK.md` with completion status
2. Update `CONTEXT.md` if technical context changed
3. Update `HANDOVER.md` if career context changed
4. Update `PLAN_EXECUTION_10_10.md` with actual vs planned dates
5. Regenerate `.agent/maps/` via git hook or `fx-agent maps`

### Tier Classification for Human Approval

Per OMEGA_PROTOCOL autonomy system:

| Tier | Tasks in This Plan | Approval Required |
|------|-------------------|-------------------|
| Tier 1 (UI/UX) | P2-T2 (UI purge), P2-T4 (copy audit) | Auto-delegate to Cursor |
| Tier 2 (Signal/Logic) | P0-T1, P0-T2, P1-T1, P3-T1, P3-T2, P3-T3, P3-T4 | Auto + approval gate before deploy |
| Tier 3 (Schema/Thresholds) | P1-T3 (audit trail), P4-T2 (backups), P5-T5 (GBP/USD) | Human required |
| Tier 4 (Immutable Ledger) | P0-T2 (trigger application), P1-T2 (parameter docs) | Human + audit trail required |

### Risk Register

| Risk | Mitigation |
|------|-----------|
| Validation engine fix breaks daily run | Run parallel for 1 week before switching |
| Immutable trigger prevents legitimate re-run | Use `ON CONFLICT DO NOTHING` — re-runs are no-ops |
| UI purge makes site too boring | Boring is the goal. Institutional = boring. |
| Parameter derivation reveals overfitting | Sensitivity analysis must show robustness |
| SSRN paper rejected | Submit to 3 journals. Rejection is data. |
| NTU MFE reject | Floor: SMU MFin. Backup: HKUST. |

### Weekly Cadence

| Day | Activity |
|-----|----------|
| Monday | Review weekend pipeline runs. Check alerts. Review validation stats. |
| Tuesday | Kimi strategy session. Task prioritization. Spec writing. |
| Wednesday | Cursor execution day. Delegate queued specs. |
| Thursday | Cursor verification. `fx-agent verify --all`. Regression check. |
| Friday | Council review. Documentation sync. Weekly Substack memo. |
| Weekend | Trading desk (London open). No dev work. |

---

*Last updated: 2026-05-08*  
*Next review: After P0 completion*  
*Governance: Triple-Chamber Council per OMEGA_PROTOCOL.md*  
*Locked decisions: HANDOVER.md Section 8*
