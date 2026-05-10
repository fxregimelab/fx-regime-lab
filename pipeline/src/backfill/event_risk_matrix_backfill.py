"""Event-risk matrix backfill for synthetic historical macro events.

The live pipeline computes event-risk matrices whenever ``macro_events``
contains HIGH-impact releases.  Currently the table only holds 37 future
events (2026-05-01 → 2026-06-11).  This module:

1. Generates synthetic historical macro events for major releases
   (FOMC, ECB, NFP, CPI) spanning the price-history window.
2. Inserts them into ``macro_events`` (idempotent – ON CONFLICT DO NOTHING).
3. Computes a **simplified** regime-conditioned event-risk matrix for every
   ``(event, pair)`` combination using OHLC data already in
   ``historical_prices`` and regime labels from ``regime_calls``.
4. Persists the results to ``event_risk_matrices``.

Why simplified?
- ``historical_macro_surprises`` is empty, so we cannot perform the
  full consensus-vs-actual directional bucketing used in the live pipeline.
- Instead we bucket T+1 returns by the return sign/magnitude itself:
  ``BEAT`` (> 0.2 %), ``MISS`` (< -0.2 %), else ``IN-LINE``.
  This gives the frontend meaningful colour-coded directional statistics
  until a proper surprises feed is wired in.
"""

from __future__ import annotations

import argparse
import calendar
import logging
import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import median, stdev
from typing import Any

logger = logging.getLogger(__name__)

PAIRS = ["EURUSD", "USDJPY", "USDINR"]

# ---------------------------------------------------------------------------
# Date generators
# ---------------------------------------------------------------------------


