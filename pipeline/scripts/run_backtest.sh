#!/bin/bash
# Run backtest comparison
# Usage: ./run_backtest.sh [EURUSD|USDJPY|USDINR|all] [start_date] [end_date]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PAIR="${1:-all}"
START_DATE="${2:-}"
END_DATE="${3:-}"

cd "${PIPELINE_DIR}"

# Validate pair argument
if [[ "${PAIR}" != "EURUSD" && "${PAIR}" != "USDJPY" && "${PAIR}" != "USDINR" && "${PAIR}" != "all" ]]; then
    echo "Error: Invalid pair '${PAIR}'. Must be one of: EURUSD, USDJPY, USDINR, all" >&2
    exit 1
fi

# Validate dates
if [[ -z "${START_DATE}" || -z "${END_DATE}" ]]; then
    echo "Error: start_date and end_date are required." >&2
    echo "Usage: ./run_backtest.sh [pair] [YYYY-MM-DD] [YYYY-MM-DD]" >&2
    exit 1
fi

for d in "${START_DATE}" "${END_DATE}"; do
    if ! [[ "${d}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "Error: Invalid date '${d}'. Expected format: YYYY-MM-DD" >&2
        exit 1
    fi
done

echo "=== Backtest Runner ==="
echo "Pair:  ${PAIR}"
echo "Start: ${START_DATE}"
echo "End:   ${END_DATE}"
echo "Dir:   ${PIPELINE_DIR}"
echo "======================="

if [[ "${PAIR}" == "all" ]]; then
    python -m src.pairs.backtest --all --start "${START_DATE}" --end "${END_DATE}"
else
    python -m src.pairs.backtest --pair "${PAIR}" --start "${START_DATE}" --end "${END_DATE}"
fi

echo "=== Backtest complete ==="
