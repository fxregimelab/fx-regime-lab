# Competitive Analysis & Benchmark Report

**FX Regime Lab — Round 1 Audit**  
*Prepared by: Senior Competitive Analyst*  
*Date: 2026-05-05*  
*Classification: Internal Design Review*

---

## Executive Summary

FX Regime Lab occupies a rare niche: a **public-facing discretionary macro research system** with daily validated calls, transparent methodology, and a terminal-grade data layer. The current site demonstrates strong foundational taste—warm dark palette, disciplined typography (Inter + JetBrains Mono), and a refusal to chase fintech clichés. However, it sits at a critical inflection point. The design is **coherent but not yet compelling**. The terminal is **functional but not yet authoritative**. The Substack integration is **present but not yet woven into the experience**.

This report benchmarks FX Regime Lab against seven reference platforms, extracts actionable patterns, and rates each current page. The verdict: **the bones are excellent; the sinew and skin need work.**

---

## 1. Bloomberg Terminal

### What Makes It Iconic

The Bloomberg Terminal is not loved for its aesthetics—it is respected for its **information architecture**. Every pixel is accountable. Four decades of refinement have produced a UI where a professional can price a bond, message a trader, and read breaking news without switching cognitive contexts. The iconic elements:

- **Dual-keyboard workflow**: `<GO>` keys, yellow function keys, command-driven navigation
- **Frame-based layout**: Persistent panels (top news, quote line, launchpad) that never reload
- **Color-coded semantics**: Green = buy/higher, Red = sell/lower, Yellow = caution—universal across all modules
- **No whitespace guilt**: Density is the product. Empty space is missed alpha.

### What to Adapt

| Element | Adaptation for FX Regime Lab |
|---------|------------------------------|
| Command-driven navigation | The Command Palette (`Cmd+K`) is a good start. Expand it to support ticker jumping (`EURUSD <GO>`), route teleporting (`perf <GO>` → Performance), and quick queries (`vol EURUSD`). |
| Persistent quote strip | The `GlobalMacroPulse` is close, but it should show **live spot + regime + confidence** for all three pairs, always visible. |
| Frame persistence | Terminal pair pages should not feel like page loads. Consider a split-pane or tabbed desk where the left side is the primary pair and the right is context (correlation matrix, calendar, memos). |

### What to Simplify

- **Bloomberg's 40,000+ functions**: FX Regime Lab has ~6 pages. Don't build a command hierarchy; build **muscle-memory shortcuts**.
- **Multi-pane overload**: Bloomberg users have 4+ monitors. FXRL visitors have one. Keep the terminal dense but not crowded.
- **Legacy color cruft**: Bloomberg's amber-on-black is heritage. FXRL's warm stone palette is already more sophisticated—don't regress.

### 3 Things to Steal (with Implementation Notes)

1. **The "Always-On" Ticker Strip**  
   *Implementation*: Elevate `GlobalMacroPulse` from a marquee to a **functional ticker bar**. Show spot, day change, regime, and confidence for all pairs. Make each cell clickable to jump to that pair's desk. Use the pair colors (EUR/USD blue, USD/JPY gold, USD/INR rose) consistently.  
   *Priority*: High | *Effort*: Low

2. **Contextual Keyboard Shortcuts**  
   *Implementation*: Map `1/2/3` to pair tabs in terminal. Map `g b` to Brief, `g p` to Performance (Vim-style leader keys). Show a `?` modal with the shortcut map. This signals "tool" not "blog."  
   *Priority*: Medium | *Effort*: Low

3. **Semantic Color Rigidity**  
   *Implementation*: Lock the meaning of green/red/amber across every surface. Currently `color-up` and `color-down` are used but inconsistently. The composite bar on pair pages uses green for positive and red for negative—this is correct. Extend to sparklines, regime history, and validation table outcomes. Never use green for anything except "up/correct/bullish."  
   *Priority*: High | *Effort*: Low

### 2 Things to Avoid

