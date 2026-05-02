-- Deep history and analog research infrastructure.

CREATE TABLE IF NOT EXISTS historical_prices (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date       DATE NOT NULL,
  pair       TEXT NOT NULL,
  open       DOUBLE PRECISION,
  high       DOUBLE PRECISION,
  low        DOUBLE PRECISION,
  close      DOUBLE PRECISION,
  volume     DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, date)
);

CREATE TABLE IF NOT EXISTS research_analogs (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  as_of_date            DATE NOT NULL,
  pair                  TEXT NOT NULL,
  rank                  INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 3),
  match_date            DATE NOT NULL,
  match_score           DOUBLE PRECISION NOT NULL,
  forward_30d_return    DOUBLE PRECISION,
  regime_stability      DOUBLE PRECISION,
  context_label         TEXT,
  current_trend_5d      DOUBLE PRECISION,
  matched_trend_5d      DOUBLE PRECISION,
  current_composite     DOUBLE PRECISION,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (pair, as_of_date, rank)
);

CREATE INDEX IF NOT EXISTS idx_historical_prices_pair_date
  ON historical_prices (pair, date DESC);

CREATE INDEX IF NOT EXISTS idx_research_analogs_pair_asof
  ON research_analogs (pair, as_of_date DESC);

ALTER TABLE historical_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_analogs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_read_historical_prices" ON historical_prices;
CREATE POLICY "anon_read_historical_prices"
  ON historical_prices
  FOR SELECT
  TO anon
  USING (true);

DROP POLICY IF EXISTS "anon_read_research_analogs" ON research_analogs;
CREATE POLICY "anon_read_research_analogs"
  ON research_analogs
  FOR SELECT
  TO anon
  USING (true);
