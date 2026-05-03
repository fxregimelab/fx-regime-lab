"""Forward-walking Alpha Ledger: EOD directional hits T+1/3/5 vs rate_signal (no lookahead)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, cast

from src.db import writer

logger = logging.getLogger(__name__)

_FORWARD_FIELDS = (
    "t1_close",
    "t3_close",
    "t5_close",
    "t1_hit",
    "t3_hit",
    "t5_hit",
    "brier_score_t5",
    "max_pain_bps",
)

HistoricalPriceBars = list[dict[str, Any]]


def _normalize_date(raw: Any) -> str:
    return str(raw)[:10]


def _horizon_hit(direction: str, entry_close: float, horizon_close: float) -> int:
    """1 correct, 0 wrong, -1 not scored (neutral view)."""
    d = direction.strip().upper()
    if d == "NEUTRAL":
        return -1
    if d == "BULLISH":
        return 1 if horizon_close > entry_close else 0
    if d == "BEARISH":
        return 1 if horizon_close < entry_close else 0
    logger.warning("Unknown ledger direction %r; scoring as miss", direction)
    return 0


def _to_hit_and_close(
    direction: str,
    entry_close: float | None,
    horizon_close_raw: Any,
) -> tuple[float | None, int | None]:
    if horizon_close_raw is None or entry_close is None:
        return None, None
    close_f = float(horizon_close_raw)
    return close_f, _horizon_hit(direction, entry_close, close_f)


def _brier_t5(direction: str, t5_hit: int | None, confidence_raw: Any) -> float | None:
    """Brier vs T+5: (y - p)^2 for non-neutral directions once t5_hit is known."""
    if t5_hit is None or direction.strip().upper() == "NEUTRAL":
        return None
    p = float(confidence_raw) if confidence_raw is not None else 0.0
    y = 1.0 if t5_hit == 1 else 0.0
    return (y - p) ** 2


def _ohlc_index_map(
    historical_prices: HistoricalPriceBars,
) -> tuple[list[str], list[float], list[float], list[float]]:
    """Align dates with close, high, low; missing OHLC limbs default to close."""
    dates: list[str] = []
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    for row in historical_prices:
        d = _normalize_date(row.get("date"))
        c = row.get("close")
        if c is None:
            continue
        close_f = float(c)
        h_raw, l_raw = row.get("high"), row.get("low")
        high_f = float(h_raw) if h_raw is not None else close_f
        low_f = float(l_raw) if l_raw is not None else close_f
        dates.append(d)
        closes.append(close_f)
        highs.append(high_f)
        lows.append(low_f)
    return dates, closes, highs, lows


def _adverse_bps_for_bar(
    direction: str,
    entry_close: float,
    high: float,
    low: float,
) -> float | None:
    """MAE in basis points vs entry for one session bar (non-negative)."""
    d = direction.strip().upper()
    if entry_close <= 0:
        return None
    if d == "BULLISH":
        return max(0.0, (entry_close - low) / entry_close * 10_000.0)
    if d == "BEARISH":
        return max(0.0, (high - entry_close) / entry_close * 10_000.0)
    return None


def log_initial_signal(
    pair: str,
    target_date: date,
    regime: str,
    primary_driver: str,
    direction: str,
    entry_close: float,
    confidence: float,
) -> None:
    """Record intent to track an edge at signal day T (idempotent upsert)."""
    driver = primary_driver.strip() if primary_driver else "UNKNOWN"
    payload: dict[str, Any] = {
        "date": target_date,
        "pair": pair,
        "regime": regime,
        "primary_driver": driver,
        "direction": direction.strip().upper(),
        "entry_close": entry_close,
        "confidence": confidence,
    }
    existing = writer.get_strategy_ledger_entry(
        target_date,
        pair,
        regime,
        driver,
    )
    if existing:
        for field in _FORWARD_FIELDS:
            if existing.get(field) is not None:
                payload[field] = existing[field]

    writer.write_ledger_entry(payload)


def mark_to_market_ledger(
    pair: str,
    historical_prices: HistoricalPriceBars,
    *,
    as_of_date: date | None = None,
) -> None:
    """Resolve T+1 / T+3 / T+5 EOD closes and hits for open ledger rows (no lookahead)."""
    dates, closes, highs, lows = _ohlc_index_map(historical_prices)
    if not dates:
        logger.warning("mark_to_market_ledger(%s): no price rows", pair)
        return

    fence = as_of_date if as_of_date is not None else date.today()

    open_entries = writer.get_open_ledger_entries(pair)
    if not open_entries:
        return

    to_write: list[dict[str, Any]] = []

    for row in open_entries:
        merged = dict(row)
        t_iso = _normalize_date(merged.get("date"))
        try:
            idx = dates.index(t_iso)
        except ValueError:
            logger.debug(
                "Ledger MTM skip: signal date %s not in price window for %s",
                t_iso,
                pair,
            )
            continue

        direction = str(merged.get("direction") or "")
        entry_close_raw = merged.get("entry_close")
        entry_close = float(entry_close_raw) if entry_close_raw is not None else None

        for horizon, span in ((1, 1), (3, 3), (5, 5)):
            key_close = f"t{span}_close"
            key_hit = f"t{span}_hit"
            j = idx + horizon
            if j >= len(dates):
                continue
            bar_d = date.fromisoformat(dates[j])
            if bar_d > fence:
                continue
            hc = closes[j]
            close_v, hit_v = _to_hit_and_close(direction, entry_close, hc)
            if close_v is not None:
                merged[key_close] = close_v
            if hit_v is not None:
                merged[key_hit] = hit_v

        direction_u = direction.strip().upper()
        mae_max: float | None = None
        if direction_u in ("BULLISH", "BEARISH") and entry_close is not None:
            for day_offset in range(1, 6):
                j = idx + day_offset
                if j >= len(dates):
                    break
                bar_d = date.fromisoformat(dates[j])
                if bar_d > fence:
                    break
                adv = _adverse_bps_for_bar(
                    direction_u,
                    float(entry_close),
                    highs[j],
                    lows[j],
                )
                if adv is None:
                    continue
                mae_max = adv if mae_max is None else max(mae_max, adv)
        if mae_max is not None:
            merged["max_pain_bps"] = mae_max
        elif direction_u == "NEUTRAL":
            merged["max_pain_bps"] = None

        brier = _brier_t5(
            direction,
            cast(int | None, merged.get("t5_hit")),
            merged.get("confidence"),
        )
        if brier is not None:
            merged["brier_score_t5"] = brier

        to_write.append(merged)

    writer.update_ledger_entries(to_write)
