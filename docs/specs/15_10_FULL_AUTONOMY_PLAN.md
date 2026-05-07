# 15/10 — Full Autonomy Plan for FX Regime Lab

> Optimized for a macro research rig (not SaaS). No execution — this is the blueprint only.  
> Deployment targets: **Prefect Cloud** (pipeline orchestration) + **Vercel** (frontend).  
> No Cloudflare. No student language. Institutional-grade safety.

---

## 1. The Difference: FinTree vs. FX Regime Lab

The shared plan assumes a SaaS product with users, auth, payments, and frequent UI deploys. FX Regime Lab is fundamentally different:

| Dimension | FinTree (SaaS) | FX Regime Lab (Research Rig) |
|-----------|---------------|------------------------------|
| **Primary output** | Web app features | Daily regime calls + research briefs |
| **Deploy surface** | Vercel only | Vercel (terminal) + Prefect Cloud (pipeline) |
| **Critical path** | UI correctness | Pipeline correctness + data integrity |
| **Audience** | Students using app | PMs/CIOs reading research |
| **Immutable assets** | None (can fix bugs retroactively) | Regime calls, validation_log, brief_log |
| **Risk of bad deploy** | User frustration | Reputational damage + invalid track record |
| **Feature cadence** | 3–5 UI features/week | 1–2 signals or terminal improvements/week |

This changes everything about autonomy. A bad UI deploy is fixable. A bad pipeline deploy that corrupts the regime call ledger is **permanent damage to credibility.**

---

## 2. The Architecture: "Desk Chief Mode"

Instead of "CEO Mode" (business product), we build **"Desk Chief Mode"** (macro research operation).

The Desk Chief gives directives. The system plans, executes, verifies, and reports — but with safety tiers that reflect the irreversibility of research data.

```
You: "Add a COT-based crowding signal to Layer 2"

System:
  1. triage.py          → "Tier 2. Signal pipeline. Non-breaking."
  2. plan.py            → Research: read COT fetcher, Layer 2, tests
  3. spec.py            → Write implementation spec
  4. validate-spec.py   → "Valid. No immutable tables touched."
  5. predict.py         → "May affect layer2_directional.py tests."
  6. delegate.py        → Cursor implements
  7. verify.py          → pytest 121/121, ruff clean, mypy clean
  8. readiness.py       → "No DB schema changes. No threshold changes."
  9. [PAUSE]            → System asks: "Approve merge?"
  10. You: "yes"
  11. merge.py          → git merge, maps regenerate
  12. deploy-prefect.py → Register new flow version with Prefect
  13. monitor.py        → "Flow registration success. Next run: 06:00 UTC."
  14. report.py         → Human-readable report
```

---

## 3. Safety Tiers (Institutional-Grade)

| Tier | Description | Examples | Autonomy Level |
|------|-------------|----------|---------------|
| **Tier 1 — Terminal Polish** | UI/UX only. No data layer. No pipeline. | New chart component, CSS fixes, mobile layout, copy changes, error state styling | **Fully auto** → plan → delegate → verify → deploy → monitor |
| **Tier 2 — Signal & Logic** | Pipeline changes that don't touch immutable data or Layer 1 thresholds. | New signal (Layer 2/3), new fetcher, new analysis module, test additions, doc updates | **Auto + Approval Gate** → everything up to git merge, then pause for your OK |
| **Tier 3 — Schema & Thresholds** | Changes to data structure, regime logic, or critical parameters. | DB migrations, RLS changes, Layer 1 gate thresholds, pair universe changes, weight changes in composite | **Human Required** → system plans and writes spec, refuses to execute without explicit confirmation |
| **Tier 4 — Immutable Ledger** | Anything that writes to or modifies historical regime calls, validation, or briefs. | Backfill of historical calls, editing validation_log, regenerating past briefs | **Human Required + Audit Trail** → system writes plan, requires signed confirmation (not just "yes") |

