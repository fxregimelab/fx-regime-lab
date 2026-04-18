"""
If deploy / `git pull --rebase` stopped mid-rebase with conflicts in generated
brief assets, run from repo root:

  python scripts/dev/resolve_deploy_rebase_conflicts.py

During a rebase, `--theirs` is the commit being replayed (your brief/deploy
commit). Then `git rebase --continue`.

If you are not in a rebase, use `git status` and resolve manually, or
`git rebase --abort` and pull with the updated deploy.py.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PATHSPECS = [
    "charts",
    "site/charts",
    "index.html",
    "site/brief/latest.html",
    "site/static/pipeline_status.json",
]


def main() -> int:
    os.chdir(ROOT)
    in_rebase = os.path.isdir(os.path.join(".git", "rebase-merge")) or os.path.isdir(
        os.path.join(".git", "rebase-apply")
    )
    if not in_rebase:
        print("Not in a git rebase. Nothing to do.")
        print("Tip: deploy.py now uses `git rebase -X theirs` to avoid this.")
        return 1
    for p in PATHSPECS:
        subprocess.run(["git", "checkout", "--theirs", "--", p], check=False)
    subprocess.run(["git", "add", "-A"], check=True)
    # Avoid blocking on editor if Git tries to open one (varies by platform).
    env = os.environ.copy()
    env.setdefault("GIT_EDITOR", ":")
    env.setdefault("EDITOR", ":")
    r = subprocess.run(["git", "rebase", "--continue"], env=env, check=False)
    return 0 if r.returncode == 0 else r.returncode


if __name__ == "__main__":
    sys.exit(main())
