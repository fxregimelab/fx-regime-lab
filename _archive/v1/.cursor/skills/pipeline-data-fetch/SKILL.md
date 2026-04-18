---
name: pipeline-data-fetch
description: >-
  Standardizes external data fetching for the FX Regime Lab pipeline: FRED API,
  CME CVOL API, CME open-interest scrape, CFTC COT download, and yfinance. Use
  when building, refactoring, or debugging any function that pulls remote market
  data into this repo.
---

# Pipeline data fetch (external sources)

## Role

Own the **fetch layer** only: HTTP/API/download calls and thin parsing. Downstream code normalizes rows for Supabase/CSV; this skill defines **return shape**, **status semantics**, **errors**, and **rate limits**.

## Scope

- FRED API
- CME CVOL API
- CME open-interest scrape (HTML/JSON as implemented)
- CFTC COT file download
- `yfinance` equity/FX pulls

Stay within approved project libraries (`requests`, `yfinance`, etc.); do not add dependencies without explicit approval.

## Standard return value

Every fetch helper returns a **single standardized dict** (one logical observation), not a bare scalar:

```python
{
    "value": ...,       # last good numeric or serializable value; None if unavailable
    "date": ...,        # observation date (date, datetime, or ISO str—match caller contract)
    "source": str,      # short id, e.g. "fred:DGS10", "cme:cvol:6E", "cot:EUR", "yfinance:EURUSD=X"
    "status": str,      # "OK" | "STALE" | "FAILED"
}
```

- **OK** — Data for the **target** business/observation date (or latest available when the source legitimately publishes with a known lag, document in the docstring).
- **STALE** — Deliberately using a **previous** observation: e.g. today’s fetch failed and a **cached or last-known** value from the prior day is returned, or the API only returned data through T-1 and the pipeline accepts that as the working value for “today.”
- **FAILED** — No usable value after fallback (e.g. no cache and network/parse error). `value` should be `None`; still **do not raise** out of the fetch helper.

## On failure

1. Wrap every external call in `try`/`except`.
2. **Log to Supabase `pipeline_errors`** (date/run context, `source`, error message, timestamp). Reuse the project’s shared helper if it exists; otherwise follow [.cursor/skills/fx-regime-supabase-writes/SKILL.md](../fx-regime-supabase-writes/SKILL.md).
3. **Return previous-day (last-known) value** when available and set **`status` to `STALE`**.
4. If nothing is available, return **`value: None`**, **`status: "FAILED"`**, with the best-known **`date`** (e.g. target date or last attempted).
5. **Never raise** from the public fetch entrypoint—the pipeline continues; callers aggregate STALE/FAILED for the brief.

Do not log API keys, OAuth tokens, or secrets.

## Rate limits and pacing

| Source   | Rule |
|----------|------|
| **FRED** | Assume **120 requests/minute** budget; batch series where possible, avoid tight loops of one-series-per-request without throttling or consolidation. |
| **CME**  | Respect **OAuth/API** quota documented for the product in use; backoff on 429; avoid parallel bursts that exceed the app’s registered limits. |
| **yfinance** | **≥ 1 second delay** between sequential calls (sleep or shared rate limiter) to reduce throttling and ban risk. |
| **CFTC** | Large file downloads: single connection per run where possible; handle timeouts with retry/backoff inside `try`/`except`, still ending in the standard dict (not raise). |

## Implementation checklist

- [ ] Public function returns the four-key dict above.
- [ ] `source` is stable and grep-friendly for ops.
- [ ] Exceptions caught; `pipeline_errors` row on failure path.
- [ ] Rate limiting / delay applied per table above.
- [ ] Docstring states: target date semantics, what `value` means, and when `STALE` vs `OK` is set.

## Conflicts

If this skill disagrees with `CURSOR_RULES.md`, `AGENTS.md`, or workspace rules, **project docs win**.
