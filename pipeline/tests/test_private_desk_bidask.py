"""Adverse archive, cache and cohort controls; all requests use bounded fixtures."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import requests

from src.private_desk import bidask
from src.private_desk.report import atomic_json

WEEK = "2025-W40"
RECEIVED = "2026-10-01T00:00:00+00:00"
ROW = "09/28/2025 21:00:00.000,1,1.1,0.9,1.05,1.0001,1.1001,0.9001,1.0501"


def archive(rows: list[str] | None = None, header: tuple[str, ...] = bidask.HEADER) -> bytes:
    return gzip.compress((",".join(header) + "\n" + "\n".join(rows or [ROW]) + "\n").encode())


class Response:
    status_code = 200

    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status_code = status

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_args: Any) -> None:
        pass

    def iter_content(self, size: int) -> Any:
        for offset in range(0, len(self.body), size):
            yield self.body[offset : offset + size]


def capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: bytes | None = None, status: int = 200
) -> dict[str, Any]:
    def get(url: str, **kwargs: Any) -> Response:
        assert url == bidask.source_url("EURUSD", WEEK)
        assert kwargs == {"stream": True, "allow_redirects": False, "timeout": (10, 30)}
        return Response(body if body is not None else archive(), status)

    monkeypatch.setattr(requests, "get", get)
    return bidask.capture_week("EURUSD", WEEK, tmp_path, refresh=True)


def test_valid_original_quotes_and_clock() -> None:
    rows = bidask.parse_archive(archive(), WEEK, RECEIVED)
    assert rows[0][0] == datetime(2025, 9, 28, 21, tzinfo=UTC)
    assert rows[0][1:] == (1, 1.1, 0.9, 1.05, 1.0001, 1.1001, 0.9001, 1.0501)


def test_empty_and_invalid_gzip_are_rejected() -> None:
    with pytest.raises(ValueError, match="Empty"):
        bidask.parse_archive(
            gzip.compress((",".join(bidask.HEADER) + "\n").encode()), WEEK, RECEIVED
        )
    with pytest.raises(OSError):
        bidask.parse_archive(b"not gzip", WEEK, RECEIVED)


@pytest.mark.parametrize(
    "row",
    [
        ROW.replace("1.0001", "0.9999"),
        ROW.replace("1.1001", "1.0999"),
        ROW.replace("0.9001", "0.8999"),
        ROW.replace("1.0501", "1.0499"),
        ROW.replace(",1,", ",nan,"),
        ROW.replace(",1,", ",inf,"),
        ROW.replace(",1,", ",0,"),
        ROW.replace(",1,", ",-1,"),
        ROW.replace(",1,", ",1.2,"),
        ROW.replace("21:00:00", "21:00:01"),
        ROW.replace(".000,", ".001,"),
        ROW.replace(".000,", ".000000,"),
        ROW.replace("09/28", "09/27"),
        ROW.replace("09/28", "10/05"),
        ROW.replace("09/28/2025", "28/09/2025"),
        ROW + ",1",
        ROW.rsplit(",", 1)[0],
    ],
)
def test_bad_observation_rejects_entire_archive(row: str) -> None:
    with pytest.raises(ValueError):
        bidask.parse_archive(archive([row]), WEEK, RECEIVED)


@pytest.mark.parametrize("rows", [[ROW, ROW], [ROW.replace("21:00", "21:01"), ROW]])
def test_duplicates_and_reversed_archive_fail(rows: list[str]) -> None:
    with pytest.raises(ValueError, match="Non-increasing"):
        bidask.parse_archive(archive(rows), WEEK, RECEIVED)


def test_future_receipt_unknown_header_and_non_utc_fail() -> None:
    with pytest.raises(ValueError):
        bidask.parse_archive(archive(), WEEK, "2025-09-28T20:59:00+00:00")
    with pytest.raises(ValueError, match="UTC"):
        bidask.parse_archive(archive(), WEEK, "2026-10-01T00:00:00+05:30")
    with pytest.raises(ValueError, match="header"):
        bidask.parse_archive(archive(header=("Date", *bidask.HEADER[1:])), WEEK, RECEIVED)


def test_compressed_and_expanded_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bidask, "MAX_COMPRESSED", 20)
    with pytest.raises(ValueError, match="Compressed"):
        bidask.parse_archive(archive(), WEEK, RECEIVED)
    monkeypatch.setattr(bidask, "MAX_COMPRESSED", 2000)
    monkeypatch.setattr(bidask, "MAX_EXPANDED", 30)
    with pytest.raises(ValueError, match="Expanded"):
        bidask.parse_archive(archive(), WEEK, RECEIVED)


def test_cache_reuse_is_offline_and_corruption_does_not_refetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = capture(tmp_path, monkeypatch)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("Cache reuse attempted a request")

    monkeypatch.setattr(requests, "get", forbidden)
    assert bidask.capture_week("EURUSD", WEEK, tmp_path) == saved
    Path(saved["capture_path"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="hash"):
        bidask.capture_week("EURUSD", WEEK, tmp_path)


def test_cache_request_mismatch_and_transport_failure_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = capture(tmp_path, monkeypatch)
    atomic_json(tmp_path / "GBPUSD-2025-W40.json", saved["receipt_file"])
    with pytest.raises(ValueError, match="Cache request"):
        bidask.capture_week("GBPUSD", WEEK, tmp_path)

    def timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise requests.Timeout("test-only sensitive request details")

    monkeypatch.setattr(requests, "get", timeout)
    failed = bidask.capture_week("EURUSD", WEEK, tmp_path, refresh=True)
    assert failed["http_status"] is None
    assert failed["body_complete"] is False
    assert failed["transport_error"] == "Timeout"
    assert "sensitive" not in json.dumps(failed)
    assert Path(failed["capture_path"]).read_bytes() == b""


def test_receipt_path_hash_and_request_identity_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = capture(tmp_path, monkeypatch)
    reference = saved["receipt_file"]
    with pytest.raises(ValueError, match="outside"):
        bidask.read_receipt(tmp_path / "other", reference)
    with pytest.raises(ValueError, match="Receipt hash"):
        bidask.read_receipt(tmp_path, {**reference, "sha256": "0" * 64})
    path = Path(reference["capture_path"])
    record = json.loads(path.read_text())
    record["url"] = "https://example.com/wrong"
    atomic_json(path, record)
    reference["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="identity"):
        bidask.read_receipt(tmp_path, reference)


def test_failed_and_oversize_bodies_preserved_without_observation_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = capture(tmp_path, monkeypatch, b"source error", 404)
    assert Path(failed["capture_path"]).read_bytes() == b"source error"
    assert bidask.audit_pair("EURUSD", [failed], tmp_path)["status"] == "UNAVAILABLE"
    monkeypatch.setattr(bidask, "MAX_COMPRESSED", 30)
    oversized = capture(tmp_path, monkeypatch, b"x" * 50)
    assert oversized["body_complete"] is False
    assert oversized["bytes"] == 30
    assert Path(failed["capture_path"]).exists()
    assert "observed_minutes" not in bidask.audit_pair("EURUSD", [oversized], tmp_path)


def test_equal_duplicate_union_and_conflict_reject_whole_cohort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = capture(tmp_path, monkeypatch)
    equal = capture(tmp_path, monkeypatch)
    result = bidask.audit_pair("EURUSD", [first, equal], tmp_path)
    assert result["observed_minutes"] == 1
    assert result["equal_duplicates"] == 1
    assert result["proxy_expected_minutes"] == 7200
    assert result["proxy_missing_minutes"] == 7199
    assert result["missing_ranges"][0]["minutes"] == 7199
    assert result["side_open_close_difference_pips"]["mean"] == 1
    conflict = capture(tmp_path, monkeypatch, archive([ROW.replace(",1,", ",1.01,")]))
    rejected = bidask.audit_pair("EURUSD", [first, conflict], tmp_path)
    assert rejected["status"] == "UNAVAILABLE"
    assert "observed_minutes" not in rejected


def test_archive_defect_is_not_silently_quarantined_by_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = ROW.replace("21:00", "21:01").replace("1.0001", "0.9999")
    record = capture(tmp_path, monkeypatch, archive([ROW, bad]))
    result = bidask.audit_pair("EURUSD", [record], tmp_path)
    assert result["status"] == "UNAVAILABLE"
    assert "Crossed side bounds" in result["failures"][0]
    assert "observed_minutes" not in result


def test_saved_audit_replays_and_tampered_statistics_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = capture(tmp_path, monkeypatch)
    item = bidask.audit_pair("EURUSD", [record], tmp_path)
    saved = {"schema_version": "private-bidask-v1", "pair_audits": [item]}
    atomic_json(tmp_path / "evidence.json", saved)
    assert bidask.load_evidence(tmp_path) == {"EURUSD": item}
    item["proxy_missing_minutes"] = 0
    atomic_json(tmp_path / "evidence.json", saved)
    with pytest.raises(ValueError, match="reproduce"):
        bidask.load_evidence(tmp_path)


def test_week_boundaries_and_dst_proxy() -> None:
    assert bidask.week_identity("2020-W53")[2].isoformat().startswith("2020-12-27")
    with pytest.raises(ValueError):
        bidask.week_identity("2021-W53")
    assert min(bidask.expected_minutes("2025-W10")).hour == 22
    assert min(bidask.expected_minutes("2025-W11")).hour == 21
    assert len(bidask.expected_minutes("2025-W11")) == 7200


@pytest.mark.parametrize(
    "weeks,pairs",
    [
        ([], ["EURUSD"]),
        ([WEEK] * 2, ["EURUSD"]),
        ([WEEK] * 13, ["EURUSD"]),
        ([WEEK], ["USDINR"]),
        ([WEEK], ["EURUSD"] * 2),
        (["2025-W99"], ["EURUSD"]),
    ],
)
def test_invalid_requests_fail_before_any_network(
    tmp_path: Path, weeks: list[str], pairs: list[str]
) -> None:
    with pytest.raises(ValueError):
        bidask.capture_cohort(tmp_path, weeks, pairs)
