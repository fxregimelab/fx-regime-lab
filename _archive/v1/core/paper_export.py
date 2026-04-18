# core/paper_export.py
# Phase 4: JSON handoff for MT5 EA — minimal latest snapshot (extend with full signal dict).

from __future__ import annotations

import json
import os
from typing import Any, Dict

from config import TODAY
from core.paths import DATA_DIR, LATEST_WITH_COT_CSV


def write_signals_latest_json() -> None:
    """Write data/signals_latest.json with last-row snapshot for EA consumption."""
    path = os.path.join(DATA_DIR, "signals_latest.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    payload: Dict[str, Any] = {"as_of": TODAY, "source": "fx_regime", "row": None}
    if os.path.exists(LATEST_WITH_COT_CSV):
        import pandas as pd

        df = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
        sub = df.dropna(subset=["EURUSD", "USDJPY"], how="any")
        if len(sub) > 0:
            row = sub.iloc[-1]
            payload["row"] = {k: (None if pd.isna(v) else (float(v) if hasattr(v, "real") else str(v))) for k, v in row.items()}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, path)
