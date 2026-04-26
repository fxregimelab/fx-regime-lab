"""yfinance FX spot OHLC for configured pairs."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf

from src.types import YF_TICKERS, SpotBar

logger = logging.getLogger(__name__)

_TICKER_TO_PAIR = {v: k for k, v in YF_TICKERS.items()}


def fetch_fx_spot(lookback_days: int = 30) -> dict[str, list[SpotBar]]:
    """Download spot history for all pairs; returns bars sorted by date ascending."""
    tickers = list(YF_TICKERS.values())
    period = f"{lookback_days}d"
    out: dict[str, list[SpotBar]] = {p: [] for p in YF_TICKERS}
    try:
        raw = yf.download(
            tickers,
            period=period,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance FX batch download failed: %s", exc)
        return out

    if raw is None or raw.empty:
        logger.warning("yfinance FX download returned empty frame")
        return out

    for ticker in tickers:
        pair = _TICKER_TO_PAIR.get(ticker)
        if pair is None:
            continue
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                sub = raw[ticker]
            elif len(tickers) == 1:
                sub = raw
            else:
                sub = raw
            if sub.empty:
                continue
            for idx, row in sub.iterrows():
                d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                o = row.get("Open", np.nan)
                h = row.get("High", np.nan)
                lo = row.get("Low", np.nan)
                c = row.get("Close", np.nan)
                if any(pd.isna(v) for v in (o, h, lo, c)):
                    continue
                out[pair].append(
                    SpotBar(
                        date=d,
                        pair=pair,
                        open=float(o),
                        high=float(h),
                        low=float(lo),
                        close=float(c),
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse failed for %s: %s", ticker, exc)

    for pair in out:
        out[pair].sort(key=lambda b: b.date)
    return out
