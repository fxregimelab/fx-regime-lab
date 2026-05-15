#!/bin/bash
set -e
cd "$(dirname "$0")"
set -a
source ../.env
set +a

PAIR=$1
START=$2
END=$3

python3 -m src.backfill.simulation_engine --pair "$PAIR" --start "$START" --end "$END"
