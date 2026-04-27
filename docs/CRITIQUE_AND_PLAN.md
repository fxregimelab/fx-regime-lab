# FX Regime Lab — Multi-Domain Frontend Audit & Master Action Plan

> **2026-04-28:** The **`web/`** tree referenced throughout this audit was **removed**. Keep the document for UX and data-flow lessons; ignore file paths under `web/` until a new frontend exists.

**Date:** 2026-04-18  
**Audited by:** 7-agent frontend team (structured critique session)  
**Scope:** Repo files under `web/` (now deleted), project docs, and alignment with live product goals (fxregimelab.com).  
**Note:** This document is an audit and planning artifact only; no code was changed in this session.

---

## CREATIVE DIRECTOR REPORT

**Overall verdict:** The shell already reads as a serious, editorial macro desk with a clear two-surface concept, but a few student-cohort tells (explicit age, “EE undergrad”) and some template-adjacent patterns keep it from full practitioner gravitas.

**Strongest element:** The **EUR/USD hero regime card** — dark surface on the light shell, large Fraunces italic regime line, and JetBrains-forward metrics create an immediate “live desk snapshot” that matches the stated positioning.

**Weakest element:** The **Research → “FX regime” destination** — it resolves to a thin dynamic strategy stub (`web/app/(shell)/[strategy]/page.tsx`) with almost no content, which undercuts the promise of a coherent research system.

**Brand identity score:** **7/10** — Typography pairing and restraint on gradients land well; amber is used mostly on links and emphasis as intended. Gaps are copy tone (age-first), incomplete narrative on secondary routes, and reliance on generic card chrome (white cards, light shadow) that sits close to “nice template” unless paired with richer content.

**5-second impression:** “Someone is publishing a daily FX regime view with validation — looks intentional and calm — the headline admits they are early in building proof.”

**Top 5 issues ranked by impact:**

1. Hero body copy leads with **age and degree** before the thesis, signaling “student portfolio” before “research desk.”
2. **“Building the track record.”** reads as honest but slightly **apologetic** next to sparse public history; it frames process over authority.
3. **Fraunces italic on all-caps pipeline strings** (e.g. `STRONG USD STRENGTH`) is authoritative but can feel **shouty**; it is not wrong, but it needs supporting gloss for non-specialists.
4. **Amber accent** is mostly disciplined; risk is overuse on every CTA link, which can feel **repetitive** rather than “highest conviction only.”
5. **Canvas grid background** is subtle and tasteful; however, continuous redraw (see engineering note) can imply “tech demo” if it ever stutters.

**Recommended fixes:**

- Rewrite hero supporting line to **lead with the research thesis**, then one credibility line (discipline, public validation) — move biographical detail to About only or a single short clause.
- Replace or qualify **“Building the track record.”** with a line that signals **discipline + transparency** without sounding provisional (e.g. emphasis on published calls and validation, not “we’re still building”).
- Add a **one-line regime glossary** or hover/tooltip pattern on the hero card for the regime string (or sentence-case mapping via `REGIME_LABELS` where appropriate).
- Reserve amber for **primary CTAs** and key numerals; use neutral underline for secondary navigation-adjacent links where possible.
- Flesh out `**/fx-regime`** into a real hub (pair links, terminal entry, what “strategy” means) so the brand reads as a **system**, not a stub.

---

## UX ARCHITECT REPORT

**Overall verdict:** Core IA (Home → Brief / Performance / About, plus Terminal) is sensible for a research journal, but naming and incomplete strategy pages create friction for first-time professional visitors.

**Critical user journey (macro PM / recruiter):**

1. Land on **Home** — scan headline, regime card, track record strip.
2. Seek **proof** — open **Performance** or **validation log**.
3. Seek **depth** — open **Brief** or **Terminal** pair desk.
4. Seek **operator credibility** — **About**.
5. Optional: verify **freshness** (pipeline timestamp) and **methodology** (linked from About / future Methodology).

**Journey breakdown points:**

- **“Research” dropdown:** “Performance” is clear; **“FX regime”** is ambiguous (sounds like a topic, not a destination). Users may expect methodology or a hub; they get a **minimal strategy title page**.
- **Shell → Terminal:** Different chrome (light vs dark) is clear, but there is **no universal “Back to shell”** beyond the browser; TerminalNav is minimal.
- **Proof density:** Track record is young; without narrative framing, users may **bounce after seeing low headline accuracy** without understanding sample size and window.
- **Brief vs archived HTML brief:** Operators may wonder if `/brief` is the same artifact as legacy pipeline HTML; **discoverability of equivalence** is weak.

