# Implementation Spec: [MIGRATION_NAME] Database Migration

## Context
Schema change for Supabase PostgreSQL.

## Files
- CREATE: `supabase/migrations/YYYYMMDDHHMMSS_[name].sql`
- MODIFY: `sql/schema.sql` (regenerate after migration)
- MODIFY: `web/src/lib/supabase/database.types.ts` (if schema changed)

## Technical Requirements
- Timestamp filename: `date +%Y%m%d%H%M%S`
- Idempotent SQL: `IF NOT EXISTS`, `DROP IF EXISTS`
- Never drop columns/tables with live data without migration plan
- Explicit column lists on selects — never `select("*")`
- RLS policies for public tables: anon SELECT allowed
- `pipeline_errors`: NO anon SELECT

## Acceptance Criteria
- [ ] Migration is idempotent
- [ ] `supabase db reset` applies cleanly
- [ ] `sql/schema.sql` regenerated from live schema
- [ ] Types updated if schema changed
- [ ] No breaking changes to existing queries

## Execution Plan
1. Write migration SQL
2. Test locally: `supabase db reset`
3. Regenerate schema: `pg_dump --schema-only` or equivalent
4. Update types: `supabase gen types typescript`
5. Verify existing queries still work
