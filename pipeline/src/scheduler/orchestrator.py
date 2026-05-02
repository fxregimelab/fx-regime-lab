"""Daily and weekly pipeline orchestration."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, cast

from dotenv import load_dotenv

from src.ai.client import (
    desk_card_brief_fallback,
    generate_brief,
    generate_desk_card_brief_async,
    generate_event_brief,
    generate_global_macro_summary,
    summarize_weekly_memo_async,
)
from src.analysis.asymmetry import compute_pain_index
from src.analysis.event_risk import compute_event_risk_matrix
from src.analysis.markov import compute_time_decayed_markov
from src.analysis.systemic import (
    apply_cluster_to_telemetry,
    assign_apex_ranking,
    build_yesterday_rank_maps,
    compute_dollar_dominance_score,
    resolve_idiosyncratic_outlier,
    top_three_clustered,
)
from src.db import writer
from src.fetchers.async_engine import build_master_buffer
from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.fetchers.macro_calendar import fetch_macro_events
from src.fetchers.open_interest import compute_oi_delta_from_cot, compute_oi_from_cot
from src.fetchers.substack import fetch_latest_substack_memo
from src.fetchers.volatility import fetch_implied_vol, fetch_realized_vol
from src.regime.classifier import VOL_EXPANDING_SUFFIX, classify_regime
from src.regime.composite import (
    TRADING_DAYS_3Y,
    compute_composite,
    compute_dominance_scores,
    compute_dynamic_betas,
    dominance_top_family,
    get_primary_driver,
)
from src.regime.confidence import compute_confidence
from src.signals.cot import compute_cot_percentile, normalize_cot_signal
from src.signals.open_interest import compute_oi_signal
from src.signals.rate import (
    build_carry_history_from_rows,
    build_real_yield_10y_spread_history_from_rows,
    compute_risk_adjusted_carry,
    normalize_rate_signal,
    rate_direction_from_spreads,
    structural_instability_from_carry_history,
)
from src.signals.volatility import compute_vol_signal, is_vol_expanding
from src.types import PAIRS, CotRow, DeskOpenCardRow, RegimeCall, SignalRow, SpotBar, load_universe
from src.validation import ledger
from src.validation.backtest import validate_call
from src.validation.ingestion_buffer import validate_ingestion_buffer

logger = logging.getLogger(__name__)


async def _ingest_weekly_research_memo(iso_date: str) -> None:
    memo = fetch_latest_substack_memo()
    bullets = await summarize_weekly_memo_async(str(memo["raw_content"]), date_str=iso_date)
    writer.write_research_memo(
        date_str=str(memo["date"])[:10],
        title=str(memo["title"]),
        raw_content=str(memo["raw_content"]),
        ai_thesis_summary=bullets,
        link_url=str(memo["link_url"]),
    )


def get_regime_age(pair: str, current_regime: str, *, as_of: date) -> int:
    """Count consecutive days (incl. ``as_of``) the regime matches, scanning backward from latest.

    Vol-expanding suffix is stripped so a vol flag does not reset the streak.
    """

    def _norm_label(label: str) -> str:
        if VOL_EXPANDING_SUFFIX in label:
            return label.split(VOL_EXPANDING_SUFFIX, maxsplit=1)[0]
        return label

    target = _norm_label(current_regime)
    rows = writer.get_historical_regime_calls(pair, limit=5000)
    age = 0
    for row in reversed(rows):
        rd = date.fromisoformat(str(row["date"])[:10])
        if rd > as_of:
            continue
        if _norm_label(str(row["regime"])) == target:
            age += 1
        else:
            break
    return age


def _universe_yield_tickers(universe: dict[str, Any], pair: str) -> tuple[str | None, str | None]:
    meta = universe.get(pair)
    if not isinstance(meta, dict):
        return None, None
    tickers = meta.get("tickers") or {}
    b_raw, q_raw = tickers.get("yield_base"), tickers.get("yield_quote")
    return (
        b_raw if isinstance(b_raw, str) else None,
        q_raw if isinstance(q_raw, str) else None,
    )


def _rate_spread_2y_for_pair(
    pair: str,
    universe: dict[str, Any],
    yields_dict: dict[str, float | None],
) -> float | None:
    base_id, quote_id = _universe_yield_tickers(universe, pair)
    if base_id is None or quote_id is None:
        logger.warning("Universe missing yield_base/yield_quote for %s", pair)
        return None
    base_val = yields_dict.get(base_id)
    quote_val = yields_dict.get(quote_id)
    if base_val is None or quote_val is None:
        logger.warning(
            "Yield leg missing for %s (base %s=%s, quote %s=%s) — rate spread unavailable",
            pair,
            base_id,
            base_val,
            quote_id,
            quote_val,
        )
        return None
    return float(base_val) - float(quote_val)


def _rate_spread_10y_legacy(
    pair: str,
    yields_dict: dict[str, float | None],
) -> float | None:
    """10Y spread where legacy ``us_10y`` / ``*_10y`` legs exist (subset of pairs)."""

    us = yields_dict.get("us_10y")
    if us is None:
        return None
    if pair == "EURUSD":
        qk = "de_10y"
    elif pair == "USDJPY":
        qk = "jp_10y"
    elif pair == "USDINR":
        qk = "in_10y"
    else:
        return None
    qv = yields_dict.get(qk)
    if qv is None:
        return None
    return float(us) - float(qv)


try:
    from src.fetchers.polymarket import (
        get_active_economics_markets,
        polymarket_odds_json_for_prompt,
    )
except ImportError:  # pragma: no cover - optional module in some environments
    get_active_economics_markets = None  # type: ignore[assignment]
    polymarket_odds_json_for_prompt = None  # type: ignore[assignment]


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


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _polymarket_json_for_llm(markets: list[dict[str, Any]]) -> str:
    if polymarket_odds_json_for_prompt is not None:
        return polymarket_odds_json_for_prompt(markets)
    return "[]"


def _format_polymarket_context(markets: list[dict[str, Any]]) -> str:
    if not markets:
        return ""
    ranked = sorted(
        markets,
        key=lambda m: _to_float(
            m.get("volume")
            or m.get("volume_usd")
            or m.get("volumeNum")
            or m.get("volume24hr")
            or 0.0
        ),
        reverse=True,
    )
    parts: list[str] = []
    for idx, market in enumerate(ranked[:3], start=1):
        question = str(market.get("question") or market.get("title") or "Unknown market")
        volume_value = _to_float(
            market.get("volume")
            or market.get("volume_usd")
            or market.get("volumeNum")
            or market.get("volume24hr")
            or 0.0
        )
        parts.append(f"{idx}. {question} - Vol: ${volume_value:,.0f}")
    return f"Polymarket Odds: {' '.join(parts)}"


def _signal_row_from_db(row: dict[str, Any]) -> SignalRow:
    return SignalRow(
        pair=str(row["pair"]),
        date=date.fromisoformat(str(row["date"])[:10]),
        rate_diff_2y=row.get("rate_diff_2y"),
        rate_diff_10y=row.get("rate_diff_10y"),
        cot_percentile=row.get("cot_percentile"),
        realized_vol_20d=row.get("realized_vol_20d"),
        realized_vol_5d=row.get("realized_vol_5d"),
        implied_vol_30d=row.get("implied_vol_30d"),
        spot=row.get("spot"),
        day_change=row.get("day_change"),
        day_change_pct=row.get("day_change_pct"),
        cross_asset_vix=row.get("cross_asset_vix"),
        cross_asset_dxy=row.get("cross_asset_dxy"),
        cross_asset_oil=row.get("cross_asset_oil"),
        cross_asset_us10y=row.get("cross_asset_us10y"),
        cross_asset_gold=row.get("cross_asset_gold"),
        cross_asset_copper=row.get("cross_asset_copper"),
        cross_asset_stoxx=row.get("cross_asset_stoxx"),
        oi_delta=row.get("oi_delta"),
        structural_instability=bool(row.get("structural_instability", False)),
        breakeven_inflation_10y=row.get("breakeven_inflation_10y"),
        rate_diff_10y_real=row.get("rate_diff_10y_real"),
        rate_z_tactical=row.get("rate_z_tactical"),
        rate_z_structural=row.get("rate_z_structural"),
    )


def _regime_call_from_db(row: dict[str, Any]) -> RegimeCall:
    return RegimeCall(
        pair=str(row["pair"]),
        date=date.fromisoformat(str(row["date"])[:10]),
        regime=str(row.get("regime") or ""),
        confidence=float(row["confidence"] if row.get("confidence") is not None else 0.0),
        signal_composite=float(
            row["signal_composite"] if row.get("signal_composite") is not None else 0.0
        ),
        rate_signal=str(row.get("rate_signal") or "NEUTRAL"),
        primary_driver=str(row["primary_driver"]) if row.get("primary_driver") else None,
    )


def _first_todays_high_impact_matrix_for_pair(
    calendar_events: list[dict[str, Any]],
    *,
    pair: str,
    as_of: date,
) -> dict[str, Any] | None:
    """First HIGH calendar event today for pair: return its event_risk_matrices row if any."""
    iso = as_of.isoformat()
    for ev in calendar_events:
        if str(ev.get("impact")) != "HIGH":
            continue
        if str(ev.get("date"))[:10] != iso:
            continue
        if pair not in list(ev.get("pairs") or []):
            continue
        ev_name = str(ev.get("event") or "")
        if not ev_name:
            continue
        return writer.get_event_risk_matrix(iso, pair, ev_name)
    return None


def _upsert_macro_event_briefs(
    date_str: str,
    forward_days: int = 7,
    polymarket_context: str = "",
) -> None:
    start_d = date.fromisoformat(date_str)
    end_d = start_d + timedelta(days=forward_days)
    macro_rows = writer.list_high_impact_events_needing_brief(
        start_d.isoformat(),
        end_d.isoformat(),
    )
    for ev in macro_rows:
        ev_date = str(ev.get("date"))[:10]
        ev_name = str(ev.get("event"))
        pairs = list(ev.get("pairs") or PAIRS)
        try:
            pair_briefs: dict[str, str] = {}
            for pair in pairs:
                matrix_row = writer.get_event_risk_matrix(ev_date, pair, ev_name)
                if matrix_row is None:
                    logger.info(
                        "Skipping event brief matrix lookup miss for %s %s %s",
                        ev_date,
                        pair,
                        ev_name,
                    )
                    continue
                pair_briefs[pair] = generate_event_brief(
                    matrix_row,
                    ev_date,
                    polymarket_context=polymarket_context,
                )
            if pair_briefs:
                writer.update_macro_event_ai_brief(ev_date, ev_name, json.dumps(pair_briefs))
        except RuntimeError as exc:
            logger.warning("Stopping macro AI updates: %s", exc)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Macro event brief failed for %s %s: %s", ev_date, ev_name, exc)


def _upsert_pair_briefs_for_date(
    date_str: str,
    polymarket_context: str,
    *,
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> list[str]:
    pair_contexts: list[str] = []
    for pair in PAIRS:
        prior = writer.get_latest_regime_call(pair)
        if not prior:
            continue
        if str(prior.get("date"))[:10] != date_str:
            continue

        sig = writer.get_signal_for_pair_date(pair, date_str)
        if not sig:
            continue
        signal_row = _signal_row_from_db(sig)

        cached = writer.get_brief_for_date(pair, date_str)
        if cached:
            analysis = cached
        else:
            analysis = generate_brief(
                pair,
                str(prior["regime"]),
                float(prior["confidence"]),
                float(prior["signal_composite"]),
                signal_row,
                date_str,
                primary_driver=(
                    str(prior.get("primary_driver")) if prior.get("primary_driver") else None
                ),
                polymarket_context=polymarket_context,
                dollar_dominance_pct=dollar_dominance_pct,
                polymarket_odds_json=polymarket_odds_json,
            )
            writer.write_brief(
                date_str,
                pair,
                str(prior["regime"]),
                float(prior["confidence"]),
                float(prior["signal_composite"]),
                analysis,
                str(prior.get("primary_driver") or ""),
            )

        pair_contexts.append(
            f"{pair} regime={prior.get('regime')} conf={float(prior['confidence']):.2f} "
            f"driver={prior.get('primary_driver') or 'unknown'} "
            f"r2y={signal_row.rate_diff_2y} r10y={signal_row.rate_diff_10y} "
            f"oil={signal_row.cross_asset_oil} spot={signal_row.spot} brief={analysis[:180]}"
        )
    return pair_contexts


def run_daily(date_str: str | None = None) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    universe = load_universe()
    buffer = asyncio.run(build_master_buffer())
    gate = validate_ingestion_buffer(buffer, universe=universe)
    if gate.telemetry_status == "OFFLINE":
        logger.critical(
            "Daily run aborted: telemetry OFFLINE — spot ingestion quorum breach "
            "(refusing to write signals/regime to protect systemic matrix)"
        )
        return
    buffer = gate.buffer

    spots_raw = buffer.get(KEY_FX_SPOT)
    spots: dict[str, Sequence[SpotBar]] = (
        cast(dict[str, Sequence[SpotBar]], spots_raw) if isinstance(spots_raw, dict) else {}
    )

    yields_dict_raw = buffer.get(KEY_YIELDS)
    yields_dict: dict[str, float | None] = (
        yields_dict_raw if isinstance(yields_dict_raw, dict) else {}
    )

    cot_raw = buffer.get(KEY_COT)
    cot_rows: list[CotRow] = cast(list[CotRow], cot_raw) if isinstance(cot_raw, list) else []

    cross_raw = buffer.get(KEY_CROSS_ASSET)
    cross: dict[str, float | None] = (
        cross_raw
        if isinstance(cross_raw, dict)
        else {
            "vix": None,
            "dxy": None,
            "oil": None,
            "gold": None,
            "copper": None,
            "stoxx": None,
        }
    )

    logger.info("Cross-asset snapshot: %s", cross)
    vol_data = fetch_realized_vol(spots)

    events = fetch_macro_events()
    writer.write_macro_events(events)

    pending_desk_cards: list[dict[str, Any]] = []

    for pair in PAIRS:
        prior_db = writer.get_latest_regime_call(pair)
        historical_rows = writer.get_historical_signals(pair, limit=1260)
        historical_carry = build_carry_history_from_rows(historical_rows, max_points=1260)
        historical_real_10y = build_real_yield_10y_spread_history_from_rows(
            historical_rows, max_points=1260
        )
        structural_instability = structural_instability_from_carry_history(historical_carry)
        historical_us10y = [
            float(v)
            for row in historical_rows
            if (v := row.get("cross_asset_us10y")) is not None
        ]
        historical_oi_delta = [
            int(v)
            for row in historical_rows
            if (v := row.get("oi_delta")) is not None
        ]
        historical_rv5 = [
            float(v)
            for row in historical_rows
            if (v := row.get("realized_vol_5d")) is not None
        ]
        spot_bars = spots.get(pair, [])
        if not spot_bars:
            logger.warning("No spot bars for %s — skipping", pair)
            continue

        today_bar = spot_bars[-1]
        yest_bar = spot_bars[-2] if len(spot_bars) >= 2 else today_bar

        rate_spread_2y = _rate_spread_2y_for_pair(pair, universe, yields_dict)
        if rate_spread_2y is None:
            logger.warning(
                "Rate 2Y spread unavailable for %s — dominance scores computed without rate carry",
                pair,
            )
        rate_spread_10y = _rate_spread_10y_legacy(pair, yields_dict)
        bei_raw = yields_dict.get("T10YIE") if isinstance(yields_dict, dict) else None
        bei = float(bei_raw) if bei_raw is not None else None
        rate_spread_10y_real = (
            None
            if rate_spread_10y is None
            else (float(rate_spread_10y) - bei if bei is not None else float(rate_spread_10y))
        )
        rate_dir = rate_direction_from_spreads(rate_spread_2y, rate_spread_10y_real)
        rate_spread_for_norm = rate_spread_2y if rate_spread_2y is not None else rate_spread_10y

        cot_pct = compute_cot_percentile(cot_rows, pair)
        cot_norm = normalize_cot_signal(cot_pct) if cot_pct is not None else None

        rv = vol_data.get(pair, {})
        rv5 = rv.get("realized_vol_5d")
        rv20 = rv.get("realized_vol_20d")
        risk_adjusted_carry = compute_risk_adjusted_carry(rate_spread_2y, rv20, pair)
        if risk_adjusted_carry is not None:
            rate_spread_for_norm = risk_adjusted_carry
        rate_norm_z = None
        if rate_spread_for_norm is not None:
            struct_spread = rate_spread_10y_real
            struct_hist = (
                historical_real_10y
                if struct_spread is not None and len(historical_real_10y) >= 5
                else None
            )
            rate_norm_z = normalize_rate_signal(
                float(rate_spread_for_norm),
                pair,
                historical_carry,
                spread_structural=struct_spread,
                historical_structural=struct_hist,
            )
        rate_norm = rate_norm_z.z_tactical if rate_norm_z is not None else None
        rate_z_structural_val = (
            rate_norm_z.z_structural if rate_norm_z is not None else None
        )
        vol_90th = _percentile(historical_rv5, 0.90) if historical_rv5 else None
        vol_norm = compute_vol_signal(rv5, rv20, vol_90th)
        vol_exp = (
            is_vol_expanding(rv5, vol_90th)
            if rv5 is not None and vol_90th is not None
            else False
        )

        oi_pct = compute_oi_from_cot(cot_rows, pair)
        oi_delta = compute_oi_delta_from_cot(cot_rows, pair)
        if oi_delta is None and historical_oi_delta:
            oi_delta = historical_oi_delta[0]
            logger.warning(
                "OI delta unavailable for %s; using latest historical value %s",
                pair,
                oi_delta,
            )
        oi_norm = compute_oi_signal(oi_pct)
        betas_5y = compute_dynamic_betas(historical_rows)
        betas_3y: dict[str, float] | None
        if len(historical_rows) >= TRADING_DAYS_3Y:
            betas_3y = compute_dynamic_betas(historical_rows[:TRADING_DAYS_3Y])
        else:
            betas_3y = None
            logger.info(
                "parameter_instability skipped for %s: history %s < %s sessions",
                pair,
                len(historical_rows),
                TRADING_DAYS_3Y,
            )
        top_5y = dominance_top_family(betas_5y, rate_norm, cot_norm, vol_norm, oi_norm)
        top_3y = (
            dominance_top_family(betas_3y, rate_norm, cot_norm, vol_norm, oi_norm)
            if betas_3y is not None
            else None
        )
        parameter_instability = (
            top_5y is not None
            and top_3y is not None
            and top_5y != top_3y
        )
        dominance_scores = compute_dominance_scores(
            rate_norm=rate_norm,
            cot_norm=cot_norm,
            vol_norm=vol_norm,
            oi_norm=oi_norm,
            betas=betas_5y,
        )
        composite = compute_composite(rate_norm, cot_norm, vol_norm, oi_norm)
        if composite is None:
            logger.warning("Not enough data for %s — skipping", pair)
            continue

        confidence = compute_confidence(composite, rate_norm, cot_norm)
        if pair == "USDINR" and cot_pct is None:
            # Best-effort mode when INR COT is unavailable: keep call, reduce confidence.
            confidence = max(0.40, confidence - 0.15)
        driver = get_primary_driver(betas_5y)
        driver_family = max(
            ("rate", "cot", "vol", "oi"),
            key=lambda f: abs(float(betas_5y.get(f, 0.0))),
        )
        logger.info(
            "pair=%s primary_driver=%s EMA_Spearman_Beta=%.4f",
            pair,
            driver,
            float(betas_5y.get(driver_family, 0.0)),
        )
        regime = classify_regime(composite, pair, vol_expanding=vol_exp)

        day_change = today_bar.close - yest_bar.close
        day_chg_pct = (day_change / yest_bar.close * 100) if yest_bar.close else 0.0
        iv = fetch_implied_vol(pair)

        us10y_value = yields_dict.get("us_10y")
        if us10y_value is None and historical_us10y:
            us10y_value = historical_us10y[0]
            logger.warning(
                "US10Y missing for %s; using latest historical value %.4f",
                pair,
                us10y_value,
            )

        signal_row = SignalRow(
            pair=pair,
            date=today_bar.date,
            rate_diff_2y=rate_spread_2y,
            rate_diff_10y=rate_spread_10y,
            cot_percentile=cot_pct,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=iv,
            spot=today_bar.close,
            day_change=day_change,
            day_change_pct=day_chg_pct,
            cross_asset_vix=cross.get("vix"),
            cross_asset_dxy=cross.get("dxy"),
            cross_asset_oil=cross.get("oil"),
            cross_asset_us10y=us10y_value,
            cross_asset_gold=cross.get("gold"),
            cross_asset_copper=cross.get("copper"),
            cross_asset_stoxx=cross.get("stoxx"),
            oi_delta=oi_delta,
            structural_instability=structural_instability,
            breakeven_inflation_10y=bei,
            rate_diff_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_norm,
            rate_z_structural=rate_z_structural_val,
        )

        if prior_db and str(prior_db.get("date"))[:10] != today_bar.date.isoformat():
            prior_signal = writer.get_signal_for_pair_date(pair, str(prior_db.get("date"))[:10])
            prior_realized_vol_20d = (
                float(prior_signal["realized_vol_20d"])
                if prior_signal and prior_signal.get("realized_vol_20d") is not None
                else None
            )
            val_row = validate_call(
                _regime_call_from_db(prior_db),
                spots,
                realized_vol_20d=prior_realized_vol_20d,
            )
            writer.write_validation_row(val_row)

        writer.write_signal_row(signal_row)

        call = RegimeCall(
            pair=pair,
            date=today_bar.date,
            regime=regime,
            confidence=confidence,
            signal_composite=composite,
            rate_signal=rate_dir,
            primary_driver=driver,
        )
        writer.write_regime_call(call)
        ledger.log_initial_signal(
            pair=pair,
            target_date=today_bar.date,
            regime=call.regime,
            primary_driver=str(call.primary_driver or ""),
            direction=call.rate_signal,
            entry_close=float(today_bar.close),
            confidence=float(call.confidence),
        )

        try:
            recent_closes = [float(bar.close) for bar in spot_bars[-10:]]
            if len(recent_closes) >= 6 and recent_closes[-6] != 0:
                current_trend_5d = (
                    (recent_closes[-1] / recent_closes[-6]) - 1.0
                ) * 100.0
            else:
                current_trend_5d = 0.0
            analog_rpc = writer.get_rpc_historical_analogs(
                pair,
                today_bar.date.isoformat(),
                current_trend_5d,
                float(composite),
            )
            if analog_rpc:
                payload_analogs: list[Mapping[str, Any]] = []
                for r in analog_rpc:
                    md = r.get("match_date")
                    match_date_str = str(md)[:10] if md is not None else ""
                    payload_analogs.append(
                        {
                            "as_of_date": today_bar.date.isoformat(),
                            "pair": pair,
                            "rank": int(r.get("rank", 0)),
                            "match_date": match_date_str,
                            "match_score": float(r.get("match_score", 0.0)),
                            "forward_30d_return": r.get("forward_30d_return"),
                            "regime_stability": r.get("regime_stability"),
                            "context_label": r.get("context_label"),
                            "current_trend_5d": r.get("current_trend_5d"),
                            "matched_trend_5d": r.get("matched_trend_5d"),
                            "current_composite": r.get("current_composite"),
                        }
                    )
                writer.write_research_analogs(payload_analogs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analog RPC failed for %s: %s", pair, exc)

        carry_by_date: dict[date, float] = {}
        for row in historical_rows:
            rd = row.get("date")
            if rd is None:
                continue
            try:
                d_co = date.fromisoformat(str(rd)[:10])
            except ValueError:
                continue
            r2c = row.get("rate_diff_2y")
            if r2c is not None:
                carry_by_date[d_co] = float(r2c)
        if rate_spread_2y is not None:
            carry_by_date[today_bar.date] = float(rate_spread_2y)

        try:
            pain = None
            pain = compute_pain_index(
                pair=pair,
                as_of_date=today_bar.date,
                regime=regime,
                cot_percentile=cot_pct,
                cot_rows=cot_rows,
                spot_bars=spot_bars,
                realized_vol_20d=rv20,
                implied_vol_30d=iv,
                carry_by_date=carry_by_date,
            )
            logger.info("Pain index (%s): %s", pair, pain)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pain index failed for %s: %s", pair, exc)

        try:
            markov = None
            markov = compute_time_decayed_markov(
                pair=pair,
                as_of_date=today_bar.date,
                current_regime=regime,
                historical_prices=writer.get_historical_prices(pair, limit=5000),
                regime_calls=writer.get_historical_regime_calls(pair, limit=5000),
                forward_days=5,
                half_life_years=3.0,
            )
            logger.info("Markov transition (%s): %s", pair, markov)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Markov analysis failed for %s: %s", pair, exc)

        dominance_array = [
            {
                "rank": row.rank,
                "signal_family": row.signal_family,
                "signal_strength": row.signal_strength,
                "beta": row.beta,
                "dominance_score": row.dominance_score,
            }
            for row in dominance_scores
        ]
        markov_probabilities = (
            {
                "continuation_probability": markov.continuation_probability,
                "transitions": markov.transition_probabilities,
                "weighted_sample_size": markov.weighted_sample_size,
            }
            if markov is not None
            else {"continuation_probability": 0.0, "transitions": {}, "weighted_sample_size": 0.0}
        )
        telemetry_audit = {
            "cot_is_stale": pain.cot_is_stale if pain is not None else True,
            "cot_age_days": pain.cot_age_days if pain is not None else None,
            "underwater_triggered": pain.underwater_triggered if pain is not None else False,
            "weighted_sample_size": (
                markov.weighted_sample_size if markov is not None else 0.0
            ),
            "parameter_instability": parameter_instability,
        }
        todays_event_matrix = _first_todays_high_impact_matrix_for_pair(
            events,
            pair=pair,
            as_of=today_bar.date,
        )
        regime_age = get_regime_age(pair, regime, as_of=today_bar.date)
        pending_desk_cards.append(
            {
                "confidence": confidence,
                "brief_kw": {
                    "pair": pair,
                    "regime": regime,
                    "date_str": today_bar.date.isoformat(),
                    "primary_driver": driver,
                    "pain_index": pain.pain_index if pain is not None else None,
                    "todays_event_matrix": todays_event_matrix,
                    "dollar_dominance_score": None,
                    "dollar_bias": None,
                },
                "card": {
                    "date": today_bar.date,
                    "pair": pair,
                    "structural_regime": regime,
                    "dominance_array": dominance_array,
                    "pain_index": pain.pain_index if pain is not None else None,
                    "markov_probabilities": markov_probabilities,
                    "telemetry_audit": telemetry_audit,
                    "invalidation_triggered": False,
                    "telemetry_status": "ONLINE",
                    "regime_age": regime_age,
                },
            }
        )

    if pending_desk_cards:
        pair_regimes_today = {
            str(item["card"]["pair"]): str(item["card"]["structural_regime"])
            for item in pending_desk_cards
        }
        dollar_score, dollar_bias = compute_dollar_dominance_score(pair_regimes_today)
        for item in pending_desk_cards:
            bkw = cast(dict[str, Any], item["brief_kw"])
            bkw["dollar_dominance_score"] = dollar_score
            bkw["dollar_bias"] = dollar_bias

    if pending_desk_cards:
        ref_raw = pending_desk_cards[0]["card"]["date"]
        ref_date = ref_raw if isinstance(ref_raw, date) else date.fromisoformat(str(ref_raw)[:10])
        yesterday = (ref_date - timedelta(days=1)).isoformat()
        y_rows = writer.get_desk_open_cards_for_date(yesterday)
        yb_rank, yb_apex, incumbent = build_yesterday_rank_maps(y_rows)
        inc_apex = yb_apex.get(incumbent) if incumbent else None

        pairs_today = [str(item["card"]["pair"]) for item in pending_desk_cards]
        conf_map = {
            str(item["card"]["pair"]): float(item["confidence"]) for item in pending_desk_cards
        }
        pain_map = {
            str(item["card"]["pair"]): cast(float | None, item["card"].get("pain_index"))
            for item in pending_desk_cards
        }

        ranking_results = assign_apex_ranking(
            pairs=pairs_today,
            confidences=conf_map,
            pain_indices=pain_map,
            yesterday_rank_by_pair=yb_rank,
            yesterday_incumbent=incumbent,
            yesterday_incumbent_apex=inc_apex,
        )
        by_apex = {r.pair: r for r in ranking_results}

        matrix: dict[str, dict[str, float]] = {}
        try:
            matrix = writer.get_rpc_g10_correlation_matrix()
        except Exception as exc:  # noqa: BLE001
            logger.warning("G10 correlation matrix RPC failed: %s", exc)

        systemic_cluster = False
        if len(ranking_results) >= 3:
            systemic_cluster = top_three_clustered(
                (ranking_results[0].pair, ranking_results[1].pair, ranking_results[2].pair),
                matrix,
            )

        if ranking_results:
            apex_leader = ranking_results[0]
            logger.info(
                "[ APEX TARGET IDENTIFIED: %s | SCORE: %.4f | STATUS: %s ]",
                apex_leader.pair,
                apex_leader.apex_score,
                "Cluster" if systemic_cluster else "Consensus",
            )

        for item in pending_desk_cards:
            pair_key = str(item["card"]["pair"])
            r_inst = by_apex.get(pair_key)
            if r_inst is not None:
                ta = cast(dict[str, Any], item["card"]["telemetry_audit"])
                item["card"]["telemetry_audit"] = apply_cluster_to_telemetry(ta, systemic_cluster)

        async def _batch_desk_briefs() -> list[Any]:
            return await asyncio.gather(
                *[
                    generate_desk_card_brief_async(**cast(dict[str, Any], item["brief_kw"]))
                    for item in pending_desk_cards
                ],
                return_exceptions=True,
            )

        brief_outcomes = asyncio.run(_batch_desk_briefs())
        bulk_desk: list[DeskOpenCardRow] = []
        for idx, item in enumerate(pending_desk_cards):
            raw_brief = brief_outcomes[idx]
            bkw = cast(dict[str, Any], item["brief_kw"])
            card = cast(dict[str, Any], item["card"])
            human_grounding = bool(writer.get_latest_research_memo_thesis_bullets())
            if isinstance(raw_brief, Exception):
                logger.warning(
                    "Desk card async failed for %s: %s",
                    bkw.get("pair"),
                    raw_brief,
                )
                ai_brief = desk_card_brief_fallback(
                    regime=str(bkw.get("regime") or ""),
                    primary_driver=bkw.get("primary_driver"),
                    pain_index=bkw.get("pain_index"),
                    todays_event_matrix=bkw.get("todays_event_matrix"),
                    dollar_dominance_score=bkw.get("dollar_dominance_score"),
                    dollar_bias=bkw.get("dollar_bias"),
                )
            else:
                brief_pair = cast(tuple[str, bool], raw_brief)
                ai_brief = brief_pair[0]
                human_grounding = brief_pair[1]
            telemetry_merged = dict(cast(dict[str, Any], card["telemetry_audit"]))
            telemetry_merged["human_grounding_active"] = human_grounding
            pair_key = str(card["pair"])
            r_inst = by_apex.get(pair_key)
            bulk_desk.append(
                DeskOpenCardRow(
                    date=card["date"],
                    pair=pair_key,
                    structural_regime=str(card["structural_regime"]),
                    dominance_array=cast(list[dict[str, Any]], card["dominance_array"]),
                    pain_index=card.get("pain_index"),
                    markov_probabilities=cast(dict[str, Any], card["markov_probabilities"]),
                    ai_brief=ai_brief,
                    telemetry_audit=telemetry_merged,
                    invalidation_triggered=bool(card.get("invalidation_triggered", False)),
                    telemetry_status=str(card.get("telemetry_status") or "ONLINE"),
                    global_rank=r_inst.global_rank if r_inst is not None else None,
                    apex_score=r_inst.apex_score if r_inst is not None else None,
                    regime_age=cast(int | None, card.get("regime_age")),
                )
            )
        writer.write_desk_open_cards_bulk(bulk_desk)

    run_as_of = date.fromisoformat(date_str[:10])
    for mtm_pair in PAIRS:
        try:
            ledger.mark_to_market_ledger(
                mtm_pair,
                writer.get_historical_prices(mtm_pair, limit=600),
                as_of_date=run_as_of,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alpha ledger MTM failed for %s: %s", mtm_pair, exc)

    markets: list[dict[str, Any]] = []
    polymarket_context = ""
    if get_active_economics_markets is not None:
        try:
            markets = get_active_economics_markets()
            polymarket_context = _format_polymarket_context(markets)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Polymarket fetch failed during daily summary: %s", exc)

    pair_regimes: dict[str, str] = {}
    for p in PAIRS:
        rc = writer.get_latest_regime_call(p)
        if rc is None:
            continue
        if str(rc.get("date") or "")[:10] != date_str:
            continue
        pair_regimes[p] = str(rc.get("regime") or "")

    dscore, _bias = compute_dollar_dominance_score(pair_regimes)
    dollar_pct = float(dscore) * 100.0

    corr_20: dict[str, float | None] = {}
    corr_60: dict[str, float | None] = {}
    for p in PAIRS:
        try:
            corr_20[p] = writer.get_rpc_calculate_dual_correlation(p, 20)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Dual correlation 20d failed for %s: %s", p, exc)
            corr_20[p] = None
        try:
            corr_60[p] = writer.get_rpc_calculate_dual_correlation(p, 60)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Dual correlation 60d failed for %s: %s", p, exc)
            corr_60[p] = None

    outlier_pair = resolve_idiosyncratic_outlier(PAIRS, corr_20, corr_60)

    top_pm: list[dict[str, Any]] = []
    for m in sorted(
        markets,
        key=lambda x: float(x.get("volume_usd") or 0.0),
        reverse=True,
    )[:3]:
        top_pm.append(
            {
                "label": str(m.get("question") or "")[:96],
                "prob": m.get("probability"),
                "volume_usd": m.get("volume_usd"),
            }
        )

    sentiment_json: dict[str, Any] = {
        "polymarket_top3": top_pm,
        "dual_correlation": {"20d": corr_20, "60d": corr_60},
    }

    pm_json = _polymarket_json_for_llm(markets)
    pair_contexts = _upsert_pair_briefs_for_date(
        date_str,
        polymarket_context,
        dollar_dominance_pct=dollar_pct,
        polymarket_odds_json=pm_json,
    )
    if pair_contexts:
        global_summary = generate_global_macro_summary(
            date_str=date_str,
            pair_contexts=pair_contexts,
            macro_context=polymarket_context,
            dollar_dominance_pct=dollar_pct,
            polymarket_odds_json=pm_json,
        )
    else:
        global_summary = (
            "Insufficient pair briefs for unified summary; systemic telemetry still updated."
        )
    writer.write_brief_log(
        date_str,
        global_summary,
        polymarket_context,
        dollar_dominance=dollar_pct,
        idiosyncratic_outlier=outlier_pair,
        sentiment_json=sentiment_json,
    )

    # Populate macro event briefs for the next 3 days immediately
    _upsert_macro_event_briefs(date_str, forward_days=3, polymarket_context=polymarket_context)

    logger.info("Daily run complete for %s", date_str)


def run_weekly(date_str: str | None = None) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    load_universe()

    markets: list[dict[str, Any]] = []
    polymarket_context = ""
    if get_active_economics_markets is not None:
        try:
            markets = get_active_economics_markets()
            polymarket_context = _format_polymarket_context(markets)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Polymarket fetch failed: %s", exc)

    weekly_events = fetch_macro_events(forward_days=7)
    writer.write_macro_events(weekly_events)
    high_impact_events = [ev for ev in weekly_events if str(ev.get("impact")) == "HIGH"]
    pure_date_universe = writer.get_historical_macro_surprises_date_universe(limit=50000)

    matrix_rows: list[dict[str, Any]] = []
    for event in high_impact_events:
        event_name = str(event.get("event", ""))
        event_date_raw = event.get("date")
        if not event_name or event_date_raw is None:
            continue
        try:
            event_date = date.fromisoformat(str(event_date_raw)[:10])
        except ValueError:
            logger.warning("Skipping malformed event date for %s: %s", event_name, event_date_raw)
            continue

        for pair in PAIRS:
            try:
                latest_call = writer.get_latest_regime_call(pair)
                if latest_call is None:
                    continue
                active_regime_raw = latest_call.get("regime")
                if active_regime_raw is None:
                    continue
                active_regime = str(active_regime_raw)
                historical_prices = writer.get_historical_prices(pair, limit=10000)
                historical_regime_calls = writer.get_historical_regime_calls(pair, limit=5000)
                historical_surprises = writer.get_historical_macro_surprises(event_name)
                risk = compute_event_risk_matrix(
                    pair=pair,
                    event_name=event_name,
                    target_date=event_date,
                    current_regime=active_regime,
                    historical_prices=historical_prices,
                    historical_surprises=historical_surprises,
                    regime_calls=historical_regime_calls,
                    all_surprises_for_pure_dates=pure_date_universe,
                )
                if risk is not None:
                    matrix_rows.append(asdict(risk))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Event risk matrix computation failed for %s %s: %s",
                    pair,
                    event_name,
                    exc,
                )

    writer.write_event_risk_matrices(matrix_rows)

    pm_json_w = _polymarket_json_for_llm(markets)
    pair_regimes_w: dict[str, str] = {}
    for p in PAIRS:
        rc = writer.get_latest_regime_call(p)
        if rc is None:
            continue
        pair_regimes_w[p] = str(rc.get("regime") or "")
    dscore_w, _ = compute_dollar_dominance_score(pair_regimes_w)
    dollar_pct_w = float(dscore_w) * 100.0
    _upsert_pair_briefs_for_date(
        date_str,
        polymarket_context,
        dollar_dominance_pct=dollar_pct_w,
        polymarket_odds_json=pm_json_w,
    )
    _upsert_macro_event_briefs(date_str, forward_days=7, polymarket_context=polymarket_context)

    try:
        asyncio.run(_ingest_weekly_research_memo(date_str))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Weekly research memo ingestion failed: %s", exc)

    logger.info("Weekly run complete for %s", date_str)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    _m = sys.argv[1] if len(sys.argv) > 1 else "daily"
    (run_weekly if _m == "weekly" else run_daily)()