1. **Feature bloat by association**: Bloomberg justifies density with 40 years of feature accretion. FXRL has 4 signal families and 3 pairs. Every new widget must earn its place. The "MORE STRATEGIES — PHASE 2+" placeholder is actually good—it shows restraint.

2. **The "wall of numbers" trap**: Bloomberg users are trained. FXRL's audience includes curious retail and potential allocators. Raw signal tables need **visual scaffolding**—progress bars, percentile dots, or micro-sparklines—so the numbers tell a story without requiring domain expertise.

### 1 Surprising Insight

> **Bloomberg's most underrated UI feature is its "last update" timestamp.** Every data point has provenance. FXRL's pipeline timestamp on the terminal is excellent, but it's visually buried. Making provenance **front-and-center** (e.g., "Ingested 06:14 UTC · Validated 14:32 UTC") transforms a data point into a credible artifact.

---

## 2. Substack

### Best Practices for Researcher-Focused Platforms

Substack has become the default publishing layer for independent research. Its best practitioners (Lyn Alden, Doomberg, Kyla Scanlon) share common patterns:

- **Voice-forward design**: The author is the brand. The site is a wrapper for the writing.
- **Archive as credibility**: A deep, searchable archive is social proof before the first word is read.
- **Email as primary UX**: The website is secondary. The inbox is where loyalty is built.
- **Minimal chrome**: Substack intentionally limits customization, forcing writers to compete on content.

### What FX Regime Lab Gets Right

- The **brief page** already mimics the Substack reading experience: clean typography, generous line-height, restrained formatting.
- The **SubstackFeed component** pulls headlines via RSS—a pragmatic integration.

### What Needs Work

| Gap | Benchmark Standard |
|-----|-------------------|
| No "Subscribe" CTA on homepage | Every Substack publication leads with email capture |
| Archive is invisible | Memos exist at `/memo/[date]` but there's no browseable index |
| No cross-linking | Substack posts interlink to build rabbit holes. FXRL briefs are islands. |
| Substack feed is orphaned | The RSS headlines appear in no obvious location in the main navigation flow |

### 3 Things to Steal (with Implementation Notes)

1. **The "Subscribe" as Primary Conversion**  
   *Implementation*: Add an email capture block to the homepage (below Validation Trust) and a sticky footer CTA on the Brief page. Use the copy pattern: "Get the morning brief in your inbox. No spam. Unsubscribe anytime." Integrate with Substack's native subscribe endpoint or use a simple API route.  
   *Priority*: High | *Effort*: Medium

2. **Browsable Memo Archive**  
   *Implementation*: Create `/memos` as a reverse-chronological list with month dividers. Show date, title (or "Daily Brief — YYYY-MM-DD"), and a one-line excerpt. Add filtering by pair or regime. This transforms ephemeral briefs into a **research corpus**.  
   *Priority*: High | *Effort*: Medium

3. **Interlinking Within Briefs**  
   *Implementation*: When a brief mentions a regime or signal, auto-link to the relevant terminal desk or methodology section. If the brief says "EUR/USD regime shifted to MODERATE USD STRENGTH," that text should link to `/terminal/fx-regime/eur-usd`. This builds the **knowledge graph** that Substack writers create manually.  
   *Priority*: Medium | *Effort*: Medium

### 2 Things to Avoid

1. **Substack's design homogenization**: Substack sites look like Substack. FXRL should not. The RSS integration is a distribution channel, not a design system. Never let Substack's generic aesthetic override FXRL's warm stone palette.

2. **Paywall anxiety**: Substack's paid/premium dynamics create friction. FXRL's thesis—"public by design"—is a differentiator. Don't introduce tiers or gates. The "subscription" is for **distribution**, not access.

### 1 Surprising Insight

