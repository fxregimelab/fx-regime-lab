"""Permutation importance diagnostic for signal families.

Measures how much each signal family contributes to T+5 directional accuracy
by shuffling its values across the lookback window and measuring the accuracy drop.

Usage::

    python -m src.diagnostics.permutation_importance --pair EURUSD --lookback 252
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import date
from typing import Any

import numpy as np

from src.backfill.simulation_engine import _pg_conn
from src.regime.composite import compute_composite, compute_dynamic_betas
from src.signals.cot import compute_cot_smart_spread_percentile, normalize_cot_signal
from src.signals.special import compute_special_signal
from src.signals.volatility import compute_vol_signal
from src.types import CotRow, normalize_fx_pair_key
from src.validation.engine import is_correct, log_return_bps, realized_direction

logger = logging.getLogger(__name__)


def _load_signals(pair: str, start: date, end: date) -> list[dict[str, Any]]:
    """Load full signal rows from the DB for the pair and date range."""
    conn = _pg_conn()
    result = conn.run(
        "SELECT date, rate_diff_2y, rate_diff_10y, cot_percentile, "
        "realized_vol_5d, realized_vol_20d, implied_vol_30d, spot, "
        "cross_asset_vix, cross_asset_dxy, cross_asset_oil, "
        "cross_asset_us10y, cross_asset_gold, cross_asset_copper, cross_asset_stoxx, "
        "oi_delta, rate_z_tactical, rate_z_structural, z_blended, fpi_flow, "
        "ecb_balance_sheet, bund_btp_spread, cot_asset_mgr_net, cot_lev_money_net "
        "FROM signals WHERE pair = :pair AND date >= :start AND date <= :end ORDER BY date",
        pair=pair,
        start=start.isoformat(),
        end=end.isoformat(),
    )
    conn.close()
    rows: list[dict[str, Any]] = []
    for r in result:
        d = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])[:10])
        rows.append(
            {
                "date": d,
                "rate_diff_2y": _f(r[1]),
                "rate_diff_10y": _f(r[2]),
                "cot_percentile": _f(r[3]),
                "realized_vol_5d": _f(r[4]),
                "realized_vol_20d": _f(r[5]),
                "implied_vol_30d": _f(r[6]),
                "spot": _f(r[7]),
                "cross_asset_vix": _f(r[8]),
                "cross_asset_dxy": _f(r[9]),
                "cross_asset_oil": _f(r[10]),
                "cross_asset_us10y": _f(r[11]),
                "cross_asset_gold": _f(r[12]),
                "cross_asset_copper": _f(r[13]),
                "cross_asset_stoxx": _f(r[14]),
                "oi_delta": _i(r[15]),
                "rate_z_tactical": _f(r[16]),
                "rate_z_structural": _f(r[17]),
                "z_blended": _f(r[18]),
                "fpi_flow": _f(r[19]),
                "ecb_balance_sheet": _f(r[20]),
                "bund_btp_spread": _f(r[21]),
                "cot_asset_mgr_net": _i(r[22]),
                "cot_lev_money_net": _i(r[23]),
            }
        )
    return rows


def _load_spots(pair: str, start: date, end: date) -> dict[date, float]:
    """Load spot closes from historical_prices for the pair and date range (wider)."""
    conn = _pg_conn()
    # Widen the range so T+5 lookups are available.
    result = conn.run(
        "SELECT date, close FROM historical_prices WHERE pair = :pair "
        "AND date >= :start AND date <= :end ORDER BY date",
        pair=pair,
        start=start.isoformat(),
        end=(end.isoformat() if end else None),
    )
    conn.close()
    out: dict[date, float] = {}
    for r in result:
        d = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])[:10])
        out[d] = float(r[1]) if r[1] is not None else 0.0
    return out


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


def _i(v: Any) -> int | None:
    return int(v) if v is not None else None


def _build_cross_asset(row: dict[str, Any]) -> dict[str, Any]:
    """Build cross-asset dict from signal row for compute_special_signal."""
    return {
        "vix": row.get("cross_asset_vix"),
        "dxy": row.get("cross_asset_dxy"),
        "oil": row.get("cross_asset_oil"),
        "gold": row.get("cross_asset_gold"),
        "copper": row.get("cross_asset_copper"),
        "stoxx": row.get("cross_asset_stoxx"),
    }


def _compute_rate_norm(row: dict[str, Any]) -> float | None:
    """Read z_blended from signal row (M.3.2).

    Falls back to recomputing from rate_z_tactical + rate_z_structural
    for rows written before the z_blended column existed.
    """
    zb = row.get("z_blended")
    if zb is not None:
        return float(zb)
    z_t = row.get("rate_z_tactical")
    z_s = row.get("rate_z_structural")
    if z_t is not None and z_s is not None:
        return float(0.60 * z_t + 0.40 * z_s)
    if z_t is not None:
        return float(z_t)
    if z_s is not None:
        return float(z_s)
    return None


def _compute_cot_norm(row: dict[str, Any], cot_rows: list[CotRow] | None = None) -> float | None:
    """Compute COT norm with smart-spread blend (M.3.3)."""
    cot_pct = row.get("cot_percentile")
    if cot_pct is None:
        return None
    cot_smart = None
    if cot_rows is not None:
        cot_smart = compute_cot_smart_spread_percentile(cot_rows, row.get("pair", ""))
    cot_pct_norm = normalize_cot_signal(cot_pct)
    cot_smart_norm = normalize_cot_signal(cot_smart) if cot_smart is not None else None
    if cot_smart_norm is not None and cot_pct_norm is not None:
        return float(0.70 * cot_pct_norm + 0.30 * cot_smart_norm)
    return cot_pct_norm


def _compute_oi_norm(row: dict[str, Any]) -> float | None:
    """OI norm from oi_delta in signals table (approximate)."""
    # The signals table stores oi_delta, not oi_pct. We skip OI norm
    # unless a full COT history is available to compute the percentile.
    _ = row
    return None


def _compute_vol_norm(row: dict[str, Any], rv5_series: list[float]) -> float | None:
    """Compute vol_norm using rolling 90th percentile of RV5."""
    rv5 = row.get("realized_vol_5d")
    rv20 = row.get("realized_vol_20d")
    if rv5 is None or rv20 is None:
        return None
    # vol_90th up to (but not including) current date
    idx = len(rv5_series)
    if idx > 0:
        hist = rv5_series[:idx]
        vol_90th = float(np.percentile(hist, 90)) if hist else None
    else:
        vol_90th = None
    return compute_vol_signal(float(rv5), float(rv20), vol_90th)


def _compute_special_norm(row: dict[str, Any], pair: str) -> float | None:
    """Compute special signal with real macro data for EURUSD (M.3.1)."""
    cross = _build_cross_asset(row)
    kwargs: dict[str, Any] = {}
    if pair == "EURUSD":
        kwargs = {
            "bund_btp_spread": row.get("bund_btp_spread"),
            "ecb_balance_sheet": row.get("ecb_balance_sheet"),
        }
    return compute_special_signal(pair, cross, **kwargs)


def _compute_fpi_norm(row: dict[str, Any]) -> float | None:
    """FPI norm for USDINR only."""
    # Requires historical FPI distribution for normalization.
    # Diagnostic skip — FPI is pair-specific and data-sparse.
    _ = row
    return None


def _predicted_direction(composite: float | None) -> str:
    if composite is None:
        return "NEUTRAL"
    if composite > 0.1:
        return "BULLISH"
    if composite < -0.1:
        return "BEARISH"
    return "NEUTRAL"


def _compute_accuracy(
    rows: list[dict[str, Any]],
    spots: dict[date, float],
    family_values: dict[str, list[float | None]],
    betas: dict[str, float],
    pair: str,
) -> float:
    """Compute T+5 directional accuracy given family values."""
    correct = 0
    total = 0
    sorted_dates = sorted(spots.keys())
    date_to_idx = {d: i for i, d in enumerate(sorted_dates)}

    for i, row in enumerate(rows):
        as_of = row["date"]
        if as_of not in date_to_idx:
            continue
        idx = date_to_idx[as_of]
        if idx + 5 >= len(sorted_dates):
            continue
        t5_date = sorted_dates[idx + 5]
        s0 = spots.get(as_of)
        s5 = spots.get(t5_date)
        if s0 is None or s5 is None or s0 <= 0 or s5 <= 0:
            continue

        rate_norm = family_values["rate"][i]
        cot_norm = family_values["cot"][i]
        vol_norm = family_values["vol"][i]
        oi_norm = family_values["oi"][i]
        special_norm = family_values["special"][i]
        fpi_norm = family_values["fpi"][i]

        composite = compute_composite(
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            pair=pair,
            special_signal=special_norm,
            fpi_signal=fpi_norm,
            betas=betas,
        )
        predicted = _predicted_direction(composite)
        if predicted == "NEUTRAL":
            continue

        bps = log_return_bps(s0, s5)
        realized = realized_direction(bps)
        if is_correct(predicted, realized):
            correct += 1
        total += 1

    if total == 0:
        return 0.0
    return correct / total


def _shuffle_family(values: list[float | None], seed: int) -> list[float | None]:
    """Shuffle a family's values while preserving None positions."""
    rng = random.Random(seed)
    non_none = [v for v in values if v is not None]
    rng.shuffle(non_none)
    out: list[float | None] = []
    it = iter(non_none)
    for v in values:
        if v is None:
            out.append(None)
        else:
            out.append(next(it))
    return out


