# core/paths.py
# Single home for all file-path constants used across the pipeline.
# Import from here so changing a folder name is a one-line edit.

import os
from datetime import datetime

# ── root ─────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(ROOT) != 'fx_regime':
    print(f"WARN: unexpected project root '{ROOT}' — expected directory named 'fx_regime'"
          f" (continuing, but path-based defaults may not work correctly)")

# ── data directory ───────────────────────────────────────────────────────────
DATA_DIR   = os.path.join(ROOT, 'data')
BRIEFS_DIR = os.path.join(ROOT, 'briefs')
RUNS_DIR   = os.path.join(ROOT, 'runs')
CHARTS_DIR = os.path.join(ROOT, 'charts')
PAGES_DIR  = os.path.join(ROOT, 'pages')
SITE_DIR   = os.path.join(ROOT, 'site')
# Written each successful pipeline run; deployed with `deploy.py` for Cloudflare Pages
PIPELINE_STATUS_JSON = os.path.join(SITE_DIR, 'data', 'pipeline_status.json')
# Written by subprocess steps (inr/cot) so run.py can merge Supabase sync metadata.
SUPABASE_SYNC_SIDECAR = os.path.join(SITE_DIR, 'data', 'supabase_sync_sidecar.json')

# ── key data files ───────────────────────────────────────────────────────────
LATEST_CSV         = os.path.join(DATA_DIR, 'latest.csv')
LATEST_WITH_COT_CSV = os.path.join(DATA_DIR, 'latest_with_cot.csv')
COT_LATEST_CSV     = os.path.join(DATA_DIR, 'cot_latest.csv')
INR_LATEST_CSV     = os.path.join(DATA_DIR, 'inr_latest.csv')


def master_csv(date_str=None):
    """Return path to data/master_YYYYMMDD.csv for a given date string (YYYY-MM-DD).
    Uses today if omitted."""
    if date_str is None:
        date_str = datetime.today().strftime('%Y-%m-%d')
    slug = date_str.replace('-', '')
    return os.path.join(DATA_DIR, f'master_{slug}.csv')


def brief_html(date_str=None):
    """Return path to briefs/brief_YYYYMMDD.html for a given date string."""
    if date_str is None:
        date_str = datetime.today().strftime('%Y-%m-%d')
    slug = date_str.replace('-', '')
    return os.path.join(BRIEFS_DIR, f'brief_{slug}.html')


def brief_txt(date_str=None):
    """Return path to briefs/brief_YYYYMMDD.txt for a given date string."""
    if date_str is None:
        date_str = datetime.today().strftime('%Y-%m-%d')
    slug = date_str.replace('-', '')
    return os.path.join(BRIEFS_DIR, f'brief_{slug}.txt')


def run_dir(date_str=None):
    """Return path to runs/YYYY-MM-DD/ for a given date string."""
    if date_str is None:
        date_str = datetime.today().strftime('%Y-%m-%d')
    return os.path.join(RUNS_DIR, date_str)
