"""Overnight telemetry check for desk_open_cards invalidation flags."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.db import writer
from src.fetchers.cross_asset import fetch_cross_asset
from src.fetchers.fx_spot import fetch_fx_spot
from src.types import SpotBar, load_universe, pairs_from_universe

logger = logging.getLogger(__name__)

_STATE_PATH = Path("/tmp/fx_regime_lab_overnight_state.json")
_OFFLINE_FAILURE_THRESHOLD = 3
_INVALIDATION_VOL_MULTIPLIER = 1.5
_INVALIDATION_PERSISTENCE_TICKS = 3


@dataclass(frozen=True)
class ProxyBasket:
    spot: dict[str, float]
    vix: float | None
    dxy: float | None


def _coerce_streak_dict(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return out


def _read_state() -> dict[str, Any]:
    if not _STATE_PATH.exists():
        return {"consecutive_failures": 0, "invalidation_streak": {}}
    try:
        parsed = json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"consecutive_failures": 0, "invalidation_streak": {}}
    cf_raw = parsed.get("consecutive_failures", 0)
    streak_raw = parsed.get("invalidation_streak", {})
    streaks = _coerce_streak_dict(streak_raw)
    return {
        "consecutive_failures": int(cf_raw) if isinstance(cf_raw, int) else 0,
        "invalidation_streak": streaks,
    }


def _write_state(consecutive_failures: int, invalidation_streak: dict[str, int]) -> None:
    payload = {
        "consecutive_failures": max(0, consecutive_failures),
        "invalidation_streak": {k: int(v) for k, v in invalidation_streak.items()},
    }
    _STATE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def fetch_proxy_basket() -> ProxyBasket:
    load_universe()
    pairs = pairs_from_universe(asset_class="FX")
    spots = fetch_fx_spot(lookback_days=3)
    cross = fetch_cross_asset(lookback_days=3)
    latest_spot: dict[str, float] = {}
    for pair in pairs:
        bars: list[SpotBar] = spots.get(pair, [])
        if not bars:
            continue
        latest_spot[pair] = bars[-1].close
    return ProxyBasket(spot=latest_spot, vix=cross.get("vix"), dxy=cross.get("dxy"))


def _set_all_latest_cards_offline() -> None:
    load_universe()
    for pair in pairs_from_universe(asset_class="FX"):
        latest = writer.get_latest_desk_open_card(pair)
        if not latest:
            continue
        row_date = str(latest.get("date", ""))[:10]
        if not row_date:
            continue
        writer.update_desk_open_card_flags(pair, row_date, telemetry_status="OFFLINE")


def run_overnight_check() -> None:
    load_universe()
    pairs = pairs_from_universe(asset_class="FX")
    state = _read_state()
    try:
        basket = fetch_proxy_basket()
        if len(basket.spot) != len(pairs):
            raise RuntimeError("Spot proxy basket incomplete")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overnight proxy fetch failed: %s", exc)
        failures = state["consecutive_failures"] + 1
        streak_clean = _coerce_streak_dict(state.get("invalidation_streak"))
        _write_state(failures, streak_clean)
        if failures >= _OFFLINE_FAILURE_THRESHOLD:
            _set_all_latest_cards_offline()
            logger.warning("Telemetry set OFFLINE after %s failures", failures)
        return

    streak_dict: dict[str, int] = _coerce_streak_dict(state.get("invalidation_streak"))
    _write_state(0, streak_dict)
    today_str = date.today().isoformat()

    baseline_vix = None
    vix_trigger = False
    vol_ref = 0.0
    for pair in pairs:
        signal_row = writer.get_signal_for_pair_date(pair, today_str)
        if not signal_row:
            continue
        if baseline_vix is None and signal_row.get("cross_asset_vix") is not None:
            baseline_vix = float(signal_row["cross_asset_vix"])
        rv20 = signal_row.get("realized_vol_20d")
        if isinstance(rv20, (int, float)):
            vol_ref = max(vol_ref, float(rv20))
    if (
        basket.vix is not None
        and baseline_vix is not None
        and baseline_vix != 0.0
        and vol_ref > 0.0
    ):
        vix_change_pct = ((basket.vix / baseline_vix) - 1.0) * 100.0
        vix_trigger = abs(vix_change_pct) > vol_ref * _INVALIDATION_VOL_MULTIPLIER

    for pair in pairs:
        signal_row = writer.get_signal_for_pair_date(pair, today_str)
        latest_card = writer.get_latest_desk_open_card(pair)
        if not signal_row or not latest_card:
            continue

        signal_date = str(signal_row.get("date", ""))[:10]
        if not signal_date:
            continue

        ny_close = signal_row.get("spot")
        realized_vol_20d = signal_row.get("realized_vol_20d")
        if not isinstance(ny_close, (int, float)) or not isinstance(
            realized_vol_20d, (int, float)
        ):
            continue
        if ny_close == 0.0 or realized_vol_20d <= 0.0:
            continue

        live_spot = basket.spot.get(pair)
        if live_spot is None:
            continue

        day_change_pct = ((live_spot / float(ny_close)) - 1.0) * 100.0
        pair_trigger = abs(day_change_pct) > float(realized_vol_20d) * _INVALIDATION_VOL_MULTIPLIER
        breach = pair_trigger or vix_trigger

        prev_inv = bool(latest_card.get("invalidation_triggered"))
        if breach:
            streak_dict[pair] = streak_dict.get(pair, 0) + 1
        else:
            streak_dict[pair] = 0

        invalidation = prev_inv or streak_dict[pair] >= _INVALIDATION_PERSISTENCE_TICKS
        pending_invalidation = (
            breach
            and not invalidation
            and 0 < streak_dict[pair] < _INVALIDATION_PERSISTENCE_TICKS
        )

        writer.update_desk_open_card_flags(
            pair,
            signal_date,
            invalidation_triggered=invalidation,
            telemetry_status="ONLINE",
        )
        writer.update_desk_open_card_telemetry_audit(
            pair,
            signal_date,
            {
                "overnight_day_change_pct": day_change_pct,
                "overnight_vol_threshold": float(realized_vol_20d) * _INVALIDATION_VOL_MULTIPLIER,
                "overnight_vix": basket.vix,
                "overnight_dxy": basket.dxy,
                "overnight_vix_triggered": vix_trigger,
                "overnight_invalidation_persistence_count": streak_dict[pair],
                "overnight_pending_invalidation": pending_invalidation,
            },
        )
        logger.info(
            (
                "Overnight check %s: change=%.4f vol20=%.4f persistence=%s/%s "
                "invalidation=%s pending=%s"
            ),
            pair,
            day_change_pct,
            float(realized_vol_20d),
            streak_dict[pair],
            _INVALIDATION_PERSISTENCE_TICKS,
            invalidation,
            pending_invalidation,
        )

    _write_state(0, streak_dict)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    run_overnight_check()
