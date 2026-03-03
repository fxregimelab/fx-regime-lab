# inr_pipeline.py
# standalone pipeline for USD/INR — adds a third pair to the framework
# three sources: yfinance (price), FRED (IN 10Y yield monthly), SEBI (FPI flows)
# saves to data/inr_latest.csv and merges with data/latest_with_cot.csv
#
# IN 10Y yield: FRED INDIRLTLT01STM (monthly, forward-filled to daily)
# RBI repo rate proxy: IN 10Y minus 1.5pp (no reliable daily FRED series exists)
# FPI flows: SEBI FPI page, net debt investment, 20D rolling cumulative

import os
import io
import requests
import pandas as pd
import numpy as np
from datetime import datetime

TODAY      = datetime.today().strftime('%Y-%m-%d')
START_DATE = "2020-01-01"


# -- source 1: USD/INR price from yfinance -------------------------------------

def fetch_usdinr():
    print("\n[1/3] fetching USD/INR price (yfinance USDINR=X)...")
    import yfinance as yf

    data = yf.download("USDINR=X", start=START_DATE, interval="1d",
                       progress=False, auto_adjust=True)
    if len(data) == 0:
        print("    FAILED -- empty dataframe")
        return pd.DataFrame()

    # flatten multi-level columns from newer yfinance
    close = data["Close"].squeeze()
    df    = close.to_frame(name="USDINR")
    df.index = pd.to_datetime(df.index.date)
    df    = df[df.index < pd.Timestamp(TODAY)]
    df    = df[df.index.dayofweek < 5]

    print(f"    OK  {len(df)} rows, latest: {df.index[-1].date()} "
          f"= {df['USDINR'].iloc[-1]:.4f}")
    return df


# -- source 2: IN 10Y yield from FRED (monthly) --------------------------------

def fetch_in_yield():
    print("\n[2/3] fetching IN 10Y yield (FRED INDIRLTLT01STM, monthly)...")

    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDIRLTLT01STM"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            print(f"    FAILED -- status {r.status_code}")
            return pd.DataFrame()

        monthly = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True)
        monthly.columns = ["IN_10Y"]
        monthly["IN_10Y"] = pd.to_numeric(monthly["IN_10Y"], errors="coerce")
        monthly = monthly.dropna()
        monthly = monthly[monthly.index >= START_DATE]

        # RBI repo rate proxy: IN 10Y minus 1.5pp
        # (no reliable daily FRED series for RBI repo rate)
        monthly["IN_repo_proxy"] = monthly["IN_10Y"] - 1.5

        latest_date = monthly.index[-1].date()
        latest_val  = monthly["IN_10Y"].iloc[-1]
        print(f"    OK  monthly, as of {latest_date} = {latest_val:.2f}%  "
              f"(repo proxy = {latest_val - 1.5:.2f}%)")
        print(f"    note: monthly data, forward-filled to daily")
        return monthly

    except Exception as e:
        print(f"    FAILED -- {e}")
        return pd.DataFrame()


# -- source 3: SEBI FPI debt flows ---------------------------------------------

def fetch_fpi_flows():
    print("\n[3/3] fetching SEBI FPI flows...")

    url = ("https://www.sebi.gov.in/sebiweb/other/OtherAction.do"
           "?doRecognisedFpi=yes&intmId=13")
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"    FAILED -- status {r.status_code}")
            return pd.DataFrame(), "unavailable"

        # parse all HTML tables, find the one with FPI debt data
        tables = pd.read_html(io.StringIO(r.text))
        fpi_df = None
        for tbl in tables:
            cols_lower = [str(c).lower() for c in tbl.columns]
            if any("debt" in c for c in cols_lower):
                fpi_df = tbl.copy()
                break

        if fpi_df is None:
            print("    FAILED -- no debt table found in page")
            return pd.DataFrame(), "unavailable"

        # normalise column names — find date column and debt net column
        fpi_df.columns = [str(c).strip() for c in fpi_df.columns]
        date_col = next((c for c in fpi_df.columns
                         if "date" in c.lower()), None)
        debt_col = next((c for c in fpi_df.columns
                         if "debt" in c.lower() and "net" in c.lower()), None)
        if debt_col is None:
            debt_col = next((c for c in fpi_df.columns
                             if "debt" in c.lower()), None)

        if date_col is None or debt_col is None:
            print(f"    FAILED -- could not identify columns: {fpi_df.columns.tolist()}")
            return pd.DataFrame(), "unavailable"

        fpi_df = fpi_df[[date_col, debt_col]].copy()
        fpi_df.columns = ["date", "FPI_debt_net"]
        fpi_df["date"] = pd.to_datetime(fpi_df["date"], dayfirst=True,
                                        errors="coerce")
        fpi_df = fpi_df.dropna(subset=["date"])
        fpi_df["FPI_debt_net"] = pd.to_numeric(
            fpi_df["FPI_debt_net"].astype(str).str.replace(",", ""),
            errors="coerce"
        )
        fpi_df = fpi_df.set_index("date").sort_index()
        fpi_df = fpi_df[fpi_df.index >= START_DATE]

        # 20-day rolling cumulative flow + 3-year rolling percentile
        fpi_df["FPI_20D_flow"]       = fpi_df["FPI_debt_net"].rolling(20).sum()
        fpi_df["FPI_20D_percentile"] = (
            fpi_df["FPI_20D_flow"]
            .rolling(252 * 3, min_periods=60)
            .rank(pct=True) * 100
        )

        latest = fpi_df.dropna(subset=["FPI_20D_flow"]).iloc[-1]
        print(f"    OK  {len(fpi_df)} rows, latest: {fpi_df.index[-1].date()}")
        print(f"    FPI 20D flow: {latest['FPI_20D_flow']:+,.0f}  "
              f"percentile: {latest['FPI_20D_percentile']:.0f}th")
        return fpi_df[["FPI_20D_flow", "FPI_20D_percentile"]], "ok"

    except Exception as e:
        print(f"    FAILED -- {e}")
        return pd.DataFrame(), "unavailable"


