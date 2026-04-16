# FX REGIME LAB — COMPLETE PROJECT CONTEXT
> This file is the single source of truth for the FX Regime Lab project. Every Cursor session starts here. Never deviate from the decisions, architecture, and philosophy documented below.

---

## 1. WHO THIS IS FOR

**Builder:** Shreyash Sakhare  
**Age:** 20  
**Degree:** B.Tech Electrical Engineering, AISSMS Institute of Information Technology Pune (SPPU-affiliated autonomous institution)  
**Graduation:** May 2028  
**Location:** Pune, India → Target relocation: Singapore or Dubai  

**Long-term target:** Own and run a quantamental macro fund by age 38. Net worth 100 crore+ (≈$12M USD) before 40. This is not a salary outcome — it is a carry, fund ownership, and track record outcome.

**Two-year mandate (2026–2028):** Build a profile that makes a top MFE application and a 6th semester boutique internship inevitable.

**Career path locked:** Quantamental macro — discretionary regime judgment combined with systematic signal execution. Not pure quant. Not pure discretionary. The hybrid is the point.

**Target MFE programs (in priority order):** NTU Singapore (primary), HKUST, SMU  
**CFA:** L1 passed February 2026. L2 registered May 2027 (self-study only). Stops at L2.  
**GRE:** Prep starts June 2026. Exam October 2026. Target 169–170 quant.

---

## 2. WHAT FX REGIME LAB IS

FX Regime Lab is a live, automated, daily G10 FX Regime Detection Framework. It is simultaneously:

1. **A research tool** — detects macro regime states across currency pairs using institutional-grade signals
2. **A career differentiator** — the primary credential that replaces the brand gap from a tier-3 Indian engineering college
3. **A public track record** — live out-of-sample predictions logged daily, forming the results section of a planned SSRN paper
4. **A future product** — designed from day one to scale into a subscription or sellable intelligence platform
5. **A quantamental showcase** — demonstrates the exact skill combination top funds hire for: deep macro knowledge + systematic signal engineering + AI/tech proficiency

**The framework must stay live and evolving at all times.** A dead pipeline is a dead career asset.

---

## 3. CURRENT FRAMEWORK STATE

### Pairs Covered
| Pair | Status | Notes |
|------|--------|-------|
| EUR/USD | Live | Primary pair, full signal stack |
| USD/JPY | Live | Full signal stack |
| USD/INR | Live | Directional only — no precision entries due to RBI intervention distortion |
| GBP/USD | Planned | Next pair to add after vol layer is stable |

### Current Signal Stack
| Signal | Source | Frequency | Status |
|--------|--------|-----------|--------|
| Rate Differentials | FRED (2Y and 10Y spreads) | Daily | Live |
| CFTC COT Positioning | CFTC.gov (Leveraged Money + Asset Manager) | Weekly (Tuesday snapshot, Friday release) | Live |
| Realized Volatility | Computed from price data | Daily | Live |
| Cross-Asset Correlations | Oil, equities, DXY vs FX pairs | Daily | Live |
| Implied Vol (FX) | CBOE FX vol indices (^EVZ, ^JYVIX) via yfinance | Daily | Live (EUR/USD, USD/JPY); INR falls back in merge |
| CME Daily OI Delta | CME open interest + price alignment | Daily | Live in `oi_pipeline.py` (pair coverage per implementation) |
| Risk reversal (25d) | yfinance FXE option chain proxy | Daily | Live in `rr_pipeline.py` (EURUSD-centric path) |
| NLP Sentiment | FinBERT on FOMC/ECB/BoJ minutes | Event-driven | **Future phase** |

### Current pipeline execution sequence (canonical: `run.py`)
```
fx → cot → inr → vol → oi → rr → merge → text → macro → ai → substack → html → validate → deploy
```
Scripts (in order): `pipeline.py`, `cot_pipeline.py`, `inr_pipeline.py`, `vol_pipeline.py`, `oi_pipeline.py`, `rr_pipeline.py`, `scripts/pipeline_merge.py`, `morning_brief.py`, `macro_pipeline.py`, `ai_brief.py`, `scripts/substack_publish.py`, `create_html_brief.py`, `validation_regime.py`, `deploy.py`. Charts ship via `create_html_brief.py` / `create_charts_plotly.py` (no `create_dashboards.py`).

### Current infrastructure
| Component | Current state | Target state |
|-----------|--------------|--------------|
| Domain | **fxregimelab.com** (GoDaddy); email **shreyash@fxregimelab.com** | DNS → **Cloudflare** (recommended) for Pages + SSL |
| Pipeline execution | GitHub Actions **`0 23 * * *` UTC** daily | Keep |
| Data storage | CSV under `data/` + optional **Supabase** upserts when secrets are set | **Supabase PostgreSQL** primary + CSV fallback |
| Public site | GitHub Pages serves repo-root `index.html` brief | **Cloudflare Pages** on **fxregimelab.com** — **Phase 0A:** full UI shell + placeholders **before** Supabase; **0B:** live reads |
| Database | Supabase optional (dual-write from pipelines when configured) | Hardened RLS + read paths for public site |
| Paper trading | Not yet live | MT5 via Exness demo, MQL5 EA → **`/performance`** |
| Public performance | Not yet live | Live Supabase-fed views on **fxregimelab.com** |

