#!/usr/bin/env bash
set -euo pipefail
REPO=/home/shreyash/fx_regime_lab/fx-regime-lab
cd "$REPO"
source pipeline/.venv/bin/activate
python -m src.scheduler.orchestrator weekly
