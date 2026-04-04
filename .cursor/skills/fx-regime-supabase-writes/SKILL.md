---
name: fx-regime-supabase-writes
description: >-
  Enforces FX Regime Lab Supabase write patterns—upsert on (date,pair), CSV
  fallback, batched rows, module-level client from env, explicit select columns,
  and pipeline_errors logging. Use when adding or editing Python that writes or
  reads Supabase, daily signal tables, or pipeline persistence in this repo.
---

# FX Regime Lab — Supabase writes and reads

## When this applies

Any Python that **persists** daily or time-series FX signals, regime rows, or similar tables in this project. Follow these rules even when copying patterns from generic Supabase tutorials.

## Client

- **Lazy init** at module level: set `supabase: Optional[Client]` to `None` if URL or key missing.
- **Never raise on import** (no `EnvironmentError` at import time). Log warning; skip remote writes; pipeline stays non-blocking.
- **CI / writes:** use `SUPABASE_SERVICE_ROLE_KEY` (or fallback to anon only if project explicitly allows). **Never** put service role in browser or Cloudflare public env.
- Reuse the same client instance after creation.

```python
import logging
import os
from typing import Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase: Optional[Client] = None
if SUPABASE_URL and _key:
    supabase = create_client(SUPABASE_URL, _key)
else:
    logger.warning("Supabase not configured — skipping remote writes")
```

## Time-series / daily signal tables

- Use **upsert** only—never plain `insert` for rows governed by `(date, pair)`.
- Pass **`on_conflict="date,pair"`** on upsert so conflicts update the existing row.
- If a table uses a different unique key (rare), stop and align with schema—do not assume `(date, pair)` without checking.

## Reads

- Never use **`select("*")`**. Always list explicit columns in `.select("col1,col2,...")`.

## Batching

- When multiple rows are ready in memory, **one upsert with a list of dicts** is preferred over one call per row.
- Keep batches reasonably sized if the API or payload limits apply (chunk if needed).

## CSV fallback

- **Every** Supabase write path for transitional daily data should also write the same logical row(s) to the existing **CSV under `data/`** pattern used in the pipeline (append with `header=False` when the file exists).
- Supabase is primary; CSV is for local dev and continuity—do not write-only to CSV without attempting Supabase first (per project rules).

## Errors: try/except and `pipeline_errors`

- Wrap **Supabase** (and ideally external **API fetch**) calls in `try/except`.
- On failure, **log to the `pipeline_errors` table** so ops can query failures; do not let one write kill the whole pipeline unless the script explicitly requires it.
- Include useful context: at minimum align with project intent—**date** (or run date), **source** (e.g. table name or script/step), **error message** (stringified exception), **timestamp** (UTC if the column expects it).

Use a small helper reused across modules if one already exists; otherwise implement a local `log_pipeline_error(source: str, message: str, ...)` that upserts/inserts into `pipeline_errors` per schema.

## Minimal write pattern (checklist)

1. Build `rows: list[dict]` with `date`, `pair`, and metric columns.
2. `try`: `supabase.table("<table>").upsert(rows, on_conflict="date,pair").execute()` if client is non-null.
3. `except`: log to `pipeline_errors`; optionally log to stderr/logger without printing secrets.
4. Write the same rows to CSV fallback.
5. For reads: `.select("date,pair,col_a,col_b")` with filters as needed.

## Conflicts with other instructions

If workspace rules or `AGENTS.md` / `CURSOR_RULES.md` disagree, **workspace and project docs win**. This skill summarizes the Supabase slice of those rules.
