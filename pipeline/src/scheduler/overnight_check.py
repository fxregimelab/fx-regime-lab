"""Overnight telemetry check for desk_open_cards invalidation flags."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from src.db import writer
from src.desk.invalidation import (
    INVALIDATION_PERSISTENCE_TICKS,
    OFFLINE_FAILURE_THRESHOLD,
    InvalidationEvaluator,
)
from src.desk.invalidation_types import BreachInput, StreakState
from src.desk.state_store import FileStateStore, OvernightState
from src.fetchers.cross_asset import fetch_cross_asset
from src.fetchers.fx_spot import fetch_fx_spot
from src.types import SpotBar, load_universe, pairs_from_universe

logger = logging.getLogger(__name__)

_state_store = FileStateStore()
_evaluator = InvalidationEvaluator()


@dataclass(frozen=True)
class ProxyBasket:
    spot: dict[str, float]
    vix: float | None
    dxy: float | None


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
    state = _state_store.load()
    try:
        basket = fetch_proxy_basket()
        if len(basket.spot) != len(pairs):
            raise RuntimeError("Spot proxy basket incomplete")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overnight proxy fetch failed: %s", exc)
        failures = state.consecutive_failures + 1
        _state_store.save(state.with_failures(failures))
        if failures >= OFFLINE_FAILURE_THRESHOLD:
            _set_all_latest_cards_offline()
            logger.warning("Telemetry set OFFLINE after %s failures", failures)
        return

    streak_dict = dict(state.invalidation_streak or {})
    _state_store.save(state.with_failures(0))
    today_str = date.today().isoformat()
    signal_rows = [
        row
        for pair in pairs
        if (row := writer.get_signal_for_pair_date(pair, today_str))
    ]
    vix_trigger = InvalidationEvaluator.resolve_vix_trigger_from_signals(
        basket.vix, signal_rows
    )

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

        decision = _evaluator.evaluate(
            BreachInput(
                live_spot=live_spot,
                ny_close=float(ny_close),
                realized_vol_20d=float(realized_vol_20d),
                vix_trigger=vix_trigger,
                prev_invalidation_triggered=bool(latest_card.get("invalidation_triggered")),
            ),
            StreakState(streak_count=streak_dict.get(pair, 0)),
        )
        streak_dict[pair] = decision.new_streak_count

        writer.update_desk_open_card_flags(
            pair,
            signal_date,
            invalidation_triggered=decision.invalidation_triggered,
            telemetry_status="ONLINE",
        )
        writer.update_desk_open_card_telemetry_audit(
            pair,
            signal_date,
            {
                "overnight_day_change_pct": decision.day_change_pct,
                "overnight_vol_threshold": decision.vol_threshold,
                "overnight_vix": basket.vix,
                "overnight_dxy": basket.dxy,
                "overnight_vix_triggered": vix_trigger,
                "overnight_invalidation_persistence_count": decision.new_streak_count,
                "overnight_pending_invalidation": decision.pending_invalidation,
            },
        )
        logger.info(
            (
                "Overnight check %s: change=%.4f vol20=%.4f persistence=%s/%s "
                "invalidation=%s pending=%s"
            ),
            pair,
            decision.day_change_pct,
            float(realized_vol_20d),
            decision.new_streak_count,
            INVALIDATION_PERSISTENCE_TICKS,
            decision.invalidation_triggered,
            decision.pending_invalidation,
        )

    _state_store.save(OvernightState(consecutive_failures=0, invalidation_streak=streak_dict))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    run_overnight_check()
