---
name: fx-regime-supabase-writes
description: >-
  Enforces FX Regime Lab Supabase write patterns. Use when adding or editing
  Python that writes or reads Supabase, daily signal tables, or pipeline persistence.
---

# FX Regime Lab — Supabase Writes and Reads

## Client

- All writes go through `pipeline/src/db/writer.py`. Do NOT create ad-hoc clients.
- For reads in pipeline: use `src/db/writer.py` read helpers or lazy-init client.
- **Never raise on import**. Skip remote writes if env vars missing.
- **CI / writes**: use `SUPABASE_SERVICE_ROLE_KEY`.
- **Never** put service role in browser or Cloudflare public env.

## Time-series / daily signal tables

- Use **upsert** only. Pass `on_conflict="date,pair"`.
- Never plain `insert` for rows governed by `(date, pair)`.

## Reads

- Never `select("*")`. Always explicit columns: `.select("date,pair,col_a,col_b")`.

## Batching

- One upsert with a list of dicts preferred over one call per row.
- Chunk if payload limits apply.

## CSV fallback

- Every Supabase write path should also write same rows to `data/*.csv`.
- Supabase is primary; CSV is for local dev.

## Errors: try/except and `pipeline_errors`

- Wrap Supabase and external API calls in `try/except`.
- On failure, log to `pipeline_errors` table.
- Include: date, source (table/script), error message, timestamp.

## Minimal write pattern

1. Build `rows: list[dict]` with `date`, `pair`, metric columns.
2. `try`: write via `src/db/writer.py` upsert helper.
3. `except`: log to `pipeline_errors`.
4. Write same rows to CSV fallback.
5. Reads: explicit column lists with filters.
