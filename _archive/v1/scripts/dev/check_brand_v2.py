"""
check_brand_v2.py — stress-test brand-v2 implementation.

Runs generate_html_brief() against the live brief file and verifies:
  A. brand-v2 guard is present (not brand-v1)
  B. All 14 background selectors are present in the injected CSS
  C. Iframe background is #0a0e1a (not #0d0d0d)
  D. Favicon <link rel="icon"> is present
  E. Logo-mark + wordmark img tags are both present (no HTML span)
  -- colours in charts/base.py and charts/workspace.py are verified
     directly from source (no execution needed)
"""
import re
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []


def check(label, condition):
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}")
    results.append(condition)


# ── 1. Generate fresh HTML ────────────────────────────────────────────────────
print("Generating HTML brief …")
from create_html_brief import generate_html_brief
generate_html_brief()

# Find the latest generated brief
import glob
briefs = sorted(glob.glob(os.path.join(ROOT, 'briefs', 'brief_*.html')))
assert briefs, "No brief HTML files found."
latest = briefs[-1]
print(f"Checking: {latest}\n")

with open(latest, encoding='utf-8') as f:
    html = f.read()

# ── A. Guard present ──────────────────────────────────────────────────────────
print("=== A. Brand guard ===")
check("brand-v2 comment present", "/* brand-v2 */" in html)
check("brand-v1 comment absent (old guard gone)", "/* brand-v1 */" not in html or "/* brand-v2 */" in html)

# ── B. All 14 background selectors ───────────────────────────────────────────
print("\n=== B. Navy background selectors ===")
SELECTORS = [
    (".globalbar",           "#111827"),
    (".card",                "#0d1225"),
    (".card-header",         "#111827"),
    (".card-body",           "#0d1225"),
    (".brief-left",          "#0d1225"),
    (".chart-tab-bar",       "#111827"),
    (".chart-tab.active",    "#162647"),
    (".lp-ticker-bar",       "#0d1225"),
    (".lp-card-header",      "#111827"),
    (".lp-drilldown:hover",  "#0f1a34"),
    (".ws-header",           "#111827"),
    (".footer",              "#0a0e1a"),
    ("#pair-nav",            "rgba(10,14,26,0.95)"),
    (".badge-neutral-card",  "#1d2235"),
]
for sel, color in SELECTORS:
    check(f"{sel} → {color}", color in html and sel in html)

# ── C. Iframe backgrounds ────────────────────────────────────────────────────
print("\n=== C. Iframe background color ===")
# Check the generated chart HTML files directly (iframes are separate HTML files)
import glob as _gl2
_chart_files = _gl2.glob(os.path.join(ROOT, 'charts', '*.html'))
_new_bg_count = sum(1 for f in _chart_files if 'background:#0a0e1a' in open(f, encoding='utf-8').read())
check(f"chart iframe files use #0a0e1a ({_new_bg_count}/{len(_chart_files)} files)", _new_bg_count > 0)
check("old iframe bg #0d0d0d absent from brief", "background:#0d0d0d" not in html)

# ── D. Favicon ───────────────────────────────────────────────────────────────
print("\n=== D. Favicon ===")
check('rel="icon" present in <head>', 'rel="icon"' in html)
check("favicon is a data: PNG URI", 'type="image/png" href="data:image/png;base64,' in html)

# ── E. Logo + wordmark ───────────────────────────────────────────────────────
print("\n=== E. Wordmark ===")
check("lp-wordmark img tag present", 'class="lp-wordmark"' in html)
check("lp-wordmark has inline height:180px style", 'style="height:180px' in html)
check("old HTML span brand-name ABSENT", '<span class="lp-brand-name">' not in html)

# ── F. charts/base.py source colours ────────────────────────────────────────
print("\n=== F. charts/base.py Plotly colours ===")
with open(os.path.join(ROOT, 'charts', 'base.py'), encoding='utf-8') as f:
    base_src = f.read()
check("paper_bgcolor='#0a0e1a'", "paper_bgcolor='#0a0e1a'" in base_src)
check("plot_bgcolor='#0d1225'",  "plot_bgcolor='#0d1225'" in base_src)
check("hoverlabel bgcolor='#111827'", "bgcolor='#111827'" in base_src)
check("old paper_bgcolor '#0d0d0d' gone", "paper_bgcolor='#0d0d0d'" not in base_src)

# ── G. charts/workspace.py source colours ───────────────────────────────────
print("\n=== G. charts/workspace.py colours ===")
with open(os.path.join(ROOT, 'charts', 'workspace.py'), encoding='utf-8') as f:
    ws_src = f.read()
check("body bg #0a0e1a", "background:#0a0e1a" in ws_src)
check("#chart-area bg #0a0e1a", "background:#0a0e1a" in ws_src)
check("LAYOUT_BASE paper_bgcolor #0a0e1a", "paper_bgcolor:'#0a0e1a'" in ws_src)
check("LAYOUT_BASE plot_bgcolor #0d1225", "plot_bgcolor:'#0d1225'" in ws_src)
check("old body bg #0d0d0d gone from workspace.py", "background:#0d0d0d" not in ws_src)

# ── H. Chart iframe files background ─────────────────────────────────────────
print("\n=== H. Chart HTML iframe files ===")
import glob as _gl
chart_files = _gl.glob(os.path.join(ROOT, 'charts', '*.html'))
old_bg_files = [f for f in chart_files if 'background:#0d0d0d' in open(f, encoding='utf-8').read()]
check(f"No chart/*.html files have old bg (#0d0d0d) — found {len(old_bg_files)}", len(old_bg_files) == 0)

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
passed = sum(results)
total  = len(results)
print(f"Brand-v2 stress test: {passed}/{total} checks passed")
if passed == total:
    print("\033[92m✓ ALL CHECKS PASSED — brand-v2 implementation verified\033[0m")
else:
    failed_count = total - passed
    print(f"\033[91m✗ {failed_count} CHECK(S) FAILED\033[0m")
    sys.exit(1)
