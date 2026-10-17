# Personal Trading Engine — Audit & Expansion Plan

> **Status: v0.2 — 2026-10-17. Owner approved defaults ("GO"); desk trading subset: EURUSD + USDJPY only.**
> Branch: `fx-live-personal`. Paper money only (MT5 demo). 3-pair research lock unchanged; no USDINR
> execution. Public product untouched.
> Owner instruction that created this document: *"audit the partial reader / local expansion / repair,
> and plan the change from the research desk to a personal trading engine — paper money, hold 1–7 days,
> real strategies and testing to decide which trade to take, with a local AI agent connected to the data."*

---

## 0. TL;DR

1. **The recent work is real and sound, but none of it is a trading system yet.** The "repair" fixed a false
   DEGRADED banner honestly; the "reader" is a strictly bounded LLM note-writing slice (currently running on
   deterministic fallback because free providers are dead); the "local expansion" is a local runner + receipt
   tooling. All three are directly reusable as the foundation of a paper desk.
2. **The signal machinery that a desk needs already exists in the codebase** — entry logic with stops
   (`layer3_execution.py`), a T+5/T+20 scoring engine with per-pair costs (`validation/`), a 1997+ replay engine
   (`simulation_engine.py`), daily OHLC bars (`historical_prices`), a 40+ column daily feature table
   (`signals`), and an overnight invalidation check. **What does not exist anywhere: orders, positions, fills,
   notional sizing, PnL accounting, broker — i.e., the hold-and-settle layer.**
3. **Honest reading of the live record (May–Oct 2026): the house directional calls are currently at or below
   coin-flip.** EURUSD 9/35 (26%), USDJPY 32/99 (32%), USDINR 33/80 (41%) directional hits; USDJPY made
   100/100 BEARISH calls into an appreciating trend. There are also 12 corrupted validation rows (~3.5% of the
   live window) and the strategy-ledger mark-to-market walk stopped on 2026-05-27. The paper desk must therefore
   be a **measurement + hypothesis-testing engine first**, not a profit machine.
4. **The plan:** build a private paper desk in 5 phases (P0 foundations → P1 backtests + strategy cohort →
   P2 paper account with risk budget → P3 local-agent layer (CLI + MCP + notes + charts) → P4 operate/gates).
   Everything local-first, zero production writes, zero public-site changes. TradingView connectivity is
   optional and unverified; local deterministic charts come first. MetaTrader 5 is the preferred market-data
   + demo-execution upgrade (§5.9) — real spreads, real fills, still paper money.
5. **The pivot is compatible with IDENTITY.md** — the public product stays research-only; `position_size`
   and `stop_level` already live in the DB "for internal research" (Masterplan §0). The personal desk is
   internal tooling, like those fields — never rendered publicly.

---

## 1. Why this document

