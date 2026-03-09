# core/utils.py
# Single home for all shared helper functions used across the fx_regime pipeline.
# Import from here instead of defining locally in each module.

import os
import base64
import math
import pandas as pd


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
    if pd.isna(val):
        return "  n/a  "
    return f"{val:>+.2f}%"


def _pp(val):
    """Format a basis-point pp change for text briefs: '+0.25pp', or '  n/a  '."""
    if pd.isna(val):
        return "  n/a  "
    rounded = round(val, 2)
    if abs(rounded) < 0.005:
        return "+0.00pp"
    return f"{val:>+.2f}pp"


def _net(val):
    """Format net futures contracts: '+12,345' or 'n/a'."""
    if pd.isna(val):
        return "n/a"
    return f"{val:>+,.0f}"


# ── file helpers ─────────────────────────────────────────────────────────────

def embed_image(filepath):
    """Return a base64 data URI for an image file, or '' if not found.
    Only serves files within the repository root to prevent path traversal.
    """
    try:
        abs_path = os.path.realpath(os.path.abspath(filepath))
        repo_root = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
