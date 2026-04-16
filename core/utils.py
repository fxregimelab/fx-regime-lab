# core/utils.py
# Single home for all shared helper functions used across the fx_regime pipeline.
# Import from here instead of defining locally in each module.

import os
import re
import base64
import math
from typing import List, Optional, Sequence, Union

import pandas as pd


def _yahoo_ticker_to_polygon(yahoo_ticker: str) -> Optional[str]:
    """Map a Yahoo Finance symbol to Polygon aggregates ticker, or None if unsupported."""
    y = str(yahoo_ticker).strip()
    known = {
        "EURUSD=X": "C:EURUSD",
        "JPY=X": "C:USDJPY",
        "USDINR=X": "C:USDINR",
        "^VIX": "I:VIX",
        "^EVZ": "I:EVZ",
        "^JYVIX": "I:JYVIX",
    }
    if y in known:
        return known[y]
    if y.endswith("=X") and len(y) >= 7:
        core = y.replace("=X", "").replace("-", "").upper()
        if len(core) == 6 and core.isalpha():
            return f"C:{core}"
    if y.startswith("^") and len(y) > 1:
        return "I:" + y[1:].upper()
    return None


def _polygon_aggs_to_yf_like_df(
    poly_ticker: str,
    start_d: str,
    end_d: str,
    api_key: str,
) -> Optional[pd.DataFrame]:
    """Fetch Polygon 1-day aggs and return a yfinance-shaped single-ticker DataFrame."""
    try:
        import requests
    except ImportError:
        return None
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{poly_ticker}"
        f"/range/1/day/{start_d}/{end_d}"
    )
    try:
        r = requests.get(
            url,
            params={
                "apiKey": api_key,
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
            },
            timeout=45,
        )
        payload = r.json()
    except Exception:
        return None
    if r.status_code != 200 or not isinstance(payload, dict):
        return None
    results = payload.get("results") or []
    if not results:
        return None
    rows = []
    for bar in results:
        ts = bar.get("t")
        if ts is None:
            continue
        dt = pd.to_datetime(int(ts), unit="ms", utc=True).tz_convert(None).normalize()
        o = float(bar.get("o") or bar.get("O") or 0)
        h = float(bar.get("h") or bar.get("H") or 0)
        lo = float(bar.get("l") or bar.get("L") or 0)
        c = float(bar.get("c") or bar.get("C") or 0)
        v = float(bar.get("v") or bar.get("V") or 0)
        rows.append((dt, o, h, lo, c, v))
    if not rows:
        return None
    idx = pd.DatetimeIndex([x[0] for x in rows])
    out = pd.DataFrame(
        {
            "Open": [x[1] for x in rows],
            "High": [x[2] for x in rows],
            "Low": [x[3] for x in rows],
            "Close": [x[4] for x in rows],
            "Adj Close": [x[4] for x in rows],
            "Volume": [x[5] for x in rows],
        },
        index=idx,
    )
    out.index.name = "Date"
    return out


def _polygon_fallback_download(
    tickers: Union[str, Sequence[str]],
    start_d: str,
    end_d: str,
    api_key: str,
) -> Optional[pd.DataFrame]:
    """Build a yfinance-compatible frame from Polygon daily aggs (per ticker)."""
    if isinstance(tickers, str):
        tlist: List[str] = [tickers]
    else:
        tlist = [str(t) for t in tickers]
    if len(tlist) == 1:
        poly = _yahoo_ticker_to_polygon(tlist[0])
        if not poly:
            return None
        return _polygon_aggs_to_yf_like_df(poly, start_d, end_d, api_key)
    close_frames = []
    for y in tlist:
        poly = _yahoo_ticker_to_polygon(y)
        if not poly:
            continue
        one = _polygon_aggs_to_yf_like_df(poly, start_d, end_d, api_key)
        if one is None or one.empty or "Close" not in one.columns:
            continue
        s = pd.to_numeric(one["Close"], errors="coerce")
        s.name = y
        close_frames.append(s)
    if not close_frames:
        return None
    merged = pd.concat(close_frames, axis=1).sort_index()
    ycols = [str(c) for c in merged.columns.tolist()]
    merged.columns = pd.MultiIndex.from_product([["Close"], ycols])
    return merged