# -- assemble and save ---------------------------------------------------------

def build_and_save(price_df, yield_monthly, fpi_df, fpi_status):
    print("\n[saving] assembling inr_latest.csv...")
    os.makedirs("data", exist_ok=True)

    if len(price_df) == 0:
        print("    ERROR -- no price data, aborting")
        return

    # reindex yield (monthly) to daily using price calendar
    inr = price_df.copy()
    if len(yield_monthly) > 0:
        yield_daily = yield_monthly.reindex(inr.index, method="ffill")
        inr["IN_10Y"]        = yield_daily["IN_10Y"]
        inr["IN_repo_proxy"] = yield_daily["IN_repo_proxy"]

    # load US_2Y from master for spread calculation
    master_path = "data/latest_with_cot.csv"
    if os.path.exists(master_path):
        master = pd.read_csv(master_path, index_col=0, parse_dates=True)
        if "US_2Y" in master.columns:
            inr["US_2Y"] = master["US_2Y"].reindex(inr.index, method="ffill")
            if "IN_10Y" in inr.columns:
                inr["US_IN_10Y_spread"]    = inr["US_2Y"] - inr["IN_10Y"]
                inr["US_IN_policy_spread"] = inr["US_2Y"] - inr["IN_repo_proxy"]

    # merge FPI flows
    if len(fpi_df) > 0:
        inr["FPI_20D_flow"]       = fpi_df["FPI_20D_flow"].reindex(inr.index, method="ffill")
        inr["FPI_20D_percentile"] = fpi_df["FPI_20D_percentile"].reindex(inr.index, method="ffill")

    inr.index.name = "date"
    inr.to_csv("data/inr_latest.csv")
    print(f"    saved: data/inr_latest.csv  ({len(inr)} rows x {len(inr.columns)} cols)")

    # merge into latest_with_cot.csv
    if os.path.exists(master_path):
        inr_aligned = inr.reindex(master.index).ffill(limit=5)
        new_cols = [c for c in inr_aligned.columns if c not in master.columns]
        upd_cols = [c for c in inr_aligned.columns if c in master.columns]
        for c in upd_cols:
            master[c] = inr_aligned[c]
        master = pd.concat([master, inr_aligned[new_cols]], axis=1)

        if "USDINR" in master.columns:
            for label, days in {"1D":1,"1W":5,"1M":21,"3M":63,"12M":252}.items():
                master[f"USDINR_chg_{label}"] = (
                    master["USDINR"] / master["USDINR"].shift(days) - 1
                ) * 100

        master.to_csv(master_path)
        print(f"    merged into: {master_path}  ({master.shape[1]} cols total)")

        inr_cols = [c for c in master.columns if "IN" in c or "INR" in c]
        print("INR columns in master:", inr_cols)

    return inr


# -- main ----------------------------------------------------------------------

def main():
    print("=" * 62)
    print(f"  INR PIPELINE -- {TODAY}")
    print("=" * 62)

    price_df     = fetch_usdinr()
    yield_df     = fetch_in_yield()
    fpi_df, fpi_status = fetch_fpi_flows()

    inr = build_and_save(price_df, yield_df, fpi_df, fpi_status)

    print("\n" + "=" * 62)
    print("  INR SUMMARY")
    print("=" * 62)
    if inr is not None and len(inr) > 0:
        latest = inr.iloc[-1]
        print(f"\n  USD/INR:          {latest.get('USDINR', float('nan')):.4f}")
        if "IN_10Y" in inr.columns:
            in10y    = latest.get("IN_10Y", float("nan"))
            cot_date = yield_df.index[-1].date() if len(yield_df) > 0 else "—"
            print(f"  IN 10Y:           {in10y:.2f}%  (FRED monthly, as of {cot_date})")
        if "US_IN_10Y_spread" in inr.columns:
            print(f"  US-IN spread:     {latest.get('US_IN_10Y_spread', float('nan')):.2f}%")
        if fpi_status == "ok" and "FPI_20D_flow" in inr.columns:
            flow = latest.get("FPI_20D_flow", float("nan"))
            pct  = latest.get("FPI_20D_percentile", float("nan"))
            print(f"  FPI 20D flow:     {flow:+,.0f}  (percentile: {pct:.0f}th)")
        else:
            print(f"  FPI data:         unavailable")
    print("\n" + "=" * 62)


if __name__ == "__main__":
    main()
