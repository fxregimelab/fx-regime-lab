# Supabase Read Policy Setup (Manual)

**Related:** Pipeline dual-write and error logging context — [PIPELINE_AUDIT_AND_OPERATIONS.md](./PIPELINE_AUDIT_AND_OPERATIONS.md).

This project expects browser-side read access (anon key) for:

- `signals`
- `regime_calls`
- `validation_log`
- `paper_positions`
- `brief_log`
- `pipeline_errors` (optional; terminal `checkPipelineErrors` skips quietly if RLS blocks anon)

Run the following SQL manually in the Supabase SQL Editor, **or** run the same query from Cursor using the **Supabase MCP** (`plugin-supabase-supabase`): `list_projects` to resolve `project_id`, then `execute_sql` with the query below. Use `apply_migration` from that MCP for new DDL migrations; ad-hoc checks use `execute_sql`.

## 1) Verify existing policies

```sql
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE tablename IN (
  'signals', 'regime_calls', 'validation_log',
  'paper_positions', 'brief_log', 'pipeline_errors'
);
```

## 2) Add missing anon SELECT policies

```sql
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_signals"
  ON signals FOR SELECT
  TO anon
  USING (true);

ALTER TABLE regime_calls ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_regime_calls"
  ON regime_calls FOR SELECT
  TO anon
  USING (true);

ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_validation_log"
  ON validation_log FOR SELECT
  TO anon
  USING (true);

ALTER TABLE paper_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_paper_positions"
  ON paper_positions FOR SELECT
  TO anon
  USING (true);

ALTER TABLE brief_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_brief_log"
  ON brief_log FOR SELECT
  TO anon
  USING (true);

ALTER TABLE pipeline_errors ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_pipeline_errors"
  ON pipeline_errors FOR SELECT
  TO anon
  USING (true);
```

If a policy already exists, skip that `CREATE POLICY` statement or replace it with an `ALTER POLICY` workflow.

## 3) `signals` table — columns expected by Python upserts

PostgREST returns **PGRST204** if the client sends a key that is not a column on `signals`. The pipeline builds rows in [`core/signal_write.py`](../core/signal_write.py) (`_row_to_signal`) and Layer 3 modules write additional fields.

**Unique constraint:** upserts use `on_conflict="date,pair"`. Ensure a **unique index** on `(date, pair)` (e.g. `idx_signals_unique`).

**Idempotent DDL** (add any column your project is missing):

- See [`signals_table_migration.sql`](signals_table_migration.sql) in this folder.

**Column checklist** (mirror of code — add with appropriate types if missing):

| Column | Typical type | Source |
|--------|----------------|--------|
| `date` | `date` | all rows |
| `pair` | `varchar` | all rows |
| `spot` | `double precision` | `_row_to_signal` |
| `rate_diff_2y`, `rate_diff_10y`, `rate_diff_zscore` | `double precision` | `_row_to_signal` |
| `cot_lev_money_net`, `cot_asset_mgr_net` | `bigint` | `_row_to_signal` |
| `cot_percentile` | `double precision` | `_row_to_signal` |
| `realized_vol_20d`, `realized_vol_5d` | `double precision` | `_row_to_signal` |
| `cross_asset_dxy`, `cross_asset_oil`, `cross_asset_vix` | `double precision` | `_row_to_signal` |
| `implied_vol_30d`, `vol_skew`, `atm_vol` | `double precision` | `vol_pipeline` / master |
| `oi_delta` | `integer` or `double precision` | `oi_pipeline` |
| `oi_price_alignment` | `text` / `varchar` | `oi_pipeline` |
| `risk_reversal_25d` | `double precision` | `rr_pipeline` |

After DDL changes, reload the API schema if needed (Supabase **Settings → API**), then run [`scripts/backfill_supabase.py`](../scripts/backfill_supabase.py) from the repo root.
