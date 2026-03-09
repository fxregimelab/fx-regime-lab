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
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv
from io import StringIO

from config import TODAY, START_DATE

load_dotenv()
FRED_KEY = os.getenv("FRED_API_KEY")
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

    raw = yf.download(
        tickers     = list(FX_TICKERS.values()),
        start       = START_DATE,
        end         = TODAY,
        interval    = "1d",
        auto_adjust = True,
        progress    = False
    )

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

    # DXY trades on ICE with different holidays -- fill gaps up to 5 days
    if "DXY" in prices.columns:
        prices["DXY"] = prices["DXY"].ffill(limit=5)

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

    raw = yf.download(
        tickers     = list(COMMODITY_TICKERS.values()),
        start       = START_DATE,
        end         = TODAY,
        interval    = "1d",
        auto_adjust = True,
        progress    = False
    )

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
        prices[col] = prices[col].ffill(limit=5)

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


def fetch_all_yields():
    print("\n[2/5] fetching all yields (FRED + ECB + MOF)...")

    all_frames = {}
    all_frames.update(_fetch_us_yields())
    all_frames.update(_fetch_ecb_yields())
    all_frames.update(_fetch_mof_yields())

    yields_df = pd.DataFrame(all_frames)
    yields_df.index = pd.to_datetime(yields_df.index)
    yields_df.index.name = "date"

    # ensure all expected series exist (fill absent ones with NaN so
    # downstream code doesn’t blow up with KeyError)
    for col in ["US_2Y", "US_10Y", "DE_2Y", "DE_10Y", "JP_2Y", "JP_10Y"]:
        if col not in yields_df.columns:
            yields_df[col] = np.nan
            print(f"    WARNING -- missing series {col}, filling with NaNs")

    # US yields: fill weekends and holidays (max 5 days)
    for col in ["US_2Y", "US_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=5)

    # DE yields (ECB): fill weekends and holidays (max 5 days)
    for col in ["DE_2Y", "DE_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=5)

    # JP yields (MOF): fill weekends and holidays (max 5 days)
    for col in ["JP_2Y", "JP_10Y"]:
        yields_df[col] = yields_df[col].ffill(limit=5)

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

    # US 2Y minus Germany 10Y -- main cross-maturity driver of EUR/USD
    diff["US_DE_10Y_spread"] = _spread("US_2Y", "DE_10Y")

    # US 2Y minus Germany 2Y -- same-maturity driver of EUR/USD
    diff["US_DE_2Y_spread"] = _spread("US_2Y", "DE_2Y")

    # US 2Y minus Japan 10Y -- main cross-maturity driver of USD/JPY
    diff["US_JP_10Y_spread"] = _spread("US_2Y", "JP_10Y")

    # US 2Y minus Japan 2Y -- same-maturity driver of USD/JPY
    diff["US_JP_2Y_spread"] = _spread("US_2Y", "JP_2Y")

    # US yield curve: 10Y minus 2Y
    # positive = normal (longer duration pays more)
    # negative = inverted (recession signal historically)
    diff["US_curve"] = _spread("US_10Y", "US_2Y")

    for col in diff.columns:
        clean = diff[col].dropna()
        if len(clean) > 0:
            print(f"    {col:<22} : {clean.iloc[-1]:+.2f}%")
        else:
            print(f"    {col:<22} : no data")

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
            log_ret.rolling(window=30).std() * np.sqrt(252) * 100
        )

    window_3y = 252 * 3
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
        v = master[col].dropna().iloc[-1]
        p = master[pct_col].dropna().iloc[-1]
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
        corr_series = spread_chg.rolling(window=60).corr(fx_ret)
        master["EURUSD_spread_corr_60d"] = corr_series
        
        # 3-year percentile
        window_3y = 252 * 3
        master["EURUSD_corr_percentile"] = (
            corr_series
            .rolling(window=window_3y, min_periods=126)
            .rank(pct=True) * 100
        )

    # USD/JPY: correlation between US_JP_10Y_spread daily change and USDJPY daily % change
    if "US_JP_10Y_spread" in master.columns and "USDJPY" in master.columns:
        # daily change in spread (pp)
        spread_chg = master["US_JP_10Y_spread"].diff()
        # daily % change in FX price
        fx_ret = master["USDJPY"].pct_change() * 100
        
        # 60-day rolling Pearson correlation
        corr_series = spread_chg.rolling(window=60).corr(fx_ret)
        master["USDJPY_spread_corr_60d"] = corr_series
        
        # 3-year percentile
        window_3y = 252 * 3
        master["USDJPY_corr_percentile"] = (
            corr_series
            .rolling(window=window_3y, min_periods=126)
            .rank(pct=True) * 100
        )

    # print summary
    for pair, col in [("EURUSD", "EURUSD_spread_corr_60d"), ("USDJPY", "USDJPY_spread_corr_60d")]:
        if col not in master.columns:
            continue
        c = master[col].dropna().iloc[-1]
        print(f"    {pair}: {c:>+.3f} correlation")

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
        master[out_col] = dxy_ret.rolling(60).corr(fx_ret)

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
        master[out_col] = brent_ret.rolling(60).corr(fx_ret)

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

    periods = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "12M": 252}

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
        master.to_csv(tmp)
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
    commodity_df = fetch_commodity_data()
    yields_df    = fetch_all_yields()
    diff_df      = calculate_differentials(yields_df)
    master       = build_master(fx_df, yields_df, diff_df, commodity_df)
    master       = calculate_volatility(master)
    master       = calculate_regime_correlation(master)
    master       = calculate_oil_correlation(master)
    master       = calculate_dxy_correlation(master)
    master       = calculate_key_levels(master)
    master       = calculate_changes(master)

    save_data(master)
    print_morning_summary(master)

    print("\n  run cot_pipeline.py next")
    print("  then create_dashboards.py for charts")
    print("=" * 70)


if __name__ == "__main__":
    main()
