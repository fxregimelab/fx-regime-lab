-- FX Regime Lab V3 — Feature flags and site configuration

CREATE TABLE IF NOT EXISTS site_settings (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key         TEXT NOT NULL UNIQUE,
  value       TEXT NOT NULL,
  value_type  TEXT DEFAULT 'string',
  description TEXT,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE site_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_site_settings" ON site_settings;
CREATE POLICY "anon_read_site_settings"
  ON site_settings FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS "anon_deny_write_site_settings" ON site_settings;
CREATE POLICY "anon_deny_write_site_settings"
  ON site_settings FOR ALL TO anon USING (false);

-- Seed feature flags
INSERT INTO site_settings (key, value, value_type, description) VALUES
('show_pipeline_health', 'false', 'boolean', 'Display pipeline health badge in UI'),
('show_backtest_tab', 'true', 'boolean', 'Show backtested track record tab'),
('hero_variant', 'principle', 'string', 'Hero section variant: principle|stats|minimal'),
('terminal_rename_enabled', 'true', 'boolean', 'Rename Terminal to Desk in nav'),
('show_structured_brief', 'true', 'boolean', 'Show structured brief cards when data available')
ON CONFLICT (key) DO NOTHING;
