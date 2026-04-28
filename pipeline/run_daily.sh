#!/usr/bin/env bash
set -euo pipefail
REPO=/home/shreyash/fx_regime_lab/fx-regime-lab
cd "$REPO"
if [ -f pipeline/.venv/bin/activate ]; then
  # Local/dev path.
  # GitHub Actions uses setup-python + pip install -e ./pipeline instead.
  source pipeline/.venv/bin/activate
fi
python -m src.scheduler.orchestrator daily
