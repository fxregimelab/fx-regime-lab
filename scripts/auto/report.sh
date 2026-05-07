#!/usr/bin/env bash
#
# report.sh — Human-readable report generation wrapper
# Usage: ./scripts/auto/report.sh <context.json>
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT="${1:-}"

if [[ -z "$CONTEXT" ]]; then
  echo "Usage: $0 <context.json>" >&2
  exit 1
fi

cd "$REPO_ROOT/pipeline"
python3 -m src.auto.report "$CONTEXT"