> **Substack's most powerful feature is not publishing—it's the "restack."** When a reader shares a post, it carries social proof. FXRL has no sharing mechanism. Adding a "Share this call" button to the brief (pre-populated with the day's regime snapshot) turns readers into amplifiers. The research is already public; the distribution should be frictionless.

---

## 3. Stripe Press / Linear.app

### How They Achieve "Professional But Not Dull"

Stripe Press and Linear.app are the gold standard for **technical credibility with emotional resonance**.

**Stripe Press**:
- Editorial typography: Large serif headlines (often Cormorant or Tiempos) against stark backgrounds
- Generous whitespace that signals confidence, not emptiness
- Photography and illustration that feels curated, not stock
- Every page feels like a **finished essay**, not a template

**Linear.app**:
- Dark mode as default, but never muddy
- Magenta/purple accents used with surgical precision
- Keyboard-first interactions that feel **fast**
- Micro-interactions (hover states, focus rings) that reward attention
- The famous "magical" quality: it feels like the UI is anticipating you

### The Common Thread

Both platforms understand that **professionalism is not the absence of personality—it is the discipline of restraint**. They use exactly one or two "unusual" choices (Stripe's serif headings, Linear's magenta glow) and execute them flawlessly.

### 3 Things to Steal (with Implementation Notes)

1. **The "One Signature Move"**  
   *Implementation*: FXRL already uses Cormorant (Playfair) for serif. Use it **more deliberately**—exclusively for the hero H1 and section titles on the homepage. Currently it's loaded but barely visible. A serif headline on a dark background signals "publication" not "product."  
   *Priority*: Medium | *Effort*: Low

2. **Linear's Focus States & Haptic Feedback**  
   *Implementation*: The `omega-haptic` class exists but is inconsistently applied. Make every interactive element (buttons, table rows, nav links) have a distinct active state. Add a subtle `box-shadow` glow on focused terminal cells. The terminal should feel **tactile**, like physical keys.  
   *Priority*: Medium | *Effort*: Low

3. **Stripe's "Credibility Through Finish"**  
   *Implementation*: Stripe Press pages have no loose ends. Every image has an alt. Every link has a hover state. Every paragraph has a measure (max-width) that respects reading comfort. Audit FXRL for "unfinished" surfaces: the audit page's fallback text, the terminal's dashed "PHASE 2+" box, the brief's plain-text parsing. These signal "work in progress" to sophisticated visitors.  
   *Priority*: High | *Effort*: Medium

### 2 Things to Avoid

1. **Linear's scope creep**: Linear can afford keyboard shortcuts for everything because it has one domain (issue tracking). FXRL has research, data, validation, and narrative. Don't unify interactions where the domains are genuinely different.

2. **Stripe's production budget**: Stripe has a full editorial team and custom photography. FXRL is a solo operation. Don't chase visual richness with stock imagery. Instead, invest in **data visualization**—the charts and tables are FXRL's "photography."

### 1 Surprising Insight

> **Linear's dark mode uses a subtle blue undertone (#0e0e10) that makes magenta pop. FXRL's `--color-void: #0c0a09` is warmer (stone/amber undertone). This is a defensible choice for finance (warmth = trust), but it means accent colors need more saturation to achieve the same "pop." Consider slightly desaturating the pair colors or adding a subtle ambient glow behind key metrics instead of relying on pure hue contrast.**

---

## 4. Aesop.com

### Minimal, Textural, Calm — What Can We Borrow?

Aesop is the master of **atmospheric restraint**. Their digital presence mirrors their retail: warm materials, unhurried pacing, and a belief that confidence whispers.

Key patterns:
- **Tactile surfaces**: Borders that feel like joinery, not dividers
- **Generous padding**: Elements breathe; the eye rests
- **Typography as texture**: Headlines feel like signage, body text like correspondence
- **Motion as ambiance**: Transitions are slow, smooth, meditative

### 3 Things to Steal (with Implementation Notes)

1. **The "Breathing Grid"**  
   *Implementation*: Aesop product grids use spacing that feels architectural. FXRL's `max-w-[1152px]` is tight for data-dense pages but appropriate for narrative pages. On the homepage, increase section padding from `py-24` to `py-32` or `py-40`. Let the Signal Architecture section feel like a **room**, not a strip.  
   *Priority*: Low | *Effort*: Low

2. **Border as Joinery**  
   *Implementation*: Aesop's borders are often 1px but feel weightier because they're accompanied by generous padding and tonal contrast. FXRL's `border-[var(--color-border)]` is correct. Enhance by adding **inset shadows** or subtle gradients on elevated panels to create depth without clutter.  
   *Priority*: Low | *Effort*: Low

3. **Calm Transitions**  
   *Implementation*: The `reveal` scroll animation is good but abrupt. Ease into it with a longer duration (`0.9s`) and a softer curve (`cubic-bezier(0.25, 0.1, 0.25, 1)`). On the About page, where the tone is contemplative, slow down.  
   *Priority*: Low | *Effort*: Low

### 2 Things to Avoid

1. **Aesop's unhurried pace on data pages**: Aesop can be slow because browsing skincare is leisurely. Terminal users want **instant legibility**. Keep the homepage calm; make the terminal **snappy**.

2. **Over-warmth**: Aesop's palette risks cloying if applied to financial data. FXRL's current balance—warm surfaces, cool data accents—is correct. Don't add more amber/stone to the terminal.

### 1 Surprising Insight

> **Aesop's product descriptions are written in the second person ("A serum to nourish your skin"). FXRL's copy is third-person and declarative ("Daily regime calls. On the record."). This is correct for credibility, but consider adding **one moment of second-person direct address**—perhaps the CTA: "Read the brief before the market opens." Direct address creates intimacy without sacrificing authority.**

---

## 5. Koyfin / TradingView

### Financial Data Presentation Patterns

**Koyfin** is the benchmark for **fundamental research dashboards**: clean dark mode, multi-panel layouts, color-coded watchlists, and a focus on **comparability** (side-by-side metrics).

**TradingView** is the benchmark for **technical analysis**: infinite customization, community scripts, social layers, and chart-first design.

### What FX Regime Lab Should Learn

| Pattern | Koyfin Implementation | TradingView Implementation | FXRL Adaptation |
|---------|----------------------|---------------------------|-----------------|
| Dark mode | Midnight blue, high contrast | True black, neon accents | Warm stone is differentiated—keep it |
| Data tables | Sortable, filterable, column-configurable | Minimal tables, chart-forward | Add sortable headers to ValidationTable |
| Watchlists | Persistent right sidebar | Community-driven lists | Terminal sidebar already has "Other Desks"—expand |
| Charting | Fundamental overlays (PE, margins) | Technical indicators | Add spot price charts with regime bands |
| Sharing | Export to PDF/image | Publish idea, social feed | Add "Share this regime" to pair pages |

### 3 Things to Steal (with Implementation Notes)

1. **Koyfin's Dashboard Panels**  
   *Implementation*: The terminal pair page currently has a 4-column top strip + signals table + sidebar. Add **collapsible panels** for correlation matrix, calendar events, and memo excerpts. Let users toggle visibility. This respects both power users and newcomers.  
   *Priority*: Medium | *Effort*: High

2. **TradingView's Chart Annotation**  
   *Implementation*: Embed a lightweight chart (TradingView widget or lightweight-charts) on each pair desk. Overlay regime-change dates as vertical markers. This transforms abstract regime labels into **visualized history**.  
   *Priority*: High | *Effort*: Medium

3. **Koyfin's Color-Coded Watchlist**  
   *Implementation*: The terminal index page already uses pair colors. Extend this to **every mention** of a pair across the site. EUR/USD should always appear in `#8fa8bc`, even in body text. This is a **wayfinding** system, not just decoration.  
   *Priority*: Medium | *Effort*: Low

### 2 Things to Avoid

1. **TradingView's social noise**: The "Ideas" feed is valuable for community but dilutes authority. FXRL is a **single-researcher** system. Don't add comments, likes, or social feeds. The credibility is in the validation trail, not the crowd.

2. **Koyfin's complexity ceiling**: Koyfin has thousands of metrics. FXRL has four signals. Don't add configurability where simplicity is the feature. The signal weights are fixed (~40/30/20/10)—the UI should reflect this confidence, not suggest adjustability.

### 1 Surprising Insight

> **Koyfin's most recent update consolidated all dark themes into a single "Dark Mode." FXRL is already more opinionated (warm stone vs. Koyfin's cool blue). This is a competitive advantage. In a sea of blue-black fintech UIs, FXRL's warm void feels distinct and premium. Protect this differentiation. Don't add a light mode—it would fracture the brand.**

