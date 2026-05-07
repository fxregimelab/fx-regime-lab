---
name: pipeline-data-fetch
description: >-
  Standardizes external data fetching for FX Regime Lab pipeline.
  Use when building, refactoring, or debugging remote market data pulls.
---

# Pipeline Data Fetch (External Sources)

## Scope

- FRED API
- CME CVOL API
- CME open-interest
- CFTC COT download
- yfinance

## Standard return value

Every fetch helper returns a **dict**:

```python
{
    "value": ...,       # last good numeric; None if unavailable
    "date": ...,        # observation date
    "source": str,      # e.g. "fred:DGS10", "yfinance:EURUSD=X"
    "status": str,      # "OK" | "STALE" | "FAILED"
}
```

- **OK** — Data for target date available.
- **STALE** — Using previous observation (cached or T-1).
- **FAILED** — No usable value after fallback. `value` is `None`.

## On failure

1. Wrap every external call in `try/except`.
2. Log to Supabase `pipeline_errors`.
3. Return previous-day value with `status: "STALE"` if available.
4. Return `value: None, status: "FAILED"` if nothing available.
5. **Never raise** from public fetch entrypoint.

## Rate limits

| Source | Rule |
|--------|------|
| FRED | 120 req/min; batch series where possible |
| CME | Respect OAuth quota; backoff on 429 |
| yfinance | ≥ 1 sec delay between sequential calls |
| CFTC | Single connection per run; handle timeouts |

## Implementation checklist

- [ ] Returns four-key dict.
- [ ] `source` is stable and grep-friendly.
- [ ] Exceptions caught; `pipeline_errors` row on failure.
- [ ] Rate limiting applied per table above.
- [ ] Docstring states target date semantics and status rules.
