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
import os
from collections import defaultdict
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import numpy as np

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.db import writer
from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.regime.classifier import classify_regime_layer1
from src.regime.composite import compute_composite
from src.regime.confidence import compute_confidence
from src.signals.cot import normalize_cot_signal
from src.signals.direction import (
    DIRECTIONAL_MODEL_VERSION,
    DIRECTIONAL_STRATEGY_VERSION,
    directional_inputs,
)
from src.signals.fpi import FPI_UNAVAILABLE_NOTES
from src.signals.rate import rate_direction_from_spreads
from src.signals.rate_inputs import (
    current_real_yield_spread,
    nominal_ten_year_context,
)
from src.signals.rate_observation import RateObservation, qualified_two_year_spread
from src.signals.special import compute_special_signal
from src.signals.volatility import (
    TRADING_DAYS_3Y_VOL_RANK,
    compute_vol_signal,
    empirical_cdf_rank,
    is_vol_expanding,
    realized_vol21_series_annualized_pct,
)
from src.types import (
    CotRow,
    Layer1ClassifierContext,
    RegimeCall,
    SignalRow,
    SpotBar,
)

logger = logging.getLogger(__name__)

YIELD_ID_MAP: dict[str, dict[str, str]] = {
    "EURUSD": {"foreign_10y": "IRLTLT01DEM156N", "foreign_10y_alias": "de_10y"},
    "USDJPY": {"foreign_10y": "IRLTLT01JPM156N", "foreign_10y_alias": "jp_10y"},
    "USDINR": {"foreign_10y": "INDIRLTLT01STM", "foreign_10y_alias": "in_10y"},
}


def _pg_conn(max_retries: int = 5) -> Any:
    import ssl
    import time

    import pg8000.native

    ctx = ssl._create_unverified_context()
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "SUPABASE_DB_PASSWORD must be set in the environment. "
            "Get it from Supabase Dashboard → Project Settings → Database → Connection string."
        )
    last_err: BaseException | None = None
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
            time.sleep(min(2**attempt, 30))
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")


def _load_all_yields() -> dict[str, dict[date, float]]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT series_id, date, value FROM historical_yields ORDER BY series_id, date"
    )
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


def _get_yield(
    series_id: str, target_date: date, yields_by_series: dict[str, dict[date, float]]
) -> float | None:
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


def _historical_rate_values(
    pair: str,
    as_of: date,
    yields_by_series: dict[str, dict[date, float]],
) -> dict[str, float | None]:
    """Return source IDs and currency aliases without changing their meaning."""
    ymap = YIELD_ID_MAP.get(pair, {})
    foreign_series = ymap.get("foreign_10y", "")
    foreign_alias = ymap.get("foreign_10y_alias", "")
    us_2y = _get_yield("DGS2", as_of, yields_by_series)
    us_10y = _get_yield("DGS10", as_of, yields_by_series)
    foreign_10y = _get_yield(foreign_series, as_of, yields_by_series)
    values: dict[str, float | None] = {
        "DGS2": us_2y,
        "ECBDFR": _get_yield("ECBDFR", as_of, yields_by_series),
        "IRLTLT01JPM156N": _get_yield("IRLTLT01JPM156N", as_of, yields_by_series),
        "INDIRLTLT01STM": _get_yield("INDIRLTLT01STM", as_of, yields_by_series),
        "T10YIE": _get_yield("T10YIE", as_of, yields_by_series),
        "us_2y": us_2y,
        "us_10y": us_10y,
    }
    if foreign_alias:
        values[foreign_alias] = foreign_10y
    return values


