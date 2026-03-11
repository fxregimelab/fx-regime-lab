# run_all.py
import subprocess
import sys
import os
import shutil
import argparse
from datetime import datetime

_parser = argparse.ArgumentParser(description='Run full FX brief pipeline')
_parser.add_argument('--months', type=int, default=12,
                     help='Chart data window in months passed to create_html_brief.py (default: 12)')
_args = _parser.parse_args()
MONTHS = _args.months

print("running full pipeline...\n")
subprocess.run([sys.executable, "pipeline.py"],          check=True)
subprocess.run([sys.executable, "cot_pipeline.py"],      check=True)
subprocess.run([sys.executable, "inr_pipeline.py"],      check=True)
subprocess.run([sys.executable, "morning_brief.py"],     check=True)
subprocess.run([sys.executable, "create_html_brief.py", "--months", str(MONTHS)], check=True)
subprocess.run([sys.executable, "deploy.py"],            check=True)
print("\ndone. brief is live at:")
print("https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/")

# --- archive run outputs into daily folder ---
TODAY = datetime.today().strftime('%Y-%m-%d')
run_dir = os.path.join('runs', TODAY)

# create folder structure
os.makedirs(os.path.join(run_dir, 'data'), exist_ok=True)

# copy data files
file_map = {
    f'data/master_{TODAY.replace("-","")}.csv': 'master.csv',
    'data/cot_latest.csv': 'cot.csv',
    'data/latest_with_cot.csv': 'master_with_cot.csv',
    f'briefs/brief_{TODAY.replace("-","")}.html': 'brief.html',
}
for src, dst_name in file_map.items():
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(run_dir, 'data', dst_name))

# copy brief
brief_src = f'briefs/brief_{TODAY.replace("-","")}.txt'
if os.path.exists(brief_src):
    shutil.copy2(brief_src, os.path.join(run_dir, 'brief.txt'))

print(f'\n  archived to: runs/{TODAY}/')