**IA score:** **7/10** — Logical top-level buckets; gaps are naming (`FX regime` label), shallow `/fx-regime`, and missing explicit “Methodology / definitions” in primary nav.

**Missing pages (or materially incomplete routes):**

- **Methodology / definitions** — expected for institutional credibility; currently only partial coverage in About and signal architecture section.
- **Changelog / data freshness** — pipeline timestamp on home helps; a single **status** page could reduce anxiety.
- **Pair index under shell** — Terminal lists pairs, but shell users may want **EUR/USD / USD/JPY / USD/INR** without entering terminal.
- **404 / error recovery** — custom `not-found` exists per architecture doc note, but **no `error.tsx`** per route for graceful Supabase failures.

**Top 5 issues ranked by impact:**

1. `**ROUTES.fxRegime` → `/fx-regime`** content is too thin to justify primary nav placement.
2. **Research naming** does not telegraph “Performance vs desks vs methodology.”
3. **Terminal exit path** relies on user knowledge; consider a persistent **Shell** link in TerminalNav.
4. **Performance page** is strong on rows but light on **interpretation** — risk of looking like a raw dump.
5. **Brief page** instability (see engineering) breaks the “research artifact” journey.

**Recommended fixes (priority):**

1. **P0:** Replace strategy stub with a **Regime hub**: links to `/terminal/fx-regime/...`, one-paragraph scope, link to Performance.
2. **P0:** Rename dropdown item to **“FX regime (desks)”** or **“Pair desks”** if terminal-first.
3. **P1:** Add **“Methodology”** or anchor section with definitions table (even stub).
4. **P1:** TerminalNav add `**Brief`** or `**Shell home**` for orientation.
5. **P2:** Consider `**/pairs`** index in shell mirroring `PAIRS`.

---

## UI DESIGNER REPORT

**Overall verdict:** The shell broadly follows the design tokens (shell-bg, accent, Fraunces for regime labels, mono for numbers), but several components use **hardcoded hex** instead of Tailwind tokens, and **Badge / pair cards** diverge from the “Fraunces for regime only” rule documented in `docs/DESIGN_SYSTEM.md`.

**Design system compliance score:** **6.5/10**

**Typography violations:**

- `Nav` brand uses `**font-display`** for site title — acceptable as brand mark, but design doc says Fraunces for **regime call labels only**; this is a minor philosophical drift (brand vs rule).  
- `SignalArchitectureSection` H2 uses `**text-[32px]`** instead of a documented type scale (no shared `text-display` token).  
- `AboutStrip` H2 uses `**text-4xl**` while other shell H1s use `**font-display text-3xl**` — heading step inconsistency.  
- `ValidationTable` shell variant at `**text-[11px]**` may fall **below readable minimum** on mobile for some users.  
- Terminal `**TerminalNav`** uses `**font-mono` for entire strip** — matches known doc gap (“mono for whole blocks”).  
- `ui/Badge.tsx` (not re-read in full here; referenced in design doc) — **regime chips use mono**, not Fraunces italic, per `DESIGN_SYSTEM.md` reality note.

**Color violations:**

- `RegimeCard` hero and empty states use `**bg-[#1a1a1a]`** instead of `**bg-terminal-surface**` (same hex, but bypasses token).  
- `TrackRecordStrip` uses `**bg-[#1a1a1a]**` instead of token class.  
- `ConfidenceBar` uses **neutral greys** for fill — aligns with “greyscale track”; **accent** is not used (doc allows accent only for peaks — acceptable).

**Spacing violations:**

- `HomeHero` / pair cards use `**rounded-xl`** while tokens define `**rounded-card**` — minor inconsistency.  
- `SignalArchitectureSection` `**gap-10` / `lg:gap-8**` mixes spacing rhythm without a clear 4/8 grid system on large breakpoints.

**Component inconsistencies:**

- **Hero regime card** vs **three pair cards:** Hero is **dark inset**; pair cards are **white** with border — intentional hierarchy, but **regime typography** differs (`text-xl` vs hero `text-2xl/md:text-3xl`).  
- **Confidence display:** Hero emphasizes **large numeric %**; compact cards emphasize **bar + separate % line** — consistent logic, different visual weight (acceptable).  
- **Performance vs home strip:** `TrackRecordStrip` vs `PerformanceClient` stat blocks — same concept, **light container vs dark band** — intentional surface split; typography scales differ slightly (`text-3xl` vs `text-2xl` in performance white cards).  
- **BriefRenderer:** `text-sm` body — reads as **generic blog**, not “institutional brief” (typography hierarchy, pull quotes, section headers).  
- **PairDesk empty state:** Uses `RegimeCard` empty message in **mono** — reads like an error log, not a guided empty state.

