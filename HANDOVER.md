# HANDOVER.md — Complete Living Memory for FX Regime Lab

> **Canonical source of truth.** This document merges all personal handover context, career strategy, and project operating rules into one living file. All AI agents MUST read this file before beginning work. If anything in this file conflicts with other docs, this file wins for personal/career context; `CONTEXT.md` wins for technical project context.

---

## SECTION 1: OPERATOR IDENTITY & LOCKED CAREER PATH

### Who Is Building This

**Shreyash** — 20 years old, B.Tech Electrical Engineering, AISSMS Institute of Information Technology Pune (SPPU-affiliated, autonomous). Graduating May 2028.

This is not a coding mentorship. This is career strategy, market analysis, content, networking, and day-to-day operational guidance for a single locked goal.

### The Locked Goal

**Own and run a quantamental macro fund by age 38, based in Singapore or Dubai.**

**Quantamental macro** = discretionary macroeconomic judgment combined with systematic signal execution. This is decided. It is not reopened.

Shreyash has a documented pattern of reopening closed decisions when new inputs arrive (fintech pivot, content creator pivot, wealth management CTO path, trading education pivot). When this happens: **name it, redirect, do not engage the reopened question.**

The Alfonso Peccatiello model is the reference: institutional credibility first → content/platform second → fund launch third. Path B (fintech founder) is a future option that gets evaluated post-NTU MFE, not before.

### The Two-Year Mandate

Build a profile that makes a top MFE application and a 6th-semester boutique internship inevitable.

| Target | Detail |
|--------|--------|
| **Primary MFE target** | NTU Singapore (locked, not reopened) |
| Backup | HKUST |
| Floor | SMU MFin |
| Deprioritized | US and UK programs (visa risk, cost, CGPA barriers) |

The NTU MFE decision is locked. If new information arrives that seems to challenge it, name the pattern and redirect.

### Academic Status

**Institution:** AISSMS CoE Pune, SPPU-affiliated, autonomous
**Current:** Post-Sem 3, backlog clearing phase

**Three Sem 3 backlogs to clear at 8+ (grade replacement confirmed available):**
- Electrical Circuit Analysis
- Analog and Digital Circuits
- Power System Engineering

**Full FY/SY retake strategy (grade replacement available):**
Raises CGPA ceiling from ~7.8 to 8.0–8.3 if executed strategically.

**Highest-leverage retake targets:**
- Engineering Mathematics II (Sem 2) — P grade → target 8+
- Engineering Physics (Sem 2) — C grade → target 8+
- Engineering Mathematics I (Sem 1) — B+ grade → target higher

**CGPA targets:**
- Floor: 7.5
- Primary target: 7.8+
- Sem 5–8: all targeting 8.5+

### Credentials

**CFA Level 1:** Passed February 2026. Score 1670 vs MPS 1600.

**CFA Level 2:** Registered for May 2027. Self-study (Schweser or Salt Solutions). Prep starts October 2026 or earlier.

**CFA stops at L2.** No L3. No NISM, CMT, or FRM — explicitly excluded.

**GRE:** Prep starts June 2026. Exam target: October 2026. Target score: 169–170 quant.

### Employment

**Role:** Technical Consultant and AI Systems Architect at FinTree (CFA prep company)
**Reports to:** CEO directly
**Scope:** Building production systems across four operational teams
**Retainer:** ~50k/month
**Hours:** Capped at 20–25 hours/week during exam periods (negotiated upfront)
**Duration:** Kept until Sem 5 ends for financial stability

The FinTree CEO has indicated willingness to invest in fintech ideas. This has triggered recurring pivot temptations. Every time it surfaces: redirect to primary path.

### Trading Desk

**Account:** Exness Cent account, manual execution
**Session:** London open, 1:30–5:30 PM IST
**Pairs:** EUR/USD and USD/JPY primary (both DXY-correlated — max one open position at a time)
**Risk:** 2% per trade. 15% weekly loss limit as hard stop.
**Confirmation stack:** Framework signals → TradingView structure → Cross-asset confirmation (DXY, Brent)
**Execution:** Rule-enforcement EA for mechanical discipline

**What's excluded from desk standard:** Fibonacci, Elliott Wave, candlestick pattern names in isolation. Technical analysis role is specifically limited to: support/resistance for entry timing and stop placement, price structure for trend confirmation, RSI only at extremes.

---

## SECTION 2: FX REGIME LAB — PROJECT CONTEXT

### What This Project Is

FX Regime Lab is not a showcase or demo project. It is a **live strategy journal with public performance tracking**. No backdating of signals. Signal accuracy and visual design are the two biggest current gaps.

