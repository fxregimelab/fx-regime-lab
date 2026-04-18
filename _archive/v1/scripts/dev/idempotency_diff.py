import re, subprocess, shutil, difflib, os, sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)

def normalise(s):
    s = re.sub(r'run: \d{2} \w+ \d{4} \d{2}:\d{2} IST', 'run: NORM IST', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s

# Save snapshot of current output
raw1 = open('briefs/brief_20260309.html', encoding='utf-8').read()
n1 = normalise(raw1).splitlines()

# Run again
subprocess.run([sys.executable, 'create_html_brief.py'], check=True)
raw2 = open('briefs/brief_20260309.html', encoding='utf-8').read()
n2 = normalise(raw2).splitlines()

# Diff
diff = list(difflib.unified_diff(n1, n2, lineterm='', n=3))
if not diff:
    print('NO DIFF — outputs identical after normalisation')
else:
    print(f'DIFF ({len(diff)} lines):')
    for line in diff[:60]:
        print(line)
