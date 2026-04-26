-- Migration: initial_schema (Phase 3)

CREATE TABLE IF NOT EXISTS regime_calls (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  pair             TEXT        NOT NULL,
  date             DATE        NOT NULL,
  regime           TEXT        NOT NULL,
  confidence       FLOAT       NOT NULL,
  signal_composite FLOAT       NOT NULL,
  rate_signal      TEXT        NOT NULL,
  primary_driver   TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS signals (
  id               UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  pair             TEXT  NOT NULL,
  date             DATE  NOT NULL,
  rate_diff_2y     FLOAT,
  cot_percentile   FLOAT,
  realized_vol_20d FLOAT,
  realized_vol_5d  FLOAT,
  implied_vol_30d  FLOAT,
  spot             FLOAT,
  day_change       FLOAT,
  day_change_pct   FLOAT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS validation_log (
  id         UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE  NOT NULL,
  pair       TEXT  NOT NULL,
  call       TEXT  NOT NULL,
  outcome    TEXT  NOT NULL CHECK (outcome IN ('correct', 'incorrect')),
  return_pct FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

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
