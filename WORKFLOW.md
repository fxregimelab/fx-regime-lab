# FX Regime Lab — What We Built, Why, and How to Use It

> Strategic inventory of the complete system as of 14/10.  
> This document answers: What do we have? Why did we build it? What did it achieve? How do we extract maximum expected value from it?

---

## 1. THE COMPLETE SYSTEM INVENTORY

### Layer 0: Data Infrastructure
| Component | Technology | What It Does |
|-----------|-----------|--------------|
| **FRED Fetcher** | Python / `requests` | Pulls Treasury yields (2Y, 10Y), rate differentials for EUR/USD, USD/JPY, USD/INR |
| **CFTC COT Fetcher** | Python / `pandas` | Parses CFTC Commitment of Traders reports, extracts non-commercial net positioning |
| **FX Spot Fetcher** | Python / Alpha Vantage + yfinance fallback | Daily closes for all 3 pairs |
| **Volatility Fetcher** | Python / Yahoo Finance | Realized vol (20D), implied vol (30D), risk reversal skew |
| **Open Interest Fetcher** | Python / CME scraper | Futures OI deltas by asset class |
| **Macro Calendar** | Python / ForexFactory XML | Upcoming central bank events, CPI, payrolls |
| **Substack RSS** | Python / `feedparser` | Pulls published memos for cross-referencing |

### Layer 1: The Signal Pipeline (Python)
| Module | Files | Purpose |
|--------|-------|---------|
| `src/logic/layer1_gate.py` | ~214 lines | **Regime Gate**: Determines macro environment from rate momentum, CB posture, growth divergence. Outputs: `BULLISH`, `BEARISH`, `NEUTRAL`, `VOL_EXPANDING` |
| `src/logic/layer2_directional.py` | ~156 lines | **Directional Signal**: COT percentile ranking, crowding ramp, conviction multiplier (1–5), Marcus invalidation |
| `src/logic/layer3_execution.py` | ~234 lines | **Timing & Entry**: RVOL rank, skew reversal, MIE proxy, stop levels, position sizing (`FULL`, `HALF`, `QUARTER`) |
| `src/regime/classifier.py` | ~67 lines | UI metadata adapter — maps gate output to colors, labels, descriptions |
| `src/regime/composite.py` | — | Dominance scores, dynamic betas, driver families |
| `src/regime/confidence.py` | — | Confidence computation from composite + signal alignment |
| `src/scheduler/orchestrator.py` | ~1,568 lines | Prefect flow: fetches data → computes signals → classifies regime → writes to DB → generates briefs |

### Layer 2: Validation & Ledger (Python)
| Module | Purpose |
|--------|---------|
| `src/validation/ledger.py` | Forward-walking alpha ledger. Tracks EOD directional calls vs T+1/3/5 outcomes |
| `src/validation/backtest.py` | Out-of-sample validation engine. Computes hit rates, Brier scores |
| `src/validation/aggregate.py` | Aggregates validation stats by regime type, pair, time horizon |
| `src/validation/engine.py` | Historical replay engine — can backfill and validate any date range |
| `src/research/artifacts.py` | Generates markdown track-record reports from validation_stats |

### Layer 3: Database (Supabase / PostgreSQL)
| Table | Purpose |
|-------|---------|
| `signals` | Immutable daily signal rows per pair (rate_norm, cot_norm, vol_norm, oi_norm, composite) |
| `regime_calls` | Immutable regime classifications with timestamp, confidence, primary_driver |
| `validation_log` | T+5/T+20 outcomes, hit/miss, Brier score per call |
| `brief_log` | Generated AI briefs with model version, token count, raw text |
| `pipeline_errors` | Operational errors for debugging |
| `desk_open_cards` | Per-pair desk cards for the terminal |
| `research_memos` | Weekly macro memos with Substack links |

