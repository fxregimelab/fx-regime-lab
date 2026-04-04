# FX REGIME LAB — COMPLETE BUILD PLAN
> Phase-by-phase implementation plan from current state to full quantamental intelligence platform. Read CONTEXT.md first. This file governs what gets built, in what order, and why.

**Repo paths:** Planning docs live under **`contaxt files/`** (folder name in this repository). Same content may be referred to elsewhere as “context files.”

**Spec precedence:** CURSOR_RULES → PLAN → CONTEXT → AGENTS.md when documents conflict.

---

## CURRENT STATE SNAPSHOT

- Pipeline runs daily via GitHub Actions ✅
- EUR/USD, USD/JPY, USD/INR covered ✅
- Rate differentials, COT, realized vol, cross-asset correlations live ✅
- Public domain **fxregimelab.com** live (DNS → **Cloudflare Pages** target) ✅ / in progress
- **Phase 0A target:** full **fxregimelab.com** UI shell (Bloomberg-style dark, placeholders) on Cloudflare Pages **before** any Supabase Python work ⚠️
- GitHub Pages: static brief via `deploy.py` until Cloudflare + cutover plan complete ⚠️
- Data stored in CSVs (temporary — migration required) ⚠️
- No implied vol signal ❌
- No risk reversal signal ❌
- No COT lead indicator (OI delta) ❌
- No out-of-sample validation log ❌
- No paper trading ❌
- No Supabase database ❌
- No live public performance dashboard ❌

---

## PHASE 0 — PUBLIC SITE + DATA LAYER
**Mandatory order:** **Phase 0A** (UI shell + branding on **Cloudflare Pages**, static placeholders) → **Phase 0B** (Supabase DDL, RLS, Python dual-write, live reads). **Do not start 0B until 0A is deployed and verified on fxregimelab.com.**  
**Phase 1** (new signal modules) stays blocked until **combined Phase 0 exit criteria** at the end of this section pass.

GitHub Actions / `run.py` pipeline continues; `deploy.py` may write **`static/pipeline_status.json`** (or agreed path) with **last run timestamp** for the `/dashboard` status board in 0A.

---

### Phase 0A — UI shell ships first (no Supabase required)

Ship the full site structure, **Bloomberg Terminal–inspired** dark UI (data-dense, sharp edges, no gradients / glassmorphism / generic SaaS hero). **Placeholder copy and static regime cards** are designed—not blank pages.

**Recommended repo location:** static site source under **`site/`** (or Pages project build output) deployed by Cloudflare Pages from this repo.

**Site map**

| Path | 0A behavior |
|------|-------------|
| `/` | Landing: wordmark header nav, hero, **3 regime cards** (static placeholder data, correct colors/type), methodology strip (4 signals), latest brief preview (static or link), footer |
| `/dashboard` | **Designed “live integration” status board** — checklist of signal groups; **pipeline last run** read from `pipeline_status.json` produced by CI/`deploy.py` (real timestamp, not fake countdown) |
| `/brief` | Embed, iframe, or **link** to current morning brief (GitHub Pages URL acceptable until `/brief` hosts artifact) |
| `/performance` | **Coming soon** card (Q3 2026 target, regime validation framing, CTA → `/newsletter`) |
| `/about` | **Coming soon** — methodology blurb + pointer to SSRN timeline |
| `/newsletter` | **301 redirect** to `https://fxregimelab.substack.com` (Cloudflare Pages redirect rule). Footer/nav “Newsletter” targets this path. |

**Public site design tokens (fxregimelab.com — use for Pages; keep Plotly/brief tokens aligned where possible)**

```
Background primary:    #0a0e1a
Background card:       #0d1117
Background elevated:   #111827
Border default:        #1e293b
Border subtle:         #161e2e

EUR/USD:               #4da6ff
USD/JPY:               #ff9944
USD/INR:               #e74c3c
GBP/USD (future):      #10b981
Gold:                  #f0a500
Positive:              #10b981
Negative:              #ef4444
Neutral:               #6b7280

Text primary:          #f9fafb
Text secondary:        #9ca3af
Text muted:            #6b7280
Text label:            #4b5563

Font UI:               Inter (Google Fonts)
Font mono (figures):   JetBrains Mono
```