**Top 5 issues ranked by severity:**

1. **Hardcoded `#1a1a1a`** instead of `terminal-surface` in multiple components — undermines token discipline.
2. **Brief typography** lacks brief-specific hierarchy (labels, sections).
3. `**ValidationTable` 11px** on shell — risks readability.
4. **Nav / About / Signal architecture** heading sizes — not on a single scale.
5. **Badge vs card regime styling** — Fraunces rule not applied uniformly.

**Recommended fixes (with token names):**

- Replace `**bg-[#1a1a1a]`** with `**bg-terminal-surface**` in `RegimeCard`, `TrackRecordStrip`.  
- Introduce `**text-brief-body` / `prose-brief**` pattern in `BriefRenderer` (could be Tailwind `@apply` in `globals.css` or component classes).  
- Bump `**ValidationTable` shell** body to **12px minimum** (`text-xs` default) or responsive step.  
- Normalize marketing headings to `**font-display`** steps shared across `HomeHero`, `SignalArchitectureSection`, `AboutStrip`.  
- Align `**Badge**` with Fraunces italic for regime text when touching that component.

---

## FRONTEND ENGINEER REPORT

**Overall verdict:** Server-side Supabase reads on the home and brief pages are **edge-configured**, but **browser Supabase** depends on `**NEXT_PUBLIC_*` at client build time**; combined with unconditional client refetch hooks, this explains persistent **“Missing NEXT_PUBLIC_SUPABASE_URL…”** and **terminal empty states** even when secrets exist in the hosting UI.

**Critical bugs (breaks functionality):**

1. `**NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` missing in client bundle**
  - **Root cause:** `web/lib/supabase/client.ts` throws if env vars are falsy. In Next.js, `NEXT_PUBLIC_*` values are **inlined at build time**. Cloudflare Pages (and similar) must expose these to the **build** step. Runtime-only injection does not fix the browser bundle.  
  - **Evidence:** `createBrowserClient` path used by `useBrief`, `useRegimeCalls`, `useHomeMarketData`, `useValidationHomeStrip`, `PerformanceClient` effects.
2. `**useBrief` overwrites successful SSR with client error**
  - **Root cause:** `BriefRenderer` always runs `useBrief`’s `useEffect` refetch (`web/hooks/useBrief.ts`). On the client, `createClient()` may throw or fail while the server (`createServerClient` in `web/lib/supabase/server.ts`) succeeded using runtime env. State then **replaces** good `initialBrief` with an error.  
  - **Exact failure line:** `createClient()` in `web/lib/supabase/client.ts` lines 6–8 throw; caught in `useBrief` lines 40–44, setting `error` and clearing content path.
3. **Terminal pair desks have no SSR data for regime calls**
  - **Root cause:** `web/app/terminal/[strategy]/[pair]/page.tsx` only renders `<PairDesk />`. `PairDesk` relies on `**useRegimeCalls` / `useSignalValues`** (client-only). If the browser cannot create Supabase client, `**row` stays null** after error handling.  
  - **Render path:** `useRegimeCalls` → `getLatestRegimeCallForPair` → on error `setRow(null)` (`web/hooks/useRegimeCalls.ts` lines 21–26) → `RegimeCard` receives `call={null}` → **“No regime call for this pair.”** (`web/components/regime/RegimeCard.tsx` lines 106–116).  
  - **Note:** Pair slug resolution (`resolvePairLabel` in `PairDesk.tsx`) is **unlikely** to be the primary bug if URLs match `PAIRS[].urlSlug`; the **client env** issue is the more plausible systemic cause.
4. **Misleading empty state vs real errors**
  - **Root cause:** `PairDesk` does not surface `useRegimeCalls` **error** string; `RegimeCard` maps null call to empty copy. Users cannot distinguish **config failure** from **no database row**.

**Non-critical bugs:**

- `PerformanceClient` `useEffect` (`web/components/shell/PerformanceClient.tsx` lines 42–57) calls `createClient()` **without try/catch** — can produce **unhandled promise rejection** if client throws.  
- `CanvasBg` runs a **tight `requestAnimationFrame` redraw loop** (`web/components/shell/CanvasBg.tsx`) — unnecessary continuous work; should redraw on resize only or throttle.  
- No `**loading.tsx` / `error.tsx`** beside routes (per `docs/FRONTEND_ARCHITECTURE.md`) — soft UX gap.

**Performance issues:**

- Continuous **canvas RAF** may impact **main-thread time** and mobile battery.  
- No Lighthouse run in this audit; **LCP** likely dominated by hero text and fonts; canvas may contribute jank on low-end devices.  
- **Image:** `next.config.js` sets `images.unoptimized: true` — acceptable for Cloudflare; no broken `next/image` pipeline observed.

