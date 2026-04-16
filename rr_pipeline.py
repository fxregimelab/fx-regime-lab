# rr_pipeline.py
# Phase 5 — Synthetic 25-delta risk reversal for EUR/USD via FXE options chain.
#
# FXE (Invesco CurrencyShares Euro Trust) is the most-liquid listed EUR/USD
# proxy. We pull its option chain from yfinance, pick the nearest 20–45-day
# expiry, interpolate Black-Scholes delta vs. implied vol across the wings,
# and compute RR = iv_call_25Δ − iv_put_25Δ (vol points). Only EUR/USD is
# covered — USD/JPY (FXY) and USD/INR stay NULL.
#
# Writes:
#   data/rr_latest.csv    — sidecar picked up by pipeline.merge_main()
#   Supabase signals.risk_reversal_25d
# Never raises into run.py — main() always sys.exit(0).

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from config import TODAY
from core.paths import DATA_DIR
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client


"""
Synthetic risk reversal (RR) Pipeline.

Execution context:
- Called by run.py as STEP 6 (rr)
- Depends on: oi_pipeline.py
- Outputs: data/rr_latest.csv + Supabase signals.risk_reversal_25d (EUR/USD)
- Next step: morning_brief.py
- Blocking: YES — main() must ALWAYS sys.exit(0)

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

_RR_LATEST_CSV = os.path.join(DATA_DIR, "rr_latest.csv")

# Risk-free rate proxy for Black-Scholes delta calc. RR is relatively
# insensitive to r at 20–45 DTE; 4% is a reasonable mid-cycle USD rate.
_RISK_FREE_RATE = 0.04


def _bs_delta(spot: float, strike: float, T: float, r: float, iv: float, is_call: bool) -> float:
    """Black-Scholes delta (non-dividend-adjusted — acceptable for FXE)."""
    try:
        from scipy.stats import norm
    except ImportError:
        return float("nan")
    if iv <= 0 or T <= 0 or spot <= 0 or strike <= 0:
        return float("nan")
    d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * T) / (iv * np.sqrt(T))
    if is_call:
        return float(norm.cdf(d1))
    return float(norm.cdf(d1) - 1.0)


def _pick_expiry(ticker) -> Tuple[Optional[str], Optional[int]]:
    """Nearest expiry in the 20–45 DTE window (tenor bucket the desk prefers)."""
    try:
        expirations = ticker.options or []
    except Exception:
        return None, None
    today = datetime.today().date()
    best = None
    for exp in expirations:
        try:
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
        except ValueError:
            continue
        if 20 <= dte <= 45:
            if best is None or dte < best[1]:
                best = (exp, dte)
    if best:
        return best
    return None, None


def _interp_iv_at_delta(chain: pd.DataFrame, target_delta: float, spot: float,
                         T: float, r: float, is_call: bool) -> Optional[float]:
    """Filter chain (tight spreads, wing delta band), interpolate IV at target delta."""
    if chain is None or chain.empty:
        return None
    required = {"strike", "bid", "ask", "impliedVolatility"}
    if not required.issubset(chain.columns):
        return None
    c = chain.copy()
    c["bid"] = pd.to_numeric(c["bid"], errors="coerce")
    c["ask"] = pd.to_numeric(c["ask"], errors="coerce")
    c["impliedVolatility"] = pd.to_numeric(c["impliedVolatility"], errors="coerce")
    c = c.dropna(subset=["bid", "ask", "impliedVolatility", "strike"])
    c = c[(c["bid"] > 0) & (c["ask"] > 0) & (c["impliedVolatility"] > 0)]
    if c.empty:
        return None
    mid = (c["bid"] + c["ask"]) / 2.0
    spread_pct = (c["ask"] - c["bid"]) / mid.replace(0, np.nan)
    c = c[spread_pct < 0.30]
    if c.empty:
        return None

    c["delta"] = c.apply(
        lambda row: _bs_delta(spot, float(row["strike"]), T, r, float(row["impliedVolatility"]), is_call),
        axis=1,
    )
    c = c.dropna(subset=["delta"])
    if is_call:
        wing = c[(c["delta"] >= 0.15) & (c["delta"] <= 0.35)]
    else:
        wing = c[(c["delta"] >= -0.35) & (c["delta"] <= -0.15)]
    if len(wing) < 2:
        return None
    wing = wing.sort_values("delta")
    try:
        return float(np.interp(target_delta, wing["delta"].to_numpy(), wing["impliedVolatility"].to_numpy()))
    except Exception:
        return None


def _write_csv(rr_value: Optional[float]) -> None:
    """Always write a sidecar — empty means "no RR today" (NaN in master)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if rr_value is None:
        df = pd.DataFrame(columns=["date", "pair", "risk_reversal_25d"])
    else:
        df = pd.DataFrame([{
            "date": TODAY,
            "pair": "EURUSD",
            "risk_reversal_25d": rr_value,
        }])
    tmp = _RR_LATEST_CSV + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, _RR_LATEST_CSV)
    print(f"  rr_pipeline: wrote {_RR_LATEST_CSV} ({len(df)} rows)")


