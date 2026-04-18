import sys, subprocess, os, hashlib, re as _re
from datetime import datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)

_TODAY = datetime.today().strftime('%Y%m%d')
BRIEF = f'briefs/brief_{_TODAY}.html'

def run_generator():
    r = subprocess.run([sys.executable, 'create_html_brief.py'], capture_output=True, text=True)
    if r.returncode != 0:
        print("GENERATOR ERROR:", r.stderr)
        sys.exit(1)
    return open(BRIEF, 'r', encoding='utf-8').read()

def normalise(html):
    """Strip known non-deterministic fields before diff comparison."""
    # 1. Run timestamp (changes every minute)
    html = _re.sub(r'run: \d\d \w+ \d{4} \d\d:\d\d IST', 'run: TIMESTAMP', html)
    # 2. Collapse ALL blank lines (cosmetic whitespace between block elements)
    html = _re.sub(r'\n\s*\n', '\n', html)
    return html

# --------------------------------------------------------------------------
# Run 1
# --------------------------------------------------------------------------
print("=== Run 1 ===")
content1 = run_generator()
h1 = hashlib.md5(content1.encode()).hexdigest()
print(f"  Output: {BRIEF}  ({len(content1):,} bytes)  md5={h1}")

# --------------------------------------------------------------------------
# CSS presence checks
# --------------------------------------------------------------------------
checks = [
    ('brand-v1 guard in HTML',       '/* brand-v1 */'                                  in content1),
    ('background #0a0e1a !important','#0a0e1a !important'                               in content1),
    ('EUR .ch-pair color rule',      '#card-eurusd .ch-pair'                            in content1),
    ('JPY .ch-pair color rule',      '#card-usdjpy .ch-pair'                            in content1),
    ('INR .ch-pair color rule',      '#card-usdinr .ch-pair'                            in content1),
    ('EUR card border-top 3px blue', '#card-eurusd { border-top: 3px solid #4da6ff'    in content1),
    ('JPY card border-top 3px amber','#card-usdjpy { border-top: 3px solid #ff9944'    in content1),
    ('INR card border-top 3px red',  '#card-usdinr { border-top: 3px solid #e74c3c'    in content1),
    ('badge-danger solid fill',      'rgba(231, 76, 60, 0.85)'                         in content1),
    ('badge-warning solid fill',     'rgba(255, 153, 68, 0.85)'                        in content1),
    ('badge-success semi-solid',     'rgba(46, 204, 113, 0.22)'                        in content1),
    ('badge-neutral dark navy',      '#1d2235'                                          in content1),
    ('.lp-logo-row CSS defined',     '.lp-logo-row'                                    in content1),
    ('.lp-brand-name CSS defined',   '.lp-brand-name'                                  in content1),
    ('.lp-morning-brief CSS defined','.lp-morning-brief'                               in content1),
    ('.brand-footer CSS defined',    '.brand-footer'                                    in content1),
    ('EUR nav active pair color', 'href="#card-eurusd"].nav-active'                in content1),
    ('JPY nav active pair color', 'href="#card-usdjpy"].nav-active'                in content1),
    ('INR nav active pair color', 'href="#card-usdinr"].nav-active'                in content1),
    ('cross-asset ticker CSS',       'lp-ticker-item--cross'                            in content1),
    ('end brand-v1 comment',         '/* end brand-v1 */'                              in content1),
    ('brand-v1 NOT duplicated',      content1.count('/* brand-v1 */') == 1),
]

print("\n=== CSS Checks ===")
all_pass = True
for name, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f"  {status}  {name}")

a2 = normalise(content1)
haN = hashlib.md5(a2.encode()).hexdigest()

# --------------------------------------------------------------------------
# Run 2 — idempotency test
# --------------------------------------------------------------------------
print("\n=== Run 2 (idempotency) ===")
content2 = run_generator()
h2 = hashlib.md5(content2.encode()).hexdigest()
print(f"  Output: {BRIEF}  ({len(content2):,} bytes)  md5={h2}")
b2 = normalise(content2)
hbN = hashlib.md5(b2.encode()).hexdigest()
idempotent = haN == hbN
if idempotent:
    print("  PASS  Output is structurally identical (normalised)")
else:
    all_pass = False
    lines1 = a2.splitlines()
    lines2 = b2.splitlines()
    for i, (a, b) in enumerate(zip(lines1, lines2)):
        if a != b:
            print(f"  FAIL  First diff at normalised line {i+1}:")
            print(f"    Run1: {a[:120]}")
            print(f"    Run2: {b[:120]}")
            break
    else:
        print(f"  FAIL  Outputs differ (Run1 {len(lines1)} lines, Run2 {len(lines2)} lines)")

# --------------------------------------------------------------------------
# brand-v1 block appears only ONCE (no accumulation across runs)
# --------------------------------------------------------------------------
count_after_two_runs = content2.count('/* brand-v1 */')
dup_check = count_after_two_runs == 1
all_pass = all_pass and dup_check
print(f"  {'PASS' if dup_check else 'FAIL'}  brand-v1 block count after 2 runs = {count_after_two_runs} (expected 1)")

# Landing page appears exactly once
lp_count = content2.count('<!-- LANDING PAGE -->')
lp_check = lp_count == 1
all_pass = all_pass and lp_check
print(f"  {'PASS' if lp_check else 'FAIL'}  Landing page count after 2 runs = {lp_count} (expected 1)")

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
print()
if all_pass:
    print("=== ALL CHECKS PASSED ===")
    sys.exit(0)
else:
    print("=== SOME CHECKS FAILED ===")
    sys.exit(1)
