"""
Phase 2+3 stress test — lp-css-v4 + landing page overhaul
19 CSS/HTML presence checks + idempotency (2 sequential runs, blank-line normalised)
"""
import sys, subprocess, os, hashlib, re as _re
from datetime import datetime

_TODAY = datetime.today().strftime('%Y%m%d')
BRIEF = f'briefs/brief_{_TODAY}.html'

def _run():
    r = subprocess.run([sys.executable, 'create_html_brief.py'], capture_output=True, text=True)
    if r.returncode != 0:
        print('GENERATOR ERROR:', r.stderr[:400])
        sys.exit(1)
    return open(BRIEF, encoding='utf-8').read()

def normalise(html):
    """Match Phase-1 normalisation: strip run timestamp + collapse ALL blank lines."""
    html = _re.sub(r'run: \d\d \w+ \d{4} \d\d:\d\d IST', 'run: TIMESTAMP', html)
    html = _re.sub(r'\n\s*\n', '\n', html)
    return html

# ---------- produce fresh output ----------
print('Run 1 (baseline)...')
content1 = _run()
n1 = normalise(content1)

# ---------- presence checks ----------
checks = [
    # Phase 2 – lp-css-v4
    ('lp-css-v4 guard present',       '/* lp-css-v4 */'         , True),
    ('lp-css-v3 guard gone',          '/* lp-css-v3 */'         , False),
    ('ws-btn navy background',        'background: #0a0e1a'     , True),
    ('ws-btn blue border 4da6ff',     'border: 1px solid #4da6ff', True),
    ('ws-btn blue hover rgba',        'rgba(77,166,255,0.08)'   , True),
    ('ticker border-bottom rgba',     'rgba(255,255,255,0.08)'  , True),
    ('framework-label color #888',    'color: #888'             , True),
    # Phase 3 – landing page HTML
    ('logo-row div present',          'class="lp-logo-row"'     , True),
    ('brand-name span present',       'class="lp-brand-name"'   , True),
    ('morning-brief div present',     'class="lp-morning-brief"', True),
    ('brand-footer div present',      'class="brand-footer"'    , True),
    ('lp-nav-hint completely gone',   'class="lp-nav-hint"'     , False),
    ('EUR pair color #4da6ff',        'style="color:#4da6ff"'   , True),
    ('JPY pair color #ff9944',        'style="color:#ff9944"'   , True),
    ('INR pair color #e74c3c',        'style="color:#e74c3c"'   , True),
    ('cross-asset CSS class',         'lp-ticker-item lp-ticker-item--cross', True),
    ('substack URL in footer',        'fxregimelab.substack.com', True),
    ('lp-logo-mark img tag',          'class="lp-logo-mark"'    , True),
    ('Morning Brief text',            'Morning Brief</div>'     , True),
]

passes = fails = 0
for label, needle, should_exist in checks:
    found = needle in content1
    ok = found if should_exist else not found
    status = 'PASS' if ok else 'FAIL'
    if ok:
        passes += 1
    else:
        fails += 1
    print(f'  {status}  {label}')

print(f'\n{passes}/{passes+fails} presence checks pass')

# ---------- block counts ----------
print('\nInjection block counts (expect 1 each):')
for label, marker in [
    ('lp-css-v4 blocks',  '/* lp-css-v4 */'),
    ('brand-v1 blocks',   '/* brand-v1 */'),
    ('landing pages',     '<!-- LANDING PAGE -->'),
    ('brand-footer divs', 'class="brand-footer"'),
]:
    count = content1.count(marker)
    ok = (count == 1)
    print(f'  {"PASS" if ok else "FAIL"}  {label}: {count}')
    if not ok:
        fails += 1

# ---------- idempotency ----------
print('\nIdempotency (run 2)...')
content2 = _run()
n2 = normalise(content2)

h1 = hashlib.md5(n1.encode()).hexdigest()
h2 = hashlib.md5(n2.encode()).hexdigest()

idempotent = (h1 == h2)
print(f'  MD5 run1: {h1[:16]}')
print(f'  MD5 run2: {h2[:16]}')
idempotency_status = 'PASS' if idempotent else 'FAIL'
print(f'  {idempotency_status}  Structurally identical after normalisation')
if not idempotent:
    fails += 1

print()
if fails == 0:
    print(f'ALL PASS  ({passes} presence + 4 counts + idempotency)')
else:
    print(f'{fails} FAILURE(S)')
    sys.exit(1)