---

## 4. BRAND AND DESIGN SYSTEM

### Dashboard / Framework (Dark Theme)
Used for **Plotly morning brief**, `charts/`, and aligned with the public site.

```
Background:     #0a0e1a
Card:           #111827   (elevated cards may use #0d1117 on fxregimelab.com — see PLAN Phase 0A)
Border:         #1f2937
EUR/USD:        #4da6ff
USD/JPY:        #ff9944
USD/INR:        #e74c3c
Gold/Commodities: #f0a500
Accent green:   #10b981
Text primary:   #f9fafb
Text secondary: #9ca3af
Text muted:     #6b7280
Grid lines:     rgba(30,41,59,0.90)
Font:           Inter (all weights)
```

### Public site (fxregimelab.com — Cloudflare Pages)
**Bloomberg Terminal–inspired:** data-dense, sharp edges, tight spacing, **no** gradients, glassmorphism, or generic SaaS hero pages. **UI and branding ship in Phase 0A** before database wiring. Full token list and page specs: **PLAN.md Phase 0A**.  
**Newsletter:** **`/newsletter`** → 301 redirect to **fxregimelab.substack.com** (do not rely on Substack custom domain on free tier).

### Curriculum / Public-Facing (Light Theme)
```
Background:     #FAFAF5 (warm cream with ruled notebook lines)
Cards:          White
Accent:         #1B3A6B (navy)
Fonts:          Playfair Display, Lora, Inter, Caveat, JetBrains Mono
```

### Brand Rules
- Logo: FX Regime Lab wordmark (file: `logos/wordmark without bg.png`)
- Footer (pipeline HTML / institutional surfaces): **fxregimelab.com** and/or Substack as appropriate; see PLAN Phase 3 locked brief footer
- Source attribution always: "FX Regime Lab Pipeline"
- All charts: single self-contained HTML — no separate CSS or JS files
- External dependencies only: Chart.js from cdnjs, Google Fonts CDN
- Dark theme: always used for framework dashboard and morning brief
- Light theme: used for curriculum/educational HTML files only

---

## 5. WHAT QUANTAMENTAL MEANS FOR THIS PROJECT

Every build decision is filtered through one question: **Does this demonstrate both deep macro judgment AND systematic signal engineering simultaneously?**

This is not a pure quant project (no ML models for their own sake, no black-box signals). This is not a pure discretionary project (no manual chart reading, no opinions without signal backing). It is the hybrid — which is exactly what funds like Graham Capital, Point72's Fund Flow desk, Millennium Systematic Macro, and Caxton Associates hire for.

### Proof of macro depth comes from:
- Signal choices that reflect how a real FX desk thinks (COT crowding, vol regime, rate differential direction + momentum, risk reversals as sentiment)
- Morning brief quality — reads like an institutional research note, not a data dump
- Trade setup construction with all six elements: thesis, instrument, entry, target, stop, invalidation
- SSRN paper documenting methodology with proper out-of-sample validation

### Proof of systematic/tech depth comes from:
- Fully automated daily pipeline running without human intervention
- Clean modular Python codebase (pandas, numpy, requests, Supabase client)
- Supabase database with proper schema, indexing, and query capability
- GitHub Actions CI/CD for pipeline execution
- **Cloudflare Pages** deployment with live Supabase reads
- MT5/MQL5 integration for paper trading via JSON handoff
- AI usage: Cursor for development, FinBERT (future) for NLP — AI as an enhancer, not a replacement for judgment

### The AI skills showcase:
The framework demonstrates AI usage at the right level — using AI to build production infrastructure faster, not to replace the analytical thinking that underpins every signal. This distinction is what separates a practitioner who uses AI from a person who outsources thinking to AI. Every signal in this framework has a macro rationale that Shreyash can explain without the code. The code just automates the execution.

---

## 6. SIGNAL DESIGN PRINCIPLES

These principles govern every signal added to the framework. A signal that doesn't pass all four tests does not get built.

1. **Institutional validity** — Does a real macro PM at a G10 FX desk actually use this, or does it just look quantitative? If it doesn't pass that test, kill it.
2. **Independence** — Does it add information not already in the existing signal stack? A noisier version of an existing signal is not a new signal.
3. **Data availability** — Is the data source free, reliable, automatable, and daily frequency or better?
4. **Regime relevance** — Does it help distinguish between trending, mean-reverting, vol-expanding, and crisis regimes? If it doesn't discriminate between regime states, it belongs in a report but not in the signal stack.