---

## 6. Ark Invest / Bernstein Research

### How Research Houses Present Credibility

**Ark Invest**:
- Big Ideas reports are **visual manifestos**: full-bleed charts, bold predictions, transparent methodology
- Cathie Wood's persona is inseparable from the brand
- Open-source research: their whitepapers are freely downloadable, building trust through transparency
- Data-forward: every claim has a chart, every chart has a source

**Bernstein Research** (the "Sell-Side Gold Standard"):
- **Analyst attribution**: Every note is signed. Every model has an owner.
- **Disclosure discipline**: Conflicts, ratings distributions, and price targets are never hidden
- **Consistency of format**: Clients know where to find the summary, the thesis, the model, and the risks
- **Institutional voice**: Confident but not arrogant; analytical but not robotic

### 3 Things to Steal (with Implementation Notes)

1. **Ark's "Big Ideas" as Annual Manifesto**  
   *Implementation*: Once per quarter or half-year, publish a long-form "Regime Outlook" that synthesizes the validation trail into forward-looking themes. Design it as a **scroll-driven narrative** with embedded charts. This is FXRL's equivalent of Ark's Big Ideas.  
   *Priority*: Medium | *Effort*: High

2. **Bernstein's Analyst Attribution**  
   *Implementation*: Every call on the validation table should show the date, the regime, the confidence, and a link to the **specific brief** that generated it. The performance page currently shows outcomes but not provenance. Add a "View call" column linking to `/memo/[date]` or `/brief?date=YYYY-MM-DD`.  
   *Priority*: High | *Effort*: Low