### Layer 4: Research Terminal (Next.js 15)
| Route | What It Shows |
|-------|--------------|
| `/` | Landing page with ticker marquee, latest calls, methodology teaser |
| `/terminal` | Live cross-pair overview, active strategies, pipeline heartbeat |
| `/terminal/fx-regime` | Full G10 mosaic: apex targets, bench pairs, outliers, correlation matrix |
| `/terminal/fx-regime/[pair]` | **Pair Desk**: spot, regime, confidence, composite, invalidation level, regime history, COT percentile sparkline |
| `/terminal/performance` | Alpha ledger, Brier scores, win rates by regime, historical P&L proxy |
| `/terminal/memos` | Research memo archive with date filter |
| `/terminal/calendar` | Macro event calendar |
| `/methodology` | Full 3-layer framework documentation with KaTeX math |
| `/about` | Operational identity, data sources, disclaimers |
| `/audit` | Pipeline run history, DQS scores, error log |
| `/brief` | Latest AI-generated daily brief |

### Layer 5: Agent System (Kimi + Subagents)
| Component | Purpose |
|-----------|---------|
| `Agent(subagent_type="explore")` | Fast codebase exploration: find files, trace code paths, understand modules |
| `Agent(subagent_type="coder")` | Cross-file implementation, debugging, running commands |
| `Agent(subagent_type="plan")` | Architecture decisions and implementation planning |
| Pre-commit hook | Runs pytest (pipeline) + npm build (web) before allowing commit |
| Git | Standard git workflow: branch → implement → test → commit → push |

### Layer 6: Deployment Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | Prefect Cloud | Daily G10 Alpha Engine runs every 24h |
| **Worker** | Cloudflare Workers | API endpoints: `/api/health`, `/api/substack-rss`, `/api/fx-price`, `/proxy/yahoo` |
| **Frontend Host** | Vercel (ready) | Next.js app deploy target |
| **Database** | Supabase | PostgreSQL 17 with RLS, SSR types generated for TypeScript |

---

## 2. WHY WE BUILT IT

### The Core Thesis
> **G10 FX is not random.** It is driven by observable, slow-moving macro variables: rate differentials, central bank posture, positioning extremes, and volatility regimes. These generate persistent edges — but only if you (1) measure them correctly, (2) classify the regime before trading, and (3) validate out-of-sample.

### The 5 Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Deterministic, not ML** | No black boxes. Every signal is a transparent arithmetic transformation. This means explainability to institutional counterparts and no overfitting risk. |
| **Immutable ledger** | Every regime call is timestamped and frozen. You cannot retroactively change a call. This creates a real track record — the only thing that matters for credibility. |
| **3-layer separation** | Layer 1 (regime gate) prevents trading in wrong environments. Layer 2 (directional) measures conviction. Layer 3 (timing) manages risk. Each layer has its own invalidation rules. |
| **Public by design** | The research terminal is public. The Substack is public. This forces discipline and turns the system into a marketing engine — every correct call is a credential. |
| **Agent-augmented velocity** | Kimi plans and executes directly. Complex multi-file work is delegated to Kimi subagents for cross-file consistency. This allows one operator to maintain institutional-grade infrastructure without a team. |

### Why Each Component Exists

**The Pipeline** — Because manual data collection is error-prone and slow. The pipeline runs in ~90 seconds and produces the exact same math every time.

**The Validation Engine** — Because without out-of-sample validation, you are guessing. The engine computes Brier scores (probabilistic calibration) and hit rates by regime type. If a regime has a 0.35 Brier score, you know it's well-calibrated. If it's 0.65, you're overconfident.

**The Terminal** — Because institutional counterparts (PMs, CIOs, macro funds) will not read Python scripts. They need a Swiss-monochrome interface that shows live status, historical performance, and methodology transparency in one click.

**The AI Briefs** — Because the operator cannot write a 1,200-character institutional brief every morning. The AI client generates it from the signal snapshot, then the operator edits before publishing.

**The Agent System** — Because the codebase is now ~150 files across Python + TypeScript + SQL. One person cannot hold all of it in working memory. The agent system compresses context into machine-readable maps and delegates execution while preserving strategic oversight.

