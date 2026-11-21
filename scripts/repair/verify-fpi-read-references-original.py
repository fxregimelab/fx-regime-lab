"""Verify compact references against retained original reports without I/O to providers."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))

from src.research import fpi_parse_record as codec  # noqa: E402
from src.research.fpi_capture import FpiCapture, build_fpi_capture  # noqa: E402
from src.research.fpi_observation import FPI_OBSERVATION_VERSION  # noqa: E402
from src.research.fpi_selection import FpiParsedDay, FpiParseResult  # noqa: E402

CAPTURE_DIR = Path("C:/Users/sakha/.agent-reach/fxregimelab-fpi-evidence")


def _expected_reference_document(
    captures: tuple[FpiCapture, ...], records: tuple[codec.FpiParseRecord, ...]
) -> str:
    """Use complete restoration, independently of the new compact builder."""
    capture_by_id = {capture.capture_sha256: capture for capture in captures}
    capture_rows = []
    for capture in sorted(captures, key=lambda item: item.capture_sha256):
        document = json.loads(capture.document_json)
        capture_rows.append({
            "capture_sha256": capture.capture_sha256,
            "document_size": len(capture.document_json.encode("ascii")),
            "source_url": document["source_url"],
            "requested_at": document["requested_at"],
            "retrieved_at": document["retrieved_at"],
            "http_status": document["http_status"],
            "body_size": document["body_size"],
            "raw_sha256": document["raw_sha256"],
        })
    parse_rows = []
    for record in sorted(records, key=lambda item: item.parse_id):
        original_document = json.loads(record.document_json)
        original = codec.restore_fpi_parse_record(
            record, capture_by_id[original_document["capture_sha256"]]
        )
        parse_rows.append({
            "parse_id": original.parse_id,
            "record_sha256": record.record_sha256,
            "document_size": len(record.document_json.encode("ascii")),
            "content_sha256": original.content_sha256,
            "capture_sha256": original.capture.capture_sha256,
            "parser_sha256": original.parser_sha256,
            "definition_version": original.definition_version,
            "recorded_at": original.recorded_at.isoformat(),
            "failure_reason": original.failure_reason,
            "memberships": [
                {
                    "reporting_date": day.reporting_date.isoformat(),
                    "value_sha256": day.value_sha256,
                    "membership_id": original.membership_id(day),
                    "source_evidence_sha256": day.source_evidence_sha256,
                }
                for day in original.days
            ],
        })
    return json.dumps(
        {"version": "fpi-read-references-v1", "captures": capture_rows, "parses": parse_rows},
        ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )


def _check_reference_output(
    captures: tuple[FpiCapture, ...], records: tuple[codec.FpiParseRecord, ...], expected: str
) -> Any:
    result = codec.build_fpi_read_references(captures=captures, records=records)
    assert result.document_json == expected, "Complete reference output differs"
    assert result.reference_sha256 == hashlib.sha256(expected.encode("ascii")).hexdigest()
    return result


def verify_original_read_references() -> None:
    spec = importlib.util.spec_from_file_location(
        "read_reference_original_source", ROOT / "pipeline/scripts/verify_fpi_source_capture.py"
    )
    assert spec is not None and spec.loader is not None
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    # This labels the inspected parser file; it is not approved execution authority.
    parser_hash = hashlib.sha256(
        (ROOT / "pipeline/src/research/fpi_parser.py").read_bytes()
    ).hexdigest()
    captures = []
    records = []
    counts = []
    for name in ("latest", "monthly"):
        parsed, retrieved_at = source._verify_capture(CAPTURE_DIR, name)
        retained = source._CAPTURES[name]
        receipt = json.loads((CAPTURE_DIR / retained["receipt"]).read_bytes())
        # Floor the pinned request start; the existing verifier ceilings completion.
        requested_at = datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00"))
        capture = build_fpi_capture(
            body=(CAPTURE_DIR / retained["html"]).read_bytes(),
            source_url=retained["source_url"], requested_at=requested_at,
            retrieved_at=retrieved_at, http_status=200,
        )
        complete = FpiParseResult(
            capture, parser_hash, FPI_OBSERVATION_VERSION, retrieved_at,
            tuple(FpiParsedDay(day.observation.document_json, day.source_evidence.evidence_sha256)
                  for day in parsed),
        )
        record = codec.build_fpi_parse_record(
            complete,
            source_evidence_documents=tuple(day.source_evidence.document_json for day in parsed),
        )
        captures.append(capture)
        records.append(record)
        counts.append(len(complete.days))
    assert counts == [1, 18], "Original report membership counts changed"
    capture_inputs, record_inputs = tuple(captures), tuple(records)
    expected = _expected_reference_document(capture_inputs, record_inputs)
    actual = _check_reference_output(capture_inputs, record_inputs, expected)
    # Equal retries and permutations cannot alter any reference or omit support dates.
    _check_reference_output(
        tuple(reversed(capture_inputs)), tuple(reversed(record_inputs)), expected
    )
    _check_reference_output(
        capture_inputs + capture_inputs, record_inputs + record_inputs, expected
    )
    decoded = json.loads(actual.document_json)
    assert sum(len(row["memberships"]) for row in decoded["parses"]) == 19
    assert len({row["membership_id"] for item in decoded["parses"]
                for row in item["memberships"]}) == 19
    assert all("body_base64" not in row for row in decoded["captures"])
    wrong_outputs = []
    incomplete = copy.deepcopy(decoded)
    monthly = next(row for row in incomplete["parses"] if len(row["memberships"]) == 18)
    monthly["memberships"].pop(0)
    wrong_outputs.append(incomplete)
    wrong_size = copy.deepcopy(decoded)
    wrong_size["captures"][0]["document_size"] += 1
    wrong_outputs.append(wrong_size)
    for wrong in wrong_outputs:
        document = json.dumps(wrong, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        forged = type(actual)(
            reference_sha256=hashlib.sha256(document.encode("ascii")).hexdigest(),
            document_json=document,
        )
        with patch.object(codec, "build_fpi_read_references", return_value=forged):
            try:
                _check_reference_output(capture_inputs, record_inputs, expected)
            except AssertionError:
                pass
            else:
                raise AssertionError("Reference oracle missed incorrect rehashed output")
    _check_reference_output(capture_inputs, record_inputs, expected)
    print("Verified 2 captures, 2 complete parses, 19 memberships; 2 wrong outputs detected")
    print("FPI_ORIGINAL_READ_REFERENCES_VERIFIED")


if __name__ == "__main__":
    verify_original_read_references()
