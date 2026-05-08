#!/usr/bin/env bash
set -euo pipefail

# Repo root (parent of pipeline/), works locally and on GitHub Actions.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/pipeline"

PYTHON="${PYTHON:-.venv/bin/python}"

$PYTHON src/scheduler/orchestrator.py daily
$PYTHON src/scheduler/overnight_check.py
$PYTHON -m src.validation.engine
$PYTHON -m src.validation.aggregate
