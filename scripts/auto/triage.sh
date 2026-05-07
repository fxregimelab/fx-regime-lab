#!/usr/bin/env bash
#
# triage.sh — Task classification wrapper for CEO Mode
# Usage: ./scripts/auto/triage.sh "<directive>"
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DIRECTIVE="${1:-}"

if [[ -z "$DIRECTIVE" ]]; then
  echo "Usage: $0 '<directive>'" >&2
  exit 1
fi

cd "$REPO_ROOT/pipeline"
python3 -m src.auto.triage "$DIRECTIVE"
