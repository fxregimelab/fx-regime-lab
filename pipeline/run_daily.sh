#!/usr/bin/env bash
set -euo pipefail

# Repo root (parent of pipeline/), works locally and on GitHub Actions.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/pipeline"

if [ -f .venv/bin/activate ]; then
  # Local/dev: optional venv beside pipeline/.
  # CI: setup-python + pip install -e ./pipeline (no venv).
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

python src/scheduler/orchestrator.py daily
python src/scheduler/overnight_check.py