3. **Ark's Chart-First Disclosure**  
   *Implementation*: Ark puts methodology appendices at the end of reports, not hidden in a separate page. FXRL's methodology page is excellent but **disconnected**. Add a "How this call was made" expander to every pair desk card and brief regime snapshot. Progressive disclosure beats separate pages for context.  
   *Priority*: Medium | *Effort*: Medium

### 2 Things to Avoid

1. **Ark's hype velocity**: Ark's predictions are deliberately provocative ("Bitcoin to $1M"). FXRL's brand is **sober validation**. Never sacrifice credibility for virality. The numbers should speak, not shout.

2. **Bernstein's paywall legacy**: Bernstein's research is institutionally gated. FXRL's entire value proposition is openness. Don't add friction to the validation trail, the methodology, or the briefs.

### 1 Surprising Insight

> **Bernstein's most effective credibility device is not the research—it's the "rate the analyst" survey. Buy-side clients rate analyst accuracy annually, and Bernstein publishes the results. FXRL's validation table is mechanically similar (outcome logged, accuracy computed), but it's presented as **internal data**. Reframe it: the validation table is not "our record"—it is "your audit." The user is the buy-side client. The site is the analyst. The language should reflect that power dynamic.**

---

## 7. Current FX Regime Lab Audit

### Page-by-Page Rating (1–10)

