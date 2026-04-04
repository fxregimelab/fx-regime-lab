---
name: fx-regime-signal-pipeline
description: >-
  Scaffolds a new FX Regime Lab signal module as `[signal]_pipeline.py` with
  fetch → compute → write_to_supabase → return dict, 260-day percentile,
  direction and regime fields, Supabase upsert, and run.py / CI ordering. Use
  when adding a new daily signal pipeline, extending the quant pipeline, or
  when the user mentions signal modules, Supabase signal writes, or pipeline
  steps after `pipeline.py`.
---

# FX Regime Lab — new signal pipeline module

## When this applies

Use this skill only for **new** signal ETL modules in this repo. Before building, confirm the signal passes **institutional validity, independence, data availability, regime relevance** (see project `CURSOR_RULES.md`). Do not duplicate an existing pipeline script.

## Deliverable shape

- **File name**: `{signal_name}_pipeline.py` (snake_case signal, e.g. `vol`, `rr`, `oi` → `vol_pipeline.py`).
- **Stack**: Python only; approved deps only (`pandas`, `numpy`, `requests`, `supabase-py`, `yfinance`, `scipy`, etc.). No new `pip` packages without explicit user approval.
- **Persistence**: Supabase first (upsert), CSV fallback second for local dev — never write-only to CSV.

## Required module structure

Implement the data path in this order (names may vary slightly but the flow must match):

1. **`fetch(...)`** — Pull from API/files; return DataFrames / series / raw payloads. Wrap **every** external call in `try/except`; log failures; prefer returning empty structures over crashing the process.
2. **`compute(...)`** — Derive the signal: raw level, **260-trading-day rolling percentile** (see below), **direction**, **regime classification**, plus any columns needed for Supabase/merge.
3. **`write_to_supabase(...)`** — Upsert daily rows. Use **`on_conflict='date,pair'`** (or the table’s documented conflict target). Never plain insert for daily signal tables.
4. **Return `signal_dict`** — A single dict (or small set of dicts) summarizing the latest observation for downstream scripts / briefs.

Expose a **`main()`** or script entry pattern consistent with sibling pipelines (`if __name__ == "__main__":` calling the chain).

## Percentile (260-day window)

- Use a **260-trading-day** rolling window (52 weeks), consistent with `CURSOR_RULES.md`.
- Compute percentile rank of the **current** value within the trailing window; **clip** to **[0, 100]** (e.g. `numpy.clip` or min/max guards after rounding).
- If fewer than 260 usable observations exist, use `min(len(series), 260)` for the window (same idea as existing `compute_percentile` in rules) and document behavior when history is short.

## `signal_dict` contents (latest bar)

Each new module should return a dict (per pair or top-level — match how `morning_brief.py` / merge expects to consume it) that includes at minimum:

| Key (concept) | Requirement |
|----------------|-------------|
| Raw value | Latest level of the signal (float or nullable) |
| Percentile | 260-day percentile, clipped to [0, 100] |
| Direction | One of `'BULLISH'`, `'BEARISH'`, `'NEUTRAL'` — define **thresholds on percentile or level** in the module docstring |
| Regime classification | String label consistent with the framework’s regime taxonomy (see `PLAN.md` / brief language); document mapping in the docstring |

Add other fields (z-scores, deltas, flags) only if needed for Supabase or downstream charts.

## Module docstring (required)

The **top-of-file or module docstring** must document:

- **Inputs**: data sources, env vars/secrets, lookback, pairs covered.
- **Outputs**: CSV paths (if any), Supabase table(s), shape of `signal_dict`.
- **Failure modes**: API timeout/empty response, partial history, NaNs, Supabase errors, and behavior (e.g. skip write, carry forward, flag gap — align with project rule: one failed source must not kill the entire pipeline).

Per-project rule: every function should still have a short docstring for what it computes, returns, and writes.

## Orchestration and CI

- **Canonical runner**: `run.py` defines `STEPS` as ordered `(name, script_file)` pairs. Insert the new step **after** data it depends on exists (typically after `inr` / merge for price-based signals) and **before** `text` (`morning_brief.py`) so the brief sees fresh columns. There is **no** `create_dashboards.py` in this repo.
- **Repo reality**: Charts for the daily brief come from `create_html_brief.py` / `create_charts_plotly.py`; the live product dashboard is **Cloudflare Pages** (fxregimelab.com), not a Python `create_dashboards` step.
- **GitHub Actions**: `.github/workflows/daily_brief.yml` runs `python run.py` (with retry). You normally **do not** add a separate workflow step per script unless the project explicitly moves to discrete steps; updating `run.py` is sufficient for CI order.

Do **not** change global cron or remove secrets handling without explicit instruction.

## Checklist before finishing

- [ ] `{signal}_pipeline.py` follows fetch → compute → write_to_supabase → return dict.
- [ ] Percentile uses 260-day window and [0, 100] clip.
- [ ] `signal_dict` includes raw, percentile, direction, regime.
- [ ] Supabase upsert with correct `on_conflict`; no plain insert for daily tables.
- [ ] Module docstring covers inputs, outputs, failure modes; functions documented.
- [ ] `run.py` `STEPS` order updated; workflow impact understood (`run.py` only unless told otherwise).
