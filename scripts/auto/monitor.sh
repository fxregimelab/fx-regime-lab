#!/usr/bin/env bash
#
# monitor.sh — Post-deploy monitoring wrapper
# Usage: ./scripts/auto/monitor.sh <vercel|prefect|supabase> [url] [duration_seconds]
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-}"
URL="${2:-}"
DURATION="${3:-30}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <vercel|prefect|supabase> [url] [duration_seconds]" >&2
  exit 1
fi

cd "$REPO_ROOT/pipeline"
python3 -m src.auto.monitor "$TARGET" "$URL" "$DURATION"
