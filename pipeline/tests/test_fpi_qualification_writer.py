"""Synthetic receipt checks: no database, source trust or execution proof."""

from __future__ import annotations

import asyncio
import hashlib
import json
import traceback
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock, PropertyMock, patch
from unittest.mock import call as mock_call

import pytest

from src.db.writer import append_fpi_qualification
from src.research.fpi_qualification import (
    FpiQualificationCommand,
    FpiQualificationEventV2,
    FpiQualificationHead,
    FpiResolutionWitness,
)

MEMBER, VALUE, PARSER, EVIDENCE, PRIOR = (char * 64 for char in "abcde")
COMMAND = FpiQualificationCommand("membership", MEMBER, "ACCEPT", "REVIEW", EVIDENCE)
RESOLVE = FpiQualificationCommand(
    "date", "2026-09-28", "RESOLVE", "REVIEW", EVIDENCE,
    chosen_membership_id=MEMBER, basis_membership_ids=(MEMBER, "f" * 64),
)
WITNESS = FpiResolutionWitness((
    FpiQualificationHead("membership", MEMBER, PRIOR),
    FpiQualificationHead("value", VALUE, None),
    FpiQualificationHead("parser", PARSER, None),
))
EVENT = FpiQualificationEventV2(COMMAND, 17, datetime(2026, 9, 28, 12, tzinfo=UTC))
RECEIPT: dict[str, Any] = {
    "version": "fpi-qualification-receipt-v2",
    "command_id": COMMAND.command_id,
    "event_id": EVENT.event_id,
    "event_ordinal": EVENT.event_ordinal,
    "recorded_at": EVENT.recorded_at.isoformat(),
    "event_document_json": EVENT.document_json,
    "inserted": True,
}
TEXT = type("Text", (str,), {})
INTEGER = type("Integer", (int,), {})


@pytest.mark.parametrize("command", [
    FpiQualificationCommand(scope, MEMBER, action, "REVIEW", EVIDENCE,
                            expected_prior_event_id=PRIOR)
    for scope in ("membership", "value", "parser")
    for action in ("ACCEPT", "WITHDRAW", "QUARANTINE")
] + [COMMAND, RESOLVE])
@pytest.mark.parametrize(("ordinal", "time"), [
    (1, datetime(1, 1, 1, tzinfo=UTC)),
    (2**63 - 1, datetime(9999, 12, 31, 23, 59, 59, 123456, tzinfo=UTC)),
])
def test_qualification_writer_valid_receipts(
    command: FpiQualificationCommand, ordinal: int, time: datetime,
) -> None:
    event = FpiQualificationEventV2(
        command, ordinal, time, WITNESS if command.scope == "date" else None,
    )
    original = dict(RECEIPT, command_id=command.command_id, event_id=event.event_id,
                    event_ordinal=ordinal, recorded_at=time.isoformat(),
                    event_document_json=event.document_json)
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = original
    with patch("src.db.writer._client", return_value=client) as factory:
        receipt = append_fpi_qualification(command)
        original["inserted"] = False
        retry = append_fpi_qualification(command)
    assert factory.call_count == 2
    assert client.mock_calls == [
        mock_call.rpc("append_fpi_qualification", {
            "p_command_id": command.command_id, "p_document_json": command.document_json,
        }),
        mock_call.rpc().execute(),
    ] * 2
    assert type(receipt) is dict and receipt is not original
    assert type(retry) is dict and retry is not original
    assert receipt == dict(original, inserted=True)
    assert retry == original
    assert {key: value for key, value in receipt.items() if key != "inserted"} == {
        key: value for key, value in retry.items() if key != "inserted"
    }


