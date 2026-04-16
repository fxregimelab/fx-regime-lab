# core/utils.py
# Single home for all shared helper functions used across the fx_regime pipeline.
# Import from here instead of defining locally in each module.

import os
import re
import base64
import math
import pandas as pd


# ── yfinance safe wrapper ────────────────────────────────────────────────────
#
# Phase 2: every yfinance call in the pipeline must go through this wrapper.
# Enforces timeout, try/except, non-empty frame, and logs failures to
# pipeline_errors. NEVER raises — returns an empty DataFrame on any error so
# callers' existing NaN/ffill paths degrade gracefully.

def _yf_safe_download(tickers, **kw):
    """Wrap yf.download with timeout + try/except + pipeline_errors logging."""
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame()
    kw.setdefault("timeout", 30)
    kw.setdefault("progress", False)
    try:
        df = yf.download(tickers, **kw)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        try:
            from core.signal_write import log_pipeline_error
            log_pipeline_error("yfinance", f"{tickers}: {e}", notes="safe_download")
        except Exception:
            pass
        return pd.DataFrame()


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
