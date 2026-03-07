# inr_pipeline.py
# standalone pipeline for USD/INR — adds a third pair to the framework
# three sources: yfinance (price), FBIL/RBI (IN 10Y yield daily), SEBI (FPI flows)
# saves to data/inr_latest.csv and merges with data/latest_with_cot.csv
#
# IN 10Y yield: FBIL Par Yield curve (daily, https://www.fbil.org.in/wasdm)
#   → annualized 10Y G-sec benchmark published each business day ~17:30 IST
#   → fallback: FRED INDIRLTLT01STM (monthly, 3-month lag) if FBIL unavailable
# RBI repo rate proxy: IN 10Y minus 1.5pp (no reliable daily FRED series exists)
# FPI flows: SEBI FPI page, net debt investment, 20D rolling cumulative

import os
import io
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta

TODAY      = datetime.today().strftime('%Y-%m-%d')
START_DATE = "2020-01-01"

# FBIL API constants
_FBIL_BASE    = "https://www.fbil.org.in/wasdm"
_FBIL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://www.fbil.org.in/",
    "Origin":     "https://www.fbil.org.in",
}


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


# -- source 2: IN 10Y yield from FBIL (daily) — with FRED monthly fallback ----

def _fbil_download_xlsx(date_str: str) -> bytes:
    """Download the G-sec XLSX for a given date (YYYY-MM-DD)."""
    r = requests.get(
        f"{_FBIL_BASE}/gsec/downloadPublished",
        headers=_FBIL_HEADERS,
        params={"date": date_str},
        timeout=30,
    )
    r.raise_for_status()
    return r.content