**Why Tier 4 exists:** In FinTree, there's no immutable ledger. In FX Regime Lab, the regime call table is the entire credibility foundation. Any backfill or retroactive change must be explicitly approved and logged.

---

## 4. Component Blueprint

### 4.1 `triage.py` — Task Classification Engine

```python
# pipeline/src/auto/triage.py

def classify_task(request: str) -> TaskTier:
    """Classify a natural language request into Tier 1/2/3/4.

    Rules:
    - Contains "page", "component", "style", "CSS", "color", "layout",
      "mobile", "copy", "text" → Tier 1
    - Contains "signal", "fetcher", "analysis", "indicator",
      "layer 2", "layer 3", "composite" → Tier 2
    - Contains "migration", "schema", "RLS", "table", "column",
      "index", "threshold", "layer 1", "weight" → Tier 3
    - Contains "backfill", "retroactive", "reprocess", "edit history",
      "fix past", "regenerate old" → Tier 4
    - Contains "deploy", "production", "prefect", "vercel" → Tier 3
      (deployment requires human judgment)
    """
```

**Output:**
```json
{
  "tier": 2,
  "confidence": 0.94,
  "reasoning": "Request mentions 'signal' and 'Layer 2' — pipeline logic. No DB or threshold changes detected.",
  "suggested_approval": "auto_up_to_merge",
  "immutable_tables_touched": [],
  "estimated_risk": "low"
}
```

### 4.2 `plan.py` — Research & Planning Engine

```python
# pipeline/src/auto/plan.py

def create_plan(request: str, tier: int, maps: dict) -> ImplementationPlan:
    """Kimi's planning function, automated.

    Steps:
    1. Load relevant maps (CODEMAP, SKILLMAP, RULEMAP)
    2. Identify files that will need changes
    3. Read current implementations for pattern matching
    4. Write implementation plan with acceptance criteria
    5. Estimate time and risk
    """
```

**Output:**
```json
{
  "task": "Add COT crowding signal to Layer 2",
  "tier": 2,
  "files_to_read": [
    "pipeline/src/signals/cot.py",
    "pipeline/src/logic/layer2_directional.py",
    "pipeline/tests/test_layer2_directional.py"
  ],
  "files_to_modify": [
    "pipeline/src/signals/cot.py",
    "pipeline/src/logic/layer2_directional.py"
  ],
  "files_to_create": [
    "pipeline/tests/test_cot_crowding.py"
  ],
  "acceptance_criteria": [
    "COT crowding computed as percentile of non-commercial net / OI",
    "Normalized to [-1, 1] using 3-year rolling window",
    "Integrated into Layer 2 composite with weight 0.12",
    "All 121 tests pass",
    "Ruff clean",
    "No Layer 1 thresholds modified"
  ],
  "estimated_time": "25 minutes",
  "risk": "low"
}
```

### 4.3 `spec.py` — Spec Generation

Converts the implementation plan into a delegation spec markdown file that Cursor can execute.

**Output:** `.cursor/delegation/queue/auto-<timestamp>.md`

### 4.4 `validate-spec.py` — Spec Validation

Enhanced version of current `spec-validator.sh`:
- Checks for forbidden imports (`src.ai` in fetchers, etc.)
- Verifies immutable tables are NOT touched for Tier 2/3
- Checks for threshold modifications in Layer 1/2/3
- Validates acceptance criteria are testable

### 4.5 `predict.py` — Failure Prediction

Enhanced version of current `predict-failures.sh`:
- Cross-references files_to_modify against CODEMAP
- Identifies circular dependencies
- Checks if modified files have test coverage
- Flags files that import the modified modules (ripple effects)

### 4.6 `delegate.py` — Cursor Delegation

Wraps `cursor-delegate.sh` with:
- `--auto` flag (no human prompts)
- JSON output parsing (success/failure, files changed, errors)
- Timeout handling (kill after 15 minutes)
- Cost tracking (track API usage per delegation)

