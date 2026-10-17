"""Tests for the local desk store: append-only hash chain + refreshable bar cache."""

from __future__ import annotations

import json
from pathlib import Path

from src.paper.store import GENESIS_HASH, Bar, DeskStore


def _new_store(tmp_path: Path) -> DeskStore:
    return DeskStore(tmp_path / "paper_desk.sqlite3")


def _bar(t: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(
        symbol="EURUSDm",
        timeframe="D1",
        time_srv=t,
        open=o,
        high=h,
        low=lo,
        close=c,
        tick_volume=100,
        spread_points=8,
    )


def test_empty_store_verifies(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        status = store.verify_chain()
        assert status.ok
        assert status.rows == 0
        assert status.head_hash == GENESIS_HASH
        assert store.head() is None


def test_append_links_chain(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        r1 = store.append("note", {"text": "hello"})
        r2 = store.append("note", {"text": "world", "n": 2})
        assert (r1.seq, r2.seq) == (1, 2)
        assert r1.prev_hash == GENESIS_HASH
        assert r2.prev_hash == r1.row_hash
        assert r2.row_hash != r1.row_hash

        status = store.verify_chain()
        assert status.ok
        assert status.rows == 2
        assert status.head_hash == r2.row_hash

        head = store.head()
        assert head is not None
        assert head.seq == 2
        assert head.payload["n"] == 2


def test_rows_filter_and_since(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        store.append("note", {"i": 1})
        store.append("fill", {"i": 2})
        store.append("note", {"i": 3})
        assert [r.payload["i"] for r in store.rows(kind="note")] == [1, 3]
        assert [r.payload["i"] for r in store.rows(since_seq=1)] == [2, 3]
        assert [r.payload["i"] for r in store.rows(limit=2)] == [1, 2]


def test_tamper_payload_edit_detected(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        store.append("note", {"text": "a"})
        store.append("note", {"text": "b"})
        store.append("note", {"text": "c"})
        store._conn.execute(  # deliberate tamper
            "UPDATE ledger SET payload_json = ? WHERE seq = 2",
            ('{"text":"hacked"}',),
        )
        store._conn.commit()
        status = store.verify_chain()
        assert not status.ok
        assert status.first_bad_seq == 2


def test_tamper_row_deletion_detected(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        store.append("note", {"text": "a"})
        store.append("note", {"text": "b"})
        store.append("note", {"text": "c"})
        store._conn.execute("DELETE FROM ledger WHERE seq = 2")  # deliberate tamper
        store._conn.commit()
        status = store.verify_chain()
        assert not status.ok
        assert status.first_bad_seq == 3  # seq gap detected at the next row


def test_bar_cache_upsert_and_query(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        store.upsert_bars([_bar(1_700_000_000, 1.05, 1.06, 1.04, 1.055)])
        store.upsert_bars(
            [
                _bar(1_700_000_000, 1.05, 1.065, 1.04, 1.055),  # refresh: same bar time
                _bar(1_700_086_400, 1.055, 1.07, 1.05, 1.065),
            ]
        )
        bars = store.bars("EURUSDm", "D1")
        assert [b.close for b in bars] == [1.055, 1.065]
        assert len(bars) == 2  # upsert refreshed, no duplicates

        stats = store.bar_stats()
        assert stats == [
            {
                "symbol": "EURUSDm",
                "timeframe": "D1",
                "n": 2,
                "first_srv": 1_700_000_000,
                "last_srv": 1_700_086_400,
            }
        ]
        # the bar cache is not part of the immutable ledger
        assert store.verify_chain().rows == 0


def test_export_receipt(tmp_path: Path) -> None:
    with _new_store(tmp_path) as store:
        store.append("note", {"text": "hi"})
        store.append("note", {"text": "later"})
        out = tmp_path / "receipts"
        path = store.export_receipt(out_dir=out, since_seq=1, label="test")
        assert path.parent == out
        assert path.name.startswith("receipt_")
        assert path.name.endswith("_test.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["chain"]["ok"] is True
        assert data["chain"]["rows"] == 2
        assert data["since_seq"] == 1
        assert [r["payload"]["text"] for r in data["rows"]] == ["later"]
