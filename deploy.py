# deploy.py
# copies latest brief to index.html in repo root and pushes to GitHub
# GitHub Pages serves index.html from root automatically

import os
import shutil
import subprocess
from datetime import datetime

TODAY = datetime.today().strftime('%Y-%m-%d')
TODAY_COMPACT = datetime.today().strftime('%Y%m%d')
BRIEF_SOURCE = f"briefs/brief_{TODAY_COMPACT}.html"  # written by create_html_brief.py this run
DEPLOY_TARGET = "index.html"

def deploy():
    # check brief exists
    if not os.path.exists(BRIEF_SOURCE):
        # fallback: find most recent brief in briefs/ dir
        BRIEF_SOURCE_FINAL = None
        if os.path.exists("briefs"):
            candidates = sorted(
                [f for f in os.listdir("briefs") if f.endswith(".html")],
                reverse=True
            )
            if candidates:
                BRIEF_SOURCE_FINAL = f"briefs/{candidates[0]}"
                print(f"using most recent brief: {BRIEF_SOURCE_FINAL}")
        if not BRIEF_SOURCE_FINAL:
            print("ERROR: no brief found to deploy")
            return
    else:
        BRIEF_SOURCE_FINAL = BRIEF_SOURCE

    # copy to index.html, fixing iframe paths:
    # briefs use ../charts/ (brief is in briefs/ subdir) but index.html is at root
    with open(BRIEF_SOURCE_FINAL, 'r', encoding='utf-8') as f:
        html = f.read()
    html = html.replace('src="../charts/', 'src="charts/')
    if '<html' not in html or '</html>' not in html:
        print("ERROR: brief HTML appears corrupted (missing <html> tags) — aborting deploy")
        return
    with open(DEPLOY_TARGET, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"copied {BRIEF_SOURCE_FINAL} -> {DEPLOY_TARGET} (patched iframe paths)")

    # git add, commit, push
    try:
        # pull remote changes first to avoid rejected push on diverged branches
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
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
        subprocess.run(["git", "commit", "-m",
                       f"brief update {TODAY} {datetime.now().strftime('%H:%M')} IST"],
                      check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"pushed to GitHub at {datetime.now().strftime('%H:%M')} IST")
        print(f"live at: https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/")
    except subprocess.CalledProcessError as e:
        print(f"git push failed: {e}")
        print("brief copied locally but not pushed - check git credentials")

if __name__ == "__main__":
    deploy()