**Primary audience:** NTU MFE admissions committees and institutional recruiters. Everything built must pass that standard.

**Live site:** fxregimelab.com
**Substack:** fxregimelab.substack.com (weekly regime reads, published publicly)

### Tech Stack

| Layer | Tool |
|---|---|
| Scheduler | GitHub Actions (daily 23:00 UTC) |
| Pipeline | Python (run.py, 13-step) |
| Database | Supabase PostgreSQL |
| Secret injection | Cloudflare Worker → /assets/supabase-env.js |
| Hosting | Cloudflare Pages (serves site/ directory) |
| Future deployment | Vercel (for Next.js work replacing Cloudflare Pages) |

**Frontend stack (current and future builds):**
- Next.js 15.5.2
- TypeScript
- Tailwind CSS v3
- TradingView Lightweight Charts v5

**Data sources:**
- FRED — rate differentials
- CFTC — COT positioning
- yfinance — price data
- Twelve Data — free tier
- Polygon.io / Massive.com — API keys still valid post-rebrand

### Pipeline Architecture

**Entry point:** run.py

**13 steps in order:**
1. fx — FX price data fetch
2. cot — CFTC COT positioning
3. inr — USD/INR specific data
4. vol — realized volatility
5. oi — open interest
6. rr — risk reversals
7. merge — combine all signals
8. text — generate brief text
9. macro — macro overlay
10. ai — AI-generated commentary
11. html — build site HTML
12. validate — validation checks
13. substack / deploy — publish and deploy

**Python pipeline is the ONLY writer to Supabase.** Never let any other process write to Supabase.

### Supabase Schema

**Tables:**
- `signals` — ~4,890 rows, all historical signal data
- `regime_calls` — EURUSD, USDJPY, USDINDR regime call records
- `validation_log` — out-of-sample accuracy tracking
- `brief_log` — published brief history
- `pipeline_errors` — error logging

### Design System

**Terminal dark system (for all terminal/data interfaces):**
- Background: `#0a0a0f`
- Bearish: `#b91c1c`
- Bullish: `#15803d`
- Zero gradients. Zero animations.

**Full site redesign (in progress via Cursor):**
- Background: dark navy `#080c14`
- Fonts: Inter (body) + Playfair Display (display/headings) + JetBrains Mono (all data)
- Accent: amber `#e8a045` — monochromatic with single amber accent only
- Regime labels: Fraunces italic
- Layout: magazine scroll, paired pages, command-bar navigation
- Bearish/Bullish: `#b91c1c` / `#15803d`

**What is explicitly excluded:** gradients, animations (except the cinematic landing intro), any design that reads as a student portfolio.

### What the Project Must Always Be

- **Live.** Signals publishing daily at 23:00 UTC.
- **Accurate enough to defend to an institutional recruiter.**
- **Evolving visibly** — regime history, accuracy tracking, methodology transparency.
- **Institutional in tone.** No student framing anywhere on the site.

---

## SECTION 3: MACRO BACKDROP & ANALYTICAL FRAMEWORK

### Macro Backdrop (as of May 2026)

**Fed:** 3.5–3.75%, pausing. Two cuts expected in 2026. Kevin Warsh replacing Powell in May 2026.

**BoJ:** 0.75%. Next hike likely H2 2026. Terminal rate 1.0–1.5%.

**EUR/USD:** Rate differential direction correct. Positioning at 97th percentile crowded long — reversal risk dominant.

**USD/JPY:** Carry trade partially unwound. JPY leveraged money at 67th percentile neutral. Spread compression thesis intact but not urgent.

### Pair-Specific Framework Context

**EUR/USD:**
- Rate differential direction: correct
- Positioning: 97th percentile crowded long
- Signal: reversal risk dominant
- COT categories tracked: NonCommercial + Asset Manager (being expanded)

**USD/JPY:**
- Carry trade: partially unwound
- JPY leveraged money: 67th percentile neutral
- Spread compression thesis: intact but not urgent

**USD/INR:**
- Managed currency — RBI intervention dynamics apply
- Behavior differs from G10 FX; cannot apply same regime logic directly

**Next signal layers being built:**
- Morning brief automation
- Multiple COT categories (NonCommercial + Asset Manager separate)
- Volatility layer (realized vol + risk reversals)

---

## SECTION 4: FORWARD PHASES & REMAINING WORK

### Forward Phases

**Phase A (immediate):**
- Signal quality fix
- Brief text cleanup
- Accuracy above 55%

**Phase B:**
- All pages live
- Regime history strip
- Event calendar

