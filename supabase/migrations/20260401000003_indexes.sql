-- Migration: indexes (Phase 3)

CREATE INDEX IF NOT EXISTS idx_regime_calls_pair_date ON regime_calls  (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_pair_date      ON signals        (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_validation_pair_date   ON validation_log (pair, date DESC);
CREATE INDEX IF NOT EXISTS idx_macro_events_date      ON macro_events   (date, impact);
CREATE INDEX IF NOT EXISTS idx_brief_pair_date        ON brief          (pair, date DESC);
