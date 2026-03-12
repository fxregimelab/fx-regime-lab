"""
Stress test script for all phases.
Run: python _stress_test.py
"""
import re
import sys
import os

BRIEF = "briefs/brief_20260312.html"

def check(condition, msg):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {msg}")
    return condition

print("=" * 60)
print("  STRESS TEST -- All Phases")
print("=" * 60)

# ── Load brief ──────────────────────────────────────────────────
if not os.path.exists(BRIEF):
    print(f"FATAL: {BRIEF} not found. Run: python run.py --only html")
    sys.exit(1)

with open(BRIEF, encoding="utf-8") as f:
    brief = f.read()

all_pass = True

print("\n--- Phase 6A: Tab structure ---")
for pair, expected_tabs, expected_panes in [
    ("eurusd", 6, 6),
    ("usdjpy", 7, 7),
    ("usdinr", 6, 6),
]:
    tabs  = sorted(set(re.findall(f'data-pair="{pair}" data-tab="(\d+)"', brief)))
    panes = sorted(set(re.findall(f'data-pair="{pair}" data-pane="(\d+)"', brief)))
    r1 = check(len(tabs) == expected_tabs, f"{pair}: {len(tabs)}/{expected_tabs} tab buttons present  {tabs}")
    r2 = check(len(panes) == expected_panes, f"{pair}: {len(panes)}/{expected_panes} pane divs present  {panes}")
    all_pass = all_pass and r1 and r2

r = check("theme-toggle-btn" in brief, "theme toggle button present in brief")
all_pass = all_pass and r

print("\n--- Phase 6A: BOJ SIGNAL tab ---")
r = check('data-pair="usdjpy" data-tab="4"' in brief, "USD/JPY tab 4 (BOJ SIGNAL) present")
all_pass = all_pass and r

print("\n--- Phase 6A: USD/INR tabs ---")
r = check('VOL &amp; CORRELATION' in brief or 'VOL & CORRELATION' in brief, "USD/INR VOL & CORRELATION tab present")
all_pass = all_pass and r
r = check('FPI FLOWS' in brief, "USD/INR FPI FLOWS tab present")
all_pass = all_pass and r

print("\n--- Phase 6B: Spread labels ---")
r = check("US\u2013IN 10Y" in brief, "USD/INR spread label is 'US-IN 10Y'")
all_pass = all_pass and r
r = check("US 2Y" not in brief or "US 2Y\u2013IN 10Y (cross)" not in brief, "Old 'US 2Y-IN 10Y (cross)' label removed")
all_pass = all_pass and r

print("\n--- Phase 8: New tabs ---")
r = check('"eurusd" data-tab="4"' in brief or 'data-pair="eurusd" data-tab="4"' in brief, "EUR/USD MOMENTUM tab present")
all_pass = all_pass and r
r = check('"eurusd" data-tab="5"' in brief or 'data-pair="eurusd" data-tab="5"' in brief, "EUR/USD COMPOSITE tab present")
all_pass = all_pass and r

print("\n--- Phase 8: Chart files ---")
expected_charts = [
    "eurusd_0", "eurusd_1", "eurusd_2", "eurusd_3", "eurusd_4", "eurusd_5",
    "usdjpy_0", "usdjpy_1", "usdjpy_2", "usdjpy_3", "usdjpy_4", "usdjpy_5", "usdjpy_6",
    "usdinr_0", "usdinr_1", "usdinr_2", "usdinr_3", "usdinr_4", "usdinr_5",
]
for c in expected_charts:
    exists = os.path.exists(f"charts/{c}.html")
    r = check(exists, f"charts/{c}.html exists")
    all_pass = all_pass and r

print("\n--- Phase 7: Workspace controls ---")
ws = open("charts/global_workspace.html", encoding="utf-8").read()
r = check("period-btn" in ws, "Period quick-pick buttons present in workspace")
all_pass = all_pass and r
r = check('id="norm-mode"' in ws, "Normalization mode selector present")
all_pass = all_pass and r
r = check('id="corr-window"' in ws, "Rolling corr window selector present")
all_pass = all_pass and r
r = check('id="btn-csv"' in ws, "CSV export button present")
all_pass = all_pass and r
r = check("composite" in ws, "SCORES preset in workspace")
all_pass = all_pass and r
r = check("eurusd_composite_score" in ws, "Composite score series in workspace data")
all_pass = all_pass and r
r = check("US_curve" in ws, "US Yield Curve series in workspace")
all_pass = all_pass and r
r = check("BTP_Bund_spread" in ws, "BTP-Bund series in workspace")
all_pass = all_pass and r

print("\n--- Phase 6B: Formula correctness ---")
pipeline_src = open("pipeline.py", encoding="utf-8").read()
r = check('_spread("US_10Y", "DE_10Y")' in pipeline_src, 'pipeline.py uses US_10Y for US_DE_10Y_spread')
all_pass = all_pass and r
r = check('_spread("US_10Y", "JP_10Y")' in pipeline_src, 'pipeline.py uses US_10Y for US_JP_10Y_spread')
all_pass = all_pass and r

inr_src = open("inr_pipeline.py", encoding="utf-8").read()
r = check('inr["US_10Y"] = master["US_10Y"]' in inr_src, 'inr_pipeline.py loads US_10Y from master')
all_pass = all_pass and r
r = check('inr["US_10Y"] - inr["IN_10Y"]' in inr_src, 'inr_pipeline.py US_IN_10Y_spread uses US_10Y')
all_pass = all_pass and r

charts_src = open("create_charts_plotly.py", encoding="utf-8").read()
r = check("US 10Y \u2013 IN 10Y" in charts_src, 'create_charts_plotly.py legend updated to US 10Y-IN 10Y')
all_pass = all_pass and r

print("\n" + "=" * 60)
if all_pass:
    print("  ALL CHECKS PASSED ✓")
else:
    print("  SOME CHECKS FAILED -- review output above")
print("=" * 60)
sys.exit(0 if all_pass else 1)