def _upsert_signal(rr_value: float) -> None:
    cli = get_client()
    if cli is None:
        print("  rr_pipeline: Supabase client unavailable — CSV only")
        return
    row = {"date": TODAY, "pair": "EURUSD", "risk_reversal_25d": float(rr_value)}
    try:
        cli.table("signals").upsert([row], on_conflict="date,pair").execute()
        print(f"  rr_pipeline: upserted EURUSD risk_reversal_25d={rr_value:+.3f}")
    except Exception as e:
        log_pipeline_error("rr_pipeline", str(e), notes="signals upsert", pair="EURUSD")


def main() -> None:
    print("  rr_pipeline: Synthetic 25-delta RR via FXE proxy (Phase 5)")
    try:
        import yfinance as yf
    except ImportError:
        print("  rr_pipeline: yfinance not installed — skipping")
        _write_csv(None)
        return

    try:
        t = yf.Ticker("FXE")
        hist = t.history(period="5d", auto_adjust=True, timeout=30)
        if hist is None or hist.empty:
            print("  rr_pipeline: FXE price history empty — skipping")
            _write_csv(None)
            return
        spot = float(hist["Close"].dropna().iloc[-1])
    except Exception as e:
        log_pipeline_error("rr_pipeline", f"spot fetch: {e}", pair="EURUSD", notes="yf_history")
        _write_csv(None)
        return

    expiry, dte = _pick_expiry(t)
    if expiry is None or dte is None:
        print("  rr_pipeline: no expiry in 20–45d window — skipping")
        _write_csv(None)
        return

    try:
        chain = t.option_chain(expiry)
    except Exception as e:
        log_pipeline_error("rr_pipeline", f"option_chain {expiry}: {e}", pair="EURUSD", notes="yf_chain")
        _write_csv(None)
        return

    T = max(dte, 1) / 365.0
    iv_call = _interp_iv_at_delta(chain.calls, 0.25, spot, T, _RISK_FREE_RATE, True)
    iv_put = _interp_iv_at_delta(chain.puts, -0.25, spot, T, _RISK_FREE_RATE, False)

    if iv_call is None or iv_put is None:
        print(f"  rr_pipeline: wing interpolation failed (call={iv_call}, put={iv_put}) — skipping")
        _write_csv(None)
        return

    rr = (iv_call - iv_put) * 100.0  # convert to vol points
    print(f"  rr_pipeline: EURUSD 25d RR = {rr:+.3f} vol pts (expiry {expiry}, {dte}d)")
    _write_csv(rr)
    _upsert_signal(rr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"  rr_pipeline: unexpected error — {e}")
        try:
            log_pipeline_error("rr_pipeline", str(e), notes="main")
        except Exception:
            pass
    sys.exit(0)
