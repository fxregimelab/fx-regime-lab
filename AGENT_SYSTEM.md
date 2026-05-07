# The FX Regime Lab Agent System — Deep Dive

> What we built, why we built it, and how to extract maximum expected value from it for all future development.

---

## 1. WHAT WE BUILT

The agent system is not a gimmick. It is an **operational control layer** that allows one person to maintain a 150-file codebase across Python, TypeScript, SQL, and infrastructure — without context overload or execution bottlenecks.

### 1.1 The Philosophy

| Problem (Before) | Solution (After) |
|------------------|------------------|
| You hold 150 files in working memory | Machine-readable maps (CODEMAP, SKILLMAP, RULEMAP) compress context to ~6,900 tokens |
| You write boilerplate code manually | Spec → Cursor executes → you verify |
| You forget which files touch the database | Semantic map tells you in 200ms |
| You break tests and only find out later | Pre-commit hook blocks the commit |
| You modify a file and maps go stale | Post-commit hook regenerates them automatically |
| You delegate a task and lose track | `fx-agent review` shows completion history |

### 1.2 The Complete Inventory (84 Files)

#### The Unified CLI: `fx-agent`
```
fx-agent init                    # One-time setup
fx-agent status                  # System health + stats
fx-agent spec create <type>      # signal | page | migration
fx-agent spec validate <file>    # Check spec before delegation
fx-agent run <spec.md>           # Delegate to Cursor
fx-agent run --queue             # Process all queued specs
fx-agent verify                  # Full suite (pytest + build + lint + ruff)
fx-agent verify --quick          # Fast (pytest + ruff only)
fx-agent review                  # Show recently completed specs
fx-agent cleanup                 # Archive specs older than 7 days
fx-agent self-test               # 8/8 system health checks
fx-agent maps                    # Regenerate all maps manually
fx-agent predict <spec.md>       # Predict failure modes
fx-agent help                    # Usage reference
```

#### Machine-Readable Maps (Auto-Regenerated)
| Map | Files | Purpose |
|-----|-------|---------|
| `CODEMAP.json` | 148 files | Every source file categorized: pipeline, web, database, deployment |
| `SKILLMAP.json` | 13 skills | Reusable capabilities: quant-math, Supabase-writes, Prefect-deploy, etc. |
| `RULEMAP.json` | 6 rules | Hard constraints: no rounding, Supabase writes only via writer.py, 3-pair lock |
| `SEMANTICMAP.json` | 108 files | Cross-reference: which files import which, function signatures |
| `HOTFILES.md` | 198 files | Recently modified files for quick context |

#### Core Scripts (15 executable scripts)
| Script | Purpose |
|--------|---------|
| `scripts/cursor-delegate.sh` | Wraps `agent --print --yolo` with spec injection and model selection |
| `scripts/cursor-verify.sh` | Post-delegation verification: pytest, npm build, npm lint, ruff check |
| `scripts/kimi-cursor-orchestrator.sh` | Parallel execution of queued specs, auto-retry, session tracking |
| `.agent/scripts/regenerate-maps.sh` | Rebuilds CODEMAP, SKILLMAP, RULEMAP, SEMANTICMAP from source |
| `.agent/scripts/self-test.sh` | 8/8 checks: map integrity, script executability, rule validity, skill validity, git hooks, map regeneration, predictive loader |
| `.agent/scripts/spec-validator.sh` | Validates spec markdown structure (task, files, acceptance criteria) |
| `.agent/scripts/predict-failures.sh` | Analyzes spec against maps to predict what might break |
| `.agent/scripts/file-watcher.sh` | Background process: regenerates maps when files change |
| `.agent/scripts/auto-debug.sh` | Parses test failures and suggests fixes |
| `.agent/scripts/build-semantic-map.sh` | Cross-reference analysis of imports and function calls |
| `.agent/scripts/build-knowledge-graph.sh` | Graphviz DOT generation from semantic relationships |
| `.agent/scripts/predictive-loader.sh` | Loads only the files a spec will need into context |

#### Delegation Infrastructure
| Directory | Purpose |
|-----------|---------|
| `.cursor/delegation/queue/` | Specs waiting to be executed |
| `.cursor/delegation/completed/` | Specs that finished successfully |
| `.cursor/delegation/archive/` | Specs older than 7 days |
| `.cursor/delegation/logs/` | Execution logs |
| `.cursor/delegation/sessions/` | Session tracking |