@pytest.mark.parametrize(("field", "value"), [
    ("scope", "value"), ("target", VALUE), ("action", "WITHDRAW"),
    ("reason_code", "OTHER"), ("evidence_sha256", PRIOR),
    ("expected_prior_event_id", PRIOR), ("chosen_membership_id", MEMBER),
    ("basis_membership_ids", (MEMBER,)), ("basis_membership_ids", []),
    ("basis_membership_ids", (TEXT(MEMBER), "f" * 64)),
    ("basis_membership_ids", ("f" * 64, MEMBER)),
    ("command_id", "0" * 64), ("command_id", TEXT(COMMAND.command_id)),
    ("scope", TEXT("membership")), ("target", TEXT(MEMBER)),
    ("action", TEXT("ACCEPT")), ("reason_code", TEXT("REVIEW")),
    ("evidence_sha256", TEXT(EVIDENCE)), ("document_json", TEXT(COMMAND.document_json)),
    ("document_json", COMMAND.document_json + " "),
    ("document_json", RESOLVE.document_json),
    pytest.param("document_json", "x" * 300001, id="oversized-command"),
    ("document_json", "[" * 20 + "]" * 20), ("document_json", "private input \x00"),
    ("document_json", COMMAND.document_json.replace('"ACCEPT"', '"ACCEPT","action":"ACCEPT"')),
    ("missing", "command_id"), ("missing", "reason_code"), ("missing", "document_json"),
    ("object", None), ("object", {}), ("object", True), ("object", COMMAND.document_json),
])
def test_qualification_writer_rejects_forged_commands_before_io(field: str, value: Any) -> None:
    command: Any = replace(RESOLVE if field == "basis_membership_ids" else COMMAND)
    if field == "object":
        command = value
    elif field == "missing":
        object.__delattr__(command, value)
    else:
        object.__setattr__(command, field, value)
    with patch("src.db.writer._client") as factory:
        with pytest.raises(ValueError, match="^Invalid FPI qualification command$") as failure:
            append_fpi_qualification(command)
    factory.assert_not_called()
    assert failure.value.__cause__ is None and failure.value.__suppress_context__
    assert "private input" not in "".join(traceback.format_exception(failure.value))


@pytest.mark.parametrize(("location", "field", "value"), [
    ("outer", "version", "fpi-qualification-receipt-v1"),
    ("outer", "version", TEXT("fpi-qualification-receipt-v2")),
    ("outer", "command_id", "0" * 64), ("outer", "command_id", COMMAND.command_id.upper()),
    ("outer", "command_id", TEXT(COMMAND.command_id)), ("outer", "command_id", True),
    ("outer", "event_id", "0" * 64), ("outer", "event_id", EVENT.event_id.upper()),
    ("outer", "event_id", TEXT(EVENT.event_id)), ("outer", "event_id", True),
    ("outer", "event_ordinal", True), ("outer", "event_ordinal", 17.0),
    ("outer", "event_ordinal", INTEGER(17)), ("outer", "event_ordinal", "17"),
    ("outer", "event_ordinal", 0), ("outer", "event_ordinal", 2**63),
    ("outer", "event_ordinal", 18), ("outer", "inserted", 1),
    ("outer", "inserted", "true"), ("outer", "inserted", None),
    ("outer", "recorded_at", "2026-09-28T12:00:00Z"),
    ("outer", "recorded_at", "2026-09-28T12:00:00.000000+00:00"),
    ("outer", "recorded_at", "2026-09-28T17:30:00+05:30"),
    ("outer", "recorded_at", "2026-09-28T12:00:01+00:00"),
    ("outer", "recorded_at", "2026-09-31T12:00:00+00:00"),
    ("outer", "recorded_at", TEXT(RECEIPT["recorded_at"])),
    ("outer", "recorded_at", None), ("outer", "extra", "private input"),
    ("outer", "event_document_json", None),
    ("outer", "event_document_json", TEXT(EVENT.document_json)),
    ("outer", "event_document_json", EVENT.document_json + " "),
    ("outer", "event_document_json", EVENT.document_json.replace(
        '"event_ordinal":17', '"event_ordinal":17,"event_ordinal":17')),
    pytest.param("outer", "event_document_json", "x" * 400001, id="oversized-event"),
    ("outer", "event_document_json", "[" * 20 + "]" * 20),
    ("event", "event_ordinal", True), ("event", "event_ordinal", 0),
    ("event", "event_ordinal", 2**63), ("event", "event_ordinal", 18),
    ("event", "recorded_at", "2026-09-28T12:00:00Z"),
    ("event", "recorded_at", "2026-09-28T12:00:01+00:00"),
    ("event", "recorded_at", "2026-09-28T12:00:00.1234567+00:00"),
    ("event", "version", "fpi-qualification-event-v1"),
    ("event", "command_id", "0" * 64), ("event", "extra", True),
    ("event", "witness", {"heads": []}),
    ("command", "reason_code", "OTHER"), ("command", "evidence_sha256", PRIOR),
    ("command", "scope", "value"), ("command", "target", VALUE),
    ("command", "action", "WITHDRAW"), ("command", "expected_prior_event_id", PRIOR),
    ("command", "chosen_membership_id", "f" * 64),
    ("command", "basis_membership_ids", [MEMBER]),
    ("command", "extra", True), ("command", "recorded_at", "2026-09-28T12:00:00+00:00"),
    ("command", "event_ordinal", 12),
    ("witness", "witness", None), ("witness", "witness", {"heads": []}),
    ("witness", "witness", {"heads": [
        {"scope": "membership", "target": MEMBER, "event_id": None},
        {"scope": "value", "target": VALUE, "event_id": None},
        {"scope": "parser", "target": PARSER, "event_id": None},
    ]}),
    ("object", "", None), ("object", "", []), ("object", "", True),
    ("object", "", {}), ("object", "", [RECEIPT]),
    *[("missing", key, None) for key in RECEIPT],
])
def test_qualification_writer_rejects_invalid_receipts(
    location: str, field: str, value: Any,
) -> None:
    command = RESOLVE if location == "witness" or (
        location == "command" and field in ("chosen_membership_id", "basis_membership_ids")
    ) else COMMAND
    event = FpiQualificationEventV2(
        command, 17, EVENT.recorded_at, WITNESS if command.scope == "date" else None,
    )
    receipt: Any = dict(RECEIPT, command_id=command.command_id, event_id=event.event_id,
                        event_document_json=event.document_json)
    if location == "object":
        receipt = value
    elif location == "missing":
        del receipt[field]
    elif location == "outer":
        receipt[field] = value
    else:
        document = json.loads(event.document_json)
        document["command" if location == "command" else field] = (
            dict(document["command"], **{field: value}) if location == "command" else value
        )
        if location == "command":
            # Rehash the complete changed command/event: compare submitted meaning too.
            command_json = json.dumps(document["command"], sort_keys=True, separators=(",", ":"))
            document["command_id"] = hashlib.sha256(command_json.encode("ascii")).hexdigest()
        receipt["event_document_json"] = json.dumps(document, sort_keys=True, separators=(",", ":"))
        receipt["event_id"] = hashlib.sha256(
            receipt["event_document_json"].encode("ascii")
        ).hexdigest()
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = receipt
    with patch("src.db.writer._client", return_value=client):
        with pytest.raises(
            RuntimeError, match="^FPI qualification append returned an invalid receipt$",
        ):
            append_fpi_qualification(command)
    client.rpc.assert_called_once()
    client.rpc.return_value.execute.assert_called_once_with()


