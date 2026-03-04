# morning_brief.py
# generates a clean, desk-readable FX regime brief
# reads from data/latest_with_cot.csv (run pipeline.py and cot_pipeline.py first)
# outputs to terminal and saves to /briefs/brief_YYYYMMDD.txt
#
# run every morning after run_all.py
# target: readable in 60 seconds by someone on an FX desk

import os
import pandas as pd
from core.utils import ordinal, _pct, _pp, _net
from config import TODAY, TODAY_FMT


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

    # Key levels (support and resistance)
    eur_levels = _extract_key_levels(row, "EURUSD")
    jpy_levels = _extract_key_levels(row, "USDJPY")

    eur_net     = row.get("EUR_net_pos",         float('nan'))
    eur_pct_oi  = row.get("EUR_net_pct_oi",      float('nan'))
    eur_pct     = row.get("EUR_percentile",      float('nan'))

    jpy_net     = row.get("JPY_net_pos",         float('nan'))
    jpy_pct_oi  = row.get("JPY_net_pct_oi",      float('nan'))
    jpy_pct     = row.get("JPY_percentile",      float('nan'))

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
    cot_date = "n/a"
    if os.path.exists("data/cot_latest.csv"):
        cot_raw = pd.read_csv("data/cot_latest.csv", index_col=0, parse_dates=True)
        cot_date = str(cot_raw.index[-1].date())

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
    lines.append(f"  data as of: {as_of}  |  COT as of: {cot_date}")
    lines.append("=" * W)

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
    lines.append(f"  COT POSITIONING (as of {cot_date})")
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
        return

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


if __name__ == "__main__":
    main()