---

## 3. WHAT WE ACHIEVED

### Quantitative Outcomes
| Metric | Status |
|--------|--------|
| Test coverage | 121/121 pytest cases pass |
| Pipeline lint | Ruff clean (0 errors) |
| Frontend lint | Biome clean (0 errors, was 2,164) |
| Frontend build | Next.js static export succeeds |
| Token efficiency | ~6,910 tokens/session (down from ~34,886, -80%) |
| File coverage | 148 files mapped, 13 skills catalogued, 6 rule sets |
| Map regeneration | Automatic via git hooks + file watcher |

### Qualitative Outcomes
| Achievement | Significance |
|-------------|--------------|
| **End-to-end delegation proven** | `fx-agent run spec.md` → Cursor modifies file → pytest passes. The loop works. |
| **Immutable track record** | Every regime call is persisted with timestamp. No retroactive editing possible. |
| **Institutional-grade terminal** | Swiss monochrome aesthetic, KaTeX math, tabular-nums, dense data tables. Looks like a Bloomberg terminal, not a dashboard. |
| **Self-healing maps** | Any git commit auto-regenerates CODEMAP, SKILLMAP, RULEMAP. The system stays synchronized with itself. |
| **Subagent operating model** | Kimi = strategy + direct execution. Complex tasks = Kimi subagents for surgical precision. No context overload. |

### What This System Can Do Today
1. **Run a full daily pipeline** in 90 seconds: fetch data → compute 3-layer signals → classify regimes → write to Supabase → generate AI brief
2. **Display live pair desks** for EUR/USD, USD/JPY, USD/INR with spot, regime, confidence, composite, and invalidation levels
3. **Track out-of-sample accuracy** with Brier scores and win rates by regime type
4. **Generate research memos** from historical backtests with markdown artifacts
5. **Accept complex specs** via Kimi subagents for cross-file implementation with automatic verification
6. **Regenerate its own maps** when files change, keeping agent context fresh without manual work

---

## 4. HOW TO USE IT FOR HIGHEST EXPECTED VALUE

### The Daily EV Loop (Morning, ~15 min)
```bash
# 1. Run the pipeline (Prefect Cloud does this automatically, or locally)
cd pipeline && prefect deploy --prefect-file prefect.yaml

# 2. If you want to run manually:
pipeline/run_daily.sh

# 3. Check the terminal for live status
open https://fxregimelab.com/terminal

# 4. Review the AI brief, edit if needed, publish to Substack
# Brief is in briefs/brief_YYYYMMDD.txt
```

### The Research EV Loop (Weekly, ~45 min)
```bash
# 1. Run weekly orchestrator (includes macro summary, memo generation)
pipeline/run_weekly.sh

# 2. Check validation stats
open https://fxregimelab.com/terminal/performance

# 3. If a regime call is wrong, the system already logged why:
# - Check validation_log for T+5 outcome
# - Check signals table for the inputs that produced the call
# - Adjust thresholds in src/logic/ if the error was systematic

# 4. Publish the weekly memo to Substack
```

### The Development EV Loop (As Needed)
```bash
# 1. Need a new signal? Plan first:
# Use EnterPlanMode for non-trivial implementation

# 2. Explore the codebase:
# Use Agent(subagent_type="explore") to find relevant files

# 3. Implement directly or delegate to subagent:
# Use Agent(subagent_type="coder") for cross-file implementation

# 4. Verify: pytest, ruff, npm run build
# 5. Commit: git commit (pre-commit hook runs tests)
```

### The Credibility EV Loop (Continuous)
| Action | Frequency | Output |
|--------|-----------|--------|
| Publish daily brief | Daily | Substack post with regime + conviction |
| Tweet apex target | When conviction ≥ 4 | Twitter/X thread with levels |
| Share terminal link | Weekly | "Live regime desk: fxregimelab.com/terminal" |
| Reference validation stats | Monthly | "Our R1 regime calls have a 0.31 Brier score over 180 observations" |
| Post methodology deep-dive | Quarterly | Long-form explaining the 3-layer framework |

