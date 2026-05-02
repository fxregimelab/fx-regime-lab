-- Structural instability flag (rate carry scale: 1y MAD vs 5y MAD)
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS structural_instability BOOLEAN NOT NULL DEFAULT false;