**Type safety issues:**

- `parseRegimeCallRow` in `web/lib/supabase/queries.ts` forces unknown `regime` strings to `**UNKNOWN`** — can **mask** DB values not in the `RegimeLabel` union until a mapping layer exists (documented in `docs/DATABASE_SCHEMA.md`).  
- `RegimeCall.regime` typed as `RegimeLabel` while DB may evolve — acceptable short-term but fragile.

**Missing error states:**

- Shell pages: server `try/catch` often swallows errors silently (`web/app/(shell)/page.tsx` lines 45–47) — user may see **empty cards** without explanation.  
- `PairDesk`: no error UI.  
- `PerformanceClient`: table refetch errors not surfaced.

**Top 5 issues ranked by severity:**

1. Client bundle **missing `NEXT_PUBLIC_*` at build** → breaks all browser Supabase.
2. `**useBrief` client refetch** clobbers SSR success.
3. **Terminal routes** client-only data path.
4. **Error vs empty** conflation in `PairDesk` / `RegimeCard`.
5. `**PerformanceClient` unhandled throw** risk.

**Exact fixes for brief page and terminal pair desks (step by step):**

**Brief page**

1. **Configure Cloudflare Pages (or CI)** so `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` exist **during `next build` / `next-on-pages` build**, not only as runtime secrets.
2. In `useBrief`, **short-circuit** the client effect when `initialBrief` is already populated and optionally when `process.env.NEXT_PUBLIC_SUPABASE_URL` is missing (guard refetch).
3. Alternatively, **remove client refetch** for v1 and rely on **server-only** brief delivery + manual refresh route segment.
4. Add `**error.tsx`** on `/brief` for server failures.

**Terminal pair desks**

1. Same **build-time public env** requirement for any client hook.
2. In `web/app/terminal/[strategy]/[pair]/page.tsx`, **server-fetch** `getLatestRegimeCallForPair` and `getSignalsForPair` using `createClient()` from `web/lib/supabase/server.ts`, pass as `**initialCall` / `initialSignals`** into `PairDesk` (refactor `PairDesk` to accept initial props + optional client refresh).
3. Surface `**useRegimeCalls` error** in `PairDesk` when `row` is null and `error` is set.
4. Confirm production URL uses `**eurusd` / `usdjpy` / `usdinr`** segments matching `PAIRS` (already normalized in `resolvePairLabel`).

**Validation log 500 rows:** `getValidationLog` with `limit: 500` matches description; ordering **newest first** is consistent with `PerformancePage` server fetch.

---

## DATA ANALYST REPORT

**Overall verdict:** Numbers are **honest but under-explained**; a few metric labels (**“20-DAY ACCURACY”**) do not match the implementation (**last 20 validation rows**, not 20 calendar days), which affects credibility with quant-literate visitors.

**Data presentation score:** **6/10**

**Missing context issues:**

- **Rate differential** — value shown without **units** (likely %-point or bp — pipeline-defined); visitors cannot interpret magnitude.  
- **COT percentile** — labeled “percentile” but not **which cohort / asset class window** in the UI (body text mentions COT in architecture section, not inline).  
- **Realized vol** — no **annualized vs daily** clarification.  
- **Signal composite** — **no scale** (expected range, neutral point). Hero shows e.g. **2.40** without anchor.  
- **Confidence** — shown as **0–100%** derived from score magnitude; methodology link not on card.

**Accuracy presentation issues:**

- **Rolling 20** uses `recentRows.slice(0, 20)` in `getValidationRolling20Display` (`web/lib/supabase/queries.ts` lines 17–22) — this is **20 most recent rows** across all pairs, **not** “20 days” and not “20 predictions per pair.” The UI label **“20-DAY ACCURACY”** (`TrackRecordStrip`, `PerformanceClient`) is **misleading**.  
- Early **low headline percentage** (e.g. 18%) can be **honest** but needs explicit **sample size, window definition, and exclusion rules** (e.g. NEUTRAL handling — see below).  
- **“DAYS LOGGED”** uses **distinct `date` values** in `validation_log` via `getValidationDistinctDateCount` — computationally heavy but semantically OK; still needs **plain-language** explanation.

**Accuracy / NEUTRAL handling (code-level observation):**

- `rolling20AccuracyDisplay` filters rows where `correct_1d != null` — does not special-case **NEUTRAL** predictions. **Credibility depends on pipeline**: if `validation_regime.py` marks `correct_1d` false for NEUTRAL when the market moved, the UI will **understate** directional skill. **Verify Python logic** — out of scope here but flagged.

