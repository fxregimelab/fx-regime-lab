# deploy.py
# copies latest brief to index.html in repo root and pushes to GitHub
# GitHub Pages serves index.html from root automatically

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

from config import DATE_SLUG, TODAY

"""
GitHub Pages deploy Pipeline.

Execution context:
- Called by run.py as STEP 12 (deploy) — end of pipeline
- Depends on: create_html_brief.py (brief HTML must exist)
- Outputs: repo-root index.html, git commit and push to GitHub Pages
- Next step: none
- Blocking: YES — pipeline halts on failure

Brief path uses config.DATE_SLUG (same as create_html_brief.py).

Stale-brief fallback:
- Local: if briefs/brief_{DATE_SLUG}.html is missing, may use newest briefs/*.html
  (WARN: not today’s slug). Set DEPLOY_ALLOW_STALE_BRIEF=1 on GitHub Actions to
  allow the same fallback in CI.
- GitHub Actions: if today’s brief does not exist, exit 1 unless
  DEPLOY_ALLOW_STALE_BRIEF=1.

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

BRIEF_SOURCE = f"briefs/brief_{DATE_SLUG}.html"
DEPLOY_TARGET = "index.html"


def _deploy_stale_fallback_allowed() -> bool:
    if os.environ.get("DEPLOY_ALLOW_STALE_BRIEF") == "1":
        return True
    return os.environ.get("GITHUB_ACTIONS") != "true"


def deploy():
    # Resolve brief path (today’s slug vs newest fallback)
    if not os.path.exists(BRIEF_SOURCE):
        if not _deploy_stale_fallback_allowed():
            print(
                "ERROR: today's brief not found (expected "
                f"{BRIEF_SOURCE}). In CI, stale fallback is disabled; "
                "set DEPLOY_ALLOW_STALE_BRIEF=1 to allow newest brief."
            )
            sys.exit(1)
        BRIEF_SOURCE_FINAL = None
        if os.path.exists("briefs"):
            candidates = sorted(
                [f for f in os.listdir("briefs") if f.endswith(".html")],
                reverse=True,
            )
            if candidates:
                BRIEF_SOURCE_FINAL = f"briefs/{candidates[0]}"
                print(
                    f"WARN: deploying stale brief (not {BRIEF_SOURCE}): "
                    f"{BRIEF_SOURCE_FINAL}"
                )
        if not BRIEF_SOURCE_FINAL:
            print("ERROR: no brief found to deploy")
            sys.exit(1)
    else:
        BRIEF_SOURCE_FINAL = BRIEF_SOURCE

    if not shutil.which("git"):
        print("ERROR: git not found in PATH — cannot push to GitHub")
        sys.exit(1)

    # copy to index.html, fixing iframe paths:
    # briefs use ../charts/ (brief is in briefs/ subdir) but index.html is at root
    with open(BRIEF_SOURCE_FINAL, 'r', encoding='utf-8') as f:
        html = f.read()
    html, n_subs = re.subn(r'(<iframe\b[^>]*\bsrc=")\.\.\/charts\/', r'\1charts/', html)
    if n_subs == 0:
        print("WARN: no iframe src paths were rewritten — charts may not load in index.html")
    # Fix CSS link path: briefs use ../static/ but index.html is at repo root
    html = html.replace('href="../static/styles.css"', 'href="static/styles.css"')
    if '<html' not in html or '</html>' not in html:
        print("ERROR: brief HTML appears corrupted (missing <html> tags) — aborting deploy")
        sys.exit(1)
    with open(DEPLOY_TARGET, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"copied {BRIEF_SOURCE_FINAL} -> {DEPLOY_TARGET} (patched iframe paths)")

    # git add, commit, push
    # Commit first, then pull --rebase to replay our commit on top of any
    # remote changes pushed since checkout.  This avoids the --autostash
    # index-loss bug: stash pop restores only the working tree, not the
    # index, so a post-pop commit would find nothing staged and exit 1.
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        # check if there is actually anything staged to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True
        )
        if not status.stdout.strip():
            print("index.html unchanged -- nothing to commit, skipping push")
            print(f"live at: https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/")
            return
        # Commit first, then rebase our commit on top of any new remote commits
        subprocess.run(["git", "commit", "-m",
                       f"brief update {TODAY} {datetime.now().strftime('%H:%M')} IST"],
                      check=True)
        # Sync with origin without manual conflict resolution: the deploy commit
        # regenerates index.html, charts/*.html, site/charts, pipeline_status, etc.
        # If main moved (e.g. site/terminal edits), plain rebase stops on conflicts.
        # - rebase -X theirs: on conflict, keep the replayed deploy commit's hunks.
        # - if rebase still fails, abort and merge preferring current branch (-X ours).
        subprocess.run(["git", "fetch", "origin", "main"], check=True)
        rb = subprocess.run(
            ["git", "rebase", "-X", "theirs", "origin/main"],
            capture_output=True,
            text=True,
        )
        if rb.returncode != 0:
            print("WARN: rebase with -X theirs failed; trying merge origin/main (-X ours)")
            if rb.stderr:
                print(rb.stderr.strip())
            subprocess.run(["git", "rebase", "--abort"], check=False)
            subprocess.run(
                [
                    "git",
                    "merge",
                    "origin/main",
                    "-m",
                    "Merge origin/main before deploy push",
                    "-X",
                    "ours",
                ],
                check=True,
            )
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"pushed to GitHub at {datetime.now().strftime('%H:%M')} IST")
        print(f"live at: https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git operation failed: {e}")
        print("brief is saved locally but NOT pushed to GitHub — check git credentials/network")
        raise SystemExit(1)  # propagate failure so callers (run.py / run_all.py) know deploy failed

if __name__ == "__main__":
    deploy()
