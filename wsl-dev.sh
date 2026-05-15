#!/usr/bin/env bash
# WSL2 Development Environment Setup for FX Regime Lab
# Usage: wsl -d Ubuntu-24.04 -- bash /mnt/d/Projects/fx_regime_lab/fx-regime-lab/wsl-dev.sh

set -e

echo "=== FX Regime Lab — WSL2 Dev Environment ==="

# Path inside WSL (native filesystem for best performance)
WSL_PROJECT="/root/fx-regime-lab"
WINDOWS_PROJECT="/mnt/d/Projects/fx_regime_lab/fx-regime-lab"

# Ensure uv is in PATH
export PATH="/root/.local/bin:$PATH"

# Navigate to WSL-native copy
cd "$WSL_PROJECT"

echo ""
echo "1. Git status:"
git status --short | head -10

echo ""
echo "2. Python environment (pipeline):"
cd "$WSL_PROJECT/pipeline"
uv --version
python --version

echo ""
echo "3. Node environment (web):"
cd "$WSL_PROJECT/web"
node --version
npm --version

echo ""
echo "=== Quick Commands ==="
echo "Build web (production):   cd $WSL_PROJECT/web && npm run build"
echo "Run web dev server:       cd $WSL_PROJECT/web && npm run dev"
echo "Run pipeline tests:       cd $WSL_PROJECT/pipeline && uv run pytest"
echo "Run pipeline lint:        cd $WSL_PROJECT/pipeline && uv run ruff check ."
echo "Run pipeline typecheck:   cd $WSL_PROJECT/pipeline && uv run mypy ."
echo ""
echo "=== Sync Windows ↔ WSL ==="
echo "The WSL copy is at: $WSL_PROJECT"
echo "The Windows copy is at: $WINDOWS_PROJECT"
echo ""
echo "To sync changes FROM Windows TO WSL:"
echo "  cd $WINDOWS_PROJECT && git push && cd $WSL_PROJECT && git pull"
echo ""
echo "To sync changes FROM WSL TO Windows:"
echo "  cd $WSL_PROJECT && git push && cd $WINDOWS_PROJECT && git pull"
echo ""
