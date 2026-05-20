"""Generate legacy backtest regime calls (v0 and v1) for historical periods.

v0 (1997-2003, EURUSD only):
  US-DE 2Y spread z-score only, static thresholds.

v1 (2003-2019, EURUSD + USDJPY):
  rates 50%, COT 30%, vol 20% composite.

Usage::

    python -m src.research.generate_legacy_backtests --version v0 --dry-run
    python -m src.research.generate_legacy_backtests --version v1 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import math
from datetime import date
from typing import Any, cast

from src.db.writer import _client
from src.types import RegimeCall, SignalRow

logger = logging.getLogger(__name__)


def _load_yields(series_id: str, start: date, end: date) -> dict[date, float]:
    out: dict[date, float] = {}
    page_size = 1000
    offset = 0
    while True:
        res = (
            _client()
            .table("historical_yields")
            .select("date,value")
            .eq("series_id", series_id)
            .gte("date", start.isoformat())
            .lte("date", end.isoformat())
            .order("date")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        if not rows:
            break
        for row in rows:
            d = date.fromisoformat(str(row["date"])[:10])
            out[d] = float(row["value"]) if row["value"] is not None else 0.0
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _load_spots(pair: str, start: date, end: date) -> dict[date, float]:
    out: dict[date, float] = {}
    page_size = 1000
    offset = 0
    while True:
        res = (
            _client()
            .table("historical_prices")
            .select("date,close")
            .eq("pair", pair)
            .gte("date", start.isoformat())
            .lte("date", end.isoformat())
            .order("date")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        if not rows:
            break
        for row in rows:
            d = date.fromisoformat(str(row["date"])[:10])
            out[d] = float(row["close"]) if row["close"] is not None else 0.0
        if len(rows) < page_size:
            break
        offset += page_size
    if out:
        return out

    # Fallback to yfinance
    yf_map = {"EURUSD": "EURUSD=X", "USDJPY": "JPY=X", "USDINR": "INR=X"}
    ticker = yf_map.get(pair)
    if ticker:
        import yfinance as yf

        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=True,
            progress=False,
        )
        for idx, row in df.iterrows():
            d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            close = float(row["Close"]) if not math.isnan(float(row["Close"])) else 0.0
            out[d] = close
    return out


def _zscore(value: float, history: list[float]) -> float:
    if not history:
        return 0.0
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std = math.sqrt(variance) if variance > 0 else 0.0
    if std == 0:
        return 0.0
    return (value - mean) / std


def _run_v0_eurusd(start: date, end: date) -> list[tuple[SignalRow, RegimeCall]]:
    """EURUSD only, US-DE 2Y spread z-score with static thresholds."""
    us2y = _load_yields("DGS2", start, end)
    de2y = _load_yields("IRLTLT01DEM156N", start, end)
    spots = _load_spots("EURUSD", start, end)
    results: list[tuple[SignalRow, RegimeCall]] = []

    sorted_dates = sorted({d for d in us2y} & {d for d in de2y})
    for i, d in enumerate(sorted_dates):
        spread = us2y[d] - de2y[d]
        hist = [us2y[sd] - de2y[sd] for sd in sorted_dates[:i]]
        z = _zscore(spread, hist[-252:] if len(hist) >= 20 else hist)

        if z > 1.0:
            regime = "STRONG USD STRENGTH"
            direction = "BULLISH"
        elif z > 0.5:
            regime = "MODERATE USD STRENGTH"
            direction = "BULLISH"
        elif z < -1.0:
            regime = "STRONG USD WEAKNESS"
            direction = "BEARISH"
        elif z < -0.5:
            regime = "MODERATE USD WEAKNESS"
            direction = "BEARISH"
        else:
            regime = "NEUTRAL"
            direction = "NEUTRAL"

        signal_row = SignalRow(
            pair="EURUSD",
            date=d,
            rate_diff_2y=spread,
            rate_diff_10y=None,
            cot_percentile=None,
            realized_vol_20d=None,
            realized_vol_5d=None,
            implied_vol_30d=None,
            spot=spots.get(d),
            day_change=None,
            day_change_pct=None,
            cross_asset_vix=None,
            cross_asset_dxy=None,
            cross_asset_oil=None,
            cross_asset_us10y=None,
            cross_asset_gold=None,
            cross_asset_copper=None,
            cross_asset_stoxx=None,
            oi_delta=None,
        )
        call = RegimeCall(
            pair="EURUSD",
            date=d,
            regime=regime,
            confidence=min(abs(z) / 2.0, 1.0),
            signal_composite=z,
            rate_signal=direction,
            predicted_direction=direction,
            model_version="0.0-legacy",
            strategy_version="v0",
            data_source="backtest",
        )
        results.append((signal_row, call))
    return results


def _run_v1(start: date, end: date) -> list[tuple[SignalRow, RegimeCall]]:
    """EURUSD + USDJPY with rates 50%, COT 30%, vol 20%."""
    pairs = ["EURUSD", "USDJPY"]
    all_results: list[tuple[SignalRow, RegimeCall]] = []

    for pair in pairs:
        spots = _load_spots(pair, start, end)
        us2y = _load_yields("DGS2", start, end)
        q2y = _load_yields(
            "IRLTLT01DEM156N" if pair == "EURUSD" else "IRLTLT01JPM156N",
            start, end,
        )
        sorted_dates = sorted({d for d in spots} & {d for d in us2y} & {d for d in q2y})

        for i, d in enumerate(sorted_dates):
            spread = us2y[d] - q2y[d]
            hist = [us2y[sd] - q2y[sd] for sd in sorted_dates[:i]]
            z = _zscore(spread, hist[-252:] if len(hist) >= 20 else hist)

            # COT and vol are not available in this simplified backtest
            cot_norm = 0.0
            vol_norm = 0.0
            composite = 0.50 * z + 0.30 * cot_norm + 0.20 * vol_norm

            if composite > 0.6:
                regime = "STRONG USD STRENGTH" if pair == "EURUSD" else "CARRY_INTACT"
                direction = "BULLISH"
            elif composite > 0.3:
                regime = "MODERATE USD STRENGTH" if pair == "EURUSD" else "CARRY_INTACT"
                direction = "BULLISH"
            elif composite < -0.6:
                regime = "STRONG USD WEAKNESS" if pair == "EURUSD" else "CARRY_UNWINDING"
                direction = "BEARISH"
            elif composite < -0.3:
                regime = "MODERATE USD WEAKNESS" if pair == "EURUSD" else "CARRY_COMPRESSING"
                direction = "BEARISH"
            else:
                regime = "NEUTRAL"
                direction = "NEUTRAL"

            signal_row = SignalRow(
                pair=pair,
                date=d,
                rate_diff_2y=spread,
                rate_diff_10y=None,
                cot_percentile=None,
                realized_vol_20d=None,
                realized_vol_5d=None,
                implied_vol_30d=None,
                spot=spots.get(d),
                day_change=None,
                day_change_pct=None,
                cross_asset_vix=None,
                cross_asset_dxy=None,
                cross_asset_oil=None,
                cross_asset_us10y=None,
                cross_asset_gold=None,
                cross_asset_copper=None,
                cross_asset_stoxx=None,
                oi_delta=None,
            )
            call = RegimeCall(
                pair=pair,
                date=d,
                regime=regime,
                confidence=min(abs(composite) / 2.0, 1.0),
                signal_composite=composite,
                rate_signal=direction,
                predicted_direction=direction,
                model_version="1.0-legacy",
                strategy_version="v1",
                data_source="backtest",
            )
            all_results.append((signal_row, call))
    return all_results


def _batch_write(results: list[tuple[SignalRow, RegimeCall]], batch_size: int = 500) -> int:
    if not results:
        return 0
    from postgrest.exceptions import APIError

    written = 0
    skipped = 0
    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        rows = [
            {
                "pair": call.pair,
                "date": call.date.isoformat(),
                "regime": call.regime,
                "confidence": call.confidence,
                "signal_composite": call.signal_composite,
                "rate_signal": call.rate_signal,
                "predicted_direction": call.predicted_direction,
                "model_version": call.model_version,
                "strategy_version": call.strategy_version,
                "data_source": call.data_source,
            }
            for _sig, call in batch
        ]
        try:
            _client().table("regime_calls").insert(rows).execute()
            written += len(batch)
            logger.info("Inserted batch %d-%d", i, i + len(batch) - 1)
        except APIError as exc:
            code = getattr(exc, "code", "")
            if code in ("23505", "409"):
                skipped += len(batch)
                logger.info("Skipped batch %d-%d (conflict)", i, i + len(batch) - 1)
            else:
                raise
    logger.info("Total inserted: %d, skipped: %d", written, skipped)
    return written


def run_generate(version: str, *, dry_run: bool = False) -> int:
    if version == "v0":
        results = _run_v0_eurusd(date(1997, 1, 1), date(2003, 12, 31))
    elif version == "v1":
        results = _run_v1(date(2003, 1, 1), date(2019, 12, 31))
    else:
        raise ValueError(f"Unknown version: {version}")

    logger.info("Generated %d legacy calls for %s", len(results), version)
    if dry_run:
        logger.info("[DRY-RUN] Would insert %d rows", len(results))
        return len(results)

    return _batch_write(results)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=["v0", "v1"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    count = run_generate(args.version, dry_run=args.dry_run)
    logger.info("Done: %d calls written", count)


if __name__ == "__main__":
    main()