**Why this generates EV:** Every correct call is a marketing asset. Every wrong call is a learning asset (because the inputs are transparent). Over 12 months, this compounds into an auditable track record that no discretionary trader can replicate.

### Tactical Uses of Each Component

| Component | Highest-EV Use |
|-----------|---------------|
| **Layer 1 Gate** | Use it to **not trade**. If the gate says NEUTRAL or VOL_EXPANDING, stay flat. The edge is in avoiding bad trades, not just finding good ones. |
| **Layer 2 Directional** | Use COT percentile extremes (>90 or <10) as contrarian flags. When rate_signal and COT_signal align, conviction is real. When they clash, wait. |
| **Layer 3 Execution** | Use RVOL rank >70 to size down. Use skew reversal to time entries. The stop level is computed from MIE proxy — do not override it emotionally. |
| **Validation Engine** | When Brier score for a regime >0.45, recalibrate. The engine tells you when you're overconfident before your capital does. |
| **AI Briefs** | Use them as first drafts, not final copy. The AI is good at structure and tone. You add the macro narrative and the specific thesis. |
| **Research Terminal** | Share the `/terminal/performance` link with PMs. It is your credibility page. The Brier score table is more convincing than any pitch deck. |
| **Agent System** | Never write boilerplate code alone. Specs for fetchers, components, and DB migrations are implemented by Kimi subagents. You review and verify. |

### What NOT to Do (EV Destroyers)
| Anti-Pattern | Why It Destroys EV |
|--------------|-------------------|
| Override Layer 1 gate manually | The gate exists because human discretion underperforms in regime classification. |
| Skip validation | Without Brier scores, you don't know if you're lucky or good. |
| Publish without editing AI briefs | AI hallucinates. Always verify the signal levels in the brief against the database. |
| Trade all 3 pairs simultaneously | The system is designed for selective exposure. Trade only when conviction ≥ 4 AND Layer 1 is directional. |
| Let the terminal go stale | A terminal with old data signals abandonment. The Prefect schedule prevents this. |

---

## 5. THE STATE MACHINE: WHERE WE ARE NOW

```
[Data Ingestion] → [Signal Pipeline] → [Regime Classification] → [Validation] → [Publication]
       ↑                                                                    ↓
       └──────────────────────[Agent System]←───────────────────────────────┘
```

| Phase | Status | Next Trigger |
|-------|--------|--------------|
| Foundation (Round 1) | ✅ Complete | — |
| Core Logic (Round 2) | ✅ Complete | — |
| Validation Engine (Round 3) | ✅ Complete | — |
| Historical Backtest (Round 4) | ✅ Complete | — |
| Research Terminal (Round 5) | ✅ Complete | Deploy to Vercel |
| Agent System (13/10) | ✅ Polished | Use for all new dev |
| Frontend Lint (14/10) | ✅ Zero errors | Maintain on every commit |
| Production Deploy | 🔄 Ready | `npx vercel --prod` in `web/` |
| Prefect Scheduling | 🔄 Active | `prefect deploy` from pipeline/ |

---

## 6. ONE-PAGE OPERATOR CHEAT SHEET

```bash
# Morning
pipeline/run_daily.sh              # or let Prefect run it
open https://fxregimelab.com/terminal/fx-regime

# Weekly
pipeline/run_weekly.sh

# When you need to build something
# Use EnterPlanMode for non-trivial implementation
# Use Agent(subagent_type="explore") to investigate
# Use Agent(subagent_type="coder") for cross-file work

# Verify everything
cd pipeline && pytest              # full test suite
cd pipeline && ruff check .        # lint
cd web && npm run build            # frontend build

# Maintenance
git log --oneline -10              # review recent commits
pytest                             # run tests before any deploy
```

---

*This system is not a toy. It is a live macro research operation that happens to be public. Treat it as such.*
