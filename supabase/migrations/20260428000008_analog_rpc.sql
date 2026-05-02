-- Server-side historical analog matching (avoids loading deep history into Python).

CREATE OR REPLACE FUNCTION public.match_historical_analogs(
  target_pair text,
  as_of_date date,
  current_trend double precision,
  current_comp double precision,
  limit_rows integer DEFAULT 3
)
RETURNS TABLE (
  rank integer,
  match_date date,
  match_score double precision,
  forward_30d_return double precision,
  regime_stability double precision,
  context_label text,
  current_trend_5d double precision,
  matched_trend_5d double precision,
  current_composite double precision
)
LANGUAGE sql
STABLE
AS $function$
WITH ordered AS (
  SELECT
    hp.date AS d,
    hp.close AS c,
    LAG(hp.close, 5) OVER (ORDER BY hp.date) AS c_lag5,
    LEAD(hp.close, 30) OVER (ORDER BY hp.date) AS c_lead30
  FROM historical_prices hp
  WHERE hp.pair = target_pair
    AND hp.date < as_of_date
    AND hp.close IS NOT NULL
    AND hp.close > 0
),
candidates AS (
  SELECT
    o.d AS match_date,
    o.c,
    o.c_lag5,
    o.c_lead30,
    CASE
      WHEN o.c_lag5 IS NOT NULL AND o.c_lag5 > 0 THEN ((o.c / o.c_lag5) - 1.0) * 100.0
    END AS matched_trend_5d
  FROM ordered o
),
scored AS (
  SELECT
    cnd.match_date,
    cnd.matched_trend_5d,
    cnd.c,
    cnd.c_lead30,
    LEAST(2.0::double precision, GREATEST(-2.0::double precision, cnd.matched_trend_5d / 2.0))
      AS hist_comp_proxy,
    ABS(cnd.matched_trend_5d - current_trend) AS trend_dist,
    ABS(
      LEAST(2.0::double precision, GREATEST(-2.0::double precision, cnd.matched_trend_5d / 2.0))
      - current_comp
    ) AS comp_dist
  FROM candidates cnd
  WHERE cnd.matched_trend_5d IS NOT NULL
    AND cnd.c_lead30 IS NOT NULL
),
ranked AS (
  SELECT
    sc.match_date,
    sc.matched_trend_5d,
    current_trend,
    current_comp,
    (1.0 / (1.0 + (sc.trend_dist / 2.0))) AS trend_sim,
    (1.0 / (1.0 + (sc.comp_dist / 1.5))) AS comp_sim,
    (sc.trend_dist + sc.comp_dist) AS total_dist,
    ((sc.c_lead30 / sc.c) - 1.0) * 100.0 AS forward_30d_return,
    CASE
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2009 THEN 'Post-GFC'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2016 THEN 'QE Divergence'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2020 THEN 'Late-Cycle / Election'
      WHEN EXTRACT(YEAR FROM sc.match_date)::integer <= 2022 THEN 'Pandemic / Shock'
      ELSE 'Tightening Cycle'
    END AS ctx_lbl
  FROM scored sc
),
topn AS (
  SELECT
    ROW_NUMBER() OVER (ORDER BY rnk.total_dist ASC, rnk.match_date DESC) AS rk,
    rnk.match_date,
    (100.0 * (0.75 * rnk.trend_sim + 0.25 * rnk.comp_sim)) AS ms,
    rnk.forward_30d_return,
    NULL::double precision AS stab,
    rnk.ctx_lbl,
    rnk.current_trend,
    rnk.matched_trend_5d,
    rnk.current_comp
  FROM ranked rnk
)
SELECT
  t.rk::integer,
  t.match_date,
  t.ms,
  t.forward_30d_return,
  t.stab,
  t.ctx_lbl,
  t.current_trend,
  t.matched_trend_5d,
  t.current_comp
FROM topn t
WHERE t.rk <= limit_rows
ORDER BY t.rk;
$function$;

GRANT EXECUTE ON FUNCTION public.match_historical_analogs(text, date, double precision, double precision, integer)
  TO service_role;
GRANT EXECUTE ON FUNCTION public.match_historical_analogs(text, date, double precision, double precision, integer)
  TO authenticated;
