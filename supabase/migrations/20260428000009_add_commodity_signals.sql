-- Cross-asset expansion: commodities + EU equity index proxies on signals.

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS cross_asset_gold DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS cross_asset_copper DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS cross_asset_stoxx DOUBLE PRECISION;
