#!/usr/bin/env bash
# Post-deploy self-heal: monitor health → auto-fix if unhealthy (max N attempts)
# Usage: ./scripts/auto/self-heal.sh '<directive>' <tier> <vercel|prefect> [deploy_url] [max_attempts]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DIRECTIVE="${1:-}"
TIER="${2:-}"
TARGET="${3:-}"
URL="${4:-}"
MAX_ATTEMPTS="${5:-3}"

cd "$REPO_ROOT"
python3 -m pipeline.src.auto.self_heal "$DIRECTIVE" "$TIER" "$TARGET" "$URL" "$MAX_ATTEMPTS" "$REPO_ROOT"
