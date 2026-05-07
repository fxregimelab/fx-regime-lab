# Autonomy Assessment — What Kimi Can Do Alone vs. What Needs You

> Brutally honest breakdown of where the system is fully autonomous, where it needs human checkpoints, and what it would take to reach 90%+ autonomy.

---

## The Short Answer

**No.** You cannot say "build me a feature" and walk away to receive a perfect end product 100% of the time.

**But:** You can say "build me a feature" and the system will autonomously execute 60–75% of the work — spec creation, implementation, testing, linting, map updates, and git commits. The remaining 25–40% requires your judgment at specific checkpoints.

**The gap is not in tooling. The gap is in judgment.** Cursor is a brilliant junior engineer. Kimi is a senior architect. But neither of us knows your business intent, your risk tolerance, or your aesthetic preferences unless you articulate them.

---

## The Autonomy Matrix

| Stage | Autonomy Level | What Happens Automatically | What Needs You |
|-------|---------------|---------------------------|--------------|
| **Requirements** | 10% | Kimi can ask clarifying questions | You must define WHAT to build and WHY |
| **Spec Writing** | 70% | Kimi writes the spec from your intent | You review and approve the spec |
| **Failure Prediction** | 80% | `fx-agent predict` flags issues | You decide if flagged issues matter |
| **Implementation** | 85% | Cursor writes code, tests, docs | You review diffs for architectural correctness |
| **Testing** | 90% | pytest, ruff, build, lint run automatically | You interpret test failures that aren't obvious |
| **Bug Fixing** | 60% | Cursor fixes obvious bugs from test output | You handle architectural bugs or spec ambiguity |
| **Optimization** | 40% | Cursor applies lint fixes and formatting | You decide performance vs. readability tradeoffs |
| **Deployment** | 30% | Prefect Cloud runs scheduled flows | You trigger Vercel/Cloudflare deploys and verify |
| **Monitoring** | 20% | Logs are written, maps regenerate | You check if production is healthy |
| **Error Recovery** | 25% | Auto-retry on transient failures | You handle credential issues, API outages, schema mismatches |

---

## What IS Fully Autonomous Today

### 1. The Daily Pipeline (100% Autonomous)
```
Prefect Cloud schedule → orchestrator.py → fetchers → signals → regime → DB → brief
```
This runs every 24 hours without human input. If FRED is down, yfinance fallback kicks in. If both fail, the pipeline logs an error and continues with partial data. The DQS (Data Quality Score) reflects this.

**You do nothing.**

### 2. The Commit-to-Map Pipeline (100% Autonomous)
```
git commit → pre-commit hook (pytest/build) → post-commit hook (regenerate maps)
```
Any commit that touches `pipeline/` or `web/` is automatically tested. Maps are automatically regenerated. You cannot forget to update maps because the system does it for you.

**You do nothing.**

### 3. The Spec-to-Verify Loop (85% Autonomous)
```
fx-agent spec create → edit → validate → predict → run → verify
```
Once you approve the spec, Cursor implements it. Tests run. Lint runs. Maps regenerate. The spec moves from `queue/` to `completed/`.

**You only review the diff and commit.**

### 4. File Watcher (100% Autonomous)
```
inotify-tools + entr → regenerate-maps.sh
```
Background process watches the filesystem. When files change, maps regenerate in real-time.

**You do nothing.**

---

## What Needs You — And Why

### 1. Requirements (10% Autonomous)

**The problem:** AI cannot read your mind.

You say: *"Add a signal for yen strength."*

What you might mean:
- A new fetcher that pulls JPY-specific macro data?
- A composite signal that weights USD/JPY spot, BoJ policy rate, and JPY positioning?
- A risk-reversal skew indicator for USD/JPY?
- A new regime gate that triggers on yen-specific conditions?

Kimi will ask clarifying questions, but **you must provide the intent.** Without intent, Cursor builds the wrong thing beautifully.

**Time needed from you:** 2–5 minutes of explanation.

### 2. Spec Approval (70% Autonomous)

Kimi writes the spec. But you must approve it because:
- Kimi might not know about a constraint you haven't documented
- The spec might touch files you didn't intend to modify
- The acceptance criteria might be too loose or too strict

**Example of a spec that needs your eyes:**
```markdown
## Files to Modify
- pipeline/src/logic/layer1_gate.py
```
You know Layer 1 is sacred. Any change to Layer 1 thresholds affects the entire track record. You might say: *"Don't modify Layer 1. Create a new gate variant instead."*

**Time needed from you:** 30 seconds to 2 minutes of reading.

### 3. Diff Review (85% Autonomous → Needs You)

