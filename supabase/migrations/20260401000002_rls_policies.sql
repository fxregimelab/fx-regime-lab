-- Migration: RLS policies (Phase 3)

ALTER TABLE regime_calls   ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals         ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE brief           ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_log    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_regime_calls" ON regime_calls  FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_signals"      ON signals        FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_validation"   ON validation_log FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_brief"        ON brief          FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_macro_events" ON macro_events   FOR SELECT TO anon USING (true);