Read `IDENTITY.md` first (hard constraint), then `MASTERPLAN.md` (product direction). This document is the
bridge from the completed `fx-live-personal` slice (live pipeline run + honest banner + reader scaffolding,
merged in PR #20) to a **personal paper-trading desk** on the same three pairs, with:

- actual (paper) trades, not theory: entries, stops, holds of 1–7 days, settlements, scorecards;
- multiple strategy types tested against each other to decide what is worth "trading" — with the evidence
  included, so decisions are measured, not vibes;
- a local AI agent (like the one writing this) able to read all desk data and produce daily analysis, chart
  packs, and candidate trades;
- optional chart/pattern tooling, including (if viable) a TradingView connection for visual review.

---

## 2. Audit Part A — What the recent work actually is

### A1. The "repair" — what it was (packets 1–7 in `reports/REPAIR_CHECKPOINT.md`)

| Item | Finding | Status |
|---|---|---|
| Footer falsely `DEGRADED` | `health_checks` empty → fallback inference scored only the *current calendar day*, but calls are dated by *trading day* → permanently red. | **Fixed** in web display code only (`queries.ts`, `desk/layout.tsx`, `audit-trail-banner.tsx`): scores the latest day **with published calls**, real DQS, 0.8 gate. Zero pipeline changes, zero DB writes. |
| DQS aborts (`DQS 0.2000 below CRITICAL 0.50`) | Correct gate behavior pre-close on incomplete data, **not** a bug. | Verified, no change. |
| `Event loop is closed` tracebacks + post-run accuracy alerts | Known noise (`SLACK_WEBHOOK` unset). | Documented, cosmetic only. |
| Append-only proof | Live run 2026-10-17 08:07–08:11 UTC published 3 calls @ 2026-10-16, DQS 1.0. `regime_calls` +3 rows; all 19,503 prior rows byte-identical (SHA-256 `eec0749c…`). `validation_log` +12 inserts, −6 **flag-only** supersessions (no content edits/deletes). | Proven, receipts in `reports/REPAIR_CHECKPOINT.md`. |
| Publish | PR #20 merged as merge commit `83d03559…` (no squash, no force push). Production verified green: `System integrity verified: 2026-10-17 · Pipeline: OK · DQS: 1.00`. Tag `v2.1-archive` (`b0d33cd`) unmoved. | Done. |

**What it is, plainly:** the research pipeline is healthy and its ledger is proven append-only; the public
status display is now honest. **6 root gates remain open** (led by EUR/USD 90-day accuracy ≥ 55%) — no
"verified release" is claimed anywhere.

### A2. The "partial reader" — what it actually is

- `pipeline/src/ai/analyst_reader.py` — one LLM reader only; input = frozen regime call + brief; output = a
  5-line analyst note that **cites its inputs**; 3-pair locked; no new signals; all AI calls go through
  `pipeline/src/ai/client.py`.
- `pipeline/src/ai/renderers/analyst_note.py` — the renderer + deterministic fallback note.
- `pipeline/src/eval/llm_reader_eval.py` + 12 tests — a faithfulness/number-accuracy/Brier eval harness.
- **Why "partial":** as of 2026-10-17 every free LLM provider path is unreachable (Groq model id
  decommissioned → 404; Gemini → 429; NIM → 410 EOL; OpenRouter free → 404). The live run therefore used the
  **deterministic fallback**. Eval v3 scored the fallback text: faithfulness 1.000, number accuracy 1.000,
  Brier n=0 (no outcome claims) — i.e., *the harness works; there is no evidence yet about real LLM prose*.
- **Verdict:** structure is good, zero ledger writes, and it is exactly the right shape for daily desk notes.
  It needs a provider refresh (parked owner decision) but is not a blocker — the fallback is honest.

### A3. The "local expansion" — what it actually is

The `fx-live-personal` slice delivered: a local live runner (`pipeline/scripts/run_live_personal.py`, loads
`.env.local`, never prints secrets), a read-only ledger snapshot/proof tool
(`pipeline/scripts/ledger_snapshot.py`), the green live run + append-only proof, the eval reports, the footer
honesty fix, and the merge. **It contains no trading, no positions, no PnL, no execution.** It is the *seam*:
local run capability + read-only tooling + receipts culture = where the paper desk attaches.

### A4. Verdict: can we use and improve it? Yes — reuse map

| Existing component | What it is | How the paper desk uses it |
|---|---|---|
| `pipeline/src/logic/layer2_directional.py` | Directional bias + conviction (crowd veto, deadbands, clamp 1–5) | Entry gate for the "house" strategy (S1) |
| `pipeline/src/logic/layer3_execution.py` | ENTER/FULL/HALF enum, vol-rank gates (`_VOL_RANK_ENTER_MAX 0.88`, `_VOL_RANK_FULL_MAX 0.70`), stop = `max(1.5·ADR20, MIE)` | The ready-made entry rule + stop levels — call unchanged |
| `pipeline/src/validation/` | T+5/T+20 outcomes, per-pair costs, Brier, CI, ledger T+1/3/5 MTM + max pain | Scoring patterns; cost table (recalibrated conservatively) |
| `pipeline/src/backfill/simulation_engine.py` | 1997+ walk-forward replay (`2.1-m3` rows in DB) | Historical signal stream for backtests (research-grade caveats) |
| `pipeline/src/research/position_sizing_simulator.py` | Research sizer ($1M nominal, one 0.5bp cost) | **Template only** — schema ideas, not importable as-is |
| `pipeline/src/desk/invalidation.py` | Overnight breach math: `|day_change| > 1.5·rv20`, sticky 3 ticks | Exit-on-invalidation for open paper positions |
| `analyst_reader` + `analyst_note` | 5-line note + fallback | Desk-note prose (fallback OK for now) |
| `run_live_personal.py` + `ledger_snapshot.py` | Local run + receipts | Attach point + receipt pattern for paper artifacts |
| `fetchers/fx_spot.py` (`SpotBar` OHLC) | Live daily OHLC (Polygon → Alpha Vantage → yfinance), persists only close | Price-integrity path; capture full OHLC later if wanted |
| `weekly_regime_read/scripts/track_record.py` | Stop-hit check from bar low/high + track-record JSON | Pattern for paper stop fills |
| `historical_prices` (OHLC) | yfinance daily bars, 1996/2003+ *(stale: ends 2026-06-29)* | Refresh → simulator + charts |
| `signals` (40+ cols) + `regime_calls` | Daily features + call intent | Desk daily inputs |

---

## 3. Audit Part B — What exists for trading today

### B1. Signal layer (complete)

- **Layers 1–3** run daily per pair: signals → bias/conviction (`layer2`) → entry timing/size-enum/stop
  (`layer3`). Persisted in `regime_calls` incl. `predicted_direction`, `conviction`, `entry_timing`,
  `position_size` (enum `FULL`/`HALF`), `stop_level`, `stress_level`, `data_quality_score`, all 8 signal
  columns, `signal_composite`, `write_hash`.
- **8-signal families** + pair-specific factors (ECB BS, Bund-BTP, BoJ rate, intervention proximity, India VIX,
  INR forward premium, FPI flow) live in `signals` with 40+ columns per pair-day (z-scores, rate diffs, COT,
  vol ranks, cross-asset: DXY/VIX/oil/gold/copper/stoxx/US10Y, etc.).
- **Desk context** exists (`desk_open_cards`): dominance array, markov transition probabilities, pain index,
  telemetry audit, overnight invalidation flags.
- Current live posture (2026-10-16): all three pairs `NEUTRAL` / `WAIT`; spots EURUSD 1.12381 (vol rank
  0.93 — high), USDJPY 157.997 (0.24), USDINR 94.6393 (0.58).

### B2. Scoring & evaluation assets (strong)

- `validation/engine.py`: T+5/T+20 outcomes from `signals.spot`; trading-date math is **weekends-only**
  (no holiday calendar — caveat).
- `validation/calculator.py`: `log_return_bps = 10⁴·ln(sₕ/s₀)`, dead-band 5 bps, costs
  `{EURUSD 0.2, USDJPY 0.3, USDINR 10.0}` bps round-trip *(idealized — see §4.2)*, Brier.
- `validation/aggregate.py`: `validation_stats` with win rates, **net-of-cost** win rates, Clopper-Pearson CIs,
  Sharpe-like, max drawdown, rolling 90d.
- `strategy_ledger`: entry close + T+1/T+3/T+5 closes + hits + `max_pain_bps` + Brier — the closest thing to
  forward marks. **441 rows since 2026-05-01; but MTM only populated for 85 rows, all ≤ 2026-05-27 — the walk
  stopped.** (May window: EURUSD t5 16/21, USDJPY 13/30, USDINR 11/34; max pain mean 25/74/116 bps.)

### B3. Replay & data

- `simulation_engine.py`: per-trading-day replay `--pair/--start/--end/--v2`; writes `(SignalRow, RegimeCall)`
  tagged `data_source="backtest"` (`2.0-historical` or `2.1-m3`). No PnL. **Research-grade only** — treat as
  calibration, not proof (IDENTITY: "Backfill only for calibration and methodology validation").
- `historical_prices`: true daily OHLC + volume (source `yfinance`): EURUSD 5,857 rows since 2003-12,
  USDJPY 7,691 since 1996-10, USDINR 5,854 since 2003-12. **Stale: last rows 2026-06-29.** Refresh script
  exists: `pipeline/scripts/populate_historical_prices.py` (yfinance; 2026-03-01 → today; deep history via
  `fetch_max_history`, 30 y). Only backfill paths write this table — the daily pipeline never does.
- `signals.spot` = the live reference price per pair-day (used by validation; current to 2026-10-16). The live
  fetchers (`fetchers/fx_spot.py`, Polygon → Alpha Vantage → yfinance fallback) already fetch daily OHLC
  (`SpotBar`) but persist **only the close**; **no bid/ask exists anywhere — all pricing is close/last-only**.

### B4. What does NOT exist (the build list)

1. **No orders / positions / fills / trades / PnL store** anywhere in `pipeline/src` (grep-verified: zero
   "paper", no broker adapter, all "order" hits are SQL `ORDER BY`).
2. **No notional sizing** — `position_size` is only the enum `FULL`/`HALF`; nothing converts stop distance +
   risk budget into units.
3. **No fresh price refresh inside the daily loop** — OHLC is 3.5 months stale; the pipeline discards the
   OHLC it fetches (close only persists); no candles/charts exist for the 3 pairs (earlier chart generators
   were deleted from the repo).
4. **No desk access layer** — nothing lets a local agent cleanly read "today's calls + features + bars" or
   record simulated trades (CLI/MCP absent).
5. **No disciplined strategy comparison** — validation scores the house calls only; nothing tests trend /
   mean-reversion / liquidity variants head-to-head at 1–7 day horizons.

---

## 4. Audit Part C — Honest performance reading (as-of 2026-10-17)

### C1. Live directional record (2026-05-01 → 2026-10-11, 344 non-superseded validations)

| Pair | Directional calls | Direction hit (T+5) | Bias skew |
|---|---|---|---|
| EURUSD | 35 | **9 (25.7%)** | BULLISH 19 / BEARISH 16 |
| USDJPY | 99 | **32 (32.3%)** | **BEARISH 100/100** (into an appreciating trend) |
| USDINR | 80 | **33 (41.2%)** | BEARISH 74 / BULLISH 6 |

Plus: NEUTRAL 129 of 344; recent `confidence` is degenerate (~0.47 on all pairs, conviction 2–3).

Official `validation_stats` (as-of 2026-10-17, all-time incl. backfill rows — mixed generations, use with
care): t5 win 0.467/0.473/0.492 (EURUSD/USDJPY/USDINR), t5 net 0.485/0.489/0.473; t20 win 0.493/0.480/0.554,
t20 net 0.502/0.488/**0.548**; Brier skill ≈ 0 / negative mostly; rolling 90d values swing wildly across
generations (EURUSD 0.158 vs 0.636 in June) — **definitions have changed over time; treat as directional
evidence, not stable truth**.

### C2. Data-hygiene findings (found during this audit — need decisions, not fixes yet)

1. **12 corrupted rows in the live window (3.5%)**: identical impossible returns across all three pairs on
   the same dates — e.g. `+44,127.9 bps` (2026-05-24, all pairs), `−49,278.0 bps` (T+20, 2026-05-21, all
   pairs). Signature = cross-pair price contamination in the validation run around May 2026. They distort
   `validation_stats` means/win-rate aggregates. *(Append-only handling required — supersede, never edit.)*
2. **`strategy_ledger` MTM walk stopped 2026-05-27** — only 85/441 rows have forward marks.
3. **Costs are idealistic**: validation uses 0.2/0.3/10 bps round-trip; retail-realistic is ~5–100× that for
   USDINR. Paper accounting must be conservative (proposal in §5.4).
4. **OHLC bars stale to 2026-06-29** — the simulator/charts need a refresh job with sanity bounds.
5. Weekend-only trading calendar (no holidays) — small date-drift risk near holidays (e.g. JPY/INR holidays).

### C3. What this means (expectations)

- The house signal turned **NEUTRAL on all 3 pairs** recently — the desk will legitimately produce **zero
  house-strategy entries some days**. That is the system working, not failure.
- Live directional performance is currently *not* evidence of edge. The paper desk's first job is to measure
  cleanly and test alternatives; profits are a hypothesis, not a promise. This mirrors the repo's culture:
  publish receipts, don't dress up numbers.

---

## 5. Target architecture — Personal Paper Desk v1

### 5.1 Principles & guardrails

- **Private/internal only** — like `position_size`/`stop_level`, nothing renders publicly; no web changes.
- **Paper only** — no broker, no real orders, no money. Real-money feasibility is a *separate future decision*.
- **3-pair lock** — EURUSD, USDJPY, USDINR. No new pairs.
- **Read-only on production data** — `regime_calls`/`validation_log`/`signals` are read, never written by the
  desk. New state lives locally (SQLite + receipts). No production pipeline behavior changes without separate
  owner approval (Prefect Cloud is prod; the desk runs locally at first).
- **Honest accounting** — conservative costs, next-open entries, glitch quarantine, no lookahead in live
  tracking (live-model rows only: `model_version = '2.0-live'`, `data_source = 'live'`).
- **Receipts everywhere** — every paper order/fill/settlement is append-only with a hash chain, exported to
  `reports/desk/` (committed); the database itself stays local.
- No paid evals; LLM only via `pipeline/src/ai/client.py` (reader slice).

### 5.2 The daily cycle (day-in-the-life)

1. **Pipeline runs as-is** (~09:00 UTC, Prefect) → new calls + validations land in Supabase.
2. **Desk day** (local: `python -m paper_desk day` or an agent run): refresh daily OHLC → mark open positions
   (MTM) → settle due exits → evaluate strategies for new entries → write **desk note** (md + chart pack) with
   candidate paper orders.
3. **Owner reviews** (or agent proposes, owner approves) → orders recorded with explicit approval.
4. **Fills simulated** at defined semantics (§5.4) — recorded append-only.
5. Later runs auto-settle stops/horizons and update the **scorecard** (weekly artifact in `reports/desk/`).

### 5.3 Module plan (new components; proposed package `pipeline/src/paper/`)

| Module | Purpose |
|---|---|
| `paper/prices.py` | Bars service: refresh `historical_prices` (yfinance), sanity bounds (±10%/day quarantine), spot cross-check vs `signals.spot` (tolerance 0.5%) |
| `paper/store.py` | Local SQLite (`data/desk/paper_desk.sqlite3`, gitignored): orders, fills, positions, equity, approvals — append-only + hash chain; JSON receipts to `reports/desk/` |
| `paper/sizing.py` | Risk-based units: `units = risk_budget / stop_distance`, leverage cap, per-pair pip/notional conversion |
| `paper/strategies/` | Strategy registry (pure functions): config + entry/exit rules (§5.5) |
| `paper/simulate.py` | Backtest/simulator over bars + (optional) replay signals; horizon sweeps T+1..T+7; cost model; MAE/MFE |
| `paper/settle.py` | Exits: stop → invalidation (`desk/invalidation` math, daily-adapted) → horizon; fill semantics §5.4 |
| `paper/scorecard.py` | Metrics, baselines (random / always-long / coin-flip), CIs, per-pair/regime buckets; md + json artifacts |
| `paper/cli.py` | `status`, `refresh`, `day`, `positions`, `settle`, `scorecard`, `chart`, `approve`, `export` |
| `paper/mcp_server.py` | Local MCP (stdio): read tools + `propose_order`; writes only via CLI `--commit` in v1 |
| `paper/charts.py` | Candles + overlays (entry/stop/EMAs/swings), PNG (agent) + HTML (human) |

Reused unchanged: `layer2/layer3` (entry+stop), `validation/calculator` patterns (costs, bps), `desk/
invalidation` (breach math), `signals` + `regime_calls` (inputs), `analyst_reader` (note prose).

### 5.4 Paper ledger & accounting model (concrete defaults — adjustable in §11)

- **Paper equity**: `E₀ = 10,000` (report-only; currency-agnostic R accounting).
- **Risk per trade**: default `0.75%` of equity → `risk_budget`; `units = risk_budget / stop_distance`.
  Fallback stop if `stop_level` is NULL: `max(1.5·ADR20, 2.0·ATR20)` self-computed. Leverage cap 3× equity
  notional.
- **Costs (round-trip bps, incl. slippage) — conservative defaults**: EURUSD 1.0, USDJPY 1.2, USDINR 15.0
  (vs validation's 0.2/0.3/10). Recorded per trade; revisable.
- **Entry**: next trading-day **open** after signal publication (no same-bar cheating).
- **Exit priority**: (1) stop hit (fill at stop; gap-through fills at open), (2) invalidation overlay
  (1.5×rv20 adverse day move, sticky — daily-adapted), (3) horizon close (T+n).
- **Horizons**: sweep T+1…T+7 in research; each strategy declares its default (house = T+5).
- **MTM**: daily at close; PnL in R and % of equity; equity curve + drawdown tracked.

### 5.5 Strategy registry — first cohort

| ID | Strategy | Logic (v1) | Horizon |
|---|---|---|---|
| S0a/b | Baselines | Random direction; Always-long (per pair) | T+5 |
| S1 | **House ENTER** | `bias ≠ NEUTRAL ∧ conviction ≥ 3 ∧ vol_rank ≤ 0.88` (`layer3`); direction = bias; stop = `layer3` | T+5 |
| S2 | House FULL subset | `conviction ≥ 4 ∧ vol_rank ≤ 0.70` | T+5 |
| S3 | Trend-following | `close > EMA20 > EMA100` and Donchian-20 breakout variant; stop 1.5×ATR20 | T+3…T+5 |
| S4 | Mean-reversion | `z=(close−SMA20)/σ20`; enter \|z\| ≥ 2 in NEUTRAL regimes; target band-mid | ≤ T+5 |
| S5 | **Liquidity-sweep reversal** (user ask) | Daily approximation: sweep of prior 10-day swing low/high then close back inside range → counter-trade | T+1…T+3 |
| S6 | Event/stress overlay | Not standalone: gate S1–S4 (no entries stress=RED; half-size AMBER; event-day rules) | — |

### 5.6 Testing protocol & graduation gates

1. **Stage 0 — Backtest** (bars 2003+; replay signals where needed — research-grade caveats). Horizon sweeps,
   per-pair/per-regime buckets, costs on, baselines side-by-side.
2. **Stage 1 — Shadow** (record-only, live): desk records every candidate daily and settles it — no account.
   This produces clean, forward, lookahead-free evidence while the system builds trust.
3. **Stage 2 — Paper account**: strategies earn a risk budget after **graduation gates**:
   ≥ 40 settled trades, net expectancy > 0 with CI lower bound > 0, profit factor ≥ 1.1,
   max drawdown ≤ 10% of paper equity, no single pair > 60% of PnL.
   **Hard pause**: 3 consecutive red weeks or 15% equity DD → freeze, review, public note in receipts.
4. Weekly scorecard artifact; monthly review; promote/cut decisions recorded.

### 5.7 Agent connectivity (the "local AI" part)

- **CLI** (`paper_desk …`): the single source of truth for day runs, approvals, settlements, exports.
- **MCP server** (stdio, local): tools = `get_status`, `get_calls`, `get_signals`, `get_bars`,
  `get_positions`, `get_scorecard`, `make_chart`, `propose_order` (records a *proposed* order only).
  Writes happen via CLI `--commit` (append-only, hashed). This lets an agent like me live-read everything,
  produce analyses/candidates/charts, while the human approves execution.
- **Desk note**: `reports/desk/YYYY-MM-DD.md` — data snapshot, open positions, candidates with rationale +
  chart links, scorecard deltas. Prose via reader slice (deterministic fallback until a provider works).
- Secrets: `.env.local` only; never printed (established practice of the repair work).

### 5.8 Charts & pattern tooling (incl. the TradingView question)

- **Phase 1 (deterministic, local)**: candlestick renderer from our OHLC with entry/stop/EMA/swing overlays →
  PNG (machine-readable by the agent) + HTML (interactive). Numeric pattern features: swing pivots, prior
  high/low sweeps, range expansion/compression, inside/outside bars, volatility-rank bands. (Built fresh —
  the old `charts/` PNGs are static leftovers and their generator no longer exists.)
- **Phase 2 (visual review)**: two options, both honest:
  - *(a)* TradingView via the user's logged-in browser (browser automation — qualitative visual check only;
    this environment supports it);
  - *(b)* community "TradingView MCP" servers — **unverified** (web search was unavailable during this audit;
    no official TradingView analysis MCP is known to exist). Validate before adopting; never the source of
    numeric truth — our bars remain authoritative.
- **Phase 3 (optional)**: TradingView alerts/webhooks as convenience pings (not analysis).

### 5.9 MetaTrader 5 integration (owner-requested) — real data, demo execution

- **What MT5 adds** (Windows-only; the official `MetaTrader5` Python package talks to the local terminal):
  true broker **bid/ask and real spreads** (closes the "close-only, no spread modeled" gap), full **OHLC
  history per timeframe** for every symbol the broker lists, tick data, and programmatic **order placement
  on a demo account** — i.e., paper trading with real market mechanics instead of simulated fills.
- **Data use:** sync daily (and optionally intraday) bars into the desk's **local** bar store
  (`data/desk/paper_desk.sqlite3`, gitignored; broker feed authoritative); refresh of the production
  `historical_prices` table is **deferred** — no production DB writes from the desk (owner constraint).
  Sample per-pair spreads by time-of-day to replace guessed cost defaults with measured
  ones. Strategy inputs stay from `signals`/`regime_calls`; MT5 is the *market* layer.
- **Execution use:** v1 = **demo account only**, and only for **approved** orders — the agent can execute
  approved paper orders end-to-end through MT5. Live-account execution is out of scope until a separate
  explicit owner decision with guardrails (per-order/daily caps, kill switch). *(Indian residents: offshore
  FX/CFD real-money trading faces regulatory limits — relevant only to any future real-money phase.)*
- **Trading universe decision (owner, 2026-10-17): EURUSD + USDJPY only.** The desk trades the two majors
  on MT5; USDINR remains research-only in the pipeline (never executed). This narrows the trading subset —
  the 3-pair research lock is unchanged (no new pairs, no expansion).
- **Adapter plan:** `paper/broker_mt5.py` (init, symbol check, rates, tick/spread, order_send, positions sync)
  + `paper/broker_sim.py` fallback, behind one `broker` interface. Credentials in `.env.local` only; never
  printed. Every MT5 action mirrored into the paper ledger receipts.
- **Broker selection (shortlist):** any MT5 broker works for the demo phase; shortlist for spread/execution
  quality: Exness, XM, IC Markets, Pepperstone. Choose empirically — the desk includes a spread sampler;
  we run demos and let measured spreads decide. Real-money broker choice is a separate future decision
  (jurisdiction/regulation matters).
- **Owner prerequisite — RESOLVED (2026-10-17 evening):** Exness demo connected. Branded
  terminal at `C:\Program Files\MetaTrader 5 EXNESS` (portable, build 6272); account demo
  `414***68` on `Exness-MT5Trial6` (hedging). Symbols carry the Exness `m` suffix:
  **`EURUSDm` + `USDJPYm`** (trade these exactly). MCP transport live — terminal
  `127.0.0.1:22346`, MetaEditor `127.0.0.1:22345`, single local key kept only in gitignored
  configs (`.mcp.json`, `.codex/config.toml`, user OpenCode config). Old MetaQuotes terminal
  uninstalled + cleaned after rescuing its chart profiles.
- **Balance granularity — RESOLVED (owner, 2026-10-17):** Exness offers Standard Cent only
  as **real** accounts — there is no cent **demo** — so the desk keeps the standard demo and
  the owner topped it up to **USD 10,000**, which is mathematically equivalent to a cent
  account at USD 100 (every risk-relevant quantity — min lot, pip value, notional — scales
  by exactly ×100, so 0.75–1% sizing granularity is identical). Owner mapping:
  **real-money equivalent = desk balance ÷ 100**; the owner's 1%-max-risk rule applies in
  desk terms (default 0.75% per trade). Desk E₀ = 10,000 now matches the live demo 1:1.
- **Transport note:** MT5 MCP servers (terminal + MetaEditor) are the agent-native route
  (trade + data + calendar + backtester as tools); the Python `MetaTrader5` package stays
  the deterministic-pipeline route (`paper/broker_mt5.py`). Both talk to the same terminal.

### 5.10 Owner directives (2026-10-17 night) — autonomous demo phase, intraday-first

- **Approval gate removed for the demo phase** (owner): the agent executes trades autonomously
  on the demo within the guardrails (risk/concurrency caps, kill-switches, blackouts, full
  receipts) — those replace per-trade approval as the control surface. Any real-money phase, or
  owner request, re-enables the explicit human gate.
- **Intraday-first management:** most trades target ≤8h; hard horizon cap **T+5**. Scale-out
  50% at 1R → SL to break-even (risk-free) → 1.2×ATR_H1 chandelier trail placed beyond
  structure (liquidity-hunt-avoidant). Early-cut triggers + time stops. No emotion; every move
  rule-receipted.
- **Confidence = binary checklist** (14 Y/N checks: 5 hard gates + 9 scored; grades A/B/C;
  only A/B trade; grade sizes risk). Deep research packet mandatory per candidate: news/calendar
  scan, multi-timeframe read (D1→H4→H1→M15), bull/bear/neutral cases each with falsifiers.
- **Multi-timeframe confirmation** required (≥2 of D1/H4/H1 aligned for grade A; no TF
  contradicting for B).
- Operating manual + agent prompts: **`docs/DESK_TRADING_PLAYBOOK.md`** (procedure this plan
  executes under); parameters mirrored in `paper/config.py` (`TradingLimits`).
- **Risk model v2 + adaptation (owner directives, later on 2026-10-17):** per-slot risk ceilings
  5% / 4% / 3% / 3% → **15% max open risk at a single point in time**, scaled DOWN by checklist
  grade (A+ ×1.0, A ×0.8, B+ ×0.6, B ×0.45); **daily max loss −10%**; weekly kill −25%;
  **weekly target +50% — tracked actual-vs-target every week, never a guarantee**; **operator
  score** — asymmetric penalty/reward (losses punished heavier than wins reward, process
  violations −20, kill-switch day −15) gating the autonomy envelope (≥85 full / 60–84: A,A+
  only + 0.75× slots / <60: pause). Every decision records the operator id so any AI model is
  comparable — the better-scoring operator earns more envelope. Instrument widening authorized
  for the desk only (research pipeline 3-pair lock untouched); first research family: SU-R1
  relative value across correlated majors.
- Strategy doctrine: **`docs/DESK_STRATEGY_FRAMEWORK.md`** — "regime-anchored liquidity/structure
  trading": lab regime models for *when/which direction*, market structure & liquidity for
  *where*, checklist execution for *when/how big*, scorecard for *what survives*; SMC kept only
  in falsifiable form (sweeps, pools — no order-block dogma).

---

### 5.11 Audit amendment (2026-10-18; supersedes readiness claims above)

See `docs/DESK_AUDIT_AND_IMPROVEMENT.md` for findings, implemented fixes and ordered gates.
Framework 1.1 / playbook 0.3. No unattended execution readiness: autonomous research/shadow
proposals only until independent admission, authoritative inputs, reconciliation,
management/watchdog, settlement and strategy graduation are verified end to end.

New pure modules: `paper/admission.py`, `paper/operator_score.py`, `paper/evidence.py`.
They are not wired to an executor/ledger adapter. Checklist eligibility is not order
authorization; version stamps are not proof of specification reading. Both child orders
share ONE parent's initial risk; all position/slot limits count parents. Remaining daily
and weekly loss capacity dominates the 15% open-risk cap. Operator safety history persists
across model swaps; profitable trades cannot erase an unreviewed breach or latched pause.
Production AI telemetry writes and replay/calendar/eval defects need separate remediation;
do not call the default production AI chain from the private desk as a read-only path.

### 5.12 Autonomous evolution design (owner decision 2026-10-18)

Owner permits automatic promotion of independently validated improvements into DEMO
operation, not changes to its own evaluator/hardlimits or real-money permissions.
Detailed private implementation draft: `docs/plans/2026-10-18-autonomous-demo-desk.md`
and `docs/specs/autonomous-desk/`. Its task packets supersede this older plan's vague
implementation steps for the autonomous extension, but do not alter IDENTITY/MASTERPLAN.
This is specification work only; execution readiness remains unproved. Runtime evolution
is allowlisted artifact selection, not self-editing Python or unattended policy changes.

## 6. Phases (effort = focused sessions, not calendar promises)

### P0 — Foundations (1–2 sessions)

- [x] `paper/config.py`: pairs, costs, risk defaults, horizons, model-version guard (`2.0-live` only for live).
- [x] MT5 spike: terminal detect/connect + `EURUSDm`/`USDJPYm` verified; live spread sampling
      runs Monday (market closed at build time). `pipeline/scripts/desk_mt5_spike.py`.
- [x] `paper/store.py`: local SQLite (`data/desk/`, gitignored) — append-only hash-chained ledger +
      refreshable bar cache; JSON receipts to `reports/desk/` (committed; genesis receipt landed).
- [x] `paper/prices.py` + `scripts/desk_prices_sync.py`: broker D1 bars into the local store
      (EURUSDm + USDJPYm, 2018-07-03 → 2026-10-16, 2×2588 bars, 0 quarantined; OHLC sanity +
      ±10%/day jump quarantine). Supabase `historical_prices` refresh deferred (no prod writes).
- [ ] Convert this audit's probes into `pipeline/scripts/desk_audit_snapshot.py` (read-only, repeatable).
- [ ] Tests: bounds/quarantine unit tests — **done** (15 tests, store + prices); spot cross-check
      vs `signals.spot` still to come.

### P1 — Strategies & backtests (2–4 sessions)

- [ ] `paper/simulate.py`: bars + optional replay signals; next-open entries; cost model; horizon sweep.
- [ ] S1/S2 from `layer2/layer3` (call unchanged); S3/S4/S5 implementations.
- [ ] Baselines S0a/S0b; per-pair + per-regime buckets; MAE/MFE; reports to `reports/desk/research/`.
- [ ] S5 research spike on the 3 pairs (swing/sweep features).
- [ ] `paper/scorecard.py` with CIs + baselines.

### P2 — Paper account (2–3 sessions)

- [ ] Proposals from live calls + strategy cohort; approvals recorded.
- [ ] Fills, positions, stops/invalidation/horizon exits, MTM, equity curve.
- [ ] Weekly scorecards; Stage-1 shadow running end-to-end (no risk budget yet).
- [ ] Owner switches Stage-2 risk budget on for graduated strategies (explicit gate).

### P3 — Agent layer (2–3 sessions)

- [ ] `paper/cli.py` + `paper/mcp_server.py`; `.mcp.json` snippet for the local agent.
- [ ] Desk note (reader/fallback) + chart pack; daily ops doc (`docs/DESK_OPERATIONS.md`).
- [ ] Optional: validate TradingView visual-review channel.

### P4 — Operate & extend (ongoing)

- [ ] Daily/weekly cadence; scorecard-driven promote/cut; pause rules enforced.
- [ ] Parked decisions surfaced: reader provider refresh; glitch-row supersession; MTM-walk revival for
      `strategy_ledger` (or fold into paper MTM); optional promotion of paper state to Supabase/Prefect.
- [ ] Real-money feasibility study — only if ever wanted, as a separate approved step with an IDENTITY review.

---

## 7. Definition of done for "we take (paper) trades"

1. P0–P2 complete; Stage-1 shadow produced ≥ 2 weeks of clean daily records.
2. Scorecard shows every strategy vs baselines with costs, per pair, CIs — no cherry-picking.
3. Owner has approved risk budget for graduated strategies; every order carries approval + hash receipt.
4. The desk runs daily with a live agent reading data, writing notes, and proposing trades; owner executes
   approvals; settlements + MTM + weekly scorecards appear automatically.
5. Nothing public changed; production data untouched (append-only proofs intact).

---

## 8. Risks & limits (named honestly)

- **Small live sample** — current live record is ~3.5 months; CIs are wide; conclusions early.
- **Backfill lookahead** — replay rows are research-grade; results may be optimistic; live shadow is the
  honest test.
- **Data hygiene** — 12 corrupted validation rows; stale OHLC; weekend-only calendars. Mitigated by desk-side
  quarantine + own price pipeline.
- **Bias risk** — USDJPY 100/100 BEARISH style skew; the desk must keep per-pair scoreboards to expose this.
- **Discipline** — paper systems are easy to abandon or fudge; receipts + gates + baseline comparisons are the
  guardrails.
- **Provider dependency** — reader prose depends on an LLM provider; fallback works meanwhile.
- **USDINR realism** — spreads/limits/onshore session are much harsher than majors; costs default wide (15 bps)
  to stay honest.

---

## 9. What this is NOT

- Not real-money trading — MetaTrader 5 usage is demo-only (paper with real market mechanics, §5.9); live
  execution is a separate future decision.
- Not a public product change — the website and methodology stay exactly as they are.
- Not a new pair / new signal-model change; not a Prefect production change without separate approval.
- Not a promise of profit — it is a measurement machine that trades paper to decide what deserves risk.
- Not paid evaluation infrastructure; no third-party paid data without an explicit decision.

---

## 10. Reproducing this audit

Read-only queries (Supabase REST via `pipeline/scripts/ledger_snapshot.py` helpers) on: `regime_calls`
(count 19,506; live `2.0-live` = 341; latest per pair), `validation_log` (non-superseded live window;
direction hits; glitch scan `|log_return_t5_bps| > 500` — exactly 12 rows), `validation_stats` (as-of
2026-10-17 rows), `strategy_ledger` (441 rows; 85 with MTM; range ends 2026-05-27), `signals` (spots +
`realized_vol_rank`), `historical_prices` (coverage per pair; last date 2026-06-29). Audit scripts ran from
the session temp dir; P0 formalizes them into a committed read-only tool.

---

## 11. Decisions needed from owner (defaults are my recommendation)

| # | Decision | Options | Default |
|---|---|---|---|
| 1 | Paper state store | **Local SQLite + receipts (recommended)** vs Supabase tables | Local SQLite |
| 2 | Paper equity & risk | E₀ and risk % per trade | 10,000 / 0.75% |
| 3 | Entry/exit semantics | Next-open entry; stop→invalidation→horizon | As stated |
| 4 | Cost model | Conservative 1.0/1.2/15 bps round-trip vs validation's 0.2/0.3/10 | Conservative |
| 5 | First strategy cohort | S1+S2 (house) + S3 (trend) + S4 (mean-rev) in shadow; S5 research-only | As stated |
| 6 | Chart channel | Local charts first; TradingView visual review later (**validate**) | Local first |
| 7 | Branch | Continue on `fx-live-personal` vs new `paper-desk` branch | Continue on `fx-live-personal` |
| 8 | Reader provider refresh | Now / later / skip (fallback is fine) | Later |
| 9 | MetaTrader 5 | Data-only / **data + demo execution** / skip | Data + demo execution |

> **Resolved (2026-10-17):** owner accepted all defaults ("GO"). Scope narrowing: the desk's trading
> universe is **EURUSD + USDJPY only** — no USDINR execution (research pipeline keeps the 3-pair lock).

---

## 12. Receipts & references

- `reports/REPAIR_CHECKPOINT.md` (packets 1–7): repair, proofs, merge, publish records.
- `reports/ledger_snapshot_after_live_green.json` + `reports/ledger_snapshot_full.json` — append-only proof.
- `reports/llm_reader_eval_v3_latest.md` / `.json` — reader eval on fresh calls.
- `docs/FX_LIVE_PERSONAL_TASK.md` — the task this plan extends.
- `docs/DB_STATUS.md` — live schema reference; `docs/SIGNAL_DEFINITIONS.md` — signal math.
- Merge: PR #20 → `83d03559 fa79e8cf b5abf067 9cad9cb5 666213b6`; tag `v2.1-archive` = `b0d33cd` (unmoved).
- Audit prepared 2026-10-17 on `fx-live-personal` @ `519ef2e` (working tree clean, in sync with origin).
