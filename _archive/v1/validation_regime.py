# validation_regime.py
# Next-trading-day check: yesterday's regime_calls vs realised 1D FX return → validation_log.

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

from config import TODAY
from core.paths import LATEST_WITH_COT_CSV
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client

"""
Regime validation Pipeline.

Execution context:
- Called by run.py as STEP 11 (validate)
- Depends on: create_html_brief.py (brief HTML must exist)
- Outputs: validation log only — no data files written
- Next step: deploy.py
- Blocking: NO — pipeline continues if this step fails

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

PAIR_TICKERS = {
    "EURUSD": "EURUSD=X",
    "USDJPY": "USDJPY=X",
    "USDINR": "USDINR=X",
}


def _predicted_direction_from_regime(regime: str, composite: Optional[float]) -> str:
    u = (regime or "").upper()
    if "LONG" in u and "SHORT" not in u:
        return "LONG"
    if "SHORT" in u:
        return "SHORT"
    if composite is not None:
        try:
            c = float(composite)
            if c > 5:
                return "LONG"
            if c < -5:
                return "SHORT"
        except (TypeError, ValueError):
            pass
    return "NEUTRAL"


def _actual_direction(ret: float) -> str:
    if ret > 1e-6:
        return "LONG"
    if ret < -1e-6:
        return "SHORT"
    return "NEUTRAL"


def _close_on_or_before(hist: pd.DataFrame, d: date) -> Optional[float]:
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None
    idx = pd.to_datetime(hist.index).tz_localize(None).normalize()
    mask = idx.date <= d
    if not mask.any():
        return None
    sub = hist.loc[mask]
    v = sub["Close"].iloc[-1]
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _close_after(hist: pd.DataFrame, d: date) -> Optional[float]:
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None
    idx = pd.to_datetime(hist.index).tz_localize(None).normalize()
    mask = idx.date > d
    if not mask.any():
        return None
    sub = hist.loc[mask]
    v = sub["Close"].iloc[0]
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_hist(pair: str) -> pd.DataFrame:
    t = PAIR_TICKERS.get(pair)
    if not t:
        return pd.DataFrame()
    try:
        tk = yf.Ticker(t)
        hist = tk.history(period="1mo", auto_adjust=True, timeout=30)
        return hist if hist is not None else pd.DataFrame()
    except Exception as e:
        try:
            from core.signal_write import log_pipeline_error
            log_pipeline_error("validation_regime", f"{t}: {e}", notes="yf_history")
        except Exception:
            pass
        return pd.DataFrame()


def _return_from_master(pair: str, pred_date: str, eval_date: str) -> Optional[float]:
    path = LATEST_WITH_COT_CSV
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
    except OSError:
        return None
    col = {"EURUSD": "EURUSD", "USDJPY": "USDJPY", "USDINR": "USDINR"}.get(pair)
    if not col or col not in df.columns:
        return None
    s = df[col].dropna()
    if s.empty:
        return None
    try:
        i0 = s.index.get_indexer([pd.Timestamp(pred_date)], method="pad")[0]
        i1 = s.index.get_indexer([pd.Timestamp(eval_date)], method="pad")[0]
    except Exception:
        return None
    if i0 < 0 or i1 < 0 or i0 >= len(s) or i1 >= len(s):
        return None
    p0 = float(s.iloc[i0])
    p1 = float(s.iloc[i1])
    if p0 <= 0:
        return None
    return (p1 / p0) - 1.0


def main() -> None:
    cli = get_client()
    if cli is None:
        print("  validation_regime: no Supabase client — skip")
        return

    try:
        yday = (date.fromisoformat(TODAY) - timedelta(days=1)).isoformat()
    except ValueError:
        print("  validation_regime: bad TODAY — skip")
        return

    for pair in ("EURUSD", "USDJPY", "USDINR"):
        try:
            res = (
                cli.table("regime_calls")
                .select("date, regime, confidence, signal_composite")
                .eq("pair", pair)
                .eq("date", yday)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if not rows:
                continue
            r = rows[0]
            regime = str(r.get("regime") or "")
            conf = r.get("confidence")
            comp = r.get("signal_composite")
            pred_dir = _predicted_direction_from_regime(regime, comp)

            hist = _load_hist(pair)
            p0 = _close_on_or_before(hist, date.fromisoformat(yday))
            p1 = _close_after(hist, date.fromisoformat(yday))
            ret: Optional[float] = None
            if p0 and p1 and p0 > 0:
                ret = (p1 / p0) - 1.0
            if ret is None:
                ret = _return_from_master(pair, yday, TODAY)
            if ret is None:
                log_pipeline_error(
                    "validation_regime",
                    f"no price window for {pair}",
                    pair=pair,
                    notes=f"pred_date={yday}",
                )
                continue

            act_dir = _actual_direction(ret)
            ok = pred_dir == act_dir if pred_dir != "NEUTRAL" else None

            payload: Dict[str, Any] = {
                "date": TODAY,
                "pair": pair,
                "predicted_direction": pred_dir,
                "predicted_regime": regime[:30] if regime else None,
                "confidence": float(conf) if conf is not None else None,
                "actual_direction": act_dir,
                "actual_return_1d": float(ret),
                "correct_1d": ok,
            }
            cli.table("validation_log").upsert([payload], on_conflict="date,pair").execute()
        except Exception as e:
            log_pipeline_error("validation_regime", str(e), pair=pair)
            print(f"  validation_regime WARN {pair}: {e}")

    print("  validation_regime: done")


if __name__ == "__main__":
    main()
    sys.exit(0)
