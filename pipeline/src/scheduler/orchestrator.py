"""Daily and weekly pipeline orchestration."""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv

from src.ai.client import generate_brief, generate_event_brief
from src.db import writer
from src.fetchers.cot import fetch_cot
from src.fetchers.cross_asset import fetch_cross_asset
from src.fetchers.fx_spot import fetch_fx_spot
from src.fetchers.macro_calendar import fetch_macro_events
from src.fetchers.open_interest import compute_oi_from_cot
from src.fetchers.volatility import fetch_implied_vol, fetch_realized_vol
from src.fetchers.yields import fetch_yields
from src.regime.classifier import classify_regime
from src.regime.composite import compute_composite, get_primary_driver
from src.regime.confidence import compute_confidence
from src.signals.cot import compute_cot_percentile, normalize_cot_signal
from src.signals.open_interest import compute_oi_signal
from src.signals.rate import compute_rate_signal, normalize_rate_signal
from src.signals.volatility import VOL_90TH, compute_vol_signal, is_vol_expanding
from src.types import PAIRS, RegimeCall, SignalRow
from src.validation.backtest import validate_call

logger = logging.getLogger(__name__)


def _signal_row_from_db(row: dict[str, Any]) -> SignalRow:
    return SignalRow(
        pair=str(row["pair"]),
        date=date.fromisoformat(str(row["date"])[:10]),
        rate_diff_2y=row.get("rate_diff_2y"),
        cot_percentile=row.get("cot_percentile"),
        realized_vol_20d=row.get("realized_vol_20d"),
        realized_vol_5d=row.get("realized_vol_5d"),
        implied_vol_30d=row.get("implied_vol_30d"),
        spot=row.get("spot"),
        day_change=row.get("day_change"),
        day_change_pct=row.get("day_change_pct"),
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


def run_daily(date_str: str | None = None) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    yields = fetch_yields()
    spots = fetch_fx_spot(lookback_days=30)
    cot_rows = fetch_cot()
    cross = fetch_cross_asset()
    logger.info("Cross-asset snapshot: %s", cross)
    vol_data = fetch_realized_vol(spots)

    events = fetch_macro_events()
    writer.write_macro_events(events)

    for pair in PAIRS:
        prior_db = writer.get_latest_regime_call(pair)
        spot_bars = spots.get(pair, [])
        if not spot_bars:
            logger.warning("No spot bars for %s — skipping", pair)
            continue

        today_bar = spot_bars[-1]
        yest_bar = spot_bars[-2] if len(spot_bars) >= 2 else today_bar
        today_yields = yields[0] if yields else None

        rate_spread, rate_dir = compute_rate_signal(today_yields, pair)
        rate_norm = normalize_rate_signal(rate_spread, pair) if rate_spread is not None else None

        cot_pct = compute_cot_percentile(cot_rows, pair)
        cot_norm = normalize_cot_signal(cot_pct) if cot_pct is not None else None

        rv = vol_data.get(pair, {})
        rv5 = rv.get("realized_vol_5d")
        rv20 = rv.get("realized_vol_20d")
        vol_norm = (
            compute_vol_signal(rv5, rv20, VOL_90TH[pair])
            if rv5 is not None and rv20 is not None
            else 0.0
        )
        vol_exp = is_vol_expanding(rv5, pair) if rv5 is not None else False

        oi_pct = compute_oi_from_cot(cot_rows, pair)
        oi_norm = compute_oi_signal(oi_pct)
        composite = compute_composite(rate_norm, cot_norm, vol_norm, oi_norm)
        if composite is None:
            logger.warning("Not enough data for %s — skipping", pair)
            continue

        confidence = compute_confidence(composite, rate_norm, cot_norm)
        driver = get_primary_driver(rate_norm, cot_norm, vol_norm)
        regime = classify_regime(composite, pair, vol_expanding=vol_exp)

        day_change = today_bar.close - yest_bar.close
        day_chg_pct = (day_change / yest_bar.close * 100) if yest_bar.close else 0.0
        iv = fetch_implied_vol(pair)

        signal_row = SignalRow(
            pair=pair,
            date=today_bar.date,
            rate_diff_2y=rate_spread,
            cot_percentile=cot_pct,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=iv,
            spot=today_bar.close,
            day_change=day_change,
            day_change_pct=day_chg_pct,
        )

        if prior_db and str(prior_db.get("date"))[:10] != today_bar.date.isoformat():
            val_row = validate_call(_regime_call_from_db(prior_db), spots)
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

    logger.info("Daily run complete for %s", date_str)


def run_weekly(date_str: str | None = None) -> None:
    if date_str is None:
        date_str = date.today().isoformat()

    for pair in PAIRS:
        cached = writer.get_brief_for_date(pair, date_str)
        if cached:
            logger.info("Brief already exists for %s %s — skipping AI call", pair, date_str)
            continue

        prior = writer.get_latest_regime_call(pair)
        if not prior:
            continue

        sig = writer.get_signal_for_pair_date(pair, date_str)
        if not sig:
            continue
        signal_row = _signal_row_from_db(sig)

        analysis = generate_brief(
            pair,
            str(prior["regime"]),
            float(prior["confidence"]),
            float(prior["signal_composite"]),
            signal_row,
            date_str,
        )
        writer.write_brief(
            date_str, pair, str(prior["regime"]), float(prior["confidence"]),
            float(prior["signal_composite"]), analysis, str(prior.get("primary_driver") or ""),
        )

    start_d = date.fromisoformat(date_str)
    end_d = start_d + timedelta(days=7)
    macro_rows = writer.list_high_impact_events_needing_brief(
        start_d.isoformat(),
        end_d.isoformat(),
    )
    for ev in macro_rows:
        ev_date = str(ev.get("date"))[:10]
        ev_name = str(ev.get("event"))
        impact = str(ev.get("impact"))
        pairs = list(ev.get("pairs") or PAIRS)
        try:
            ai_text = generate_event_brief(ev_name, impact, pairs, date_str)
            writer.update_macro_event_ai_brief(ev_date, ev_name, ai_text)
        except RuntimeError as exc:
            logger.warning("Stopping macro AI updates: %s", exc)
            break

    logger.info("Weekly run complete for %s", date_str)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    _m = sys.argv[1] if len(sys.argv) > 1 else "daily"
    (run_weekly if _m == "weekly" else run_daily)()
