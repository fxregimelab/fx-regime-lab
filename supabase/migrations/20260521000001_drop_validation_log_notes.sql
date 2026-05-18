-- Drop unused `notes` column from validation_log
-- This column was never populated by the current validation engine.
-- Audit ref: docs/DB_AUDIT_STRATEGY.md

ALTER TABLE public.validation_log
    DROP COLUMN IF EXISTS notes;
