"""Append-only local ledger + market-data cache for the personal paper desk.

Private local state for the desk (never rendered publicly). Two stores share one
SQLite file:

- ``ledger`` - the immutable, hash-chained record of desk events (order
  proposals/approvals, fills, position opens/settlements, equity marks, notes).
  Rows are append-only; each row's ``row_hash`` chains the previous row, so any
  payload edit, deletion, or reorder breaks ``verify_chain()``. Limitation:
  truncating the *last* row(s) cannot be detected from the file alone - exported
  receipts (with the head hash) are the external witness.
- ``bars`` - a *refreshable cache* of broker OHLC bars (NOT part of the
  immutable ledger; rows are upserted on refresh).

Default location: ``data/desk/paper_desk.sqlite3`` (gitignored). Receipts are
exported as JSON to ``reports/desk/`` (committed). Single-process use only.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = _REPO_ROOT / "data" / "desk" / "paper_desk.sqlite3"
DEFAULT_RECEIPTS_DIR = _REPO_ROOT / "reports" / "desk"

GENESIS_HASH = "0" * 64

# Ledger event-kind vocabulary (storage accepts any string; these are the desk's).
KIND_ORDER_PROPOSED = "order_proposed"
KIND_ORDER_APPROVED = "order_approved"
KIND_FILL = "fill"
KIND_POSITION_OPEN = "position_open"
KIND_POSITION_SETTLE = "position_settle"
KIND_EQUITY_MARK = "equity_mark"
KIND_NOTE = "note"


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Deterministic JSON encoding used for hashing (sorted keys, no spaces)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _compute_row_hash(seq: int, ts_utc: str, kind: str, payload_json: str, prev_hash: str) -> str:
    material = f"{seq}|{ts_utc}|{kind}|{payload_json}|{prev_hash}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LedgerRow:
    """One appended ledger row (payload parsed for convenience, raw text kept)."""

    seq: int
    ts_utc: str
    kind: str
    payload: dict[str, Any]
    payload_json: str
    prev_hash: str
    row_hash: str


@dataclass(frozen=True)
class ChainStatus:
    ok: bool
    rows: int
    head_hash: str
    first_bad_seq: int | None = None


@dataclass(frozen=True)
class Bar:
    """One OHLC bar from the broker feed.

    ``time_srv`` is the MT5 *server-time* epoch in seconds (the epoch of the
    server wall clock, not true UTC). ``spread_points`` is the broker-reported
    spread in points for the bar.
    """

    symbol: str
    timeframe: str
    time_srv: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0
    spread_points: int = 0


def _to_ledger_row(row: sqlite3.Row) -> LedgerRow:
    payload_json = str(row["payload_json"])
    return LedgerRow(
        seq=int(row["seq"]),
        ts_utc=str(row["ts_utc"]),
        kind=str(row["kind"]),
        payload=json.loads(payload_json),
        payload_json=payload_json,
        prev_hash=str(row["prev_hash"]),
        row_hash=str(row["row_hash"]),
    )


def _to_bar(row: sqlite3.Row) -> Bar:
    return Bar(
        symbol=str(row["symbol"]),
        timeframe=str(row["timeframe"]),
        time_srv=int(row["time_srv"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        tick_volume=int(row["tick_volume"]),
        spread_points=int(row["spread_points"]),
    )


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


class DeskStore:
    """SQLite-backed local desk store (single-process use)."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> DeskStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- schema -------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger (
                    seq          INTEGER PRIMARY KEY,
                    ts_utc       TEXT NOT NULL,
                    kind         TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    prev_hash    TEXT NOT NULL,
                    row_hash     TEXT NOT NULL UNIQUE
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bars (
                    symbol        TEXT NOT NULL,
                    timeframe     TEXT NOT NULL,
                    time_srv      INTEGER NOT NULL,
                    open          REAL NOT NULL,
                    high          REAL NOT NULL,
                    low           REAL NOT NULL,
                    close         REAL NOT NULL,
                    tick_volume   INTEGER NOT NULL,
                    spread_points INTEGER NOT NULL,
                    PRIMARY KEY (symbol, timeframe, time_srv)
                )
                """
            )

    # --- ledger (append-only, hash-chained) ---------------------------------

    def append(self, kind: str, payload: Mapping[str, Any], ts_utc: str | None = None) -> LedgerRow:
        """Append one immutable row; returns the row including its hash."""
        ts = ts_utc or datetime.now(UTC).isoformat(timespec="microseconds")
        payload_json = canonical_json(payload)
        with self._conn:
            head = self._head_row()
            seq = head["seq"] + 1 if head is not None else 1
            prev_hash = head["row_hash"] if head is not None else GENESIS_HASH
            row_hash = _compute_row_hash(seq, ts, kind, payload_json, prev_hash)
            self._conn.execute(
                "INSERT INTO ledger (seq, ts_utc, kind, payload_json, prev_hash, row_hash)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (seq, ts, kind, payload_json, prev_hash, row_hash),
            )
        return LedgerRow(
            seq=seq,
            ts_utc=ts,
            kind=kind,
            payload=dict(payload),
            payload_json=payload_json,
            prev_hash=prev_hash,
            row_hash=row_hash,
        )

    def _head_row(self) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT seq, row_hash FROM ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row is not None else None

    def head(self) -> LedgerRow | None:
        row = self._conn.execute("SELECT * FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return _to_ledger_row(row) if row is not None else None

    def rows(
        self,
        kind: str | None = None,
        since_seq: int = 0,
        limit: int | None = None,
    ) -> list[LedgerRow]:
        sql = "SELECT * FROM ledger WHERE seq > ?"
        params: list[Any] = [since_seq]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        sql += " ORDER BY seq"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        return [_to_ledger_row(r) for r in self._conn.execute(sql, params).fetchall()]

    def verify_chain(self) -> ChainStatus:
        """Recompute the hash chain; detects payload edits, deletions, reorders."""
        rows = self._conn.execute(
            "SELECT seq, ts_utc, kind, payload_json, prev_hash, row_hash"
            " FROM ledger ORDER BY seq"
        ).fetchall()
        prev_hash = GENESIS_HASH
        expected_seq = 1
        for row in rows:
            seq = int(row["seq"])
            if seq != expected_seq or str(row["prev_hash"]) != prev_hash:
                return ChainStatus(
                    ok=False, rows=len(rows), head_hash=prev_hash, first_bad_seq=seq
                )
            expected = _compute_row_hash(
                seq,
                str(row["ts_utc"]),
                str(row["kind"]),
                str(row["payload_json"]),
                str(row["prev_hash"]),
            )
            if expected != str(row["row_hash"]):
                return ChainStatus(
                    ok=False, rows=len(rows), head_hash=prev_hash, first_bad_seq=seq
                )
            prev_hash = str(row["row_hash"])
            expected_seq += 1
        return ChainStatus(ok=True, rows=len(rows), head_hash=prev_hash)

    def export_receipt(
        self,
        out_dir: Path | None = None,
        since_seq: int = 0,
        label: str = "ledger",
    ) -> Path:
        """Write a JSON receipt (chain status + ledger rows since ``since_seq``)."""
        out = Path(out_dir) if out_dir is not None else DEFAULT_RECEIPTS_DIR
        out.mkdir(parents=True, exist_ok=True)
        status = self.verify_chain()
        head = self.head()
        rows = self.rows(since_seq=since_seq)
        now = datetime.now(UTC)
        receipt = {
            "exported_at_utc": now.isoformat(timespec="seconds"),
            "db_path": _display_path(self.db_path),
            "chain": {
                "ok": status.ok,
                "rows": status.rows,
                "head_seq": head.seq if head is not None else 0,
                "head_hash": status.head_hash,
                "first_bad_seq": status.first_bad_seq,
            },
            "since_seq": since_seq,
            "rows": [
                {
                    "seq": r.seq,
                    "ts_utc": r.ts_utc,
                    "kind": r.kind,
                    "payload": r.payload,
                    "row_hash": r.row_hash,
                }
                for r in rows
            ],
        }
        path = out / f"receipt_{now.strftime('%Y%m%dT%H%M%SZ')}_{label}.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    # --- bar cache (refreshable, NOT part of the ledger) --------------------

    def upsert_bars(self, bars: Sequence[Bar]) -> int:
        """Insert or refresh bars; returns the number of rows written."""
        if not bars:
            return 0
        with self._conn:
            self._conn.executemany(
                "INSERT INTO bars (symbol, timeframe, time_srv, open, high, low, close,"
                " tick_volume, spread_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (symbol, timeframe, time_srv) DO UPDATE SET"
                " open = excluded.open, high = excluded.high, low = excluded.low,"
                " close = excluded.close, tick_volume = excluded.tick_volume,"
                " spread_points = excluded.spread_points",
                [
                    (
                        b.symbol,
                        b.timeframe,
                        b.time_srv,
                        b.open,
                        b.high,
                        b.low,
                        b.close,
                        b.tick_volume,
                        b.spread_points,
                    )
                    for b in bars
                ],
            )
        return len(bars)

    def bars(
        self,
        symbol: str,
        timeframe: str,
        start_srv: int | None = None,
        end_srv: int | None = None,
    ) -> list[Bar]:
        sql = "SELECT * FROM bars WHERE symbol = ? AND timeframe = ?"
        params: list[Any] = [symbol, timeframe]
        if start_srv is not None:
            sql += " AND time_srv >= ?"
            params.append(start_srv)
        if end_srv is not None:
            sql += " AND time_srv <= ?"
            params.append(end_srv)
        sql += " ORDER BY time_srv"
        return [_to_bar(r) for r in self._conn.execute(sql, params).fetchall()]

    def bar_stats(self) -> list[dict[str, Any]]:
        """Per (symbol, timeframe): bar count and first/last server-time epoch."""
        rows = self._conn.execute(
            "SELECT symbol, timeframe, COUNT(*) AS n, MIN(time_srv) AS first_srv,"
            " MAX(time_srv) AS last_srv FROM bars GROUP BY symbol, timeframe"
            " ORDER BY symbol, timeframe"
        ).fetchall()
        return [dict(r) for r in rows]