**Landing (`/`) content rules:** No generic “Get Started” SaaS CTAs. Primary CTA: **“View Live Dashboard →”**. Header: logo left; nav **Dashboard · Brief · Performance · About · Newsletter**.

**Substack:** Redirect-only on `/newsletter` for now (free). Optional later: Substack RSS embed on landing (Phase 3).

---

### Phase 0B — Supabase wired; UI goes live

1. Create Supabase project; apply **DDL + indexes + RLS** below; `pipeline_errors` included.  
2. **Lazy Python client:** initialize Supabase only when URL + key present; **never raise on import**; skip remote write and log warning if keys missing locally — pipeline stays non-blocking.  
3. `core/signal_write.py` — upsert (`on_conflict='date,pair'`), batching, `pipeline_errors`, CSV fallback.  
4. Dual-write from `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py` (+ merge) → `signals`.  
5. `persist_regime_call()` + `brief_log` stub from brief path.  
6. GitHub Secrets + `daily_brief.yml` `.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `CME_API_KEY`; cron **`0 23 * * *`**.  
7. **Wire live data:** landing regime cards + `/dashboard` replace placeholders with **anon-key** Supabase reads (explicit columns, RLS).  
8. Cloudflare Pages env: `SUPABASE_URL`, `SUPABASE_ANON_KEY` for browser client.

**Orchestrator truth:** [run.py](run.py) — `fx → cot → inr → merge → text → macro → ai → html → deploy`. No `create_dashboards.py`.

**CI cron:** `0 23 * * *` UTC daily (`.github/workflows/daily_brief.yml`).

### DDL — Supabase tables, indexes, RLS

Apply in the Supabase SQL editor (tables below match this repo’s Phase 0 spec):

```sql
-- Daily signal data per pair
CREATE TABLE signals (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,          -- 'EURUSD', 'USDJPY', 'USDINR', 'GBPUSD'
  rate_diff_2y FLOAT,                  -- 2Y rate differential (basis points)
  rate_diff_10y FLOAT,                 -- 10Y rate differential
  rate_diff_zscore FLOAT,              -- 5-day change z-score, 60-day trailing window
  cot_lev_money_net BIGINT,            -- Leveraged money net contracts
  cot_asset_mgr_net BIGINT,            -- Asset manager net contracts
  cot_percentile FLOAT,                -- Percentile rank, 52-week rolling
  realized_vol_5d FLOAT,               -- 5-day realized vol (annualized)
  realized_vol_20d FLOAT,              -- 20-day realized vol
  implied_vol_30d FLOAT,               -- CME CVOL 30-day implied vol
  vol_skew FLOAT,                      -- CME CVOL Skew (UpVar - DnVar)
  atm_vol FLOAT,                       -- CME CVOL ATM vol
  risk_reversal_25d FLOAT,             -- Synthetic 25-delta risk reversal (yfinance FXE)
  oi_delta INT,                        -- CME daily OI change vs prior day
  oi_price_alignment VARCHAR(10),      -- 'confirming', 'diverging', 'neutral'
  cross_asset_vix FLOAT,               -- VIX close
  cross_asset_dxy FLOAT,               -- DXY index close
  cross_asset_oil FLOAT,               -- Brent crude close
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Regime calls — one row per pair per day
CREATE TABLE regime_calls (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  pair VARCHAR(10) NOT NULL,
  regime VARCHAR(30) NOT NULL,         -- 'TRENDING_LONG', 'TRENDING_SHORT', 'MEAN_REVERTING', 'VOL_EXPANDING', 'CRISIS', 'NEUTRAL'
  confidence FLOAT,                    -- 0.0 to 1.0
  signal_composite FLOAT,             -- weighted composite score
  rate_signal VARCHAR(10),             -- 'BULLISH', 'BEARISH', 'NEUTRAL'
  cot_signal VARCHAR(10),
  vol_signal VARCHAR(10),
  rr_signal VARCHAR(10),
  oi_signal VARCHAR(10),
  primary_driver TEXT,                 -- free text, e.g. "crowded long unwind + vol expansion"
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Out-of-sample validation log — the SSRN paper results section
CREATE TABLE validation_log (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,                  -- date regime call was made
  pair VARCHAR(10) NOT NULL,
  predicted_direction VARCHAR(10),     -- 'LONG', 'SHORT', 'NEUTRAL'
  predicted_regime VARCHAR(30),
  confidence FLOAT,
  actual_direction VARCHAR(10),        -- filled next trading day: 'UP', 'DOWN', 'FLAT'
  actual_return_1d FLOAT,             -- next day % return
  actual_return_5d FLOAT,             -- 5-day forward return
  correct_1d BOOLEAN,                 -- prediction matched 1-day outcome
  correct_5d BOOLEAN,                 -- prediction matched 5-day outcome
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Paper trading positions
CREATE TABLE paper_positions (
  id SERIAL PRIMARY KEY,
  opened_date DATE NOT NULL,
  closed_date DATE,
  pair VARCHAR(10) NOT NULL,
  direction VARCHAR(10) NOT NULL,      -- 'LONG', 'SHORT'
  entry_price FLOAT NOT NULL,
  stop_loss FLOAT NOT NULL,
  target_1 FLOAT,
  target_2 FLOAT,
  target_3 FLOAT,
  invalidation_thesis TEXT,
  conviction_level VARCHAR(10),        -- 'HIGH', 'MEDIUM', 'LOW'
  regime_at_entry VARCHAR(30),
  status VARCHAR(20),                  -- 'OPEN', 'CLOSED_TP', 'CLOSED_SL', 'CLOSED_MANUAL'
  exit_price FLOAT,
  pnl_pips FLOAT,
  pnl_pct FLOAT,
  r_multiple FLOAT,                    -- outcome in R (risk units)
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Morning brief metadata log
CREATE TABLE brief_log (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  brief_text TEXT,                     -- full morning brief content
  eurusd_regime VARCHAR(30),
  usdjpy_regime VARCHAR(30),
  usdinr_regime VARCHAR(30),
  macro_context TEXT,                  -- key macro events driving the brief
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline failure audit (required by CURSOR_RULES; not in original PLAN v1)
CREATE TABLE pipeline_errors (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL DEFAULT CURRENT_DATE,
  source VARCHAR(50) NOT NULL,
  pair VARCHAR(10),
  error_message TEXT NOT NULL,
  notes TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes to add:**
```sql
CREATE INDEX idx_signals_date_pair ON signals(date, pair);
CREATE INDEX idx_regime_calls_date_pair ON regime_calls(date, pair);
CREATE INDEX idx_validation_date_pair ON validation_log(date, pair);
CREATE UNIQUE INDEX idx_signals_unique ON signals(date, pair);
CREATE UNIQUE INDEX idx_regime_unique ON regime_calls(date, pair);
CREATE UNIQUE INDEX idx_validation_unique ON validation_log(date, pair);
CREATE INDEX idx_pipeline_errors_date_source ON pipeline_errors(date, source);
CREATE UNIQUE INDEX idx_brief_log_date ON brief_log(date);
```

**Row Level Security (before public dashboard exposure):**
```sql
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE regime_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE brief_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_errors ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read_signals" ON signals FOR SELECT USING (true);
CREATE POLICY "public_read_regime" ON regime_calls FOR SELECT USING (true);
CREATE POLICY "public_read_validation" ON validation_log FOR SELECT USING (true);
CREATE POLICY "public_read_positions" ON paper_positions FOR SELECT USING (true);
-- brief_log: add SELECT policy if/when the site reads it; pipeline_errors: no public read
```

CI uses **`SUPABASE_SERVICE_ROLE_KEY`** (bypasses RLS). Public **fxregimelab.com** uses **anon key** in the browser — SELECT-only policies as above. Cloudflare Pages also supports **Workers** for future server-side behavior; not required for read-only Supabase JS + RLS.

### DNS, Pages deploy, and GitHub Pages
- **DNS:** Cloudflare recommended; preserve **MX** for **shreyash@fxregimelab.com** if moving nameservers.
- **Pages:** connect repo — **0A** can ship **without** Supabase env; add `SUPABASE_*` for anon in **0B**.
- **GitHub Pages:** keep `deploy.py` brief push until **10+** clean days after live Supabase + site wire-up; then archive-only optional; **fxregimelab.com** canonical.

### Phase 0 combined exit criteria (all before Phase 1)
**0A — UI shell**
- [ ] fxregimelab.com on Cloudflare Pages with SSL; **www** policy explicit (redirect OK)
- [ ] All routes live: `/`, `/dashboard`, `/brief`, `/performance`, `/about`, **`/newsletter` → 301 Substack**
- [ ] Bloomberg-style layout: wordmark, nav, mobile responsive, designed placeholders (not blank)
- [ ] Landing: **3 static regime cards** (correct tokens); `/dashboard` status board shows **real** last pipeline time via **`pipeline_status.json`** (or agreed path) from CI / `deploy.py`
- [ ] `/brief` points at current brief (embed, iframe, or link to GitHub Pages)
- [ ] Email verified after any DNS change

**0B — Data + live UI**
- [ ] One CI run upserts EUR/USD, USD/JPY, USD/INR into `signals` without CSV regression
- [ ] `regime_calls` one row per pair for run date; `brief_log` stub if scoped
- [ ] Forced failure logs to `pipeline_errors` without killing the job
- [ ] RLS: anon SELECT ok; INSERT denied
- [ ] Landing + `/dashboard` show **live** Supabase reads (replace placeholders)

---

## PHASE 1 — VOL AND RISK SIGNAL LAYER
**Priority: After Phase 0A + 0B exit criteria are met.**  
**Goal:** Add the three missing signal dimensions: implied vol, directional skew, and COT lead indicator; ship dashboard panels on deploy.

### 1.1 CME CVOL Pipeline (`vol_pipeline.py`)

**What it detects:** Forward-looking implied volatility regime and directional asymmetry  
**Why a PM uses it:** Vol regime determines whether signals are in a trending or uncertain environment. High IV + rising skew = options market pricing directional risk. Low IV complacency with high COT crowding = squeeze setup.  
**Data source:** CME CVOL EOD REST API (free with registration at cmegroup.com/market-data/market-data-api.html)  
**Auth:** OAuth API key — store as GitHub Actions secret `CME_API_KEY`  
**Pairs covered:** EUR/USD (EURUSD CVOL), USD/JPY (USDJPY CVOL)

**Outputs per pair per day:**
- `implied_vol_30d` — primary CVOL index (annualized std dev, 30-day forward)
- `vol_skew` — UpVar minus DnVar (positive = upside risk priced higher, negative = downside risk priced higher)
- `atm_vol` — at-the-money vol component
- `vol_percentile` — CVOL vs 52-week history (same logic as COT percentile)
- `vol_regime` — derived classification: LOW (<25th pct), NORMAL (25–75th), ELEVATED (75–90th), CRISIS (>90th)

**Signal interpretation:**
- CVOL elevated + skew negative (puts bid) + COT crowded long → unwind imminent, high conviction short
- CVOL low + skew neutral + rate diff directional → carry regime, trend following valid
- CVOL spiking + skew flipping → regime break incoming, reduce all positioning

**Failure modes to watch:** CVOL uses listed futures options — can diverge from OTC interbank vol during stress. Cross-check against realized vol z-score. If CVOL and realized vol diverge by >5 vol points, flag in morning brief.

### 1.2 CME Daily OI Delta Pipeline (`oi_pipeline.py`)

**What it detects:** Daily flow direction inference — who is entering or exiting positions  
**Why a PM uses it:** Solves the 3-day COT lag. OI drop on down days = longs exiting (bearish confirmation). OI rise on up days = new longs building (bullish confirmation). OI divergence from price = institutional positioning against the move.  
**Data source:** CME website daily OI report (free, scrapeable)  
**URL pattern:** `https://www.cmegroup.com/CmeWS/mvc/Volume/getVolumeDownload.do` or CME daily bulletin  

**Outputs per pair per day:**
- `oi_total` — total open interest in contracts
- `oi_delta` — day-over-day change
- `oi_price_alignment` — 'confirming' (OI up + price up, or OI up + price down), 'diverging' (OI down into move), 'neutral'
- `oi_5d_trend` — 5-day OI change direction

**Signal interpretation:**
- OI falling + price rising → short covering rally, not new longs — weak signal, caution
- OI rising + price rising → new longs building — strong bullish signal
- OI falling sharply at 97th percentile COT crowding → unwind in progress — high conviction

### 1.3 Synthetic Risk Reversal Pipeline (`rr_pipeline.py`)

**What it detects:** Options market directional sentiment — call premium vs put premium  
**Why a PM uses it:** 25-delta risk reversal is the standard FX options skew metric. When calls are bid over puts, market is pricing upside risk. When puts are bid, market expects downside. This leads COT by 3–7 days at turning points.  
**Data source:** yfinance → FXE (EUR/USD ETF) options chain  
**Method:**
1. Pull FXE options chain for nearest 30-day expiry
2. Find 25-delta call and 25-delta put (interpolate from delta curve)
3. Compute RR = IV(25D call) - IV(25D put)
4. Store daily. Compute 20-day rolling percentile.

**Important caveat:** FXE listed options ≠ OTC interbank RR. Directionally correct, not identical. Flag this clearly in the morning brief and SSRN paper. Labeled "synthetic RR proxy" everywhere.

**Outputs per pair per day:** (EUR/USD only via FXE — extend to JPY via FXY when stable)
- `risk_reversal_25d` — RR in vol points
- `rr_percentile` — vs 52-week history
- `rr_direction` — 'CALLS_BID', 'PUTS_BID', 'NEUTRAL'
- `rr_regime_signal` — derived: 'BULLISH_SKEW', 'BEARISH_SKEW', 'NEUTRAL'

### 1.4 Phase 1 exit criteria

- [ ] `vol_pipeline.py`, `oi_pipeline.py`, `rr_pipeline.py` run in CI without breaking prior steps (`run.py` order: after `inr`, before `text` unless dependencies dictate otherwise)
- [ ] New columns populated in Supabase `signals` for EUR/USD and USD/JPY for 5+ consecutive days
- [ ] **fxregimelab.com/dashboard** shows vol regime, synthetic RR (caveat label), and OI panels
- [ ] Morning brief mentions vol regime and synthetic RR proxy with caveat
- [ ] No new pip dependencies without explicit approval

---

## PHASE 2 — OUT-OF-SAMPLE VALIDATION LOG
**Priority: Runs in parallel with Phase 1. Not sequential — start immediately.**  
**Goal:** Build the SSRN paper results section automatically from day one.

Every day after pipeline runs:
1. Write today's regime call to `regime_calls` table with timestamp
2. Predicted direction logged: LONG / SHORT / NEUTRAL per pair
3. Next trading day: fetch actual price return, compute 1D and 5D outcomes
4. Write to `validation_log` table: predicted vs actual, correct/incorrect flags
5. Cumulative accuracy tracked: rolling 20-day hit rate, 60-day hit rate, full history hit rate

**Morning brief — first line after header (non-negotiable):**  
`Regime Accuracy (last 20 days): EUR/USD X% | USD/JPY X% | USD/INR X%`  
Also show rolling accuracy on **fxregimelab.com/dashboard**.

This is the live audit trail. It cannot be faked, backdated, or cherry-picked — which is exactly the point.

---

## PHASE 3 — DASHBOARD AND BRIEF UPGRADE
**Priority: After Phase 1 signals are stable in Supabase.**  
**Goal:** Dashboard pulls live from Supabase. Morning brief reads as institutional research, not data dump.

### 3.1 Dashboard on fxregimelab.com (`/dashboard`) + Supabase live feed
- Host on **Cloudflare Pages**; dashboard fetches from Supabase via REST / JS client at load (anon key, explicit column queries)
- New sections: Signal heatmap (all pairs × all signals), Vol regime panel, RR skew panel, OI flow panel
- Validation log summary: rolling accuracy for each pair
- Paper trading performance (when live): equity curve, drawdown, R-multiple distribution — also **`/performance`**

### 3.2 Morning brief — locked template
**Required structure — every brief:**
```
[DATE] | [MACRO CONTEXT — 1 sentence max]

REGIME CALL ACCURACY (last 20 days)
EUR/USD: X% | USD/JPY: X% | USD/INR: X%

REGIME CALLS
EUR/USD:  [REGIME] | Confidence: X% | Change vs yesterday: [Yes/No]
USD/JPY:  [REGIME] | Confidence: X%
USD/INR:  [REGIME] | Directional only — RBI intervention distortion

KEY SIGNAL CHANGES [materially changed signals only]
[Signal]: [Previous] → [Current] | Implication: [1 sentence]

CROSS-ASSET CONTEXT [only if regime-relevant]
Oil/VIX/DXY: 1 sentence each

ACTIVE PAPER POSITIONS [empty until Phase 4]
[Pair | Direction | Entry | Current | P&L in R]

WATCH LIST [1–2 setups forming, not yet triggered]
```
Footer: `Source: FX Regime Lab Pipeline · fxregimelab.com` (Substack may appear in other surfaces; keep institutional tone.)

### 3.3 `/about` — methodology page
One paragraph per signal: what it measures, why a macro PM uses it, high/low meaning, divergences. This is the default answer to “how does this work?”

### 3.4 GitHub Pages vs Cloudflare
After **10+** consecutive clean days on Cloudflare Pages, narrow GitHub Pages to static brief archive if desired; **fxregimelab.com** stays canonical for live dashboard and brief.

---

## PHASE 4 — PAPER TRADING DEPLOYMENT
**Priority: After Phase 3 brief structure is clean.**  
**Goal:** Deploy systematic paper trades based on regime signals. Log publicly. Build live track record.

### 4.1 Paper Strategy Rules
**Entry conditions (all must be met):**
1. Regime signal: TRENDING regime with confidence >0.65
2. Rate differential: directional and z-score >1.5
3. COT percentile: not in extreme crowding (avoid >90th percentile longs for new longs)
4. Vol regime: NORMAL or LOW (elevated vol = wait for entry, not pile in)
5. RR skew: directionally aligned with trade direction
6. OI delta: confirming (not diverging)

**Position management:**
- Risk per trade: fixed (defined in regime-conditional sizing model — Phase 7)
- Stop: invalidation thesis level, not arbitrary pip count
- Partial exit: 50% at 1:1 R, move stop to breakeven on remainder
- Runner: trailing stop on residual position

**Logging to Supabase:** Every position opened and closed with all six elements documented. Public dashboard shows live equity curve.

### 4.2 MT5 / MQL5 Integration
- Python pipeline writes JSON signal file after each run
- MQL5 EA reads JSON, checks entry conditions, executes if met
- EA writes trade log back to file → Python reads → stores to Supabase
- This is the existing architecture from the algo trading session — extend it, don't rebuild

---

## PHASE 5 — SYSTEMATIC BACKTESTING LAYER
**Priority: After Python Phase 4 complete (Python sprint Day 60+).**  
**Goal:** Backtest regime signal combinations against historical FX returns. Produce performance statistics for SSRN paper.

**Framework:** Custom backtesting in Python using pandas — not Zipline or Backtrader (adds unnecessary dependency). Simple vectorized backtesting is sufficient for daily signals.

**Required outputs:**
- Annualized return per regime type per pair
- Sharpe ratio (annualized)
- Max drawdown
- Hit rate (% of signals that produced positive return at 1D and 5D horizon)
- Signal combination performance (rate diff + COT vs rate diff + COT + vol vs full stack)
- Comparison to carry benchmark (long high-yielder, short low-yielder)

**Data sources:** Historical FRED data (already in pipeline), historical COT from CFTC bulk download, historical FX prices from yfinance

---

## PHASE 6 — PAIR EXPANSION (GBP/USD)
**Priority: After backtesting layer is stable.**  
**Goal:** Add fourth pair. GBP/USD chosen because: BoE policy divergence from Fed and ECB is a live macro theme, positioning data is clean in CFTC, and GBP is highly liquid with active options market.

**New pipeline additions:**
- `gbpusd_pipeline.py` — rate differential (US-UK 2Y and 10Y from FRED)
- COT: GBP futures, same Leveraged Money + Asset Manager split
- CVOL: CME GBP CVOL (if available via same API endpoint)
- Synthetic RR: via FXB ETF options on yfinance (GBP/USD proxy)
- All outputs write to same Supabase schema with pair='GBPUSD'

---

## PHASE 7 — NLP SENTIMENT LAYER (FinBERT)
**Priority: Sem 7, approx. July–November 2027. After SSRN paper is drafted.**  
**Goal:** Extract directional sentiment from central bank communications. Add as a regime input.

**Target documents:**
- FOMC statements and minutes (8x per year)
- ECB press conference transcripts (8x per year)
- BoJ policy statements (8x per year)
- BoE MPC minutes (8x per year)

**Implementation:**
- Use `transformers` library with `ProsusAI/finbert` model
- Fine-tune on central bank corpus for hawkish/dovish classification
- Output per document: hawkish_score, dovish_score, neutral_score, net_sentiment
- Store to Supabase `central_bank_sentiment` table
- Integrate into morning brief: "ECB tone: [Hawkish/Dovish/Neutral] — [key phrase flagged]"
- Compare sentiment shift vs rate differential direction — divergence = early signal

**This is the AI showcase layer.** FinBERT on central bank minutes, integrated into a live pipeline, is what Point72, Brevan Howard, and Bloomberg Economics research teams build internally. This at student level, publicly documented, is a differentiator.

---

## PHASE 8 — ASSET CLASS EXPANSION (COMMODITIES + RATES)
**Priority: After NLP layer. MFE application period.**  
**Goal:** Expand cross-asset inputs from indicators to full regime signals. Move toward a true quantamental multi-asset intelligence platform.

### 8.1 Gold Regime Module
- Real rates (US 10Y TIPS yield from FRED) vs gold price — the core driver
- Gold/DXY correlation regime: when correlation breaks, it signals a regime shift
- Gold as safe haven validity checker: if gold falls with bonds and JPY simultaneously, it's a safe-haven failure regime (this is exactly what the Safe Haven Breakdown chart captured)

### 8.2 Oil Regime Module
- Brent crude daily via yfinance
- Oil/USD correlation: positive correlation = oil is driving USD (petrodollar regime), negative = USD is independent
- Oil/CAD driver: USD/CAD regime signal (prep for USD/CAD pair addition)
- Oil as inflation input: feeds into rate differential momentum expectations

### 8.3 Rates Curve Module
- US 2Y-10Y spread (yield curve shape) from FRED
- Inversion depth and duration as recession probability input
- Term premium estimate (ACM model from NY Fed — freely available)
- Cross-market: US-DE 10Y spread (already partially in rate differential module) — upgrade to full term structure comparison

---

## PHASE 9 — PUBLIC PRODUCT LAYER
**Priority: Post-MFE application. Long-term.**  
**Goal:** Convert from career asset to revenue-generating intelligence product.

### 9.1 Subscription Tiers
- **Free:** Daily regime call for one pair, 24-hour delay
- **Practitioner ($X/month):** Full signal stack, all pairs, morning brief, paper trading performance
- **Institutional (custom):** API access to Supabase signal data, historical backtested results, SSRN paper

### 9.2 Auth and Payments
- Supabase Auth for user management (already in Supabase free tier)
- Stripe for payments
- **Cloudflare Workers** (or Pages Functions) for API gating where needed
- Do not build this until track record is >12 months and SSRN paper is submitted

### 9.3 AI Usage Disclosure
Every public-facing page includes a clear statement: "The FX Regime Lab pipeline is built and maintained using AI-assisted development (Cursor, Claude). All signal logic, macro judgment, and trade construction are human-designed and human-validated. AI is used to accelerate implementation, not replace analytical judgment."

This is not a disclaimer — it's a feature. It demonstrates exactly the right level of AI fluency for a quantamental practitioner in 2026.

---

## COMPLETE BUILD SEQUENCE (SUMMARY)

| Phase | What | When |
|-------|------|------|
| 0A | UI shell on fxregimelab.com (Bloomberg-style, placeholders, `/newsletter` redirect) | **First — ship before Supabase code** |
| 0B | Supabase DDL/RLS + Python dual-write + live site reads + GHA secrets | After 0A verified |
| 1 | CVOL + OI + RR pipelines + dashboard panels | After **0A+0B** exit criteria |
| 2 | Out-of-sample validation log | **In parallel with Phase 1** |
| 3 | Full dashboard panels + locked brief + `/about` content | After Phase 1 stable ~10d |
| 4 | Paper trading deployment (MT5/MQL5 + Supabase logging) | After Phase 3 |
| 5 | Systematic backtesting layer | Python sprint Day 60+ |
| 6 | GBP/USD pair addition | After Phase 5 |
| 7 | FinBERT NLP sentiment layer | Sem 7, ~July 2027 |
| 8 | Commodities + rates cross-asset expansion | After NLP layer |
| 9 | Public product layer (subscription + auth + payments) | Post-MFE |