**Validation table issues:**

- Columns **Date / Pair / Pred / Actual / 1d** are a decent minimum; **missing** for evaluation: **predicted regime**, **confidence**, **actual 1d return**, **notes**, and **per-pair filter** in UI.  
- **“Pred”** should expand to **“Predicted direction”** on first use or in caption.

**Regime label clarity:**

- Raw labels like `**STRONG USD STRENGTH`** are **jargon-heavy** for casual visitors; for FX practitioners they are **fine**. `REGIME_LABELS` in `web/lib/constants/regimes.ts` provides **sentence-case titles** but **RegimeCard does not use them** — it prints `**call.regime` raw from DB**.

**Performance page narrative:**

- Reads as **metrics + dump** — needs a short **interpretation** paragraph: what window, what population, what “good” means in context of regime classification vs directional bets.

**Top 5 issues ranked by impact on credibility:**

1. **Mislabeled rolling metric** (“20-DAY” vs 20-row).
2. **Composite score without range**.
3. **Raw regime strings** instead of humanized labels.
4. **Missing units** on market fields.
5. **NEUTRAL scoring** must be validated in pipeline and reflected in copy.

**Recommended fixes:**

- Rename UI to **“Last 20 scored outcomes (1d)”** or compute a true **20-trading-day** window on distinct dates.  
- Add **units** beside rate diff and vol; add **footnote** for COT percentile definition.  
- Display `**REGIME_LABELS[regime]`** (with fallback to raw) on cards.  
- Add **methodology box** on Performance: population, horizon, exclusions.  
- If sample is tiny, add **explicit caution** next to accuracy.

---

## CONTENT STRATEGIST REPORT

**Overall verdict:** Voice is **clear and non-hype**, but several strings **lead with student identity** and **internal product language** (`validation_log` in user-facing Performance copy) that works in-repo but not on the public surface.

**Copy that works well:**

- **Signal architecture** pillars — concrete, practitioner tone (“52-week percentile”, “iv_gate”, “carry regime”).  
- **About** sections “What this is” and “Validation” — disciplined, no overclaim.  
- **Footer** — short disclaimer posture is appropriate.  
- **Track record strip** subcopy — **“No backdating…”** is strong.

**Copy that undermines positioning (with direction for rewrites):**

- **“20. EE undergrad.”** — reads as **dossier**, not desk. Move to About or shorten to **one clause** without leading.  
- **“Studying how…”** — academic framing; prefer **“Tracking how…”** or **“Measuring…”**.  
- **“Building the track record.”** — slightly **defensive**; pair with **what is already on record** (dates, pairs, validation).  
- **Performance:** “Metrics aggregate all pairs in `validation_log`” — **table name** in user-facing copy reads **developer-first**.  
- **Performance:** “Recent rows from `validation_log`…” — same issue.  
- **About strip:** “This is where I practice.” — true but **student-studio** cadence; tighten to **operations language**.  
- **Strategy page (`/fx-regime`):** “Overview and links to terminal desks.” — **placeholder tone**; either add real links or hide route from nav until ready.

**Tone inconsistencies:**

- Home hero: **first-person youthful bio** vs Signal architecture: **analytical third-person explainer**.  
- Terminal: mostly **neutral labels**; shell: **personal**. Acceptable if intentional, but **hero should pick one mode** for the first screen.

**Missing copy:**

- **Regime string** humanization on cards.  
- **What “1d Y/N” means** in validation table (caption).  
- **Brief:** date line / title from `brief_log` not surfaced in `BriefRenderer` (only body text).

**Top 5 issues ranked by positioning impact:**

1. **Age-first hero** clause.
2. **SQL/table names** in Performance prose.
3. **Placeholder `/fx-regime` copy** linked from nav.
4. **“Practice”** language in About strip.
5. **H1 “Building…”** without anchoring existing receipts.

**Recommended rewrites (old → new):**

- **“LIVE MACRO STRATEGY · SINCE APRIL 2026”** → **“PUBLIC FX REGIME DESK · LIVE SINCE APR 2026”** (or keep if brand prefers “macro strategy”).  
- **“Building the track record.”** → **“Daily G10 regime calls, validated in public.”** (example — keep Fraunces hierarchy).  
- **“20. EE undergrad. Studying how G10 FX regimes form and break…”** → **“G10 FX regimes through rates, positioning, and vol. Calls are timestamped; outcomes are logged next session.”** + short bio link.  
- **“Public validation trail… in `validation_log`.”** → **“Public validation trail across all pairs in the database (no backdating).”**  
- **“Recent rows from `validation_log` (newest first, up to 500).”** → **“Most recent validated outcomes (newest first, up to 500 rows).”**  
- **“This is where I practice.”** → **“This is the live stack: daily runs, public calls, documented methodology.”**  
- **Strategy stub sentence** → replace with **three links**: EUR/USD, USD/JPY, USD/INR terminal desks + Performance.

