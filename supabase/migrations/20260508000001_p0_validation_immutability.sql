-- P0-T1 + P0-T2 Combined Migration
-- Validation Engine Schema + Immutable Ledger Enforcement
--
-- NOTE: This migration must be applied via Supabase dashboard or CLI
--       (`supabase db push`) before the updated Python code runs against
--       the new columns.

-- ───────────────────────────────────────────────────────────────────────────
-- 1. Validation_log: add T+5/T+20 horizon columns (if not already present)
-- ───────────────────────────────────────────────────────────────────────────

-- Columns from the pending 20260505000001_round3_validation_engine migration
ALTER TABLE public.validation_log
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

-- P0-T1: additional T+20 columns using decimal-fraction convention
-- (log_return_t20_bps is the canonical bps field; actual_return_20d
--  exists for parity with the legacy actual_return_5d column.)
ALTER TABLE public.validation_log
    ADD COLUMN IF NOT EXISTS actual_return_20d FLOAT,
    ADD COLUMN IF NOT EXISTS correct_20d BOOLEAN,
    ADD COLUMN IF NOT EXISTS brier_20d FLOAT;

-- P0-T1: ensure T+5 Brier column exists (legacy tables lack it)
ALTER TABLE public.validation_log
    ADD COLUMN IF NOT EXISTS brier_5d FLOAT;

-- Drop old unique indexes that may have non-partial definitions from earlier
-- migrations; recreate them as partial unique indexes for the versioning model.
DROP INDEX IF EXISTS idx_validation_unique;
DROP INDEX IF EXISTS idx_validation_call_id;
DROP INDEX IF EXISTS idx_validation_call_pair;

-- Unique index on call_id for current versions only
-- (Superseded historical versions are allowed to coexist.)
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_id
    ON public.validation_log (call_id)
    WHERE call_id IS NOT NULL AND is_superseded = false;

-- Unique index on (call_date, pair) for current versions only
-- (Legacy rows have call_date = NULL; Postgres NULLs do not conflict.)
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_pair
    ON public.validation_log (call_date, pair)
    WHERE call_date IS NOT NULL AND is_superseded = false;

-- Non-unique index on (date, pair) for legacy queries
CREATE INDEX IF NOT EXISTS idx_validation_date_pair
    ON public.validation_log (date, pair);

-- Index for superseded lookups
CREATE INDEX IF NOT EXISTS idx_validation_superseded
    ON public.validation_log (is_superseded)
    WHERE is_superseded = true;

-- ───────────────────────────────────────────────────────────────────────────
-- 2. FK type alignment (live DB already has integer on both sides;
--    this section is idempotent and documents the relationship.)
-- ───────────────────────────────────────────────────────────────────────────

-- The live database currently has:
--   regime_calls.id         -> integer (serial)
--   validation_log.call_id  -> integer (nullable)
--
-- If a future migration ever changes regime_calls.id to UUID, this
-- statement will raise an error and must be updated first.
DO $$
BEGIN
    -- Only add FK if call_id column exists and FK does not already exist
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'validation_log' AND column_name = 'call_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'validation_log'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'fk_validation_log_call_id'
    ) THEN
        ALTER TABLE public.validation_log
            ADD CONSTRAINT fk_validation_log_call_id
            FOREIGN KEY (call_id) REFERENCES public.regime_calls(id)
            ON DELETE RESTRICT;
    END IF;
END $$;