### 4.7 `verify.py` — Multi-Stage Verification

```python
def verify(tier: int, files_changed: list[str]) -> VerificationResult:
    """Run verification suite appropriate for the tier.

    Tier 1: npm run build + npm run lint + type check
    Tier 2: pytest + ruff + mypy + npm build (if web files touched)
    Tier 3: pytest + ruff + mypy + npm build + migration dry-run
    Tier 4: Full suite + manual audit checklist
    """
```

### 4.8 `fix.py` — Auto-Fix Loop (Max 3 Attempts)

```python
def auto_fix(failure: str, spec: str, attempt: int) -> FixResult:
    """Generate a fix spec and re-delegate.

    Rules:
    - Parse test failure output
    - Generate fix spec with error context
    - Re-delegate to Cursor
    - Max 3 attempts
    - After 3: escalate to human with full context
    """
```

### 4.9 `readiness.py` — Production Readiness Check

**For Vercel deploys (Tier 1):**
- Bundle size delta (< 50KB acceptable)
- No `console.log` in production build
- No `.env` secrets in build output
- No broken imports
- Accessibility scan (axe-core)
- Mobile viewport check

**For Prefect deploys (Tier 2/3):**
- Flow registration succeeds
- No breaking changes to task signatures
- Environment variables present
- Connection test to Supabase (dry-run)
- Next scheduled run sanity check

### 4.10 `deploy.py` — Deployment Orchestration

```python
def deploy(tier: int, target: str) -> DeployResult:
    """Deploy to the appropriate target.

    Vercel (Tier 1):
      1. Deploy preview: npx vercel
      2. smoke_test(preview_url)
      3. If pass: npx vercel --prod
      4. monitor(production_url, duration=30min)

    Prefect (Tier 2/3):
      1. Register flow: prefect deploy --prefect-file prefect.yaml
      2. Verify registration in Prefect Cloud UI
      3. Trigger test run (dry-run mode)
      4. Monitor next scheduled execution
    """
```

### 4.11 `monitor.py` — Post-Deploy Monitoring

```python
def monitor(target: str, duration_minutes: int = 30) -> MonitorResult:
    """Monitor production health.

    Vercel: Check error logs for 5xx, check build status
    Prefect: Check last flow run status, check DQS score
    Supabase: Check connection health, check RLS
    """
```

### 4.12 `report.py` — Human-Readable Reporting

```
═══════════════════════════════════════════════════
  FX Regime Lab — Autonomous Execution Report
═══════════════════════════════════════════════════

Directive:    "Add COT crowding signal to Layer 2"
Tier:         2 (Signal & Logic)
Status:       ✅ COMPLETE — Awaiting your approval for merge

Execution:
  Planning:        2 min
  Delegation:      18 min
  Verification:    3 min
  Total:           23 min

Results:
  Tests:           121/121 pass
  Ruff:            Clean
  Mypy:            Clean
  Invariants:      0 violations
  Immutable data:  NOT TOUCHED
  Thresholds:      NOT MODIFIED

Files Changed:
  M  pipeline/src/signals/cot.py          (+34 lines)
  M  pipeline/src/logic/layer2_directional.py  (+18 lines)
  A  pipeline/tests/test_cot_crowding.py    (+89 lines)

Readiness:
  DB migration:    Not required
  Prefect deploy:  Flow registration ready
  Risk:            LOW

Next Step:
  Run: fx-agent approve auto-spec-12345
  Or:  fx-agent reject auto-spec-12345 --reason "..."
```

### 4.13 `self-heal.py` — Error Recovery

```python
def self_heal(error: str, context: dict, max_attempts: int = 3) -> HealResult:
    """If health check fails after deploy:

    1. Generate Fix Spec with error context
    2. delegate.py --spec fix-spec.md
    3. verify.py
    4. If pass: re-deploy
    5. If fail after 3 attempts: escalate to human
    """
```

---

