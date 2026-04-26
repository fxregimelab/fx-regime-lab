from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

def fetch_cross_asset(lookback_days: int = 5) -> dict[str, float | None]:
    def last_close(df: object) -> float:
        c = df["Close"]  # type: ignore[index]
        return float((c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c).dropna().iloc[-1])

    period = f"{lookback_days}d"
    vix: float | None = None
    dxy: float | None = None
    try:
        df = yf.download("^VIX", period=period, auto_adjust=True, progress=False)
        if not df.empty:
            vix = last_close(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX fetch failed: %s", exc)
    try:
        df = yf.download("DX-Y.NYB", period=period, auto_adjust=True, progress=False)
        if not df.empty:
            dxy = last_close(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY fetch failed: %s", exc)
    return {"vix": vix, "dxy": dxy}
