-- Hardening: Revoke public/authenticated access to sensitive log tables
-- These should only be accessible via service_role (pipeline)

-- 1. ai_usage_log
ALTER TABLE ai_usage_log DISABLE ROW LEVEL SECURITY; -- Or keep enabled but with no policies
REVOKE ALL ON ai_usage_log FROM anon, authenticated;
GRANT ALL ON ai_usage_log TO service_role;

-- 2. pipeline_errors (if it exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'pipeline_errors') THEN
        REVOKE ALL ON pipeline_errors FROM anon, authenticated;
        GRANT ALL ON pipeline_errors TO service_role;
    END IF;
END $$;

-- 3. Ensure RLS is active and clean on public tables
ALTER TABLE brief_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_brief_log" ON brief_log;
CREATE POLICY "anon_read_brief_log" ON brief_log FOR SELECT TO anon USING (true);

-- Validation log is public for transparency
ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_validation" ON validation_log;
CREATE POLICY "anon_read_validation" ON validation_log FOR SELECT TO anon USING (true);