---

## MOBILE AND ACCESSIBILITY REPORT

**Overall verdict:** Layout is **responsive-first** in structure (grids collapse, overflow-x on table), but **navigation**, **touch targets**, and **table readability** need hardening for small phones and WCAG-aligned contrast.

**Mobile layout score:** **7/10**

**Critical mobile breaks:**

- `**ValidationTable` on Performance** — wide monospace table inside `**overflow-x-auto`** forces **horizontal scroll** on ~390px; usable but **not ideal** without **card fallback** or **sticky first column**.  
- **Research dropdown** — **no click-outside / Escape** handler visible in `Nav.tsx`; may **trap focus** or stay open unintentionally (behavior not fully verified in browser here).

**Accessibility violations (likely / code-based):**

- **Research dropdown button** lacks `**aria-controls` / `aria-haspopup`** and an `**id` for the menu** for screen readers (`web/components/shell/Nav.tsx`).  
- **Canvas background** — `aria-hidden` present (good); still **continuous animation** may affect users sensitive to motion — consider `**prefers-reduced-motion`** gating.  
- **Footer / nav links** — contrast on `**text-neutral-600`** on `**shell-bg**` likely passes for large text; **small muted text** near **11–12px** should be verified against **WCAG 1.4.3** (use contrast checker on `neutral-500` / `neutral-600` vs `#f5f5f0`).

**Touch target issues:**

- **Nav links** (`text-sm`, padding implicit from flex only) — **likely under 44×44px** per Apple HIG / WCAG 2.5.5 (target size **Level AAA**).  
- **Research button** — similar concern.  
- **TerminalNav** links — **small text** (`text-xs`) with `**py-2`** — probably **under 44px height**.

**Color contrast issues:**

- `**text-muted` equivalents** (`text-neutral-500`, `text-neutral-600`) on `**shell-bg`** for **fine print** — borderline; verify with tooling.  
- **Accent links** on shell — underline helps; still verify **orange on warm off-white**.

**Top 5 issues ranked by severity:**

1. **Small touch targets** in `Nav` / `TerminalNav`.
2. **Validation table** horizontal scroll cognitive load.
3. **Dropdown a11y** attributes + focus trap.
4. **Motion** (`CanvasBg`) without reduced-motion guard.
5. **Font sizes at 11px** in validation table.

**Recommended fixes:**

- Increase **clickable padding** on nav links (`py-3 px-2` min) and terminal links.  
- Add `**aria-haspopup="menu"`**, `**aria-expanded**`, and **keyboard handlers** (Escape).  
- Add `**@media (prefers-reduced-motion: reduce)`** to disable or slow canvas updates.  
- Bump validation mono table to `**text-xs` (12px)** minimum or provide **stacked card view** under `md`.  
- Run **axe** / **Lighthouse a11y** on production URLs for definitive WCAG signaling.

---

## MASTER ACTION PLAN — FX Regime Lab Frontend Audit

**Date:** 2026-04-18  
**Audited by:** 7-agent frontend team

### EXECUTIVE SUMMARY

The **v2 shell** successfully communicates a **two-surface research product** (calm public shell, dense terminal) with **strong hero regime visualization** and a **coherent typography stack** (Inter / Fraunces / JetBrains). **Live Supabase reads on the server** (`web/app/(shell)/page.tsx`, `brief/page.tsx`, `performance/page.tsx`) are architecturally sound for **edge runtime**.

The **most critical problem** is the **browser Supabase client contract**: `NEXT_PUBLIC_*` variables must exist at **build time**, and several **client hooks refetch unconditionally**, which can **overwrite SSR success** (notably `**useBrief`**) or show **misleading empty states** in `**PairDesk`** when the real issue is **configuration**, not missing DB rows.

Overall quality is **solid for an early Phase 1 scaffold** — roughly **“strong design intent with production wiring gaps”** — but **professional sharing** should wait until **env/build**, **terminal SSR or guarded hooks**, and **metric label honesty** are fixed.

---

### CRITICAL BUGS — Fix immediately (blocks functionality or breaks credibility)

#### 1. Browser bundle missing `NEXT_PUBLIC_SUPABASE_*` at build time