### What is explicitly excluded:
- Social media sentiment (Reddit, X) — retail noise, no institutional signal for G10 FX
- DCF or equity valuation — wrong domain
- Fibonacci, Elliott Wave, MACD, candlestick names — retail TA, excluded entirely
- C++ — not needed for this stack
- ML models before Phase 4 is complete — premature, adds complexity without signal clarity

### Equities enter only through cross-asset layer:
VIX as USD regime signal, equity risk premium as carry input, sector rotation as growth/recession indicator. Never as stock-picking or equity analysis.

---

## 7. EXPANSION ROADMAP

### Pair Expansion (in order)
1. GBP/USD — after vol layer (CVOL + RR) is stable on existing pairs
2. AUD/USD — commodity currency, adds terms of trade signal dimension
3. USD/CAD — oil-linked, natural cross-asset complement

### Asset Class Expansion (cross-asset layer only, not separate domains)
1. **Gold** — already partially covered as safe haven signal. Expand to full regime input: real rates vs. gold price divergence, gold/DXY correlation regime
2. **Oil (Brent/WTI)** — terms of trade signal for commodity currencies, inflation regime indicator, USD/CAD direct driver
3. **Rates (US 10Y, DE 10Y, JP 10Y)** — term premium, yield curve shape as regime discriminator, already partially used in rate differential module
4. **Equities (VIX, SPX)** — cross-asset layer only: VIX as risk-off USD signal, SPX/USD correlation regime

### Signal Layer Expansion (in build order)
1. CME CVOL implied vol + Skew — **next build**
2. CME daily OI delta — **next build**
3. Synthetic 25-delta risk reversal via yfinance FXE — **next build**
4. Out-of-sample validation log to Supabase — **in parallel with above**
5. Systematic backtesting layer — after Python Phase 4
6. Morning brief automation upgrade — after backtesting layer
7. NLP layer: FinBERT on FOMC, ECB, BoJ communications — planned sem 7
8. Regime-conditional position sizing model — after NLP layer

---

## 8. PAPER TRADING ARCHITECTURE

**Platform:** MT5 via Exness (demo account)  
**EA:** MQL5 Expert Advisor  
**Signal handoff:** Python pipeline writes JSON file → EA reads and executes  
**Position logging:** EA writes trade log → Python reads → stores to Supabase  
**Public visibility:** Supabase-fed dashboard and performance on **fxregimelab.com** (Cloudflare Pages) — live, timestamped, auditable  

### Trade rules (non-negotiable):
- No trade without all six elements: thesis, instrument, entry, target, stop, invalidation thesis + conviction level
- USD/INR: directional only, no precision entries
- TA tools allowed: support/resistance, price structure, volume at key levels, 50D/200D MAs, RSI at extremes
- TA tools excluded: Fibonacci, Elliott Wave, candlestick names, MACD

### Why public visibility matters:
A timestamped, publicly visible out-of-sample track record is what transforms a "college project" into institutional-grade evidence. This is the SSRN paper results section. This is what gets shown in MFE applications and internship interviews.

---

## 9. SSRN PAPER

**Target:** Documenting the framework methodology, signal construction, and backtested + live out-of-sample results  
**Timeline:** Sem 7 (approx. July–November 2027)  
**Submission:** Before MFE applications in early 2028  
**Structure:** Signal methodology → Regime classification logic → Backtested results → Out-of-sample validation log (live data from now) → Comparison to benchmark (carry, momentum)  

The out-of-sample validation log must run from today. Every regime call logged with timestamp, signal values, predicted direction. Actual outcome logged next trading day. This accumulates automatically into the paper's results section.

---

## 10. LOCKED DECISIONS — NEVER REOPEN

| Decision | Status |
|----------|--------|
| Python only — no C++ | Locked |
| No ML before Phase 4 complete | Locked |
| No social media sentiment in signal stack | Locked |
| No equity analysis — cross-asset layer only | Locked |
| CFA stops at L2 | Locked |
| GRE October 2026 | Locked |
| NTU MFE primary target | Locked |
| GitHub Actions for pipeline execution | Locked — do not move |
| Supabase for database | Locked |
| **Cloudflare Pages** on **fxregimelab.com** for public dashboard + site | Locked |
| No Firebase | Locked |

---

## 11. NETWORKING AND LINKEDIN CONTEXT

**Current warm contacts:**
- Ruth Carson (Bloomberg Chief FX/Rates Correspondent Asia) — replied to comment; engage via comments on future JPY/carry/BoJ posts only, no direct message yet
- Ankita Anand (HSBC VP FX Corporate Sales) — warm; engage when she posts relevant FX content
- Akul (Anand's partner, runs quant strategies) — follow up with GitHub framework link to reset perception after surface-level call

**LinkedIn content:** Three posts per week. Sunday regime read teaser. Tuesday market observation. Thursday engagement question. All data verified before posting. Dark theme visuals. Comment style: under 50-60 words, single paragraph, casual and human, data-grounded, always ending with a question to the specific person's expertise.

**Framework is the primary LinkedIn content engine.** Every regime signal, every morning brief, every new pipeline addition is potential content.
