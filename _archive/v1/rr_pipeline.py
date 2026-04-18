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
from typing import Optional

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


def _layer3_strict() -> bool:
    return os.environ.get("LAYER3_STRICT") == "1"


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


def _expiry_candidates(ticker) -> list[tuple[str, int]]:
    """Ordered list of (expiry_str, dte): prefer 20–45d, then 10–60d, then 5–120d."""
    try:
        expirations = ticker.options or []
    except Exception:
        return []
    today = datetime.today().date()
    preferred: list[tuple[str, int]] = []
    secondary: list[tuple[str, int]] = []
    fallback: list[tuple[str, int]] = []
    for exp in expirations:
        try:
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
        except ValueError:
            continue
        if dte < 5 or dte > 120:
            continue
        if 20 <= dte <= 45:
            preferred.append((exp, dte))
        elif 10 <= dte <= 60:
            secondary.append((exp, dte))
        else:
            fallback.append((exp, dte))
    preferred.sort(key=lambda x: x[1])
    secondary.sort(key=lambda x: abs(x[1] - 32))
    fallback.sort(key=lambda x: abs(x[1] - 32))
    return preferred + secondary + fallback


def _interp_iv_at_delta(
    chain: pd.DataFrame,
    target_delta: float,
    spot: float,
    T: float,
    r: float,
    is_call: bool,
    *,
    max_spread_pct: float = 0.30,
) -> Optional[float]:
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
    c = c[spread_pct < max_spread_pct]
    if c.empty:
        return None

    c["delta"] = c.apply(
        lambda row: _bs_delta(spot, float(row["strike"]), T, r, float(row["impliedVolatility"]), is_call),
        axis=1,
    )
    c = c.dropna(subset=["delta"])
    if is_call:
        wing = c[(c["delta"] >= 0.12) & (c["delta"] <= 0.38)]
    else:
        wing = c[(c["delta"] >= -0.38) & (c["delta"] <= -0.12)]
    if wing.empty:
        return None
    if len(wing) == 1:
        d0 = float(wing["delta"].iloc[0])
        if abs(d0 - target_delta) < 0.10:
            return float(wing["impliedVolatility"].iloc[0])
        return None
    wing = wing.sort_values("delta")
    try:
        return float(np.interp(target_delta, wing["delta"].to_numpy(), wing["impliedVolatility"].to_numpy()))
    except Exception:
        return None


_CALL_DELTA_TARGETS = (0.25, 0.22, 0.28, 0.20, 0.30, 0.18, 0.32)
_PUT_DELTA_TARGETS = (-0.25, -0.22, -0.28, -0.20, -0.30, -0.18, -0.32)


def _wing_rr_vol_points(
    calls: pd.DataFrame,
    puts: pd.DataFrame,
    spot: float,
    T: float,
    r: float,
) -> Optional[float]:
    """Try 25d RR with multiple delta targets and slightly wider spreads."""
    for max_sp in (0.30, 0.50):
        for tc, tp in zip(_CALL_DELTA_TARGETS, _PUT_DELTA_TARGETS):
            iv_c = _interp_iv_at_delta(calls, tc, spot, T, r, True, max_spread_pct=max_sp)
            iv_p = _interp_iv_at_delta(puts, tp, spot, T, r, False, max_spread_pct=max_sp)
            if iv_c is not None and iv_p is not None:
                return (iv_c - iv_p) * 100.0
    return None


def _atm_iv_rr_vol_points(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> Optional[float]:
    """Fallback: call IV minus put IV at each side's strike nearest spot (ATM proxy)."""
    def _clean(ch: pd.DataFrame) -> Optional[pd.DataFrame]:
        if ch is None or ch.empty:
            return None
        req = {"strike", "impliedVolatility"}
        if not req.issubset(ch.columns):
            return None
        x = ch.copy()
        x["strike"] = pd.to_numeric(x["strike"], errors="coerce")
        x["iv"] = pd.to_numeric(x["impliedVolatility"], errors="coerce")
        x = x.dropna(subset=["strike", "iv"])
        x = x[x["iv"] > 0]
        return x if not x.empty else None

    cc = _clean(calls)
    pp = _clean(puts)
    if cc is None or pp is None:
        return None
    ic = (cc["strike"] - spot).abs().idxmin()
    ip = (pp["strike"] - spot).abs().idxmin()
    iv_c = float(cc.loc[ic, "iv"])
    iv_p = float(pp.loc[ip, "iv"])
    return (iv_c - iv_p) * 100.0


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
        if _layer3_strict():
            print("  rr_pipeline: LAYER3_STRICT — yfinance required")
            sys.exit(1)
        _write_csv(None)
        return

    try:
        t = yf.Ticker("FXE")
        hist = t.history(period="5d", auto_adjust=True, timeout=30)
        if hist is None or hist.empty:
            print("  rr_pipeline: FXE price history empty — skipping")
            if _layer3_strict():
                print("  rr_pipeline: LAYER3_STRICT — FXE history required")
                sys.exit(1)
            _write_csv(None)
            return
        spot = float(hist["Close"].dropna().iloc[-1])
    except Exception as e:
        log_pipeline_error("rr_pipeline", f"spot fetch: {e}", pair="EURUSD", notes="yf_history")
        if _layer3_strict():
            print("  rr_pipeline: LAYER3_STRICT — FXE spot fetch failed")
            sys.exit(1)
        _write_csv(None)
        return

    candidates = _expiry_candidates(t)
    if not candidates:
        print("  rr_pipeline: no usable option expiries — skipping")
        if _layer3_strict():
            print("  rr_pipeline: LAYER3_STRICT — option expiries required")
            sys.exit(1)
        _write_csv(None)
        return

    chain_err: Optional[Exception] = None
    for expiry, dte in candidates:
        try:
            chain = t.option_chain(expiry)
        except Exception as e:
            chain_err = e
            continue
        T = max(dte, 1) / 365.0
        n_c = len(chain.calls) if getattr(chain, "calls", None) is not None else 0
        n_p = len(chain.puts) if getattr(chain, "puts", None) is not None else 0
        rr = _wing_rr_vol_points(chain.calls, chain.puts, spot, T, _RISK_FREE_RATE)
        method = "25d_wing"
        if rr is None:
            rr = _atm_iv_rr_vol_points(chain.calls, chain.puts, spot)
            method = "atm_proxy"
        if rr is not None:
            print(f"  rr_pipeline: EURUSD RR = {rr:+.3f} vol pts ({method}, expiry {expiry}, {dte}d)")
            _write_csv(rr)
            _upsert_signal(rr)
            return
        log_pipeline_error(
            "rr_pipeline",
            f"expiry {expiry} dte={dte}d: wing+ATM failed (n_calls={n_c}, n_puts={n_p})",
            pair="EURUSD",
            notes="rr_interp",
        )

    if chain_err is not None:
        log_pipeline_error("rr_pipeline", f"option_chain: {chain_err}", pair="EURUSD", notes="yf_chain")
    print("  rr_pipeline: all expiries failed wing+ATM interpolation — skipping")
    if _layer3_strict():
        print("  rr_pipeline: LAYER3_STRICT — RR interpolation required")
        sys.exit(1)
    _write_csv(None)


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
