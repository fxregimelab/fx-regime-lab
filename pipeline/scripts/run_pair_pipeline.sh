#!/bin/bash
# Run pair-specific pipeline
# Usage: ./run_pair_pipeline.sh [EURUSD|USDJPY|USDINR|all] [YYYY-MM-DD]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PAIR="${1:-all}"
DATE_STR="${2:-$(date +%Y-%m-%d)}"

cd "${PIPELINE_DIR}"

# Validate pair argument
if [[ "${PAIR}" != "EURUSD" && "${PAIR}" != "USDJPY" && "${PAIR}" != "USDINR" && "${PAIR}" != "all" ]]; then
    echo "Error: Invalid pair '${PAIR}'. Must be one of: EURUSD, USDJPY, USDINR, all" >&2
    exit 1
fi

# Validate date format
if ! [[ "${DATE_STR}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Error: Invalid date '${DATE_STR}'. Expected format: YYYY-MM-DD" >&2
    exit 1
fi

echo "=== Pair Pipeline Runner ==="
echo "Pair:  ${PAIR}"
echo "Date:  ${DATE_STR}"
echo "Dir:   ${PIPELINE_DIR}"
echo "=============================="

if [[ "${PAIR}" == "all" ]]; then
    python -m src.pairs.runner --all --date "${DATE_STR}"
else
    python -m src.pairs.runner --pair "${PAIR}" --date "${DATE_STR}"
fi

echo "=== Pipeline complete ==="
