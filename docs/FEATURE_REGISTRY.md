# Feature registry

**Update:** The shipped **`web/`** Next.js implementation was **removed**. The table below is **historical** for product planning; paths under `web/` no longer exist. Data-backed features remain in **Supabase** and the **pipeline**. UX intent for a rebuild lives in **`claude-design/`**. Read patterns from the old app are summarized in [[DATA_READS_SPEC]].

Status vocabulary (unchanged for planning):

- **LIVE:** Produced in data layer (pipeline / Supabase).
- **REMOVED:** Had a `web/` implementation; removed with UI teardown.
- **PLANNED:** Not implemented.

| Feature | Phase | Status | Description | Supabase table | Notes |
|---------|-------|--------|-------------|----------------|--------|
| Regime summary UI | 1 | REMOVED | Pair regime card, confidence | `regime_calls` | Rebuild from `claude-design/` |
| Validation table UI | 1 | REMOVED | Tabular validation history | `validation_log` | See DATA_READS_SPEC |
| Brief display UI | 1 | REMOVED | Latest brief text | `brief` | Pipeline writes text |
| Performance / shell pages | 1 | REMOVED | Aggregate stats | `validation_log` | |
| Terminal / charts | 1 | REMOVED | Pair desk, Lightweight Charts | `regime_calls`, `signals` | |
| DivergenceAlert | 2 | PLANNED | Banner for model vs market divergence | — | |
| API health | 0 | LIVE | Worker heartbeat | — | `workers/site-entry.js` `/api/health` |
| Yahoo proxy | 0 | LIVE | Worker Yahoo proxy routes | — | `workers/site-entry.js` |

## Related docs

- [[DATA_READS_SPEC]]
- [[DATABASE_SCHEMA]]
- [[PHASES]]
