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
import sys
import time
import requests
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

from config import TODAY, START_DATE, MAX_FFILL_DAYS, ROLLING_WINDOW, CORR_WINDOW, VOL_WINDOW

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
        try:
            if row[0] is not None and float(row[0]) == 10.0:  # Tenor == 10 years (may be int, float, or string)
                return float(row[2])  # col C = YTM% p.a. Annualized
        except (TypeError, ValueError):
            continue
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
            cached = pd.read_csv(_FBIL_CACHE, index_col=0, parse_dates=True, encoding='utf-8')
            cached.index = pd.to_datetime(cached.index.date)
            print(f"    FBIL cache: {len(cached)} rows, "
                  f"last = {cached.index[-1].date()}")
        except (pd.errors.ParserError, OSError, ValueError) as e:
            print(f"    FBIL cache read failed ({e}) — re-fetching from scratch")
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
              f"({new_days[0]} to {new_days[-1]})")
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
        except (OSError, ValueError, KeyError, RuntimeError):
            return None

    # Use 5 concurrent workers — avoid hammering the server
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch_one, d): d for d in new_days}
        for fut in as_completed(futures):
            try:
                result = fut.result()
            except (OSError, ValueError, KeyError, RuntimeError):
                result = None
            if result is not None:
                records.append(result)
            else:
                failed += 1

    if failed:
        print(f"    FBIL: {failed} dates skipped (holidays/errors)")

    # ── merge new rows with cache ────────────────────────────────────────────
    if records:
        new_df = pd.DataFrame(records).set_index("date")
        # Use column intersection so IN_repo_proxy (and any future cols) are preserved
        cache_slice = cached[cached.columns.intersection(new_df.columns)] if len(cached) > 0 else pd.DataFrame()
        combined = pd.concat([cache_slice, new_df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        combined["IN_repo_proxy"] = combined["IN_10Y"] - 1.5
        # atomic write: write to .tmp then rename so a crash can't corrupt cache
        _tmp = _FBIL_CACHE + ".tmp"
        combined.to_csv(_tmp, encoding='utf-8')
        os.replace(_tmp, _FBIL_CACHE)
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


def _fetch_rbi_reserves() -> pd.Series:
    """Fetch India FX reserves.
    Primary: FRED RBUKRESERVES (weekly, USD billions) via fredapi.
    Fallback: FRED TRESEGINM052N (monthly total reserves excl gold, USD millions → convert to bn).
    """
    # Primary: weekly series via fredapi with API key
    try:
        from fredapi import Fred
        from dotenv import load_dotenv
        load_dotenv()
        _api_key = os.getenv("FRED_API_KEY")
        if not _api_key:
            raise ValueError("FRED_API_KEY not set")
        fred_client = Fred(api_key=_api_key)
        raw = fred_client.get_series("RBUKRESERVES", observation_start=START_DATE)
        raw = raw.dropna()
        if len(raw) == 0:
            raise ValueError("RBUKRESERVES returned no data")
        raw.name = "rbi_reserves"
        return raw
    except (ImportError, OSError, ValueError, RuntimeError) as e:
        print(f"    WARN: RBI reserves primary (RBUKRESERVES) failed: {e} — trying fallback")

    # Fallback: FRED TRESEGINM052N monthly (USD millions → convert to billions)
    try:
        from fredapi import Fred
        from dotenv import load_dotenv
        load_dotenv()
        _api_key = os.getenv("FRED_API_KEY")
        if _api_key:
            fred_client = Fred(api_key=_api_key)
            raw = fred_client.get_series("TRESEGINM052N", observation_start=START_DATE)
            raw = raw.dropna() / 1000  # millions → billions
            if len(raw) > 0:
                raw.name = "rbi_reserves"
                return raw
    except (ImportError, OSError, ValueError, RuntimeError) as e:
        print(f"    WARN: RBI reserves fallback (TRESEGINM052N) also failed: {e}")

    raise RuntimeError("All RBI reserves data sources failed")


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

_NSE_FPI_CACHE = os.path.join("data", "fpi_daily.csv")
_NSE_HOMEPAGE  = "https://www.nseindia.com"
_NSE_FIIDII    = "https://www.nseindia.com/api/fiidiiTradeReact"


def _fetch_fpi_nse():
    """Fetch today's FII/FPI equity net flow from NSE and update the daily cache.

    NSE requires loading the homepage first to obtain session cookies before
    the API endpoint will respond. The API returns only the latest trading
    day's data (one row per category: DII and FII/FPI).

    Returns a DataFrame indexed by date with column 'FPI_equity_net' (Cr INR).
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    # Load homepage to obtain anti-bot cookies
    session.get(_NSE_HOMEPAGE, timeout=15)
    time.sleep(0.5)

    session.headers.update({
        "Accept":           "application/json, text/plain, */*",
        "Referer":          _NSE_HOMEPAGE + "/",
        "X-Requested-With": "XMLHttpRequest",
    })
    r = session.get(_NSE_FIIDII, timeout=15)
    r.raise_for_status()
    rows = r.json()

    fii_row = next(
        (x for x in rows if "FII" in str(x.get("category", "")).upper()), None
    )
    if fii_row is None:
        raise ValueError(f"No FII/FPI entry in NSE response: {rows}")

    trade_date = pd.to_datetime(fii_row["date"], dayfirst=True, errors="coerce")
    net_val    = float(str(fii_row["netValue"]).replace(",", ""))

    new_row = pd.DataFrame({"FPI_equity_net": [net_val]}, index=[trade_date])
    new_row.index.name = "date"

    # Load existing cache, append new row, deduplicate, persist
    if os.path.exists(_NSE_FPI_CACHE):
        cache = pd.read_csv(_NSE_FPI_CACHE, index_col=0, parse_dates=True)
        cache = pd.concat([cache, new_row])
    else:
        cache = new_row
    cache = cache[~cache.index.duplicated(keep="last")].sort_index()
    cache.to_csv(_NSE_FPI_CACHE)
    return cache


def fetch_fpi_flows():
    print("\n[3/3] fetching FPI flows (NSE primary, SEBI fallback)...")

    # ── Primary: NSE FII/FPI equity flow (builds growing daily cache) ─────────
    try:
        cache = _fetch_fpi_nse()
        cache = cache[cache.index >= START_DATE]

        # 20-day rolling sum; min_periods=1 so the signal is live from day one
        # (a single-day value equals that day's net flow until the window fills)
        cache["FPI_20D_flow"] = (
            cache["FPI_equity_net"].rolling(20, min_periods=1).sum()
        )
        cache["FPI_20D_percentile"] = (
            cache["FPI_20D_flow"]
            .rolling(ROLLING_WINDOW * 3, min_periods=30)
            .rank(pct=True) * 100
        )

        valid = cache.dropna(subset=["FPI_20D_flow"])
        if len(valid) == 0:
            raise ValueError("cache exists but FPI_20D_flow all NaN")

        latest = valid.iloc[-1]
        n_days = int(cache["FPI_equity_net"].notna().sum())
        pct_str = (
            f"{latest['FPI_20D_percentile']:.0f}th"
            if pd.notna(latest["FPI_20D_percentile"])
            else "N/A (building cache)"
        )
        print(f"    OK  NSE cache {n_days}d, latest: {cache.index[-1].date()}")
        print(f"    FPI 20D flow: {latest['FPI_20D_flow']:+,.0f}  "
              f"percentile: {pct_str}")
        return cache[["FPI_20D_flow", "FPI_20D_percentile"]], "ok"

    except Exception as nse_err:
        print(f"    NSE failed ({nse_err}); trying SEBI fallback...")

    # ── Fallback: SEBI HTML scrape (debt market flows) ────────────────────────
    url = (
        "https://www.sebi.gov.in/sebiweb/other/OtherAction.do"
        "?doRecognisedFpi=yes&intmId=13"
    )
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            print(f"    FAILED -- status {r.status_code}")
            return pd.DataFrame(), "unavailable"

        tables = pd.read_html(io.StringIO(r.text))
        fpi_df = None
        for tbl in tables:
            cols_lower = [str(c).lower() for c in tbl.columns]
            if any("debt" in c for c in cols_lower):
                fpi_df = tbl.copy()
                break

        if fpi_df is None:
            print("    FAILED -- no debt table found in SEBI page")
            return pd.DataFrame(), "unavailable"

        fpi_df.columns = [str(c).strip() for c in fpi_df.columns]
        date_col = next((c for c in fpi_df.columns if "date" in c.lower()), None)
        debt_col = next(
            (c for c in fpi_df.columns if "debt" in c.lower() and "net" in c.lower()),
            None,
        )
        if debt_col is None:
            debt_col = next(
                (c for c in fpi_df.columns if "debt" in c.lower()), None
            )

        if date_col is None or debt_col is None:
            print(f"    FAILED -- columns: {fpi_df.columns.tolist()}")
            return pd.DataFrame(), "unavailable"

        fpi_df = fpi_df[[date_col, debt_col]].copy()
        fpi_df.columns = ["date", "FPI_debt_net"]
        fpi_df["date"] = pd.to_datetime(fpi_df["date"], dayfirst=True, errors="coerce")
        fpi_df = fpi_df.dropna(subset=["date"])
        fpi_df["FPI_debt_net"] = pd.to_numeric(
            fpi_df["FPI_debt_net"].astype(str).str.replace(",", ""), errors="coerce"
        )
        fpi_df = fpi_df.set_index("date").sort_index()
        fpi_df = fpi_df[fpi_df.index >= START_DATE]

        fpi_df["FPI_20D_flow"] = fpi_df["FPI_debt_net"].rolling(20).sum()
        fpi_df["FPI_20D_percentile"] = (
            fpi_df["FPI_20D_flow"]
            .rolling(ROLLING_WINDOW * 3, min_periods=60)
            .rank(pct=True) * 100
        )

        latest = fpi_df.dropna(subset=["FPI_20D_flow"]).iloc[-1]
        print(f"    OK (SEBI)  {len(fpi_df)} rows, latest: {fpi_df.index[-1].date()}")
        print(
            f"    FPI 20D flow: {latest['FPI_20D_flow']:+,.0f}  "
            f"percentile: {latest['FPI_20D_percentile']:.0f}th"
        )
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
            # FRED fallback: FRED INDIRLTLT01STM lags ~2 months (last print Jan 2026).
            # Cap at 90 trading days (~4 months) so CI runs through April without
            # going NaN — mirrors the IT_10Y / BTP-Bund fix already in pipeline.py.
            yield_daily = yield_df.reindex(inr.index).ffill(limit=90)
            source_label = "FRED monthly (fallback)"
        else:
            # FBIL daily: allow up to 5-day fill (weekends / holidays only)
            yield_daily = yield_df.reindex(inr.index).ffill(limit=MAX_FFILL_DAYS)
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
        if "US_10Y" in master.columns:
            inr["US_10Y"] = master["US_10Y"].reindex(inr.index).ffill()
            if "IN_10Y" in inr.columns:
                inr["US_IN_10Y_spread"]    = inr["US_10Y"] - inr["IN_10Y"]
                inr["US_IN_policy_spread"] = inr["US_2Y"] - inr["IN_repo_proxy"]

    # merge FPI flows
    if len(fpi_df) > 0:
        # asof() aligns on nearest preceding date — handles the common case where
        # NSE reports tomorrow's FPI row before yfinance has updated today's price
        inr["FPI_20D_flow"]       = fpi_df["FPI_20D_flow"].asof(inr.index)
        inr["FPI_20D_percentile"] = fpi_df["FPI_20D_percentile"].asof(inr.index)
        # When the entire FPI cache is ahead of the price calendar (e.g., NSE reports
        # same-day after market close but yfinance still shows yesterday's close),
        # asof returns NaN for all rows. Carry the latest FPI value back to the
        # last 5 price dates (same-week signal, same economic content).
        if inr["FPI_20D_flow"].iloc[-1:].isna().all():
            last_fpi_flow = fpi_df["FPI_20D_flow"].dropna()
            last_fpi_pct  = fpi_df["FPI_20D_percentile"].dropna()
            if len(last_fpi_flow) > 0:
                tail_idx = inr.index[-5:]
                inr.loc[tail_idx, "FPI_20D_flow"] = (
                    inr.loc[tail_idx, "FPI_20D_flow"].fillna(last_fpi_flow.iloc[-1])
                )
                if len(last_fpi_pct) > 0:
                    inr.loc[tail_idx, "FPI_20D_percentile"] = (
                        inr.loc[tail_idx, "FPI_20D_percentile"].fillna(last_fpi_pct.iloc[-1])
                    )

    # Compute USDINR vol on the original price series BEFORE reindexing to the
    # US trading calendar.  Reindexing introduces ffill gaps (Indian holidays
    # mapped to US dates) which produce zero log-returns and understate vol.
    if "USDINR" in inr.columns:
        _lr = np.log(inr["USDINR"] / inr["USDINR"].shift(1))
        inr["USDINR_vol30"] = _lr.rolling(window=VOL_WINDOW).std() * np.sqrt(252) * 100
        inr["USDINR_vol_pct"] = (
            inr["USDINR_vol30"]
            .rolling(window=ROLLING_WINDOW * 3, min_periods=126)
            .rank(pct=True) * 100
        )
        _v = inr["USDINR_vol30"].dropna().iloc[-1]
        _p = inr["USDINR_vol_pct"].dropna().iloc[-1]
        _flag = "EXTREME" if _p >= 90 else ("ELEVATED" if _p >= 75 else "NORMAL")
        print(f"    USDINR vol: {_v:.1f}% annualized | {_p:.0f}th pct | {_flag}")

    inr.index.name = "date"
    inr.to_csv("data/inr_latest.csv", encoding='utf-8')
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
            master["oil_inr_corr_60d"] = brent_ret.rolling(CORR_WINDOW).corr(usdinr_ret)
            latest_oil = master["oil_inr_corr_60d"].dropna()
            if len(latest_oil) > 0:
                print(f"    oil_inr_corr_60d: {latest_oil.iloc[-1]:>+.3f}")

        # DXY decomposition for INR (Phase 2)
        # DXY lives in master from pipeline.py; USDINR joined above
        if "DXY" in master.columns and "USDINR" in master.columns:
            dxy_ret    = master["DXY"].pct_change()
            usdinr_ret = master["USDINR"].pct_change()
            master["dxy_inr_corr_60d"] = dxy_ret.rolling(CORR_WINDOW).corr(usdinr_ret)
            latest_dxy = master["dxy_inr_corr_60d"].dropna()
            if len(latest_dxy) > 0:
                print(f"    dxy_inr_corr_60d:  {latest_dxy.iloc[-1]:>+.3f}")

        # gold correlation for INR (Phase 4)
        # India is world's 2nd-largest gold consumer: import demand = USD buying = INR selling
        # Expected correlation: positive (gold up -> INR weaker -> USD/INR up)
        if "Gold" in master.columns and "USDINR" in master.columns:
            gold_ret_inr = master["Gold"].pct_change()
            usdinr_ret_g = master["USDINR"].pct_change()
            master["gold_inr_corr_60d"] = gold_ret_inr.rolling(CORR_WINDOW).corr(usdinr_ret_g)
            latest_gold = master["gold_inr_corr_60d"].dropna()
            if len(latest_gold) > 0:
                print(f"    gold_inr_corr_60d: {latest_gold.iloc[-1]:>+.3f}")

        # gold seasonal demand flags for INR
        # Oct-Nov: Diwali season, Dec-Feb: Wedding season, Apr-May: Akshaya Tritiya
        master["gold_seasonal_flag"] = master.index.month.isin(
            [10, 11, 12, 1, 2, 4, 5]
        ).astype(int)

        def _gold_seasonal_label(m):
            if m in [10, 11]:
                return "DIWALI SEASON"
            elif m in [12, 1, 2]:
                return "WEDDING SEASON"
            elif m in [4, 5]:
                return "AKSHAYA TRITIYA"
            return None

        master["gold_seasonal_label"] = pd.Series(
            master.index.month, index=master.index
        ).map(_gold_seasonal_label)
        latest_flag = int(master["gold_seasonal_flag"].iloc[-1])
        latest_lbl  = master["gold_seasonal_label"].iloc[-1]
        print(f"    gold_seasonal_flag: {latest_flag}  label: {latest_lbl}")

        # RBI FX reserves (Phase 5)
        # FRED RBUKRESERVES: weekly, USD billions (India total reserves incl. gold, SDR)
        # Drop >$3B in 7 days = RBI selling USD to defend INR floor (ACTIVE SUPPORT)
        # Rise >$3B in 7 days = RBI buying USD to cap appreciation  (ACTIVE CAPPING)
        try:
            rbi_raw         = _fetch_rbi_reserves()
            rbi_chg_raw     = rbi_raw.diff(1)   # 1-period change (weekly or monthly, in USD bn)
            rbi_daily_val   = rbi_raw.resample("D").ffill()
            rbi_daily_chg   = rbi_chg_raw.resample("D").ffill()
            # limit=90: covers up to ~3 months of trading days (handles monthly data lag)
            rbi_aligned     = rbi_daily_val.reindex(master.index).ffill(limit=90)
            rbi_chg_aligned = rbi_daily_chg.reindex(master.index).ffill(limit=90)
            master["rbi_reserves"]       = rbi_aligned
            master["rbi_reserve_chg_1w"] = rbi_chg_aligned

            def _rbi_flag(chg):
                if pd.isna(chg):  return "UNKNOWN"
                elif chg < -3.0:  return "ACTIVE SUPPORT"   # -$3B/wk or -$5B/month
                elif chg >  3.0:  return "ACTIVE CAPPING"   # +$3B/wk or +$5B/month
                else:             return "NEUTRAL"

            master["rbi_intervention_flag"] = master["rbi_reserve_chg_1w"].apply(_rbi_flag)
            latest_rbi_chg  = master["rbi_reserve_chg_1w"].dropna()
            latest_rbi_flag = master["rbi_intervention_flag"].dropna()
            if len(latest_rbi_chg) > 0:
                print(f"    rbi_reserve_chg_1w: {latest_rbi_chg.iloc[-1]:>+.1f}B  "
                      f"flag: {latest_rbi_flag.iloc[-1]}")
        except Exception as e:
            print(f"    WARN -- RBI reserves fetch failed: {e}")
            master["rbi_reserves"]          = float("nan")
            master["rbi_reserve_chg_1w"]    = float("nan")
            master["rbi_intervention_flag"] = "UNKNOWN"

        # INR Composite Regime Score (Phase 7)
        # Synthesizes 5 signals into [-100, +100] score
        # Positive = depreciation pressure (USD/INR up), Negative = appreciation pressure
        # FPI and RBI components default to 0 (neutral) when data is unavailable
        _required_composite = ["oil_inr_corr_60d", "dxy_inr_corr_60d", "US_IN_10Y_spread"]
        if all(c in master.columns for c in _required_composite):
            _brent_1d = master["Brent"].pct_change() if "Brent" in master.columns else pd.Series(0.0, index=master.index)
            _dxy_1d   = master["DXY"].pct_change()   if "DXY"   in master.columns else pd.Series(0.0, index=master.index)
            _rbi_score_map = {"ACTIVE SUPPORT": -0.30, "ACTIVE CAPPING": 0.20, "NEUTRAL": 0.0, "UNKNOWN": 0.0}

            def _compute_inr_composite(row_s):
                try:
                    def _safe(v): return 0.0 if pd.isna(v) else float(v)
                    def _sign(v): return 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)
                    oil_s  = _safe(row_s.get("oil_inr_corr_60d")) * _sign(_safe(_brent_1d.get(row_s.name, 0))) * 0.25
                    dxy_s  = _safe(row_s.get("dxy_inr_corr_60d")) * _sign(_safe(_dxy_1d.get(row_s.name,   0))) * 0.20
                    fpi_s  = -min(max(_safe(row_s.get("FPI_20D_flow")) / 20000, -1.0), 1.0) * 0.25
                    rbi_fv = str(row_s.get("rbi_intervention_flag", "NEUTRAL"))
                    rbi_fv = rbi_fv if rbi_fv != "nan" else "NEUTRAL"
                    rbi_s  = _rbi_score_map.get(rbi_fv, 0.0) * 0.20
                    rate_s = _sign(-_safe(row_s.get("US_IN_10Y_spread"))) * 0.10
                    return float(np.clip((oil_s + dxy_s + fpi_s + rbi_s + rate_s) * 100, -100, 100))
                except (TypeError, KeyError, ArithmeticError, ValueError):
                    return float("nan")

            master["inr_composite_score"] = master.apply(_compute_inr_composite, axis=1)

            def _inr_score_label_fn(score):
                if pd.isna(score): return "UNKNOWN"
                if score >  60:    return "STRONG DEPRECIATION PRESSURE"
                if score >  30:    return "MODERATE DEPRECIATION PRESSURE"
                if score > -30:    return "NEUTRAL"
                if score > -60:    return "MODERATE APPRECIATION PRESSURE"
                return "STRONG APPRECIATION PRESSURE"

            master["inr_composite_label"] = master["inr_composite_score"].apply(_inr_score_label_fn)
            latest_score = master["inr_composite_score"].dropna()
            if len(latest_score) > 0:
                print(f"    inr_composite_score: {latest_score.iloc[-1]:>+.1f}  "
                      f"[{master['inr_composite_label'].dropna().iloc[-1]}]")
        else:
            _missing = [c for c in _required_composite if c not in master.columns]
            print(f"    SKIP inr_composite -- missing cols: {_missing}")

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
                    # search ±10 integer positions around target for nearest non-NaN
                    lo = max(0, target - 10)
                    hi = min(len(s) - 1, target + 10)
                    # use integer positions directly — O(1) per lookup, no get_loc needed
                    win_valid_positions = [p for p in range(lo, hi + 1) if not pd.isna(s.iloc[p])]
                    if not win_valid_positions:
                        continue
                    best_int_pos = min(win_valid_positions, key=lambda p: abs(p - target))
                    chg.iloc[pos] = curr - s.iloc[best_int_pos]
                master[chg_col] = chg

        master.to_csv(master_path, encoding='utf-8')
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
    if price_df.empty:
        print("ERROR: USD/INR price data unavailable — aborting pipeline")
        sys.exit(1)
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

    try:
        from core.signal_write import sync_all_signals_from_master_csv
        from core.paper_export import write_signals_latest_json

        if sync_all_signals_from_master_csv():
            print("  Supabase: full signals history upsert OK (if configured)")
        write_signals_latest_json()
    except Exception as e:
        print(f"  WARN: Supabase signals sync / paper export skipped: {e}")


if __name__ == "__main__":
    main()
