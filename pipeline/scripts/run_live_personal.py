"""Live personal run launcher (background branch only).

Loads repo-root ``.env.local`` into process env (never prints values),
then executes the production daily pipeline for today via
``src.scheduler.run_pipeline``. All DB writes go through
``src.db.writer``; all AI calls through ``src.ai.client``.

Usage (from ``pipeline/``):  python scripts/run_live_personal.py [YYYY-MM-DD]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))


def _load_env_local() -> None:
    path = REPO_ROOT / ".env.local"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export ") :].strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")


def main() -> None:
    _load_env_local()
    from src.scheduler.run_pipeline import run_pipeline

    date_override = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(date_override)


if __name__ == "__main__":
    main()