def _fbil_parse_10y(xlsx_bytes: bytes) -> float:
    """Extract annualized 10Y yield from Par Yield sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    ws = wb["Par Yield"]
    for row in ws.iter_rows(values_only=True):
        if row[0] == 10:          # Tenor == 10.0 years
            return float(row[2])  # col C = YTM% p.a. Annualized
    raise ValueError("10Y tenor not found in FBIL Par Yield sheet")


_FBIL_CACHE = "data/fbil_in10y_cache.csv"


def _fbil_history(start_date: str = START_DATE) -> pd.DataFrame:
    """
    Build a daily IN_10Y series from FBIL using an incremental cache.

    On first run: fetches all business days from start_date → today.
    On subsequent runs: loads the cache, then only fetches dates newer
    than the last cached row (incremental update — typically 1-3 requests).

    Returns a DataFrame indexed by date with columns [IN_10Y, IN_repo_proxy].
    """
    today_dt  = date.today()
    start_dt  = date.fromisoformat(start_date)

    # ── load existing cache ──────────────────────────────────────────────────
    cached = pd.DataFrame()
    if os.path.exists(_FBIL_CACHE):
        try:
            cached = pd.read_csv(_FBIL_CACHE, index_col=0, parse_dates=True)
            cached.index = pd.to_datetime(cached.index.date)
            print(f"    FBIL cache: {len(cached)} rows, "
                  f"last = {cached.index[-1].date()}")
        except Exception:
            cached = pd.DataFrame()

    # ── decide which days to fetch ───────────────────────────────────────────
    if len(cached) > 0:
        fetch_from = cached.index[-1].date() + timedelta(days=1)
    else:
        fetch_from = start_dt

    new_days = [
        fetch_from + timedelta(days=i)
        for i in range((today_dt - fetch_from).days + 1)
        if (fetch_from + timedelta(days=i)).weekday() < 5
    ]

    if new_days:
        print(f"    FBIL: fetching {len(new_days)} new business days "
              f"({new_days[0]} → {new_days[-1]})")
    else:
        print(f"    FBIL: cache is up to date")

    records = []
    failed  = 0

    def _fetch_one(d):
        ds = d.strftime("%Y-%m-%d")
        try:
            xlsx = _fbil_download_xlsx(ds)
            if len(xlsx) < 1000:
                return None
            yield10 = _fbil_parse_10y(xlsx)
            return {"date": pd.Timestamp(ds), "IN_10Y": yield10}
        except Exception:
            return None

    # Use 20 concurrent workers — fast enough without hammering the server
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_fetch_one, d): d for d in new_days}
        for fut in as_completed(futures):
            result = fut.result()
            if result is not None:
                records.append(result)
            else:
                failed += 1

    if failed:
        print(f"    FBIL: {failed} dates skipped (holidays/errors)")

    # ── merge new rows with cache ────────────────────────────────────────────
    if records:
        new_df = pd.DataFrame(records).set_index("date")
        combined = pd.concat([cached[["IN_10Y"]] if len(cached) > 0 else pd.DataFrame(), new_df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        combined["IN_repo_proxy"] = combined["IN_10Y"] - 1.5
        # save updated cache
        combined.to_csv(_FBIL_CACHE)
        print(f"    FBIL cache updated: {len(combined)} rows total, "
              f"last = {combined.index[-1].date()}")
        return combined
    elif len(cached) > 0:
        cached["IN_repo_proxy"] = cached["IN_10Y"] - 1.5
        return cached
    else:
        raise RuntimeError("FBIL: no records fetched and no cache available")


def _fred_in_yield_fallback() -> pd.DataFrame:
    """Fallback: FRED INDIRLTLT01STM monthly series (3-month lag)."""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDIRLTLT01STM"
    r   = requests.get(url, timeout=15)
    r.raise_for_status()
    monthly = pd.read_csv(io.StringIO(r.text), index_col=0, parse_dates=True)
    monthly.columns = ["IN_10Y"]
    monthly["IN_10Y"] = pd.to_numeric(monthly["IN_10Y"], errors="coerce")
    monthly = monthly.dropna()
    monthly = monthly[monthly.index >= START_DATE]
    monthly["IN_repo_proxy"] = monthly["IN_10Y"] - 1.5
    return monthly


def fetch_in_yield():
    print("\n[2/3] fetching IN 10Y yield (FBIL daily G-sec benchmark)...")

    # ── Primary: FBIL daily ──────────────────────────────────────────────────
    try:
        daily = _fbil_history(start_date=START_DATE)
        latest_date = daily.index[-1].date()
        latest_val  = daily["IN_10Y"].iloc[-1]

        lag_days = (date.today() - latest_date).days
        if lag_days > 5:
            print(f"    WARNING: FBIL data is {lag_days} calendar days old "
                  f"(last: {latest_date}). Check FBIL availability.")
        else:
            print(f"    OK  daily, as of {latest_date} = {latest_val:.2f}%  "
                  f"(repo proxy = {latest_val - 1.5:.2f}%)")

        daily.source = "FBIL"
        daily.is_monthly = False
        return daily

    except Exception as e:
        print(f"    FBIL FAILED ({e}) — falling back to FRED monthly...")

    # ── Fallback: FRED monthly (3-month lag) ─────────────────────────────────
    try:
        monthly = _fred_in_yield_fallback()
        latest_date = monthly.index[-1].date()
        latest_val  = monthly["IN_10Y"].iloc[-1]
        lag_days    = (date.today() - latest_date).days
        print(f"    FRED fallback OK  monthly, as of {latest_date} = {latest_val:.2f}%")
        if lag_days > 30:
            print(f"    WARNING: FRED IN_10Y is {lag_days} days stale — "
                  f"spread charts will be frozen at {latest_date}")
        monthly.source = "FRED"
        monthly.is_monthly = True
        return monthly

    except Exception as e2:
        print(f"    FRED FAILED -- {e2}")
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

def build_and_save(price_df, yield_df, fpi_df, fpi_status):
    print("\n[saving] assembling inr_latest.csv...")
    os.makedirs("data", exist_ok=True)

    if len(price_df) == 0:
        print("    ERROR -- no price data, aborting")
        return

    # reindex yield to daily using price calendar
    # FBIL: already daily — just reindex (no ffill needed across holidays)
    # FRED: monthly — forward-fill but cap at 22 trading days (~1 month) to
    #       avoid silently propagating a stale Dec value through all of 2026
    inr = price_df.copy()
    if len(yield_df) > 0:
        is_monthly = getattr(yield_df, 'is_monthly', True)
        if is_monthly:
            # FRED fallback: cap forward-fill at 22 rows (1 calendar month approx)
            yield_daily = yield_df.reindex(inr.index).ffill(limit=22)
            source_label = "FRED monthly (fallback)"
        else:
            # FBIL daily: allow up to 5-day fill (weekends / holidays only)
            yield_daily = yield_df.reindex(inr.index).ffill(limit=5)
            source_label = "FBIL daily"
        inr["IN_10Y"]        = yield_daily["IN_10Y"]
        inr["IN_repo_proxy"] = yield_daily["IN_repo_proxy"]
        inr["IN_10Y_source"] = source_label

    # load US_2Y from master for spread calculation
    master_path = "data/latest_with_cot.csv"
    if os.path.exists(master_path):
        master = pd.read_csv(master_path, index_col=0, parse_dates=True)
        if "US_2Y" in master.columns:
            inr["US_2Y"] = master["US_2Y"].reindex(inr.index).ffill()
            if "IN_10Y" in inr.columns:
                inr["US_IN_10Y_spread"]    = inr["US_2Y"] - inr["IN_10Y"]
                inr["US_IN_policy_spread"] = inr["US_2Y"] - inr["IN_repo_proxy"]

    # merge FPI flows
    if len(fpi_df) > 0:
        inr["FPI_20D_flow"]       = fpi_df["FPI_20D_flow"].reindex(inr.index).ffill()
        inr["FPI_20D_percentile"] = fpi_df["FPI_20D_percentile"].reindex(inr.index).ffill()

    # Compute USDINR vol on the original price series BEFORE reindexing to the
    # US trading calendar.  Reindexing introduces ffill gaps (Indian holidays
    # mapped to US dates) which produce zero log-returns and understate vol.
    if "USDINR" in inr.columns:
        _lr = np.log(inr["USDINR"] / inr["USDINR"].shift(1))
        inr["USDINR_vol30"] = _lr.rolling(window=30).std() * np.sqrt(252) * 100
        inr["USDINR_vol_pct"] = (
            inr["USDINR_vol30"]
            .rolling(window=252 * 3, min_periods=126)
            .rank(pct=True) * 100
        )
        _v = inr["USDINR_vol30"].dropna().iloc[-1]
        _p = inr["USDINR_vol_pct"].dropna().iloc[-1]
        _flag = "EXTREME" if _p >= 90 else ("ELEVATED" if _p >= 75 else "NORMAL")
        print(f"    USDINR vol: {_v:.1f}% annualized | {_p:.0f}th pct | {_flag}")

    inr.index.name = "date"
    inr.to_csv("data/inr_latest.csv")
    print(f"    saved: data/inr_latest.csv  ({len(inr)} rows x {len(inr.columns)} cols)")

    # merge into latest_with_cot.csv
    if os.path.exists(master_path):
        # for USDINR and daily yields, allow only small forward-fill gaps (weekends)
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

        # USDINR_vol30 / USDINR_vol_pct are computed on the original INR
        # price series above (before reindexing) and carried through inr_aligned.

        # oil correlation for INR (Phase 1)
        # Brent is fetched by pipeline.py and lives in master at this point
        if "Brent" in master.columns and "USDINR" in master.columns:
            brent_ret = master["Brent"].pct_change()
            usdinr_ret = master["USDINR"].pct_change()
            master["oil_inr_corr_60d"] = brent_ret.rolling(60).corr(usdinr_ret)
            latest_oil = master["oil_inr_corr_60d"].dropna()
            if len(latest_oil) > 0:
                print(f"    oil_inr_corr_60d: {latest_oil.iloc[-1]:>+.3f}")

        # DXY decomposition for INR (Phase 2)
        # DXY lives in master from pipeline.py; USDINR joined above
        if "DXY" in master.columns and "USDINR" in master.columns:
            dxy_ret    = master["DXY"].pct_change()
            usdinr_ret = master["USDINR"].pct_change()
            master["dxy_inr_corr_60d"] = dxy_ret.rolling(60).corr(usdinr_ret)
            latest_dxy = master["dxy_inr_corr_60d"].dropna()
            if len(latest_dxy) > 0:
                print(f"    dxy_inr_corr_60d:  {latest_dxy.iloc[-1]:>+.3f}")

        # 12M change for US-IN spreads — windowed search to handle monthly source gaps
        for col in ("US_IN_10Y_spread", "US_IN_policy_spread"):
            chg_col = f"{col}_chg_12M"
            if col in master.columns:
                s = master[col]
                chg = pd.Series(index=master.index, dtype=float)
                for pos in range(len(s)):
                    curr = s.iloc[pos]
                    if pd.isna(curr):
                        continue
                    target = pos - 252
                    if target < 0:
                        continue
                    # search ±10 rows around the 252-row mark for nearest non-NaN
                    lo = max(0, target - 10)
                    hi = min(len(s) - 1, target + 10)
                    window = s.iloc[lo:hi + 1].dropna()
                    if len(window) == 0:
                        continue
                    # pick the row closest to target position
                    best_idx = min(window.index, key=lambda d: abs(s.index.get_loc(d) - target))
                    chg.iloc[pos] = curr - s[best_idx]
                master[chg_col] = chg

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

    price_df             = fetch_usdinr()
    yield_df             = fetch_in_yield()
    fpi_df, fpi_status   = fetch_fpi_flows()

    inr = build_and_save(price_df, yield_df, fpi_df, fpi_status)

    print("\n" + "=" * 62)
    print("  INR SUMMARY")
    print("=" * 62)
    if inr is not None and len(inr) > 0:
        latest = inr.iloc[-1]
        print(f"\n  USD/INR:          {latest.get('USDINR', float('nan')):.4f}")
        if "IN_10Y" in inr.columns:
            in10y    = latest.get("IN_10Y", float("nan"))
            # find last non-NaN date for IN_10Y (may be gap-filled)
            in10y_dates = inr["IN_10Y"].dropna()
            in10y_date  = in10y_dates.index[-1].date() if len(in10y_dates) > 0 else "?"
            source_lbl  = latest.get("IN_10Y_source", "")
            print(f"  IN 10Y:           {in10y:.2f}%  ({source_lbl}, as of {in10y_date})")
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
