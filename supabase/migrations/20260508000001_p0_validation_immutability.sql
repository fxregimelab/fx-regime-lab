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

-- Drop old unique index that conflicts with new semantics
DROP INDEX IF EXISTS idx_validation_unique;

-- Unique index on call_id for upsert idempotency
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_id
    ON public.validation_log (call_id)
    WHERE call_id IS NOT NULL;

-- Unique index on (call_date, pair) for new rows
-- (Legacy rows have call_date = NULL; Postgres NULLs do not conflict.)
CREATE UNIQUE INDEX IF NOT EXISTS idx_validation_call_pair
    ON public.validation_log (call_date, pair)
    WHERE call_date IS NOT NULL;

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
-- Blocks UPDATE/DELETE on rows that already have T+5 validation data.
-- Rows with NULL brier_score_t5 may still be updated (T+20 backfill).

CREATE OR REPLACE FUNCTION public.protect_immutable_validation()
RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Allow updates that only fill in T+20 data on a row that already
        -- has T+5 data, but block changes to T+5 columns once set.
        IF OLD.brier_score_t5 IS NOT NULL THEN
            -- Whitelist: only allow updates to T+20 fields and is_superseded
            IF OLD.log_return_t5_bps IS DISTINCT FROM NEW.log_return_t5_bps
               OR OLD.correct_t5 IS DISTINCT FROM NEW.correct_t5
               OR OLD.brier_score_t5 IS DISTINCT FROM NEW.brier_score_t5
               OR OLD.actual_direction_t5 IS DISTINCT FROM NEW.actual_direction_t5
               OR OLD.call_date IS DISTINCT FROM NEW.call_date
               OR OLD.pair IS DISTINCT FROM NEW.pair
               OR OLD.call_id IS DISTINCT FROM NEW.call_id
            THEN
                RAISE EXCEPTION 'Validation_log T+5 data is immutable. Attempted update on row id=% (pair=%, date=%).',
                    OLD.id, OLD.pair, OLD.date;
            END IF;
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF OLD.brier_score_t5 IS NOT NULL THEN
            RAISE EXCEPTION 'Validation_log rows with T+5 data are immutable. Delete attempted on row id=% (pair=%, date=%).',
                OLD.id, OLD.pair, OLD.date;
        END IF;
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
