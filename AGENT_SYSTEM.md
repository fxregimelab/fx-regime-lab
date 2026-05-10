# The FX Regime Lab Agent System — Deep Dive

> What we built, why we built it, and how to extract maximum expected value from it for all future development.

---

## 1. WHAT WE BUILT

The agent system is not a gimmick. It is an **operational control layer** that allows one person to maintain a 150-file codebase across Python, TypeScript, SQL, and infrastructure — without context overload or execution bottlenecks.

### 1.1 The Philosophy

| Problem (Before) | Solution (After) |
|------------------|------------------|
| You hold 150 files in working memory | Subagent exploration compresses context to targeted investigations |
| You write boilerplate code manually | Spec → Subagent executes → you verify |
| You break tests and only find out later | Pre-commit hook blocks the commit |
| You modify a file and lose track of side effects | Subagents analyze cross-file dependencies before changing code |

### 1.2 The Complete Inventory

#### Kimi Subagent Types
```
Agent(subagent_type="explore")   # Fast codebase exploration (read-only)
Agent(subagent_type="coder")     # Cross-file implementation + commands
Agent(subagent_type="plan")      # Architecture planning before implementation
```

#### When to Use Each Type
| Type | Best For | Example |
|------|----------|---------|
| `explore` | Finding files, tracing imports, understanding modules | "How does the rate signal flow from fetcher to Layer 2?" |
| `coder` | Multi-file edits, running tests, debugging | "Add a new COT fetcher with tests and integrate into composite" |
| `plan` | Architecture decisions, trade-off analysis | "Should we add Redis caching or stay stateless?" |

#### Verification Commands
| Command | Purpose | Time |
|---------|---------|------|
| `cd pipeline && pytest` | Full test suite | ~90s |
| `cd pipeline && ruff check .` | Python lint | ~5s |
| `cd pipeline && mypy .` | Type check | ~30s |
| `cd web && npm run build` | Frontend build | ~30s |
| `cd web && npm run lint` | Frontend lint | ~10s |

#### Git Hooks (Auto-Installed)
| Hook | Trigger | Action |
|------|---------|--------|
| `pre-commit` | `git commit` | Runs pytest (pipeline changes) or npm build (web changes). Blocks commit if fails. |

---

## 2. WHY WE BUILT IT

### The Fundamental Constraint
> **One operator. 150 files. 4 languages. Zero team.**

Without subagents, you have three choices:
1. **Work slower** — Context-switch between Python math, Next.js components, SQL migrations, and infrastructure. Every switch costs 15+ minutes of re-orientation.
2. **Work narrower** — Only touch one layer (e.g., only pipeline, ignore frontend). The terminal goes stale. Credibility decays.
3. **Make mistakes** — Forget which files import `writer.py`. Accidentally round a float. Break the build and find out hours later.

Subagents create a fourth option: **Work faster AND wider AND safer.**

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Kimi      │────▶│    Spec      │────▶│   Kimi      │
│ (Strategy)  │     │   (plan.md)  │     │  Subagent   │
└─────────────┘     └──────────────┘     │ (Execution) │
       │                                  └─────────────┘
       │                                         │
       │                                         ▼
       │                                ┌──────────────┐
       │                                │  Modifies    │
       │                                │  source files│
       │                                └──────────────┘
       │                                         │
       ▼                                         ▼
┌─────────────┐                       ┌──────────────┐
│   pytest    │◀──────────────────────│   verify     │
│   + build   │                       │  (manual)    │
└─────────────┘                       └──────────────┘
```

**Kimi writes specs, researches, plans, and decides.** For complex multi-file work, a Kimi subagent implements with full context of the codebase. For simple fixes, Kimi executes directly. This separation prevents context corruption — strategic context stays clean while execution context is loaded with cross-file dependencies.

### The Value Equation

| Without Subagents | With Subagents |
|---------------------|-------------------|
| Adding a new signal: 4 hours | Adding a new signal: 45 min (15 min spec + 30 min subagent execution + review) |
| Remembering 150 files: impossible | Exploration agent finds exactly where to look |
| Breaking tests: discovered manually | Pre-commit hook blocks the bad commit |
| Refactoring with side effects: risky | Subagent analyzes all callers before modifying |

---

## 3. HOW TO USE IT FOR HIGHEST EV

### 3.1 The Development Velocity Loop

This is the core loop. Master this and you can add features at 3–5x the speed of manual development.

```bash
# Step 1: Create a spec from template (15 seconds)
# Write a markdown plan: what to build, which files, acceptance criteria

# Step 2: Edit the spec (5–15 minutes)
# vim plan.md

# Step 3: Validate the approach (5 seconds)
# Use Agent(subagent_type="explore") to verify file references exist

