-- FX Regime Lab V3 — Lightweight page view analytics
-- Privacy-preserving: no PII, hashed user agents

CREATE TABLE IF NOT EXISTS page_views (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_path       TEXT NOT NULL,
  referrer        TEXT,
  user_agent_hash TEXT,
  session_id      TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_page_views_path_date
  ON page_views (page_path, created_at);

ALTER TABLE page_views ENABLE ROW LEVEL SECURITY;

-- Service role only — no anon access
