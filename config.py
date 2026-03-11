# config.py
# All configuration lives here. Change settings in one place, affects everything.

from datetime import datetime
import pandas as pd

# ── DATES ────────────────────────────────────────────────────
TODAY      = datetime.today().strftime('%Y-%m-%d')
TODAY_FMT  = datetime.today().strftime('%A, %d %B %Y')
DATE_SLUG  = TODAY.replace('-', '')
START_DATE = "2020-01-01"   # 5 years of history is enough for regime work

# ── CROWDING / VOLATILITY THRESHOLDS ────────────────────────────────────────
CROWDING_HIGH  = 80   # percentile above which positioning is "crowded"
CROWDING_LOW   = 20   # percentile below which positioning is "crowded short"
EXTENDED_HIGH  = 70   # percentile for "extended" (amber) warning
VOL_EXTREME    = 90   # vol percentile: extreme regime
VOL_ELEVATED   = 75   # vol percentile: elevated (amber)

# ── FX TICKERS (Yahoo Finance format) ───────────────────────
FX_TICKERS = {
    "EURUSD": "EURUSD=X",   # Euro vs US Dollar
    "USDJPY": "JPY=X",      # US Dollar vs Japanese Yen
    "DXY":    "DX-Y.NYB",   # Dollar Index (basket of currencies vs USD)
}

# ── YIELD SOURCES ───────────────────────────────────────────
# US yields: FRED (daily)
FRED_SERIES = {
    "US_2Y":  "DGS2",    # US 2-Year Treasury Yield (daily)
    "US_10Y": "DGS10",   # US 10-Year Treasury Yield (daily)
}

# DE yields: ECB Yield Curve data (daily, eurozone government bonds)
# API: https://data-api.ecb.europa.eu/service/data/YC/...
# G_N_A = Government, Nominal, All issuers
# SV_C_YM = Svensson Continuous Yield to Maturity
ECB_SERIES = {
    "DE_2Y":  "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
    "DE_10Y": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
}
ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"

# JP yields: Ministry of Finance Japan (daily JGB yield curve)
# Historical: https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv
# Current month: https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv
MOF_HISTORICAL_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
MOF_CURRENT_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"

# ── RATE DIFFERENTIAL PAIRS ──────────────────────────────────
# Format: (series_A, series_B, label)
# Differential = A minus B
# Positive = A pays more than B
DIFFERENTIALS = [
    ("US_2Y",  "DE_10Y", "US_DE_10Y_spread"),  # USD vs EUR driver (cross-maturity)
    ("US_2Y",  "DE_2Y",  "US_DE_2Y_spread"),   # USD vs EUR driver (same maturity)
    ("US_2Y",  "JP_10Y", "US_JP_10Y_spread"),  # USD vs JPY driver (cross-maturity)
    ("US_2Y",  "JP_2Y",  "US_JP_2Y_spread"),   # USD vs JPY driver (same maturity)
]

# ── PAIRS REGISTRY ───────────────────────────────────────────────────────────
# The single source of truth for all FX pairs in the system.
# Adding a new pair (e.g. GBPUSD): add one dict here; charts, briefs, and HTML
# auto-scale from this registry.
#
# Keys per pair:
#   price_col    — column name in latest_with_cot.csv
#   yahoo_ticker — Yahoo Finance symbol for price fetch
#   color        — hex colour for chart traces
#   spread_10y   — rate differential column (10Y cross-maturity)
#   spread_2y    — rate differential column (2Y same-maturity)
#   label_10y    — short label for the 10Y spread in charts
#   label_2y     — short label for the 2Y spread in charts
#   subtitle     — spread subplot annotation
#   cot_currency — CFTC currency name (None if no COT data)
#   chart_tabs   — which tabs to render in the HTML brief
#   chart_height — pixel height for fundamentals chart (others use fixed heights)
PAIRS = {
    "eurusd": dict(
        price_col    = "EURUSD",
        yahoo_ticker = "EURUSD=X",
        color        = "#4da6ff",
        spread_10y   = "US_DE_10Y_spread",
        spread_2y    = "US_DE_2Y_spread",
        label_10y    = "DE 10Y",
        label_2y     = "DE 2Y",
        subtitle     = "narrowing = EUR/USD should rise",
        cot_currency = "EUR",
        chart_tabs   = ["fundamentals", "positioning", "vol"],
        chart_height = 400,
    ),
    "usdjpy": dict(
        price_col    = "USDJPY",
        yahoo_ticker = "JPY=X",
        color        = "#ff9944",
        spread_10y   = "US_JP_10Y_spread",
        spread_2y    = "US_JP_2Y_spread",
        label_10y    = "JP 10Y",
        label_2y     = "JP 2Y",
        subtitle     = "narrowing = USD/JPY should fall",
        cot_currency = "JPY",
        chart_tabs   = ["fundamentals", "positioning", "vol"],
        chart_height = 400,
    ),
    "usdinr": dict(
        price_col    = "USDINR",
        yahoo_ticker = "USDINR=X",
        color        = "#e74c3c",
        spread_10y   = "US_IN_10Y_spread",
        spread_2y    = "US_IN_policy_spread",
        label_10y    = "IN 10Y",
        label_2y     = "IN policy",
        subtitle     = "negative = India yields higher = INR strength",
        cot_currency = None,             # no CFTC COT for INR
        chart_tabs   = ["fundamentals"],  # no positioning or vol tab yet
        chart_height = 360,
    ),
}

# ── MACRO CALENDAR (Phase 10) ────────────────────────────────────────────────
# Central bank event dates for the macro calendar flag.
# Format: 'YYYY-MM-DD': 'Event label'  — update monthly.
# When TODAY matches a key, the brief displays a MACRO EVENT WARNING strip.
CB_EVENTS = {
    # 2026 H1
    '2026-03-19': 'Fed FOMC / BoJ Policy',
    '2026-04-09': 'RBI MPC',
    '2026-04-17': 'ECB Meeting',
    '2026-05-01': 'BoJ Policy',
    '2026-05-07': 'Fed FOMC',
    '2026-06-05': 'ECB Meeting / RBI MPC',
    '2026-06-17': 'BoJ Policy',
    '2026-06-18': 'Fed FOMC',
    # 2026 H2
    '2026-07-24': 'ECB Meeting',
    '2026-07-30': 'Fed FOMC',
    '2026-07-31': 'BoJ Policy',
    '2026-08-06': 'RBI MPC',
    '2026-09-11': 'ECB Meeting',
    '2026-09-17': 'Fed FOMC',
    '2026-09-19': 'BoJ Policy',
    '2026-10-08': 'RBI MPC',
    '2026-10-29': 'ECB Meeting',
    '2026-10-30': 'BoJ Policy',
    '2026-11-05': 'Fed FOMC',
    '2026-12-04': 'RBI MPC',
    '2026-12-10': 'Fed FOMC',
    '2026-12-17': 'ECB Meeting',
    '2026-12-19': 'BoJ Policy',
}


def get_upcoming_event(today=None, window_days=7):
    """Return the nearest CB event within window_days, or None.

    Returns dict: {'event': str, 'date': str, 'days_away': int}
    or None if no event within window.
    """
    if today is None:
        today = TODAY
    nearest = None
    min_days = window_days + 1
    for date_str, name in CB_EVENTS.items():
        days_away = (pd.Timestamp(date_str) - pd.Timestamp(today)).days
        if 0 <= days_away <= window_days and days_away < min_days:
            min_days = days_away
            nearest = {'event': name, 'date': date_str, 'days_away': days_away}
    return nearest
