# cot_pipeline.py
# pulls CFTC COT disaggregated futures data for EUR and JPY
# extracts leveraged money (hedge fund) net positioning
# calculates rolling percentile to detect crowded positions
# saves to data/cot_latest.csv and merges with master FX data
#
# run every friday after 3:30 PM EST when CFTC publishes new data
# on other days it uses the most recent available weekly file
# charts are handled separately by create_dashboards.py
#
# why leveraged money and not noncommercial:
#   leveraged money = hedge funds and CTAs only
#   noncommercial   = hedge funds + asset managers + retail speculators
#   hedge funds drive carry trades and react to rate differentials
#   asset managers move slowly for different reasons (equity hedging etc)
#   leveraged money gives a cleaner signal for regime detection
#
# data source: CFTC financial futures disaggregated report
# URL: https://www.cftc.gov/files/dea/history/fut_fin_txt_YYYY.zip

import os
import sys
import requests
import zipfile
import pandas as pd
from io import BytesIO
from core.paths import LATEST_CSV, LATEST_WITH_COT_CSV
from datetime import datetime
from core.utils import ordinal
from config import TODAY

"""
CFTC COT positioning Pipeline.

Execution context:
- Called by run.py as STEP 2 (cot)
- Depends on: pipeline.py (fx step must complete, data/latest.csv must exist)
- Outputs: data/cot_latest.csv
- Next step: inr_pipeline.py
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

CURRENT_YR = datetime.today().year

# years of history to pull for percentile calculation
# 3 years = 156 weekly observations = enough for meaningful percentiles
HISTORY_YEARS = 3

# exact market names as they appear in the CFTC file
TARGET_MARKETS = {
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": "JPY",
    "EURO FX - CHICAGO MERCANTILE EXCHANGE":      "EUR",
}

# columns we need -- everything else is discarded immediately to save memory
COLS_NEEDED = [
    "Market_and_Exchange_Names",
    "Report_Date_as_YYYY-MM-DD",
    # Leveraged Money (hedge funds, CTAs)
    "Lev_Money_Positions_Long_All",
    "Lev_Money_Positions_Short_All",
    # Asset Manager / Institutional
    "Asset_Mgr_Positions_Long_All",
    "Asset_Mgr_Positions_Short_All",
    "Open_Interest_All",              # total open interest for normalization
]


# -- step 1: fetch one year of CFTC data ---------------------------------------

def fetch_cot_year(year):
    url = f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"

    try:
        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            print(f"    FAILED {year} -- status {r.status_code}")
            return pd.DataFrame()

        z  = zipfile.ZipFile(BytesIO(r.content))
        names = z.namelist()
        if len(names) != 1:
            print(f"    FAILED {year} -- unexpected zip contents: {names}")
            return pd.DataFrame()
        df = pd.read_csv(z.open(names[0]), low_memory=False)

        # filter immediately -- keeps only EUR and JPY rows
        mask = df["Market_and_Exchange_Names"].isin(TARGET_MARKETS.keys())
        df   = df[mask][COLS_NEEDED].copy()

        print(f"    OK  {year} -- {len(df)} rows")
        return df

    except (requests.RequestException, zipfile.BadZipFile, KeyError, ValueError) as e:
        print(f"    FAILED {year} -- {e}")
        return pd.DataFrame()


# -- step 2: fetch multiple years and combine ----------------------------------

def fetch_all_cot():
    print("\n[1/4] fetching CFTC COT data...")

    years  = range(CURRENT_YR - HISTORY_YEARS, CURRENT_YR + 1)
    frames = []

    for year in years:
        df = fetch_cot_year(year)
        if len(df) > 0:
            frames.append(df)

    if len(frames) == 0:
        print("    FAILED -- no data retrieved")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["Report_Date_as_YYYY-MM-DD"] = pd.to_datetime(
        combined["Report_Date_as_YYYY-MM-DD"]
    )
    combined = combined.sort_values("Report_Date_as_YYYY-MM-DD")
    combined = combined.drop_duplicates(
        subset=["Report_Date_as_YYYY-MM-DD", "Market_and_Exchange_Names"],
        keep="last"
    )

    print(f"    combined: {len(combined)} rows, "
          f"{years[0]} to {years[-1]}")
    return combined


# -- step 3: calculate net positioning and percentiles -------------------------
#
# TWO CATEGORIES per pair:
#
# 1. LEVERAGED MONEY (hedge funds, CTAs - macro traders)
#    net position = leveraged money longs minus shorts
#    positive = hedge funds net long (bullish on the currency)
#    negative = hedge funds net short (bearish, carry trade sellers)
#
# 2. ASSET MANAGER (institutional, ETFs, long-only portfolios)
#    net position = asset manager longs minus shorts
#    positive = institutions net long (mechanical hedging or structural longs)
#    negative = institutions net short (rare for long-only accounts)
#
# NonCommercial is not used; it does not exist in the disaggregated report.
# The framework relies solely on Leveraged Money for the primary signal and
# Asset Manager for confirmation.
#
# For each category:
#   net % of open interest = net position / total open interest * 100
#   percentile = where does this week rank vs all weeks in the history window
#   crowding thresholds:
#     above 80th = crowded long -- limited upside, reversal risk
#     below 20th = crowded short -- squeeze risk if catalyst appears
#     20-80 = neutral, no crowding signal

def calculate_positioning(raw_df):
    print("\n[2/4] calculating net positioning and percentiles...")

    results = {}

    for market_name, ticker in TARGET_MARKETS.items():
        df = raw_df[
            raw_df["Market_and_Exchange_Names"] == market_name
        ].copy()
        df = df.set_index("Report_Date_as_YYYY-MM-DD").sort_index()

        # convert to numeric -- CFTC files sometimes contain commas in numbers
        all_cols = [
            "Lev_Money_Positions_Long_All",
            "Lev_Money_Positions_Short_All",
            "Asset_Mgr_Positions_Long_All",
            "Asset_Mgr_Positions_Short_All",
            "Open_Interest_All"
        ]
        for col in all_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ""),
                    errors="coerce"
                )

        # ──────────────────────────────────────────────────────────────────────
        # CATEGORY 1: LEVERAGED MONEY
        # ──────────────────────────────────────────────────────────────────────
        df["lev_net"] = (
            df["Lev_Money_Positions_Long_All"] -
            df["Lev_Money_Positions_Short_All"]
        )
        df["lev_pct_oi"] = (
            df["lev_net"] / df["Open_Interest_All"].replace(0, float('nan')) * 100
        )
        df["lev_percentile"] = df["lev_net"].rank(pct=True) * 100

        # ──────────────────────────────────────────────────────────────────────
        # CATEGORY 2: ASSET MANAGER
        # ──────────────────────────────────────────────────────────────────────
        df["assetmgr_net"] = (
            df["Asset_Mgr_Positions_Long_All"] -
            df["Asset_Mgr_Positions_Short_All"]
        )
        df["assetmgr_pct_oi"] = (
            df["assetmgr_net"] / df["Open_Interest_All"].replace(0, float('nan')) * 100
        )
        df["assetmgr_percentile"] = df["assetmgr_net"].rank(pct=True) * 100


        # Keep leveraged money + asset manager in results
        results[ticker] = df[[
            # Leveraged Money
            "lev_net",
            "lev_pct_oi",
            "lev_percentile",
            "Lev_Money_Positions_Long_All",
            "Lev_Money_Positions_Short_All",
            # Asset Manager
            "assetmgr_net",
            "assetmgr_pct_oi",
            "assetmgr_percentile",
            "Asset_Mgr_Positions_Long_All",
            "Asset_Mgr_Positions_Short_All",
        ]].copy()

        # Print summary for each ticker
        latest    = df.iloc[-1]
        lev_dir   = "LONG" if latest["lev_net"] > 0 else ("SHORT" if latest["lev_net"] < 0 else "NEUTRAL")
        am_dir    = "LONG" if latest["assetmgr_net"] > 0 else ("SHORT" if latest["assetmgr_net"] < 0 else "NEUTRAL")
        lev_p     = latest["lev_percentile"]
        am_p      = latest["assetmgr_percentile"]

        print(f"\n    {ticker}:")
        print(f"      Leveraged Money:")
        print(f"        net : {latest['lev_net']:>+,.0f} contracts ({lev_dir})")
        print(f"        % OI: {latest['lev_pct_oi']:>+.1f}%  |  percentile: {ordinal(lev_p)}")
        print(f"        regime: ", end="")
        if lev_p >= 80:
            print("CROWDED LONG")
        elif lev_p <= 20:
            print("CROWDED SHORT")
        else:
            print("NEUTRAL")

        print(f"      Asset Manager:")
        print(f"        net : {latest['assetmgr_net']:>+,.0f} contracts ({am_dir})")
        print(f"        % OI: {latest['assetmgr_pct_oi']:>+.1f}%  |  percentile: {ordinal(am_p)}")
        print(f"        regime: ", end="")
        if am_p >= 80:
            print("CROWDED LONG")
        elif am_p <= 20:
            print("CROWDED SHORT")
        else:
            print("NEUTRAL")

    return results


# -- step 4: save COT data -----------------------------------------------------

def save_cot(positioning_dict):
    os.makedirs("data", exist_ok=True)

    frames = []
    for ticker, df in positioning_dict.items():
        # New naming convention with category prefixes
        # PLUS backward-compatible columns (EUR_net_pos, EUR_percentile) for create_dashboards.py
        renamed = df.rename(columns={
            # Leveraged Money -- new names
            "lev_net":                                f"{ticker}_lev_net",
            "lev_pct_oi":                             f"{ticker}_lev_pct_oi",
            "lev_percentile":                         f"{ticker}_lev_percentile",
            # Asset Manager -- new names
            "assetmgr_net":                           f"{ticker}_assetmgr_net",
            "assetmgr_pct_oi":                        f"{ticker}_assetmgr_pct_oi",
            "assetmgr_percentile":                    f"{ticker}_assetmgr_percentile",
            # Raw position columns (informational)
            "Lev_Money_Positions_Long_All":           f"{ticker}_lev_long",
            "Lev_Money_Positions_Short_All":          f"{ticker}_lev_short",
            "Asset_Mgr_Positions_Long_All":           f"{ticker}_assetmgr_long",
            "Asset_Mgr_Positions_Short_All":          f"{ticker}_assetmgr_short",
        })

        frames.append(renamed)

    cot_df = pd.concat(frames, axis=1)
    cot_df.index.name = "date"

    cot_df.to_csv("data/cot_latest.csv", encoding='utf-8')
    print(f"\n    saved: data/cot_latest.csv")
    print(f"    rows: {len(cot_df)}, "
          f"from {cot_df.index[0].date()} to {cot_df.index[-1].date()}")

    return cot_df


# -- step 4: merge COT with FX master ------------------------------------------
#
# COT is weekly (published every friday)
# master is daily (trading calendar)
# solution: reindex COT onto daily dates using forward fill
# each trading day gets the most recent weekly COT reading
# this is valid -- positioning doesn't change day to day between publications

def merge_with_master(cot_df):
    print("\n[4/4] merging COT with FX master data...")

    master_path = LATEST_CSV
    if not os.path.exists(master_path):
        print("    WARNING -- data/latest.csv not found")
        print("    run pipeline.py first, then cot_pipeline.py")
        return

    master    = pd.read_csv(master_path, index_col=0, parse_dates=True, encoding='utf-8')
    cot_daily = cot_df.reindex(master.index).ffill()

    for col in cot_daily.columns:
        master[col] = cot_daily[col]

    master.to_csv(LATEST_WITH_COT_CSV, encoding='utf-8')
    print(f"    saved: {LATEST_WITH_COT_CSV}")
    print(f"    shape: {master.shape[0]} rows x {master.shape[1]} columns")


# -- main ----------------------------------------------------------------------

def main():
    print("=" * 62)
    print(f"  COT POSITIONING PIPELINE -- {TODAY}")
    print("=" * 62)

    raw_df      = fetch_all_cot()
    if raw_df.empty:
        print("ERROR: COT data fetch failed — all years unavailable")
        sys.exit(1)
    positioning = calculate_positioning(raw_df)

    print("\n[3/4] saving data...")
    cot_df = save_cot(positioning)
    merge_with_master(cot_df)

    # final summary
    print("\n" + "=" * 62)
    print("  COT SUMMARY (Leveraged Money)")
    print("=" * 62)

    for ticker, df in positioning.items():
        latest      = df.iloc[-1]
        latest_date = df.index[-1].date()
        direction   = "LONG" if latest["lev_net"] > 0 else ("SHORT" if latest["lev_net"] < 0 else "NEUTRAL")
        p           = latest["lev_percentile"]
        net         = latest["lev_net"]

        if p >= 80:
            regime = "CROWDED LONG -- limited upside, watch for reversal"
        elif p <= 20:
            regime = "CROWDED SHORT -- squeeze risk if catalyst appears"
        elif net > 0:
            regime = f"MODERATELY LONG ({ordinal(p)} pct) -- no crowding signal"
        elif net < 0:
            regime = f"MODERATELY SHORT ({ordinal(p)} pct) -- no crowding signal"
        else:
            regime = "NEUTRAL"

        print(f"\n  {ticker} (as of {latest_date}):")
        print(f"    net position : {net:>+,.0f} contracts ({direction})")
        print(f"    % of OI      : {latest['lev_pct_oi']:>+.1f}%")
        print(f"    percentile   : {ordinal(p)} (vs last {HISTORY_YEARS} years)")
        print(f"    regime       : {regime}")

    print("\n" + "=" * 62)
    print("  run create_dashboards.py for charts")
    print("=" * 62)

    try:
        from core.signal_write import sync_all_signals_from_master_csv

        sync_all_signals_from_master_csv()
    except Exception as e:
        print(f"  WARN: Supabase signals sync after COT merge: {e}")


if __name__ == "__main__":
    main()