## 5. The New CLI: `fx-agent ceo`

```bash
# Tier 1 — Fully autonomous
fx-agent ceo "Add a mobile-responsive layout to the pair desk page"
# → Triage: Tier 1
# → Plan: Read pair desk page, identify breakpoints
# → Spec: Write spec
# → Delegate: Cursor implements
# → Verify: npm build + lint pass
# → Readiness: Bundle +12KB, no secrets
# → Deploy: Preview → smoke test → production
# → Monitor: 30 minutes, 0 errors
# → Report: "Done. Live at /terminal/fx-regime/eurusd"

# Tier 2 — Auto + Approval Gate
fx-agent ceo "Add a COT crowding signal to Layer 2"
# → Triage: Tier 2
# → Plan: Read COT fetcher, Layer 2, tests
# → Spec: Write spec
# → Delegate: Cursor implements
# → Verify: pytest 121/121, ruff clean
# → Readiness: No DB changes, no threshold changes
# → [PAUSE] "Approve merge? (yes/no/review)"
# You: "yes"
# → Merge: git commit, maps regenerate
# → Deploy: Prefect flow registration
# → Monitor: Next run scheduled
# → Report: "Done. Flow registered. Next run: 06:00 UTC."

# Tier 3 — Human Required
fx-agent ceo "Change Layer 1 threshold for BULLISH from 0.3 to 0.25"
# → Triage: Tier 3
# → Plan: Read layer1_gate.py, identify threshold
# → [STOP] "This changes a critical threshold in Layer 1.
#            The regime gate is the foundation of the track record.
#            This requires explicit human approval.
#            
#            Spec written: .cursor/delegation/queue/threshold-change.md
#            
#            To proceed: fx-agent approve --tier-3 threshold-change.md
#            To reject:  fx-agent reject threshold-change.md"
```

---

## 6. Phase Roadmap

### Phase 1: Safety Layer (Priority: CRITICAL)
**Duration:** 2–3 hours of dev time  
**Components:**
- `triage.py` — Task classification
- `readiness.py` — Pre-deploy checks for Vercel + Prefect
- `monitor.py` — Post-deploy health checks
- `report.py` — Human-readable reporting

**Why first:** Without safety, auto-deploy is reckless. A bad deploy to the terminal is embarrassing. A bad deploy to the pipeline corrupts the track record.

**Verification:** Manually run readiness checks 5 times on real deploys. It must catch at least one real issue before Phase 2.

### Phase 2: Orchestrator (Priority: HIGH)
**Duration:** 3–4 hours  
**Components:**
- `plan.py` — Research & planning engine
- `spec.py` — Spec generation from plan
- `validate-spec.py` — Enhanced spec validation
- `predict.py` — Enhanced failure prediction
- `delegate.py` — Auto-delegation wrapper
- `fix.py` — Auto-fix loop (max 3 attempts)

**Why second:** The orchestrator is the brain, but it's useless without the safety layer.

**Verification:** Run the full loop manually 5 times on Tier 1 tasks. Confirm it works end-to-end.

### Phase 3: Auto-Deploy (Priority: MEDIUM)
**Duration:** 2–3 hours  
**Components:**
- `deploy.py` — Vercel + Prefect deployment
- `self-heal.py` — Error recovery loop
- Integration with `fx-agent ceo` command

**Why third:** Only after safety and orchestration are proven.

**Verification:** Auto-deploy 3 Tier 1 tasks to production. Monitor for 30 minutes each. Zero errors.

### Phase 4: Polish & Integration (Priority: LOW)
**Duration:** 1–2 hours  
**Components:**
- Update `.agent/index.json`
- Update skills to include "CEO Mode" workflows
- Update `AGENTS.md` with new autonomy levels
- Add `fx-agent ceo` help text
- Update `self-test.sh` to cover new components

---