def _yf_frame_has_close(raw: Optional[pd.DataFrame]) -> bool:
    """True if frame has a Close series (flat or MultiIndex columns, yfinance-style)."""
    if raw is None or raw.empty:
        return False
    if "Close" in raw.columns:
        return True
    cols = raw.columns
    if isinstance(cols, pd.MultiIndex):
        return "Close" in cols.get_level_values(0)
    return False


# ── yfinance safe wrapper ────────────────────────────────────────────────────
#
# Phase 2: every yfinance call in the pipeline must go through this wrapper.
# On yfinance failure: if POLYGON_KEY is set, Polygon.io daily aggs are used
# when the Yahoo symbol maps to a Polygon ticker. Otherwise logs and returns
# None so callers treat missing data explicitly.

def _yf_safe_download(tickers, **kw):
    """Wrap yf.download with timeout; optional Polygon fallback; returns None on total failure."""
    try:
        import yfinance as yf
    except ImportError:
        return None
    kw.setdefault("timeout", 30)
    kw.setdefault("progress", False)
    df = None
    y_err = None
    try:
        df = yf.download(tickers, **kw)
    except Exception as e:
        y_err = e

    from config import POLYGON_KEY, START_DATE, TODAY
    from core.signal_write import log_pipeline_error

    start_d = str(kw.get("start") or START_DATE)[:10]
    end_d = str(kw.get("end") or TODAY)[:10]

    ok = df is not None and not df.empty
    if ok:
        return df

    if POLYGON_KEY:
        try:
            poly_df = _polygon_fallback_download(
                tickers, start_d, end_d, POLYGON_KEY,
            )
            if poly_df is not None and not poly_df.empty:
                return poly_df
        except Exception as poly_exc:
            try:
                log_pipeline_error(
                    "yfinance",
                    f"{tickers}: Polygon fallback error: {poly_exc}",
                    notes="safe_download_polygon",
                )
            except Exception:
                pass
        try:
            msg = (
                f"{tickers}: yfinance failed"
                + (f" ({y_err})" if y_err else " (empty)")
                + "; Polygon fallback failed or unmapped ticker"
            )
            log_pipeline_error("yfinance", msg, notes="safe_download_polygon")
        except Exception:
            pass
        return None

    try:
        if y_err:
            log_pipeline_error(
                "yfinance", f"{tickers}: {y_err}", notes="safe_download",
            )
        else:
            log_pipeline_error(
                "yfinance",
                f"{tickers}: empty download (POLYGON_KEY unset)",
                notes="safe_download",
            )
    except Exception:
        pass
    return None


# ── brief text cleaner (Python port of site/terminal/data-client.js) ─────────
#
# Strips markdown syntax before Supabase brief_log.brief_text upsert so the
# dashboard shows clean prose. Port of cleanBriefText in data-client.js.

_BRIEF_MD_INLINE = re.compile(r"(\*\*|__|\*|_|`|~~)")
_BRIEF_MD_HEADING = re.compile(r"^#{1,6}\s*", flags=re.MULTILINE)
_BRIEF_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BRIEF_MD_BLANKS = re.compile(r"\n{3,}")


def _clean_brief_text(raw):
    """Strip markdown (headings, inline emphasis, links) from a brief text blob."""
    if not raw or not isinstance(raw, str):
        return ""
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = _BRIEF_MD_LINK.sub(r"\1", t)
    t = _BRIEF_MD_HEADING.sub("", t)
    t = _BRIEF_MD_INLINE.sub("", t)
    t = _BRIEF_MD_BLANKS.sub("\n\n", t)
    return t.strip()


# ── number / text formatters ─────────────────────────────────────────────────