@pytest.mark.parametrize("stage", ["client", "rpc", "execute", "data", "command", "event"])
@pytest.mark.parametrize("exception_type", [RuntimeError, KeyboardInterrupt, SystemExit,
                                          asyncio.CancelledError])
def test_qualification_writer_errors_and_cancellation(
    stage: str, exception_type: type[BaseException],
) -> None:
    sensitive = "synthetic-private-input-and-credential-text"
    error = exception_type(sensitive)
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = dict(RECEIPT)
    if stage in ("rpc", "execute"):
        (client.rpc if stage == "rpc" else client.rpc.return_value.execute).side_effect = error
    elif stage == "data":
        type(client.rpc.return_value.execute.return_value).data = PropertyMock(side_effect=error)
    target = {
        "command": "decode_fpi_qualification_command", "event": "decode_fpi_qualification_event",
    }.get(stage, "_client")
    expected_type = (ValueError if stage == "command" else RuntimeError)
    if exception_type is not RuntimeError:
        expected_type = cast(Any, exception_type)
    with patch("src.db.writer._client", return_value=client):
        with patch("src.db.writer." + target, **(
            {"side_effect": error} if stage in ("client", "command", "event")
            else {"return_value": client}
        )):
            with pytest.raises(expected_type) as failure:
                append_fpi_qualification(COMMAND)
    if exception_type is RuntimeError:
        assert str(failure.value) == {
            "command": "Invalid FPI qualification command",
            "event": "FPI qualification append returned an invalid receipt",
        }.get(stage, "FPI qualification append failed")
        assert sensitive not in "".join(traceback.format_exception(failure.value))
        assert failure.value.__cause__ is None and failure.value.__suppress_context__
    else:
        assert failure.value is error
