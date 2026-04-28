-- Add raw US 10Y yield to signals for frontend pulse bar.
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS cross_asset_us10y DOUBLE PRECISION;