| Page | Score | Rationale |
|------|-------|-----------|
| **Homepage** | 7/10 | Strong hierarchy, clear value prop, good CTA flow. Weaknesses: no email capture, Substack feed invisible, live snapshot data is static/mock, "Scroll" hint feels generic. |
| **Brief** | 6/10 | Clean reading experience. Weaknesses: markdown parsing is naive (no lists, no links), no archive navigation, no "previous brief" / "next brief" pagination, no share CTA. |
| **Terminal (Index)** | 7/10 | Good data density, pair color system works. Weaknesses: inconsistent implementation between server page and client dashboard, "PHASE 2+" placeholder signals incompleteness, no charting. |
| **Terminal (Pair Desk)** | 7/10 | Best data page on the site. Sparkline and regime history are excellent. Weaknesses: no actual price chart, signals table is raw numbers without visual encoding, "Other Desks" sidebar is cramped. |
| **Performance** | 6/10 | Validation table is the core credibility asset. Weaknesses: metrics are computed client-side-ish (SSR but basic), transition matrix is hardcoded mock data, no cumulative P&L chart, no drawdown visualization, no Sharpe/Sortino. |
| **About** | 7/10 | Honest, direct, well-structured "This is / This is not" grid. Weaknesses: no photo (fine for anonymity, but a visual would help), pipeline stages are decorative (not clickable), social links absent. |
| **Methodology** | 8/10 | Best page on the site. KaTeX integration, sticky sidebar, clear threshold table. Weaknesses: no interactive "what-if" explorer (e.g., slider to see how changing weights affects regime), no downloadable PDF. |
| **Audit** | 4/10 | Conceptually interesting (transparency of process). Weaknesses: visually disconnected from the rest of the site (pure black, different typography), often shows fallback text, no clear value to the visitor. |
| **Calendar** | 5/10 | Functional but sparse. Weaknesses: no macro event integration (Fed meetings, NFP, ECB), no color-coding by impact level, feels like a template not a tool. |
| **Memo** | 5/10 | Good for deep linking. Weaknesses: no browseable index, no related memos, design is identical to Brief (should it be?). |

### What's Working

1. **Color system**: The Obsidian Stone palette is sophisticated and differentiated. Warm void, muted accents, pair-specific colors—this is a genuine brand asset.
2. **Typography pairing**: Inter + JetBrains Mono is a proven combination. The mono for data, sans for narrative, creates automatic hierarchy.
3. **Terminal concept**: The bifurcation between "shell" (marketing/pages) and "terminal" (data/dense) is architecturally sound. It gives permission for the terminal to be complex.
4. **Validation-first positioning**: The site never lets you forget that outcomes are logged. This is the core moat.
5. **Performance mindset**: The pipeline timestamp, the accuracy metrics, the transition matrix—all signal that this is a **system**, not a blog.

### What's Not Working

1. **Static data masquerading as live**: The homepage snapshot cards show hardcoded values ("1.0847", "72.4%"). If the API is down, the site lies. Add a "stale data" indicator or server-side fallback.
2. **No charting**: A financial research site without interactive charts is like a restaurant without plates. The sparkline is cute; a proper regime-overlay chart is essential.
3. **Mobile experience is second-class**: The terminal pair page grid collapses to single column but loses context. The 4-column top strip becomes a scroll marathon.
4. **Substack is an orphan**: The RSS feed exists but is not prominently displayed. The newsletter is arguably the primary distribution channel; it should be central to the UX, not a footnote.
5. **No social proof mechanisms**: No Twitter/X embed, no "shared by" counts, no testimonial quotes. For a public research system, the absence of community signals is deafening.
6. **Search is absent**: No site search, no memo search, no regime history search. At 27 calls, this is manageable. At 270, it's unusable.
7. **Inconsistent terminal implementations**: There are at least three terminal-related components (`terminal-home-dashboard.tsx`, `terminal/page.tsx`, `TerminalNav`) with overlapping concerns and different styling approaches. This is technical debt that will compound.

---

## Synthesis

### Design Direction Statement

> **FX Regime Lab should feel like the private research terminal of a disciplined macro analyst who decided to leave the door open. The aesthetic is warm, rigorous, and unhurried on the surface—but densely informative when you lean in. Every page should answer two questions simultaneously: "What is the call?" and "Why should I believe it?" The design must earn the right to be minimal by making every remaining element exceptionally precise. The target is not "Bloomberg for retail"—it is "Bernstein for the open web."**

### Feature Gap Analysis

