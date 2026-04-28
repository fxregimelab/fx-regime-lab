from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def _latest_and_change_1d(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if df.empty or "Close" not in df:
        return None, None
    close_values = df["Close"]
    close_series = (
        close_values.iloc[:, 0] if isinstance(close_values, pd.DataFrame) else close_values
    )
    close_series = close_series.dropna()
    if close_series.empty:
        return None, None
    latest = float(close_series.iloc[-1])
    if len(close_series) < 2:
        return latest, None
    change_1d = float(close_series.iloc[-1] - close_series.iloc[-2])
    return latest, change_1d


def fetch_cross_asset(lookback_days: int = 5) -> dict[str, float | None]:
    period = f"{lookback_days}d"
    vix: float | None = None
    dxy: float | None = None
    oil: float | None = None
    oil_change_1d: float | None = None
    try:
        df = yf.download("^VIX", period=period, auto_adjust=True, progress=False)
        vix, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX fetch failed: %s", exc)
    try:
        df = yf.download("DX-Y.NYB", period=period, auto_adjust=True, progress=False)
        dxy, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY fetch failed: %s", exc)
    try:
        df = yf.download("CL=F", period=period, auto_adjust=True, progress=False)
        oil, oil_change_1d = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Oil fetch failed: %s", exc)
    return {
        "vix": vix,
        "dxy": dxy,
        "oil": oil,
        "oil_change_1d": oil_change_1d,
    }
