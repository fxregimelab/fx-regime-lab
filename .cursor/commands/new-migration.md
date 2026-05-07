# new-migration

Add a new Supabase migration:
1. Generate timestamp: `date +%Y%m%d%H%M%S`
2. Create `supabase/migrations/<timestamp>_description.sql`
3. Write idempotent SQL (`IF NOT EXISTS`, `DROP IF EXISTS`)
4. Run `supabase db reset` locally to verify
5. Regenerate `sql/schema.sql` from live schema
6. Update `web/src/lib/supabase/database.types.ts` if schema changed

Usage: `/new-migration`
