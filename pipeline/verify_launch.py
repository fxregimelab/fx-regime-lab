"""Post-run health check: desk_open_cards must exist for UTC today with regimes set."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any, cast

from dotenv import load_dotenv

from src.db.writer import _client


def main() -> int:
    load_dotenv()
    today = datetime.now(UTC).date()
    iso = today.isoformat()
    client = _client()
    res = (
        client.table("desk_open_cards")
        .select("pair,structural_regime")
        .eq("date", iso)
        .execute()
    )
    rows: list[dict[str, Any]] = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        print(f"verify_launch: FAIL — no desk_open_cards rows for {iso}", file=sys.stderr)
        return 1
    empty_pairs = [
        str(r.get("pair") or "?")
        for r in rows
        if not str(r.get("structural_regime") or "").strip()
    ]
    if empty_pairs:
        print(
            f"verify_launch: FAIL — empty structural_regime for: {empty_pairs} ({iso})",
            file=sys.stderr,
        )
        return 1
    print(f"verify_launch: OK — {len(rows)} desk row(s) for {iso}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
