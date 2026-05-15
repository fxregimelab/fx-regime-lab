#!/usr/bin/env bash
# Deploy to Vercel (frontend) or Prefect (pipeline)
# Usage: ./scripts/auto/deploy.sh <vercel|prefect> [repo_root]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TARGET="${1:-}"
REPO_ROOT_ARG="${2:-$REPO_ROOT}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: deploy.sh <vercel|prefect> [repo_root]" >&2
  exit 1
fi

cd "$REPO_ROOT"
python3 -m pipeline.src.auto.deploy "$TARGET" "$REPO_ROOT_ARG"