## 7. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auto-deploy breaks terminal | Medium | High | smoke-test.py + monitor.py + auto-rollback |
| Auto-deploy breaks pipeline | Low | Critical | Tier 2 stops at approval gate; Tier 3 requires human |
| Infinite fix loop | Low | Medium | Max 3 attempts, then escalate |
| Wrong feature built | Medium | Medium | triage.py + spec approval for Tier 2+ |
| Credential leak in build | Low | Critical | readiness.py scans for API keys, secrets |
| Cost explosion (Cursor API) | Medium | Low | Cost tracking per delegation; caps on auto-fix attempts |
| Immutable ledger corruption | Very Low | Critical | Tier 4 exists; system NEVER auto-touches regime_calls |
| False positive in triage | Medium | Medium | Confidence threshold (e.g., <0.85 → default to human) |

---

## 8. What Makes This Better Than the FinTree Plan

| Improvement | FinTree Plan | FX Regime Lab Plan |
|-------------|-------------|-------------------|
| **Safety tier granularity** | 3 tiers | **4 tiers** — adds Tier 4 for immutable ledger protection |
| **Deploy targets** | Vercel only | **Vercel + Prefect Cloud** — research rig has two surfaces |
| **Readiness checks** | Web-only | **Web + Pipeline** — Prefect flow registration, dry-run, DQS |
| **Monitoring** | Vercel error logs | **Vercel + Prefect + Supabase** — three health signals |
| **Report format** | Generic | **Desk Chief format** — research-specific (DQS, regime stats, track record integrity) |
| **Auto-fix scope** | Any file | **Tier-limited** — Tier 1/2 auto-fix, Tier 3/4 never auto-fix |
| **Immutable data protection** | None | **Explicit Tier 4** — regime calls, validation_log, brief_log are sacred |
| **Cost tracking** | None | **Per-delegation cost tracking** — Cursor API calls are not free |

---

## 9. The Honest Assessment

**Can we build this?** Yes. The components are well-defined. The existing `fx-agent` CLI is the foundation. The maps and skills are already in place.

**Should we build it?** Yes — but only after Phase 1 (safety layer) is bulletproof. A single bad auto-deploy that corrupts the regime call ledger is permanent reputational damage.

**What does it cost?**
- Development: ~8–12 hours of spec → delegate → verify → iterate
- Cursor API costs: ~$5–15 per complex delegation (Tier 2), ~$1–3 per Tier 1
- Maintenance: Low — the system self-documents via maps and reports

**What does it save?**
- Tier 1 tasks: 30–45 min → 10 seconds (99.6% time reduction)
- Tier 2 tasks: 45–60 min → 2 minutes (97% time reduction)
- Tier 3 tasks: No time saved (human required, as it should be)

**The real value:** Not time savings. **Decision bandwidth.** With the system handling Tier 1 and 2, you think about regime classification and macro thesis. Not about whether a CSS class should be `border-[#222]` or `border-[#333]`.

---

## 10. One-Page Decision Tree

```
You give directive
        │
        ▼
   triage.py
        │
    ┌───┴───┐
    ▼       ▼
 Tier 1   Tier 2
 (UI)     (Signal)
    │       │
    ▼       ▼
  FULL    AUTO+
  AUTO    APPROVAL
    │       │
    ▼       ▼
 DEPLOY   MERGE?
    │       │
    ▼       ▼
 REPORT   DEPLOY
    │       │
    └───────┘
        │
    ┌───┴───┐
    ▼       ▼
 Tier 3   Tier 4
 (Schema) (Ledger)
    │       │
    ▼       ▼
 HUMAN   HUMAN+
 REQUIRED  AUDIT
    │       │
    ▼       ▼
 SPEC    SPEC
 READY   READY
    │       │
    ▼       ▼
 WAIT    WAIT
 FOR     FOR
 YOU     YOU
```

---

*This is the blueprint. The foundation is solid. The safety layer is the only gate between "ambitious" and "reckless." Build Phase 1 first. Prove it catches real issues. Then build the rest.*