| Feature | Benchmark Standard | FXRL Status | Gap Severity |
|---------|-------------------|-------------|--------------|
| Interactive charting | TradingView/Koyfin | Sparkline only | 🔴 Critical |
| Email subscription | Substack | RSS only, no capture | 🔴 Critical |
| Memo archive browse | Substack/Bernstein | Deep links only | 🔴 Critical |
| Site search | Bloomberg/Linear | None | 🟡 High |
| Social sharing | Substack/Ark | None | 🟡 High |
| Mobile terminal UX | Koyfin | Collapsed grid | 🟡 High |
| Macro calendar | Koyfin/Bloomberg | Sparse placeholder | 🟡 High |
| PDF export | Bernstein/Ark | Print styles exist but untested | 🟢 Medium |
| Keyboard shortcuts | Bloomberg/Linear | Command palette only | 🟢 Medium |
| Dark theme consistency | Linear/Koyfin | One theme (good) | 🟢 Low |

### Quick Wins — 5 Changes with Highest Impact

1. **Add Email Capture to Homepage**  
   Place a simple email input + "Get the brief" button below the Validation Trust section. Route to Substack or a simple Supabase table. *Impact: Converts visitors to subscribers. Effort: 2 hours.*

2. **Replace Hardcoded Homepage Stats with Live Data**  
   The snapshot cards should pull from the same API as the terminal. Add a "last updated" timestamp. If data is stale, gray out the card. *Impact: Eliminates the "toy" feeling. Effort: 4 hours.*

3. **Add a TradingView Chart to Each Pair Desk**  
   Embed the free TradingView widget with FX spot data. Overlay regime-change dates as markers. *Impact: Transforms the terminal from a data table to a research tool. Effort: 4 hours.*

4. **Create `/memos` Archive Page**  
   Reverse-chronological list with month dividers, pair tags, and one-line excerpts. *Impact: Turns ephemeral briefs into a searchable corpus. Effort: 6 hours.*

5. **Unify Terminal Implementation**  
   Consolidate `terminal-home-dashboard.tsx` and `terminal/page.tsx` into a single source of truth. The server component approach is correct for SEO; the client dashboard should be a thin wrapper. *Impact: Reduces maintenance burden and visual inconsistency. Effort: 8 hours.*

### Long-Term Vision — Where Should the Site Be in 6 Months?

**Month 1–2: Foundation**
- Fix all static data on homepage
- Launch `/memos` archive
- Add email capture + Substack integration
- Unify terminal codebase
- Add TradingView charts to pair desks

**Month 3–4: Depth**
- Build interactive regime-explorer (what-if weight slider)
- Add cumulative performance chart to Performance page
- Implement site search (Algolia or FlexSearch)
- Launch "Regime Outlook" long-form report (Ark-style)
- Add macro calendar with event impact markers

**Month 5–6: Distribution**
- Add "Share this call" social cards (OpenGraph images already exist—extend)
- Build weekly summary email automation
- Launch API endpoint for regime data (developer access)
- Publish downloadable PDF reports
- Consider open-sourcing the validation methodology repo

**6-Month Success Metrics**
- Homepage → Terminal conversion rate > 15%
- Email subscriber count > 500
- Average time on pair desk > 90 seconds
- Zero hardcoded financial data on any page
- Mobile terminal usability score > 8/10

---

## Honest Assessment

FX Regime Lab is not a bad site. It is a **good site with great bones** that has not yet decided whether it wants to be a blog, a dashboard, or a research publication. The ambiguity is visible in the code: three terminal implementations, a Substack feed that goes nowhere, a print stylesheet that may or may not work, and an audit page that feels like a developer joke.

The good news: these are all **execution gaps**, not strategy gaps. The strategy—public validation, transparent methodology, daily discipline—is rock solid. The design system—Obsidian Stone, Inter + Mono, warm dark mode—is differentiated and defensible.

The next phase is about **finishing**. Finish the terminal. Finish the archive. Finish the mobile experience. Finish the integration between shell and terminal so the user never feels like they've switched applications.

Then, and only then, add new features. The discipline of restraint is what separates Bloomberg from its imitators. FX Regime Lab should inherit that discipline.

---

*End of Round 1 Competitive Analysis*
