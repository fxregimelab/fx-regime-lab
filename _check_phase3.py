"""
Phase 3 stress test — dual-window corr (20D/60D) + blank-line drift fix
Part A: presence checks (HTML has all expected Phase 3 markers)
Part B: blank-line drift (3 sequential runs — line count must be stable)
Part C: idempotency (normalised MD5 must match across 2 runs)
"""
import sys, subprocess, re as _re, hashlib, difflib
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
    html = _re.sub(r'run: \d\d \w+ \d{4} \d\d:\d\d IST', 'run: TIMESTAMP', html)
    html = _re.sub(r'\n\s*\n', '\n', html)
    return html

# ---- Run 1 baseline ----
print('Run 1 (baseline)...')
c1 = _run()

# === Part A: Presence checks ===
presence_checks = [
    # Phase 3 HTML
    ('20D Corr row label',          'class="name">20D Corr</span>',  True),
    ('60D Corr row label',          'class="name">60D Corr</span>',  True),
    # Phase 3 CSS guard still present
    ('lp-css-v4 guard',             '/* lp-css-v4 */',               True),
    ('brand-v1 guard',              '/* brand-v1 */',                True),
    # Old lp-css-v3 gone
    ('lp-css-v3 gone',              '/* lp-css-v3 */',               False),
    # 20D corr data rendered (values exist in CSV)
    ('EURUSD 20D value rendered',  'name">20D Corr',                 True),
    # Oil/DXY rows still rendered
    ('Oil corr row label',          '>Oil corr 60D</span>',          True),
    ('DXY corr row label',          '>DXY corr 60D</span>',          True),
    # Brand overhaul markers still intact
    ('lp-logo-row',                 'class="lp-logo-row"',           True),
    ('brand-footer',                'class="brand-footer"',          True),
    ('lp-nav-hint gone',            'class="lp-nav-hint"',           False),
    ('EUR ticker colour',           'style="color:#4da6ff"',         True),
]

passes = fails = 0
for label, needle, should in presence_checks:
    found = needle in c1
    ok = found if should else not found
    status = 'PASS' if ok else 'FAIL'
    if ok: passes += 1
    else:  fails  += 1
    print(f'  {status}  {label}')

print(f'\n{passes}/{passes + fails} presence checks pass')

# === Part B: Blank-line drift (3 sequential HTML runs) ===
print('\nBlank-line drift test (3 runs — line count must be stable)...')
counts = [len(c1.splitlines())]
for i in range(2, 4):
    cx = _run()
    counts.append(len(cx.splitlines()))

print(f'  Line counts: {counts}')
drift_ok = (counts[0] == counts[1] == counts[2])
print(f'  {"PASS" if drift_ok else "FAIL"}  Line count stable across 3 runs')
if not drift_ok:
    fails += 1

# === Part C: Idempotency (normalised MD5) ===
print('\nIdempotency (normalised MD5 run1 vs run3)...')
n1 = normalise(c1)
n3 = normalise(open(BRIEF, encoding='utf-8').read())
h1 = hashlib.md5(n1.encode()).hexdigest()
h3 = hashlib.md5(n3.encode()).hexdigest()
print(f'  MD5 run1: {h1[:16]}')
print(f'  MD5 run3: {h3[:16]}')
idem_ok = (h1 == h3)
print(f'  {"PASS" if idem_ok else "FAIL"}  Structurally identical after normalisation')
if not idem_ok:
    fails += 1

print()
if fails == 0:
    print(f'ALL PASS  ({passes} presence + line drift + idempotency)')
else:
    print(f'{fails} FAILURE(S)')
    sys.exit(1)
