# FX Regime Lab — project overview

FX Regime Lab is a **personal, public research system** for daily G10 FX regime work: it ingests macro and positioning data, scores EUR/USD, USD/JPY, and USD/INR on a consistent composite, persists calls and signals to Supabase, generates a daily brief, and surfaces the same truth on a website so every call sits on the record.

## Two layers (conceptual)

- **Research ledger (private, immutable intent):** The durable record of *why* a view existed (hypotheses, rationale, drafts, private notes). In this repo today, that layer is **not** fully modeled in Postgres: there is **no** `call_rationale` or `hypothesis_log` table in the checked-in [[DATABASE_SCHEMA]]. Treat disk artifacts under `runs/`, `briefs/`, and archived `_archive/v1/docs/` as historical research context until those tables ship.
- **Performance record (public, auto-generated):** What the pipeline persists: `signals`, `regime_calls`, `validation_log`, `brief`, `macro_events`, and optional JSON under `site/data/` when writers use that path. There is **no** shipped website in this repo; see [[DATA_READS_SPEC]] for the former Next.js read surface and [[HOSTING_AFTER_UI_REMOVAL]] for ops notes.

## strategy_id

The **product vision** is multiple strategies under one domain. **Reality in Postgres (as of `sql/schema.sql` in this repo):** there is **no** `strategy_id` column on `signals`, `regime_calls`, `validation_log`, or `brief_log`. Until migrations add `strategy_id`, document FX Regime Lab as **strategy 1 of N conceptually**, not in schema.

## North star

Build a **15-year research operating system** for a discretionary macro PM career: daily discipline, measurable calls, honest validation, and a public trace that compounds credibility over time.

## What this is not

- Not a SaaS product, not a subscription business, not a framework demo.
- Not a trading tool sold to others.
- It is a **live practice environment** that happens to be public: data in Supabase (and future site) proves the work exists on a calendar.

## Current status (repo reality, April 2026)

- **Pipeline:** Live GitHub Actions cron (see [[docs/PIPELINE_REFERENCE]]). Validation rows are written by `validation_regime.py` when that step succeeds.
- **Site / UI:** No production frontend in-repo. UX reference: `claude-design/`. Worker: API-only [`workers/site-entry.js`](../workers/site-entry.js). See [[HOSTING_AFTER_UI_REMOVAL]].
- **Deploy:** GitHub Actions run the Python pipeline only (see `.github/workflows/pipeline_*.yml`). Cloudflare Pages / root `wrangler.toml` for the old Next app are removed.

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
