"""Quick verification of HTML brief output for all implemented phases."""
import glob
import os
import sys

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)

_briefs = sorted(glob.glob('briefs/brief_*.html'))
if not _briefs:
    print('No briefs/brief_*.html found. Run: python run.py --only html')
    sys.exit(1)
html = open(_briefs[-1], encoding='utf-8').read()

_df = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
_latest = _df.iloc[-1]
_eur20 = _latest.get('EURUSD_corr_20d')
_jpy20 = _latest.get('USDJPY_corr_20d')
_eur20_s = f"{float(_eur20):+.3f}" if _eur20 is not None and pd.notna(_eur20) else None
_jpy20_s = f"{float(_jpy20):+.3f}" if _jpy20 is not None and pd.notna(_jpy20) else None

checks = [
    ('Phase 3: two 20D Corr rows',      html.count('20D Corr') >= 2),
    ('Phase 3: EUR 20D value in brief', _eur20_s is not None and _eur20_s in html),
    ('Phase 3: JPY 20D value in brief', _jpy20_s is not None and _jpy20_s in html),
    ('Phase 4: JPY gold corr row',     'gold_usdjpy_corr_60d'),
    ('Phase 4: INR gold corr row',     'gold_inr_corr_60d'),
    ('Phase 5: CENTRAL BANK section',  'CENTRAL BANK ACTIVITY'),
    ('Phase 5: RBI reserves row',      'RBI Reserves 1W'),
    ('Phase 5: ACTIVE SUPPORT badge',  'ACTIVE SUPPORT'),
    ('Phase 7: INR COMPOSITE section', 'INR COMPOSITE'),
    ('Phase 7: Regime Score row',      'Regime Score'),
    ('Phase 7: score bar 4px',         'height:4px;width:'),
    ('Phase 7: Oil component',         '>Oil<'),
    ('Phase 7: Dollar component',      '>Dollar<'),
    ('Phase 7: FPI component',         '>FPI<'),
    ('Phase 7: RBI component',         '>RBI<'),
    ('Phase 7: Rate diff component',   '>Rate diff<'),
    ('EUR/USD card present',           'card-eurusd'),
    ('USD/JPY card present',           'card-usdjpy'),
    ('USD/INR card present',           'card-usdinr'),
]

print('=== HTML BRIEF CHECK ===')
all_ok = True
for desc, pattern in checks:
    if isinstance(pattern, bool):
        found = pattern
    else:
        found = pattern in html
    status = 'OK  ' if found else 'FAIL'
    if not found:
        all_ok = False
    print(f'  {status}  {desc}')

# verify gold NOT incorrectly appearing in EUR/USD section
eur_start = html.find('card-eurusd')
eur_end   = html.find('card-usdjpy')
eur_section = html[eur_start:eur_end] if eur_start != -1 and eur_end != -1 else ''
gold_in_eur = 'gold_inr_corr' in eur_section or 'gold_usdjpy' in eur_section
status2 = 'FAIL' if gold_in_eur else 'OK  '
if gold_in_eur:
    all_ok = False
print(f'  {status2}  EUR/USD card: no orphan gold columns')

print()
print('All checks passed:', all_ok)
if not all_ok:
    sys.exit(1)