def simulate_all_days(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
    *,
    rate_observations_by_date: Mapping[date, Mapping[str, RateObservation]] | None = None,
    decision_times: Mapping[date, datetime] | None = None,
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
        all_rv20[j] = float(np.std(all_log_returns[j - 21 : j]) * np.sqrt(252) * 100)
        all_rv5[j] = float(np.std(all_log_returns[j - 5 : j]) * np.sqrt(252) * 100)

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
        tail = all_rv21_series[21 : j + 1]
        win = tail[-TRADING_DAYS_3Y_VOL_RANK:] if len(tail) > TRADING_DAYS_3Y_VOL_RANK else tail
        if len(win) >= 2:
            current = float(win[-1])
            hist = win[:-1]
            all_rv_rank[j] = empirical_cdf_rank(current, hist)

    driver = "Static directional reference (unvalidated)"
    special_signal = directional_inputs(
        pair, rate=None, cot=None, special=compute_special_signal(pair, {}), fpi=None
    ).special

    results: list[tuple[SignalRow, RegimeCall]] = []
    prior_regime: str | None = None

    for full_idx, as_of in date_indices:
        if full_idx < 60:
            continue

        today_bar = spot_map[as_of]
        window_bars = [
            spot_map[d] for d in all_sorted_dates[max(0, full_idx - 2519) : full_idx + 1]
        ]
        spot_closes = [b.close for b in window_bars]

        rate_values = _historical_rate_values(pair, as_of, yields_by_series)
        bei = rate_values.get("T10YIE")
        rate_spread_2y = qualified_two_year_spread(
            pair,
            (rate_observations_by_date or {}).get(as_of, {}),
            decision_at=(decision_times or {}).get(as_of),
        )
        rate_spread_10y = nominal_ten_year_context(pair, rate_values)
        rate_spread_10y_real = current_real_yield_spread(pair, rate_spread_10y, rate_values)
        rate_norm = None
        rate_z_structural_val = None
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
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            pair=pair,
            special_signal=special_signal,
        )
        if composite is None:
            logger.debug("directional_inputs_unavailable for %s at %s — no call", pair, as_of)
            continue

        confidence = compute_confidence(
            composite,
            rate_norm,
            cot_norm,
            pair=pair,
            special_signal=special_signal,
        )

        structural_instability = False
        gate_out = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol_exp,
                structural_instability=structural_instability,
                prior_regime_label=prior_regime,
                carry_risk_adjusted_chronological=(),
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
            pair=pair,
            composite=float(composite),
            z_tactical=rate_norm,
            z_structural=rate_z_structural_val,
            rate_direction=rate_dir,
            positioning_percentile=None,
            layer1_invalidated=bool(gate_out["invalidated"]),
        )

        rv_rank_layer3 = (
            float(all_rv_rank[full_idx]) if not np.isnan(all_rv_rank[full_idx]) else None
        )
        layer3_out = run_layer3_execution(
            layer2=layer2_out,
            spot=float(today_bar.close) if today_bar.close else None,
            spot_bars=window_bars,
            realized_vol_rank=rv_rank_layer3,
            risk_reversal_series_bps=(),
        )

        conviction_cap = 0.42 + 0.10 * float(layer2_out["conviction"])
        confidence = min(float(confidence), conviction_cap)

        snapshot = _build_historical_snapshot(
            pair=pair,
            as_of=as_of,
            full_idx=full_idx,
            all_sorted_dates=all_sorted_dates,
            spot_map=spot_map,
            yields_by_series=yields_by_series,
            sig_row={},
        )
        builder = RegimeCallBuilder(snapshot)

        signal_row = builder.build_signal_row(
            pair=pair,
            rate_spread_2y=rate_spread_2y,
            rate_spread_10y=rate_spread_10y,
            rate_spread_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_norm,
            rate_z_structural=rate_z_structural_val,
            z_blended=rate_norm,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=None,
            vol_norm=vol_norm,
            vol_expanding=vol_exp,
            oi_delta=None,
            oi_norm=None,
            special_signal=special_signal,
            structural_instability=structural_instability,
            breakeven_inflation_10y=bei,
            realized_vol_rank=layer3_out["realized_vol_rank"],
            skew_alignment=layer3_out["skew_alignment"],
        )
        signal_row.data_quality_notes = [
            "rate_inputs_unqualified",
            "rate_history_unavailable",
        ]
        if pair == "USDINR":
            signal_row.data_quality_notes.extend(FPI_UNAVAILABLE_NOTES)

        call = builder.build_regime_call(
            pair=pair,
            signal_row=signal_row,
            composite=composite,
            confidence=confidence,
            regime=regime,
            primary_driver=driver,
            layer2=layer2_out,
            layer3=layer3_out,
            rate_direction=rate_dir,
            cot_norm=None,
            vol_norm=vol_norm,
            vol_expanding=vol_exp,
            oi_norm=None,
            special_signal=special_signal,
            apply_dqs_cap=False,
            model_version=DIRECTIONAL_MODEL_VERSION,
            strategy_version=DIRECTIONAL_STRATEGY_VERSION,
            data_source="backtest",
        )
        call.regime_category = None

        results.append((signal_row, call))
        prior_regime = call.regime

        if len(results) % 500 == 0:
            logger.info("%s: %d days computed", pair, len(results))

    logger.info("%s: total computed %d days", pair, len(results))
    return results


