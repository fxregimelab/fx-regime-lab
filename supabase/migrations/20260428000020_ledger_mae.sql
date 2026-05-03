-- Maximum adverse excursion (BPS) over T+1..T+5 forward window for strategy_ledger rows.
ALTER TABLE strategy_ledger
    ADD COLUMN IF NOT EXISTS max_pain_bps DOUBLE PRECISION;