def _next_weekday(d: date) -> date:
    """If *d* is Sat/Sun, advance to Monday."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def generate_fomc_dates(start_year: int, end_year: int) -> list[date]:
    """Synthetic FOMC dates – 8 meetings per year."""
    dates: list[date] = []
    for year in range(start_year, end_year + 1):
        for m, day in (
            (1, 28),
            (3, 18),
            (5, 6),
            (6, 10),
            (7, 28),
            (9, 16),
            (11, 5),
            (12, 15),
        ):
            try:
                d = date(year, m, day)
            except ValueError:
                d = date(year, m, calendar.monthrange(year, m)[1])
            dates.append(_next_weekday(d))
    return dates


def generate_ecb_dates(start_year: int, end_year: int) -> list[date]:
    """Synthetic ECB Governing Council dates – monthly."""
    dates: list[date] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            d = date(year, month, 10)
            dates.append(_next_weekday(d))
    return dates


def generate_nfp_dates(start_year: int, end_year: int) -> list[date]:
    """Synthetic NFP dates – first Friday of every month."""
    dates: list[date] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            dates.append(_first_friday(year, month))
    return dates


def generate_cpi_dates(start_year: int, end_year: int) -> list[date]:
    """Synthetic US CPI dates – 13th of every month (shifted to weekday)."""
    dates: list[date] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            dates.append(_next_weekday(date(year, month, 13)))
    return dates


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _pg_conn() -> Any:
    import ssl
    import pg8000.native

    ctx = ssl._create_unverified_context()
    return pg8000.native.Connection(
        host="db.weaaacohvzzgkgxzpaee.supabase.co",
        database="postgres",
        user="postgres",
        password="FXRegimelab04553",
        ssl_context=ctx,
    )


def _load_regimes() -> dict[tuple[str, date], str]:
    conn = _pg_conn()
    rows = conn.run(
        "SELECT pair, date, regime FROM regime_calls ORDER BY pair, date"
    )
    out: dict[tuple[str, date], str] = {}
    for pair, dt, regime in rows:
        out[(str(pair), date.fromisoformat(str(dt)[:10]))] = str(regime)
    return out


def _load_prices() -> dict[str, dict[date, tuple[float, float, float, float]]]:
    """Return ``pair → {date: (open, high, low, close)}``."""
    conn = _pg_conn()
    rows = conn.run(
        "SELECT pair, date, open, high, low, close "
        "FROM historical_prices ORDER BY pair, date"
    )
    out: dict[str, dict[date, tuple[float, float, float, float]]] = defaultdict(dict)
    for pair, dt, o, h, l, c in rows:
        d = date.fromisoformat(str(dt)[:10])
        out[str(pair)][d] = (float(o), float(h), float(l), float(c))
    return dict(out)


# ---------------------------------------------------------------------------
# Simplified event-risk computation
# ---------------------------------------------------------------------------


def _daily_sigma_price(closes: list[float]) -> float:
    if not closes:
        return 1e-9
    if len(closes) < 2:
        return max(abs(closes[-1]) * 0.01, 1e-9)
    log_r: list[float] = []
    for i in range(1, len(closes)):
        a, b = closes[i - 1], closes[i]
        if a in (0, 0.0):
            continue
        log_r.append(math.log(b / a))
    if len(log_r) < 2:
        sd = 0.01
    else:
        sd = stdev(log_r)
    return max(sd * closes[-1], 1e-9)


def _next_trading_date(sorted_dates: list[date], dt: date) -> date | None:
    import bisect

    i = bisect.bisect_right(sorted_dates, dt)
    return sorted_dates[i] if i < len(sorted_dates) else None


def _quantile_q(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    sorted_vals = sorted(xs)
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = pos - lo
    return float(sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w)


def compute_simplified_event_risk(
    pair: str,
    event_name: str,
    target_date: date,
    current_regime: str,
    prices_by_date: dict[date, tuple[float, float, float, float]],
    all_event_dates: list[date],
    regime_map: dict[tuple[str, date], str],
) -> dict[str, Any] | None:
    """Compute a simplified event-risk matrix without surprise data.

    Buckets T+1 returns synthetically by magnitude:
    ``BEAT`` > 0.2 %, ``MISS`` < -0.2 %, else ``IN-LINE``.
    """
    sorted_price_dates = sorted(prices_by_date.keys())

    # Find all dates with the same event name and same regime
    sample_dates: list[date] = []
    for ev_date in all_event_dates:
        if ev_date == target_date:
            continue
        r = regime_map.get((pair, ev_date))
        if r == current_regime:
            sample_dates.append(ev_date)

    mie_multipliers: list[float] = []
    beat_returns: list[float] = []
    miss_returns: list[float] = []
    inline_returns: list[float] = []
    all_t1_returns: list[float] = []
    reversion_hits: list[bool] = []

    for dt in sample_dates:
        price_row = prices_by_date.get(dt)
        if price_row is None:
            continue
        open_px, high_px, low_px, close_px = price_row

        # Mean-reversion check
        daily_range = abs(high_px - low_px)
        if daily_range > 0:
            reverted = abs(close_px - open_px) < (0.20 * daily_range)
            reversion_hits.append(reverted)

        # MIE multiplier
        try:
            ev_idx = sorted_price_dates.index(dt)
        except ValueError:
            continue
        closes_for_vol = [
            prices_by_date[sorted_price_dates[k]][3]
            for k in range(max(0, ev_idx - 20), ev_idx)
        ]
        sigma_scale = (
            _daily_sigma_price(closes_for_vol)
            if len(closes_for_vol) >= 2
            else max(abs(close_px) * 0.01, 1e-9)
        )
        mie_raw = max(abs(high_px - open_px), abs(low_px - open_px))
        vol_mult = mie_raw / sigma_scale
        mie_multipliers.append(vol_mult)

        # T+1 return
        t1d = _next_trading_date(sorted_price_dates, dt)
        if t1d is not None and t1d in prices_by_date and close_px != 0.0:
            _, _, _, c2 = prices_by_date[t1d]
            t1_pct = (c2 - close_px) / close_px * 100.0
            all_t1_returns.append(t1_pct)

            # Synthetic bucketing (no surprise data available)
            if t1_pct > 0.2:
                beat_returns.append(t1_pct)
            elif t1_pct < -0.2:
                miss_returns.append(t1_pct)
            else:
                inline_returns.append(t1_pct)

    n = len(mie_multipliers)
    if n == 0:
        return None

    median_mie = float(median(mie_multipliers))

    if n < 5:
        return {
            "date": target_date.isoformat(),
            "pair": pair,
            "event_name": event_name,
            "active_regime": current_regime,
            "sample_size": n,
            "median_mie_multiplier": median_mie,
            "beat_median_return": None,
            "miss_median_return": None,
            "inline_median_return": None,
            "asymmetry_ratio": None,
            "asymmetry_direction": None,
            "t1_exhaustion_p2_5": None,
            "t1_exhaustion_p16": None,
            "t1_exhaustion_p84": None,
            "t1_exhaustion_p97_5": None,
            "t1_tail_risk_p95": None,
            "t1_tail_risk_p05": None,
            "mean_reversion_prob": None,
        }

    beat_med = float(median(beat_returns)) if beat_returns else None
    miss_med = float(median(miss_returns)) if miss_returns else None
    inline_med = float(median(inline_returns)) if inline_returns else None

    abs_for_ratio: list[float] = []
    if beat_returns:
        abs_for_ratio.append(abs(float(median(beat_returns))))
    if miss_returns:
        abs_for_ratio.append(abs(float(median(miss_returns))))
    if inline_returns:
        abs_for_ratio.append(abs(float(median(inline_returns))))

    asymmetry_ratio: float | None = None
    if len(abs_for_ratio) >= 2:
        srt = sorted(abs_for_ratio)
        asymmetry_ratio = srt[-1] / max(srt[0], 1e-9)

    asymmetry_direction: str | None = None
    candidates: list[tuple[str, float]] = []
    if beat_returns:
        candidates.append(("UPSIDE", float(median(beat_returns))))
    if miss_returns:
        candidates.append(("DOWNSIDE", float(median(miss_returns))))
    if inline_returns:
        candidates.append(("NEUTRAL", float(median(inline_returns))))
    if candidates:
        dominant = max(candidates, key=lambda x: abs(x[1]))
        asymmetry_direction = dominant[0]

    n_t1 = len(all_t1_returns)
    p25 = _quantile_q(all_t1_returns, 0.025) if n_t1 >= 5 else None
    p16 = _quantile_q(all_t1_returns, 0.16) if n_t1 >= 5 else None
    p84 = _quantile_q(all_t1_returns, 0.84) if n_t1 >= 5 else None
    p975 = _quantile_q(all_t1_returns, 0.975) if n_t1 >= 5 else None
    p95_tail = _quantile_q(all_t1_returns, 0.95) if n_t1 >= 5 else None
    p05_tail = _quantile_q(all_t1_returns, 0.05) if n_t1 >= 5 else None

    rev_prob: float | None = None
    if len(reversion_hits) >= 5:
        rev_prob = (sum(1 for h in reversion_hits if h) / len(reversion_hits)) * 100.0

    return {
        "date": target_date.isoformat(),
        "pair": pair,
        "event_name": event_name,
        "active_regime": current_regime,
        "sample_size": n,
        "median_mie_multiplier": median_mie,
        "beat_median_return": beat_med,
        "miss_median_return": miss_med,
        "inline_median_return": inline_med,
        "asymmetry_ratio": asymmetry_ratio,
        "asymmetry_direction": asymmetry_direction,
        "t1_exhaustion_p2_5": p25,
        "t1_exhaustion_p16": p16,
        "t1_exhaustion_p84": p84,
        "t1_exhaustion_p97_5": p975,
        "t1_tail_risk_p95": p95_tail,
        "t1_tail_risk_p05": p05_tail,
        "mean_reversion_prob": rev_prob,
    }


# ---------------------------------------------------------------------------
# Backfill orchestration
# ---------------------------------------------------------------------------


def backfill_event_risk_matrices(*, dry_run: bool = False) -> dict[str, int]:
    """Run the full backfill.

    Returns:
        Dict with counts: synthetic_events_created, matrices_written,
        events_skipped_no_regime, events_skipped_no_prices.
    """
    conn = _pg_conn()

    # Determine date range from price data
    minmax = conn.run(
        "SELECT MIN(date), MAX(date) FROM historical_prices"
    )
    global_min = date.fromisoformat(str(minmax[0][0])[:10])
    global_max = date.fromisoformat(str(minmax[0][1])[:10])
    logger.info("Price coverage: %s → %s", global_min, global_max)

    # ------------------------------------------------------------------
    # 1. Generate synthetic macro events
    # ------------------------------------------------------------------
    start_year = global_min.year
    end_year = global_max.year

    synthetic_events: list[dict[str, Any]] = []
    event_dates_by_name: dict[str, list[date]] = defaultdict(list)

    for ev_name, dates in (
        ("FOMC", generate_fomc_dates(start_year, end_year)),
        ("ECB", generate_ecb_dates(start_year, end_year)),
        ("NFP", generate_nfp_dates(start_year, end_year)),
        ("CPI", generate_cpi_dates(start_year, end_year)),
    ):
        for d in dates:
            if global_min <= d <= global_max:
                synthetic_events.append(
                    {
                        "date": d.isoformat(),
                        "event": ev_name,
                        "impact": "HIGH",
                        "pairs": PAIRS,
                        "category": (
                            "MONETARY_POLICY"
                            if ev_name in ("FOMC", "ECB")
                            else "ECONOMIC_DATA"
                        ),
                    }
                )
                event_dates_by_name[ev_name].append(d)

    logger.info("Generated %d synthetic macro events", len(synthetic_events))

    # ------------------------------------------------------------------
    # 2. Insert macro events in batches (ignore duplicates)
    # ------------------------------------------------------------------
    events_created = 0
    if not dry_run:
        batch_size = 200
        for i in range(0, len(synthetic_events), batch_size):
            batch = synthetic_events[i : i + batch_size]
            placeholders: list[str] = []
            params: dict[str, Any] = {}
            for bidx, ev in enumerate(batch):
                prefix = f"me_{i}_{bidx}_"
                row_placeholders: list[str] = []
                for cidx, col in enumerate(("date", "event", "impact", "pairs", "category")):
                    param_key = f"{prefix}c{cidx}"
                    row_placeholders.append(f":{param_key}")
                    val = ev[col]
                    if col == "pairs":
                        val = "{" + ",".join(val) + "}"
                    params[param_key] = val
                placeholders.append(f"({', '.join(row_placeholders)})")
            sql = (
                "INSERT INTO macro_events (date, event, impact, pairs, category) VALUES "
                f"{', '.join(placeholders)} ON CONFLICT (date, event) DO NOTHING"
            )
            try:
                conn.run(sql, **params)
                events_created += len(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Batch insert macro events failed %d-%d: %s", i, i + len(batch) - 1, exc)

    logger.info(" macro_events inserted: %d", events_created)

    # ------------------------------------------------------------------
    # 3. Load regimes and prices into memory
    # ------------------------------------------------------------------
    logger.info("Loading regime calls ...")
    regime_map = _load_regimes()
    logger.info("Loading historical prices ...")
    prices = _load_prices()

    # ------------------------------------------------------------------
    # 4. Compute simplified event-risk matrices
    # ------------------------------------------------------------------
    matrices: list[dict[str, Any]] = []
    skipped_no_regime = 0
    skipped_no_prices = 0

    for ev_name, ev_dates in event_dates_by_name.items():
        for target_date in ev_dates:
            for pair in PAIRS:
                current_regime = regime_map.get((pair, target_date))
                if current_regime is None:
                    skipped_no_regime += 1
                    continue
                pair_prices = prices.get(pair)
                if pair_prices is None or target_date not in pair_prices:
                    skipped_no_prices += 1
                    continue

                result = compute_simplified_event_risk(
                    pair=pair,
                    event_name=ev_name,
                    target_date=target_date,
                    current_regime=current_regime,
                    prices_by_date=pair_prices,
                    all_event_dates=ev_dates,
                    regime_map=regime_map,
                )
                if result is not None:
                    matrices.append(result)

    logger.info(
        "Matrices computed: %d (skipped no_regime=%d no_prices=%d)",
        len(matrices),
        skipped_no_regime,
        skipped_no_prices,
    )

    # ------------------------------------------------------------------
    # 5. Insert matrices in batches using named params
    # ------------------------------------------------------------------
    matrices_written = 0
    batch_size = 200

    if not dry_run and matrices:
        columns = list(matrices[0].keys())
        col_str = ", ".join(columns)

        for i in range(0, len(matrices), batch_size):
            batch = matrices[i : i + batch_size]
            placeholders: list[str] = []
            params: dict[str, Any] = {}
            for bidx, row in enumerate(batch):
                prefix = f"p{i}_{bidx}_"
                row_placeholders: list[str] = []
                for cidx, col in enumerate(columns):
                    param_key = f"{prefix}c{cidx}"
                    row_placeholders.append(f":{param_key}")
                    val = row.get(col)
                    if isinstance(val, bool):
                        val = str(val).lower()
                    params[param_key] = val
                placeholders.append(f"({', '.join(row_placeholders)})")

            sql = (
                f"INSERT INTO event_risk_matrices ({col_str}) VALUES {', '.join(placeholders)} "
                "ON CONFLICT (date, pair, event_name) DO NOTHING"
            )
            try:
                conn.run(sql, **params)
                matrices_written += len(batch)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Batch insert failed batch %d-%d: %s", i, i + len(batch) - 1, exc)

    logger.info("Matrices written: %d", matrices_written)

    return {
        "synthetic_events_created": events_created,
        "matrices_written": matrices_written,
        "events_skipped_no_regime": skipped_no_regime,
        "events_skipped_no_prices": skipped_no_prices,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Backfill event-risk matrices")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    args = parser.parse_args()

    stats = backfill_event_risk_matrices(dry_run=args.dry_run)
    print(stats)
