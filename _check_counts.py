import re, hashlib

raw = open('briefs/brief_20260309.html', encoding='utf-8').read()

checks = [
    ('lp-css-v4 blocks',  '/* lp-css-v4 */'),
    ('brand-v1 blocks',   '/* brand-v1 */'),
    ('landing pages',     '<!-- LANDING PAGE -->'),
    ('brand-footer divs', 'class="brand-footer"'),
    ('lp-nav-hint divs',  'class="lp-nav-hint"'),
    ('pnav-css-v1',       '/* pnav-css-v1 */'),
]
for label, pat in checks:
    print(f'{label}: {raw.count(pat)}')

# Diff two normalised runs
def normalise(s):
    s = re.sub(r'run: \d{2} \w+ \d{4} \d{2}:\d{2} IST', 'run: NORM IST', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s

norm_now = normalise(raw)
print()
print('Lines in current output:', len(raw.splitlines()))