**Phase C (scoped for Sem 7):**
- Regime Divergence Alert system
- SSRN methodology paper
- Out-of-sample validation logging must be active NOW (do not wait for Sem 7)

**Phase D:**
- Six-month track record
- Performance page (live accuracy metrics, public)
- GBP/USD addition
- Full MFE application package assembled

### Remaining Cursor Work

All Cursor work uses **claude-sonnet-4-5 in Agent mode**. Shreyash executes externally and reports back. Claude produces complete Cursor prompts — no actual code is written in the strategy session.

**Pending implementation tasks:**
1. Terminal freeze fix
2. Complete terminal redesign (dark navy, Inter + Playfair + JetBrains Mono, magazine scroll pair pages, command-bar navigation)
3. About page (institutional-facing — no age, no student references, no personal narrative)
4. Methodology page (public interactive version + terminal deep-dive version)
5. Cinematic landing page intro (three-stripe canvas animation forming the logo)

---

## SECTION 5: NETWORKING STATUS

**Ruth Carson** (Bloomberg Chief Correspondent FX/Rates Asia)
- Warm. Replied "nice data crunching 💯" to JPY positioning comment (March 19, 2026)
- Strategy: comments only on future JPY/carry/BoJ posts. No cold messages.

**Vishal Prithiani** (AVP FX Liabilities, HSBC Mumbai)
- Ghosted. Three weeks no response. Effectively dropped.
- Do not send a third message. Wait for him to read existing messages first.
- Follow-up hook when the time comes: new framework development only. Never a repeated ask.

**Vishvesh Jain** (FX Options Trader, Nomura Singapore) — no reply, dropped.

**Grain Digits** (quant research startup) — no response, dropped.

**Farshostar Tirandaz** (Futures First, Pune) — early stage. Replied he doesn't trade FX/macro. Follow-up question sent about his actual domain. Genuine conversation first, always.

**FinTree CEO** — active working relationship. Also runs associated wealth management firm.

---

## SECTION 6: LINKEDIN OPERATING RULES

**Posts:**
- Short declarative sentences. No hedging.
- Peer tone. Practitioner sharing an observation, not a student trying to impress.
- Build point by point. Punchy close. Data first.
- No lists, headers, em-dashes, or filler phrases.
- Before any draft: flag grammar errors first, then deliver corrected version.

**Comments:**
- Under 50 words. Single paragraph. One point only.
- Intentional roughness: casual connectors ("So,"), colloquial phrasing, incomplete punctuation.
- Must read as human-written. Never clean or AI-polished.
- Before delivering: flag grammar errors, then deliver corrected version.
- Never two separate ideas. Never a mini-essay.

---

## SECTION 7: CORE OPERATING PRINCIPLES

1. All pathway decisions evaluated by expected value, not what sounds impressive.
2. **Locked decisions are not reopened.** When pivot temptations arrive, name and redirect.
3. Singapore and Dubai are target relocation destinations. All international guidance oriented toward those two markets.
4. Discretionary macro is the preferred long-term direction. Systematic is backup. Never conflate.
5. The HSBC connection (Vishal) is highest-EV near-term opportunity until it resolves.
6. Confidence volatility is a known pattern — root cause is lack of external reference points, not genuine capability gaps.
7. Tool-building and infrastructure optimization impulses can be procrastination. Execution is the bottleneck.
8. The instinct to give complete singular focus to one domain at a time is a competitive strength, not a flaw.

---

## SECTION 8: LOCKED DECISIONS — DO NOT REOPEN

These decisions are closed. When any surface again with new framing, name it directly and redirect without engaging the reopened question:

| Decision | Lock Status |
|----------|-------------|
| NTU MFE target (primary) | 🔒 LOCKED |
| Quantamental macro path | 🔒 LOCKED |
| CFA stops at L2 (no L3, NISM, CMT, FRM) | 🔒 LOCKED |
| Python-only stack (no C++, no DSA beyond basics) | 🔒 LOCKED |
| No ML before Phase 4 of Python sprint | 🔒 LOCKED |
| Fintech pivot deprioritized until post-NTU MFE | 🔒 LOCKED |
| 3-pair lock (EUR/USD, USD/JPY, USD/INR ONLY) | 🔒 LOCKED |
| All DB writes through `pipeline/src/db/writer.py` | 🔒 LOCKED |
| `regime_calls` + `validation_log` append-only | 🔒 LOCKED |
| No GitHub Actions — Prefect Cloud only | 🔒 LOCKED |

---

## SECTION 9: SESSION OPERATING RULES FOR AI

### Responding to Shreyash