-- ───────────────────────────────────────────────────────────────────────────
-- 3. audit_log table (P0-T2)
-- ───────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.audit_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation      TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    table_name     TEXT NOT NULL,
    row_id         UUID,
    old_value      JSONB,
    new_value      JSONB,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    correlation_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_table_op
    ON public.audit_log (table_name, operation, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_row_id
    ON public.audit_log (row_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_correlation
    ON public.audit_log (correlation_id)
    WHERE correlation_id IS NOT NULL;

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Internal ops only — no anon read policy
DROP POLICY IF EXISTS "anon_read_audit_log" ON public.audit_log;

-- ───────────────────────────────────────────────────────────────────────────
-- 4. Immutable trigger on regime_calls (P0-T2)
-- ───────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.protect_immutable_calls()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Regime calls are immutable once written to the ledger. Update attempted on % (pair=%, date=%).',
            OLD.id, OLD.pair, OLD.date;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Regime calls are immutable once written to the ledger. Delete attempted on % (pair=%, date=%).',
            OLD.id, OLD.pair, OLD.date;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger (was previously defined but NOT attached)
DROP TRIGGER IF EXISTS trg_protect_immutable_calls ON public.regime_calls;
CREATE TRIGGER trg_protect_immutable_calls
    BEFORE UPDATE OR DELETE ON public.regime_calls
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_immutable_calls();

-- ───────────────────────────────────────────────────────────────────────────
-- 5. Immutable trigger on validation_log (P0-T2)
-- ───────────────────────────────────────────────────────────────────────────
-- Blocks all UPDATE and DELETE on validation_log. The only permitted
-- mutation is setting is_superseded = true, which is required for the
-- append-only versioning model. All other changes must create a new row.

CREATE OR REPLACE FUNCTION public.protect_immutable_validation()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Allow the single versioning operation: marking an old row superseded.
        -- All other columns must remain unchanged.
        IF NEW.is_superseded = true
           AND OLD.is_superseded IS DISTINCT FROM NEW.is_superseded
           AND OLD.id IS NOT DISTINCT FROM NEW.id
           AND OLD.date IS NOT DISTINCT FROM NEW.date
           AND OLD.pair IS NOT DISTINCT FROM NEW.pair
           AND OLD.call IS NOT DISTINCT FROM NEW.call
           AND OLD.outcome IS NOT DISTINCT FROM NEW.outcome
           AND OLD.return_pct IS NOT DISTINCT FROM NEW.return_pct
           AND OLD.created_at IS NOT DISTINCT FROM NEW.created_at
           AND OLD.call_id IS NOT DISTINCT FROM NEW.call_id
           AND OLD.validation_date IS NOT DISTINCT FROM NEW.validation_date
           AND OLD.is_correct IS NOT DISTINCT FROM NEW.is_correct
           AND OLD.pnl_bps IS NOT DISTINCT FROM NEW.pnl_bps
           AND OLD.actual_direction_t5 IS NOT DISTINCT FROM NEW.actual_direction_t5
           AND OLD.actual_direction_t20 IS NOT DISTINCT FROM NEW.actual_direction_t20
           AND OLD.log_return_t5_bps IS NOT DISTINCT FROM NEW.log_return_t5_bps
           AND OLD.log_return_t20_bps IS NOT DISTINCT FROM NEW.log_return_t20_bps
           AND OLD.correct_t5 IS NOT DISTINCT FROM NEW.correct_t5
           AND OLD.correct_t20 IS NOT DISTINCT FROM NEW.correct_t20
           AND OLD.brier_score_t5 IS NOT DISTINCT FROM NEW.brier_score_t5
           AND OLD.brier_score_t20 IS NOT DISTINCT FROM NEW.brier_score_t20
           AND OLD.actual_return_5d IS NOT DISTINCT FROM NEW.actual_return_5d
           AND OLD.actual_return_20d IS NOT DISTINCT FROM NEW.actual_return_20d
           AND OLD.correct_5d IS NOT DISTINCT FROM NEW.correct_5d
           AND OLD.correct_20d IS NOT DISTINCT FROM NEW.correct_20d
           AND OLD.brier_5d IS NOT DISTINCT FROM NEW.brier_5d
           AND OLD.brier_20d IS NOT DISTINCT FROM NEW.brier_20d
           AND OLD.predicted_direction IS NOT DISTINCT FROM NEW.predicted_direction
           AND OLD.predicted_regime IS NOT DISTINCT FROM NEW.predicted_regime
           AND OLD.confidence IS NOT DISTINCT FROM NEW.confidence
           AND OLD.call_date IS NOT DISTINCT FROM NEW.call_date
           AND OLD.strategy_version IS NOT DISTINCT FROM NEW.strategy_version
           AND OLD.data_source IS NOT DISTINCT FROM NEW.data_source
        THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION 'Validation_log is immutable. Update attempted on row id=% (pair=%, date=%).',
            OLD.id, OLD.pair, OLD.date;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Validation_log is immutable. Delete attempted on row id=% (pair=%, date=%).',
            OLD.id, OLD.pair, OLD.date;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_protect_immutable_validation ON public.validation_log;
CREATE TRIGGER trg_protect_immutable_validation
    BEFORE UPDATE OR DELETE ON public.validation_log
    FOR EACH ROW
    EXECUTE FUNCTION public.protect_immutable_validation();

-- ───────────────────────────────────────────────────────────────────────────
-- 6. audit_log trigger on regime_calls (P0-T2)
-- ───────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.log_regime_call_audit()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.audit_log (operation, table_name, row_id, new_value, correlation_id)
    VALUES (
        TG_OP,
        TG_TABLE_NAME,
        NEW.id,
        to_jsonb(NEW),
        NULL
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_regime_call_audit ON public.regime_calls;
CREATE TRIGGER trg_log_regime_call_audit
    AFTER INSERT ON public.regime_calls
    FOR EACH ROW
    EXECUTE FUNCTION public.log_regime_call_audit();
