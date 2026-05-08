# Immutability Guarantee

> **Status:** Enforced at the database level for `regime_calls` and `validation_log`.
> **Migration:** `supabase/migrations/20260508000001_p0_validation_immutability.sql`

---

## What Is Guaranteed

1. **Regime calls are append-only.**
   - `UPDATE` and `DELETE` on any row in `regime_calls` are blocked by the trigger `trg_protect_immutable_calls`.
   - Re-running the pipeline with the same `(pair, date)` is a no-op (insert-or-ignore semantics).

2. **Validation rows with T+5 data are append-only.**
   - `validation_log` rows where `brier_score_t5 IS NOT NULL` cannot have their T+5 columns overwritten or be deleted.
   - T+20 backfill is still allowed on the same row (updates to `*_t20` columns are permitted).

3. **Every regime call insert is audited.**
   - The `audit_log` table records `operation`, `table_name`, `row_id`, `new_value`, and `created_at` for every `INSERT` into `regime_calls`.

4. **Historical deletion requires explicit intent.**
   - `delete_pipeline_data_for_date()` raises `RuntimeError` unless `force=True` is passed.
   - When `force=True`, all deleted rows are first logged to `audit_log`.

---

## Schema Enforcement

### `regime_calls`

```sql
CREATE TRIGGER trg_protect_immutable_calls
    BEFORE UPDATE OR DELETE ON public.regime_calls
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_immutable_calls();
```

### `validation_log`

```sql
CREATE TRIGGER trg_protect_immutable_validation
    BEFORE UPDATE OR DELETE ON public.validation_log
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_immutable_validation();
```

### `audit_log`

```sql
CREATE TABLE IF NOT EXISTS public.audit_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation      TEXT NOT NULL,
    table_name     TEXT NOT NULL,
    row_id         UUID,
    old_value      JSONB,
    new_value      JSONB,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    correlation_id TEXT
);
```

---

## Tamper Evidence

5. **Every regime call has a deterministic hash.**
   - `write_hash` is SHA-256 of sorted JSON-serialized signal inputs at call time.
   - Changing the inputs changes the hash. Changing the hash requires regenerating the call.
   - Verify: `SELECT write_hash FROM regime_calls WHERE id = ?` and recompute from inputs.

6. **Every pipeline run is traceable.**
   - `correlation_id` links all tables (`regime_calls`, `validation_log`, `audit_log`, `pipeline_errors`) to a single pipeline execution.
   - Query: `SELECT * FROM regime_calls WHERE correlation_id = '...'`

## Python Compliance

- `pipeline/src/db/writer.py::write_regime_call()` queries for existing `(pair, date)` before inserting. It never uses `upsert` for regime calls.
- `pipeline/src/db/writer.py::write_validation_row()` strips T+5 fields from the payload if the existing row already has `log_return_t5_bps IS NOT NULL`.
- `pipeline/src/db/writer.py::delete_pipeline_data_for_date()` requires `force=True`.
- `pipeline/src/db/writer.py::compute_write_hash()` produces deterministic SHA-256 of inputs.

---

## Operational Notes

- **Applying the migration:** The triggers and `audit_log` table are defined in `20260508000001_p0_validation_immutability.sql`. Apply via `supabase db push` or the Supabase SQL Editor.
- **Rollback:** If an emergency requires disabling the triggers, run:
  ```sql
  DROP TRIGGER IF EXISTS trg_protect_immutable_calls ON regime_calls;
  DROP TRIGGER IF EXISTS trg_protect_immutable_validation ON validation_log;
  ```
  This action itself should be logged in `audit_log` (or in your operational runbook).
