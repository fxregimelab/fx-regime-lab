# morning_brief.py
# generates a clean, desk-readable FX regime brief
# reads from data/latest_with_cot.csv (run pipeline.py and cot_pipeline.py first)
# outputs to terminal and saves to /briefs/brief_YYYYMMDD.txt
#
# run every morning after run_all.py
# target: readable in 60 seconds by someone on an FX desk

import json
import os
import sys
import pandas as pd
from core.utils import ordinal, _pct, _pp, _net
from core.utils import (
    _dxy_corr_label,
    _gold_corr_label,
    _oil_corr_label,
    _rbi_intervention_label,
    _btp_bund_label,
    _eur_interpretation,
    _jpy_interpretation,
)
from config import TODAY, TODAY_FMT, get_upcoming_event


"""
Text morning brief Pipeline.

Execution context:
- Called by run.py as STEP 7 (text)
- Depends on: all ETL steps complete, data/latest_with_cot.csv must exist
- Outputs: briefs/brief_YYYYMMDD.txt
- Next step: macro_pipeline.py
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


def _regime_label(percentile, net):
    """Return a short regime string."""
    if pd.isna(percentile):
        return "NO DATA"
    pct_str = ordinal(percentile) + " pct"
    if percentile >= 80:
        return f"CROWDED LONG  ({pct_str})"
    elif percentile <= 20:
        return f"CROWDED SHORT ({pct_str})"
    elif net > 0:
        return f"NEUTRAL LONG  ({pct_str})"
    else:
        return f"NEUTRAL SHORT ({pct_str})"


def _divergence_flag(lev_net, assetmgr_net, lev_pct=None, am_pct=None):
    """Return divergence flag when categories oppose AND one is crowded.

    Both direction and percentile thresholds must be considered.  An opposite
    sign where neither series is extreme is ignored.
    """
    if pd.isna(lev_net) or pd.isna(assetmgr_net):
        return ""
    lev_sign = lev_net > 0
    am_sign = assetmgr_net > 0
    if lev_sign == am_sign:
        return ""
    # require at least one category outside neutral zone
    if lev_pct is not None and am_pct is not None:
        if 20 < lev_pct < 80 and 20 < am_pct < 80:
            return ""
    return "  >> DIVERGENCE: Leveraged Money and Asset Manager opposing — signal reliability reduced"


def _correlation_flag(corr_val):
    """Return correlation status flag.
    
    INTACT: correlation > 0.6 (spread changes drive FX moves)
    WEAKENING: correlation 0.3 - 0.6 (regime becoming uncertain)
    BROKEN: correlation < 0.3 (fundamentals decoupled from FX)
    """
    if pd.isna(corr_val):
        return "NO DATA"
    if corr_val > 0.6:
        return "INTACT"
    elif corr_val > 0.3:
        return "WEAKENING"
    else:
        return "BROKEN"


def _corr_fmt(val):
    """Format correlation value with sign and three decimals."""
    if pd.isna(val):
        return "  n/a  "
    return f"{val:>+.3f}"


def _extract_key_levels(row, pair):
    """Extract S1, S2, S3, R1, R2, R3 from row data.
    
    Returns dict with keys like 'S1', 'S2', etc., values like "1.1234 (5)"
    """
    levels = {}
    for label in ['S1', 'S2', 'S3', 'R1', 'R2', 'R3']:
        col = f"{pair}_{label}"
        val = row.get(col, "")
        levels[label] = val if pd.notna(val) and val != "" else "—"
    return levels


# -- build the brief -----------------------------------------------------------

def build_brief(df):
    # use last row that has both FX prices and COT data
    row = df.dropna(subset=["EURUSD", "USDJPY"]).iloc[-1]
    as_of = df.dropna(subset=["EURUSD", "USDJPY"]).index[-1].date()

    # -- pull all values --
    eurusd      = row.get("EURUSD",             float('nan'))
    usdjpy      = row.get("USDJPY",             float('nan'))
    dxy         = row.get("DXY",                float('nan'))

    eur_1d      = row.get("EURUSD_chg_1D",      float('nan'))
    eur_12m     = row.get("EURUSD_chg_12M",     float('nan'))
    jpy_1d      = row.get("USDJPY_chg_1D",      float('nan'))
    jpy_12m     = row.get("USDJPY_chg_12M",     float('nan'))
    dxy_1d      = row.get("DXY_chg_1D",         float('nan'))
    dxy_12m     = row.get("DXY_chg_12M",        float('nan'))

    de10_today  = row.get("US_DE_10Y_spread",   float('nan'))
    de10_1w     = row.get("US_DE_10Y_spread_chg_1W",  float('nan'))
    de10_12m    = row.get("US_DE_10Y_spread_chg_12M", float('nan'))

    de2_today   = row.get("US_DE_2Y_spread",    float('nan'))
    de2_1w      = row.get("US_DE_2Y_spread_chg_1W",   float('nan'))
    de2_12m     = row.get("US_DE_2Y_spread_chg_12M",  float('nan'))

    jp10_today  = row.get("US_JP_10Y_spread",   float('nan'))
    jp10_1w     = row.get("US_JP_10Y_spread_chg_1W",  float('nan'))
    jp10_12m    = row.get("US_JP_10Y_spread_chg_12M", float('nan'))

    jp2_today   = row.get("US_JP_2Y_spread",    float('nan'))
    jp2_1w      = row.get("US_JP_2Y_spread_chg_1W",   float('nan'))
    jp2_12m     = row.get("US_JP_2Y_spread_chg_12M",  float('nan'))

    # Regime correlation
    eur_corr    = row.get("EURUSD_spread_corr_60d",   float('nan'))
    jpy_corr    = row.get("USDJPY_spread_corr_60d",   float('nan'))

    # Oil correlation (Phase 1)
    oil_eur_corr = row.get("oil_eurusd_corr_60d", float('nan'))
    oil_jpy_corr = row.get("oil_usdjpy_corr_60d", float('nan'))
    oil_inr_corr = row.get("oil_inr_corr_60d",    float('nan'))

    # DXY decomposition (Phase 2)
    dxy_eur_corr = row.get("dxy_eurusd_corr_60d", float('nan'))
    dxy_jpy_corr = row.get("dxy_usdjpy_corr_60d", float('nan'))
    dxy_inr_corr = row.get("dxy_inr_corr_60d",    float('nan'))

    # Gold correlation (Phase 4)
    gold_jpy_corr       = row.get("gold_usdjpy_corr_60d", float('nan'))
    gold_inr_corr       = row.get("gold_inr_corr_60d",    float('nan'))
    gold_seasonal_flag  = row.get("gold_seasonal_flag",   0)
    gold_seasonal_label = row.get("gold_seasonal_label",  "")

    # RBI intervention (Phase 5)
    rbi_chg  = row.get("rbi_reserve_chg_1w",   float('nan'))
    rbi_flag = row.get("rbi_intervention_flag", "UNKNOWN")

    # INR Composite Score (Phase 7)
    inr_composite_score = row.get("inr_composite_score", float('nan'))
    inr_composite_label = row.get("inr_composite_label", "UNKNOWN")

    # BTP-Bund spread (Phase 9)
    btp_spread  = row.get("BTP_Bund_spread", float('nan'))
    btp_flag    = row.get("BTP_Bund_flag",   "UNAVAILABLE")

    # G10 composite scores (Phase 8)
    eur_comp_score = row.get("eurusd_composite_score", float('nan'))
    eur_comp_label = row.get("eurusd_composite_label", "UNKNOWN")
    jpy_comp_score = row.get("usdjpy_composite_score", float('nan'))
    jpy_comp_label = row.get("usdjpy_composite_label", "UNKNOWN")

    # Macro calendar (Phase 10)
    upcoming_event = get_upcoming_event()

    # Key levels (support and resistance)
    eur_levels = _extract_key_levels(row, "EURUSD")
    jpy_levels = _extract_key_levels(row, "USDJPY")

    eur_net     = row.get("EUR_lev_net",         float('nan'))
    eur_pct_oi  = row.get("EUR_lev_pct_oi",      float('nan'))
    eur_pct     = row.get("EUR_lev_percentile",  float('nan'))

    jpy_net     = row.get("JPY_lev_net",         float('nan'))
    jpy_pct_oi  = row.get("JPY_lev_pct_oi",      float('nan'))
    jpy_pct     = row.get("JPY_lev_percentile",  float('nan'))

    # EUR Asset Manager
    eur_am_net  = row.get("EUR_assetmgr_net",    float('nan'))
    eur_am_pct_oi = row.get("EUR_assetmgr_pct_oi", float('nan'))
    eur_am_pct  = row.get("EUR_assetmgr_percentile", float('nan'))

    # (NonCommercial removed - not used in this report)

    # JPY Asset Manager
    jpy_am_net  = row.get("JPY_assetmgr_net",    float('nan'))
    jpy_am_pct_oi = row.get("JPY_assetmgr_pct_oi", float('nan'))
    jpy_am_pct  = row.get("JPY_assetmgr_percentile", float('nan'))

    # (NonCommercial removed - not used in this report)

    # COT data is weekly -- find the actual COT date (last non-NaN)
    # CFTC schedule: positions snapshot = Tuesday close (cutoff)
    #                publication    = Friday of the same week (cutoff + 3 days)
    cot_cutoff    = "n/a"
    cot_published = "n/a"
    if os.path.exists("data/cot_latest.csv"):
        cot_raw       = pd.read_csv("data/cot_latest.csv", index_col=0, parse_dates=True)
        cot_last      = cot_raw.index[-1]
        cot_cutoff    = str(cot_last.date())
        cot_published = str((cot_last + pd.Timedelta(days=3)).date())
    # keep cot_date as alias so downstream references still work
    cot_date = cot_cutoff

    # IN 10Y freshness -- find last non-NaN date in the loaded data
    in10y_date = "n/a"
    if "IN_10Y" in df.columns:
        in10y_valid = df["IN_10Y"].dropna()
        if len(in10y_valid) > 0:
            in10y_date = str(in10y_valid.index[-1].date())

    # -- interpretations --
    eur_read = _eur_interpretation(
        de10_today, de10_12m,
        eur_pct, eur_net,
        eur_am_pct, eur_am_net
    )
    # append volatility flag for EUR/USD if elevated or extreme
    eur_vol_pct = row.get("EURUSD_vol_pct", float('nan'))
    if not pd.isna(eur_vol_pct):
        if eur_vol_pct >= 90:
            eur_read += " vol EXTREME — forced liquidation risk, fundamental signals unreliable."
        elif eur_vol_pct >= 75:
            eur_read += " vol elevated — positioning signals less reliable."

    jpy_read = _jpy_interpretation(
        jp10_today, jp10_12m,
        jpy_pct, jpy_net,
        jpy_am_pct, jpy_am_net
    )
    # append volatility flag for USD/JPY
    jpy_vol_pct = row.get("USDJPY_vol_pct", float('nan'))
    if not pd.isna(jpy_vol_pct):
        if jpy_vol_pct >= 90:
            jpy_read += " vol EXTREME — forced liquidation risk, fundamental signals unreliable."
        elif jpy_vol_pct >= 75:
            jpy_read += " vol elevated — positioning signals less reliable."

    W = 70  # total line width

    lines = []
    lines.append("=" * W)
    lines.append(f"  G10 FX MORNING BRIEF")
    lines.append(f"  {TODAY_FMT}")
    lines.append(f"  FX as of: {as_of}  |  IN 10Y as of: {in10y_date}  |  COT cutoff: {cot_cutoff} (pub'd: {cot_published})")
    lines.append("=" * W)

    # Lead narrative (desk tone) — tables below stay numeric; this block is for fast human + AI read.
    eur_c = row.get("eurusd_composite_label", "")
    jpy_c = row.get("usdjpy_composite_label", "")
    inr_c = row.get("inr_composite_label", "")
    if isinstance(eur_c, float) and pd.isna(eur_c):
        eur_c = ""
    if isinstance(jpy_c, float) and pd.isna(jpy_c):
        jpy_c = ""
    if isinstance(inr_c, float) and pd.isna(inr_c):
        inr_c = ""
    eur_c = str(eur_c).strip() or "n/a"
    jpy_c = str(jpy_c).strip() or "n/a"
    inr_c = str(inr_c).strip() or "directional-only frame"
    lines.append("")
    lines.append("  DESK SUMMARY")
    lines.append(f"  {'-' * 66}")
    lines.append(
        f"  As of {as_of}, the working story is anchored in rate spreads: US–DE 10Y sits at "
        f"{de10_today:.2f}% ({_pp(de10_1w)} over 1W) while US–JP 10Y is {jp10_today:.2f}% ({_pp(jp10_1w)} over 1W). "
        f"Composite labels read EUR/USD {eur_c}, USD/JPY {jpy_c}, USD/INR {inr_c}. "
        "Treat COT and realized vol in the sections below as overlays on that rates spine—crowding and stress "
        "change how aggressively to trade the spread signal, they rarely invalidate it in isolation."
    )
    if upcoming_event is not None:
        lines.append(
            f"  Near-term catalyst: {upcoming_event['event']} on {upcoming_event['date']} "
            f"({upcoming_event['days_away']} day(s) out)."
        )

    acc_path = "data/validation_accuracy.json"
    if os.path.exists(acc_path):
        try:
            with open(acc_path, encoding="utf-8") as af:
                acc = json.load(af)
            lines.append("")
            w = acc.get("window_days", 20)
            lines.append(f"  REGIME CALL ACCURACY (last {w} days)")
            lines.append(
                f"  EUR/USD: {acc.get('EURUSD', '—')}% | USD/JPY: {acc.get('USDJPY', '—')}% | USD/INR: {acc.get('USDINR', '—')}%"
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    # ── MACRO CALENDAR ALERT ─────────────────────────────────────────────────
    if upcoming_event is not None:
        days_away = upcoming_event['days_away']
        evt_name  = upcoming_event['event']
        evt_date  = upcoming_event['date']
        if days_away == 0:
            day_str = "TODAY"
        elif days_away == 1:
            day_str = "TOMORROW"
        else:
            day_str = f"in {days_away} days"
        lines.append("")
        lines.append(f"  !! MACRO EVENT {day_str}: {evt_name} ({evt_date}) !!")

    # ── PRICES ────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  PRICES")
    lines.append(f"  {'pair':<10} {'price':>9}  {'1D':>8}  {'12M':>8}")
    lines.append(f"  {'-'*48}")
    lines.append(f"  {'EUR/USD':<10} {eurusd:>9.4f}  {_pct(eur_1d):>8}  {_pct(eur_12m):>8}")
    lines.append(f"  {'USD/JPY':<10} {usdjpy:>9.4f}  {_pct(jpy_1d):>8}  {_pct(jpy_12m):>8}")
    lines.append(f"  {'DXY':<10} {dxy:>9.4f}  {_pct(dxy_1d):>8}  {_pct(dxy_12m):>8}")

    # ── RATE DIFFERENTIALS ────────────────────────────────────────────────────
    lines.append("")
    lines.append("  RATE DIFFERENTIALS  (narrowing = foreign currency should strengthen)")
    lines.append(f"  {'spread':<22} {'today':>7}  {'1W chg':>8}  {'12M chg':>8}")
    lines.append(f"  {'-'*52}")
    lines.append(f"  {'US-DE 10Y (cross)':<22} {de10_today:>6.2f}%  {_pp(de10_1w):>8}  {_pp(de10_12m):>8}")
    lines.append(f"  {'US-DE 2Y  (same) ':<22} {de2_today:>6.2f}%  {_pp(de2_1w):>8}  {_pp(de2_12m):>8}")
    lines.append(f"  {'US-JP 10Y (cross)':<22} {jp10_today:>6.2f}%  {_pp(jp10_1w):>8}  {_pp(jp10_12m):>8}")
    lines.append(f"  {'US-JP 2Y  (same) ':<22} {jp2_today:>6.2f}%  {_pp(jp2_1w):>8}  {_pp(jp2_12m):>8}")
    # BTP-Bund spread (Phase 9 -- EUR/USD-relevant Italian sovereign risk)
    btp_text, _btp_color = _btp_bund_label(btp_flag)
    btp_spread_str = f"{btp_spread:.2f}pp" if not pd.isna(btp_spread) else "n/a"
    btp_note = ""
    if str(btp_flag) == "STRESS":
        btp_note = "  << Italian sovereign stress -- EUR negative"
    elif str(btp_flag) == "ELEVATED":
        btp_note = "  << elevated BTP-Bund premium -- monitor"
    lines.append(f"  {'BTP-Bund (IT-DE 10Y)':<22} {btp_spread_str:>8}  {'':>8}  {'':>8}  [{btp_text}]{btp_note}")

    # ── REGIME CORRELATION ────────────────────────────────────────────────────
    lines.append("")
    lines.append("  REGIME CORRELATION  (60D rolling | spread vs FX move)")
    lines.append(f"  {'pair':<12} {'correlation':>12}   {'flag'}")
    lines.append(f"  {'-'*52}")
    eur_corr_flag = _correlation_flag(eur_corr)
    jpy_corr_flag = _correlation_flag(jpy_corr)
    lines.append(f"  {'EUR/USD':<12} {_corr_fmt(eur_corr):>12}   {eur_corr_flag}")
    lines.append(f"  {'USD/JPY':<12} {_corr_fmt(jpy_corr):>12}   {jpy_corr_flag}")

    # ── OIL CORRELATION ───────────────────────────────────────────────────────
    lines.append("")
    lines.append("  OIL CORRELATION  (60D rolling | Brent returns vs FX returns)")
    lines.append("  expected: EUR/USD negative, USD/JPY positive, USD/INR positive")
    lines.append(f"  {'pair':<12} {'correlation':>12}   {'flag'}")
    lines.append(f"  {'-'*52}")
    for pair_name, fx_key, corr_val in [
        ("EUR/USD", "EURUSD", oil_eur_corr),
        ("USD/JPY", "USDJPY", oil_jpy_corr),
        ("USD/INR", "USDINR", oil_inr_corr),
    ]:
        label, is_div = _oil_corr_label(corr_val, fx_key)
        div_note = "  << sign reversal — pair-specific factor overriding oil channel" if is_div else ""
        lines.append(f"  {pair_name:<12} {_corr_fmt(corr_val):>12}   {label}{div_note}")

    # ── DXY DECOMPOSITION ─────────────────────────────────────────────────────
    lines.append("")
    lines.append("  DXY DECOMPOSITION  (60D rolling | DXY returns vs FX returns)")
    lines.append("  high +ve = dollar-driven | low corr = pair-specific factor")
    lines.append(f"  {'pair':<12} {'correlation':>12}   {'regime'}")
    lines.append(f"  {'-'*52}")
    for pair_name, fx_key, corr_val in [
        ("EUR/USD", "EURUSD", dxy_eur_corr),
        ("USD/JPY", "USDJPY", dxy_jpy_corr),
        ("USD/INR", "USDINR", dxy_inr_corr),
    ]:
        label, is_dollar = _dxy_corr_label(corr_val, fx_key)
        dollar_note = "  << broad USD move" if is_dollar else ""
        lines.append(f"  {pair_name:<12} {_corr_fmt(corr_val):>12}   {label}{dollar_note}")

    # ── GOLD CORRELATION ─────────────────────────────────────────────────────
    lines.append("")
    lines.append("  GOLD CORRELATION  (60D rolling | Gold returns vs FX returns)")
    lines.append("  USD/JPY: negative expected (safe-haven) | USD/INR: positive expected (import demand)")
    lines.append(f"  {'pair':<12} {'correlation':>12}   {'flag'}")
    lines.append(f"  {'-'*52}")
    for pair_name, fx_key, corr_val in [
        ("USD/JPY", "USDJPY", gold_jpy_corr),
        ("USD/INR", "USDINR", gold_inr_corr),
    ]:
        label, is_div = _gold_corr_label(corr_val, fx_key)
        div_note = "  << sign reversal -- safe-haven/import demand channel broken" if is_div else ""
        lines.append(f"  {pair_name:<12} {_corr_fmt(corr_val):>12}   {label}{div_note}")
    # seasonal demand flag (USD/INR only, when gold_seasonal_flag is active)
    try:
        seasonal_active = float(gold_seasonal_flag) > 0.5
    except (TypeError, ValueError):
        seasonal_active = False
    if seasonal_active and str(gold_seasonal_label) not in ('nan', 'None', ''):
        lines.append(f"  {'':12} {'':>12}   SEASONAL: {gold_seasonal_label}")
    # ── RBI INTERVENTION ─────────────────────────────────────────────
    lines.append("")
    lines.append("  RBI INTERVENTION  (FRED RBUKRESERVES | 7-day change in USD bn)")
    lines.append(f"  {'-'*52}")
    rbi_text, _rbi_color, _rbi_active = _rbi_intervention_label(rbi_flag)
    chg_str = f"{rbi_chg:+.1f}B" if not pd.isna(rbi_chg) else "n/a"
    div_note = ""
    if str(rbi_flag) == "ACTIVE SUPPORT":
        div_note = "  << defending INR floor"
    elif str(rbi_flag) == "ACTIVE CAPPING":
        div_note = "  << capping INR appreciation"
    lines.append(f"  {'RBI Reserves':<20} {chg_str:>10}   {rbi_text}{div_note}")

    # ── INR COMPOSITE SCORE ─────────────────────────────────────────
    lines.append("")
    lines.append("  INR COMPOSITE SCORE  (oil 25% | DXY 20% | FPI 25% | RBI 20% | rate 10%)")
    lines.append(f"  {'-'*52}")
    if not pd.isna(inr_composite_score):
        lines.append(f"  SCORE: {inr_composite_score:+.1f}  [{inr_composite_label}]")
        try:
            _oil_c = float(row.get("oil_inr_corr_60d", 0) or 0)
            _dxy_c = float(row.get("dxy_inr_corr_60d", 0) or 0)
            _fpi_c = float(row.get("FPI_20D_flow",     0) or 0)
            _spr_c = float(row.get("US_IN_10Y_spread", 0) or 0)
            _b1d   = float(row.get("Brent_chg_1D",     0) or 0)
            _d1d   = float(row.get("DXY_chg_1D",       0) or 0)
            _rbi_wt = {"ACTIVE SUPPORT": -0.30, "ACTIVE CAPPING": 0.20, "NEUTRAL": 0.0, "UNKNOWN": 0.0}
            _sgn = lambda v: 1 if v > 0 else (-1 if v < 0 else 0)
            oil_sub  = _oil_c * _sgn(_b1d) * 0.25 * 100
            dxy_sub  = _dxy_c * _sgn(_d1d) * 0.20 * 100
            fpi_sub  = -min(max(_fpi_c / 20000, -1), 1) * 0.25 * 100
            rbi_sub  = _rbi_wt.get(str(rbi_flag) if str(rbi_flag) != "nan" else "NEUTRAL", 0.0) * 0.20 * 100
            rate_sub = _sgn(-_spr_c) * 0.10 * 100
            lines.append(f"  Components: Oil({oil_sub:+.0f}) DXY({dxy_sub:+.0f}) FPI({fpi_sub:+.0f}) RBI({rbi_sub:+.0f}) Rate({rate_sub:+.0f})")
        except (TypeError, KeyError, ValueError, ArithmeticError):
            pass  # display only — non-critical if component breakdown fails
    else:
        lines.append(f"  SCORE: n/a  (run inr pipeline to populate)")
    # ── G10 COMPOSITE SCORES ─────────────────────────────────────────────────
    lines.append("")
    lines.append("  G10 COMPOSITE REGIME SCORES  (Phase 8 | +ve = USD strength pressure)")
    lines.append(f"  {'-'*62}")
    lines.append(f"  {'pair':<12} {'score':>8}   {'label'}")
    lines.append(f"  {'-'*62}")
    eur_score_str = f"{eur_comp_score:>+.1f}" if not pd.isna(eur_comp_score) else "  n/a"
    jpy_score_str = f"{jpy_comp_score:>+.1f}" if not pd.isna(jpy_comp_score) else "  n/a"
    lines.append(f"  {'EUR/USD':<12} {eur_score_str:>8}   {eur_comp_label}")
    lines.append(f"  {'USD/JPY':<12} {jpy_score_str:>8}   {jpy_comp_label}")
    lines.append(f"  weights: EUR/USD rate 30%+lev 20%+amgr 10%+vol 10%+corr 15%+oil 8%+dxy 7%")
    lines.append(f"           USD/JPY rate 25%+lev 20%+amgr 10%+vol 10%+corr 15%+oil 10%+gold 5%+dxy 5%")

    # ── KEY LEVELS ────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  KEY LEVELS  (90D | S=support, R=resistance, (n)=touches)")
    lines.append(f"  {'-'*62}")
    lines.append(f"  EUR/USD:  S3: {eur_levels['S3']:<15} S2: {eur_levels['S2']:<15} S1: {eur_levels['S1']:<15}")
    lines.append(f"           R1: {eur_levels['R1']:<15} R2: {eur_levels['R2']:<15} R3: {eur_levels['R3']:<15}")
    lines.append(f"  USD/JPY:  S3: {jpy_levels['S3']:<15} S2: {jpy_levels['S2']:<15} S1: {jpy_levels['S1']:<15}")
    lines.append(f"           R1: {jpy_levels['R1']:<15} R2: {jpy_levels['R2']:<15} R3: {jpy_levels['R3']:<15}")

    # ── VOLATILITY ───────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  VOLATILITY  (30D realized, annualized | 3Y percentile)")

    lines.append(f"  {'-'*56}")
    lines.append(f"  {'pair':<12} {'vol30':>8}   {'pct':>8}   {'flag'}")
    lines.append(f"  {'-'*56}")
    for pair in ["EURUSD", "USDJPY"]:
        vol_col = f"{pair}_vol30"
        pct_col = f"{pair}_vol_pct"
        if vol_col not in row.index:
            continue
        v = row[vol_col]
        p = row[pct_col]
        flag = "EXTREME" if p >= 90 else ("ELEVATED" if p >= 75 else "NORMAL")
        lines.append(f"  {pair:<12} {v:>7.1f}%   {p:>6.0f}th   {flag}")

    # ── POSITIONING ───────────────────────────────────────────────────────────
    lines.append("")
    lines.append(f"  COT POSITIONING  (cutoff: {cot_cutoff} = Tue close | pub'd: {cot_published} = Fri)")
    lines.append(f"  {'-'*66}")

    # EUR/USD positioning - all three categories
    lines.append("")
    lines.append(f"  EUR/USD:")

    # Leveraged Money
    eur_lev_net_str = _net(eur_net)
    eur_lev_oi_str  = f"{eur_pct_oi:>+.1f}% OI" if not pd.isna(eur_pct_oi) else "n/a"
    eur_lev_regime  = _regime_label(eur_pct, eur_net)
    lines.append(f"    Leveraged Money   : {eur_lev_net_str} contracts | {eur_lev_oi_str} | {eur_lev_regime}")

    # Asset Manager
    eur_am_net_str  = _net(eur_am_net)
    eur_am_oi_str   = f"{eur_am_pct_oi:>+.1f}% OI" if not pd.isna(eur_am_pct_oi) else "n/a"
    eur_am_regime   = _regime_label(eur_am_pct, eur_am_net)
    lines.append(f"    Asset Manager     : {eur_am_net_str} contracts | {eur_am_oi_str} | {eur_am_regime}")

    # NonCommercial suppressed per new framework (not displayed)

    # Divergence flag for EUR
    eur_div = _divergence_flag(eur_net, eur_am_net, eur_pct, eur_am_pct)
    if eur_div:
        lines.append(eur_div)

    # USD/JPY positioning - all three categories
    lines.append("")
    lines.append(f"  USD/JPY:")

    # Leveraged Money
    jpy_lev_net_str = _net(jpy_net)
    jpy_lev_oi_str  = f"{jpy_pct_oi:>+.1f}% OI" if not pd.isna(jpy_pct_oi) else "n/a"
    jpy_lev_regime  = _regime_label(jpy_pct, jpy_net)
    lines.append(f"    Leveraged Money   : {jpy_lev_net_str} contracts | {jpy_lev_oi_str} | {jpy_lev_regime}")

    # Asset Manager
    jpy_am_net_str  = _net(jpy_am_net)
    jpy_am_oi_str   = f"{jpy_am_pct_oi:>+.1f}% OI" if not pd.isna(jpy_am_pct_oi) else "n/a"
    jpy_am_regime   = _regime_label(jpy_am_pct, jpy_am_net)
    lines.append(f"    Asset Manager     : {jpy_am_net_str} contracts | {jpy_am_oi_str} | {jpy_am_regime}")

    # NonCommercial suppressed per new framework (not displayed)

    # Divergence flag for JPY
    jpy_div = _divergence_flag(jpy_net, jpy_am_net, jpy_pct, jpy_am_pct)
    if jpy_div:
        lines.append(jpy_div)

    # ── REGIME READS ──────────────────────────────────────────────────────────
    lines.append("")
    lines.append("  REGIME READ")
    lines.append(f"  {'-'*66}")

    # wrap long interpretation lines at W-4 chars
    def _wrap(prefix, text, width=W - 4):
        import textwrap
        wrapped = textwrap.fill(text, width=width - len(prefix))
        indented = wrapped.replace("\n", "\n  " + " " * len(prefix))
        return f"  {prefix}{indented}"

    lines.append(_wrap("EUR/USD  ", eur_read))
    lines.append("")
    lines.append(_wrap("USD/JPY  ", jpy_read))

    lines.append("")
    lines.append("=" * W)
    lines.append("")

    return "\n".join(lines)


# -- main ----------------------------------------------------------------------

def main():
    master_path = "data/latest_with_cot.csv"
    if not os.path.exists(master_path):
        print("ERROR: data/latest_with_cot.csv not found")
        print("Run pipeline.py then cot_pipeline.py first")
        sys.exit(1)

    df = pd.read_csv(master_path, index_col=0, parse_dates=True)

    brief = build_brief(df)

    # print to terminal
    print(brief)

    # save to /briefs
    os.makedirs("briefs", exist_ok=True)
    filepath = f"briefs/brief_{TODAY.replace('-', '')}.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"  saved: {filepath}")

    try:
        from core.regime_persist import persist_regime_calls_and_brief

        persist_regime_calls_and_brief(df, brief)
    except Exception as e:
        print(f"  WARN: Supabase regime/brief persist skipped: {e}")


if __name__ == "__main__":
    main()