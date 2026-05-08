#!/usr/bin/env bash
set -euo pipefail

# Repo root (parent of pipeline/), works locally and on GitHub Actions.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/pipeline"

PYTHON="${PYTHON:-.venv/bin/python}"

$PYTHON src/scheduler/run_pipeline.py
