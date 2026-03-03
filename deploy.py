# deploy.py
# copies latest brief to index.html in repo root and pushes to GitHub
# GitHub Pages serves index.html from root automatically

import os
import shutil
import subprocess
from datetime import datetime

TODAY = datetime.today().strftime('%Y-%m-%d')
BRIEF_SOURCE = f"runs/{TODAY}/data/brief.html"
DEPLOY_TARGET = "index.html"

def deploy():
    # check brief exists
    if not os.path.exists(BRIEF_SOURCE):
        # fallback: find most recent brief
        runs_dir = "runs"
        BRIEF_SOURCE_FINAL = None
        if os.path.exists(runs_dir):
            dates = sorted(os.listdir(runs_dir), reverse=True)
            for d in dates:
                candidate = f"runs/{d}/data/brief.html"
                if os.path.exists(candidate):
                    BRIEF_SOURCE_FINAL = candidate
                    print(f"using most recent brief: {candidate}")
                    break
        if not BRIEF_SOURCE_FINAL:
            print("ERROR: no brief found to deploy")
            return
    else:
        BRIEF_SOURCE_FINAL = BRIEF_SOURCE

    # copy to index.html
    shutil.copy2(BRIEF_SOURCE_FINAL, DEPLOY_TARGET)
    print(f"copied {BRIEF_SOURCE_FINAL} -> {DEPLOY_TARGET}")

    # git add, commit, push
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
