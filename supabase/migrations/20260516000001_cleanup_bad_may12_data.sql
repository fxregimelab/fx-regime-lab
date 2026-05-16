-- Cleanup: Remove corrupt 2026-05-12 regime_calls and signals created during aborted run.
-- Also adds unique constraints to prevent future duplicates.

-- Disable immutability trigger temporarily
ALTER TABLE public.regime_calls DISABLE TRIGGER trg_protect_immutable_calls;

-- Delete bad regime_calls for 2026-05-12 (duplicates with confidence > 1)
DELETE FROM public.regime_calls
WHERE date = '2026-05-12'
  AND confidence > 1;

-- Delete corresponding bad signals for 2026-05-12 (spot IS NULL)
DELETE FROM public.signals
WHERE date = '2026-05-12'
  AND spot IS NULL;

-- Re-enable immutability trigger
ALTER TABLE public.regime_calls ENABLE TRIGGER trg_protect_immutable_calls;

-- Add unique constraint on (pair, date) to prevent future duplicates
-- Use IF NOT EXISTS pattern via constraint check
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'regime_calls_pair_date_unique'
        AND conrelid = 'public.regime_calls'::regclass
    ) THEN
        ALTER TABLE public.regime_calls
        ADD CONSTRAINT regime_calls_pair_date_unique
        UNIQUE (pair, date);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'signals_pair_date_unique'
        AND conrelid = 'public.signals'::regclass
    ) THEN
        ALTER TABLE public.signals
        ADD CONSTRAINT signals_pair_date_unique
        UNIQUE (pair, date);
    END IF;
END $$;

-- Add check constraint on confidence [0, 1]
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'regime_calls_confidence_check'
        AND conrelid = 'public.regime_calls'::regclass
    ) THEN
        ALTER TABLE public.regime_calls
        ADD CONSTRAINT regime_calls_confidence_check
        CHECK (confidence >= 0 AND confidence <= 1);
    END IF;
END $$;
