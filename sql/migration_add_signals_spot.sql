-- Run once on existing Supabase projects (new installs get `spot` from schema.sql).
ALTER TABLE signals ADD COLUMN IF NOT EXISTS spot DOUBLE PRECISION;
