# Supabase Read Policy Setup (Manual)

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
