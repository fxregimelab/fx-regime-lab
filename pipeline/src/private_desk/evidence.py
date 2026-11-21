"""Immutable, replay-verifiable captures from approved central-bank publishers."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

MAX_BODY_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = (5.0, 20.0)
USER_AGENT = "FX-Regime-Lab-Evidence/1.0 (+bounded research capture)"
OFFSET_BASIS = "UTF8_EXTRACTED_TEXT"
MAX_SPAN_BYTES = 1_200

_PUBLISHERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Federal Reserve": (
        "www.federalreserve.gov",
        ("#article", "#content .col-xs-12.col-sm-8.col-md-8", "main", "article"),
    ),
    "European Central Bank": (
        "www.ecb.europa.eu",
        ("main", ".ecb-pressContent", "#main-wrapper", "article"),
    ),
    "Bank of England": (
        "www.bankofengland.co.uk",
        ("main", "#main-content", ".page-content", "article"),
    ),
    "Reserve Bank of Australia": (
        "www.rba.gov.au",
        ("#content", "main", "article"),
    ),
    "Reserve Bank of New Zealand": (
        "www.rbnz.govt.nz",
        ("main", "#main-content", "article"),
    ),
    "Bank of Canada": (
        "www.bankofcanada.ca",
        ("main", "#content", "article"),
    ),
    "Swiss National Bank": (
        "www.snb.ch",
        ("main", "#main-content", "article"),
    ),
}
_CHALLENGE_MARKERS = (
    "access denied",
    "captcha",
    "verify you are human",
    "checking your browser",
    "cloudflare ray id",
    "sign in to continue",
    "log in to continue",
)
_SPACE = re.compile(r"[ \t\f\v]+")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _publisher(url: str, source: str) -> tuple[str | None, tuple[str, ...] | None, str | None]:
    publisher = _PUBLISHERS.get(source)
    if publisher is None:
        return None, None, "UNSUPPORTED_SOURCE"
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None, None, "INVALID_URL"
    if parts.scheme.lower() != "https":
        return None, None, "HTTPS_REQUIRED"
    if parts.username is not None or parts.password is not None:
        return None, None, "URL_USERINFO"
    if port not in (None, 443):
        return None, None, "NONSTANDARD_PORT"
    if not parts.hostname:
        return None, None, "INVALID_URL"
    host, selectors = publisher
    if parts.hostname.lower().rstrip(".") != host:
        if parts.hostname.lower().rstrip(".") in {item[0] for item in _PUBLISHERS.values()}:
            return None, None, "SOURCE_HOST_MISMATCH"
        return None, None, "UNTRUSTED_HOST"
    if parts.fragment:
        return None, None, "URL_FRAGMENT"
    return host, selectors, None


def _safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("receipt path must be a non-empty relative path")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("receipt path escapes evidence root") from exc
    return resolved


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _decode_html(raw: bytes, content_type: str) -> str:
    match = re.search(r"charset\s*=\s*['\"]?([^;\s'\"]+)", content_type, re.IGNORECASE)
    charset = match.group(1).lower() if match else "utf-8"
    if charset not in {"utf-8", "utf8", "us-ascii", "ascii"}:
        raise ValueError("UNSUPPORTED_ENCODING")
    try:
        return raw.decode("utf-8" if charset in {"utf-8", "utf8"} else "ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("INVALID_ENCODING") from exc


def _extract_article(raw: bytes, content_type: str, selectors: tuple[str, ...]) -> tuple[str, str]:
    html = _decode_html(raw, content_type)
    soup = BeautifulSoup(html, "html.parser")
    probe = " ".join(soup.stripped_strings).lower()[:4_000]
    if any(marker in probe for marker in _CHALLENGE_MARKERS):
        raise ValueError("CHALLENGE_PAGE")
    selected = None
    selected_by = ""
    for selector in selectors:
        selected = soup.select_one(selector)
        if selected is not None:
            selected_by = selector
            break
    if selected is None:
        raise ValueError("ARTICLE_NOT_FOUND")
    for unwanted in selected.select(
        "script, style, nav, header, footer, aside, form, noscript, svg"
    ):
        unwanted.decompose()
    blocks: list[str] = []
    for node in selected.select("h1, h2, h3, p, li, blockquote"):
        value = _SPACE.sub(" ", node.get_text(" ", strip=True)).strip()
        if value and (not blocks or value != blocks[-1]):
            blocks.append(value)
    text = "\n\n".join(blocks)
    paragraph_count = sum(
        1 for node in selected.select("p, li, blockquote") if node.get_text(strip=True)
    )
    if len(text) < 160 or paragraph_count < 2:
        raise ValueError("INSUFFICIENT_ARTICLE_TEXT")
    return text, selected_by


def derive_spans(text: str) -> list[dict[str, Any]]:
    """Derive deterministic chunks with exact UTF-8 extracted-text byte offsets."""
    if not isinstance(text, str) or not text.strip() or "\r" in text:
        raise ValueError("text must be non-empty canonical LF text")
    raw = text.encode("utf-8")
    spans: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(raw):
        proposed = min(cursor + MAX_SPAN_BYTES, len(raw))
        end = proposed
        while end > cursor:
            try:
                raw[cursor:end].decode("utf-8")
                break
            except UnicodeDecodeError:
                end -= 1
        if end < len(raw):
            floor = cursor + MAX_SPAN_BYTES // 2
            split = max(raw.rfind(b"\n\n", floor, end), raw.rfind(b" ", floor, end))
            if split > cursor:
                end = split
        while end < len(raw) and raw[end : end + 1] in {b" ", b"\n"}:
            end += 1
        chunk = raw[cursor:end]
        span_text = chunk.decode("utf-8")
        digest = _sha256(chunk)
        spans.append(
            {
                "id": f"span-{cursor}-{end}-{digest[:12]}",
                "start": cursor,
                "end": end,
                "text": span_text,
                "sha256": digest,
                "offset_basis": OFFSET_BASIS,
            }
        )
        cursor = end
    return spans


def _write_receipt(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    canonical_without_path = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    capture_id = _sha256(canonical_without_path)[:32]
    receipt = {**receipt, "capture_id": capture_id, "receipt_path": f"receipts/{capture_id}.json"}
    payload = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    _write_new(_safe_path(root, receipt["receipt_path"]), payload)
    return receipt


def capture_evidence(
    url: str,
    source: str,
    root: Path,
    *,
    publication: str | None = None,
) -> dict[str, Any]:
    """Capture one approved publisher page, or persist a visible UNAVAILABLE receipt."""
    root = Path(root)
    host, selectors, boundary_error = _publisher(url, source)
    base: dict[str, Any] = {
        "schema_version": "private-central-bank-evidence-v1",
        "status": "UNAVAILABLE",
        "source": source,
        "publisher_host": host,
        "url": url,
        "received_at": None,
        "arrival_basis": "NO_FETCH",
        "publication": (
            {
                "value": publication,
                "basis": "SUPPLIED_PUBLISHER_FEED_CLAIM",
                "article_verified": False,
            }
            if publication is not None
            else None
        ),
        "vintage": "UNKNOWN",
        "request_policy": {
            "timeout_seconds": list(REQUEST_TIMEOUT_SECONDS),
            "maximum_body_bytes": MAX_BODY_BYTES,
            "redirects": "DISABLED",
        },
        "http": None,
        "raw": None,
        "raw_sha256": None,
        "text": None,
        "text_sha256": None,
        "spans": [],
        "extraction_scope": "SELECTED_ARTICLE_BLOCKS_NOT_FULL_DOCUMENT",
        "model_calls": "PROHIBITED",
        "failure": None,
    }
    if boundary_error is not None:
        base["failure"] = {"code": boundary_error}
        return _write_receipt(root, base)

    response: requests.Response | Any | None = None
    raw = bytearray()
    too_large = False
    try:
        response = requests.get(
            url,
            allow_redirects=False,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        for chunk in response.iter_content(chunk_size=65_536):
            if not chunk:
                continue
            remaining = MAX_BODY_BYTES - len(raw)
            if len(chunk) > remaining:
                raw.extend(chunk[:remaining])
                too_large = True
                break
            raw.extend(chunk)
        base["received_at"] = _utc_now()
        base["arrival_basis"] = "POST_FETCH_UTC_RECEIPT"
    except requests.RequestException:
        base["received_at"] = _utc_now()
        base["arrival_basis"] = "POST_FETCH_ATTEMPT_UTC_RECEIPT"
        if response is not None:
            status_code = int(response.status_code)
            content_type = str(response.headers.get("Content-Type", ""))
            base["http"] = {
                "status_code": status_code,
                "content_type": content_type,
                "declared_content_length": response.headers.get("Content-Length"),
            }
        if raw:
            partial_bytes = bytes(raw)
            partial_digest = _sha256(partial_bytes)
            partial_relative = f"raw/{partial_digest}.html"
            partial_path = _safe_path(root, partial_relative)
            if partial_path.exists():
                if partial_path.read_bytes() != partial_bytes:
                    raise ValueError("immutable partial raw artifact collision")
            else:
                _write_new(partial_path, partial_bytes)
            base["raw"] = {
                "path": partial_relative,
                "sha256": partial_digest,
                "bytes": len(partial_bytes),
            }
            base["raw_sha256"] = partial_digest
        base["failure"] = {"code": "FETCH_FAILED"}
        return _write_receipt(root, base)
    finally:
        if response is not None:
            response.close()

    status_code = int(response.status_code)
    content_type = str(response.headers.get("Content-Type", ""))
    base["http"] = {
        "status_code": status_code,
        "content_type": content_type,
        "declared_content_length": response.headers.get("Content-Length"),
    }
    raw_bytes = bytes(raw)
    if raw_bytes:
        raw_digest = _sha256(raw_bytes)
        raw_relative = f"raw/{raw_digest}.html"
        raw_path = _safe_path(root, raw_relative)
        if raw_path.exists():
            if raw_path.read_bytes() != raw_bytes:
                raise ValueError("immutable raw artifact collision")
        else:
            _write_new(raw_path, raw_bytes)
        base["raw"] = {"path": raw_relative, "sha256": raw_digest, "bytes": len(raw_bytes)}
        base["raw_sha256"] = raw_digest

    if too_large:
        base["failure"] = {"code": "BODY_TOO_LARGE"}
        return _write_receipt(root, base)
    if 300 <= status_code < 400:
        base["failure"] = {"code": "REDIRECT_REJECTED"}
        return _write_receipt(root, base)
    if status_code != 200:
        base["failure"] = {"code": "HTTP_STATUS", "status_code": status_code}
        return _write_receipt(root, base)
    if not raw_bytes:
        base["failure"] = {"code": "EMPTY_BODY"}
        return _write_receipt(root, base)
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in {"text/html", "application/xhtml+xml"}:
        base["failure"] = {"code": "UNSUPPORTED_CONTENT_TYPE"}
        return _write_receipt(root, base)

    assert selectors is not None
    try:
        extracted, selected_by = _extract_article(raw_bytes, content_type, selectors)
    except ValueError as exc:
        base["failure"] = {"code": str(exc)}
        return _write_receipt(root, base)
    text_bytes = extracted.encode("utf-8")
    text_digest = _sha256(text_bytes)
    text_relative = f"text/{text_digest}.txt"
    text_path = _safe_path(root, text_relative)
    if text_path.exists():
        if text_path.read_bytes() != text_bytes:
            raise ValueError("immutable text artifact collision")
    else:
        _write_new(text_path, text_bytes)
    base.update(
        {
            "status": "AVAILABLE",
            "text": {
                "path": text_relative,
                "sha256": text_digest,
                "bytes": len(text_bytes),
                "encoding": "UTF-8",
                "selector": selected_by,
            },
            "text_sha256": text_digest,
            "spans": derive_spans(extracted),
            "failure": None,
        }
    )
    return _write_receipt(root, base)


def verify_evidence(receipt: dict[str, Any], root: Path) -> dict[str, Any]:
    """Replay raw extraction and return receipt fields plus verified text and spans."""
    if not isinstance(receipt, dict) or receipt.get("status") != "AVAILABLE":
        raise ValueError("only AVAILABLE evidence can be verified")
    receipt_path = _safe_path(Path(root), receipt.get("receipt_path", ""))
    try:
        stored_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("stored receipt is unavailable or invalid") from exc
    if stored_receipt != receipt:
        raise ValueError("supplied metadata does not match immutable receipt")
    identity_fields = {
        key: value for key, value in receipt.items() if key not in {"capture_id", "receipt_path"}
    }
    expected_id = _sha256(
        json.dumps(
            identity_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )[:32]
    if (
        receipt.get("capture_id") != expected_id
        or receipt.get("receipt_path") != f"receipts/{expected_id}.json"
    ):
        raise ValueError("receipt capture identity mismatch")
    if (
        receipt.get("schema_version") != "private-central-bank-evidence-v1"
        or receipt.get("status") != "AVAILABLE"
        or receipt.get("vintage") != "UNKNOWN"
        or receipt.get("model_calls") != "PROHIBITED"
        or receipt.get("extraction_scope") != "SELECTED_ARTICLE_BLOCKS_NOT_FULL_DOCUMENT"
        or receipt.get("failure") is not None
        or receipt.get("request_policy")
        != {
            "timeout_seconds": list(REQUEST_TIMEOUT_SECONDS),
            "maximum_body_bytes": MAX_BODY_BYTES,
            "redirects": "DISABLED",
        }
    ):
        raise ValueError("receipt policy metadata mismatch")
    publication = receipt.get("publication")
    if publication is not None and (
        not isinstance(publication, dict)
        or set(publication) != {"value", "basis", "article_verified"}
        or not isinstance(publication.get("value"), str)
        or not publication["value"].strip()
        or publication.get("basis") != "SUPPLIED_PUBLISHER_FEED_CLAIM"
        or publication.get("article_verified") is not False
    ):
        raise ValueError("publication claim metadata mismatch")
    host, selectors, boundary_error = _publisher(receipt.get("url", ""), receipt.get("source", ""))
    if boundary_error is not None or receipt.get("publisher_host") != host:
        raise ValueError("publisher boundary mismatch")
    received_at = receipt.get("received_at")
    if not isinstance(received_at, str):
        raise ValueError("received_at must be an aware UTC clock")
    try:
        parsed_clock = datetime.fromisoformat(received_at)
    except (TypeError, ValueError) as exc:
        raise ValueError("received_at must be an aware UTC clock") from exc
    if parsed_clock.tzinfo is None or parsed_clock.utcoffset() != UTC.utcoffset(parsed_clock):
        raise ValueError("received_at must be an aware UTC clock")
    if parsed_clock > datetime.now(UTC):
        raise ValueError("received_at cannot be in the future")
    if receipt.get("arrival_basis") != "POST_FETCH_UTC_RECEIPT":
        raise ValueError("arrival basis mismatch")
    raw_meta = receipt.get("raw")
    text_meta = receipt.get("text")
    http_meta = receipt.get("http")
    if (
        not isinstance(raw_meta, dict)
        or not isinstance(text_meta, dict)
        or not isinstance(http_meta, dict)
    ):
        raise ValueError("missing source artifacts")
    if (
        set(raw_meta) != {"path", "sha256", "bytes"}
        or set(text_meta) != {"path", "sha256", "bytes", "encoding", "selector"}
        or text_meta.get("encoding") != "UTF-8"
        or not isinstance(raw_meta.get("bytes"), int)
        or not 0 < raw_meta["bytes"] <= MAX_BODY_BYTES
        or http_meta.get("status_code") != 200
        or str(http_meta.get("content_type", "")).split(";", 1)[0].strip().lower()
        not in {"text/html", "application/xhtml+xml"}
    ):
        raise ValueError("source artifact metadata mismatch")
    raw_path = _safe_path(Path(root), raw_meta.get("path", ""))
    text_path = _safe_path(Path(root), text_meta.get("path", ""))
    raw = raw_path.read_bytes()
    if (
        _sha256(raw) != raw_meta.get("sha256")
        or raw_meta.get("sha256") != receipt.get("raw_sha256")
        or len(raw) != raw_meta.get("bytes")
        or len(raw) > MAX_BODY_BYTES
        or raw_meta.get("path") != f"raw/{_sha256(raw)}.html"
    ):
        raise ValueError("raw source hash or size mismatch")
    content_type = http_meta.get("content_type")
    if not isinstance(content_type, str) or selectors is None:
        raise ValueError("invalid extraction metadata")
    replay_text, selected_by = _extract_article(raw, content_type, selectors)
    if selected_by != text_meta.get("selector"):
        raise ValueError("publisher selector changed")
    replay_bytes = replay_text.encode("utf-8")
    if (
        _sha256(replay_bytes) != text_meta.get("sha256")
        or text_meta.get("sha256") != receipt.get("text_sha256")
        or len(replay_bytes) != text_meta.get("bytes")
        or text_path.read_bytes() != replay_bytes
        or text_meta.get("path") != f"text/{_sha256(replay_bytes)}.txt"
    ):
        raise ValueError("extracted text does not match raw-source replay")
    spans = derive_spans(replay_text)
    if spans != receipt.get("spans"):
        raise ValueError("span metadata does not match extracted text")
    return {**receipt, "text": replay_text, "spans": spans}