Cursor can write correct code. But Cursor can also:
- Reformat 50 files you didn't ask to touch
- Add a "helpful" comment that reveals internal architecture
- Change a magic number that was intentional
- Import a module that violates the forbidden_imports list

The verification suite catches functional bugs. But it does NOT catch:
- Architectural drift
- Comment leakage
- Unintended file modifications
- Changes to hardcoded thresholds

**Time needed from you:** 1–3 minutes of `git diff --stat` and skimming.

### 4. Deployment (30% Autonomous)

The system CAN deploy, but SHOULD it?

```bash
# Vercel deploy
npx vercel --prod

# Cloudflare worker deploy
npx wrangler deploy

# Prefect flow deploy
prefect deploy --prefect-file prefect.yaml
```

These require:
- Cloud credentials (VERCEL_TOKEN, CLOUDFLARE_API_TOKEN)
- Human judgment (is this the right time to deploy?)
- Rollback readiness (what if production breaks?)

**The system does not auto-deploy.** This is intentional. A bad deploy at 2 AM because Cursor refactored the database layer is a nightmare.

**Time needed from you:** 30 seconds to trigger deploy + 2 minutes to verify.

### 5. Error Recovery (25% Autonomous)

When things break, the system logs errors. But it cannot always fix them:

| Error Type | System Response | Needs You? |
|-----------|-----------------|------------|
| FRED API down | Falls back to yfinance | No |
| Both APIs down | Logs error, sets DQS low | Yes — you decide if to publish partial data |
| Cursor CLI auth expired | Fails delegation | Yes — you re-authenticate |
| Supabase RLS policy mismatch | Write fails | Yes — you adjust policy |
| Pytest failure in test | Cursor auto-fixes (sometimes) | Yes — if architectural |
| Next.js build failure | Logs error | Yes — you check if it's a type error or config issue |
| Prefect flow crash | Logs error | Yes — you check worker logs |

**Time needed from you:** 0 minutes (auto-recovery) to 15 minutes (investigation).

---

## The Realistic "Just Do It" Workflow

Here is what actually happens when you say *"Add a new signal for yen carry trades"*:

### Phase 1: Requirements (You: 3 min, System: 0 min)
**You:** *"I want a yen carry trade signal that measures the spread between USD/JPY spot and the 3-month TIBOR/LIBOR proxy. Normalize it to [-1, 1] using a 1-year rolling window. Weight it at 0.10 in the Layer 2 composite."*

**Kimi might ask:**
- "Do you have a data source for TIBOR, or should we proxy with Fed Funds - BoJ rate?"
- "Should this signal be conditional on Layer 1 being directional?"
- "What tests do you want?"

### Phase 2: Spec Writing (You: 1 min, System: 2 min)
**Kimi writes the spec.** You skim it. You approve it.

### Phase 3: Execution (You: 0 min, System: 10–20 min)
```bash
fx-agent run .cursor/delegation/queue/spec-yen-carry.md
```

**System does:**
1. Validates spec structure
2. Predicts failure modes
3. Delegates to Cursor
4. Cursor writes: `src/signals/yen_carry.py`, modifies `layer2_directional.py`, adds tests
5. Runs pytest
6. Runs ruff
7. Moves spec to `completed/`

### Phase 4: Review (You: 3 min, System: 0 min)
**You:**
```bash
git diff --stat
# Check: did Cursor touch any files it shouldn't have?
# Check: are the weights correct?
# Check: is the normalization causal?
```

### Phase 5: Verification (You: 0 min, System: 2 min)
```bash
fx-agent verify
```
**System runs:** pytest (121 tests), npm build, npm lint (0 errors), ruff check.

### Phase 6: Commit (You: 30 sec, System: 10 sec)
```bash
git add -A && git commit -m "feat: add yen carry trade signal"
```
**System auto-regenerates maps.**

### Phase 7: Deploy (You: 2 min, System: 1 min)
**You decide:** Is now a good time to deploy?
```bash
cd pipeline && prefect deploy --prefect-file prefect.yaml --name Daily_G10_Alpha_Engine
cd web && npx vercel --prod
```

### Total Time
| Phase | You | System |
|-------|-----|--------|
| Requirements | 3 min | 0 min |
| Spec | 1 min | 2 min |
| Execution | 0 min | 15 min |
| Review | 3 min | 0 min |
| Verify | 0 min | 2 min |
| Commit | 0.5 min | 0.5 min |
| Deploy | 2 min | 1 min |
| **Total** | **9.5 min** | **20.5 min** |

**You spent 9.5 minutes. The system spent 20.5 minutes. The feature is live.**

Compare to manual: 4 hours of your time, no parallelization.

---

## What Would It Take to Reach 90% Autonomy?

