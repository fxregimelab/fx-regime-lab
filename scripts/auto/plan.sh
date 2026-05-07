#!/usr/bin/env bash
# Generate implementation plan + spec from directive
# Usage: ./scripts/auto/plan.sh '<directive>' <tier>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
python3 -m pipeline.src.auto.plan "$1" "$2" "$REPO_ROOT"