#### Rules (6 `.mdc` files readable by Cursor)
| Rule | Scope |
|------|-------|
| `FX-Regime-Lab-Core.mdc` | Project identity, 3-pair lock, immutable ledger |
| `Pipeline-Rules.mdc` | Python style, ruff, mypy, causal rolling stats |
| `Frontend-Rules.mdc` | Next.js App Router, Tailwind v4, Swiss Monochrome, KaTeX |
| `Database-Rules.mdc` | Supabase writes via writer.py only, RLS policies, service-role key |
| `Deployment-Rules.mdc` | Prefect Cloud, Cloudflare Worker, Vercel |
| `Session-Start.mdc` | Read AGENTS.md first, token budget, delegation protocol |

#### Skills (13 reusable capabilities)
Each skill is a `SKILL.md` file with instructions, examples, and constraints:
- `quant-math` — Rolling statistics, percentile ranking, Brier scores
- `fx-regime-signal-pipeline` — 3-layer framework implementation
- `fx-regime-supabase-writes` — Database persistence patterns
- `nextjs-frontend` — Page creation, component patterns, data fetching
- `prefect-deploy` — Flow deployment, scheduling, work pools
- `cloudflare-worker` — Edge function patterns, API routes
- `cursor-delegation` — How to write specs that Cursor executes correctly
- `cursor-orchestration` — Multi-spec parallel execution

#### Templates (3 spec templates)
| Template | Use Case |
|----------|----------|
| `pipeline-signal.md` | Add a new signal to the Python pipeline |
| `nextjs-page.md` | Add a new page to the Next.js terminal |
| `db-migration.md` | Add a new Supabase table/column/index |

#### Git Hooks (Auto-Installed)
| Hook | Trigger | Action |
|------|---------|--------|
| `pre-commit` | `git commit` | Runs pytest (pipeline changes) or npm build (web changes). Blocks commit if fails. |
| `post-commit` | `git commit` | Regenerates all maps in background. |
| `post-merge` | `git merge` | Regenerates all maps. |

#### MCP Servers (Configured)
- **Supabase** — Database introspection, query execution
- **GitHub** — PR creation, issue tracking
- **Vercel** — Deployment management
- **Cloudflare** — Worker deployment

---

## 2. WHY WE BUILT IT

### The Fundamental Constraint
> **One operator. 150 files. 4 languages. Zero team.**

Without an agent system, you have three choices:
1. **Work slower** — Context-switch between Python math, Next.js components, SQL migrations, and infrastructure. Every switch costs 15+ minutes of re-orientation.
2. **Work narrower** — Only touch one layer (e.g., only pipeline, ignore frontend). The terminal goes stale. Credibility decays.
3. **Make mistakes** — Forget which files import `writer.py`. Accidentally round a float. Break the build and find out hours later.

The agent system creates a fourth option: **Work faster AND wider AND safer.**

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Kimi      │────▶│  Spec (md)   │────▶│   Cursor    │
│ (Strategy)  │     │              │     │ (Execution) │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                    │
       │                                    ▼
       │                           ┌──────────────┐
       │                           │  Modifies    │
       │                           │  source files│
       │                           └──────────────┘
       │                                    │
       ▼                                    ▼
┌─────────────┐                   ┌──────────────┐
│  fx-agent   │◀──────────────────│  cursor-     │
│  verify     │                   │  verify.sh   │
└─────────────┘                   └──────────────┘
```

**Kimi never writes production code.** Kimi writes specs, researches, plans, and decides. Cursor implements. This separation prevents context corruption — Kimi's strategic context stays clean while Cursor's execution context is loaded with maps and skills.

### The Value Equation

| Without Agent System | With Agent System |
|---------------------|-------------------|
| Adding a new signal: 4 hours | Adding a new signal: 45 min (15 min spec + 30 min Cursor execution + review) |
| Remembering 150 files: impossible | CODEMAP tells you exactly where to look |
| Breaking tests: discovered manually | Pre-commit hook blocks the bad commit |
| Maps go stale: always | Maps regenerate automatically on every commit |
| Delegation tracking: spreadsheet or memory | `fx-agent review` shows history |
| Failure prediction: guesswork | `fx-agent predict` analyzes spec against codebase |

---

## 3. HOW TO USE IT FOR HIGHEST EV

### 3.1 The Development Velocity Loop

This is the core loop. Master this and you can add features at 3–5x the speed of manual development.

```bash
# Step 1: Create a spec from template (15 seconds)
fx-agent spec create signal
# → Creates .cursor/delegation/queue/spec-<timestamp>.md