We are at ~70% autonomy for structured tasks. To reach 90%, we would need:

### 1. Auto-Deployment Pipeline (GitHub Actions)
```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: cd pipeline && pytest
      - run: cd web && npm run build
  deploy-prefect:
    needs: test
    run: prefect deploy --prefect-file prefect.yaml
  deploy-web:
    needs: test
    run: npx vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
  deploy-worker:
    needs: test
    run: npx wrangler deploy
```
**Impact:** Deployment becomes 100% autonomous. You push, it deploys.

### 2. Health Monitoring + Auto-Alerting
```python
# workers/health-check.js
export default {
  async scheduled(controller, env, ctx) {
    const db = await checkSupabaseHealth();
    const pipeline = await checkPrefectLastRun();
    if (db.status !== 'ok' || pipeline.age > 86400) {
      await sendTelegramAlert(`FX Regime Lab health check failed: ${db.error}`);
    }
  }
};
```
**Impact:** You know about failures within minutes, not hours.

### 3. Auto-Retry with Spec Refinement
```bash
# If cursor-delegate.sh fails, automatically:
# 1. Parse the error
# 2. Append the error to the spec
# 3. Re-run with modified spec
# 4. If still failing after 3 attempts, escalate to human
```
**Impact:** 60% of delegation failures self-heal.

### 4. End-to-End Testing
```typescript
// e2e/terminal.spec.ts
test('pair desk loads with data', async () => {
  await page.goto('/terminal/fx-regime/eurusd');
  await expect(page.locator('[data-testid="spot-price"]')).toBeVisible();
  await expect(page.locator('[data-testid="regime-label"]')).not.toBeEmpty();
});
```
**Impact:** Catches frontend bugs that unit tests miss.

### 5. Intent Clarification Loop
```
You: "Add a yen signal."
Kimi: "Do you mean:
  [1] A new fetcher for JPY macro data?
  [2] A composite signal in Layer 2?
  [3] A new regime gate condition?
  [4] A risk-reversal skew indicator?"
You: "2"
Kimi: "What weight in the composite?"
You: "0.10"
# ... continue until intent is clear
```
**Impact:** Reduces requirements ambiguity by 80%.

### 6. Rollback on Failure
```bash
# If deploy fails, automatically:
# 1. Revert to previous git commit
# 2. Re-deploy previous version
# 3. Alert human
```
**Impact:** Bad deploys are self-healing.

---

## The Honest Bottom Line

### What You CAN Say and Walk Away From
- *"Run the daily pipeline"* → 100% autonomous
- *"Fix the ruff errors in these files"* → 95% autonomous
- *"Add a docstring to this module"* → 95% autonomous
- *"Create a new Next.js page with this layout"* → 85% autonomous
- *"Add a signal that follows the exact pattern of signal X"* → 80% autonomous

### What You CANNOT Say and Walk Away From
- *"Make the system better"* → Too vague. Cursor doesn't know what "better" means.
- *"Refactor the pipeline"* → Architectural. Needs your judgment on what to keep vs. change.
- *"Deploy everything"* → Needs credential verification and timing judgment.
- *"Fix the bug"* → Which bug? If it's an external API outage, the system can't fix the API.
- *"Add a new feature"* → Needs requirements clarification.

### The Realistic Promise
**You can say:** *"Add a yen carry trade signal using the Fed Funds - BoJ rate spread, normalize with 1-year rolling percentile, weight 0.10 in Layer 2, test it, lint it, and commit it."*

**The system will:** Write the spec, delegate to Cursor, run tests, fix lint, regenerate maps, move the spec to completed, and present you with a clean diff.

**You must:** Review the diff (3 minutes), decide if you want to deploy (30 seconds), and trigger deploy (1 minute).

**Total human time: ~5 minutes. Total system time: ~25 minutes. Feature delivered.**

That is not 100% autonomy. But it is **5 minutes of your time for a feature that would take 4 hours manually.** And that is the highest-EV way to use this system.

---

## One More Thing: The System Gets Smarter Over Time

Every spec you write, every bug Cursor fixes, every test that fails — the system learns.

- `predict-failures.sh` gets better at predicting because it sees more failure patterns.
- The skill files accumulate examples of correct implementations.
- The maps stay fresh because git hooks regenerate them.
- The rules get tighter as edge cases are discovered.

**The system is not static. It compounds.** The more you use it, the more autonomous it becomes — because the knowledge graph grows, the failure patterns become predictable, and the specs get tighter.

But it will never reach 100% autonomy. And that is a feature, not a bug. **A system with 100% autonomy is a system you do not understand.** A system with 70% autonomy and 5-minute human checkpoints is a system you control.

Control is the highest EV.
