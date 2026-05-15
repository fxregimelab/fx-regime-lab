#!/usr/bin/env bash
#
# readiness.sh — Production readiness check wrapper
# Usage: ./scripts/auto/readiness.sh <vercel|prefect> [repo_root]
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <vercel|prefect> [repo_root]" >&2
  exit 1
fi

cd "$REPO_ROOT/pipeline"
python3 -m src.auto.readiness "$TARGET" "${2:-$REPO_ROOT}"