# Step 2: Edit the spec (5–15 minutes)
vim .cursor/delegation/queue/spec-<timestamp>.md

# Step 3: Validate the spec (5 seconds)
fx-agent spec validate .cursor/delegation/queue/spec-<timestamp>.md

# Step 4: Predict failure modes (10 seconds)
fx-agent predict .cursor/delegation/queue/spec-<timestamp>.md

# Step 5: Delegate to Cursor (5–30 minutes, depending on spec)
fx-agent run .cursor/delegation/queue/spec-<timestamp>.md

# Step 6: Review what Cursor built
fx-agent review

# Step 7: Verify everything passes
fx-agent verify        # full suite
# or
fx-agent verify --quick  # fast (pytest + ruff only)

# Step 8: Commit (hooks auto-update maps)
git add -A && git commit -m "feat: add new signal"
```

**Total time for a new signal:** ~45 minutes vs. ~4 hours manually.

### 3.2 What Makes a Good Spec

A spec is a markdown file with four sections. The quality of the spec determines the quality of Cursor's output.

```markdown
# Spec: Add RSI-14 Signal to Layer 2

## Task
Add a relative strength index (RSI-14) signal to the Layer 2 directional
framework. The signal should be computed from daily FX spot closes and
normalized to [-1, 1].

## Files to Modify
- `pipeline/src/signals/rsi.py` — new file
- `pipeline/src/logic/layer2_directional.py` — integrate RSI into composite
- `pipeline/tests/test_layer2_directional.py` — add test cases
- `docs/SIGNAL_DEFINITIONS.md` — document the math

