-- Emergency cleanup: remove bad 2026-05-15 data written by aborted pipeline run
-- The pipeline run aborted due to missing API keys but partial/test data was written

BEGIN;
ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls;
DELETE FROM regime_calls WHERE date = '2026-05-15';
ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls;

DELETE FROM signals WHERE date = '2026-05-15';
COMMIT;
