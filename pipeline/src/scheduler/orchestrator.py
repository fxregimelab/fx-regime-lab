"""
@agent_context: High-level Prefect workflow orchestrator for daily and weekly
FX regime classification and intelligence pipelines.
@allowed_imports: [asyncio, logging, os, sys, collections.abc, dataclasses,
    datetime, typing, dotenv, prefect, src.*]
@forbidden_imports: []
@obsidian_link: [[Orchestration#Pipeline Flow]]
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Literal, cast

# ── Prefect managed worker patch ──────────────────────────────────────────────
# Prefect's managed worker base images currently ship with a broken prefect
# install where task_engine.py expects internal symbols that results.py doesn't
# define. We inject all missing internals at import time so the flow runner
# process sees them before any @task-decorated function is called.
import prefect.results as _pr
from dotenv import load_dotenv
from prefect import flow, task

if not hasattr(_pr, "_has_current_run_context"):
    def _has_current_run_context() -> bool:
        from prefect.context import FlowRunContext, TaskRunContext
        return TaskRunContext.get() is not None or FlowRunContext.get() is not None

    _pr._has_current_run_context = _has_current_run_context  # type: ignore[attr-defined]

if not hasattr(_pr, "get_current_settings"):
    def get_current_settings():
        from prefect.context import SettingsContext
        from prefect.settings import Settings
        settings_context = SettingsContext.get()
        if settings_context is not None:
            return settings_context.settings
        return Settings()

    _pr.get_current_settings = get_current_settings  # type: ignore[attr-defined]

if not hasattr(_pr, "get_default_persist_setting"):
    def get_default_persist_setting() -> bool:
        return _pr.get_current_settings().results.persist_by_default

    _pr.get_default_persist_setting = get_default_persist_setting  # type: ignore[attr-defined]

if not hasattr(_pr, "_read_server_default_result_storage_block_id"):
    from uuid import UUID
    def _read_server_default_result_storage_block_id() -> UUID | None:
        import httpx
        from prefect.client.orchestration import get_client
        from prefect.exceptions import PrefectHTTPStatusError
        try:
            client = get_client(sync_client=True)
            configuration = client.read_server_default_result_storage()
        except (PrefectHTTPStatusError, httpx.HTTPError, RuntimeError, ValueError):
            return None
        return configuration.default_result_storage_block_id

    _pr._read_server_default_result_storage_block_id = _read_server_default_result_storage_block_id  # type: ignore[attr-defined]

if not hasattr(_pr, "_aread_server_default_result_storage_block_id"):
    from uuid import UUID
    async def _aread_server_default_result_storage_block_id() -> UUID | None:
        import httpx
        from prefect.client.orchestration import get_client
        from prefect.exceptions import PrefectHTTPStatusError
        try:
            client = get_client()
            configuration = await client.read_server_default_result_storage()
        except (PrefectHTTPStatusError, httpx.HTTPError, RuntimeError, ValueError):
            return None
        return configuration.default_result_storage_block_id

    _pr._aread_server_default_result_storage_block_id = (  # type: ignore[attr-defined]
        _aread_server_default_result_storage_block_id
    )

if not hasattr(_pr, "_get_default_persist_result"):
    def _get_default_persist_result() -> bool:
        persist_result = _pr.should_persist_result()
        if persist_result or _pr._has_current_run_context():
            return persist_result
        default_block = _pr.get_current_settings().results.default_storage_block
        if default_block is not None:
            return True
        return _pr._read_server_default_result_storage_block_id() is not None

    _pr._get_default_persist_result = _get_default_persist_result  # type: ignore[attr-defined]

if not hasattr(_pr, "_aget_default_persist_result"):
    async def _aget_default_persist_result() -> bool:
        persist_result = _pr.should_persist_result()
        if persist_result or _pr._has_current_run_context():
            return persist_result
        default_block = _pr.get_current_settings().results.default_storage_block
        if default_block is not None:
            return True
        return await _pr._aread_server_default_result_storage_block_id() is not None

    _pr._aget_default_persist_result = _aget_default_persist_result  # type: ignore[attr-defined]
# ──────────────────────────────────────────────────────────────────────────────

from src.ai.client import desk_card_brief_fallback
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
from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.core.regime_persist import persist_regime_call
from src.db import writer
from src.fetchers.async_engine import build_master_buffer
from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.fetchers.cross_asset import fetch_india_vix, fetch_inr_forward_premium
from src.fetchers.fpi_india import fetch_fpi_flows
from src.fetchers.macro_calendar import fetch_macro_events
from src.fetchers.open_interest import compute_oi_delta_from_cot, compute_oi_from_cot
from src.fetchers.substack import fetch_latest_substack_memo
from src.fetchers.volatility import fetch_implied_vol, fetch_realized_vol
from src.fetchers.yields import (
    fetch_boj_policy_rate,
    fetch_bund_btp_spread,
    fetch_ecb_balance_sheet,
)
from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.monitoring.alerts import (
    alert_on_low_dqs,
    send_success_heartbeat,
)
from src.regime.classifier import (
    VOL_EXPANDING_SUFFIX,
    classify_regime_layer1,
)
from src.regime.composite import (
    TRADING_DAYS_3Y,
    _redundancy_penalty,
    compute_composite,
    compute_dominance_scores,
    compute_dynamic_betas,
    dominance_top_family,
    get_primary_driver,
)
from src.regime.confidence import compute_confidence
from src.signals.cot import (
    compute_cot_percentile,
    compute_cot_smart_spread_percentile,
    normalize_cot_signal,
)
from src.signals.fpi import normalize_fpi_signal
from src.signals.intervention import compute_intervention_proximity
from src.signals.open_interest import compute_oi_signal
from src.signals.rate import (
    build_carry_history_from_rows,
    build_real_yield_10y_spread_history_from_rows,
    compute_risk_adjusted_carry_v2,
    normalize_rate_signal,
    rate_direction_from_spreads,
    structural_instability_from_carry_history,
)
from src.signals.special import compute_special_signal
from src.signals.volatility import (
    TRADING_DAYS_3Y_VOL_RANK,
    compute_realized_vol_rank_from_closes,
    compute_rvol,
    compute_vol_signal,
    is_vol_expanding,
)
from src.types import (
    PAIRS,
    CotRow,
    DeskOpenCardRow,
    Layer1ClassifierContext,
    Layer3EntryTiming,
    Layer3PositionSize,
    RegimeCall,
    SignalRow,
    SpotBar,
    load_universe,
)
from src.validation import ledger
from src.validation.engine import run_validation
from src.validation.ingestion_buffer import (
    compute_dqs,
    fx_pairs_from_universe,
    validate_ingestion_buffer,
)

logger = logging.getLogger(__name__)


def _yfinance_dl() -> Any:
    import yfinance as yf

    return yf


def _dxy_overnight_pct_abs() -> float | None:
    """Absolute overnight % move for DXY (DX-Y.NYB last vs prior close)."""

    try:
        import pandas as pd

        df = _yfinance_dl().download(
            "DX-Y.NYB",
            period="5d",
            auto_adjust=True,
            progress=False,
        )
        if df.empty or "Close" not in df:
            return None
        close_values = df["Close"]
        close_series = (
            close_values.iloc[:, 0] if isinstance(close_values, pd.DataFrame) else close_values
        )
        close_series = close_series.dropna()
        if close_series.empty or len(close_series) < 2:
            return None
        latest = float(close_series.iloc[-1])
        prev = float(close_series.iloc[-2])
        if prev == 0.0:
            return None
        return abs((latest - prev) / prev * 100.0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY overnight %% move unavailable: %s", exc)
        return None


def _max_abs_pair_overnight_pct(
    spots: dict[str, Sequence[SpotBar]],
    universe: dict[str, Any],
) -> float | None:
    mx: float | None = None
    for p in fx_pairs_from_universe(universe):
        bars = spots.get(p)
        if not bars or len(bars) < 2:
            continue
        today_bar = bars[-1]
        yest_bar = bars[-2]
        yc = float(yest_bar.close) if yest_bar.close else 0.0
        if yc == 0.0:
            continue
        tc = float(today_bar.close) if today_bar.close else 0.0
        pct = abs((tc - yc) / yc * 100.0)
        mx = pct if mx is None else max(mx, pct)
    return mx


def assess_stress(
    *,
    vix: float | None,
    dxy_overnight_pct_abs: float | None,
    max_pair_overnight_pct_abs: float | None,
) -> tuple[int, Literal["GREEN", "AMBER", "RED"]]:
    """Stress score from cross-asset volatility and gap risk; maps to circuit-breaker color."""

    score = 0
    if vix is not None:
        if vix >= 35.0:
            score += 2
        elif vix >= 25.0:
            score += 1
    if dxy_overnight_pct_abs is not None:
        if dxy_overnight_pct_abs >= 1.0:
            score += 2
        elif dxy_overnight_pct_abs >= 0.7:
            score += 1
    if max_pair_overnight_pct_abs is not None and max_pair_overnight_pct_abs >= 2.0:
        score += 1

    if score >= 3:
        return score, "RED"
    if score >= 1:
        return score, "AMBER"
    return score, "GREEN"


def _log_dqs_band(dqs: float) -> None:
    if dqs >= 0.90:
        logger.info("DQS interpretation: EXCELLENT (>=0.90) — publish normally")
    elif dqs >= 0.75:
        logger.info("DQS interpretation: GOOD — confidence capped at 85%%")
    elif dqs >= 0.60:
        logger.warning(
            "DQS interpretation: FAIR — confidence capped at 70%%, flagged for review",
        )
    elif dqs >= 0.50:
        logger.warning(
            "DQS interpretation: POOR — stale-data warning; directional confidence tightened",
        )


def _market_dislocation_notice_brief(
    *,
    date_str: str,
    stress_score: int,
    cross: dict[str, float | None],
    dxy_move_pct: float | None,
    max_pair_move_pct: float | None,
    dqs_score: float,
) -> str:
    vix_disp = f"{cross['vix']:.2f}" if cross.get("vix") is not None else "n/a"
    dxy_disp = f"{cross['dxy']:.4f}" if cross.get("dxy") is not None else "n/a"
    dxy_m = f"{dxy_move_pct:.3f}%" if dxy_move_pct is not None else "n/a"
    pair_m = f"{max_pair_move_pct:.3f}%" if max_pair_move_pct is not None else "n/a"
    return (
        f"MARKET DISLOCATION NOTICE ({date_str}). "
        f"Stress Mode RED (score={stress_score}). "
        f"Directional regime calls were withheld today due to elevated systemic gap risk. "
        f"Telemetry snapshot: VIX={vix_disp}, DXY spot={dxy_disp}, "
        f"|overnight DXY|={dxy_m}, max |overnight FX pair|={pair_m}. "
        f"Run health: DQS={dqs_score:.3f}. "
        f"Resume standard publication when stress score falls below 3."
    )


def _require_pipeline_runtime_env() -> None:
    """Fail fast with actionable errors when Prefect/worker env is incomplete."""

    required: dict[str, str] = {
        "SUPABASE_URL": "Supabase project URL (Prefect job_variables.env or secrets).",
        "SUPABASE_SERVICE_ROLE_KEY": "Service role key for pipeline DB writes.",
        "FRED_API_KEY": "FRED API key for yields and macro series.",
        "OPENROUTER_API_KEY": "OpenRouter key for AI briefs and desk card copy.",
    }
    warned: dict[str, str] = {
        "SLACK_WEBHOOK_URL": "Slack webhook for failure alerts (optional but recommended).",
        "RESEND_API_KEY": "Resend API key for email alerts (optional but recommended).",
    }
    missing_warned = [name for name in warned if not os.environ.get(name)]
    if missing_warned:
        detail_warned = "\n".join(f"  - {k}: {warned[k]}" for k in missing_warned)
        logger.warning("Missing optional environment variables:\n%s", detail_warned)
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        detail = "\n".join(f"  - {k}: {required[k]}" for k in missing)
        raise RuntimeError(
            "Missing required environment variables for the FX pipeline:\n"
            f"{detail}\n"
            "Prefect managed workers: ensure deployment `job_variables.env` includes these keys "
            "(see `pipeline/prefect.yaml`; redeploy with `set -a && source .env && set +a` before "
            "`prefect deploy`, or set env in the deployment / work pool UI). "
            "For local runs, use repo-root `.env` or export the variables."
        )


async def _ingest_weekly_research_memo(iso_date: str) -> None:
    """Weekly memo ingestion — fetch Substack and generate AI thesis summary."""
    memo = fetch_latest_substack_memo()
    link_url = str(memo["link_url"])

    # Idempotency check — skip if already ingested
    if writer.research_memo_exists(link_url):
        logger.info("Weekly memo already ingested: %s", link_url)
        return

    date_str = str(memo["date"])[:10]
    raw_content = str(memo["raw_content"])
    try:
        from src.ai.client import summarize_weekly_memo_async
        theses = await summarize_weekly_memo_async(raw_content, date_str=date_str)
        ai_summary = json.dumps(theses)
    except Exception as exc:
        logger.warning("Weekly memo AI summarization failed: %s", exc)
        ai_summary = None
    writer.write_research_memo(
        date_str=date_str,
        title=str(memo["title"]),
        raw_content=raw_content,
        ai_thesis_summary=ai_summary,
        link_url=link_url,
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
        fetch_economics_markets_async,
        get_active_economics_markets,
        polymarket_odds_json_for_prompt,
    )
except ImportError:  # pragma: no cover - optional module in some environments
    fetch_economics_markets_async = None  # type: ignore[assignment]
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


def _breakeven_series_chronological(
    historical_rows: list[dict[str, Any]],
    *,
    today_be: float | None,
) -> tuple[float, ...] | None:
    """Oldest-first breakeven points for Δπ telemetry (optional when history is sparse)."""

    parsed: list[tuple[date, float]] = []
    for row in historical_rows:
        dt_raw = row.get("date")
        if dt_raw is None:
            continue
        try:
            d_co = date.fromisoformat(str(dt_raw)[:10])
        except ValueError:
            continue
        b = row.get("breakeven_inflation_10y")
        if b is None:
            continue
        try:
            parsed.append((d_co, float(b)))
        except (TypeError, ValueError):
            continue
    parsed.sort(key=lambda x: x[0])
    series = [float(v) for _, v in parsed]
    if today_be is not None:
        series.append(float(today_be))
    return tuple(series) if series else None


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
        volume_rvol=row.get("volume_rvol"),
        structural_instability=row.get("structural_instability", False),

        breakeven_inflation_10y=row.get("breakeven_inflation_10y"),
        rate_diff_10y_real=row.get("rate_diff_10y_real"),
        rate_z_tactical=row.get("rate_z_tactical"),
        rate_z_structural=row.get("rate_z_structural"),
        realized_vol_rank=row.get("realized_vol_rank"),
        skew_alignment=int(row["skew_alignment"])
        if row.get("skew_alignment") is not None
        else None,
        risk_reversal_25d=row.get("risk_reversal_25d"),
        fpi_flow=row.get("fpi_flow"),
        cot_net_pos=row.get("cot_net_pos"),
        cot_asset_mgr_net=row.get("cot_asset_mgr_net"),
        cot_lev_money_net=row.get("cot_lev_money_net"),
        ecb_balance_sheet=row.get("ecb_balance_sheet"),
        bund_btp_spread=row.get("bund_btp_spread"),
        boj_policy_rate=row.get("boj_policy_rate"),
        india_vix=row.get("india_vix"),
        inr_forward_premium=row.get("inr_forward_premium"),
    )


def _regime_call_from_db(row: dict[str, Any]) -> RegimeCall:
    et_raw = row.get("entry_timing")
    entry_timing: Layer3EntryTiming | None
    if et_raw == "ENTER" or et_raw == "WAIT":
        entry_timing = et_raw
    else:
        entry_timing = None
    ps_raw = row.get("position_size")
    position_size: Layer3PositionSize | None
    if ps_raw == "FULL" or ps_raw == "HALF":
        position_size = ps_raw
    else:
        position_size = None
    sl_raw = row.get("stop_level")
    stop_level = float(sl_raw) if sl_raw is not None else None
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
        entry_timing=entry_timing,
        position_size=position_size,
        stop_level=stop_level,
        data_quality_score=(
            float(row["data_quality_score"])
            if row.get("data_quality_score") is not None
            else None
        ),
        stress_level=str(row["stress_level"]) if row.get("stress_level") else None,
        predicted_direction=(
            str(row.get("predicted_direction")) if row.get("predicted_direction") else None
        ),
        directional_bias=str(row.get("directional_bias")) if row.get("directional_bias") else None,
        conviction=int(row["conviction"]) if row.get("conviction") is not None else None,
        cot_signal=str(row.get("cot_signal")) if row.get("cot_signal") else None,
        vol_signal=str(row.get("vol_signal")) if row.get("vol_signal") else None,
        oi_signal=str(row.get("oi_signal")) if row.get("oi_signal") else None,
        rr_signal=str(row.get("rr_signal")) if row.get("rr_signal") else None,
        special_signal_value=(
            float(row["special_signal_value"])
            if row.get("special_signal_value") is not None
            else None
        ),
        special_signal_label=(
            str(row.get("special_signal_label"))
            if row.get("special_signal_label")
            else None
        ),
        regime_category=(
            str(row.get("regime_category"))
            if row.get("regime_category")
            else None
        ),
        model_version=str(row.get("model_version")) if row.get("model_version") else None,
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
    """Generate AI briefs for high-impact macro events in the forward window."""
    from src.ai.client import generate_event_brief

    start_d = date.fromisoformat(date_str)
    end_d = start_d + timedelta(days=forward_days)
    try:
        macro_rows = writer.list_high_impact_events_needing_brief(
            start_d.isoformat(),
            end_d.isoformat(),
        )
    except Exception as exc:
        logger.warning("Failed to list macro events needing brief: %s", exc)
        return

    for ev in macro_rows:
        ev_date = str(ev.get("date"))[:10]
        ev_name = str(ev.get("event"))
        try:
            # Build a minimal risk matrix dict for the event
            risk_matrix = {
                "event_name": ev_name,
                "pair": ",".join(list(ev.get("pairs") or PAIRS)),
                "active_regime": "NEUTRAL",
                "sample_size": 0,
                "median_mie_multiplier": None,
                "asymmetry_ratio": None,
                "asymmetry_direction": None,
            }
            ai_text = generate_event_brief(
                risk_matrix,
                date_str=date_str,
                polymarket_context=polymarket_context,
            )
            writer.update_macro_event_ai_brief(ev_date, ev_name, ai_text)
            logger.info("Macro event AI brief generated for %s", ev_name)
        except RuntimeError as exc:
            logger.warning("Stopping macro AI updates: %s", exc)
            break
        except Exception as exc:
            logger.warning("Macro event brief failed for %s: %s", ev_name, exc)


def _upsert_pair_briefs_for_date(
    date_str: str,
    polymarket_context: str,
    *,
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> list[str]:
    """Generate per-pair AI briefs and return telemetry context strings."""
    from src.ai.client import generate_brief

    pair_contexts: list[str] = []
    for pair in PAIRS:
        prior = writer.get_latest_regime_call(pair)
        if not prior:
            continue
        prior_date = str(prior.get("date") or "")[:10]
        # Accept latest regime call regardless of exact date — on weekends the
        # trading date (e.g. Friday) won't match the run date (e.g. Saturday).
        if not prior_date:
            continue

        # Look up signal using the regime call's actual trading date.
        sig = writer.get_signal_for_pair_date(pair, prior_date)
        if not sig:
            continue
        signal_row = _signal_row_from_db(sig)

        try:
            brief = generate_brief(
                pair=pair,
                regime=str(prior.get("regime") or ""),
                confidence=float(prior.get("confidence") or 0.0),
                composite=float(prior.get("signal_composite") or 0.0),
                signal_row=signal_row,
                date_str=date_str,
                primary_driver=(
                    str(prior.get("primary_driver"))
                    if prior.get("primary_driver")
                    else None
                ),
                polymarket_context=polymarket_context,
                dollar_dominance_pct=dollar_dominance_pct,
                polymarket_odds_json=polymarket_odds_json,
            )
            writer.write_brief(
                date_str=date_str,
                pair=pair,
                regime=str(prior.get("regime") or ""),
                confidence=float(prior.get("confidence") or 0.0),
                composite=float(prior.get("signal_composite") or 0.0),
                analysis=brief,
                primary_driver=(
                    str(prior.get("primary_driver"))
                    if prior.get("primary_driver")
                    else ""
                ),
            )
            pair_contexts.append(brief)
        except Exception as exc:
            logger.warning("Pair brief generation failed for %s: %s", pair, exc)
            pair_contexts.append(
                f"{pair} regime={prior.get('regime')} conf={float(prior['confidence']):.2f} "
                f"driver={prior.get('primary_driver') or 'unknown'} "
                f"r2y={signal_row.rate_diff_2y} r10y={signal_row.rate_diff_10y} "
                f"oil={signal_row.cross_asset_oil} spot={signal_row.spot}"
            )
    return pair_contexts


@task(retries=3, retry_delay_seconds=30)
async def build_master_buffer_task(
    *,
    spot_lookback_days: int = 120,
    yield_lookback_days: int = 5,
) -> dict[str, Any]:
    """Concurrent fetch of spots, yields, COT, cross-asset (retries on transient failures)."""

    return await build_master_buffer(
        spot_lookback_days=spot_lookback_days,
        yield_lookback_days=yield_lookback_days,
    )


@task(retries=2, retry_delay_seconds=30)
async def batch_desk_briefs_task(
    pending_desk_cards: list[dict[str, Any]],
) -> list[Any]:
    """Generate desk-card briefs — AI first, deterministic fallback on failure."""
    from src.ai.client import generate_desk_card_brief_async

    outcomes: list[Any] = []
    for item in pending_desk_cards:
        bkw = cast(dict[str, Any], item["brief_kw"])
        try:
            brief, human_grounding = await generate_desk_card_brief_async(
                pair=str(bkw.get("pair") or ""),
                regime=str(bkw.get("regime") or ""),
                date_str=str(bkw.get("date_str") or ""),
                primary_driver=bkw.get("primary_driver"),
                pain_index=bkw.get("pain_index"),
                rvol=bkw.get("rvol"),
                todays_event_matrix=bkw.get("todays_event_matrix"),
                dollar_dominance_score=bkw.get("dollar_dominance_score"),
                dollar_bias=bkw.get("dollar_bias"),
            )
            outcomes.append((brief, human_grounding))
        except Exception as exc:
            logger.warning("Desk card AI brief failed: %s", exc)
            fb = desk_card_brief_fallback(
                regime=str(bkw.get("regime") or ""),
                primary_driver=bkw.get("primary_driver"),
                pain_index=bkw.get("pain_index"),
                rvol=bkw.get("rvol"),
                todays_event_matrix=bkw.get("todays_event_matrix"),
                dollar_dominance_score=bkw.get("dollar_dominance_score"),
                dollar_bias=bkw.get("dollar_bias"),
            )
            outcomes.append((fb, False))
    return outcomes


@task(retries=2, retry_delay_seconds=30)
def write_desk_open_cards_bulk_task(rows: list[DeskOpenCardRow]) -> None:
    writer.write_desk_open_cards_bulk(rows)


@task(retries=2, retry_delay_seconds=30)
def upsert_pair_briefs_task(
    date_str: str,
    polymarket_context: str,
    *,
    dollar_dominance_pct: float | None = None,
    polymarket_odds_json: str = "[]",
) -> list[str]:
    return _upsert_pair_briefs_for_date(
        date_str,
        polymarket_context,
        dollar_dominance_pct=dollar_dominance_pct,
        polymarket_odds_json=polymarket_odds_json,
    )


@task(retries=2, retry_delay_seconds=30)
def upsert_macro_event_briefs_task(
    date_str: str,
    forward_days: int = 3,
    polymarket_context: str = "",
) -> None:
    _upsert_macro_event_briefs(
        date_str,
        forward_days=forward_days,
        polymarket_context=polymarket_context,
    )


@flow(name="Daily G10 FX Pipeline", log_prints=True, timeout_seconds=1800)
async def run_daily(
    date_str: str | None = None,
    *,
    correlation_id: str | None = None,
) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    logger.info("Pipeline correlation_id=%s for date=%s", correlation_id, date_str)

    _require_pipeline_runtime_env()

    universe = load_universe()
    buffer = await build_master_buffer_task()
    gate = validate_ingestion_buffer(buffer, universe=universe)
    if gate.telemetry_status == "OFFLINE":
        logger.critical(
            "Daily run aborted: telemetry OFFLINE — spot ingestion quorum breach "
            "(refusing to write signals/regime to protect systemic matrix)"
        )
        raise RuntimeError("Spot ingestion quorum breach — telemetry OFFLINE.")
    buffer = gate.buffer

    as_of_day = date.fromisoformat(date_str[:10])
    dqs_out = compute_dqs(buffer, universe, as_of_day)
    logger.info(
        "DQS=%.4f (rates=%.3f spots=%.3f cot=%.3f comm=%.3f "
        "cross=%.3f penalty=%s spot_obs=%s cot_obs=%s)",
        dqs_out.score,
        dqs_out.rates_freshness,
        dqs_out.spots_freshness,
        dqs_out.cot_freshness,
        dqs_out.commodities_freshness,
        dqs_out.cross_asset_freshness,
        dqs_out.critical_penalty_applied,
        dqs_out.spot_observation_date,
        dqs_out.cot_observation_date,
    )
    if dqs_out.score < 0.50:
        logger.critical(
            "Pipeline aborted: DQS %.4f below CRITICAL threshold 0.50 — refusing to publish",
            dqs_out.score,
        )
        raise RuntimeError(f"Data Quality Score critical: {dqs_out.score:.4f} < 0.50")
    _log_dqs_band(dqs_out.score)

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
        {k: v for k, v in cross_raw.items() if k != "hist"}
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
    cross_for_special: dict[str, Any] = dict(cross_raw) if isinstance(cross_raw, dict) else {}

    logger.info("Cross-asset snapshot: %s", cross)
    dxy_overnight_pct = _dxy_overnight_pct_abs()
    max_pair_overnight_pct = _max_abs_pair_overnight_pct(spots, universe)
    vix_raw = cross.get("vix")
    vix_val: float | None = None
    if vix_raw is not None:
        try:
            vix_val = float(vix_raw)
        except (TypeError, ValueError):
            vix_val = None
    stress_score, stress_level = assess_stress(
        vix=vix_val,
        dxy_overnight_pct_abs=dxy_overnight_pct,
        max_pair_overnight_pct_abs=max_pair_overnight_pct,
    )
    stress_red = stress_level == "RED"
    logger.info(
        "Stress Mode: score=%s level=%s (|overnight DXY|=%s max |pair overnight|=%s)",
        stress_score,
        stress_level,
        dxy_overnight_pct,
        max_pair_overnight_pct,
    )

    vol_data = fetch_realized_vol(spots)

    events = fetch_macro_events()
    writer.write_macro_events(events)

    # ── Stream A: pair-specific macro signal fetchers ─────────────────────
    ecb_balance_sheet = fetch_ecb_balance_sheet()
    bund_btp_spread = fetch_bund_btp_spread(
        germany_10y=yields_dict.get("de_10y")
    )
    boj_policy_rate = fetch_boj_policy_rate()
    india_vix = fetch_india_vix()
    inr_forward_premium = fetch_inr_forward_premium()
    logger.info(
        "Stream A macro signals: ECB=%s BundBTP=%s BoJ=%s IndiaVIX=%s INRPrem=%s",
        ecb_balance_sheet,
        bund_btp_spread,
        boj_policy_rate,
        india_vix,
        inr_forward_premium,
    )

    # ── IngestionSnapshot: typed domain object for the new builder seam ────
    ingestion_snapshot = IngestionSnapshot.from_buffer(
        as_of=as_of_day,
        buffer=buffer,
        macro={
            "ecb_balance_sheet": ecb_balance_sheet,
            "bund_btp_spread": bund_btp_spread,
            "boj_policy_rate": boj_policy_rate,
            "india_vix": india_vix,
            "inr_forward_premium": inr_forward_premium,
        },
        dqs_score=float(dqs_out.score),
        stress_level=stress_level,
    )

    pending_desk_cards: list[dict[str, Any]] = []

    for pair in PAIRS:
        prior_db = writer.get_latest_regime_call(pair)
        historical_rows = writer.get_historical_signals(pair, limit=2520)
        historical_carry = build_carry_history_from_rows(historical_rows, max_points=2520)
        historical_real_10y = build_real_yield_10y_spread_history_from_rows(
            historical_rows, max_points=2520
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
        historical_rr = [
            float(v)
            for row in historical_rows
            if (v := row.get("risk_reversal_25d")) is not None
        ]
        historical_fpi = [
            float(v)
            for row in historical_rows
            if (v := row.get("fpi_flow")) is not None
        ]
        spot_bars = spots.get(pair, [])
        if not spot_bars:
            logger.warning("No spot bars for %s — skipping", pair)
            continue

        # Find bar matching as_of_day for backfill; fall back to latest
        _as_of_idx = next(
            (i for i, b in enumerate(spot_bars) if b.date == as_of_day),
            len(spot_bars) - 1,
        )
        today_bar = spot_bars[_as_of_idx]

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
        rate_spread_for_norm = rate_spread_2y if rate_spread_2y is not None else rate_spread_10y

        # ── COT: traditional net long + smart spread (M.3.3) ────────────────
        cot_pct = compute_cot_percentile(cot_rows, pair, as_of=today_bar.date)
        cot_smart = compute_cot_smart_spread_percentile(
            cot_rows, pair, as_of=today_bar.date
        )
        cot_pct_norm = normalize_cot_signal(cot_pct) if cot_pct is not None else None
        cot_smart_norm = normalize_cot_signal(cot_smart) if cot_smart is not None else None
        cot_blended: float | None = None
        if cot_pct_norm is not None and cot_smart_norm is not None:
            cot_blended = 0.70 * cot_pct_norm + 0.30 * cot_smart_norm
        elif cot_pct_norm is not None:
            cot_blended = cot_pct_norm
        cot_norm = cot_blended

        # Extract latest COT breakdowns for signal row.
        pair_cot_rows = sorted(
            [r for r in cot_rows if r.pair == pair and r.date <= today_bar.date],
            key=lambda r: r.date,
        )
        latest_cot = pair_cot_rows[-1] if pair_cot_rows else None
        cot_net_pos = latest_cot.net_long if latest_cot else None
        cot_asset_mgr_net = latest_cot.asset_mgr_net if latest_cot else None
        cot_lev_money_net = latest_cot.lev_money_net if latest_cot else None

        days_since_cot = (today_bar.date - latest_cot.date).days if latest_cot else 999

        rv = vol_data.get(pair, {})
        rv5 = rv.get("realized_vol_5d")
        rv20 = rv.get("realized_vol_20d")

        # ── Rate: risk-adjusted carry v2 prefers implied vol (M.3.4) ────────
        iv = fetch_implied_vol(pair)
        risk_adjusted_carry = compute_risk_adjusted_carry_v2(
            rate_spread_2y, rv20, iv, pair
        )
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
        rate_norm = rate_norm_z.z_blended if rate_norm_z is not None else None
        rate_z_tactical_val = (
            rate_norm_z.z_tactical if rate_norm_z is not None else None
        )
        rate_z_structural_val = (
            rate_norm_z.z_structural if rate_norm_z is not None else None
        )
        # Rate direction uses z-score when available (detects changes, not levels).
        rate_dir = rate_direction_from_spreads(
            rate_spread_2y, rate_spread_10y_real, z_tactical=rate_norm
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
        # ── EURUSD real special signal (M.3.1): macro-driven, not post-hoc ──
        eur_special_kwargs: dict[str, Any] = {}
        if pair == "EURUSD":
            eur_special_kwargs = {
                "bund_btp_spread": bund_btp_spread,
                "ecb_balance_sheet": ecb_balance_sheet,
            }
        special_signal = compute_special_signal(pair, cross_for_special, **eur_special_kwargs)

        # ── Stream A: blend pair-specific macro signals into special slot ────
        if pair == "USDJPY":
            intervention = compute_intervention_proximity(
                today_bar.close if today_bar.close else None
            )
            if intervention is not None and special_signal is not None:
                special_signal = 0.85 * special_signal + 0.15 * intervention
            # Supplementary US-JP rate differential context (does not replace rate_diff_2y)
            us_2y_for_jp = yields_dict.get("us_2y")
            if us_2y_for_jp is not None and boj_policy_rate is not None:
                jp_rate_spread = float(us_2y_for_jp) - float(boj_policy_rate)
                logger.info(
                    "USDJPY supplementary rate spread (US 2Y %.3f - BoJ %.3f) = %.4f",
                    us_2y_for_jp,
                    boj_policy_rate,
                    jp_rate_spread,
                )
        special_norm = special_signal if special_signal is not None else 0.0

        # ── FPI flow (USDINR only) ──────────────────────────────────────────
        fpi_signal: float | None = None
        fpi_raw: dict[str, Any] | None = None
        if pair == "USDINR":
            try:
                fpi_raw = fetch_fpi_flows(today_bar.date)
                if fpi_raw:
                    fpi_flow_cr = fpi_raw.get("fpi_total_net_cr")
                    fpi_signal = normalize_fpi_signal(
                        latest_flow=fpi_flow_cr,
                        history=historical_fpi,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("FPI fetch failed for %s: %s", pair, exc)
        fpi_norm = fpi_signal if fpi_signal is not None else 0.0

        top_5y = dominance_top_family(
            betas_5y,
            rate_norm,
            cot_norm,
            vol_norm,
            oi_norm,
            special_norm=special_norm,
            fpi_norm=fpi_norm,
        )
        top_3y = (
            dominance_top_family(
                betas_3y,
                rate_norm,
                cot_norm,
                vol_norm,
                oi_norm,
                special_norm=special_norm,
                fpi_norm=fpi_norm,
            )
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
            special_norm=special_norm,
            fpi_norm=fpi_norm,
        )
        # ── Composite with beta-informed precision weighting (M.2.1) ────────
        composite = compute_composite(
            rate_norm, cot_norm, vol_norm, oi_norm,
            pair=pair,
            special_signal=special_signal,
            fpi_signal=fpi_signal,
            betas=betas_5y,
        )
        if composite is None:
            logger.warning("Not enough data for %s — skipping", pair)
            continue

        # Pair-specific confidence adjustments
        commodity_components_agree = None
        wti_wcs_agree = None
        brent_above_p80 = None
        if pair == "AUDUSD":
            # Commodity convergence: all 3 components same sign and non-neutral
            hist = cross_for_special.get("hist", {})
            if hist:
                # Simplified: if special_signal is strong, components likely agree
                commodity_components_agree = abs(special_signal or 0.0) > 0.5
        elif pair == "USDCAD":
            wti_wcs_agree = abs(special_signal or 0.0) > 0.5
        elif pair == "USDINR":
            brent_above_p80 = (cross.get("oil") or 0) > 80  # crude proxy

        # ── Confidence with redundancy penalty (M.2.2) ──────────────────────
        red_penalty = _redundancy_penalty(
            {
                "rate": rate_norm or 0.0,
                "cot": cot_norm or 0.0,
                "vol": vol_norm or 0.0,
                "oi": oi_norm or 0.0,
                "special": special_norm,
                "fpi": fpi_norm,
            },
            betas_5y,
        )
        confidence = compute_confidence(
            composite, rate_norm, cot_norm,
            pair=pair,
            special_signal=special_signal,
            commodity_components_agree=commodity_components_agree,
            wti_wcs_agree=wti_wcs_agree,
            brent_above_p80=brent_above_p80,
            redundancy_penalty=red_penalty,
        )
        if pair == "USDINR" and cot_pct is None:
            # INR does not have liquid CFTC positioning — do not penalise for missing COT.
            pass
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
        prior_label = (
            str(prior_db["regime"])
            if prior_db and prior_db.get("regime") is not None
            else None
        )
        spot_closes = tuple(float(bar.close) for bar in spot_bars)
        carry_gate: tuple[float, ...] = tuple(float(x) for x in historical_carry)
        if risk_adjusted_carry is not None:
            carry_gate = carry_gate + (float(risk_adjusted_carry),)
        bei_series = _breakeven_series_chronological(historical_rows, today_be=bei)
        gate_out = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol_exp,
                structural_instability=structural_instability,
                prior_regime_label=prior_label,
                carry_risk_adjusted_chronological=carry_gate,
                spot_closes_chronological=spot_closes,
                breakeven_inflation_chronological=bei_series,
                rate_diff_2y=rate_spread_2y,
                realized_vol_20d=rv20,
            ),
        )
        regime = gate_out["regime"]
        if gate_out["invalidated"]:
            rate_dir = "NEUTRAL"
            confidence = float(max(0.40, confidence * 0.50))
            logger.warning(
                "Layer 1 invalidated for %s (stale: %s) — directional bias flattened",
                pair,
                ",".join(gate_out["stale_fields"]),
            )

        layer2_out = run_layer2_directional(
            composite=float(composite),
            z_tactical=rate_norm,
            z_structural=rate_z_structural_val,
            rate_direction=rate_dir,
            positioning_percentile=cot_pct,
            layer1_invalidated=bool(gate_out["invalidated"]),
        )
        # ── Risk reversal proxy (all pairs) ─────────────────────────────────
        # v2.1: Synthetic RR proxy removed. Real 25Δ risk reversal data is being sourced.
        # Layer 3 operates without RR until real data is available.
        rr_proxy = None
        rr_source = "PENDING_REAL_DATA"
        rr_series = tuple(historical_rr)

        rv_rank_layer3 = compute_realized_vol_rank_from_closes(
            tuple(float(b.close) for b in spot_bars),
            window=TRADING_DAYS_3Y_VOL_RANK,
        )
        layer3_out = run_layer3_execution(
            layer2=layer2_out,
            spot=float(today_bar.close) if today_bar.close else None,
            spot_bars=spot_bars,
            realized_vol_rank=rv_rank_layer3,
            risk_reversal_series_bps=rr_series,
        )
        # Layer2 conviction cap: less aggressive than v1.
        # Conviction 1→5 maps to cap 0.50→0.90 (was 0.46→0.90).
        conviction_cap = 0.42 + 0.10 * float(layer2_out["conviction"])
        confidence = min(float(confidence), conviction_cap)
        if stress_level == "AMBER":
            confidence = min(float(confidence), 0.72)

        iv = fetch_implied_vol(pair)

        us10y_value = yields_dict.get("us_10y")
        if us10y_value is None and historical_us10y:
            us10y_value = historical_us10y[0]
            logger.warning(
                "US10Y missing for %s; using latest historical value %.4f",
                pair,
                us10y_value,
            )

        # Pillar 2: RVOL calculation (Institutional Proxy)
        volumes = [b.volume for b in spot_bars if b.volume > 0]
        rvol = compute_rvol(volumes)

        builder = RegimeCallBuilder(ingestion_snapshot)
        signal_row = builder.build_signal_row(
            pair=pair,
            rate_spread_2y=rate_spread_2y,
            rate_spread_10y=rate_spread_10y,
            rate_spread_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_z_tactical_val,
            rate_z_structural=rate_z_structural_val,
            z_blended=rate_norm,
            cot_percentile=cot_pct,
            cot_norm=cot_norm,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=iv,
            vol_norm=vol_norm,
            vol_expanding=vol_exp,
            oi_delta=oi_delta,
            oi_norm=oi_norm,
            special_signal=special_signal,
            fpi_signal=fpi_signal,
            fpi_raw=fpi_raw,
            risk_adjusted_carry=risk_adjusted_carry,
            days_since_cot=days_since_cot,
            cot_net_pos=cot_net_pos,
            cot_asset_mgr_net=cot_asset_mgr_net,
            cot_lev_money_net=cot_lev_money_net,
            structural_instability=structural_instability,
            breakeven_inflation_10y=bei,
            realized_vol_rank=layer3_out["realized_vol_rank"],
            skew_alignment=layer3_out["skew_alignment"],
            risk_reversal_25d=rr_proxy,
            risk_reversal_source=rr_source,
            historical_us10y=us10y_value,
        )
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
            risk_reversal_25d=rr_proxy,
            special_signal=special_signal,
        )
        # Builder applies the DQS cap consistently for all pairs.
        confidence = call.confidence

        if pair == "TESTPAIR":
            continue
        writer.write_signal_row(signal_row)

        if stress_red:
            logger.warning(
                "RED Stress Mode — withholding regime call "
                "publication for %s (signals still saved)",
                pair,
            )
        else:
            persist_regime_call(
                call,
                signals=signal_row,
                correlation_id=correlation_id,
            )
            ledger.log_initial_signal(
                pair=pair,
                target_date=today_bar.date,
                regime=call.regime,
                primary_driver=str(call.primary_driver or ""),
                direction=str(call.predicted_direction or call.rate_signal),
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
                rvol=rvol,
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
            "layer2_directional": dict(layer2_out),
            "layer3_execution": dict(layer3_out),
            "data_quality_score": float(dqs_out.score),
            "stress_level": stress_level,
            "dqs_stale_data_warning": 0.50 <= dqs_out.score < 0.60,
            "dqs_flag_review": 0.60 <= dqs_out.score < 0.75,
        }
        todays_event_matrix = _first_todays_high_impact_matrix_for_pair(
            events,
            pair=pair,
            as_of=today_bar.date,
        )
        regime_age = get_regime_age(pair, regime, as_of=today_bar.date)
        if not stress_red:
            pending_desk_cards.append(
                {
                    "confidence": confidence,
                    "brief_kw": {
                        "pair": pair,
                        "regime": regime,
                        "date_str": today_bar.date.isoformat(),
                        "primary_driver": driver,
                        "pain_index": pain.pain_index if pain is not None else None,
                        "rvol": rvol,
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

    if not pending_desk_cards:
        raise RuntimeError("No regime calls produced for any pair — systemic data failure.")

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
        trading_date_str = ref_date.isoformat()
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

        brief_outcomes = await batch_desk_briefs_task(pending_desk_cards)
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
        write_desk_open_cards_bulk_task(bulk_desk)

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
    if fetch_economics_markets_async is not None:
        try:
            markets = await fetch_economics_markets_async()
            polymarket_context = _format_polymarket_context(markets)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Polymarket fetch failed during daily summary: %s", exc)

    pair_regimes: dict[str, str] = {}
    for p in PAIRS:
        rc = writer.get_latest_regime_call(p)
        if rc is None:
            continue
        rc_date = str(rc.get("date") or "")[:10]
        # Accept regime call if it matches run date OR the actual trading date
        # (on weekends the trading date is Friday while run date is Saturday).
        if rc_date != date_str and rc_date != trading_date_str:
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
    if stress_red:
        global_summary = _market_dislocation_notice_brief(
            date_str=date_str,
            stress_score=stress_score,
            cross=cross,
            dxy_move_pct=dxy_overnight_pct,
            max_pair_move_pct=max_pair_overnight_pct,
            dqs_score=dqs_out.score,
        )
        logger.warning("RED Stress Mode — publishing dislocation notice only")
    else:
        pair_contexts = upsert_pair_briefs_task(
            date_str,
            polymarket_context,
            dollar_dominance_pct=dollar_pct,
            polymarket_odds_json=pm_json,
        )
        try:
            from src.ai.client import generate_global_macro_summary
            global_summary = await generate_global_macro_summary(
                date_str=date_str,
                pair_contexts=pair_contexts,
                macro_context=polymarket_context,
                dollar_dominance_pct=dollar_pct,
                polymarket_odds_json=pm_json,
            )
        except Exception as exc:
            logger.warning("Global macro summary generation failed: %s", exc)
            global_summary = (
                f"FX Regime Lab telemetry for {date_str}. "
                f"Active pairs: {', '.join(pair_regimes.keys())}. "
                f"Dollar dominance: {dollar_pct:.1f}%. "
                f"Idiosyncratic outlier: {outlier_pair or 'none'}."
            )
    # Build deterministic structured summary for UI consumption
    structured_summary: dict[str, Any] = {
        "key_takeaways": [
            f"Dollar dominance: {dollar_pct:.0f}%",
            f"Idiosyncratic outlier: {outlier_pair or 'none'}",
            f"Active pairs: {', '.join(pair_regimes.keys())}",
        ],
        "risk_flags": ["RED STRESS"] if stress_red else [],
        "dollar_dominance_score": round(dollar_pct, 1),
        "idiosyncratic_outlier": outlier_pair,
        "pair_regimes": pair_regimes,
        "stress_red": stress_red,
    }

    writer.write_brief_log(
        date_str,
        global_summary,
        polymarket_context,
        dollar_dominance=dollar_pct,
        idiosyncratic_outlier=outlier_pair,
        sentiment_json=sentiment_json,
        pair_regimes=pair_regimes,
        structured_summary=structured_summary,
    )

    # Populate macro event briefs for the next 3 days immediately
    upsert_macro_event_briefs_task(
        date_str,
        forward_days=3,
        polymarket_context=polymarket_context,
    )

    # ── Run Round 3 validation engine (T+5 / T+20 Brier scores) ─────
    try:
        run_validation(as_of_date=run_as_of)
        logger.info("Validation engine completed for %s", date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Validation engine failed for %s: %s", date_str, exc)

    # ── Alerting / heartbeat ──────────────────────────────────────────
    try:
        if dqs_out.score < 0.70:
            stale_sources: list[str] = []
            if dqs_out.rates_freshness < 0.80:
                stale_sources.append("rates")
            if dqs_out.spots_freshness < 0.80:
                stale_sources.append("spots")
            if dqs_out.cot_freshness < 0.80:
                stale_sources.append("cot")
            alert_on_low_dqs(date_str, dqs_out.score, stale_sources)
        else:
            send_success_heartbeat(
                date_str=date_str,
                pairs_processed=len(pair_regimes),
                regime_calls_count=len(pair_regimes),
                dqs_score=dqs_out.score,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alerting/heartbeat failed for %s: %s", date_str, exc)

    logger.info("Daily run complete for %s", date_str)


def run_weekly(date_str: str | None = None) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    _require_pipeline_runtime_env()

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
    if _m == "weekly":
        _d = sys.argv[2] if len(sys.argv) > 2 else None
        run_weekly(_d)
    else:
        _d = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(run_daily(_d))