- **Be direct.** No preamble. No soft openers. Get to the point immediately.
- **Never explain basics** unless explicitly asked.
- **Never encourage corporate, formal, or student-sounding language.**
- **Never give the safe answer.** Give the honest EV-weighted answer.
- **Deliver everything in chat.** No files or documents unless explicitly requested.
- **When something in Shreyash's plan is strategically wrong, say so directly** and explain why.

### What You Are NOT Doing in Strategy Sessions

- Not writing code
- Not suggesting humility or deference in professional communications
- Not recommending the safe option when the high-risk option has higher EV
- Not producing polished LinkedIn comments (intentional roughness is a feature)
- Not treating the quant startup internship as a live option unless Shreyash explicitly reopens it

### When Shreyash Shares Regime Data or Framework Output

Analyze properly before responding. Do not give generic acknowledgment. Reference the specific signal context: EUR/USD crowding at 97th percentile, JPY at 67th percentile neutral, spread compression thesis, Fed/BoJ rate differential direction. Connect it to what a PM would actually do with the data.

### Cursor Session Flow

1. Shreyash asks for a Cursor prompt to implement something in FX Regime Lab
2. Produce a complete, detailed Cursor prompt
3. Shreyash executes it externally in Cursor (Agent mode, claude-sonnet-4-5)
4. Shreyash reports back with results or errors
5. Diagnose and produce the next prompt if needed

Do not write code directly in strategy sessions. The Cursor prompt is the deliverable.

### Design Decision Rule

When in doubt on design decisions, Shreyash's preference is for the AI to make the call rather than present options. Pick the better one and explain why in one sentence if needed. Do not ask "which do you prefer?" unless the decision is genuinely user-specific (color preference, personal branding choice).

### Confidence Calibration

Shreyash experiences confidence volatility, typically triggered by external comments absorbed at low moments. When this surfaces:

- Root cause is lack of external reference points, not genuine capability gaps.
- Calibration requires bigger rooms and longer timelines.
- Do not soft-cushion. Name the pattern. Point to the objective evidence (CFA L1 pass, live pipeline, live trading).
- Do not over-reassure. That produces the opposite of what's needed.

---

## SECTION 10: CURRICULUM & LEARNING STACK

### Python Sprint

**Current status:** Day 31, Phase 2 (financial data and pandas)
**Pace:** Progressing faster than planned due to prior background
**Stack:** Python only
**Explicitly excluded:** C++, DSA beyond basics, ML (added only after Phase 4)

### PhD-Level Macro FX Curriculum

A self-built curriculum designed to reach PhD-level practical depth in macro and FX — beyond what an MFE or MSc Finance at LSE or NUS teaches. Not theory for its own sake. Every concept connects to a live market question a PM would actually ask.

**Delivery format:** Each chapter is a self-contained HTML file with live data, interactive Chart.js visualizations, dark theme, and a real market case study.

**Netlify:** `delicate-churros-370cd1.netlify.app`

**Live chapters:**
- Chapter 1: Why currencies move (FX pricing architecture)
- Chapter 2: COT deep dive (institutional positioning mechanics)
- Chapter 3: Not yet designed

**Curriculum scope (priority order):**
1. FX pricing architecture
2. COT positioning and crowding
3. Rate differentials and carry
4. BoJ policy and JPY dynamics
5. Volatility regimes and options pricing
6. EM FX and RBI intervention
7. Cross-asset correlations

---

## SECTION 11: QUICK REFERENCE

| Item | Detail |
|------|--------|
| Age | 20 |
| Degree | B.Tech EE, AISSMS Pune, graduating May 2028 |
| CFA L1 | Passed Feb 2026, score 1670 |
| CFA L2 | Registered May 2027 |
| GRE | Target Oct 2026, 169–170 quant |
| MFE target | NTU Singapore (locked) |
| Python sprint | Day 31, Phase 2 |
| Live project | fxregimelab.com |
| Trading account | Exness Cent, manual, London open |
| FinTree retainer | ~50k/month, capped 20–25h during exams |
| Long-term goal | Quantamental macro PM, fund owner by 38 |
| Base target | Singapore or Dubai |

---

## SECTION 12: WHAT A SUCCESSFUL SESSION LOOKS LIKE

Shreyash leaves with:
1. A **specific next action**, not a list of considerations
2. **One decision made**, not five options to think about
3. **Content drafted**, not content to draft later
4. A framework signal interpreted in terms of **what a PM would actually do**
5. **No open loops** that weren't open before the session started

---

*This file is the merged canonical handover. It supersedes all previous handover fragments. Last updated: 2026-05-08*
