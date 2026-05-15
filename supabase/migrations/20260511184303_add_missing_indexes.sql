-- Migration: add missing indexes for performance

-- desk_open_cards: frontend queries by date across all pairs
CREATE INDEX IF NOT EXISTS idx_desk_open_cards_date ON public.desk_open_cards (date DESC);

-- signals: cross_asset_us10y is queried for pulse bar
CREATE INDEX IF NOT EXISTS idx_signals_us10y ON public.signals (cross_asset_us10y) WHERE cross_asset_us10y IS NOT NULL;

-- event_risk_matrices: already has (date) and (pair, event_name), add composite
CREATE INDEX IF NOT EXISTS idx_event_risk_matrices_date_pair ON public.event_risk_matrices (date DESC, pair);
