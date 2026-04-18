# FX Regime Lab — project overview

FX Regime Lab is a **personal, public research system** for daily G10 FX regime work: it ingests macro and positioning data, scores EUR/USD, USD/JPY, and USD/INR on a consistent composite, persists calls and signals to Supabase, generates a daily brief, and surfaces the same truth on a website so every call sits on the record.

## Two layers (conceptual)

- **Research ledger (private, immutable intent):** The durable record of *why* a view existed (hypotheses, rationale, drafts, private notes). In this repo today, that layer is **not** fully modeled in Postgres: there is **no** `call_rationale` or `hypothesis_log` table in the checked-in [[DATABASE_SCHEMA]]. Treat disk artifacts under `runs/`, `briefs/`, and archived `_archive/v1/docs/` as historical research context until those tables ship.
- **Performance record (public, auto-generated):** What the pipeline and site actually show: `signals`, `regime_calls`, `validation_log`, `brief_log`, and static outputs (`briefs/*.html`, `site/data/pipeline_status.json` when the pipeline creates `site/data/`). The Next.js app in `web/` is being wired to read this layer via the Supabase anon key and RLS read policies.

## strategy_id

The **product vision** is multiple strategies under one domain. **Reality in Postgres (as of `sql/schema.sql` in this repo):** there is **no** `strategy_id` column on `signals`, `regime_calls`, `validation_log`, or `brief_log`. The only strategy identifier in the Next.js codebase today is the **string** `fx-regime` in `web/lib/constants/strategies.ts`. Until migrations add `strategy_id`, document FX Regime Lab as **strategy 1 of N conceptually**, not in schema.

## North star

Build a **15-year research operating system** for a discretionary macro PM career: daily discipline, measurable calls, honest validation, and a public trace that compounds credibility over time.

## What this is not

- Not a SaaS product, not a subscription business, not a framework demo.
- Not a trading tool sold to others.
- It is a **live practice environment** that happens to be public: the site proves the work exists on a calendar.

## Current status (repo reality, April 2026)

- **Pipeline:** Live GitHub Actions cron (see [[docs/PIPELINE_REFERENCE]]). Validation rows are written by `validation_regime.py` when that step succeeds.
- **Site:** Legacy static `site/` build lives under `_archive/v1/site` after the v2 scaffold; root `web/` is a **Next.js 15.5.2** App Router app in progress (see [[TECH_STACK]]).
- **Deploy:** CI today still runs `npx wrangler deploy` against the **Workers + `site/` assets** pattern documented in `.github/workflows/daily_brief.yml`. Root `wrangler.toml` at repo root is **Pages-oriented** for the Next app (`pages_build_output_dir`); wiring CI to `wrangler pages deploy` for `web/` is **not** done in the workflow file inspected for this doc.

## Positioning

**Shreyash Sakhare** (20, EE undergrad Pune) runs this stack as discretionary macro practice, publishing under FX Regime Lab. **NTU MFE Singapore 2028** is the stated academic target; this repository is the working body of evidence toward that path.

## Doc map

- [[TECH_STACK]]
- [[FRONTEND_ARCHITECTURE]]
- [[DESIGN_SYSTEM]]
- [[DATABASE_SCHEMA]]
- [[PIPELINE_REFERENCE]]
- [[SIGNAL_DEFINITIONS]]
- [[CURSOR_RULES]]
- [[PHASES]]
- [[FEATURE_REGISTRY]]
- [[_index]]
