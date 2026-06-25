-- Round 3: Validation Engine schema evolution
-- Adds T+20 log-return metrics, Brier scores, and call_date anchor.

-- 1. Add call_date to validation_log (nullable for legacy rows)
ALTER TABLE validation_log
    ADD COLUMN IF NOT EXISTS call_date DATE,
    ADD COLUMN IF NOT EXISTS actual_direction_t5 VARCHAR(10),
    ADD COLUMN IF NOT EXISTS actual_direction_t20 VARCHAR(10),
    ADD COLUMN IF NOT EXISTS log_return_t5_bps FLOAT,
    ADD COLUMN IF NOT EXISTS log_return_t20_bps FLOAT,
    ADD COLUMN IF NOT EXISTS correct_t5 BOOLEAN,
    ADD COLUMN IF NOT EXISTS correct_t20 BOOLEAN,
    ADD COLUMN IF NOT EXISTS brier_score_t5 FLOAT,
    ADD COLUMN IF NOT EXISTS brier_score_t20 FLOAT,
    ADD COLUMN IF NOT EXISTS is_superseded BOOLEAN DEFAULT false;

-- 2. Drop old unique index (it conflicts with new semantics where date = call_date)
DROP INDEX IF EXISTS idx_validation_unique;

-- 3. Create partial unique index on (call_date, pair) for current versions only
-- Legacy rows have call_date = NULL; Postgres NULLs do not conflict in unique indexes.
-- Superseded historical versions are allowed to coexist.
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_pair
    ON validation_log (call_date, pair)
    WHERE call_date IS NOT NULL AND is_superseded = false;

-- 4. Partial unique index on call_id for current versions only
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_id
    ON validation_log (call_id)
    WHERE call_id IS NOT NULL AND is_superseded = false;

-- 5. Keep non-unique index on (date, pair) for legacy queries
CREATE INDEX IF NOT EXISTS idx_validation_date_pair ON validation_log (date, pair);

-- 6. Index for superseded lookups
CREATE INDEX IF NOT EXISTS idx_validation_superseded
    ON validation_log (is_superseded)
    WHERE is_superseded = true;
