CREATE TABLE IF NOT EXISTS strategy_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    pair TEXT NOT NULL,
    regime TEXT NOT NULL,
    primary_driver TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_close DOUBLE PRECISION,
    confidence DOUBLE PRECISION,
    t1_close DOUBLE PRECISION,
    t3_close DOUBLE PRECISION,
    t5_close DOUBLE PRECISION,
    t1_hit INT,
    t3_hit INT,
    t5_hit INT,
    brier_score_t5 DOUBLE PRECISION,
    UNIQUE (date, pair, regime, primary_driver)
);

ALTER TABLE strategy_ledger ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anonymous read access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Allow anonymous read access on strategy_ledger"
    ON strategy_ledger FOR SELECT
    TO anon
    USING (true);

DROP POLICY IF EXISTS "Deny anonymous insert access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous insert access on strategy_ledger"
    ON strategy_ledger FOR INSERT
    TO anon
    WITH CHECK (false);

DROP POLICY IF EXISTS "Deny anonymous update access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous update access on strategy_ledger"
    ON strategy_ledger FOR UPDATE
    TO anon
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS "Deny anonymous delete access on strategy_ledger" ON strategy_ledger;
CREATE POLICY "Deny anonymous delete access on strategy_ledger"
    ON strategy_ledger FOR DELETE
    TO anon
    USING (false);

CREATE INDEX IF NOT EXISTS strategy_ledger_date_idx ON strategy_ledger (date);
CREATE INDEX IF NOT EXISTS strategy_ledger_pair_idx ON strategy_ledger (pair);