## Acceptance Criteria
- [ ] RSI-14 computed causally (today's RSI uses t-1 history only)
- [ ] Normalized to [-1, 1] using 3-year rolling percentile
- [ ] Integrated into Layer 2 composite with weight 0.15
- [ ] Tests pass: `cd pipeline && pytest tests/test_layer2_directional.py -v`
- [ ] Ruff clean: `cd pipeline && ruff check .`
- [ ] No rounding. Use np.float64 explicitly.

## Context
- RSI formula: 100 - (100 / (1 + RS)), RS = avg gain / avg loss
- Look at `src/signals/volatility.py` for causal rolling pattern
- Look at `src/logic/layer2_directional.py:42` for composite integration
```

**Why this spec is high-EV:**
- **Explicit file list** — Cursor doesn't waste time searching
- **Explicit acceptance criteria** — Verification is automatic
- **Context references** — Cursor knows exactly which patterns to follow
- **No ambiguity** — "causal" and "np.float64" prevent common mistakes

**Low-EV spec (what NOT to write):**
```markdown
# Add RSI

Make an RSI signal. It should work like the other signals.
```
This spec will fail because Cursor will:
- Not know which files to touch
- Not know the normalization convention
- Not know the weight in the composite
- Probably round floats
- Probably use non-causal rolling

### 3.3 The Queue Processing Mode

If you have multiple specs ready, process them in parallel:

```bash
# Put all specs in queue/
fx-agent spec create signal  # spec-A
fx-agent spec create page    # spec-B
fx-agent spec create migration # spec-C

# Edit all three specs...

# Process them in parallel
fx-agent run --queue
```

The orchestrator (`kimi-cursor-orchestrator.sh`) will:
1. Run up to 3 specs in parallel
2. Auto-retry failed specs once
3. Track session state
4. Move completed specs to `completed/`
5. Log everything to `logs/`

**EV of queue mode:** You write 3 specs in 30 minutes, then walk away. When you return, all three are implemented and verified. Manual approach: 3 × 4 hours = 12 hours of context switching.

### 3.4 The Review and Cleanup Loop

```bash
# See what Cursor built recently
fx-agent review

# Output:
#   ✓ spec-1778155924.md  (2h ago)
#   ✓ spec-1778156001.md  (5h ago)
#   ✓ test-delegation.md  (1d ago)

# Archive old specs to keep queue clean
fx-agent cleanup

# Output:
#   Archived 3 old spec(s) to .cursor/delegation/archive/
#   Kept 2 recent spec(s) in queue
```

**Why this matters:** A cluttered queue creates decision fatigue. You look at 20 old specs and don't know which ones matter. Cleanup forces you to either execute or archive. Clean queue = clear priorities.

### 3.5 The Verification Strategy

| When to Use | Command | What It Checks | Time |
|-------------|---------|---------------|------|
| After every delegation | `fx-agent verify --quick` | pytest + ruff | ~30s |
| Before every commit | `fx-agent verify` | pytest + build + lint + ruff | ~2min |
| Before pushing to main | `fx-agent verify` + manual check | Full suite + read diff | ~5min |
| After major refactor | `fx-agent verify` + `fx-agent self-test` | Everything + agent health | ~3min |

**The pre-commit hook already runs pytest/build automatically.** The `fx-agent verify` is for your own confidence before you stage changes.

### 3.6 The Map Regeneration Strategy

Maps regenerate automatically on git commit/merge. But sometimes you need them immediately:

```bash
# After a big refactor, regenerate manually
fx-agent maps

# Check if maps are stale
fx-agent status

# Output:
#   ✓ Maps fresh (45s old)
# or:
#   ⚠ Maps stale (3700s old) — run 'fx-agent maps'
```

**Why maps matter:** When you delegate a spec, Cursor loads the maps into context. Stale maps = wrong file references = Cursor modifies the wrong files = wasted time.

### 3.7 The Failure Prediction Strategy

Before delegating a complex spec, predict what will break:

```bash
fx-agent predict .cursor/delegation/queue/my-big-spec.md
```

This script:
1. Parses the spec for file references
2. Checks if those files exist in CODEMAP
3. Identifies cross-file dependencies
4. Flags potential issues (missing tests, no docs reference, etc.)

**EV of prediction:** Catching a missing test file in 5 seconds is infinitely better than Cursor implementing the feature, you reviewing it, and then realizing there's no test coverage.

---

## 4. TACTICAL PLAYBOOK BY TASK TYPE

### Adding a New Signal (Pipeline)
```bash
fx-agent spec create signal
# Edit: define math, files, tests, docs
fx-agent run .cursor/delegation/queue/spec-*.md
fx-agent verify --quick
```

### Adding a New Terminal Page (Frontend)
```bash
fx-agent spec create page
# Edit: route, components, data fetching, styling
fx-agent run .cursor/delegation/queue/spec-*.md
fx-agent verify  # includes npm run build
```

### Adding a Database Migration
```bash
fx-agent spec create migration
# Edit: table schema, indexes, RLS policies, types
fx-agent run .cursor/delegation/queue/spec-*.md
# Manually run: supabase db reset (to validate migration)
fx-agent verify --quick
```

### Debugging a Test Failure
```bash
# The test failed. Don't fix it manually yet.
cd pipeline && pytest tests/test_layer3_execution.py -v --tb=short

# Write a debug spec
fx-agent spec create signal  # or just write a custom spec
cat > .cursor/delegation/queue/debug.md << 'EOF'
# Debug: Fix Layer 3 Execution Test

## Task
Fix the failing test in tests/test_layer3_execution.py::test_stop_level.
The test expects stop level 1.0045 but gets 1.0043.

## Files to Modify
- pipeline/tests/test_layer3_execution.py
- pipeline/src/logic/layer3_execution.py (if the implementation is wrong)

## Acceptance Criteria
- [ ] pytest tests/test_layer3_execution.py::test_stop_level passes
- [ ] No other tests break

## Context
Run: cd pipeline && pytest tests/test_layer3_execution.py::test_stop_level -v
EOF

fx-agent run .cursor/delegation/queue/debug.md
```

### Refactoring a Core Module
```bash
# NEVER refactor without a spec. Refactors are high-risk.
cat > .cursor/delegation/queue/refactor.md << 'EOF'
# Refactor: Extract Rate Signal Logic

## Task
Extract the rate signal normalization from layer2_directional.py into
a new module src/signals/rate_norm.py. No behavior changes.

## Files to Modify
- pipeline/src/signals/rate_norm.py (new)
- pipeline/src/logic/layer2_directional.py
- pipeline/tests/test_layer2_directional.py

## Acceptance Criteria
- [ ] All 121 tests pass
- [ ] Ruff clean
- [ ] No behavior changes (same outputs for same inputs)
EOF

fx-agent run .cursor/delegation/queue/refactor.md
fx-agent verify
```

---

## 5. THE ANTI-PATTERNS (EV Destroyers)

| Anti-Pattern | Why It Destroys Value | The Fix |
|--------------|----------------------|---------|
| **Writing code manually when a spec would work** | You burn 2–4 hours on boilerplate that Cursor does in 20 min | Always spec first. Only write code manually for architectural decisions. |
| **Delegating without validating the spec** | Cursor implements the wrong thing. You review it, reject it, re-delegate. Waste. | `fx-agent spec validate` before `fx-agent run` |
| **Skipping verification after delegation** | Cursor might have broken a test you didn't look at. You find out later. | `fx-agent verify --quick` is 30 seconds. Do it. |
| **Letting the queue grow indefinitely** | 20 old specs = decision fatigue = paralysis | `fx-agent cleanup` weekly. Archive or execute. |
| **Not reading Cursor's diff before committing** | Cursor might have added a docstring (good) or reformatted 50 files (bad) | Always `git diff --stat` before commit |
| **Writing vague specs** | "Make it work like the other signals" means Cursor guesses. Guessing = rework. | Explicit file list, explicit math, explicit acceptance criteria |
| **Ignoring map freshness** | Stale maps = Cursor touches wrong files | `fx-agent status` shows map age. Regenerate if >1 hour. |
| **Not using `--yolo` for trusted specs** | `--yolo` skips confirmation prompts. For specs you've validated, this saves minutes. | Validate once, then `fx-agent run` uses `--yolo` automatically |

---

## 6. ADVANCED: MULTI-SPEC WORKFLOWS

### The Sprint Workflow
```bash
# Monday: Plan the week
# Write 5 specs for the week's work
fx-agent spec create signal  # Spec 1: Add new fetcher
fx-agent spec create signal  # Spec 2: Modify Layer 1 threshold
fx-agent spec create page    # Spec 3: New terminal component
fx-agent spec create page    # Spec 4: Mobile responsive layout
fx-agent spec create migration # Spec 5: New validation table column

# Tuesday morning: Process all at once
fx-agent run --queue

# Tuesday afternoon: Review, fix, verify
fx-agent review
fx-agent verify

# Wednesday: Commit everything
git add -A && git commit -m "sprint: 5 specs implemented"
```

**EV of sprint workflow:** One 3-hour block on Tuesday replaces 5 × 4-hour manual sessions = 20 hours → 3 hours.

### The Hotfix Workflow
```bash
# Production bug found. Don't panic.
# Write a focused debug spec in 2 minutes.
cat > .cursor/delegation/queue/hotfix.md << 'EOF'
# HOTFIX: Fix COT Fetcher Date Parsing

## Task
The COT fetcher fails on weeks where the CFTC report is delayed.
Handle missing dates gracefully by falling back to the previous week.

## Files to Modify
- pipeline/src/fetchers/cot.py
- pipeline/tests/test_fetchers.py

## Acceptance Criteria
- [ ] pytest passes
- [ ] Ruff clean
- [ ] Graceful fallback when report is delayed
EOF

fx-agent run .cursor/delegation/queue/hotfix.md
fx-agent verify --quick
git add -A && git commit -m "hotfix: COT delayed report handling"
```

### The Research Workflow
```bash
# You have a hypothesis: "RVOL rank >80 predicts regime shift"
# Don't code it yet. Spec it, delegate it, validate it.

fx-agent spec create signal
cat > .cursor/delegation/queue/research-rvol-regime.md << 'EOF'
# Research: RVOL-Regime Shift Signal

## Task
Add a research-only signal that computes the probability of regime shift
within 5 days when RVOL rank >80. Do NOT integrate into production pipeline.

## Files to Modify
- pipeline/src/research/rvol_regime_shift.py (new)
- pipeline/notebooks/rvol_analysis.ipynb (new, optional)

## Acceptance Criteria
- [ ] Signal computes conditional probability P(regime_shift | rvol_rank > 80)
- [ ] Uses historical data from validation_log
- [ ] Outputs markdown report with statistics
- [ ] Does NOT modify production pipeline files
EOF

fx-agent run .cursor/delegation/queue/research-rvol-regime.md
# Review results. If promising, write a SECOND spec to integrate into production.
```

**Why research specs are high-EV:** They let you test hypotheses without risking production stability. Cursor builds the analysis. You review the numbers. Only integrate if the edge is real.

---

## 7. MAINTENANCE AND HEALTH

### Weekly Maintenance (5 minutes)
```bash
fx-agent self-test        # Verify all 8 checks pass
fx-agent cleanup          # Archive old specs
fx-agent status           # Check map freshness, queue size
```

### Monthly Maintenance (15 minutes)
```bash
# Review the knowledge graph
open .agent/graph/codebase.dot

# Check if any skills are stale
ls -lt .cursor/skills/*/SKILL.md

# Review rules for accuracy
cat .cursor/rules/FX-Regime-Lab-Core.mdc

# Update .agent/index.json if new scripts were added
```

### When Something Breaks
```bash
# Step 1: Check system health
fx-agent self-test

# Step 2: Check if maps are stale
fx-agent status

# Step 3: Regenerate maps
fx-agent maps

# Step 4: If a script fails, check syntax
bash -n scripts/cursor-verify.sh

# Step 5: If delegation fails, check Cursor CLI
agent --version

# Step 6: If tests fail, run individually
cd pipeline && pytest tests/test_layer1_gate.py -v --tb=short
```

---

## 8. THE EV MATH

| Activity | Manual Time | Agent System Time | Time Saved |
|----------|-------------|-------------------|------------|
| Add new signal | 4 hours | 45 min | 3h 15m (81%) |
| Add new terminal page | 3 hours | 40 min | 2h 20m (78%) |
| Fix test failure | 1 hour | 20 min | 40m (67%) |
| Refactor core module | 6 hours | 1.5 hours | 4.5h (75%) |
| Write 3 specs in parallel | 12 hours | 3 hours | 9h (75%) |
| Keep maps updated | Manual tracking | Automatic | 100% |
| Pre-commit verification | Manual run | Automatic | 100% |

**Conservative estimate:** The agent system saves ~75% of development time on structured tasks. For a codebase that requires ~20 hours/week of maintenance and feature work, this is **15 hours saved per week** — or roughly **750 hours per year**.

But time savings is not the real EV. The real EV is:

1. **Velocity compounds.** A feature that takes 45 minutes gets built. A feature that takes 4 hours gets deferred indefinitely. The agent system converts "deferred" into "shipped."

2. **Quality is enforced.** Pre-commit hooks, spec validation, and automatic verification mean bugs are caught before they reach production. The cost of a production bug in a public research operation is reputational death.

3. **Context is preserved.** Maps and skills mean you can step away for a week and return without losing state. The system documents itself.

4. **Delegation scales.** You are one person. With the agent system, you have two agents (Kimi + Cursor) working in parallel. This is the closest thing to a team without hiring.

---

## 9. ONE-PAGE CHEAT SHEET

```bash
# Daily
fx-agent status                    # 5s — check health

# When you need to build something
fx-agent spec create <type>        # 15s — create spec
vim .cursor/delegation/queue/*.md  # 5–15min — edit spec
fx-agent spec validate <file>      # 5s — check spec
fx-agent predict <file>            # 10s — predict failures
fx-agent run <file>                # 5–30min — delegate to Cursor
fx-agent verify --quick            # 30s — check tests

# When you have multiple specs
fx-agent run --queue               # parallel execution

# Weekly
fx-agent review                    # see completed specs
fx-agent cleanup                   # archive old specs
fx-agent self-test                 # 8/8 health checks

# Emergency
fx-agent maps                      # regenerate maps
fx-agent verify                    # full verification
```

---

*The agent system is not the product. The agent system is the factory that builds the product. A well-run factory lets you focus on design, not assembly.*