def _load_signals_for_pair(pair: str, start: date, end: date) -> dict[date, dict[str, Any]]:
    """Load signal rows from DB indexed by date."""
    conn = _pg_conn()
    result = conn.run(
        "SELECT date, cot_percentile, realized_vol_5d, realized_vol_20d, "
        "implied_vol_30d, oi_delta, rate_z_tactical, rate_z_structural, z_blended, "
        "fpi_flow, ecb_balance_sheet, bund_btp_spread, "
        "cot_asset_mgr_net, cot_lev_money_net, cot_net_pos, "
        "cross_asset_vix, cross_asset_dxy, cross_asset_oil, "
        "cross_asset_gold, cross_asset_copper, cross_asset_stoxx, "
        "boj_policy_rate, india_vix, inr_forward_premium "
        "FROM signals WHERE pair = :pair AND date >= :start AND date <= :end ORDER BY date",
        pair=pair,
        start=start.isoformat(),
        end=end.isoformat(),
    )
    conn.close()
    out: dict[date, dict[str, Any]] = {}
    for r in result:
        d = r[0] if isinstance(r[0], date) else date.fromisoformat(str(r[0])[:10])
        out[d] = {
            "cot_percentile": float(r[1]) if r[1] is not None else None,
            "realized_vol_5d": float(r[2]) if r[2] is not None else None,
            "realized_vol_20d": float(r[3]) if r[3] is not None else None,
            "implied_vol_30d": float(r[4]) if r[4] is not None else None,
            "oi_delta": int(r[5]) if r[5] is not None else None,
            "rate_z_tactical": float(r[6]) if r[6] is not None else None,
            "rate_z_structural": float(r[7]) if r[7] is not None else None,
            "z_blended": float(r[8]) if r[8] is not None else None,
            "fpi_flow": float(r[9]) if r[9] is not None else None,
            "ecb_balance_sheet": float(r[10]) if r[10] is not None else None,
            "bund_btp_spread": float(r[11]) if r[11] is not None else None,
            "cot_asset_mgr_net": int(r[12]) if r[12] is not None else None,
            "cot_lev_money_net": int(r[13]) if r[13] is not None else None,
            "cot_net_pos": int(r[14]) if r[14] is not None else None,
            "cross_asset_vix": float(r[15]) if r[15] is not None else None,
            "cross_asset_dxy": float(r[16]) if r[16] is not None else None,
            "cross_asset_oil": float(r[17]) if r[17] is not None else None,
            "cross_asset_gold": float(r[18]) if r[18] is not None else None,
            "cross_asset_copper": float(r[19]) if r[19] is not None else None,
            "cross_asset_stoxx": float(r[20]) if r[20] is not None else None,
            "boj_policy_rate": float(r[21]) if r[21] is not None else None,
            "india_vix": float(r[22]) if r[22] is not None else None,
            "inr_forward_premium": float(r[23]) if r[23] is not None else None,
        }
    return out


