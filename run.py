# run.py
# Single entry-point for the full fx_regime pipeline.
# Replaces run_all.py with argparse, per-step timing, and clean error output.
#
# Usage:
#   python run.py                          # run all steps
#   python run.py --skip deploy            # skip git push
#   python run.py --only html              # re-build HTML brief only
#   python run.py --only cot inr merge    # refresh COT + INR data, rebuild merge
#   python run.py --skip cot inr          # skip slow network steps
#
# Step names: fx cot inr vol oi rr merge text macro ai substack html validate deploy

import sys
import os
import glob
import shutil
import subprocess
import argparse
import time
from datetime import datetime

from core.pipeline_status import write_pipeline_status


"""
FX Regime Lab pipeline orchestrator Pipeline.

Execution context:
- Invoked as: python run.py (orchestrator; see STEPS for ordered subprocess scripts)
- Depends on: none (entry point)
- Outputs: none directly; delegates to each step's script
- Next step: first step runs pipeline.py (fx); full chain ends with deploy.py
- Blocking: per STEPS; non-blocking step names: macro, ai, validate, substack (see NON_BLOCKING_STEPS)

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


class _Tee:
    """Write output to both a stream and a log file simultaneously."""
    def __init__(self, stream, logfile):
        self._stream  = stream
        self._logfile = logfile

    def write(self, data):
        try:
            self._stream.write(data)
        except UnicodeEncodeError:
            safe = data.encode(getattr(self._stream, 'encoding', 'utf-8') or 'utf-8',
                               errors='replace').decode(
                               getattr(self._stream, 'encoding', 'utf-8') or 'utf-8')
            self._stream.write(safe)
        self._logfile.write(data)

    def flush(self):
        self._stream.flush()
        self._logfile.flush()

    def isatty(self):
        return False


# ── pipeline step definitions ─────────────────────────────────────────────────
# Each entry: (name, script_file)
# Order matters — each step may depend on the output of the previous one.
STEPS = [
    ("fx",      "pipeline.py"),           # fetch FX prices + yields → data/latest.csv
    ("cot",     "cot_pipeline.py"),       # fetch CFTC COT data → data/cot_latest.csv
    ("inr",     "inr_pipeline.py"),       # fetch USD/INR + IN yields → data/inr_latest.csv
    ("vol",     "vol_pipeline.py"),       # Phase 1: CME CVOL (stub until API wired)
    ("oi",      "oi_pipeline.py"),        # Phase 1: CME OI delta (stub)
    ("rr",      "rr_pipeline.py"),        # Phase 1: synthetic RR proxy (yfinance)
    ("merge",   "scripts/pipeline_merge.py"),  # Phase 1: re-entrant merge — script name differs from "fx" so dedup below is inert
    ("text",    "morning_brief.py"),      # generate text brief → briefs/brief_YYYYMMDD.txt
    ("macro",   "macro_pipeline.py"),      # Phase 10 Stage 2: fetch economic calendar → data/macro_cal.json
    ("ai",      "ai_brief.py"),           # Phase 13: AI regime reads → data/ai_regime_read.json
    ("substack", "scripts/substack_publish.py"),  # Create Substack draft from ai_article.json
    ("html",    "create_html_brief.py"),  # generate HTML brief → briefs/brief_YYYYMMDD.html
    ("validate", "validation_regime.py"), # Phase 2: out-of-sample validation (stub)
    ("deploy",  "deploy.py"),             # copy to index.html and push to GitHub
]

# Deduplicated step scripts (some names share a script — merge is inside pipeline.py)
# When --only merge is requested, pipeline.py still runs (the merge phase is its final step).
_STEP_NAMES = [name for name, _ in STEPS]

# Steps that are non-blocking: pipeline continues even if they fail.
# ai_brief.py has no ANTHROPIC_API_KEY on CI → always exits 0, but guard
# here ensures a true failure (import error, crash) is still non-fatal.
NON_BLOCKING_STEPS = {"ai", "macro", "validate", "substack"}  # substack: optional draft publish


def _run_step(name, script, python_exe):
    """Run one pipeline step.  Returns (success: bool, elapsed_seconds: float)."""
    t0 = time.perf_counter()
    result = subprocess.run(
        [python_exe, script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    elapsed = time.perf_counter() - t0
    # Write captured output through sys.stdout/_Tee so it reaches both
    # the console AND the pipeline.log file.
    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.returncode == 0, elapsed


def _archive(today_str):
    """Archive run outputs into runs/YYYY-MM-DD/."""
    run_dir = os.path.join('runs', today_str)
    os.makedirs(os.path.join(run_dir, 'data'), exist_ok=True)
    os.makedirs(os.path.join(run_dir, 'charts'), exist_ok=True)

    slug = today_str.replace('-', '')
    file_map = {
        f'data/master_{slug}.csv':       'master.csv',
        'data/cot_latest.csv':           'cot.csv',
        'data/latest_with_cot.csv':      'master_with_cot.csv',
        f'briefs/brief_{slug}.html':     'brief.html',
    }
    for src, dst_name in file_map.items():
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(run_dir, 'data', dst_name))

    brief_txt = f'briefs/brief_{slug}.txt'
    if os.path.exists(brief_txt):
        shutil.copy2(brief_txt, os.path.join(run_dir, 'brief.txt'))

    # Copy chart HTML files so the archived brief is self-contained
    for chart_file in glob.glob('charts/*.html'):
        shutil.copy2(chart_file, os.path.join(run_dir, 'charts', os.path.basename(chart_file)))

    print(f'  archived -> runs/{today_str}/')


def main():
    parser = argparse.ArgumentParser(
        description='fx_regime daily pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'Available steps: {", ".join(_STEP_NAMES)}'
    )
    parser.add_argument(
        '--skip', nargs='*', default=[], metavar='STEP',
        help='Steps to skip (space-separated)'
    )
    parser.add_argument(
        '--only', nargs='*', default=None, metavar='STEP',
        help='Run only these steps (space-separated)'
    )
    args = parser.parse_args()

    # Validate step names
    all_names = set(_STEP_NAMES)
    for n in (args.skip or []) + (args.only or []):
        if n not in all_names:
            print(f'ERROR: unknown step "{n}". Valid: {", ".join(_STEP_NAMES)}')
            sys.exit(1)

    python_exe = sys.executable
    today_str  = datetime.today().strftime('%Y-%m-%d')

    # ── per-run log file ────────────────────────────────────────────────────────
    log_path = os.path.join('runs', today_str, 'pipeline.log')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    _log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
    # Wrap everything in try/finally so the log handle is ALWAYS closed,
    # even if an uncaught exception escapes the step loop (Windows file lock fix).
    failed = False
    try:
        sys.stdout = _Tee(sys.__stdout__, _log_file)
        sys.stderr = _Tee(sys.__stderr__, _log_file)

        # Deduplicate: pipeline.py appears as both "fx" and "merge"
        # — if both are in the run set, only run pipeline.py once.
        seen_scripts = set()
        completed_steps: list[str] = []
        total_start = time.perf_counter()

        print(f'\n{"="*50}')
        print(f'  fx_regime pipeline  --  {today_str}')
        print(f'{"="*50}')

        for name, script in STEPS:
            # Filter by --only / --skip
            if args.only is not None and name not in args.only:
                print(f'  [skip]  {name}')
                continue
            if name in args.skip:
                print(f'  [skip]  {name}')
                continue
            # Deduplicate scripts (fx and merge both call pipeline.py)
            if script in seen_scripts:
                print(f'  [dedup] {name}  ({script} already ran)')
                continue
            seen_scripts.add(script)

            print(f'\n>>  {name}  ({script})')
            ok, elapsed = _run_step(name, script, python_exe)
            if ok:
                print(f'OK  {name}  -- {elapsed:.1f}s')
                completed_steps.append(name)
            else:
                print(f'FAIL  {name} after {elapsed:.1f}s')
                if name in NON_BLOCKING_STEPS:
                    print(f'   WARN: {name} failed — non-blocking, pipeline continues')
                else:
                    print(f'   Fix {script} and re-run:  python run.py --only {name}')
                    failed = True
                    try:
                        write_pipeline_status(
                            ok=False,
                            steps_completed=completed_steps,
                            error_message=f"step:{name}",
                        )
                    except OSError as e:
                        print(f"  WARN: could not write pipeline_status.json: {e}")
                    break

        total = time.perf_counter() - total_start

        if not failed:
            print(f'\n{"="*50}')
            print(f'  all steps done  ({total:.1f}s total)')
            _archive(today_str)

            # Notion sync — runs after all pipeline output is complete
            print("\nRunning Notion sync...")
            notion_result = subprocess.run(
                [python_exe, "notion_sync.py"],
                capture_output=True, text=True,
            )
            print(notion_result.stdout)
            if notion_result.returncode != 0:
                print(f"Notion sync warning: {notion_result.stderr[:200]}")
                print("(Pipeline complete — Notion sync failure is non-blocking)")

            print()
            print('  live at: https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/')
            print(f'{"="*50}\n')
            try:
                write_pipeline_status(ok=True, steps_completed=completed_steps)
            except OSError as e:
                print(f"  WARN: could not write pipeline_status.json: {e}")
        else:
            print(f'\n  pipeline stopped after {total:.1f}s -- fix the error above and retry.\n')

    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        _log_file.close()

    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
