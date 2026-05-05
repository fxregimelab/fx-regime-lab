# Round 1 Synthesis — Team Consensus Brief

## Brand Direction
**"Precision under pressure."** — Rigorous. Warm. Terminal-native. Quietly confident. Alive.
Design direction: *"Bernstein for the open web."*

## Consensus Principles
1. Darkness is the canvas, not absence of light
2. Every pixel must justify its existence
3. Motion is information, not entertainment
4. Performance is the primary content
5. Data reveals itself like a live terminal

## Target Users (3 Personas)
- **Priya** — Verifying Allocator (needs auditability in <90s)
- **Marcus** — Active Trader (needs immediacy, TL;DR)
- **Diego** — Learning Student (needs guided explanations)

## Critical Gaps (P0)
1. **Equity curve / charting** — No charts on a financial research site
2. **Hardcoded homepage stats** — Static data pretending to be live
3. **Substack orphan** — No capture, no archive, no bidirectional link
4. **Performance page needs depth** — Regime-specific breakdowns, T+1/T+5 hit rates
5. **Trader TL;DR** — Quick call summary with invalidation context

## Motion Language
- Two canonical easings: `INSTITUTIONAL_SETTLE` (0.16, 1, 0.3, 1) and `CRISP_EASE` (0.25, 0.1, 0.25, 1)
- Duration scale: 80ms–3s
- Framer Motion for orchestrated, CSS keyframes for ambient
- No parallax in terminal, no GSAP, no Lottie
- Full prefers-reduced-motion support

## What NOT To Do
- No rounded corners above 4px
- No drop shadows
- No loading spinners
- No generic stock photography
- No light mode
- No delight-for-delight's-sake animations
- No blur/backdrop-filter

## Page Ratings (Current)
- Methodology: 8/10 (best page)
- Terminal Pair Desk: 7/10 (best data page)
- Performance: 6/10 (needs charts)
- Landing: 5/10 (hardcoded stats)
- Audit: 4/10 (visually disconnected)

## Quick Wins
1. Email capture for Substack
2. Live data on homepage
3. TradingView chart embed
4. `/memos` archive page
5. Unify terminal implementations
