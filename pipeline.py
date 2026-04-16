# pipeline.py
# pulls G10 FX + yields, calculates spreads and % changes
# data sources:
#   FX prices  -> Yahoo Finance (yfinance)
#   US yields  -> FRED API (daily)
#   DE yields  -> ECB Yield Curve API (daily, eurozone govt bonds)
#   JP yields  -> MOF Japan (daily JGB yield curve CSV)
#
# run every morning before writing your memo
# charts are handled separately by create_dashboards.py

import os
import sys
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv
from io import StringIO
from concurrent.futures import ThreadPoolExecutor

from config import TODAY, START_DATE, MAX_FFILL_DAYS, VOL_WINDOW, ROLLING_WINDOW, CORR_WINDOW, PERIODS, VIX_TICKER
from core.paths import LATEST_WITH_COT_CSV, DATA_DIR
from core.utils import _yf_safe_download

"""
G10 FX and yields (fx + merge) Pipeline.

Execution context:
- Called by run.py as STEP 1 (fx) and merge (same script)
- Depends on: none
- Outputs: data/latest.csv, data/latest_with_cot.csv (merge phase)
- Next step: cot_pipeline.py
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

load_dotenv()
FRED_KEY = os.getenv("FRED_API_KEY")
if not FRED_KEY:
    import warnings
    warnings.warn(
        "FRED_API_KEY not set — FRED data fetches will fail",
        RuntimeWarning,
        stacklevel=2,
    )
fred     = Fred(api_key=FRED_KEY)

# -- settings ------------------------------------------------------------------

FX_TICKERS = {
    "EURUSD": "EURUSD=X",
    "USDJPY": "JPY=X",
    "DXY":    "DX-Y.NYB",
}

# Commodity prices from Yahoo Finance (daily futures)
# Brent crude: BZ=F (ICE front-month Brent)
# Gold:        GC=F (COMEX front-month Gold)
COMMODITY_TICKERS = {
    "Brent": "BZ=F",
    "Gold":  "GC=F",
}

# US yields from FRED (daily)
FRED_SERIES = {
    "US_2Y":  "DGS2",
    "US_10Y": "DGS10",
}

# DE yields from ECB (daily, eurozone govt bond yield curve)
ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"
ECB_SERIES = {
    "DE_2Y":  "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
    "DE_10Y": "YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
}

# JP yields from MOF Japan (daily JGB yield curve)
MOF_HISTORICAL_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
MOF_CURRENT_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"


# -- step 1: fx prices ---------------------------------------------------------

def fetch_fx_data():
    print("\n[1/5] fetching FX prices from yahoo finance...")

    raw = pd.DataFrame()
    for attempt in range(1, 4):
        raw = _yf_safe_download(
            list(FX_TICKERS.values()),
            start=START_DATE,
            end=TODAY,
            interval="1d",
            auto_adjust=True,
        )
        if not raw.empty and "Close" in raw.columns:
            break
        wait = 30 * attempt
        print(f"    yfinance attempt {attempt}/3 returned empty -- retrying in {wait}s...")
        time.sleep(wait)
    else:
        print("    WARN: yfinance failed after 3 attempts — returning empty frame")
        return pd.DataFrame()

    prices = raw["Close"].copy()
    reverse_map = {v: k for k, v in FX_TICKERS.items()}
    prices.rename(columns=reverse_map, inplace=True)
    prices.index = pd.to_datetime(prices.index)
    prices.index.name = "date"

    # yfinance daily bars already carry the correct calendar date — just strip
    # any time/tz component without shifting via tz_convert (tz_convert shifts
    # midnight UTC back 5 h → T-2 bug on NY closing data)
    prices.index = pd.to_datetime(prices.index.date)

    prices = prices[prices.index.date < pd.Timestamp(TODAY).date()]
    prices = prices[prices.index.dayofweek < 5]

    # DXY trades on ICE with different holidays -- fill gaps up to MAX_FFILL_DAYS days
    # Fallback: yfinance silently drops DXY from batch downloads; retry standalone with DX=F
    if "DXY" not in prices.columns or prices["DXY"].tail(5).isna().all():
        print("    DXY missing/NaN from batch -- retrying standalone with DX=F...")
        try:
            _dxy_raw = _yf_safe_download(
                "DX=F", start=START_DATE, end=TODAY,
                interval="1d", auto_adjust=True,
            )
            if not _dxy_raw.empty:
                _dxy_series = (_dxy_raw["Close"] if "Close" in _dxy_raw.columns
                               else _dxy_raw.iloc[:, 0]).copy()
                _dxy_series.index = pd.to_datetime(_dxy_series.index.date)
                _dxy_series = _dxy_series[_dxy_series.index.date < pd.Timestamp(TODAY).date()]
                _dxy_series = _dxy_series[_dxy_series.index.dayofweek < 5]
                prices["DXY"] = _dxy_series
                print(f"    DXY fallback (DX=F) OK -- {int(_dxy_series.notna().sum())} rows")
            else:
                print("    DXY fallback (DX=F) returned empty -- DXY will be NaN")
        except Exception as _dxy_err:
            print(f"    DXY fallback failed: {_dxy_err}")
    if "DXY" in prices.columns:
        prices["DXY"] = prices["DXY"].ffill(limit=MAX_FFILL_DAYS)

    print(f"    got {prices.shape[0]} rows, {prices.shape[1]} pairs")
    print(f"    from {prices.index[0].date()} to {prices.index[-1].date()}")
    return prices


# -- step 1b: commodity prices -------------------------------------------------
#
# Brent crude (BZ=F) and Gold (GC=F) via Yahoo Finance.
# These are front-month futures — prices roll forward at expiry but are
# good enough for daily correlation and trend work.
# Forward-filled up to 5 days to bridge exchange holidays.

def fetch_commodity_data():
    print("\n[1b] fetching commodity prices from yahoo finance...")

    raw = pd.DataFrame()
    for attempt in range(1, 4):
        raw = _yf_safe_download(
            list(COMMODITY_TICKERS.values()),
            start=START_DATE,
            end=TODAY,
            interval="1d",
            auto_adjust=True,
        )
        if not raw.empty:
            break
        wait = 30 * attempt
        print(f"    yfinance attempt {attempt}/3 returned empty -- retrying in {wait}s...")
        time.sleep(wait)
    else:
        print("    WARN: commodity yfinance failed after 3 attempts — returning empty frame")
        return pd.DataFrame()

    # yfinance returns multi-level columns when fetching multiple tickers
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].copy()
    else:
        prices = raw[["Close"]].copy()

    reverse_map = {v: k for k, v in COMMODITY_TICKERS.items()}
    prices.rename(columns=reverse_map, inplace=True)
    prices.index = pd.to_datetime(prices.index)
    prices.index.name = "date"

    # yfinance daily bars already carry the correct calendar date
    prices.index = pd.to_datetime(prices.index.date)

    prices = prices[prices.index.date < pd.Timestamp(TODAY).date()]
    prices = prices[prices.index.dayofweek < 5]

    # forward-fill gaps (exchange holidays, expiry roll gaps)
    for col in prices.columns:
        prices[col] = prices[col].ffill(limit=MAX_FFILL_DAYS)

    for col in prices.columns:
        clean = prices[col].dropna()
        if len(clean) > 0:
            print(f"    OK  {col} ({COMMODITY_TICKERS.get(col, '?')}) -- "
                  f"{len(clean)} rows, latest: {clean.iloc[-1]:.2f} on {clean.index[-1].date()}")
        else:
            print(f"    FAIL {col} -- no data")

    return prices


# -- step 2: all yields --------------------------------------------------------
#
# US  -> FRED (daily, same as before)
# DE  -> ECB data-api yield curve (daily, replaces monthly FRED series)
# JP  -> MOF Japan JGB CSV (daily, replaces monthly FRED series)

def _fetch_us_yields():
    """Fetch US 2Y and 10Y from FRED (daily)."""
    frames = {}
    for name, series_id in FRED_SERIES.items():
        try:
            data = fred.get_series(
                series_id,
                observation_start=START_DATE,
                observation_end=TODAY
            )
            data = data.dropna()
            frames[name] = data
            print(f"    OK  {name} (FRED {series_id}) -- {len(data)} rows, "
                  f"latest: {data.iloc[-1]:.2f}% on {data.index[-1].date()}")
        except Exception as e:
            print(f"    FAIL {name} (FRED {series_id}) -- {e}")
    return frames


def _fetch_ecb_yields():
    """Fetch DE 2Y and 10Y from ECB yield curve API (daily)."""
    headers = {"Accept": "application/json"}
    frames = {}

    for name, key in ECB_SERIES.items():
        url = f"{ECB_BASE_URL}/{key}"
        params = {"startPeriod": START_DATE, "detail": "dataonly"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=60)
            r.raise_for_status()

            data = r.json()
            series = data["dataSets"][0]["series"]
            dates_dim = data["structure"]["dimensions"]["observation"][0]["values"]

            # extract observations from first (only) series
            for _, val in series.items():
                obs = val["observations"]
                records = []
                for idx_str, values in obs.items():
                    idx = int(idx_str)
                    date_str = dates_dim[idx]["id"]
                    records.append((pd.Timestamp(date_str), values[0]))

                s = pd.Series(
                    [r[1] for r in records],
                    index=pd.DatetimeIndex([r[0] for r in records]),
                    name=name
                ).sort_index()
                s = s.dropna()
                frames[name] = s
                print(f"    OK  {name} (ECB daily) -- {len(s)} rows, "
                      f"latest: {s.iloc[-1]:.2f}% on {s.index[-1].date()}")
                break  # only one series per key

        except Exception as e:
            print(f"    FAIL {name} (ECB) -- {e}")

    return frames


def _fetch_mof_yields():
    """Fetch JP 2Y and 10Y from MOF Japan JGB CSV (daily).

    Downloads historical file (1974 to end of previous month) and
    current month file, then concatenates and deduplicates.
    """
    frames = {}

    try:
        # historical file (up to end of previous month)
        r_hist = requests.get(MOF_HISTORICAL_URL, timeout=60)
        r_hist.raise_for_status()
        text_hist = r_hist.content.decode("shift-jis", errors="replace")

        # current month file
        r_cur = requests.get(MOF_CURRENT_URL, timeout=60)
        r_cur.raise_for_status()
        text_cur = r_cur.content.decode("shift-jis", errors="replace")

        # parse both CSVs (first row is title, second row is header)
        df_hist = pd.read_csv(StringIO(text_hist), skiprows=1)
        df_cur = pd.read_csv(StringIO(text_cur), skiprows=1)

        # combine, keeping current month data if overlapping
        df = pd.concat([df_hist, df_cur], ignore_index=True)

        # drop rows where Date is not a valid date (footer text, blank rows)
        df = df[df["Date"].astype(str).str.match(r"^\d{4}/\d{1,2}/\d{1,2}$", na=False)]

        df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df.drop_duplicates(subset=["Date"], keep="last")
        df = df.sort_values("Date").set_index("Date")
        df.index.name = "date"

        # filter to start date
        df = df[df.index >= START_DATE]

        # extract 2Y and 10Y
        for col_name, mof_col in [("JP_2Y", "2Y"), ("JP_10Y", "10Y")]:
            if mof_col in df.columns:
                s = pd.to_numeric(df[mof_col], errors="coerce").dropna()
                s.name = col_name
                frames[col_name] = s
                print(f"    OK  {col_name} (MOF daily) -- {len(s)} rows, "
                      f"latest: {s.iloc[-1]:.2f}% on {s.index[-1].date()}")
            else:
                print(f"    FAIL {col_name} -- column '{mof_col}' not found in MOF data")

    except Exception as e:
        print(f"    FAIL JP yields (MOF) -- {str(e).encode('ascii', 'replace').decode()}")

    return frames


def _fetch_it_yield() -> dict:
    """Fetch Italian 10Y government bond yield for BTP-Bund spread (Phase 9).

    Primary  : ECB SDW YC dataset (daily, country-specific series) — currently
               returning 404 as the series has been discontinued.
    Fallback : FRED IRLTLT01ITM156N (monthly OECD source, Italy 10Y).
               Reindexed to the business-day calendar with forward-fill so the
               series is non-NaN through the current date even when FRED lags
               1–2 months behind real-time.  No interpolation — the last known
               monthly value is carried forward cleanly.
    Returns  : dict with key 'IT_10Y' or empty dict on failure.
    """
    # Primary: ECB SDW (kept for future when series is reinstated)
    try:
        it_key = "YC/B.IT.EUR.4F.G_N_A.SV_C_YM.SR_10Y"
        headers = {"Accept": "application/json"}
        r = requests.get(
            f"{ECB_BASE_URL}/{it_key}",
            headers=headers,
            params={"startPeriod": START_DATE, "detail": "dataonly"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        datasets = data.get("dataSets", [])
        if datasets:
            series_dict = datasets[0].get("series", {})
            dates_dim = data["structure"]["dimensions"]["observation"][0]["values"]
            for _, val in series_dict.items():
                obs = val.get("observations", {})
                records = [
                    (pd.Timestamp(dates_dim[int(k)]["id"]), v[0])
                    for k, v in obs.items()
                ]
                s = pd.Series(
                    [r[1] for r in records],
                    index=pd.DatetimeIndex([r[0] for r in records]),
                    name="IT_10Y",
                ).sort_index().dropna()
                if len(s) > 100:
                    print(f"    OK  IT_10Y (ECB daily) -- {len(s)} rows, "
                          f"latest: {s.iloc[-1]:.2f}% on {s.index[-1].date()}")
                    return {"IT_10Y": s}
                break  # only one series expected
    except Exception as e:
        print(f"    WARN IT_10Y ECB failed ({type(e).__name__}): {e}")

    # Fallback: FRED IRLTLT01ITM156N — monthly OECD Italy 10Y.
    # Reindex to a full business-day calendar and forward-fill (no interpolation).
    # The ffill in calculate_spreads() adds a safety ceil of 90 days, so even if
    # FRED lags ~60 days the spread remains live and correctly classified.
    try:
        raw = fred.get_series("IRLTLT01ITM156N", observation_start=START_DATE).dropna()
        bday_range = pd.bdate_range(start=START_DATE, end=pd.Timestamp.today())
        daily = raw.reindex(bday_range).ffill()
        daily.name = "IT_10Y"
        last_valid = daily.last_valid_index()
        print(
            f"    OK  IT_10Y (FRED monthly->bday ffill) -- "
            f"{daily.notna().sum()} rows, "
            f"latest non-NaN: {daily[last_valid]:.2f}% on {last_valid.date()}"
        )
        return {"IT_10Y": daily}
    except Exception as e2:
        print(f"    WARN IT_10Y FRED fallback failed ({type(e2).__name__}): {e2}")

    print("    WARN IT_10Y: all sources failed, BTP-Bund spread will be NaN")
    return {}


def fetch_all_yields():
    print("\n[2/5] fetching all yields (FRED + ECB + MOF + IT — parallel)...")

    with ThreadPoolExecutor(max_workers=4) as pool:
        fut_us  = pool.submit(_fetch_us_yields)
        fut_ecb = pool.submit(_fetch_ecb_yields)
        fut_mof = pool.submit(_fetch_mof_yields)
        fut_it  = pool.submit(_fetch_it_yield)
        all_frames = {}
        all_frames.update(fut_us.result())
        all_frames.update(fut_ecb.result())
        all_frames.update(fut_mof.result())
        all_frames.update(fut_it.result())

    yields_df = pd.DataFrame(all_frames)
    yields_df.index = pd.to_datetime(yields_df.index)
    yields_df.index.name = "date"

    # ensure all expected series exist (fill absent ones with NaN so
    # downstream code doesn’t blow up with KeyError)
    for col in ["US_2Y", "US_10Y", "DE_2Y", "DE_10Y", "JP_2Y", "JP_10Y"]:
        if col not in yields_df.columns:
            yields_df[col] = np.nan
            print(f"    WARNING -- missing series {col}, filling with NaNs")

    # US yields: fill weekends and holidays (max MAX_FFILL_DAYS trading days)
    for col in ["US_2Y", "US_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=MAX_FFILL_DAYS)

    # DE yields (ECB): fill weekends and holidays (max MAX_FFILL_DAYS trading days)
    for col in ["DE_2Y", "DE_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=MAX_FFILL_DAYS)

    # JP yields (MOF): fill weekends and holidays (max MAX_FFILL_DAYS trading days)
    for col in ["JP_2Y", "JP_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=MAX_FFILL_DAYS)

    return yields_df


# -- step 3: rate differentials ------------------------------------------------
#
# US 2Y is used because it reflects Fed policy expectations most directly
# it moves faster than 10Y when the market reprices the rate path
# spread = US yield advantage over foreign yield
# narrowing spread = less incentive to hold USD = foreign currency should rise

def calculate_differentials(yields_df):
    print("\n[3/5] calculating rate differentials...")

    diff = pd.DataFrame(index=yields_df.index)

    # helper that returns series or NaNs if either input is missing
    def _spread(a, b):
        if a not in yields_df.columns or b not in yields_df.columns:
            missing = [x for x in (a, b) if x not in yields_df.columns]
            print(f"    WARNING -- cannot compute spread {a}-{b}, missing {missing}")
            return pd.Series(index=yields_df.index, dtype=float)
        return yields_df[a] - yields_df[b]

    # US 10Y minus Germany 10Y -- same-maturity 10Y driver of EUR/USD
    diff["US_DE_10Y_spread"] = _spread("US_10Y", "DE_10Y")

    # US 2Y minus Germany 2Y -- same-maturity driver of EUR/USD
    diff["US_DE_2Y_spread"] = _spread("US_2Y", "DE_2Y")

    # US 10Y minus Japan 10Y -- same-maturity 10Y driver of USD/JPY
    diff["US_JP_10Y_spread"] = _spread("US_10Y", "JP_10Y")
    # 5-day momentum of the US-JP spread (BoJ signal: rate of change over a week)
    diff["US_JP_10Y_spread_accel"] = diff["US_JP_10Y_spread"].diff(5)

    # US 2Y minus Japan 2Y -- same-maturity driver of USD/JPY
    diff["US_JP_2Y_spread"] = _spread("US_2Y", "JP_2Y")

    # US yield curve: 10Y minus 2Y
    # positive = normal (longer duration pays more)
    # negative = inverted (recession signal historically)
    diff["US_curve"] = _spread("US_10Y", "US_2Y")

    # BTP-Bund spread: Italian 10Y minus German 10Y (Phase 9 — eurozone fragmentation signal)
    if "IT_10Y" in yields_df.columns and "DE_10Y" in yields_df.columns:
        # ffill up to 90 days: IT_10Y source is monthly (FRED/OECD) and lags 1-2 months;
        # forward-filling the last known value keeps the spread non-NaN while remaining
        # economically valid (Italian yields change slowly over short horizons).
        yields_df["IT_10Y"] = yields_df["IT_10Y"].ffill(limit=90)
        diff["BTP_Bund_spread"] = yields_df["IT_10Y"] - yields_df["DE_10Y"]

        def _btp_flag(x):
            if pd.isna(x):  return "UNAVAILABLE"
            if x > 2.5:     return "STRESS"
            if x > 1.8:     return "ELEVATED"
            return "NORMAL"

        diff["BTP_Bund_flag"] = diff["BTP_Bund_spread"].apply(_btp_flag)

    for col in diff.columns:
        clean = diff[col].dropna()
        if len(clean) == 0:
            print(f"    {col:<22} : no data")
            continue
        v = clean.iloc[-1]
        # skip non-numeric flag columns
        try:
            v_float = float(v)
        except (TypeError, ValueError):
            print(f"    {col:<22} : {v}")
            continue
        flag = diff.get("BTP_Bund_flag", pd.Series()).dropna()
        suffix = f"  [{flag.iloc[-1]}]" if col == "BTP_Bund_spread" and len(flag) > 0 else ""
        print(f"    {col:<22} : {v_float:+.2f}%{suffix}")

    return diff


# -- step 3.5: volatility ------------------------------------------------------

def calculate_volatility(master):
    print("\n[VOL] calculating realized volatility...")

    # Note: USDINR is not present at this stage — it is added later by
    # inr_pipeline.py which computes USDINR_vol30/USDINR_vol_pct on the
    # original (non-reindexed) price series before merging into master.
    for pair in ["EURUSD", "USDJPY"]:
        if pair not in master.columns:
            continue
        log_ret = np.log(master[pair] / master[pair].shift(1))
        master[f"{pair}_vol30"] = (
            log_ret.rolling(window=VOL_WINDOW).std() * np.sqrt(252) * 100
        )

    window_3y = ROLLING_WINDOW * 3
    for pair in ["EURUSD", "USDJPY"]:
        col = f"{pair}_vol30"
        if col not in master.columns:
            continue
        master[f"{pair}_vol_pct"] = (
            master[col]
            .rolling(window=window_3y, min_periods=126)
            .rank(pct=True) * 100
        )

    for pair in ["EURUSD", "USDJPY"]:
        col     = f"{pair}_vol30"
        pct_col = f"{pair}_vol_pct"
        if col not in master.columns:
            continue
        _vol_s  = master[col].dropna()
        _vopp_s = master[pct_col].dropna()
        if _vol_s.empty or _vopp_s.empty:
            continue
        v = _vol_s.iloc[-1]
        p = _vopp_s.iloc[-1]
        flag = "EXTREME" if p >= 90 else ("ELEVATED" if p >= 75 else "NORMAL")
        print(f"    {pair}: {v:.1f}% annualized | {p:.0f}th pct | {flag}")

    return master


# -- step 3.6: regime correlation ----------------------------------------------

def calculate_regime_correlation(master):
    print("\n[CORR] calculating regime correlation...")

    master = master.copy()

    # EUR/USD: correlation between US_DE_10Y_spread daily change and EURUSD daily % change
    if "US_DE_10Y_spread" in master.columns and "EURUSD" in master.columns:
        # daily change in spread (pp)
        spread_chg = master["US_DE_10Y_spread"].diff()
        # daily % change in FX price
        fx_ret = master["EURUSD"].pct_change() * 100
        
        # 60-day rolling Pearson correlation
        corr_series = spread_chg.rolling(window=CORR_WINDOW).corr(fx_ret)
        master["EURUSD_spread_corr_60d"] = corr_series
        
        # 3-year percentile
        window_3y = ROLLING_WINDOW * 3
        master["EURUSD_corr_percentile"] = (
            corr_series
            .rolling(window=window_3y, min_periods=126)
            .rank(pct=True) * 100
        )

        # 20-day rolling correlation (Phase 3 dual-window)
        master["EURUSD_corr_20d"] = spread_chg.rolling(window=20).corr(fx_ret)

    # USD/JPY: correlation between US_JP_10Y_spread daily change and USDJPY daily % change
    if "US_JP_10Y_spread" in master.columns and "USDJPY" in master.columns:
        # daily change in spread (pp)
        spread_chg = master["US_JP_10Y_spread"].diff()
        # daily % change in FX price
        fx_ret = master["USDJPY"].pct_change() * 100
        
        # 60-day rolling Pearson correlation
        corr_series = spread_chg.rolling(window=CORR_WINDOW).corr(fx_ret)
        master["USDJPY_spread_corr_60d"] = corr_series
        
        # 3-year percentile
        window_3y = ROLLING_WINDOW * 3
        master["USDJPY_corr_percentile"] = (
            corr_series
            .rolling(window=window_3y, min_periods=126)
            .rank(pct=True) * 100
        )

        # 20-day rolling correlation (Phase 3 dual-window)
        master["USDJPY_corr_20d"] = spread_chg.rolling(window=20).corr(fx_ret)

    # print summary
    for pair, col60, col20 in [
        ("EURUSD", "EURUSD_spread_corr_60d", "EURUSD_corr_20d"),
        ("USDJPY", "USDJPY_spread_corr_60d", "USDJPY_corr_20d"),
    ]:
        if col60 not in master.columns:
            continue
        _s60 = master[col60].dropna()
        if len(_s60) == 0:
            print(f"    {pair}: no correlation data (yield series unavailable)")
            continue
        c60 = _s60.iloc[-1]
        label_20 = ''
        if col20 in master.columns and len(master[col20].dropna()) > 0:
            c20 = master[col20].dropna().iloc[-1]
            div_flag = '  REGIME TRANSITION' if abs(c60 - c20) > 0.3 else ''
            label_20 = f'  /  20D:{c20:>+.3f}{div_flag}'
        print(f"    {pair}: 60D:{c60:>+.3f}{label_20}")

    return master


# -- step 3.7: oil correlation layer (Phase 1) ---------------------------------
#
# 60D rolling correlation between Brent daily returns and each FX pair's
# daily returns.  Signals whether oil price moves are transmitting into FX.
#
# Expected sign logic:
#   EUR/USD:  negative  (oil up → wider eurozone trade deficit → EUR weaker)
#   USD/JPY:  positive  (oil up → wider Japan trade deficit   → JPY weaker)
#   USD/INR:  positive  (oil up → India import costs rise     → INR weaker)
#
# Sign reversal beyond threshold = divergence flag (pair-specific factor
# overriding the commodity channel — analytically informative).

def calculate_dxy_correlation(master):
    print("\n[DXY] calculating DXY decomposition (Phase 2)...")

    if "DXY" not in master.columns:
        print("    SKIP -- DXY column not found")
        return master

    dxy_ret = master["DXY"].pct_change()

    pairs = [
        ("EURUSD", "dxy_eurusd_corr_60d"),
        ("USDJPY", "dxy_usdjpy_corr_60d"),
        # USDINR handled by inr_pipeline.py (USDINR prices not available at this stage)
    ]

    for fx_col, out_col in pairs:
        if fx_col not in master.columns:
            print(f"    SKIP -- {fx_col} not in master")
            continue
        fx_ret = master[fx_col].pct_change()
        master[out_col] = dxy_ret.rolling(CORR_WINDOW).corr(fx_ret)

        latest = master[out_col].dropna()
        if len(latest) > 0:
            c = latest.iloc[-1]
            print(f"    {fx_col:<8}: {c:>+.3f}  ({out_col})")
        else:
            print(f"    {fx_col:<8}: no data")

    return master

def calculate_gold_correlation(master):
    print("\n[GOLD] calculating gold correlation (Phase 4)...")

    if "Gold" not in master.columns:
        print("    SKIP -- Gold column not found")
        return master

    gold_ret = master["Gold"].pct_change()

    pairs = [
        ("USDJPY", "gold_usdjpy_corr_60d"),
        # EURUSD excluded: EUR/gold relationship structurally unstable
        # USDINR handled by inr_pipeline.py
    ]

    for fx_col, out_col in pairs:
        if fx_col not in master.columns:
            print(f"    SKIP -- {fx_col} not in master")
            continue
        fx_ret = master[fx_col].pct_change()
        master[out_col] = gold_ret.rolling(CORR_WINDOW).corr(fx_ret)

        latest = master[out_col].dropna()
        if len(latest) > 0:
            c = latest.iloc[-1]
            print(f"    {fx_col:<8}: {c:>+.3f}  ({out_col})")
        else:
            print(f"    {fx_col:<8}: no data")

    return master

def calculate_oil_correlation(master):
    print("\n[OIL] calculating oil correlation (Phase 1)...")

    if "Brent" not in master.columns:
        print("    SKIP -- Brent column not found (run pipeline with commodity fetch)")
        return master

    brent_ret = master["Brent"].pct_change()

    pairs = [
        ("EURUSD", "oil_eurusd_corr_60d"),
        ("USDJPY", "oil_usdjpy_corr_60d"),
        # USDINR handled by inr_pipeline.py (USDINR prices not available at this stage)
    ]

    for fx_col, out_col in pairs:
        if fx_col not in master.columns:
            print(f"    SKIP -- {fx_col} not in master")
            continue
        fx_ret = master[fx_col].pct_change()
        master[out_col] = brent_ret.rolling(CORR_WINDOW).corr(fx_ret)

        latest = master[out_col].dropna()
        if len(latest) > 0:
            c = latest.iloc[-1]
            print(f"    {fx_col:<8}: {c:>+.3f}  ({out_col})")
        else:
            print(f"    {fx_col:<8}: no data")

    return master


# -- step 3.7: key support/resistance levels ------------------------------------

def calculate_key_levels(master):
    """Calculate rolling support/resistance key levels (Phase 11 foundation).

    Uses rolling high/low windows on daily close prices as S/R proxies:
      S3 / R3 = 90-day rolling low / high  (strong structural level)
      S2 / R2 = 63-day rolling low / high  (medium-term quarterly level)
      S1 / R1 = 20-day rolling low / high  (short-term monthly level)

    Output columns: {pair}_S1 ... {pair}_R3  (for EURUSD and USDJPY)
    """
    print("\n[LEVELS] calculating rolling key support/resistance levels...")
    for pair in ["EURUSD", "USDJPY"]:
        if pair not in master.columns:
            continue
        px       = master[pair]
        decimals = 4 if pair == "EURUSD" else 2
        master[f"{pair}_S1"] = px.rolling(20, min_periods=10).min().round(decimals)
        master[f"{pair}_S2"] = px.rolling(63, min_periods=30).min().round(decimals)
        master[f"{pair}_S3"] = px.rolling(90, min_periods=45).min().round(decimals)
        master[f"{pair}_R1"] = px.rolling(20, min_periods=10).max().round(decimals)
        master[f"{pair}_R2"] = px.rolling(63, min_periods=30).max().round(decimals)
        master[f"{pair}_R3"] = px.rolling(90, min_periods=45).max().round(decimals)
        latest = master[[f"{pair}_S1", f"{pair}_R1"]].dropna()
        if len(latest) > 0:
            row = latest.iloc[-1]
            print(f"    {pair}: S1={row[f'{pair}_S1']:.{decimals}f}  "
                  f"R1={row[f'{pair}_R1']:.{decimals}f}")
    return master


# -- Phase 8: G10 composite regime scores --------------------------------------
#
# EUR/USD weights: rate_diff 30%, lev_money 20%, asset_mgr 10%,
#                  vol 10%, corr_60d 15%, oil 8%, dxy 7%
# USD/JPY weights: rate_diff 25%, lev_money 20%, asset_mgr 10%,
#                  vol 10%, corr_60d 15%, oil 10%, gold 5%, dxy 5%
#
# Score > 0  = net USD strength pressure
# Score < 0  = net USD weakness / foreign-currency strength pressure
# Clipped to [-100, 100].

def _norm_percentile(series):
    """Map a 0-100 percentile → [-1, +1].  50th pct = 0 (neutral)."""
    return (series.clip(0, 100) - 50) / 50.0


def _norm_corr(series, expected_sign=1.0):
    """Map a correlation to a signed contribution:
    positive contribution when correlation is in expected direction.
    Result bounded to [-1, +1].
    """
    return (series.clip(-1, 1) * expected_sign)


def calculate_g10_composites(master):
    """Phase 8: compute eurusd_composite_score and usdjpy_composite_score.

    All sub-signals are normalised to [-1, +1] before weighting.
    A positive sub-signal means USD is likely to strengthen against that pair.
    Final score is clipped to [-100, 100].
    """
    print("\n[COMPOSITE] calculating G10 composite regime scores (Phase 8)...")
    df = master.copy()

    # Recompute BTP_Bund_flag from the ffill'd spread (build_master ffills values
    # but the flag strings were written before ffill, so they may show UNAVAILABLE).
    if "BTP_Bund_spread" in df.columns:
        def _btp_flag_post(x):
            if pd.isna(x):  return "UNAVAILABLE"
            if x > 2.5:     return "STRESS"
            if x > 1.8:     return "ELEVATED"
            return "NORMAL"
        df["BTP_Bund_flag"] = df["BTP_Bund_spread"].apply(_btp_flag_post)

    # ── EUR/USD ───────────────────────────────────────────────────────────────
    # Rate differential: higher US-DE spread → USD strength (positive score)
    if "US_DE_10Y_spread" in df.columns:
        # Normalise by rolling z-score (252D window); cap at ±3 → /3 → ±1
        spread_z = (
            df["US_DE_10Y_spread"]
            .sub(df["US_DE_10Y_spread"].rolling(252, min_periods=60).mean())
            .div(df["US_DE_10Y_spread"].rolling(252, min_periods=60).std().replace(0, float('nan')))
            .clip(-3, 3) / 3.0
        )
    else:
        spread_z = pd.Series(0.0, index=df.index)

    # Leveraged Money EUR percentile: high percentile = crowded EUR long →
    #   typically precedes EUR weakness (USD strength) so +ve → +ve signal
    if "EUR_lev_percentile" in df.columns:
        lev_sig = _norm_percentile(df["EUR_lev_percentile"])
    else:
        lev_sig = pd.Series(0.0, index=df.index)

    # Asset Manager EUR percentile: same direction
    if "EUR_assetmgr_percentile" in df.columns:
        am_sig = _norm_percentile(df["EUR_assetmgr_percentile"])
    else:
        am_sig = pd.Series(0.0, index=df.index)

    # Vol percentile: high vol → USD strength pressure (risk-off)
    if "EURUSD_vol_pct" in df.columns:
        vol_sig = _norm_percentile(df["EURUSD_vol_pct"])
    else:
        vol_sig = pd.Series(0.0, index=df.index)

    # Regime correlation: high positive 60D corr (spread drives pair) with
    #   spread being positive (USD direction) → enhances USD signal.
    #   corr_60d + spread_z combined:
    if "EURUSD_spread_corr_60d" in df.columns:
        corr_sig = _norm_corr(df["EURUSD_spread_corr_60d"], expected_sign=1.0) * spread_z.abs()
    else:
        corr_sig = pd.Series(0.0, index=df.index)

    # Oil: EUR/USD typically inversely correlated with oil → oil_eur_corr
    #   negative expected; when corr is negative and oil rising it hurts EUR
    if "oil_eurusd_corr_60d" in df.columns:
        oil_sig = _norm_corr(df["oil_eurusd_corr_60d"], expected_sign=-1.0)
    else:
        oil_sig = pd.Series(0.0, index=df.index)

    # DXY: strong negative corr with EUR/USD → dollar driving
    if "dxy_eurusd_corr_60d" in df.columns:
        dxy_sig = _norm_corr(df["dxy_eurusd_corr_60d"], expected_sign=-1.0)
    else:
        dxy_sig = pd.Series(0.0, index=df.index)

    eur_raw = (
        0.30 * spread_z
        + 0.20 * lev_sig
        + 0.10 * am_sig
        + 0.10 * vol_sig
        + 0.15 * corr_sig
        + 0.08 * oil_sig
        + 0.07 * dxy_sig
    )
    df["eurusd_composite_score"] = (eur_raw * 100).clip(-100, 100).round(1)

    def _g10_label(x):
        if pd.isna(x):    return "UNKNOWN"
        if x >  60:       return "STRONG USD STRENGTH"
        if x >  30:       return "MODERATE USD STRENGTH"
        if x > -30:       return "NEUTRAL"
        if x > -60:       return "MODERATE USD WEAKNESS"
        return "STRONG USD WEAKNESS"

    df["eurusd_composite_label"] = df["eurusd_composite_score"].apply(_g10_label)

    # ── USD/JPY ───────────────────────────────────────────────────────────────
    if "US_JP_10Y_spread" in df.columns:
        jpy_spread_z = (
            df["US_JP_10Y_spread"]
            .sub(df["US_JP_10Y_spread"].rolling(252, min_periods=60).mean())
            .div(df["US_JP_10Y_spread"].rolling(252, min_periods=60).std().replace(0, float('nan')))
            .clip(-3, 3) / 3.0
        )
    else:
        jpy_spread_z = pd.Series(0.0, index=df.index)

    if "JPY_lev_percentile" in df.columns:
        jpy_lev_sig = _norm_percentile(df["JPY_lev_percentile"])
    else:
        jpy_lev_sig = pd.Series(0.0, index=df.index)

    if "JPY_assetmgr_percentile" in df.columns:
        jpy_am_sig = _norm_percentile(df["JPY_assetmgr_percentile"])
    else:
        jpy_am_sig = pd.Series(0.0, index=df.index)

    if "USDJPY_vol_pct" in df.columns:
        jpy_vol_sig = _norm_percentile(df["USDJPY_vol_pct"])
    else:
        jpy_vol_sig = pd.Series(0.0, index=df.index)

    if "USDJPY_spread_corr_60d" in df.columns:
        jpy_corr_sig = _norm_corr(df["USDJPY_spread_corr_60d"], expected_sign=1.0) * jpy_spread_z.abs()
    else:
        jpy_corr_sig = pd.Series(0.0, index=df.index)

    # Oil: positive expected for USD/JPY (oil up → JPY weaker)
    if "oil_usdjpy_corr_60d" in df.columns:
        jpy_oil_sig = _norm_corr(df["oil_usdjpy_corr_60d"], expected_sign=1.0)
    else:
        jpy_oil_sig = pd.Series(0.0, index=df.index)

    # Gold: negative expected for USD/JPY (gold up → safe-haven JPY → lower USD/JPY)
    if "gold_usdjpy_corr_60d" in df.columns:
        gold_sig = _norm_corr(df["gold_usdjpy_corr_60d"], expected_sign=-1.0)
    else:
        gold_sig = pd.Series(0.0, index=df.index)

    # DXY: positive expected for USD/JPY
    if "dxy_usdjpy_corr_60d" in df.columns:
        jpy_dxy_sig = _norm_corr(df["dxy_usdjpy_corr_60d"], expected_sign=1.0)
    else:
        jpy_dxy_sig = pd.Series(0.0, index=df.index)

    jpy_raw = (
        0.25 * jpy_spread_z
        + 0.20 * jpy_lev_sig
        + 0.10 * jpy_am_sig
        + 0.10 * jpy_vol_sig
        + 0.15 * jpy_corr_sig
        + 0.10 * jpy_oil_sig
        + 0.05 * gold_sig
        + 0.05 * jpy_dxy_sig
    )
    df["usdjpy_composite_score"] = (jpy_raw * 100).clip(-100, 100).round(1)
    df["usdjpy_composite_label"] = df["usdjpy_composite_score"].apply(_g10_label)

    # Print latest composite readings
    latest = df.dropna(subset=["eurusd_composite_score", "usdjpy_composite_score"])
    if len(latest) > 0:
        row = latest.iloc[-1]
        print(f"    EUR/USD composite: {row['eurusd_composite_score']:+.1f}  [{row['eurusd_composite_label']}]")
        print(f"    USD/JPY composite: {row['usdjpy_composite_score']:+.1f}  [{row['usdjpy_composite_label']}]")

    return df


# -- step 4: build master table ------------------------------------------------

def build_master(fx_df, yields_df, diff_df, commodity_df=None):
    print("\n[4/5] building master dataset...")

    # FX is the base -- its dates define our trading calendar
    master = fx_df.copy()
    master = master.join(yields_df, how="left")
    master = master.join(diff_df,   how="left")

    # commodity prices: join and forward-fill gaps (exchange holidays)
    if commodity_df is not None and not commodity_df.empty:
        master = master.join(commodity_df, how="left")
        for col in commodity_df.columns:
            if col in master.columns:
                master[col] = master[col].ffill(limit=5)

    # fill gaps in yield/spread columns after join (max 5 days -- all daily now)
    non_fx_cols = list(yields_df.columns) + list(diff_df.columns)
    master[non_fx_cols] = master[non_fx_cols].ffill(limit=5)

    # drop rows where core FX data is missing
    master = master[master["EURUSD"].notna()]

    # ensure no weekend rows sneak in (e.g. from filled yields)
    master = master[master.index.dayofweek < 5]

    missing = master.isnull().sum()
    if missing.sum() > 0:
        print("    WARNING -- missing values:")
        print(missing[missing > 0])
    else:
        print("    clean -- no missing values")

    print(f"    shape: {master.shape[0]} rows x {master.shape[1]} columns")
    return master


# -- step 5: percentage and pp changes -----------------------------------------
#
# FX pairs:       % change  = (today / N trading days ago - 1) * 100
# yields/spreads: pp change = today value minus value N trading days ago
#
# using trading days not calendar days because weekends have no rows
# 1D=1, 1W=5, 1M=21, 3M=63, 12M=252 trading days

def calculate_changes(master):
    print("\n[5/5] calculating changes...")

    periods = PERIODS

    master = master.copy()

    # FX % changes
    for pair in FX_TICKERS.keys():
        if pair not in master.columns:
            continue
        for label, days in periods.items():
            master[f"{pair}_chg_{label}"] = (
                (master[pair] / master[pair].shift(days) - 1) * 100
            )

    # USD/INR changes -- added by inr_pipeline.py, calculated here if present
    if "USDINR" in master.columns:
        for label, days in periods.items():
            master[f"USDINR_chg_{label}"] = (
                (master["USDINR"] / master["USDINR"].shift(days) - 1) * 100
            )
        print("    USDINR change columns added")
    else:
        print("    USDINR not in master -- run inr_pipeline.py first")

    # Commodity % changes (Brent, Gold)
    for commodity in ["Brent", "Gold"]:
        if commodity not in master.columns:
            continue
        for label, days in periods.items():
            master[f"{commodity}_chg_{label}"] = (
                (master[commodity] / master[commodity].shift(days) - 1) * 100
            )
        print(f"    {commodity} change columns added")

    # yield and spread pp changes
    pp_cols = [
        "US_2Y", "US_10Y", "DE_2Y", "DE_10Y", "JP_2Y", "JP_10Y",
        "US_DE_10Y_spread", "US_DE_2Y_spread",
        "US_JP_10Y_spread", "US_JP_2Y_spread",
        "US_curve"
    ]
    for col in pp_cols:
        if col not in master.columns:
            continue
        for label, days in periods.items():
            master[f"{col}_chg_{label}"] = master[col] - master[col].shift(days)

    print(f"    added change columns for {len(periods)} periods")
    return master


# -- save ----------------------------------------------------------------------

def save_data(master):
    os.makedirs("data", exist_ok=True)

    dated = f"data/master_{TODAY.replace('-', '')}.csv"

    # Atomic write: write to .tmp then os.replace so a partial failure
    # never leaves dated file written but latest.csv stale/corrupted.
    for target in [dated, "data/latest.csv"]:
        tmp = target + ".tmp"
        master.to_csv(tmp, encoding='utf-8')
        os.replace(tmp, target)

    print(f"\n    saved: {dated}")
    print(f"    saved: data/latest.csv")


# -- morning summary -----------------------------------------------------------

def print_morning_summary(master):
    print("\n" + "=" * 70)
    print("  MORNING NUMBERS")
    print("=" * 70)

    latest    = master.dropna(subset=["EURUSD", "USDJPY"]).iloc[-1]
    last_date = master.dropna(subset=["EURUSD", "USDJPY"]).index[-1].date()

    print(f"  as of: {last_date}")
    print()

    # Commodities
    if "Brent" in latest.index or "Gold" in latest.index:
        print("  COMMODITIES:")
        print(f"  {'asset':<10} {'price':>8}  {'1D%':>7}  {'1W%':>7}  {'1M%':>7}")
        print(f"  {'-'*48}")
        for com in ["Brent", "Gold"]:
            if com not in latest.index:
                continue
            price = latest[com]
            d1    = latest.get(f"{com}_chg_1D",  float('nan'))
            w1    = latest.get(f"{com}_chg_1W",  float('nan'))
            m1    = latest.get(f"{com}_chg_1M",  float('nan'))
            unit  = "$/bbl" if com == "Brent" else "$/oz"
            print(f"  {com:<10} {price:>8.2f}  {d1:>+6.2f}%  {w1:>+6.2f}%  {m1:>+6.2f}%  ({unit})")
        print()

    # FX prices
    print("  FX PRICES:")
    print(f"  {'pair':<10} {'price':>8}  {'1D%':>7}  {'1W%':>7}  "
          f"{'1M%':>7}  {'3M%':>7}  {'12M%':>7}")
    print(f"  {'-'*66}")

    for pair in ["EURUSD", "USDJPY", "DXY", "USDINR"]:
        if pair not in latest.index:
            continue
        price = latest[pair]
        d1    = latest.get(f"{pair}_chg_1D",  float('nan'))
        w1    = latest.get(f"{pair}_chg_1W",  float('nan'))
        m1    = latest.get(f"{pair}_chg_1M",  float('nan'))
        m3    = latest.get(f"{pair}_chg_3M",  float('nan'))
        m12   = latest.get(f"{pair}_chg_12M", float('nan'))
        print(f"  {pair:<10} {price:>8.4f}  {d1:>+6.2f}%  {w1:>+6.2f}%  "
              f"{m1:>+6.2f}%  {m3:>+6.2f}%  {m12:>+6.2f}%")

    print()

    # yields
    print("  YIELDS:")
    print(f"  {'series':<18} {'today':>8}  {'1D chg':>8}  "
          f"{'1M chg':>8}  {'12M chg':>8}")
    print(f"  {'-'*58}")

    yield_items = [
        ("US_2Y",   "US 2Y"),
        ("US_10Y",  "US 10Y"),
        ("DE_2Y",   "DE 2Y"),
        ("DE_10Y",  "DE 10Y"),
        ("JP_2Y",   "JP 2Y"),
        ("JP_10Y",  "JP 10Y"),
        ("US_curve", "US curve"),
    ]

    for col, label in yield_items:
        if col not in latest.index:
            continue
        val = latest[col]
        d1  = latest.get(f"{col}_chg_1D",  float('nan'))
        m1  = latest.get(f"{col}_chg_1M",  float('nan'))
        m12 = latest.get(f"{col}_chg_12M", float('nan'))
        print(f"  {label:<18} {val:>7.2f}%  {d1:>+7.2f}pp  "
              f"{m1:>+7.2f}pp  {m12:>+7.2f}pp")

    print()

    # spreads
    print("  RATE DIFFERENTIALS:")
    print(f"  {'spread':<22} {'today':>8}  {'1D chg':>8}  "
          f"{'1M chg':>8}  {'12M chg':>8}")
    print(f"  {'-'*62}")

    spread_items = [
        ("US_DE_10Y_spread", "US-DE 10Y"),
        ("US_DE_2Y_spread",  "US-DE 2Y"),
        ("US_JP_10Y_spread", "US-JP 10Y"),
        ("US_JP_2Y_spread",  "US-JP 2Y"),
    ]

    for col, label in spread_items:
        if col not in latest.index:
            continue
        val = latest[col]
        d1  = latest.get(f"{col}_chg_1D",  float('nan'))
        m1  = latest.get(f"{col}_chg_1M",  float('nan'))
        m12 = latest.get(f"{col}_chg_12M", float('nan'))
        print(f"  {label:<22} {val:>7.2f}%  {d1:>+7.2f}pp  "
              f"{m1:>+7.2f}pp  {m12:>+7.2f}pp")

    print()
    print("  pp = percentage points (yields and spreads move in pp)")
    print("   % = percentage change (FX prices)")
    print("=" * 70)


# -- main ----------------------------------------------------------------------

def main():
    print("=" * 70)
    print(f"  G10 FX PIPELINE -- {TODAY}")
    print("=" * 70)

    fx_df        = fetch_fx_data()
    if fx_df.empty:
        print("ERROR: FX price data unavailable — aborting pipeline")
        sys.exit(1)
    commodity_df = fetch_commodity_data()
    yields_df    = fetch_all_yields()
    if yields_df.empty:
        print("ERROR: Yield data unavailable — aborting pipeline")
        sys.exit(1)
    diff_df      = calculate_differentials(yields_df)
    master       = build_master(fx_df, yields_df, diff_df, commodity_df)
    master       = calculate_volatility(master)
    master       = calculate_regime_correlation(master)
    master       = calculate_oil_correlation(master)
    master       = calculate_gold_correlation(master)
    master       = calculate_dxy_correlation(master)
    master       = calculate_key_levels(master)
    master       = calculate_g10_composites(master)
    master       = calculate_changes(master)

    save_data(master)
    print_morning_summary(master)

    print("\n  run cot_pipeline.py next")
    print("  then create_dashboards.py for charts")
    print("=" * 70)


# ── Phase 1 foundation merge ─────────────────────────────────────────────────
#
# merge_main() is the re-entrant merge step invoked by the "merge" pipeline
# stage (via scripts/pipeline_merge.py). It runs AFTER fx/cot/inr/vol/oi/rr
# have written their latest CSV sidecars. Its job is to:
#   1. Re-read data/latest_with_cot.csv (already contains fx+cot+inr output)
#   2. Join data/{vol,oi,rr}_latest.csv (Layer 3 signals) as pair-indexed cols
#   3. Compute realized_vol_5d, VIX column, rate_diff_zscore (5d / 60d z-score)
#   4. Apply iv_gate / oi_norm / rr_modifier composite wiring when the columns
#      are present (partial rollout → NaN-safe defaults)
#   5. Compute per-pair primary_driver from normalised signal contributions
#   6. Persist updated master and Supabase upsert the latest rows
#
# Never raises — every external step is wrapped. Failure logs pipeline_errors
# and leaves the master untouched on disk.

_PAIR_COT = {"eur": "EUR", "jpy": "JPY", "inr": None}
_PAIR_ID  = {"eur": "EURUSD", "jpy": "USDJPY", "inr": "USDINR"}
_PAIR_SPREAD_PREFIX = {
    "eur": "US_DE_10Y_spread",
    "jpy": "US_JP_10Y_spread",
    "inr": "US_IN_10Y_spread",
}


def _merge_compute_vol5(m):
    """Annualised 5-day realised vol for every covered pair."""
    for pair in ("EURUSD", "USDJPY", "USDINR"):
        if pair not in m.columns:
            continue
        px = pd.to_numeric(m[pair], errors="coerce")
        lr = np.log(px / px.shift(1))
        m[f"{pair}_vol5"] = lr.rolling(5).std() * np.sqrt(252) * 100
    return m


def _merge_fetch_vix(m):
    """Fetch VIX close series and align to master index. NaN-safe on failure."""
    from core.signal_write import log_pipeline_error
    try:
        from core.utils import _yf_safe_download
        raw = _yf_safe_download(VIX_TICKER, start=START_DATE, end=TODAY, interval="1d", auto_adjust=True)
        if raw is None or raw.empty:
            log_pipeline_error("merge_main", "VIX fetch empty", notes="vix")
            return m
        if isinstance(raw.columns, pd.MultiIndex):
            vix = raw["Close"].iloc[:, 0]
        elif "Close" in raw.columns:
            vix = raw["Close"]
        else:
            vix = raw.iloc[:, 0]
        vix.index = pd.to_datetime(vix.index.date)
        m["VIX"] = vix.reindex(m.index).ffill(limit=MAX_FFILL_DAYS)
    except Exception as e:
        log_pipeline_error("merge_main", f"VIX fetch: {e}", notes="vix")
    return m


def _merge_compute_rate_zscore(m):
    """5-day change z-score over 60-day trailing window for every spread column."""
    prefixes = [
        "US_DE_2Y_spread", "US_DE_10Y_spread",
        "US_JP_2Y_spread", "US_JP_10Y_spread",
        "US_IN_policy_spread", "US_IN_10Y_spread",
    ]
    for prefix in prefixes:
        if prefix not in m.columns:
            continue
        s = pd.to_numeric(m[prefix], errors="coerce")
        chg5 = s.diff(5)
        mu = chg5.rolling(60, min_periods=20).mean()
        sd = chg5.rolling(60, min_periods=20).std().replace(0, np.nan)
        m[f"{prefix}_zscore"] = ((chg5 - mu) / sd).clip(-3, 3)
    return m


def _left_join_sidecar(m, csv_path):
    """Left-join a sidecar CSV (columns: date, pair, *metrics) onto master by date.

    Metrics are written as {pair}_{metric} columns on the master for the
    latest date present in the sidecar. Idempotent across runs.
    """
    if not os.path.exists(csv_path):
        return m
    try:
        side = pd.read_csv(csv_path)
        if side.empty or "date" not in side.columns or "pair" not in side.columns:
            return m
        side["date"] = pd.to_datetime(side["date"]).dt.normalize()
        metric_cols = [c for c in side.columns if c not in ("date", "pair")]
        if not metric_cols:
            return m
        for pair, grp in side.groupby("pair"):
            grp = grp.sort_values("date").set_index("date")
            for metric in metric_cols:
                col = f"{pair}_{metric}"
                aligned = grp[metric].reindex(m.index).astype("float64", errors="ignore")
                if col in m.columns:
                    m[col] = m[col].combine_first(aligned)
                else:
                    m[col] = aligned
    except Exception as e:
        from core.signal_write import log_pipeline_error
        log_pipeline_error("merge_main", f"sidecar {csv_path}: {e}", notes="sidecar_join")
    return m


def _apply_iv_gate(m):
    """CVOL iv_gate multiplier + VOL_EXPANDING override per approved design."""
    for pair in ("EURUSD", "USDJPY"):
        iv_col = f"{pair}_implied_vol_30d"
        if iv_col not in m.columns:
            continue
        iv = pd.to_numeric(m[iv_col], errors="coerce")
        m[f"{pair}_iv_pct"] = iv.rolling(260, min_periods=60).rank(pct=True)
        gate = np.select(
            [m[f"{pair}_iv_pct"] > 0.90,
             m[f"{pair}_iv_pct"] > 0.75,
             m[f"{pair}_iv_pct"] < 0.25],
            [0.2, 0.7, 1.0],
            default=1.0,
        )
        score_col = f"{pair.lower()}_composite_score"
        label_col = f"{pair.lower()}_composite_label"
        if score_col in m.columns:
            m[score_col] = m[score_col] * gate
        if label_col in m.columns:
            mask = m[f"{pair}_iv_pct"] > 0.90
            m.loc[mask, label_col] = "VOL_EXPANDING"
    return m


def _apply_oi_alignment(m):
    """oi_norm (+/-/0) and UNWIND_IN_PROGRESS flag using 3-day consecutive rule."""
    for pair in ("EURUSD", "USDJPY"):
        align_col = f"{pair}_oi_price_alignment"
        delta_col = f"{pair}_oi_delta"
        px_delta_col = f"{pair}_px_delta"
        if align_col not in m.columns or delta_col not in m.columns:
            continue
        if px_delta_col not in m.columns:
            m[px_delta_col] = pd.to_numeric(m.get(pair), errors="coerce").diff()
        alignment = m[align_col]
        px_sign = np.sign(pd.to_numeric(m[px_delta_col], errors="coerce").fillna(0))
        m[f"{pair}_oi_norm"] = np.where(
            alignment == "confirming", px_sign,
            np.where(alignment == "diverging", -px_sign, 0),
        )
        cot_col = "EUR_lev_percentile" if pair == "EURUSD" else "JPY_lev_percentile"
        if cot_col in m.columns:
            crowded = pd.to_numeric(m[cot_col], errors="coerce") > 90
            shrinking = pd.to_numeric(m[delta_col], errors="coerce") < 0
            trio = (crowded & shrinking).astype(int).rolling(3).sum() >= 3
            flag_col = f"{pair}_flags"
            if flag_col not in m.columns:
                m[flag_col] = ""
            m.loc[trio.fillna(False), flag_col] = "UNWIND_IN_PROGRESS"
    return m


def _apply_rr_modifier(m):
    """rr_modifier (1.15/1.0/0.60) + OPTIONS_DIVERGENCE flag for EUR/USD only."""
    rr_col = "EURUSD_risk_reversal_25d"
    score_col = "eurusd_composite_score"
    if rr_col not in m.columns or score_col not in m.columns:
        return m
    rr = pd.to_numeric(m[rr_col], errors="coerce")
    mu = rr.rolling(260, min_periods=60).mean()
    sd = rr.rolling(260, min_periods=60).std().replace(0, np.nan)
    rr_z = ((rr - mu) / sd).clip(-3, 3)
    m["EURUSD_rr_z"] = rr_z
    score = pd.to_numeric(m[score_col], errors="coerce")
    composite_sign = np.sign(score)
    rr_sign = np.sign(rr)
    agree = (composite_sign == rr_sign) & (composite_sign != 0)
    confirm = agree & (rr_z.abs() > 0.5)
    contradict = (~agree) & (rr_z.abs() > 1.5)
    modifier = np.select([confirm, contradict], [1.15, 0.60], default=1.0)
    m["EURUSD_rr_modifier"] = modifier
    m[score_col] = m[score_col] * modifier
    flag_col = "EURUSD_flags"
    if flag_col not in m.columns:
        m[flag_col] = ""
    m.loc[contradict.fillna(False), flag_col] = "OPTIONS_DIVERGENCE"
    return m


def _compute_primary_driver(m):
    """For each pair, pick the signal with highest weighted absolute contribution.

    Contributions per design spec:
      rate  0.30 * |rate_diff_zscore|
      cot   0.25 * |cot_percentile - 50| / 50
      skew  0.15 * |vol_skew / 3|        (0 if column absent)
      rr    0.15 * |rr_z / 2|            (0 if column absent)
      oi    0.15 * |oi_norm|             (0 if column absent)
    Written to column {pair_lower}_primary_driver as "name:weight" text.
    """
    if m.empty:
        return m
    idx = m.index[-1]
    for pair_key in ("eur", "jpy", "inr"):
        fxid = _PAIR_ID[pair_key]
        cot_prefix = _PAIR_COT[pair_key]
        spread_prefix = _PAIR_SPREAD_PREFIX[pair_key]

        def _latest(col):
            if col not in m.columns:
                return 0.0
            v = m.at[idx, col] if idx in m.index else m[col].iloc[-1]
            try:
                if pd.isna(v):
                    return 0.0
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        rate_z = _latest(f"{spread_prefix}_zscore")
        cot_pct = _latest(f"{cot_prefix}_lev_percentile") if cot_prefix else 50.0
        vol_skew = _latest(f"{fxid}_vol_skew")
        rr_z = _latest(f"{fxid}_rr_z")
        oi_norm = _latest(f"{fxid}_oi_norm")

        contribs = {
            "rate":     0.30 * abs(rate_z),
            "cot":      0.25 * abs(cot_pct - 50.0) / 50.0 if cot_prefix else 0.0,
            "vol_skew": 0.15 * min(abs(vol_skew) / 3.0, 1.0),
            "rr":       0.15 * min(abs(rr_z) / 2.0, 1.0),
            "oi":       0.15 * abs(oi_norm),
        }
        if all(v == 0.0 for v in contribs.values()):
            driver = "unknown:0.00"
        else:
            top = max(contribs, key=contribs.get)
            driver = f"{top}:{contribs[top]:.2f}"
        col = f"{pair_key}_primary_driver"
        if col not in m.columns:
            m[col] = None
        m.at[idx, col] = driver
    return m


def merge_main():
    """Idempotent merge step — safe to invoke multiple times.

    Reads LATEST_WITH_COT_CSV (must exist from fx/cot/inr steps), joins
    Layer-3 sidecar CSVs, computes derived columns, applies composite
    modifiers, rewrites the master CSV, and upserts to Supabase signals.
    Degrades gracefully — never raises into run.py.
    """
    print("\n" + "=" * 70)
    print(f"  MERGE STEP -- {TODAY}")
    print("=" * 70)

    if not os.path.exists(LATEST_WITH_COT_CSV):
        print(f"  merge_main: {LATEST_WITH_COT_CSV} missing — skip")
        return

    try:
        m = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
    except Exception as e:
        from core.signal_write import log_pipeline_error
        log_pipeline_error("merge_main", f"read master: {e}", notes="read_master")
        print(f"  merge_main: could not read master — {e}")
        return

    m = _merge_compute_vol5(m)
    m = _merge_fetch_vix(m)
    m = _merge_compute_rate_zscore(m)

    for side in ("vol_latest.csv", "oi_latest.csv", "rr_latest.csv"):
        m = _left_join_sidecar(m, os.path.join(DATA_DIR, side))

    m = _apply_iv_gate(m)
    m = _apply_oi_alignment(m)
    m = _apply_rr_modifier(m)
    m = _compute_primary_driver(m)

    try:
        tmp = LATEST_WITH_COT_CSV + ".tmp"
        m.to_csv(tmp, encoding="utf-8")
        os.replace(tmp, LATEST_WITH_COT_CSV)
        print(f"  merge_main: wrote {LATEST_WITH_COT_CSV} ({m.shape[0]} rows, {m.shape[1]} cols)")
    except Exception as e:
        from core.signal_write import log_pipeline_error
        log_pipeline_error("merge_main", f"write master: {e}", notes="write_master")
        print(f"  merge_main: write failed — {e}")
        return

    try:
        from core.signal_write import sync_signals_from_master_csv
        sync_signals_from_master_csv()
    except Exception as e:
        from core.signal_write import log_pipeline_error
        log_pipeline_error("merge_main", f"signals sync: {e}", notes="signals_sync")
        print(f"  merge_main: signals sync failed — {e}")


if __name__ == "__main__":
    main()
