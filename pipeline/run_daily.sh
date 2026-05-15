#!/usr/bin/env bash
set -euo pipefail

# Repo root (parent of pipeline/), works locally and on GitHub Actions.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/pipeline"

PYTHON="${PYTHON:-.venv/bin/python}"

# Parse optional flags
V3_SHADOW=""
for arg in "$@"; do
  case "$arg" in
    --v3-shadow) V3_SHADOW="--v3-shadow" ;;
  esac
done

$PYTHON -m src.scheduler.run_pipeline ${V3_SHADOW}
