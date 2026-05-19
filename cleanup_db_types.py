#!/usr/bin/env python3
"""Remove stale columns from database.types.ts signals and validation_log types."""

import re
from pathlib import Path

FILE = Path("D:/Projects/fx_regime_lab/fx-regime-lab/web/src/lib/supabase/database.types.ts")

SIGNALS_STALE = {
    "atm_vol",
    "oi_price_alignment",
    "rate_diff_zscore",
    "vol_skew",
    "rate_diff_mom",
    "realized_vol_21",
}

VALIDATION_STALE = {
    "validation_date",
    "is_correct",
    "pnl_bps",
    "actual_return_1d",
    "alpha_return_1d",
    "correct_1d",
    "dxy_return_1d",
    "max_intraday_adverse_bps",
    "predicted_direction",
    "predicted_regime",
    "regime_at_call",
    "vol_regime_at_call",
}

content = FILE.read_text(encoding="utf-8")
lines = content.splitlines()


def is_stale_line(line: str, cols: set[str]) -> bool:
    """Check if a line defines one of the stale columns."""
    stripped = line.strip()
    m = re.match(r'^([a-z_][a-z0-9_]*)\??\s*:', stripped)
    if m and m.group(1) in cols:
        return True
    return False


def find_block_bounds(lines: list[str], table_name: str) -> tuple[int, int]:
    """Find the start and end line indices of a table block."""
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{table_name}: {{"):
            start = i
            break
    if start is None:
        return -1, -1

    # Find the closing brace at the same indent level
    base_indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "};" or lines[i].strip() == "}":
            line_indent = len(lines[i]) - len(lines[i].lstrip())
            if line_indent == base_indent:
                return start, i
    return start, len(lines) - 1


def remove_stale_from_block(lines: list[str], start: int, end: int, cols: set[str]) -> list[str]:
    """Remove stale column lines from within [start, end] range."""
    result = []
    for i in range(start, end + 1):
        if is_stale_line(lines[i], cols):
            continue
        result.append(lines[i])
    return result


# Process signals block
sig_start, sig_end = find_block_bounds(lines, "signals")
if sig_start >= 0:
    before = lines[:sig_start]
    block = remove_stale_from_block(lines, sig_start, sig_end, SIGNALS_STALE)
    after = lines[sig_end + 1:]
    lines = before + block + after

# Process validation_log block
val_start, val_end = find_block_bounds(lines, "validation_log")
if val_start >= 0:
    before = lines[:val_start]
    block = remove_stale_from_block(lines, val_start, val_end, VALIDATION_STALE)
    after = lines[val_end + 1:]
    lines = before + block + after

FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("database.types.ts cleaned.")
print(f"   Removed {len(SIGNALS_STALE)} stale columns from signals")
print(f"   Removed {len(VALIDATION_STALE)} stale columns from validation_log")
