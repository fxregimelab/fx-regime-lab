"""Bounded original BOJ current-source bytes; no historical availability inference."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from src.private_desk.evidence import _write_new

POLICY_URL = "https://www.boj.or.jp/en/index.htm"
FEED_URL = "https://www.boj.or.jp/en/rss/whatsnew.xml"
METHOD_VERSION = "boj-current-source-v1"
SOURCES = {
    POLICY_URL: (128 * 1024, {"text/html"}),
    FEED_URL: (256 * 1024, {"application/xml", "text/xml", "application/rss+xml"}),
}


def capture_source(
    root: Path, url: str, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> tuple[str, dict[str, Any]]:
    """Capture one pinned HTTPS source without redirects or a proxy fallback."""
    if url not in SOURCES:
        raise ValueError("Unsupported BOJ current source")
    bound, allowed_media = SOURCES[url]
    try:
        with requests.get(
            url, timeout=(5, 12), stream=True, allow_redirects=False,
            headers={"User-Agent": "FXResearchLab-PrivateResearch/1.0"},
        ) as response:
            media = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if response.status_code != 200 or response.url != url or media not in allowed_media:
                raise ValueError("BOJ source status, origin or media rejected")
            body = bytearray()
            for chunk in response.iter_content(16 * 1024):
                body.extend(chunk)
                if len(body) > bound:
                    raise ValueError("BOJ source exceeds capture limit")
            headers = {
                key: response.headers[key]
                for key in ("Content-Type", "Last-Modified", "ETag") if key in response.headers
            }
    except requests.RequestException:
        raise ValueError("BOJ source request unavailable") from None
    raw = bytes(body)
    text = raw.decode("utf-8-sig")
    received = clock()
    if received.utcoffset() != timedelta(0):
        raise ValueError("BOJ receipt clock must be UTC")
    digest = hashlib.sha256(raw).hexdigest()
    body_path = root / "bodies" / (digest + ".bin")
    if body_path.exists():
        if body_path.read_bytes() != raw:
            raise ValueError("BOJ source body changed")
    else:
        _write_new(body_path, raw)
    record = {
        "method_version": METHOD_VERSION, "source_url": url,
        "received_at": received.isoformat(), "response_status": 200,
        "response_media_type": media, "response_bytes": len(raw), "headers": headers,
        "redirects": 0, "point_in_time": False,
        "research_status": "CURRENT_DESCRIPTIVE_ONLY",
        "source_body": {"capture_path": str(body_path.resolve()), "sha256": digest},
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    receipt_hash = hashlib.sha256(encoded).hexdigest()
    receipt_path = root / "receipts" / (receipt_hash + ".json")
    if receipt_path.exists():
        if receipt_path.read_bytes() != encoded:
            raise ValueError("BOJ source receipt changed")
    else:
        _write_new(receipt_path, encoded)
    return text, {
        **record,
        "source_receipt": {"capture_path": str(receipt_path.resolve()), "sha256": receipt_hash},
    }
