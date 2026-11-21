"""Retired unqualified FPI adapter; see docs/FPI_OBSERVATION_CONTRACT.md.

The former SEBI endpoint and guessed table layout were not a verified source.
Parsing helpers remain for compatibility, not source qualification.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any


def _parse_inr_crores(text: str) -> float | None:
    """Parse strings like '1,234.56' or '-1,234.56 Cr' to float."""
    cleaned = text.replace(",", "").replace("Cr", "").strip()
    # Handle parentheses for negative numbers: (1,234.56)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        value = float(cleaned)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def _parse_sebi_date(text: str) -> date | None:
    """Parse SEBI date formats like '15-May-2026'."""
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text.strip()):
            return date.fromisoformat(text.strip())
    except ValueError:
        pass
    # Try DD-Mon-YYYY
    match = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", text.strip())
    if match:
        day, mon, year = match.groups()
        months = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }
        if mon in months:
            try:
                return date(int(year), months[mon], int(day))
            except ValueError:
                return None
    return None


def fetch_fpi_flows(target_date: date | None = None) -> dict[str, Any] | None:
    """Reject the retired source before any network or persistence operation."""
    raise RuntimeError("Unqualified FPI source is retired; dated NSDL evidence required")


def fetch_fpi_history(start_date: date, end_date: date) -> list[dict[str, Any]]:
    """Reject the former repeated-current-page pseudo-history."""
    raise RuntimeError("Unqualified FPI source is retired; dated NSDL evidence required")


if __name__ == "__main__":
    raise SystemExit("Unqualified FPI source is retired; no request was made")
