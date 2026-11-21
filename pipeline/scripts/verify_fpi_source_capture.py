"""Verify the two privately retained original NSDL FPI HTML captures offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.research.fpi_parser import ParsedFpiDay, parse_nsdl_fpi_html  # noqa: E402

_CAPTURES = {
    "latest": {
        "html": "latest-direct.html",
        "receipt": "latest-direct.receipt.json",
        "html_sha256": "5283f52784fd0cc9a7d41968cb6a34f69700923f4adb20ffe6d509a38ca8ca81",
        "receipt_sha256": "75dcaebe53b9b85bc6cd58bb27f478de7aae8283647b8f1492214ca9776076d8",
        "source_url": "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
        "retrieved_at": "2026-09-27T12:32:50.1044666Z",
    },
    "monthly": {
        "html": "monthly-direct.html",
        "receipt": "monthly-direct.receipt.json",
        "html_sha256": "632537a467a15ff386104b3fa7a4a6b983b062d752ac1757eb8974954cdcd752",
        "receipt_sha256": "bf61035072d75eff7e5c3b773f7cb7289508e1a231e5c9d1bd833961fb2df6e0",
        "source_url": "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx",
        "retrieved_at": "2026-09-27T12:32:32.0884114Z",
    },
}
_MONTHLY_DAYS = (1, 2, 3, 4, 7, 8, 9, 10, 11, 15, 16, 17, 18, 21, 22, 23, 24, 25)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_receipt(path: Path, expected_sha256: str) -> dict[str, Any]:
    body = path.read_bytes()
    if _sha256(body) != expected_sha256:
        raise ValueError(f"Receipt hash mismatch: {path.name}")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError(f"Receipt is not an object: {path.name}")
    return value


def _parse_timestamp(value: str) -> datetime:
    match = re.fullmatch(r"(.+?)(?:\.([0-9]{1,9}))?Z", value)
    if match is None:
        raise ValueError("Capture receipt timestamp is not UTC ISO text")
    fraction = match.group(2) or ""
    parsed = datetime.fromisoformat(f"{match.group(1)}+00:00").replace(
        microsecond=int(fraction[:6].ljust(6, "0"))
    )
    if any(digit != "0" for digit in fraction[6:]):
        parsed += timedelta(microseconds=1)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Capture receipt timestamp is not timezone-aware")
    return parsed


def _verify_capture(capture_dir: Path, name: str) -> tuple[tuple[ParsedFpiDay, ...], datetime]:
    expected = _CAPTURES[name]
    html_path = capture_dir / expected["html"]
    receipt_path = capture_dir / expected["receipt"]
    body = html_path.read_bytes()
    if _sha256(body) != expected["html_sha256"]:
        raise ValueError(f"Original HTML hash mismatch: {html_path.name}")
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"Unexpected UTF-8 BOM in known capture: {html_path.name}")
    receipt = _read_receipt(receipt_path, expected["receipt_sha256"])
    if receipt.get("source_url") != expected["source_url"]:
        raise ValueError(f"Receipt URL mismatch: {receipt_path.name}")
    if receipt.get("retrieved_at") != expected["retrieved_at"]:
        raise ValueError(f"Receipt retrieval time mismatch: {receipt_path.name}")
    if receipt.get("status") != 200:
        raise ValueError(f"Receipt HTTP status is not 200: {receipt_path.name}")
    retrieved_at = _parse_timestamp(expected["retrieved_at"])
    parsed = parse_nsdl_fpi_html(
        body,
        source_url=expected["source_url"],
        retrieved_at=retrieved_at,
    )
    return parsed, retrieved_at


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    args = parser.parse_args()
    capture_dir: Path = args.capture_dir
    if not capture_dir.is_dir():
        raise ValueError("Capture directory does not exist")

    latest, _ = _verify_capture(capture_dir, "latest")
    monthly, _ = _verify_capture(capture_dir, "monthly")
    if len(latest) != 1 or len(monthly) != 18:
        raise ValueError("Known captures do not contain one latest day and 18 monthly days")
    if tuple(item.observation.reporting_date.day for item in monthly) != _MONTHLY_DAYS:
        raise ValueError("Monthly capture reporting dates changed")

    latest_day = latest[0]
    monthly_final = monthly[-1]
    if latest_day.observation.net_hundredths_cr != -655271:
        raise ValueError("25 September published INR total changed")
    if latest_day.observation.document_json != monthly_final.observation.document_json:
        raise ValueError("Latest and final Monthly INR components differ")
    if latest_day.source_evidence.document_json != monthly_final.source_evidence.document_json:
        raise ValueError("Latest and final Monthly USD or conversion evidence differs")

    # Parsing validates captured contents; it cannot establish past decision visibility.
    print("FPI_ORIGINAL_CAPTURE_VERIFIED")


if __name__ == "__main__":
    main()
