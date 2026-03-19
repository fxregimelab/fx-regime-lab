"""Full verification of all implemented phases — HTML + CSV."""
import glob
import os
import re
import sys

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)

_briefs = sorted(glob.glob('briefs/brief_*.html'))
if not _briefs:
    print('No briefs/brief_*.html found. Run: python run.py --only html')
    sys.exit(1)
html = open(_briefs[-1], encoding='utf-8').read()
df   = pd.read_csv('data/latest_with_cot.csv', index_col=0, parse_dates=True)
latest = df.iloc[-1]

print('=== CSV COLUMN CHECK ===')
phase_cols = {
    'Phase 3': ['EURUSD_corr_20d', 'USDJPY_corr_20d'],
    'Phase 4': ['gold_usdjpy_corr_60d', 'gold_inr_corr_60d',
                'gold_seasonal_flag', 'gold_seasonal_label'],
    'Phase 5': ['rbi_reserves', 'rbi_reserve_chg_1w', 'rbi_intervention_flag'],
    'Phase 7': ['inr_composite_score', 'inr_composite_label'],
}
csv_ok = True
for phase, cols in phase_cols.items():
    for col in cols:
        if col in latest.index:
            print(f'  OK    {phase}  {col:35s} = {latest[col]}')
        else:
            print(f'  FAIL  {phase}  {col:35s} MISSING')
            csv_ok = False

print()
print('=== HTML CHECK ===')
html_checks = [
    # Phase 3 — rendered as "20D Corr" label with value
    ('Phase 3: EUR 20D Corr rendered',    '20D Corr'),
    ('Phase 3: EUR -0.223 value',         '-0.223'),
    ('Phase 3: JPY +0.150 value',         '+0.150'),
    # Phase 4
    ('Phase 4: JPY gold row',             'data-field="gold_usdjpy_corr_60d"'),
    ('Phase 4: INR gold row',             'data-field="gold_inr_corr_60d"'),
    # Phase 5
    ('Phase 5: CENTRAL BANK ACTIVITY',    'CENTRAL BANK ACTIVITY'),
    ('Phase 5: RBI Reserves 1W row',      'RBI Reserves 1W'),
    ('Phase 5: ACTIVE SUPPORT badge',     'ACTIVE SUPPORT'),
    # Phase 7
    ('Phase 7: INR COMPOSITE section',    'INR COMPOSITE'),
    ('Phase 7: Regime Score row',         'Regime Score'),
    ('Phase 7: 4px score bar',            'height:4px;width:'),
    ('Phase 7: Oil sub-row',              '>Oil<'),
    ('Phase 7: Dollar sub-row',           '>Dollar<'),
    ('Phase 7: FPI sub-row',              '>FPI<'),
    ('Phase 7: RBI sub-row',              '>RBI<'),
    ('Phase 7: Rate diff sub-row',        '>Rate diff<'),
    # Cards
    ('card-eurusd present',               'card-eurusd'),
    ('card-usdjpy present',               'card-usdjpy'),
    ('card-usdinr present',               'card-usdinr'),
]

html_ok = True
for desc, pattern in html_checks:
    found = pattern in html
    status = 'OK  ' if found else 'FAIL'
    if not found:
        html_ok = False
    print(f'  {status}  {desc}')

# EUR card should not have RBI/composite sections
# Use id="card-..." to find actual card div boundaries (not CSS rules)
eur_start = html.find('id="card-eurusd"')
jpy_start = html.find('id="card-usdjpy"')
inr_start = html.find('id="card-usdinr"')
eur_section = html[eur_start:jpy_start]
jpy_section = html[jpy_start:inr_start]

rbi_in_eur = 'CENTRAL BANK ACTIVITY' in eur_section
composite_in_eur = 'INR COMPOSITE' in eur_section
status_rbi = 'FAIL' if rbi_in_eur else 'OK  '
status_cmp = 'FAIL' if composite_in_eur else 'OK  '
if rbi_in_eur or composite_in_eur:
    html_ok = False
print(f'  {status_rbi}  EUR/USD card: no RBI section (INR-only correct)')
print(f'  {status_cmp}  EUR/USD card: no composite section (INR-only correct)')

# JPY card should have gold but no RBI/composite
gold_in_jpy = 'gold_usdjpy_corr_60d' in jpy_section
rbi_in_jpy  = 'CENTRAL BANK ACTIVITY' in jpy_section
status_gj = 'OK  ' if gold_in_jpy else 'FAIL'
status_rj = 'OK  ' if not rbi_in_jpy else 'FAIL'
if not gold_in_jpy or rbi_in_jpy:
    html_ok = False
print(f'  {status_gj}  USD/JPY card: gold section present (correct)')
print(f'  {status_rj}  USD/JPY card: no RBI section (INR-only correct)')

print()
print(f'CSV all columns OK : {csv_ok}')
print(f'HTML all checks OK : {html_ok}')
print(f'OVERALL            : {"PASS" if csv_ok and html_ok else "FAIL — see failures above"}')
