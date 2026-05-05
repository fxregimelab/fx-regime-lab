# FX Regime Lab — Master Implementation Plan
## Synthesis of Rounds 1–2 | Ready to Build

---

## P0 — Ship First (Highest Impact)

### 1. Performance Page Overhaul
- [ ] Equity curve (Lightweight Charts, 320px, regime band overlays, drawdown shading)
- [ ] Fix cumulative return math (currently wrong)
- [ ] Hit rate by horizon: T+1 / T+5 / T+20 horizontal bars
- [ ] Regime-specific breakdown table (calls, hit%, avg ret, max DD, streak)
- [ ] Brier score trend (30-day rolling, baseline 0.25)
- [ ] Streak indicator (current + longest)
- [ ] Monthly performance table (running cumulative)
- [ ] Timestamp + stale indicator on all data

### 2. Homepage — Live Data
- [ ] Replace hardcoded stats with real Supabase queries
- [ ] Live snapshot cards fetch real regime_calls + signals
- [ ] Validation trust section pulls from validation_log

### 3. Terminal Pair Desk Enhancement
- [ ] Trader's TL;DR box (5-line summary: bias, driver, invalidation, watchlist)
- [ ] Signal architecture visualization (4-family weighted bars)
- [ ] TradingView chart embed with regime-change markers
- [ ] 30-day historical regime timeline with validation outcomes
- [ ] Invalidation level display

### 4. Nav Restructure
- [ ] Reorder: PERFORMANCE → TERMINAL → METHODOLOGY → BRIEF → ABOUT
- [ ] Terminal dropdown: Overview, Pair Desks, Calendar, Memos, Alpha Ledger

### 5. Substack Integration
- [ ] Footer email capture (inline, no modal)
- [ ] /terminal/memos archive page
- [ ] Bidirectional links between site and Substack

### 6. Motion System
- [ ] useReducedMotion hook
- [ ] prefers-reduced-motion CSS override
- [ ] Institutional timing: 300ms default, 80ms micro, 600ms emphasis

---

## P1 — Next Sprint

### 7. Content Enhancements
- [ ] Expert / Student mode toggle on methodology
- [ ] Auto-linking: pair mentions → desk, regime labels → methodology
- [ ] OG image generation for brief/performance/pair pages

### 8. Terminal Index
- [ ] Live indicators strip (sync age, COT age, VIX, DXY)
- [ ] Strategy cards with performance preview
- [ ] Quick actions row

### 9. Validation Log Enhancements
- [ ] Pair color filter chips
- [ ] Brief deep-links
- [ ] Pagination (never infinite scroll)

---

## P2 — Polish

### 10. Mobile
- [ ] Tables → cards on mobile
- [ ] Terminal context rail as drawer
- [ ] Chart crosshair on tap

### 11. Audit
- [ ] Pipeline heartbeat visualization
- [ ] Data provenance chain

---

## Design System Tokens (Locked)

| Token | Value |
|---|---|
| --color-void | #0c0a09 |
| --color-surface | #141210 |
| --color-elevated | #1c1917 |
| --color-border | #2a2725 |
| --color-text | #f5f5f4 |
| --color-text-secondary | #a8a29e |
| --color-text-muted | #78716c |
| --color-accent | #d6d3d1 |
| --color-up | #7a9e7a |
| --color-down | #b87a7a |

## Motion Tokens (Locked)
- Easing: cubic-bezier(0.16, 1, 0.3, 1)
- Duration: 300ms default, 80ms micro, 600ms emphasis
- Stagger: 50ms tight, 100ms default, 150ms loose