- **Issue:** Client `createClient` throws; hooks fail; brief may error after hydration; terminal shows **“No regime call…”**.  
- **Root cause:** Next.js inlines `NEXT_PUBLIC_*` at **build**; Pages runtime secrets alone are insufficient for the browser bundle.  
- **Fix:** Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to **Cloudflare Pages → Build environment** (and local `.env` for dev). **Rebuild** deploy. Verify `window` bundle contains non-empty strings (spot-check built artifact or runtime test).  
- **Files:** `web/lib/supabase/client.ts` (consumer), deployment docs / `DEPLOY.md` if present, Pages project settings.  
- **Effort:** **0.5–2 h** (fast if access is straightforward; longer if CI secrets need restructuring).

#### 2. `useBrief` client refetch overwrites successful SSR

- **Issue:** Brief flashes then shows **error** even when server rendered content.  
- **Root cause:** `useBrief` always refetches on mount (`web/hooks/useBrief.ts`); client failure replaces good state.  
- **Fix:** Guard client fetch: if `initialBrief?.brief_text` is present, **skip** refetch OR catch missing env and **preserve SSR state**. Optionally remove client refetch for Phase 1.  
- **Files:** `web/hooks/useBrief.ts`, optionally `web/components/brief/BriefRenderer.tsx`.  
- **Effort:** **1–2 h**.

#### 3. Terminal pair desks depend on client-only Supabase

- **Issue:** No regime data shown when browser client fails; worse than home (which SSR-seeds).  
- **Root cause:** `PairDesk` only uses hooks; page does not pass server-fetched rows.  
- **Fix:** Server-fetch in `web/app/terminal/[strategy]/[pair]/page.tsx` via `createClient` from `web/lib/supabase/server.ts`, pass `**initialCall` / `initialSignals`** into `PairDesk`; keep optional client refresh.  
- **Files:** `web/app/terminal/[strategy]/[pair]/page.tsx`, `web/components/terminal/PairDesk.tsx`, possibly `web/hooks/useRegimeCalls.ts`.  
- **Effort:** **3–5 h**.

#### 4. Empty state conflates “no row” with “misconfigured client / query error”

- **Issue:** **“No regime call for this pair”** appears for **errors**.  
- **Root cause:** `PairDesk` / `RegimeCard` do not branch on `useRegimeCalls.error`.  
- **Fix:** Pass `error` through; show **distinct copy** for misconfiguration vs empty DB.  
- **Files:** `web/components/terminal/PairDesk.tsx`, `web/components/regime/RegimeCard.tsx` (optional new prop).  
- **Effort:** **1–2 h**.

---

### HIGH PRIORITY — Fix before sharing publicly with any professional contact

#### 5. Mislabeled “20-DAY ACCURACY” vs 20-row window

- **Issue:** Quant-literate visitors see **label mismatch**.  
- **Root cause:** `rolling20AccuracyDisplay` uses **20 rows**, not 20 days (`web/lib/supabase/queries.ts`).  
- **Fix:** Rename labels OR change computation to **true 20-day / 20-session** rule; document in UI.  
- **Files:** `web/lib/supabase/queries.ts`, `TrackRecordStrip.tsx`, `PerformanceClient.tsx`.  
- **Effort:** **2–4 h** depending on desired metric.

#### 6. SQL identifiers in Performance page copy

- **Issue:** Reads **developer-first**, not practitioner-first.  
- **Root cause:** Copy includes ``validation_log`` strings.  
- **Fix:** Replace with plain language per Content Strategist rewrites.  
- **Files:** `web/app/(shell)/performance/page.tsx`, `web/components/shell/PerformanceClient.tsx`.  
- **Effort:** **0.5 h**.

#### 7. `/fx-regime` strategy page is placeholder while linked from primary nav

- **Issue:** Dead-end / low-value journey from **Research**.  
- **Root cause:** `web/app/(shell)/[strategy]/page.tsx` minimal.  
- **Fix:** Add **pair links**, **Performance** link, one-paragraph scope; or **temporarily remove** nav item until built.  
- **Files:** `web/app/(shell)/[strategy]/page.tsx`, possibly `web/components/shell/Nav.tsx` (label).  
- **Effort:** **2–3 h**.

#### 8. `PerformanceClient` fetch without try/catch

- **Issue:** Potential **unhandled rejection**.  
- **Root cause:** `createClient()` throw escapes async effect.  
- **Fix:** Wrap in **try/catch** like other hooks.  
- **Files:** `web/components/shell/PerformanceClient.tsx`.  
- **Effort:** **0.25 h**.

#### 9. Canvas continuous `requestAnimationFrame` loop

