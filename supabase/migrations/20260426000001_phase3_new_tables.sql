-- Phase 3: new tables (brief, macro_events, ai_usage_log)
-- regime_calls / signals / validation_log already exist from prior schema

CREATE TABLE IF NOT EXISTS brief (
  id             UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  date           DATE  NOT NULL,
  pair           TEXT  NOT NULL,
  regime         TEXT  NOT NULL,
  confidence     FLOAT NOT NULL,
  composite      FLOAT NOT NULL,
  analysis       TEXT  NOT NULL,
  primary_driver TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS macro_events (
  id         UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE    NOT NULL,
  event      TEXT    NOT NULL,
  impact     TEXT    NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW')),
  pairs      TEXT[]  NOT NULL DEFAULT '{}',
  category   TEXT,
  ai_brief   TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (date, event)
);

CREATE TABLE IF NOT EXISTS ai_usage_log (
  id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  date          DATE    NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 1,
  purpose       TEXT,
  model         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE brief          ENABLE ROW LEVEL SECURITY;
ALTER TABLE macro_events   ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_log   ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_brief"        ON brief        FOR SELECT TO anon USING (true);
CREATE POLICY "anon_read_macro_events" ON macro_events FOR SELECT TO anon USING (true);
-- ai_usage_log: no anon access (service role only)

-- Indexes
CREATE INDEX IF NOT EXISTS idx_brief_pair_date       ON brief        (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_events_date     ON macro_events (date, impact);
