-- Regime streak on desk cards + server-side MAX chart thinning (weekly outside 2Y window).

ALTER TABLE public.desk_open_cards
  ADD COLUMN IF NOT EXISTS regime_age INTEGER;

COMMENT ON COLUMN public.desk_open_cards.regime_age IS
  'Consecutive trading days (incl. as-of) the structural regime label has matched, vol-expanding suffix ignored.';

CREATE OR REPLACE FUNCTION public.historical_prices_for_max_chart(
  p_pair text,
  p_cutoff date
)
RETURNS TABLE (
  date date,
  pair text,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision,
  created_at timestamptz
)
LANGUAGE sql
STABLE
AS $function$
  SELECT
    hp.date,
    hp.pair,
    hp.open,
    hp.high,
    hp.low,
    hp.close,
    hp.volume,
    hp.created_at
  FROM public.historical_prices hp
  WHERE hp.pair = p_pair
    AND (
      hp.date >= p_cutoff
      OR (
        hp.date < p_cutoff
        AND EXTRACT(ISODOW FROM hp.date) = 5
      )
    )
  ORDER BY hp.date ASC;
$function$;

GRANT EXECUTE ON FUNCTION public.historical_prices_for_max_chart(text, date)
  TO anon, authenticated, service_role;