def run_permutation_importance(
    pair: str,
    lookback_days: int = 252,
    n_shuffle: int = 5,
) -> dict[str, Any]:
    """For each signal family, shuffle its historical values and measure accuracy drop.

    Returns {family: delta_accuracy} where delta = baseline_accuracy - shuffled_accuracy.
    A large positive delta means the signal family is important.
    A near-zero or negative delta means the signal family adds noise.
    """
    pair = normalize_fx_pair_key(pair) or pair
    end = date.today()
    start = date.fromordinal(end.toordinal() - lookback_days)

    rows = _load_signals(pair, start, end)
    if len(rows) < 30:
        logger.warning("Only %d signal rows for %s — insufficient data", len(rows), pair)
        return {
            "pair": pair,
            "lookback_days": lookback_days,
            "baseline_accuracy": 0.0,
            "families": {},
        }

    # Widen spot window for T+5 lookups.
    spots = _load_spots(pair, start, date.fromordinal(end.toordinal() + 10))

    # Build family values for each day.
    rate_values: list[float | None] = []
    cot_values: list[float | None] = []
    vol_values: list[float | None] = []
    oi_values: list[float | None] = []
    special_values: list[float | None] = []
    fpi_values: list[float | None] = []

    rv5_series: list[float] = []
    for row in rows:
        rv5 = row.get("realized_vol_5d")
        if rv5 is not None:
            rv5_series.append(float(rv5))

    for i, row in enumerate(rows):
        rate_values.append(_compute_rate_norm(row))
        cot_values.append(_compute_cot_norm(row))
        vol_values.append(_compute_vol_norm(row, rv5_series[:i]))
        oi_values.append(_compute_oi_norm(row))
        special_values.append(_compute_special_norm(row, pair))
        fpi_values.append(_compute_fpi_norm(row))

    # Compute betas once from the full window of family values.
    # Simplified: compute_dynamic_betas expects historical_rows
    # (list of dicts with signal keys). We approximate by using
    # the signal values directly.
    hist_rows: list[dict[str, float]] = []
    for i in range(len(rows)):
        r: dict[str, float] = {}
        for k, v in {
            "rate": rate_values[i],
            "cot": cot_values[i],
            "vol": vol_values[i],
            "oi": oi_values[i],
            "special": special_values[i],
            "fpi": fpi_values[i],
        }.items():
            if v is not None:
                r[k] = v
        if r:
            hist_rows.append(r)
    betas = compute_dynamic_betas(hist_rows) if len(hist_rows) >= 30 else {}

    family_values = {
        "rate": rate_values,
        "cot": cot_values,
        "vol": vol_values,
        "oi": oi_values,
        "special": special_values,
        "fpi": fpi_values,
    }

    baseline = _compute_accuracy(rows, spots, family_values, betas, pair)
    logger.info("%s baseline accuracy: %.3f", pair, baseline)

    families = ["rate", "cot", "vol", "oi", "special", "fpi"]
    results: dict[str, Any] = {}
    for family in families:
        deltas: list[float] = []
        for shuffle_i in range(n_shuffle):
            shuffled = dict(family_values)
            shuffled[family] = _shuffle_family(family_values[family], seed=shuffle_i + 42)
            acc = _compute_accuracy(rows, spots, shuffled, betas, pair)
            deltas.append(baseline - acc)
        avg_delta = float(np.mean(deltas))
        results[family] = {"delta": round(avg_delta, 4), "n_shuffle": n_shuffle}
        logger.info("%s %s delta: %.4f", pair, family, avg_delta)

    return {
        "pair": pair,
        "lookback_days": lookback_days,
        "baseline_accuracy": round(baseline, 4),
        "families": results,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    parser.add_argument("--lookback", type=int, default=252)
    parser.add_argument("--n-shuffle", type=int, default=5)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    result = run_permutation_importance(
        args.pair,
        lookback_days=args.lookback,
        n_shuffle=args.n_shuffle,
    )
    print(json.dumps(result, indent=2, default=str))
    if args.output:
        with open(args.output, "w") as fh:
            json.dump(result, fh, indent=2, default=str)


if __name__ == "__main__":
    main()
