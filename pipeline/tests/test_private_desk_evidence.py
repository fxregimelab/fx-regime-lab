"""Bounded, replayable central-bank evidence capture tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import requests

from src.private_desk import evidence

ARTICLE = b"""<!doctype html><html><head><title>Policy decision</title></head><body>
<main><h1>Policy decision</h1>
<p>The central bank maintained its policy rate after reviewing inflation and activity.</p>
<p>Officials said future decisions would depend on incoming data and the outlook.</p>
<p>Prices rose by 2.5 percent, while the labour market remained resilient.</p>
</main></body></html>"""


class FakeResponse:
    def __init__(
        self,
        body: bytes = ARTICLE,
        *,
        status: int = 200,
        content_type: str = "text/html; charset=utf-8",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status
        self.headers = {"Content-Type": content_type, **(headers or {})}
        self._body = body
        self.closed = False

    def iter_content(self, chunk_size: int) -> Any:
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset : offset + chunk_size]

    def close(self) -> None:
        self.closed = True


def _capture(monkeypatch: pytest.MonkeyPatch, root: Path, response: FakeResponse) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    receipt = evidence.capture_evidence(
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "Federal Reserve",
        root,
        publication="2026-09-16T18:00:00Z",
    )
    assert calls == [
        {
            "url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
            "allow_redirects": False,
            "stream": True,
            "timeout": evidence.REQUEST_TIMEOUT_SECONDS,
            "headers": {"User-Agent": evidence.USER_AGENT},
        }
    ]
    return receipt


@pytest.mark.parametrize(
    ("url", "source", "code"),
    [
        ("https://www.federalreserve.gov.evil.test/x", "Federal Reserve", "UNTRUSTED_HOST"),
        ("https://user@www.federalreserve.gov/x", "Federal Reserve", "URL_USERINFO"),
        ("https://www.federalreserve.gov:444/x", "Federal Reserve", "NONSTANDARD_PORT"),
        ("http://www.federalreserve.gov/x", "Federal Reserve", "HTTPS_REQUIRED"),
        ("https://www.federalreserve.gov/x", "European Central Bank", "SOURCE_HOST_MISMATCH"),
    ],
)
def test_url_boundary_fails_before_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    url: str,
    source: str,
    code: str,
) -> None:
    def no_network(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("network should not be called")

    monkeypatch.setattr(requests, "get", no_network)
    receipt = evidence.capture_evidence(url, source, tmp_path)
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"]["code"] == code
    assert Path(tmp_path, receipt["receipt_path"]).is_file()


def test_redirect_is_visible_and_not_followed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    response = FakeResponse(b"redirect", status=302, headers={"Location": "https://evil.test/"})
    receipt = _capture(monkeypatch, tmp_path, response)
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"]["code"] == "REDIRECT_REJECTED"
    assert receipt["raw"]["bytes"] == 8


def test_oversized_body_is_stopped_and_recorded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = b"a" * (evidence.MAX_BODY_BYTES + 1)
    receipt = _capture(monkeypatch, tmp_path, FakeResponse(body))
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"]["code"] == "BODY_TOO_LARGE"
    assert receipt["raw"]["bytes"] <= evidence.MAX_BODY_BYTES


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (
            b"<html><title>Access denied</title><main><p>Complete the CAPTCHA.</p></main></html>",
            "CHALLENGE_PAGE",
        ),
        (b"<html><body><nav>Policy links only</nav></body></html>", "ARTICLE_NOT_FOUND"),
        (b"<html><main><p>Short.</p></main></html>", "INSUFFICIENT_ARTICLE_TEXT"),
    ],
)
def test_invalid_extraction_is_visible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: bytes, code: str
) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse(body))
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"]["code"] == code
    assert receipt["raw"] is not None
    assert receipt["text"] is None


def test_capture_and_replay_bind_raw_text_spans_and_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    before = datetime.now(UTC)
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    after = datetime.now(UTC)

    assert receipt["status"] == "AVAILABLE"
    fetched = datetime.fromisoformat(receipt["received_at"])
    assert before <= fetched <= after
    assert receipt["publication"] == {
        "value": "2026-09-16T18:00:00Z",
        "basis": "SUPPLIED_PUBLISHER_FEED_CLAIM",
        "article_verified": False,
    }
    assert receipt["arrival_basis"] == "POST_FETCH_UTC_RECEIPT"
    assert receipt["vintage"] == "UNKNOWN"
    assert receipt["model_calls"] == "PROHIBITED"
    verified = evidence.verify_evidence(receipt, tmp_path)
    assert verified["text"].startswith("Policy decision")
    assert verified["spans"] == receipt["spans"]
    assert all(span["offset_basis"] == "UTF8_EXTRACTED_TEXT" for span in verified["spans"])

    receipt_file = Path(tmp_path, receipt["receipt_path"])
    assert json.loads(receipt_file.read_text(encoding="utf-8")) == receipt
    with pytest.raises(FileExistsError):
        evidence._write_new(receipt_file, b"replacement")


def test_utf8_span_offsets_are_exact_and_stable() -> None:
    text = "Policy stayed unchanged — inflation eased.\n\nCafé prices rose 2%."
    first = evidence.derive_spans(text)
    second = evidence.derive_spans(text)
    assert first == second
    raw = text.encode("utf-8")
    for span in first:
        assert raw[span["start"] : span["end"]].decode("utf-8") == span["text"]


@pytest.mark.parametrize("target", ["raw", "text", "spans"])
def test_replay_rejects_hash_or_span_tampering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, target: str
) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    tampered = json.loads(json.dumps(receipt))
    if target == "raw":
        raw_path = Path(tmp_path, receipt["raw"]["path"])
        raw_path.chmod(0o644)
        raw_path.write_bytes(b"changed")
    elif target == "text":
        tampered["text"]["sha256"] = "0" * 64
    else:
        tampered["spans"][0]["end"] -= 1
    with pytest.raises(ValueError):
        evidence.verify_evidence(tampered, tmp_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "https://www.federalreserve.gov/another-approved-path.htm"),
        (
            "publication",
            {
                "value": "1999-01-01",
                "basis": "SUPPLIED_PUBLISHER_FEED_CLAIM",
                "article_verified": False,
            },
        ),
        (
            "http",
            {
                "status_code": 201,
                "content_type": "text/html; charset=utf-8",
                "declared_content_length": None,
            },
        ),
        ("model_calls", "ALLOWED"),
        ("received_at", "2099-01-01T00:00:00+00:00"),
    ],
)
def test_replay_rejects_receipt_metadata_tampering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: Any
) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    tampered = json.loads(json.dumps(receipt))
    tampered[field] = value
    with pytest.raises(ValueError, match="immutable receipt"):
        evidence.verify_evidence(tampered, tmp_path)


def test_replay_rejects_path_escape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    tampered = json.loads(json.dumps(receipt))
    tampered["raw"]["path"] = "../outside.html"
    with pytest.raises(ValueError):
        evidence.verify_evidence(tampered, tmp_path)


def test_bad_clock_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    tampered = json.loads(json.dumps(receipt))
    tampered["received_at"] = "2026-09-16T18:00:00"
    with pytest.raises(ValueError):
        evidence.verify_evidence(tampered, tmp_path)


def test_replay_rejects_oversized_raw_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    receipt = _capture(monkeypatch, tmp_path, FakeResponse())
    raw_path = Path(tmp_path, receipt["raw"]["path"])
    raw_path.chmod(0o644)
    raw_path.write_bytes(b"x" * (evidence.MAX_BODY_BYTES + 1))
    with pytest.raises(ValueError, match="raw source"):
        evidence.verify_evidence(receipt, tmp_path)


def test_partial_stream_failure_preserves_observed_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    response = FakeResponse()

    def broken_stream(chunk_size: int) -> Any:
        yield b"<html><main><p>observed partial bytes</p>"
        raise requests.ConnectionError("stream ended")

    response.iter_content = broken_stream  # type: ignore[method-assign]
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    receipt = evidence.capture_evidence(
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
        "Federal Reserve",
        tmp_path,
    )
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"] == {"code": "FETCH_FAILED"}
    assert receipt["raw"]["bytes"] == len(b"<html><main><p>observed partial bytes</p>")
    assert Path(tmp_path, receipt["raw"]["path"]).read_bytes().endswith(b"bytes</p>")
    assert response.closed is True


def test_network_failure_has_immutable_visible_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise requests.Timeout("private detail")

    monkeypatch.setattr(requests, "get", fail)
    receipt = evidence.capture_evidence(
        "https://www.rba.gov.au/media-releases/2026/mr-26-28.html",
        "Reserve Bank of Australia",
        tmp_path,
    )
    assert receipt["status"] == "UNAVAILABLE"
    assert receipt["failure"] == {"code": "FETCH_FAILED"}
    assert Path(tmp_path, receipt["receipt_path"]).is_file()