# Step 4: Implement (5–30 minutes, depending on spec)
# Use Agent(subagent_type="coder") with the spec as prompt

# Step 5: Review what the subagent built
# git diff --stat

# Step 6: Verify everything passes
cd pipeline && pytest              # full suite
# or
cd pipeline && pytest -q --tb=short  # fast

# Step 7: Commit (hook auto-runs tests)
git add -A && git commit -m "feat: add new signal"
```

**Total time for a new signal:** ~45 minutes vs. ~4 hours manually.

### 3.2 What Makes a Good Spec

A spec is a markdown file with four sections. The quality of the spec determines the quality of the subagent's output.

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
- **Explicit file list** — Subagent doesn't waste time searching
- **Explicit acceptance criteria** — Verification is automatic
- **Context references** — Subagent knows exactly which patterns to follow
- **No ambiguity** — "causal" and "np.float64" prevent common mistakes

**Low-EV spec (what NOT to write):**
```markdown
# Add RSI

Make an RSI signal. It should work like the other signals.
```
This spec will fail because the subagent will:
- Not know which files to touch
- Not know the normalization convention
- Not know the weight in the composite
- Probably round floats
- Probably use non-causal rolling

### 3.3 Parallel Exploration Mode

If you have multiple independent questions, launch multiple explore agents in parallel:

```bash
# Agent 1: investigate auth module
# Agent 2: investigate database schema
# Agent 3: investigate frontend routing
```

Each agent returns findings independently. You synthesize the results.

**EV of parallel mode:** You get 3 investigations in the time of 1 sequential investigation.

### 3.4 The Review and Verification Loop

```bash
# See what changed
git diff --stat

# Run targeted tests
cd pipeline && pytest tests/test_layer3_execution.py -v --tb=short

# Run full suite before commit
cd pipeline && pytest
```

**Why this matters:** Subagents are precise but not infallible. Always review the diff and run tests. The pre-commit hook is the final safety net.

### 3.5 The Verification Strategy

| When to Use | Command | What It Checks | Time |
|-------------|---------|---------------|------|
| After subagent delegation | `pytest -q --tb=short` | pytest only | ~30s |
| Before every commit | `pytest` + `ruff check .` | Full python suite | ~90s |
| Before pushing to main | `pytest` + `npm run build` | Everything | ~2min |
| After major refactor | `pytest` + `mypy .` | Everything + types | ~3min |

**The pre-commit hook already runs pytest/build automatically.** The manual verification is for your own confidence before you stage changes.

---

## 4. TACTICAL PLAYBOOK BY TASK TYPE

### Adding a New Signal (Pipeline)
```bash
# 1. Write a spec (plan.md)
# 2. Explore to verify file references:
#    Agent(subagent_type="explore"): "Find all files that compute signals"
# 3. Delegate implementation:
#    Agent(subagent_type="coder"): "Implement spec in plan.md"
# 4. Verify
cd pipeline && pytest -q --tb=short
```

### Adding a New Terminal Page (Frontend)
```bash
# 1. Write a spec
# 2. Explore to verify component patterns
# 3. Delegate implementation
# 4. Verify
cd web && npm run build
```

### Adding a Database Migration
```bash
# 1. Write a spec
# 2. Explore to verify migration patterns
# 3. Delegate implementation
# 4. Manually run: supabase db reset (to validate migration)
# 5. Verify
cd pipeline && pytest -q --tb=short
```

### Debugging a Test Failure
```bash
# The test failed. Don't fix it manually yet.
cd pipeline && pytest tests/test_layer3_execution.py -v --tb=short

# Write a debug spec and delegate to subagent:
# Agent(subagent_type="coder"): "Fix test_stop_level in 
#   tests/test_layer3_execution.py. Expected 1.0045, got 1.0043.
#   Check layer3_execution.py implementation."
```

### Refactoring a Core Module
```bash
# NEVER refactor without a spec. Refactors are high-risk.
# Write spec: "Extract rate signal normalization from layer2_directional.py 
#   into src/signals/rate_norm.py. No behavior changes."
# Delegate to subagent
# Verify: All 219 tests pass
```

---

## 5. THE ANTI-PATTERNS (EV Destroyers)

| Anti-Pattern | Why It Destroys Value | The Fix |
|--------------|----------------------|---------|
| **Writing code manually when a spec would work** | You burn 2–4 hours on boilerplate that a subagent does in 20 min | Always spec first. Only write code manually for architectural decisions. |
| **Delegating without a clear spec** | Subagent implements the wrong thing. You review it, reject it, re-delegate. Waste. | Write explicit file list, math, and acceptance criteria before delegating. |
| **Skipping verification after delegation** | Subagent might have broken a test you didn't look at. You find out later. | `pytest -q --tb=short` is 30 seconds. Do it. |
| **Writing vague specs** | "Make it work like the other signals" means the subagent guesses. Guessing = rework. | Explicit file list, explicit math, explicit acceptance criteria |
| **Not reading the diff before committing** | Subagent might have added a docstring (good) or reformatted 50 files (bad) | Always `git diff --stat` before commit |
| **Launching subagents without context** | Subagent has no project context, makes wrong assumptions | Always include relevant file paths and conventions in the prompt |

---

## 6. ADVANCED: MULTI-SPEC WORKFLOWS

### The Sprint Workflow
```bash
# Monday: Plan the week
# Write 3 specs for the week's work
# Spec 1: Add new fetcher
# Spec 2: Modify Layer 1 threshold
# Spec 3: New terminal component