- **Issue:** Unnecessary **per-frame** work; mobile/battery impact.  
- **Root cause:** `CanvasBg` redraws forever (`web/components/shell/CanvasBg.tsx`).  
- **Fix:** Draw on **resize** only; respect `**prefers-reduced-motion`**.  
- **Files:** `web/components/shell/CanvasBg.tsx`.  
- **Effort:** **1–2 h**.

---

### MEDIUM PRIORITY — Fix within Phase 1 completion

#### 10. Token discipline (`#1a1a1a` → `terminal-surface`)

- **Files:** `RegimeCard.tsx`, `TrackRecordStrip.tsx`.  
- **Effort:** **0.5 h**.

#### 11. Brief typography — institutional brief styling

- **Files:** `BriefRenderer.tsx`, possibly `globals.css`.  
- **Effort:** **2–4 h**.

#### 12. Validation table readability + optional mobile card layout

- **Files:** `ValidationTable.tsx`, `PerformanceClient.tsx`.  
- **Effort:** **3–6 h**.

#### 13. Nav / TerminalNav touch targets + dropdown a11y

- **Files:** `Nav.tsx`, `TerminalNav.tsx`.  
- **Effort:** **2–4 h**.

#### 14. Humanized regime labels on cards using `REGIME_LABELS`

- **Files:** `RegimeCard.tsx`, `HomePairCards.tsx`.  
- **Effort:** **1–2 h**.

#### 15. Route-level `error.tsx` / `loading.tsx` for shell and terminal

- **Files:** `web/app/(shell)/…`, `web/app/terminal/…`.  
- **Effort:** **2–4 h**.

---

### LOW PRIORITY — Phase 2 and beyond

- **Methodology page** with definitions and units for all headline metrics.  
- **Centralize Supabase reads** in `queries.ts` only (per architecture doc — incremental).  
- **Badge / Fraunces alignment** for regime chips.  
- **Multi-strategy** true routing when `strategy_id` exists in DB.  
- **Divergence / hypothesis logs** as in roadmap.

---

### PHASE 1 COMPLETION CHECKLIST

- `**NEXT_PUBLIC_SUPABASE_*` present at build**; production **brief** stable (no post-hydration error).  
- `**useBrief` does not clobber** successful SSR.  
- **Terminal pair desks** show latest regime rows **via SSR seed** and/or fixed client env.  
- **Distinct UI** for **Supabase config/query errors** vs **empty tables**.  
- **Rolling accuracy label** matches computation (rename or fix math).  
- **Performance copy** free of raw SQL table names in user-facing text.  
- `**/fx-regime` hub** useful or hidden until ready.  
- **Profile photo** replaced (still placeholder if pink/generic — user noted in `TASK.md`).  
- **Canvas** not continuously repainting at 60fps.  
- **Mobile validation** pass on **390px** width for **Performance** + **Terminal**.  
- **CI deploy** documented: `**wrangler pages deploy`** with Next build + env (per `TASK.md` / `docs/PHASES.md` gap).

---

### DESIGN SYSTEM VIOLATIONS TO FIX

- Hardcoded `**bg-[#1a1a1a]**` instead of `**bg-terminal-surface**` (RegimeCard, TrackRecordStrip).  
- **Heading scale** fragmentation (`text-[32px]` vs `text-3xl` vs `text-4xl`).  
- **Brief** body styling too generic for “research brief.”  
- `**Badge`** / chips: **mono vs Fraunces** for regime labels (per `DESIGN_SYSTEM.md`).  
- **Terminal** overuse of **mono for entire strips** vs numbers-only rule.  
- **ConfidenceBar** already close to greyscale intent — optional future accent-for-peaks.

---

### COPY TO REWRITE

- Hero: **age-first** clause → thesis-first (see Content Strategist).  
- H1: **“Building the track record.”** → stronger receipt-led headline.  
- Performance: remove `*`*validation_log`**` from user-facing sentences.  
- About strip: **“where I practice”** → operations-forward wording.  
- Strategy stub: replace placeholder **“Overview and links…”** with **real links** or remove from nav.

---

### WHAT IS GENUINELY GOOD AND SHOULD NOT BE CHANGED

- **Two-surface concept** (light shell / dark terminal) and **absence of gimmicky gradients**.  
- **Signal architecture** section: concrete, non-marketing copy.  
- **Footer** disclaimer posture and **no overclaim** tone in About.  
- **Home SSR + edge runtime** pattern for market data (`web/app/(shell)/page.tsx`).  
- **Pair constants** module (`web/lib/constants/pairs.ts`) and **URL normalization** in `PairDesk`.  
- **JetBrains** for numeric fields on cards — aligns with readability goals.  
- `**validation_log` table** direction — public accountability is the right differentiator.

---

**End of document.**