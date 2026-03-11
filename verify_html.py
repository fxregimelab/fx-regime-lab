"""Quick verification of HTML brief output for all implemented phases."""
html = open('briefs/brief_20260310.html', encoding='utf-8').read()

checks = [
    ('Phase 3: EUR 20D corr row',      'EURUSD_corr_20d'),
    ('Phase 3: JPY 20D corr row',      'USDJPY_corr_20d'),
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
