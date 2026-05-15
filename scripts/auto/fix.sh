#!/usr/bin/env bash
# Auto-fix loop: run verification → fix → re-verify (max N attempts)
# Usage: ./scripts/auto/fix.sh '<directive>' <tier> [max_attempts]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DIRECTIVE="${1:-}"
TIER="${2:-}"
MAX_ATTEMPTS="${3:-3}"

cd "$REPO_ROOT"
python3 -m pipeline.src.auto.fix "$DIRECTIVE" "$TIER" "$MAX_ATTEMPTS" "$REPO_ROOT"
