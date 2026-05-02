-- Dual correlation: target pair log-returns vs cross-sectional mean of other G10 FX log-returns.

CREATE OR REPLACE FUNCTION public.calculate_dual_correlation(p_pair text, p_lookback int)
RETURNS double precision
LANGUAGE sql
STABLE
AS $sql$
WITH g10 AS (
  SELECT unnest(ARRAY[
    'EURUSD', 'USDJPY', 'USDINR', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF'
  ]::text[]) AS pair
),
bounds AS (
  SELECT COALESCE(MAX(hp.date), CURRENT_DATE) AS dmax
  FROM historical_prices hp
  INNER JOIN g10 g ON g.pair = hp.pair
),
r AS (
  SELECT
    p.pair,
    p.date,
    CASE
      WHEN lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) IS NOT NULL
        AND lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date) > 0
        AND p.close > 0
      THEN LN(p.close / lag(p.close) OVER (PARTITION BY p.pair ORDER BY p.date))
      ELSE NULL
    END AS lr
  FROM historical_prices p
  INNER JOIN g10 g ON g.pair = p.pair
  CROSS JOIN bounds b
  WHERE p.date >= (b.dmax - INTERVAL '400 days')::date
),
target AS (
  SELECT date, lr AS lr_target
  FROM r
  WHERE pair = p_pair
),
basket AS (
  SELECT
    date,
    AVG(lr) AS lr_basket
  FROM r
  WHERE pair <> p_pair
    AND lr IS NOT NULL
  GROUP BY date
),
joined AS (
  SELECT
    t.date,
    t.lr_target,
    b.lr_basket
  FROM target t
  INNER JOIN basket b ON b.date = t.date
  WHERE t.lr_target IS NOT NULL
    AND b.lr_basket IS NOT NULL
),
trimmed AS (
  SELECT
    lr_target,
    lr_basket,
    ROW_NUMBER() OVER (ORDER BY date DESC) AS rn
  FROM joined
)
SELECT corr(lr_target, lr_basket)
FROM trimmed
WHERE rn <= GREATEST(p_lookback, 5);
$sql$;

GRANT EXECUTE ON FUNCTION public.calculate_dual_correlation(text, int) TO anon, authenticated, service_role;

ALTER TABLE brief_log
  ADD COLUMN IF NOT EXISTS dollar_dominance double precision,
  ADD COLUMN IF NOT EXISTS idiosyncratic_outlier text,
  ADD COLUMN IF NOT EXISTS sentiment_json jsonb;

COMMENT ON COLUMN brief_log.dollar_dominance IS 'Book-wide USD thematic alignment 0–100 (percent).';
COMMENT ON COLUMN brief_log.idiosyncratic_outlier IS 'FX pair most idiosyncratic vs G10 basket (low dual correlation).';
COMMENT ON COLUMN brief_log.sentiment_json IS 'Pre-baked Polymarket + synthesis metadata for UI (single-query home).';
