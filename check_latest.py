# check_latest.py
# Validates data/latest_with_cot.csv for existence, required columns,
# freshness, and NaN density.  Exit 0 = OK, Exit 1 = problem found.

import sys
import os
from datetime import datetime

import pandas as pd

CSV_PATH = 'data/latest_with_cot.csv'

REQUIRED_COLS = [
    'EURUSD', 'USDJPY',
    'US_2Y', 'US_10Y', 'DE_2Y', 'DE_10Y', 'JP_2Y', 'JP_10Y',
    'US_DE_10Y_spread', 'US_JP_10Y_spread',
    'EURUSD_vol30', 'USDJPY_vol30',
]

STALE_DAYS   = 5   # warn if latest row is older than this
NAN_WARN_PCT = 30  # warn if a required column has more than 30 % NaN


def main():
    ok = True
    print(f'check_latest: {CSV_PATH}')

    # 1. existence
    if not os.path.exists(CSV_PATH):
        print(f'  ERROR: file not found — run pipeline.py first')
        sys.exit(1)

    # 2. load
    try:
        df = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
    except Exception as exc:
        print(f'  ERROR: could not load CSV: {exc}')
        sys.exit(1)

    if len(df) == 0:
        print('  ERROR: CSV is empty')
        sys.exit(1)

    # 3. freshness
    try:
        last_date = pd.to_datetime(df.index[-1])
        age = (datetime.today() - last_date).days
        if age > STALE_DAYS:
            print(f'  WARN: latest row is {age}d old ({last_date.date()}) — data may be stale')
            ok = False
        else:
            print(f'  freshness : {last_date.date()} ({age}d ago)  OK')
    except Exception as exc:
        print(f'  WARN: could not parse date index: {exc}')

    # 4. required columns
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        print(f'  ERROR: missing columns: {missing}')
        sys.exit(1)
    print(f'  columns   : {len(REQUIRED_COLS)} required columns present  OK')

    # 5. NaN density
    nan_warn = False
    for col in REQUIRED_COLS:
        pct = df[col].isna().mean() * 100
        if pct > NAN_WARN_PCT:
            print(f'  WARN: {col} has {pct:.0f}% NaN')
            nan_warn = True
            ok = False  # stale/sparse data propagates to exit code
    if not nan_warn:
        print(f'  NaN check : all required columns below {NAN_WARN_PCT}% NaN  OK')

    print(f'check_latest: PASS  ({len(df)} rows, {len(df.columns)} cols)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

