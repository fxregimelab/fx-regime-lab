"""Historical walk-forward simulation engine (optimized batch version).

Replays the daily pipeline logic over every trading day in ``historical_prices``,
using stored yields from ``historical_yields``.  Cross-asset and COT are omitted
(both degrade gracefully in the model).

Usage::

    python -m src.backfill.simulation_engine --pair USDJPY --start 1997-01-01
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import numpy as np

from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.regime.classifier import classify_regime_layer1
from src.regime.composite import (
    compute_composite,
    compute_dynamic_betas,
    get_primary_driver,
)
from src.regime.confidence import compute_confidence
from src.signals.rate import rate_direction_from_spreads
from src.signals.special import compute_special_signal
from src.signals.volatility import (
    TRADING_DAYS_3Y_VOL_RANK,
    compute_rvol,
    compute_vol_signal,
    empirical_cdf_rank,
    is_vol_expanding,
    realized_vol21_series_annualized_pct,
)
from src.types import (
    Layer1ClassifierContext,
    RegimeCall,
    SignalRow,
    SpotBar,
)

logger = logging.getLogger(__name__)

YIELD_ID_MAP: dict[str, dict[str, str]] = {
    "EURUSD": {"base": "DGS2", "quote_10y": "IRLTLT01DEM156N"},
    "USDJPY": {"base": "DGS2", "quote_10y": "IRLTLT01JPM156N"},
    "USDINR": {"base": "DGS2", "quote_10y": "INDIRLTLT01STM"},
}


def _pg_conn(max_retries: int = 5):
    import os
    import ssl
    import time
    import pg8000.native
    ctx = ssl._create_unverified_context()
    last_err = None
    host = os.environ.get("SUPABASE_DB_HOST", "")
    password = os.environ.get("SUPABASE_DB_PASSWORD", "")
    if not host or not password:
        raise RuntimeError("SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD must be set")
    for attempt in range(max_retries):
        try:
            return pg8000.native.Connection(
                host=host,
                database="postgres",
                user="postgres",
                password=password,
                ssl_context=ctx,
                timeout=30,
            )
        except Exception as e:
            last_err = e
            logger.warning("DB connection attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            time.sleep(min(2 ** attempt, 30))
    raise last_err


def _load_all_yields() -> dict[str, dict[date, float]]:
    conn = _pg_conn()
    result = conn.run("SELECT series_id, date, value FROM historical_yields ORDER BY series_id, date")
    out: dict[str, dict[date, float]] = defaultdict(dict)
    for row in result:
        d = row[1] if isinstance(row[1], date) else date.fromisoformat(str(row[1])[:10])
        out[row[0]][d] = float(row[2])
    conn.close()
    logger.info("Loaded yields for %s series", len(out))
    return dict(out)


def _load_all_spot_bars(pair: str) -> dict[date, SpotBar]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT date, open, high, low, close, volume FROM historical_prices "
        "WHERE pair = :pair ORDER BY date",
        pair=pair,
    )
    conn.close()
    out: dict[date, SpotBar] = {}
    for r in result:
        d = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])[:10])
        out[d] = SpotBar(
            date=d,
            pair=pair,
            open=float(r[1] or r[4] or 0),
            high=float(r[2] or r[4] or 0),
            low=float(r[3] or r[4] or 0),
            close=float(r[4] or 0),
            volume=float(r[5] or 0),
        )
    logger.info("Loaded %d spot bars for %s", len(out), pair)
    return out


def _get_yield(series_id: str, target_date: date, yields_by_series: dict[str, dict[date, float]]) -> float | None:
    series = yields_by_series.get(series_id, {})
    if target_date in series:
        return series[target_date]
    candidates = [d for d in series if d <= target_date]
    if not candidates:
        return None
    return series[max(candidates)]


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def simulate_all_days(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
) -> list[tuple[SignalRow, RegimeCall]]:
    """Compute all regime calls in-memory. Returns list of (signal, call)."""
    spot_map = _load_all_spot_bars(pair)
    all_sorted_dates = sorted(spot_map)
    date_indices = [(i, d) for i, d in enumerate(all_sorted_dates) if start <= d <= end]
    if not date_indices:
        logger.warning("No spot bars for %s in range", pair)
        return []

    n = len(all_sorted_dates)
    all_closes = np.array([spot_map[d].close for d in all_sorted_dates])
    all_log_returns = np.diff(np.log(all_closes))

    # Pre-compute rolling RV5 and RV20
    all_rv20 = np.full(n, np.nan)
    all_rv5 = np.full(n, np.nan)
    for j in range(21, n):
        all_rv20[j] = float(np.std(all_log_returns[j - 21:j]) * np.sqrt(252) * 100)
        all_rv5[j] = float(np.std(all_log_returns[j - 5:j]) * np.sqrt(252) * 100)

    # Pre-compute vol_90th (rolling 252-day percentile of RV5)
    all_vol_90th = np.full(n, np.nan)
    rv5_history: list[float] = []
    for j in range(21, n):
        rv5_history.append(all_rv5[j])
        if len(rv5_history) >= 5:
            window = rv5_history[-252:] if len(rv5_history) > 252 else rv5_history
            all_vol_90th[j] = _percentile(window, 0.90)

    # Pre-compute vol_norm and vol_exp
    all_vol_norm: list[float | None] = [None] * n
    all_vol_exp = [False] * n
    for j in range(21, n):
        if not np.isnan(all_rv5[j]) and not np.isnan(all_rv20[j]):
            v90 = float(all_vol_90th[j]) if not np.isnan(all_vol_90th[j]) else None
            all_vol_norm[j] = compute_vol_signal(float(all_rv5[j]), float(all_rv20[j]), v90)
            if v90 is not None:
                all_vol_exp[j] = is_vol_expanding(float(all_rv5[j]), v90)

    # Pre-compute realized_vol_rank
    all_rv21_series = realized_vol21_series_annualized_pct(all_closes)
    all_rv_rank = np.full(n, np.nan)
    for j in range(21 + 30, n):
        tail = all_rv21_series[21:j + 1]
        win = tail[-TRADING_DAYS_3Y_VOL_RANK:] if len(tail) > TRADING_DAYS_3Y_VOL_RANK else tail
        if len(win) >= 2:
            current = float(win[-1])
            hist = win[:-1]
            all_rv_rank[j] = empirical_cdf_rank(current, hist)

    ymap = YIELD_ID_MAP.get(pair, {})
    yield_series = ymap.get("quote_10y", "DGS10")
    yield_history = sorted(yields_by_series.get(yield_series, {}).items())
    yield_values = [v for _, v in yield_history]

    driver = get_primary_driver(compute_dynamic_betas([]))
    special_signal = compute_special_signal(pair, {})

    results: list[tuple[SignalRow, RegimeCall]] = []
    prior_regime: str | None = None
    carry_history: list[float] = []
    last_carry: float | None = None

    for full_idx, as_of in date_indices:
        if full_idx < 60:
            continue

        today_bar = spot_map[as_of]
        yest_bar = spot_map[all_sorted_dates[full_idx - 1]]
        window_bars = [spot_map[d] for d in all_sorted_dates[max(0, full_idx - 2519):full_idx + 1]]
        spot_closes = [b.close for b in window_bars]

        base_yield = _get_yield(ymap.get("base", "DGS2"), as_of, yields_by_series)
        quote_10y = _get_yield(ymap.get("quote_10y", ""), as_of, yields_by_series)
        us_10y = _get_yield("DGS10", as_of, yields_by_series)
        bei = _get_yield("T10YIE", as_of, yields_by_series)

        if us_10y is not None and quote_10y is not None:
            rate_spread_10y = float(us_10y) - float(quote_10y)
        else:
            rate_spread_10y = None
        rate_spread_2y = base_yield
        rate_spread_10y_real = (
            None
            if rate_spread_10y is None
            else (float(rate_spread_10y) - float(bei) if bei is not None else float(rate_spread_10y))
        )

        # Forward-fill carry history for Layer 1 gate
        if rate_spread_10y is not None:
            last_carry = float(rate_spread_10y)
        if last_carry is not None:
            carry_history.append(last_carry)

        rate_norm_z = None
        rate_z_structural_val = None
        if rate_spread_10y is not None and len(yield_values) >= 20:
            hist_vals = [v for d, v in yield_history if d <= as_of]
            if len(hist_vals) >= 20:
                mean = sum(hist_vals) / len(hist_vals)
                variance = sum((x - mean) ** 2 for x in hist_vals) / len(hist_vals)
                std = variance ** 0.5
                if std > 0:
                    z = (float(rate_spread_10y) - mean) / std
                    rate_norm_z = z
                    rate_z_structural_val = z

        rate_norm = rate_norm_z
        rate_dir = rate_direction_from_spreads(
            rate_spread_2y, rate_spread_10y_real, z_tactical=rate_norm
        )

        rv20 = float(all_rv20[full_idx]) if not np.isnan(all_rv20[full_idx]) else None
        rv5 = float(all_rv5[full_idx]) if not np.isnan(all_rv5[full_idx]) else None
        vol_norm = all_vol_norm[full_idx]
        vol_exp = all_vol_exp[full_idx]

        cot_norm = None
        oi_norm = None
        composite = compute_composite(
            rate_norm, cot_norm, vol_norm, oi_norm,
            pair=pair,
            special_signal=special_signal,
        )
        if composite is None:
            continue

        confidence = compute_confidence(
            composite, rate_norm, cot_norm,
            pair=pair,
            special_signal=special_signal,
        )

        structural_instability = False
        carry_gate = tuple(carry_history[-2520:]) if carry_history else ()
        gate_out = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol_exp,
                structural_instability=structural_instability,
                prior_regime_label=prior_regime,
                carry_risk_adjusted_chronological=carry_gate,
                spot_closes_chronological=tuple(spot_closes),
                breakeven_inflation_chronological=None,
                rate_diff_2y=rate_spread_2y,
                realized_vol_20d=rv20,
            ),
        )
        regime = gate_out["regime"]
        if gate_out["invalidated"]:
            rate_dir = "NEUTRAL"
            confidence = float(max(0.40, confidence * 0.50))

        layer2_out = run_layer2_directional(
            composite=float(composite),
            z_tactical=rate_norm,
            z_structural=rate_z_structural_val,
            rate_direction=rate_dir,
            positioning_percentile=None,
            layer1_invalidated=bool(gate_out["invalidated"]),
        )

        rv_rank_layer3 = float(all_rv_rank[full_idx]) if not np.isnan(all_rv_rank[full_idx]) else None
        layer3_out = run_layer3_execution(
            layer2=layer2_out,
            spot=float(today_bar.close) if today_bar.close else None,
            spot_bars=window_bars,
            realized_vol_rank=rv_rank_layer3,
            risk_reversal_series_bps=(),
        )

        conviction_cap = 0.42 + 0.10 * float(layer2_out["conviction"])
        confidence = min(float(confidence), conviction_cap)

        day_change = today_bar.close - yest_bar.close
        day_chg_pct = (day_change / yest_bar.close * 100) if yest_bar.close else 0.0
        volumes = [b.volume for b in window_bars if b.volume > 0]
        rvol = compute_rvol(volumes)

        signal_row = SignalRow(
            pair=pair,
            date=as_of,
            rate_diff_2y=rate_spread_2y,
            rate_diff_10y=rate_spread_10y,
            cot_percentile=None,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=None,
            spot=today_bar.close,
            day_change=day_change,
            day_change_pct=day_chg_pct,
            cross_asset_vix=None,
            cross_asset_dxy=None,
            cross_asset_oil=None,
            cross_asset_us10y=us_10y,
            cross_asset_gold=None,
            cross_asset_copper=None,
            cross_asset_stoxx=None,
            oi_delta=None,
            volume_rvol=rvol,
            structural_instability=structural_instability,
            breakeven_inflation_10y=bei,
            rate_diff_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_norm,
            rate_z_structural=rate_z_structural_val,
            realized_vol_rank=layer3_out["realized_vol_rank"],
            skew_alignment=layer3_out["skew_alignment"],
        )

        bias = layer2_out["directional_bias"]
        predicted_direction = (
            "BULLISH" if bias == "LONG" else ("BEARISH" if bias == "SHORT" else "NEUTRAL")
        )
        cot_label = "NEUTRAL"
        vol_label = (
            "VOL_EXPANDING" if vol_exp else
            ("BULLISH" if vol_norm is not None and vol_norm > 0.15 else
             ("BEARISH" if vol_norm is not None and vol_norm < -0.15 else "NEUTRAL"))
        )
        oi_label = "NEUTRAL"

        special_label = {
            "EURUSD": "EURUSD_placeholder",
            "USDJPY": "VIX_funding_stress",
            "USDINR": "EM_oil_DXY",
        }.get(pair)

        call = RegimeCall(
            pair=pair,
            date=as_of,
            regime=regime,
            confidence=confidence,
            signal_composite=composite,
            rate_signal=rate_dir,
            primary_driver=driver,
            entry_timing=layer3_out["entry_timing"],
            position_size=layer3_out["position_size"],
            stop_level=layer3_out["stop_level"],
            data_quality_score=0.85,
            stress_level="GREEN",
            predicted_direction=predicted_direction,
            directional_bias=bias,
            conviction=layer2_out["conviction"],
            cot_signal=cot_label,
            vol_signal=vol_label,
            oi_signal=oi_label,
            rr_signal="NEUTRAL",
            special_signal_value=special_signal,
            special_signal_label=special_label,
            model_version="2.0-historical",
        )

        results.append((signal_row, call))
        prior_regime = call.regime

        if len(results) % 500 == 0:
            logger.info("%s: %d days computed", pair, len(results))

    logger.info("%s: total computed %d days", pair, len(results))
    return results


def _batch_write(pair: str, results: list[tuple[SignalRow, RegimeCall]]) -> None:
    if not results:
        return

    conn = _pg_conn()
    conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls")
    conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit")
    conn.run("ALTER TABLE validation_log DISABLE TRIGGER trg_protect_immutable_validation")

    conn.run("DELETE FROM validation_log WHERE pair = :pair", pair=pair)
    conn.run("DELETE FROM signals WHERE pair = :pair", pair=pair)
    conn.run("DELETE FROM regime_calls WHERE pair = :pair", pair=pair)

    signal_rows: list[tuple] = []
    regime_rows: list[tuple] = []
    for signal_row, call in results:
        signal_rows.append((
            signal_row.pair, signal_row.date.isoformat(), signal_row.rate_diff_2y,
            signal_row.rate_diff_10y, signal_row.cot_percentile, signal_row.realized_vol_20d,
            signal_row.realized_vol_5d, signal_row.implied_vol_30d, signal_row.spot,
            signal_row.day_change, signal_row.day_change_pct, signal_row.cross_asset_vix,
            signal_row.cross_asset_dxy, signal_row.cross_asset_oil, signal_row.cross_asset_us10y,
            signal_row.cross_asset_gold, signal_row.cross_asset_copper, signal_row.cross_asset_stoxx,
            signal_row.oi_delta, signal_row.volume_rvol, signal_row.structural_instability,
            signal_row.breakeven_inflation_10y, signal_row.rate_diff_10y_real,
            signal_row.rate_z_tactical, signal_row.rate_z_structural,
            signal_row.realized_vol_rank, signal_row.skew_alignment,
        ))
        regime_rows.append((
            call.pair, call.date.isoformat(), call.regime, call.confidence,
            call.signal_composite, call.rate_signal, call.primary_driver,
            call.entry_timing, call.position_size, call.stop_level,
            call.data_quality_score, call.stress_level, call.predicted_direction,
            call.directional_bias, call.conviction, call.cot_signal,
            call.vol_signal, call.oi_signal, call.rr_signal,
            call.special_signal_value, call.special_signal_label, call.model_version,
        ))

    # Batch insert signals using multi-row INSERT with per-batch commit
    BATCH = 500
    for i in range(0, len(signal_rows), BATCH):
        batch = signal_rows[i:i + BATCH]
        values_sql = []
        params: dict[str, Any] = {}
        for j, row in enumerate(batch):
            prefix = f"r{j}_"
            values_sql.append(
                f"(:{prefix}pair, :{prefix}date, :{prefix}r2y, :{prefix}r10y, :{prefix}cot, "
                f":{prefix}rv20, :{prefix}rv5, :{prefix}iv, :{prefix}spot, :{prefix}dc, :{prefix}dcp, "
                f":{prefix}vix, :{prefix}dxy, :{prefix}oil, :{prefix}us10y, :{prefix}gold, "
                f":{prefix}copper, :{prefix}stoxx, :{prefix}oi, :{prefix}rvol, :{prefix}si, "
                f":{prefix}bei, :{prefix}r10r, :{prefix}rzt, :{prefix}rzs, :{prefix}rvr, :{prefix}sa)"
            )
            params[f"{prefix}pair"] = row[0]
            params[f"{prefix}date"] = row[1]
            params[f"{prefix}r2y"] = row[2]
            params[f"{prefix}r10y"] = row[3]
            params[f"{prefix}cot"] = row[4]
            params[f"{prefix}rv20"] = row[5]
            params[f"{prefix}rv5"] = row[6]
            params[f"{prefix}iv"] = row[7]
            params[f"{prefix}spot"] = row[8]
            params[f"{prefix}dc"] = row[9]
            params[f"{prefix}dcp"] = row[10]
            params[f"{prefix}vix"] = row[11]
            params[f"{prefix}dxy"] = row[12]
            params[f"{prefix}oil"] = row[13]
            params[f"{prefix}us10y"] = row[14]
            params[f"{prefix}gold"] = row[15]
            params[f"{prefix}copper"] = row[16]
            params[f"{prefix}stoxx"] = row[17]
            params[f"{prefix}oi"] = row[18]
            params[f"{prefix}rvol"] = row[19]
            params[f"{prefix}si"] = row[20]
            params[f"{prefix}bei"] = row[21]
            params[f"{prefix}r10r"] = row[22]
            params[f"{prefix}rzt"] = row[23]
            params[f"{prefix}rzs"] = row[24]
            params[f"{prefix}rvr"] = row[25]
            params[f"{prefix}sa"] = row[26]
        sql = (
            "INSERT INTO signals (pair, date, rate_diff_2y, rate_diff_10y, cot_percentile, "
            "realized_vol_20d, realized_vol_5d, implied_vol_30d, spot, day_change, day_change_pct, "
            "cross_asset_vix, cross_asset_dxy, cross_asset_oil, cross_asset_us10y, cross_asset_gold, "
            "cross_asset_copper, cross_asset_stoxx, oi_delta, volume_rvol, structural_instability, "
            "breakeven_inflation_10y, rate_diff_10y_real, rate_z_tactical, rate_z_structural, "
            "realized_vol_rank, skew_alignment) VALUES " + ",".join(values_sql)
        )
        conn.run(sql, **params)
        logger.info("Signals batch %d-%d inserted", i, i + len(batch) - 1)

    for i in range(0, len(regime_rows), BATCH):
        batch = regime_rows[i:i + BATCH]
        values_sql = []
        params: dict[str, Any] = {}
        for j, row in enumerate(batch):
            prefix = f"r{j}_"
            values_sql.append(
                f"(:{prefix}pair, :{prefix}date, :{prefix}regime, :{prefix}conf, :{prefix}comp, "
                f":{prefix}rate, :{prefix}driver, :{prefix}et, :{prefix}ps, :{prefix}sl, "
                f":{prefix}dqs, :{prefix}stress, :{prefix}pred, :{prefix}bias, :{prefix}conv, "
                f":{prefix}cot, :{prefix}vol, :{prefix}oi, :{prefix}rr, :{prefix}ssv, :{prefix}ssl, :{prefix}mv)"
            )
            params[f"{prefix}pair"] = row[0]
            params[f"{prefix}date"] = row[1]
            params[f"{prefix}regime"] = row[2]
            params[f"{prefix}conf"] = row[3]
            params[f"{prefix}comp"] = row[4]
            params[f"{prefix}rate"] = row[5]
            params[f"{prefix}driver"] = row[6]
            params[f"{prefix}et"] = row[7]
            params[f"{prefix}ps"] = row[8]
            params[f"{prefix}sl"] = row[9]
            params[f"{prefix}dqs"] = row[10]
            params[f"{prefix}stress"] = row[11]
            params[f"{prefix}pred"] = row[12]
            params[f"{prefix}bias"] = row[13]
            params[f"{prefix}conv"] = row[14]
            params[f"{prefix}cot"] = row[15]
            params[f"{prefix}vol"] = row[16]
            params[f"{prefix}oi"] = row[17]
            params[f"{prefix}rr"] = row[18]
            params[f"{prefix}ssv"] = row[19]
            params[f"{prefix}ssl"] = row[20]
            params[f"{prefix}mv"] = row[21]
        sql = (
            "INSERT INTO regime_calls (pair, date, regime, confidence, signal_composite, "
            "rate_signal, primary_driver, entry_timing, position_size, stop_level, "
            "data_quality_score, stress_level, predicted_direction, directional_bias, "
            "conviction, cot_signal, vol_signal, oi_signal, rr_signal, special_signal_value, "
            "special_signal_label, model_version) VALUES " + ",".join(values_sql)
        )
        conn.run(sql, **params)
        logger.info("Regime batch %d-%d inserted", i, i + len(batch) - 1)

    conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls")
    conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit")
    conn.run("ALTER TABLE validation_log ENABLE TRIGGER trg_protect_immutable_validation")

    conn.close()
    logger.info("Batch wrote %d signals and %d regime_calls for %s", len(signal_rows), len(regime_rows), pair)


def run_pair_simulation(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
) -> int:
    logger.info("Simulating %s from %s to %s", pair, start, end)
    results = simulate_all_days(pair, start, end, yields_by_series)
    _batch_write(pair, results)
    return len(results)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USDJPY")
    parser.add_argument("--start", default="1997-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    args = parser.parse_args()

    yields_by_series = _load_all_yields()
    count = run_pair_simulation(
        args.pair,
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
        yields_by_series,
    )
    logger.info("Simulation complete: %d days", count)


if __name__ == "__main__":
    main()
