"""Read-only ledger snapshot for append-only proof (fx-live-personal).

SELECT-only. Never imports ``src.db.writer``. Never writes to the database.
Loads credentials from repo-root ``.env.local`` without printing values.
Output JSON contains counts + SHA-256 hashes only (no secrets).

Usage (from ``pipeline/``):
    python scripts/ledger_snapshot.py --out ../reports/ledger_snapshot_before.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))


def _load_env_local() -> None:
    path = REPO_ROOT / ".env.local"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export ") :].strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip('"').strip("'")


def _client() -> Any:  # lazy import, read-only use only
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key.strip():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(url, key)


def _canon(rows: list[dict[str, Any]]) -> str:
    lines = [json.dumps(r, sort_keys=True, ensure_ascii=True, default=str) for r in rows]
    return "\n".join(sorted(lines))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_all(client: Any, table: str, columns: str) -> tuple[list[dict[str, Any]], int]:
    """Paginated SELECT (Supabase caps rows per request); returns (rows, exact_count)."""
    exact = (
        client.table(table).select("id", count="exact").limit(0).execute()
    )
    total = int(exact.count or 0)
    rows: list[dict[str, Any]] = []
    chunk = 1000
    for offset in range(0, total, chunk):
        res = (
            client.table(table)
            .select(columns)
            .range(offset, offset + chunk - 1)
            .execute()
        )
        rows.extend(res.data or [])
        if len(res.data or []) < chunk:
            break
    return rows, total


def snapshot() -> dict[str, Any]:
    client = _client()

    call_rows, call_exact = _fetch_all(
        client,
        "regime_calls",
        "pair,date,regime,confidence,signal_composite,model_version",
    )
    call_rows.sort(key=lambda r: (str(r.get("pair")), str(r.get("date"))))

    val_all, _ = _fetch_all(
        client,
        "validation_log",
        "call_date,pair,brier_score_t5,brier_score_t20,is_superseded",
    )
    val_rows = [r for r in val_all if r.get("is_superseded") is False]
    val_rows.sort(key=lambda r: (str(r.get("call_date")), str(r.get("pair"))))

    latest: dict[str, str] = {}
    for r in call_rows:
        pair = str(r.get("pair"))
        d = str(r.get("date"))
        if pair not in latest or d > latest[pair]:
            latest[pair] = d

    return {
        "regime_calls": {
            "count": call_exact,
            "hashed_rows": len(call_rows),
            "sha256": _sha(_canon(call_rows)),
        },
        "validation_log": {
            "count": len(val_rows),
            "sha256": _sha(_canon(val_rows)),
        },
        "latest_call_date_per_pair": latest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only ledger snapshot")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()
    _load_env_local()
    result = snapshot()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"regime_calls count={result['regime_calls']['count']}")  # counts only
    print(f"validation_log count={result['validation_log']['count']}")  # counts only
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
