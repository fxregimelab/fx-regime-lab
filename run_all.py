# run_all.py
import subprocess
import sys
import os
import shutil
from datetime import datetime

print("running full pipeline...\n")
subprocess.run([sys.executable, "pipeline.py"],          check=True)
subprocess.run([sys.executable, "cot_pipeline.py"],      check=True)
subprocess.run([sys.executable, "inr_pipeline.py"],      check=True)
subprocess.run([sys.executable, "create_dashboards.py"], check=True)
subprocess.run([sys.executable, "morning_brief.py"],     check=True)
subprocess.run([sys.executable, "create_html_brief.py"], check=True)
subprocess.run([sys.executable, "deploy.py"],            check=True)
print("\ndone. brief is live at:")
print("https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/")

# --- archive run outputs into daily folder ---
TODAY = datetime.today().strftime('%Y-%m-%d')
run_dir = os.path.join('runs', TODAY)

# create folder structure
os.makedirs(os.path.join(run_dir, 'charts'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data'), exist_ok=True)

# copy charts
for fname in [
    f'eurusd_fundamentals_{TODAY.replace("-","")}.png',
    f'eurusd_positioning_{TODAY.replace("-","")}.png',
    f'eurusd_volatility_{TODAY.replace("-","")}.png',
    f'usdjpy_fundamentals_{TODAY.replace("-","")}.png',
    f'usdjpy_positioning_{TODAY.replace("-","")}.png',
    f'usdjpy_volatility_{TODAY.replace("-","")}.png',
]:
    src = os.path.join('charts', fname)
    dst = os.path.join(run_dir, 'charts', fname.replace(f'_{TODAY.replace("-","")}', ''))
    if os.path.exists(src):
        shutil.copy2(src, dst)

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