def ordinal(n):
    """Return integer n with its ordinal suffix: 1→'1st', 11→'11th', etc."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def fmt_pct(val, suffix='%', decimals=2):
    """Format a float as a signed percentage string. Returns '—' on error."""
    try:
        v = float(val)
        sign = '+' if v >= 0 else ''
        return f"{sign}{v:.{decimals}f}{suffix}"
    except Exception:
        return '—'


def color_class(val):
    """Return 'positive' or 'negative' CSS class string based on sign."""
    try:
        return 'positive' if float(val) >= 0 else 'negative'
    except Exception:
        return ''


def _pct(val):
    """Format a pct change for text briefs: '+1.23%', or '  n/a  ' on NaN."""
    try:
        if pd.isna(val):
            return "  n/a  "
        return f"{float(val):>+.2f}%"
    except (TypeError, ValueError):
        return "  n/a  "


def _pp(val):
    """Format a basis-point pp change for text briefs: '+0.25pp', or '  n/a  '."""
    try:
        if pd.isna(val):
            return "  n/a  "
        v = float(val)
        rounded = round(v, 2)
        if abs(rounded) < 0.005:
            return "+0.00pp"
        return f"{v:>+.2f}pp"
    except (TypeError, ValueError):
        return "  n/a  "


def _net(val):
    """Format net futures contracts: '+12,345' or 'n/a'."""
    try:
        if pd.isna(val):
            return "n/a"
        return f"{float(val):>+,.0f}"
    except (TypeError, ValueError):
        return "n/a"


# ── file helpers ─────────────────────────────────────────────────────────────

def embed_image(filepath):
    """Return a base64 data URI for an image file, or '' if not found.
    Only serves files within the repository root to prevent path traversal.
    """
    try:
        repo_root = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Resolve relative paths from repo root (not CWD) so the path is stable
        # regardless of which directory the script is launched from
        if not os.path.isabs(filepath):
            abs_path = os.path.realpath(os.path.join(repo_root, filepath))
        else:
            abs_path = os.path.realpath(filepath)
        # Block access outside the repo directory
        if not abs_path.startswith(repo_root + os.sep) and abs_path != repo_root:
            return ""
    except Exception:
        return ""
    if not os.path.exists(abs_path):
        return ""
    ext = os.path.splitext(filepath)[1].lower().lstrip('.')
    mime = {
        'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'gif': 'image/gif', 'svg': 'image/svg+xml',
    }.get(ext, 'image/png')
    try:
        with open(abs_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""


# ── interpretation helpers ────────────────────────────────────────────────────

def _dxy_corr_label(corr, pair):
    """Return (badge_text, is_dollar_regime) for a DXY correlation value.

    Expected signs per pair:
      EUR/USD  strong negative  (DXY up = EUR/USD down, opposite direction)
      USD/JPY  strong positive  (DXY up = USD/JPY up, same direction)
      USD/INR  strong positive  (DXY up = USD/INR up, dollar drives)

    Regime badges:
      EUR/USD: corr < -0.60 = DOLLAR REGIME | -0.60→-0.30 = MIXED | > -0.30 = EUR SPECIFIC
      USD/JPY: corr > +0.60 = DOLLAR REGIME | +0.30→+0.60 = MIXED | < +0.30 = YEN SPECIFIC
      USD/INR: corr > +0.60 = DOLLAR REGIME | +0.30→+0.60 = MIXED | < +0.30 = INDIA SPECIFIC
    """
    if pd.isna(corr):
        return "NO DATA", False

    if pair == "EURUSD":
        if corr < -0.60:
            return "DOLLAR REGIME", True
        elif corr < -0.30:
            return "MIXED", False
        else:
            return "EUR SPECIFIC", False
    elif pair == "USDJPY":
        if corr > 0.60:
            return "DOLLAR REGIME", True
        elif corr > 0.30:
            return "MIXED", False
        else:
            return "YEN SPECIFIC", False
    elif pair == "USDINR":
        if corr > 0.60:
            return "DOLLAR REGIME", True
        elif corr > 0.30:
            return "MIXED", False
        else:
            return "INDIA SPECIFIC", False
    return "UNKNOWN", False


def _oil_corr_label(corr, pair):
    """Return (badge_text, is_divergence) for an oil correlation value.

    Expected signs per pair:
      EUR/USD  negative  (oil up → EUR weaker via trade deficit)
      USD/JPY  positive  (oil up → JPY weaker via trade deficit)
      USD/INR  positive  (oil up → INR weaker via import cost)

    Divergence = sign reversal beyond threshold.
    Magnitude badge: |corr| > 0.5 = HIGH, 0.3-0.5 = MODERATE, < 0.3 = LOW
    """
    if pd.isna(corr):
        return "NO DATA", False

    # divergence check: sign flips from expected
    divergence = False
    if pair == "EURUSD" and corr > 0.20:
        divergence = True
    elif pair == "USDJPY" and corr < -0.20:
        divergence = True
    elif pair == "USDINR" and corr < -0.20:
        divergence = True

    if divergence:
        return "OIL DIVERGENCE", True

    abs_c = abs(corr)
    if abs_c >= 0.50:
        return "HIGH", False
    elif abs_c >= 0.30:
        return "MODERATE", False
    else:
        return "LOW", False


def _gold_corr_label(corr, pair):
    """Return (badge_text, is_divergence) for a gold correlation value.

    Expected signs per pair:
      USD/JPY  negative  (gold up -> safe-haven flow -> JPY strengthens -> USD/JPY down)
      USD/INR  positive  (gold up -> India import demand -> USD buying -> INR weaker)
      EUR/USD  excluded  (EUR/gold relationship structurally unstable)

    Divergence = sign reversal beyond threshold.
    Magnitude badge: |corr| >= 0.60 = STRONG, 0.30-0.60 = MODERATE, < 0.30 = WEAK
    """
    if pd.isna(corr):
        return "NO DATA", False

    # divergence check: sign reversal from expected
    divergence = False
    if pair == "USDJPY" and corr > 0.20:
        divergence = True
    elif pair == "USDINR" and corr < -0.20:
        divergence = True

    if divergence:
        return "GOLD DIVERGENCE", True

    abs_c = abs(corr)
    if abs_c >= 0.60:
        return "STRONG", False
    elif abs_c >= 0.30:
        return "MODERATE", False
    else:
        return "WEAK", False


def _rbi_intervention_label(flag):
    """Return (display_text, color, is_active) for an RBI intervention flag string.
    ACTIVE SUPPORT = RBI selling USD to defend INR floor (teal)
    ACTIVE CAPPING = RBI buying USD to limit appreciation (amber)
    NEUTRAL        = no significant reserve change
    """
    try:
        if pd.isna(flag):
            return "UNKNOWN", "#555555", False
    except TypeError:
        pass
    mapping = {
        "ACTIVE SUPPORT": ("ACTIVE SUPPORT", "#00d4aa", True),
        "ACTIVE CAPPING": ("ACTIVE CAPPING", "#f0a500", True),
        "NEUTRAL":        ("NEUTRAL",        "#888888", False),
        "UNKNOWN":        ("UNKNOWN",        "#555555", False),
    }
    return mapping.get(str(flag), ("UNKNOWN", "#555555", False))


def _inr_score_label(score):
    """Return a severity label for the INR composite regime score."""
    if pd.isna(score): return "UNKNOWN"
    if score >  60:    return "STRONG DEPRECIATION PRESSURE"
    if score >  30:    return "MODERATE DEPRECIATION PRESSURE"
    if score > -30:    return "NEUTRAL"
    if score > -60:    return "MODERATE APPRECIATION PRESSURE"
    return "STRONG APPRECIATION PRESSURE"


def _btp_bund_label(flag):
    """Return (display_text, color) for a BTP-Bund spread flag.

    STRESS   = spread > 2.5pp  → red     (Italian sovereign risk flaring)
    ELEVATED = spread > 1.8pp  → amber   (worth monitoring)
    NORMAL   = spread <= 1.8pp → grey    (benign)
    """
    mapping = {
        "STRESS":      ("STRESS",      "#ff4444"),
        "ELEVATED":    ("ELEVATED",    "#f0a500"),
        "NORMAL":      ("NORMAL",      "#888888"),
        "UNAVAILABLE": ("N/A",         "#555555"),
    }
    return mapping.get(str(flag), ("UNKNOWN", "#555555"))


def _g10_score_label(score):
    """Return a direction label for EUR/USD or USD/JPY composite regime score.

    Score > 0  = USD strength pressure against that pair.
    Score < 0  = USD weakness / foreign-currency strength pressure.
    """
    if pd.isna(score): return "UNKNOWN"
    if score >  60:    return "STRONG USD STRENGTH"
    if score >  30:    return "MODERATE USD STRENGTH"
    if score > -30:    return "NEUTRAL"
    if score > -60:    return "MODERATE USD WEAKNESS"
    return "STRONG USD WEAKNESS"


def _eur_interpretation(spread_10y, spread_10y_12m,
                         lev_pct, lev_net,
                         am_pct, am_net):
    """One-line plain English read on EUR/USD regime.

    Adds special language when both leveraged money and asset manager
    percentiles are simultaneously crowded in the same direction.
    """
    # direction from spread
    if spread_10y_12m < -0.10:
        direction = "spread compression supports EUR strength"
    elif spread_10y_12m > 0.10:
        direction = "spread widening supports USD strength"
    else:
        direction = "spreads flat, no directional signal from differentials"

    # dual crowding check
    if lev_pct >= 80 and am_pct >= 80 and lev_net > 0 and am_net > 0:
        crowding = (
            f"Leveraged Money {ordinal(lev_pct)} pct and Asset Manager {ordinal(am_pct)} pct "
            "both crowded long — dual category confirmation, strongest reversal "
            "risk signal this framework produces"
        )
    elif lev_pct <= 20 and am_pct <= 20 and lev_net < 0 and am_net < 0:
        crowding = (
            f"Leveraged Money {ordinal(lev_pct)} pct and Asset Manager {ordinal(am_pct)} pct "
            "both crowded short — dual category confirmation, strongest squeeze "
            "signal this framework produces"
        )
    else:
        # single-category or neutral descriptions (existing language)
        if lev_pct >= 80:
            crowding = "positioning crowded — asymmetric reversal risk, easy move likely priced"
        elif lev_pct <= 20:
            crowding = "positioning crowded short — squeeze risk if EUR catalyst appears"
        else:
            crowding = "positioning neutral — no crowding distortion"

    return f"{direction}; {crowding}."


def _jpy_interpretation(spread_10y, spread_10y_12m,
                         lev_pct, lev_net,
                         am_pct, am_net):
    """One-line plain English read on USD/JPY regime.

    Applies the same dual confirmation language when both categories are crowded.
    """
    if spread_10y_12m < -0.10:
        direction = "spread compression favors lower USD/JPY"
    elif spread_10y_12m > 0.10:
        direction = "spread widening favors higher USD/JPY"
    else:
        direction = "spreads flat, no directional signal"

    # dual crowding
    if lev_pct >= 80 and am_pct >= 80 and lev_net > 0 and am_net > 0:
        crowding = (
            f"Leveraged Money {ordinal(lev_pct)} pct and Asset Manager {ordinal(am_pct)} pct "
            "both crowded long — dual category confirmation, strongest reversal "
            "risk signal this framework produces"
        )
    elif lev_pct <= 20 and am_pct <= 20 and lev_net < 0 and am_net < 0:
        crowding = (
            f"Leveraged Money {ordinal(lev_pct)} pct and Asset Manager {ordinal(am_pct)} pct "
            "both crowded short — dual category confirmation, strongest squeeze "
            "signal this framework produces"
        )
    elif 20 < lev_pct < 80 and 20 < am_pct < 80:
        crowding = (
            f"Leveraged Money {ordinal(lev_pct)} pct and Asset Manager {ordinal(am_pct)} pct "
            "both neutral — carry partially intact, BoJ path is key variable"
        )
    else:
        if lev_pct <= 20:
            crowding = "yen shorts crowded — unwind/squeeze risk elevated"
        elif lev_pct >= 80:
            crowding = "yen longs crowded — reversal risk if BoJ disappoints"
        elif lev_net < 0:
            crowding = f"carry trade partially intact ({ordinal(lev_pct)} pct) — BoJ path is key variable"
        else:
            crowding = f"carry trade unwound, net long yen ({ordinal(lev_pct)} pct) — watch BoJ forward guidance"

    return f"{direction}; {crowding}."
