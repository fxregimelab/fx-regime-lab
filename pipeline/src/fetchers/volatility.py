"""Realized vol from spot closes; implied vol from listed FX options (best effort)."""

from __future__ import annotations

import logging

import numpy as np
import yfinance as yf

from src.types import YF_TICKERS, SpotBar

logger = logging.getLogger(__name__)


def fetch_realized_vol(spots: dict[str, list[SpotBar]]) -> dict[str, dict[str, float]]:
    """Annualized realized vol (%) from log returns over 5d and 20d windows."""
    out: dict[str, dict[str, float]] = {}
    for pair, bars in spots.items():
        if len(bars) < 6:
            continue
        closes = np.array([b.close for b in bars], dtype=float)
        if np.any(closes <= 0):
            continue
        log_returns = np.diff(np.log(closes))
        if log_returns.size < 20:
            continue
        rv5 = float(np.std(log_returns[-5:], ddof=0) * np.sqrt(252) * 100)
        rv20 = float(np.std(log_returns[-20:], ddof=0) * np.sqrt(252) * 100)
        out[pair] = {"realized_vol_5d": rv5, "realized_vol_20d": rv20}
    return out


def fetch_implied_vol(pair: str) -> float | None:
    """ATM-ish implied vol from nearest listed expiry (>=25d); returns annualized % or None."""
    try:
        ticker_sym = YF_TICKERS[pair]
        t = yf.Ticker(ticker_sym)
        exps = list(t.options or [])
        if not exps:
            return None
        from datetime import date

        today = date.today()
        chosen: str | None = None
        for exp in exps:
            try:
                exp_d = date.fromisoformat(exp[:10])
            except ValueError:
                continue
            if (exp_d - today).days >= 25:
                chosen = exp
                break
        if chosen is None:
            chosen = exps[-1]
        chain = t.option_chain(chosen)
        calls = chain.calls
        if calls is None or calls.empty:
            return None
        spot = float(t.info.get("regularMarketPrice") or t.fast_info.get("last_price") or 0.0)
        if spot <= 0:
            hist = t.history(period="5d")
            if hist is not None and not hist.empty:
                spot = float(hist["Close"].iloc[-1])
        if spot <= 0:
            return None
        strikes = calls["strike"].astype(float)
        ivs = calls["impliedVolatility"].astype(float)
        mask = ivs.notna() & (ivs > 0)
        strikes = strikes[mask]
        ivs = ivs[mask]
        if strikes.empty:
            return None
        dist = (strikes.to_numpy(dtype=float) - spot).astype(float)
        order = np.argsort(np.abs(dist))[:5]
        iv_mean = float(ivs.iloc[order].mean())
        return iv_mean * 100.0
    except Exception as exc:  # noqa: BLE001
        logger.debug("implied vol unavailable for %s: %s", pair, exc)
        return None