# Tuesday morning: Process all at once
# Launch 3 coder subagents in parallel (if tasks are independent)

# Tuesday afternoon: Review, fix, verify
pytest

# Wednesday: Commit everything
git add -A && git commit -m "sprint: 3 specs implemented"
```

**EV of sprint workflow:** One 3-hour block on Tuesday replaces 5 × 4-hour manual sessions = 20 hours → 3 hours.

### The Hotfix Workflow
```bash
# Production bug found. Don't panic.
# Write a focused debug spec in 2 minutes.
# Delegate to subagent immediately.
# Verify and commit.
```

### The Research Workflow
```bash
# You have a hypothesis: "RVOL rank >80 predicts regime shift"
# Don't code it yet. Spec it, delegate it, validate it.

# Write spec:
# "Add a research-only signal that computes the probability of regime shift
# within 5 days when RVOL rank >80. Do NOT integrate into production pipeline."

# Delegate to explore agent first to understand validation_log schema.
# Then delegate to coder agent to implement the analysis.
# Review results. If promising, write a SECOND spec to integrate into production.
```

**Why research specs are high-EV:** They let you test hypotheses without risking production stability. Subagents build the analysis. You review the numbers. Only integrate if the edge is real.

---

## 7. MAINTENANCE AND HEALTH

### Weekly Maintenance (5 minutes)
```bash
cd pipeline && pytest -q              # verify tests still pass
git status                            # check for uncommitted work
git log --oneline -10                 # review recent commits
```

### When Something Breaks
```bash
# Step 1: Run targeted test
cd pipeline && pytest tests/test_layer1_gate.py -v --tb=short

# Step 2: If tests fail, explore to find root cause
# Agent(subagent_type="explore"): "Trace why test_X fails"

# Step 3: Fix via subagent or directly
# Agent(subagent_type="coder"): "Fix the failing test"

# Step 4: Verify
pytest
```

---

## 8. THE EV MATH

| Activity | Manual Time | Subagent Time | Time Saved |
|----------|-------------|---------------|------------|
| Add new signal | 4 hours | 45 min | 3h 15m (81%) |
| Add new terminal page | 3 hours | 40 min | 2h 20m (78%) |
| Fix test failure | 1 hour | 20 min | 40m (67%) |
| Refactor core module | 6 hours | 1.5 hours | 4.5h (75%) |
| Write 3 specs in parallel | 12 hours | 3 hours | 9h (75%) |
| Pre-commit verification | Manual run | Automatic | 100% |

**Conservative estimate:** Subagents save ~75% of development time on structured tasks. For a codebase that requires ~20 hours/week of maintenance and feature work, this is **15 hours saved per week** — or roughly **750 hours per year**.

But time savings is not the real EV. The real EV is:

1. **Velocity compounds.** A feature that takes 45 minutes gets built. A feature that takes 4 hours gets deferred indefinitely. Subagents convert "deferred" into "shipped."

2. **Quality is enforced.** Pre-commit hooks, spec discipline, and automatic verification mean bugs are caught before they reach production. The cost of a production bug in a public research operation is reputational death.

3. **Context is preserved.** Specs and tests document intent. You can step away for a week and return without losing state.

4. **Delegation scales.** You are one person. With subagents, you have parallel execution capacity. This is the closest thing to a team without hiring.

---

## 9. ONE-PAGE CHEAT SHEET

```bash
# Daily
cd pipeline && pytest -q            # 30s — verify tests pass

# When you need to build something
# 1. Write a spec (plan.md) — 5-15min
# 2. Explore to verify references — Agent(subagent_type="explore")
# 3. Delegate to coder subagent — Agent(subagent_type="coder")
# 4. Review diff — git diff --stat
# 5. Verify — pytest -q --tb=short

# When you have multiple questions
# Launch multiple explore agents in parallel

# Weekly
git log --oneline -10               # review commits
pytest                              # full suite

# Emergency
# Explore first, then fix, then verify
```

---

*The agent system is not the product. The agent system is the factory that builds the product. A well-run factory lets you focus on design, not assembly.*
