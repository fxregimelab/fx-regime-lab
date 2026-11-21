"""Use actual central-writer envelopes to verify the read-only revision boundary."""

import copy
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.db.writer import archive_quote_capture, archive_quote_snapshot
from src.research.quote_capture import capture_quote_page
from src.research.quote_revision import reconcile_quote_snapshots


@pytest.mark.parametrize("pair,instrument", [
    ("EURUSD", "C:EUR-USD"), ("USDJPY", "C:USD-JPY"), ("USDINR", "C:USD-INR"),
])
def test_actual_writer_envelopes_reconcile_with_preserved_originals(
    pair: str, instrument: str,
) -> None:
    captured: dict[str, str] = {}
    snapshots: dict[str, dict[str, str]] = {}
    client = MagicMock()

    def rpc(name: str, parameters: dict[str, str]) -> MagicMock:
        unsigned = parameters["p_unsigned_json"]
        if name == "append_quote_capture":
            digest = parameters["p_capture_sha256"]
            inserted = digest not in captured
            if not inserted:
                assert captured[digest] == unsigned
            captured[digest] = unsigned
            receipt: dict[str, Any] = {"capture_sha256": digest, "inserted": inserted}
        else:
            assert name == "append_quote_snapshot"
            digest = parameters["p_snapshot_sha256"]
            document = json.loads(unsigned)
            hashes = document["reference"]["capture_sha256"]
            assert all(item in captured for item in hashes)
            envelope = {"snapshot_sha256": digest, "unsigned_json": unsigned}
            inserted = digest not in snapshots
            if not inserted:
                assert snapshots[digest] == envelope
            snapshots[digest] = envelope
            receipt = {"snapshot_sha256": digest, "inserted": inserted,
                       "capture_count": len(hashes)}
        return MagicMock(execute=lambda: MagicMock(data=receipt))

    client.rpc.side_effect = rpc
    stamp = datetime(2026, 5, 3, tzinfo=UTC)
    pages = []
    envelopes = []
    with patch("src.db.writer._client", return_value=client):
        for index, close in enumerate((b"1.2", b"1.3")):
            receipt_time = stamp + timedelta(days=index)
            body = (
                b'{"status":"OK","results":['
                b'{"participant_timestamp":1,"bid_price":1.1,"ask_price":1.1},'
                b'{"participant_timestamp":2,"bid_price":' + close + b',"ask_price":'
                + close + b'}]}'
            )
            page = capture_quote_page(
                pair=pair, instrument=instrument, window_start_ns=0,
                window_end_ns=86_400_000_000_000, page_index=0,
                requested_at=receipt_time, received_at=receipt_time,
                status_code=200, body=body, response_headers={},
                request_params={"timestamp.gte": "0", "timestamp.lt": "86400000000000",
                                "sort": "timestamp", "order": "asc", "limit": "50000"},
            )
            archive_quote_capture(page)
            receipt = archive_quote_snapshot(
                [page], as_of=receipt_time, implementation_sha256="a" * 64,
                client_version="synthetic-fixture-v1",
            )
            retry = archive_quote_snapshot(
                [page], as_of=receipt_time, implementation_sha256="a" * 64,
                client_version="synthetic-fixture-v1",
            )
            assert retry["inserted"] is False
            pages.append([page])
            envelopes.append(snapshots[receipt["snapshot_sha256"]])

    original = copy.deepcopy((captured, snapshots, pages, envelopes))
    calls_before = client.rpc.call_count
    result = reconcile_quote_snapshots(
        before=envelopes[0], before_pages=pages[0], after=envelopes[1], after_pages=pages[1],
        as_of=stamp + timedelta(days=2),
    )
    assert result["pair"] == pair
    assert result["comparable"] is True
    assert result["retained_occurrence_count"] == 1
    assert result["removed_occurrence_count"] == 1
    assert result["added_occurrence_count"] == 1
    assert len(result["changes"]) == 2
    assert result["reference_changes"] == {
        "close": {"before": "1.2", "after": "1.3"},
        "high": {"before": "1.2", "after": "1.3"},
    }
    assert result["event_lineage"] == "ambiguous"
    assert result["validation_eligible"] is False
    assert result["provider_finality"] == "unknown"
    assert (captured, snapshots, pages, envelopes) == original
    assert client.rpc.call_count == calls_before
    client.table.assert_not_called()