def _build_cross_asset_from_signal(sig: dict[str, Any] | None) -> dict[str, Any]:
    if sig is None:
        return {}
    return {
        "vix": sig.get("cross_asset_vix"),
        "dxy": sig.get("cross_asset_dxy"),
        "oil": sig.get("cross_asset_oil"),
        "gold": sig.get("cross_asset_gold"),
        "copper": sig.get("cross_asset_copper"),
        "stoxx": sig.get("cross_asset_stoxx"),
    }


def _build_historical_snapshot(
    pair: str,
    as_of: date,
    full_idx: int,
    all_sorted_dates: list[date],
    spot_map: dict[date, SpotBar],
    yields_by_series: dict[str, dict[date, float]],
    sig_row: dict[str, Any],
) -> IngestionSnapshot:
    """Construct an ``IngestionSnapshot`` for a historical simulation date."""

    yields = _historical_rate_values(pair, as_of, yields_by_series)

    window_bars = [spot_map[d] for d in all_sorted_dates[max(0, full_idx - 2519) : full_idx + 1]]

    # Backfill snapshots are reconstructed from stored signals; COT rows are not
    # needed for assembly because the builder reads cot_percentile/cot_norm directly.
    cot_rows: list[CotRow] = []

    macro: dict[str, Any] = {
        "ecb_balance_sheet": sig_row.get("ecb_balance_sheet"),
        "bund_btp_spread": sig_row.get("bund_btp_spread"),
        "boj_policy_rate": sig_row.get("boj_policy_rate"),
        "india_vix": sig_row.get("india_vix"),
        "inr_forward_premium": sig_row.get("inr_forward_premium"),
    }

    # Fixed research-quality defaults: historical rows have no live DQS/stress computation.
    return IngestionSnapshot(
        date=as_of,
        spots={pair: window_bars},
        yields=yields,
        cot_rows=cot_rows,
        cross_asset=_build_cross_asset_from_signal(sig_row),
        macro=macro,
        dqs_score=0.85,
        stress_level="GREEN",
    )


