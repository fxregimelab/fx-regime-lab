-- Cross-sectional apex ranking on desk_open_cards
ALTER TABLE desk_open_cards
  ADD COLUMN IF NOT EXISTS global_rank INT,
  ADD COLUMN IF NOT EXISTS apex_score DOUBLE PRECISION;

-- Pairwise return correlations for G10 cluster detection (JSON: { "EURUSD": { "USDJPY": 0.85, ... }, ... })
CREATE OR REPLACE FUNCTION public.get_g10_correlation_matrix()
RETURNS jsonb
LANGUAGE sql
STABLE
AS $sql$
WITH bounds AS (
  SELECT COALESCE(MAX(date), CURRENT_DATE) AS dmax
  FROM historical_prices
),
r AS (
  SELECT
    p.pair,
    p.date,
    CASE
      WHEN lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) IS NOT NULL
        AND lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) > 0
      THEN LN(p.close / lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date))
      ELSE NULL
    END AS lr
  FROM historical_prices p
  CROSS JOIN bounds b
  WHERE p.pair IN (
    'EURUSD', 'USDJPY', 'USDINR', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF'
  )
    AND p.date >= (b.dmax - INTERVAL '120 days')::date
),
cp AS (
  SELECT
    a.pair AS pa,
    b.pair AS pb,
    corr(a.lr, b.lr) AS c
  FROM r a
  INNER JOIN r b ON a.date = b.date AND a.pair < b.pair
  WHERE a.lr IS NOT NULL AND b.lr IS NOT NULL
  GROUP BY a.pair, b.pair
),
agg AS (
  SELECT pa, jsonb_object_agg(pb, c) AS obj
  FROM cp
  WHERE c IS NOT NULL
  GROUP BY pa
)
SELECT COALESCE(jsonb_object_agg(pa, obj), '{}'::jsonb) FROM agg;
$sql$;

GRANT EXECUTE ON FUNCTION public.get_g10_correlation_matrix() TO anon, authenticated, service_role;