def simulate_all_days_v2(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
    signals_by_date: dict[date, dict[str, Any]] | None = None,
    *,
    rate_observations_by_date: Mapping[date, Mapping[str, RateObservation]] | None = None,
    decision_times: Mapping[date, datetime] | None = None,
) -> list[tuple[SignalRow, RegimeCall]]:
    """Compute all regime calls using M.3 signal logic.

    Improvements over v1:
    - Unqualified rate normalization remains unavailable
    - COT loaded from signals table with smart-spread 70/30 blend
    - Special signal uses real macro data for EURUSD
    - Static directional weights; beta adaptation is disabled
    """
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
        all_rv20[j] = float(np.std(all_log_returns[j - 21 : j]) * np.sqrt(252) * 100)
        all_rv5[j] = float(np.std(all_log_returns[j - 5 : j]) * np.sqrt(252) * 100)

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
        tail = all_rv21_series[21 : j + 1]
        win = tail[-TRADING_DAYS_3Y_VOL_RANK:] if len(tail) > TRADING_DAYS_3Y_VOL_RANK else tail
        if len(win) >= 2:
            current = float(win[-1])
            hist = win[:-1]
            all_rv_rank[j] = empirical_cdf_rank(current, hist)

    # Load signals if not provided
    sig_map = signals_by_date or _load_signals_for_pair(pair, start, end)

    results: list[tuple[SignalRow, RegimeCall]] = []
    prior_regime: str | None = None

    for full_idx, as_of in date_indices:
        if full_idx < 60:
            continue

        today_bar = spot_map[as_of]
        window_bars = [
            spot_map[d] for d in all_sorted_dates[max(0, full_idx - 2519) : full_idx + 1]
        ]
        spot_closes = [b.close for b in window_bars]

        rate_values = _historical_rate_values(pair, as_of, yields_by_series)
        bei = rate_values.get("T10YIE")
        rate_spread_2y = qualified_two_year_spread(
            pair,
            (rate_observations_by_date or {}).get(as_of, {}),
            decision_at=(decision_times or {}).get(as_of),
        )
        rate_spread_10y = nominal_ten_year_context(pair, rate_values)
        rate_spread_10y_real = current_real_yield_spread(pair, rate_spread_10y, rate_values)
        rate_norm = None
        rate_z_structural_val = None
        rate_dir = rate_direction_from_spreads(
            rate_spread_2y, rate_spread_10y_real, z_tactical=rate_norm
        )

        rv20 = float(all_rv20[full_idx]) if not np.isnan(all_rv20[full_idx]) else None
        rv5 = float(all_rv5[full_idx]) if not np.isnan(all_rv5[full_idx]) else None
        vol_norm = all_vol_norm[full_idx]
        vol_exp = all_vol_exp[full_idx]

        # ── COT with smart spread (M.3.3) ────────────────────────────────────
        sig_row = sig_map.get(as_of, {})
        cot_pct = sig_row.get("cot_percentile")
        # Stored daily snapshots do not supply a homogeneous report history.
        cot_norm = normalize_cot_signal(cot_pct)
        if pair == "USDINR":
            cot_pct = None
            cot_norm = None

        # ── OI ───────────────────────────────────────────────────────────────
        oi_delta = sig_row.get("oi_delta")
        oi_norm = None
        # A change in contracts cannot reconstruct a level percentile.

        # ── Special signal with real macro data (M.3.1) ──────────────────────
        cross_for_special = _build_cross_asset_from_signal(sig_row)
        eur_kwargs: dict[str, Any] = {}
        if pair == "EURUSD":
            eur_kwargs = {
                "bund_btp_spread": sig_row.get("bund_btp_spread"),
                "ecb_balance_sheet": sig_row.get("ecb_balance_sheet"),
            }
        special_signal = compute_special_signal(pair, cross_for_special, **eur_kwargs)

        # ── FPI (USDINR only) ────────────────────────────────────────────────
        fpi_signal: float | None = None
        # Legacy scalar flows lack source/vintage evidence and are not republished.
        directional = directional_inputs(
            pair, rate=rate_norm, cot=cot_norm, special=special_signal, fpi=None
        )
        rate_norm, cot_norm = directional.rate, directional.cot
        special_signal = directional.special

        # Static directional reference; no contemporaneous-beta adaptation.
        composite = compute_composite(
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            pair=pair,
            special_signal=special_signal,
            fpi_signal=fpi_signal,
        )
        if composite is None:
            logger.debug("directional_inputs_unavailable for %s at %s — no call", pair, as_of)
            continue

        confidence = compute_confidence(
            composite,
            rate_norm,
            cot_norm,
            pair=pair,
            special_signal=special_signal,
        )

        structural_instability = False
        gate_out = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol_exp,
                structural_instability=structural_instability,
                prior_regime_label=prior_regime,
                carry_risk_adjusted_chronological=(),
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
            pair=pair,
            composite=float(composite),
            z_tactical=rate_norm,
            z_structural=rate_z_structural_val,
            rate_direction=rate_dir,
            positioning_percentile=cot_pct,
            layer1_invalidated=bool(gate_out["invalidated"]),
        )

        rv_rank_layer3 = (
            float(all_rv_rank[full_idx]) if not np.isnan(all_rv_rank[full_idx]) else None
        )
        layer3_out = run_layer3_execution(
            layer2=layer2_out,
            spot=float(today_bar.close) if today_bar.close else None,
            spot_bars=window_bars,
            realized_vol_rank=rv_rank_layer3,
            risk_reversal_series_bps=(),
        )

        conviction_cap = 0.42 + 0.10 * float(layer2_out["conviction"])
        confidence = min(float(confidence), conviction_cap)

        snapshot = _build_historical_snapshot(
            pair=pair,
            as_of=as_of,
            full_idx=full_idx,
            all_sorted_dates=all_sorted_dates,
            spot_map=spot_map,
            yields_by_series=yields_by_series,
            sig_row=sig_row,
        )
        builder = RegimeCallBuilder(snapshot)

        signal_row = builder.build_signal_row(
            pair=pair,
            rate_spread_2y=rate_spread_2y,
            rate_spread_10y=rate_spread_10y,
            rate_spread_10y_real=rate_spread_10y_real,
            rate_z_tactical=None,
            rate_z_structural=None,
            z_blended=None,
            cot_percentile=cot_pct,
            cot_norm=cot_norm,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=sig_row.get("implied_vol_30d"),
            vol_norm=vol_norm,
            vol_expanding=vol_exp,
            oi_delta=oi_delta,
            oi_norm=oi_norm,
            special_signal=special_signal,
            fpi_signal=fpi_signal,
            fpi_raw=None,
            structural_instability=structural_instability,
            breakeven_inflation_10y=bei,
            realized_vol_rank=layer3_out["realized_vol_rank"],
            skew_alignment=layer3_out["skew_alignment"],
        )
        signal_row.data_quality_notes = [
            "rate_inputs_unqualified",
            "rate_history_unavailable",
        ]
        if pair == "USDINR":
            signal_row.data_quality_notes.extend(FPI_UNAVAILABLE_NOTES)

        driver = "Static directional reference (unvalidated)"
        call = builder.build_regime_call(
            pair=pair,
            signal_row=signal_row,
            composite=composite,
            confidence=confidence,
            regime=regime,
            primary_driver=driver,
            layer2=layer2_out,
            layer3=layer3_out,
            rate_direction=rate_dir,
            cot_norm=cot_norm,
            vol_norm=vol_norm,
            vol_expanding=vol_exp,
            oi_norm=oi_norm,
            special_signal=special_signal,
            apply_dqs_cap=False,
            model_version=DIRECTIONAL_MODEL_VERSION,
            strategy_version=DIRECTIONAL_STRATEGY_VERSION,
            data_source="backtest",
        )

        results.append((signal_row, call))
        prior_regime = call.regime

        if len(results) % 500 == 0:
            logger.info("%s v2: %d days computed", pair, len(results))

    logger.info("%s v2: total computed %d days", pair, len(results))
    return results


def run_pair_simulation_v2(
    pair: str,
    start: date,
    end: date,
    yields_by_series: dict[str, dict[date, float]],
    signals_by_date: dict[date, dict[str, Any]] | None = None,
) -> int:
    logger.info("Simulating v2 %s from %s to %s", pair, start, end)
    results = simulate_all_days_v2(pair, start, end, yields_by_series, signals_by_date)
    _batch_write(pair, results)
    return len(results)


def _batch_write(pair: str, results: list[tuple[SignalRow, RegimeCall]]) -> None:
    writer.bulk_write_backfill_results(pair, results)


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
    parser.add_argument("--v2", action="store_true", help="Use M.3 signal logic")
    args = parser.parse_args()

    yields_by_series = _load_all_yields()
    if args.v2:
        count = run_pair_simulation_v2(
            args.pair,
            date.fromisoformat(args.start),
            date.fromisoformat(args.end),
            yields_by_series,
        )
    else:
        count = run_pair_simulation(
            args.pair,
            date.fromisoformat(args.start),
            date.fromisoformat(args.end),
            yields_by_series,
        )
    logger.info("Simulation complete: %d days", count)


if __name__ == "__main__":
    main()
