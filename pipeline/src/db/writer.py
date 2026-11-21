"""
@agent_context: Primary database interface for Supabase, handling all
authenticated writes and service-role reads for the pipeline.
@allowed_imports: [json, os, collections.abc, dataclasses, datetime,
    functools, typing, supabase, src.types]
@forbidden_imports: [src.ai, src.regime, src.signals]
@obsidian_link: [[Infrastructure#Supabase Persistence]]
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import CancelledError
from dataclasses import asdict, fields
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Any, cast

from postgrest.exceptions import APIError
from postgrest.types import CountMethod
from supabase import Client, create_client

from src.research.fpi_capture import FpiCapture, validate_fpi_capture
from src.research.fpi_parse_record import (
    FpiArtifact,
    build_fpi_parse_record,
    validate_fpi_artifact,
)
from src.research.fpi_qualification import (
    FpiQualificationCommand,
    decode_fpi_qualification_command,
    decode_fpi_qualification_event,
)
from src.research.fpi_saved_read import (
    FpiAdminReadManifest,
    FpiAdminReadPolicy,
    FpiAdminReadRequest,
    validate_fpi_admin_policy_receipt,
    validate_fpi_admin_read_receipt,
    verify_fpi_admin_read_originals,
)
from src.research.fpi_selection import FpiParseResult
from src.research.quote_attempt import validate_quote_acquisition_event
from src.research.quote_capture import canonical_json, validate_quote_page
from src.research.quote_reference import build_quote_reference
from src.types import DeskOpenCardRow, RegimeCall, SignalRow
from src.validation.calculator import EVALUATION_VERSION

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not (key and str(key).strip()):
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment "
            "(Prefect: deployment job_variables.env, or local .env). "
            f"SUPABASE_URL set: {bool(url)}, SUPABASE_SERVICE_ROLE_KEY set: {bool(key)}."
        )
    return create_client(url, key)


def archive_price_observations(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Append provider evidence atomically; never promote it to a final close."""
    if len(observations) > 5000:
        raise ValueError("Price observation batches cannot exceed 5000 rows")
    payload = json.loads(json.dumps([dict(row) for row in observations], allow_nan=False))
    result = _client().rpc("append_price_observations", {"p_observations": payload}).execute().data
    if not isinstance(result, dict):
        raise RuntimeError("Price observation archive returned no receipt")
    ids = result.get("observation_ids")
    inserted, existing = result.get("inserted_count"), result.get("existing_count")
    if (
        not isinstance(ids, list) or len(ids) != len(payload)
        or any(type(value) is not int or value <= 0 for value in ids)
        or type(inserted) is not int or type(existing) is not int
        or inserted < 0 or existing < 0 or inserted + existing != len(payload)
        or inserted > len(set(ids))
    ):
        raise RuntimeError("Price observation archive returned an invalid receipt")
    return cast(dict[str, Any], result)


def archive_fpi_capture(capture: FpiCapture) -> dict[str, Any]:
    """Archive one validated private FPI response and verify its database receipt."""
    validate_fpi_capture(capture)
    requested_identity = capture.capture_sha256
    retrieved_at = datetime.fromisoformat(json.loads(capture.document_json)["retrieved_at"])
    try:
        result = _client().rpc(
            "append_fpi_capture",
            {
                "p_capture_sha256": requested_identity,
                "p_document_json": capture.document_json,
            },
        ).execute().data
    except Exception:
        raise RuntimeError("FPI capture archive failed") from None
    if (
        type(result) is not dict
        or set(result) != {"capture_sha256", "inserted", "stored_at"}
        or type(result.get("capture_sha256")) is not str
        or result["capture_sha256"] != requested_identity
        or type(result.get("inserted")) is not bool
        or type(result.get("stored_at")) is not str
        or re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]{1,6})?(?:\+00:00|Z)",
            result["stored_at"],
        ) is None
    ):
        raise RuntimeError("FPI capture archive returned an invalid receipt")
    try:
        stored_at = datetime.fromisoformat(result["stored_at"].replace("Z", "+00:00"))
    except ValueError:
        raise RuntimeError("FPI capture archive returned an invalid receipt") from None
    if stored_at.tzinfo != UTC or stored_at < retrieved_at:
        raise RuntimeError("FPI capture archive returned an invalid receipt")
    return {
        "capture_sha256": result["capture_sha256"],
        "inserted": result["inserted"],
        "stored_at": result["stored_at"],
    }


def _fpi_receipt_timestamp(value: Any, *, minimum: datetime | None = None) -> None:
    if type(value) is not str or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:\+00:00|Z)",
        value,
    ) is None:
        raise RuntimeError("FPI archive returned an invalid receipt")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise RuntimeError("FPI archive returned an invalid receipt") from None
    if parsed.tzinfo != UTC or minimum is not None and parsed < minimum:
        raise RuntimeError("FPI archive returned an invalid receipt")


def archive_fpi_artifact(artifact: FpiArtifact) -> dict[str, Any]:
    """Retain exact implementation bytes without executing the artifact."""
    validate_fpi_artifact(artifact)
    document = json.loads(artifact.document_json)
    try:
        result = _client().rpc(
            "append_fpi_artifact",
            {
                "p_artifact_sha256": artifact.artifact_sha256,
                "p_document_json": artifact.document_json,
            },
        ).execute().data
    except Exception:
        raise RuntimeError("FPI artifact archive failed") from None
    if (
        type(result) is not dict
        or set(result) != {"artifact_sha256", "kind", "inserted", "stored_at"}
        or type(result.get("artifact_sha256")) is not str
        or result.get("artifact_sha256") != artifact.artifact_sha256
        or type(result.get("kind")) is not str
        or result.get("kind") != document["kind"]
        or type(result.get("inserted")) is not bool
    ):
        raise RuntimeError("FPI artifact archive returned an invalid receipt")
    try:
        _fpi_receipt_timestamp(result.get("stored_at"))
    except RuntimeError:
        raise RuntimeError("FPI artifact archive returned an invalid receipt") from None
    return {
        "artifact_sha256": result["artifact_sha256"],
        "kind": result["kind"],
        "inserted": result["inserted"],
        "stored_at": result["stored_at"],
    }


def archive_fpi_parse_result(
    parse: FpiParseResult, *, source_evidence_documents: tuple[str, ...]
) -> dict[str, Any]:
    """Append one complete parse envelope; dependencies are archived separately."""
    record = build_fpi_parse_record(
        parse, source_evidence_documents=source_evidence_documents
    )
    document = json.loads(record.document_json)
    membership_ids = [day["membership_id"] for day in document["days"]]
    try:
        result = _client().rpc(
            "append_fpi_parse_result",
            {
                "p_parse_id": record.parse_id,
                "p_record_sha256": record.record_sha256,
                "p_document_json": record.document_json,
            },
        ).execute().data
    except Exception:
        raise RuntimeError("FPI parse archive failed") from None
    if (
        type(result) is not dict
        or set(result)
        != {
            "parse_id",
            "record_sha256",
            "content_sha256",
            "membership_ids",
            "inserted",
            "stored_at",
        }
        or type(result.get("parse_id")) is not str
        or result.get("parse_id") != record.parse_id
        or type(result.get("record_sha256")) is not str
        or result.get("record_sha256") != record.record_sha256
        or type(result.get("content_sha256")) is not str
        or result.get("content_sha256") != document["content_sha256"]
        or type(result.get("membership_ids")) is not list
        or result.get("membership_ids") != membership_ids
        or any(type(value) is not str for value in result["membership_ids"])
        or type(result.get("inserted")) is not bool
    ):
        raise RuntimeError("FPI parse archive returned an invalid receipt")
    try:
        _fpi_receipt_timestamp(result.get("stored_at"), minimum=parse.recorded_at)
    except RuntimeError:
        raise RuntimeError("FPI parse archive returned an invalid receipt") from None
    return {
        "parse_id": result["parse_id"],
        "record_sha256": result["record_sha256"],
        "content_sha256": result["content_sha256"],
        "membership_ids": list(result["membership_ids"]),
        "inserted": result["inserted"],
        "stored_at": result["stored_at"],
    }


def append_fpi_qualification(command: FpiQualificationCommand) -> dict[str, Any]:
    """Append an administrative assertion; a receipt does not authorize consumption."""
    try:
        if type(command) is not FpiQualificationCommand:
            raise ValueError
        submitted = decode_fpi_qualification_command(command.document_json)
        for name in (
            "scope", "target", "action", "reason_code", "evidence_sha256",
            "expected_prior_event_id", "chosen_membership_id", "basis_membership_ids",
            "document_json", "command_id",
        ):
            original, rebuilt = getattr(command, name), getattr(submitted, name)
            if type(original) is not type(rebuilt):
                raise ValueError
            if name == "basis_membership_ids" and (
                len(original) != len(rebuilt) or any(type(item) is not str for item in original)
            ):
                raise ValueError
            if original != rebuilt:
                raise ValueError
    except Exception:
        raise ValueError("Invalid FPI qualification command") from None
    try:
        result = _client().rpc(
            "append_fpi_qualification",
            {"p_command_id": submitted.command_id, "p_document_json": submitted.document_json},
        ).execute().data
    except Exception:
        raise RuntimeError("FPI qualification append failed") from None
    try:
        if (
            type(result) is not dict
            or any(type(key) is not str for key in result)
            or set(result) != {
                "version", "command_id", "event_id", "event_ordinal", "recorded_at",
                "event_document_json", "inserted",
            }
            or type(result["version"]) is not str
            or result["version"] != "fpi-qualification-receipt-v2"
            or type(result["command_id"]) is not str
            or result["command_id"] != submitted.command_id
            or type(result["event_id"]) is not str
            or type(result["event_ordinal"]) is not int
            or not 1 <= result["event_ordinal"] <= 2**63 - 1
            or type(result["recorded_at"]) is not str
            or type(result["inserted"]) is not bool
        ):
            raise ValueError
        event = decode_fpi_qualification_event(result["event_document_json"])
        if (
            event.command != submitted
            or event.event_id != result["event_id"]
            or event.event_ordinal != result["event_ordinal"]
            or event.recorded_at.isoformat() != result["recorded_at"]
        ):
            raise ValueError
    except Exception:
        raise RuntimeError("FPI qualification append returned an invalid receipt") from None
    return {
        "version": "fpi-qualification-receipt-v2",
        "command_id": submitted.command_id,
        "event_id": event.event_id,
        "event_ordinal": event.event_ordinal,
        "recorded_at": event.recorded_at.isoformat(),
        "event_document_json": event.document_json,
        "inserted": result["inserted"],
    }


_FPI_ADMIN_READ_PROJECTION = (
    "read_id,decision_id,request_sha256,request_document_json,policy_sha256,"
    "read_sha256,manifest_document_json,read_at,status"
)
_FPI_ADMIN_BATCH_SIZE = 64


class _FpiAdminDependencyMissing(ValueError):  # noqa: N818
    pass


def _fpi_admin_rebuild(value: Any, expected: type[Any]) -> Any:
    try:
        if type(value) is not expected:
            raise ValueError
        rebuilt = expected(value.document_json)
        for item in fields(rebuilt):
            original = getattr(value, item.name)
            if type(original) is not str or original != getattr(rebuilt, item.name):
                raise ValueError
        return rebuilt
    except (ValueError, TypeError, AttributeError):
        raise ValueError("READ_INTEGRITY_ERROR") from None


def append_fpi_admin_read_policy(policy: FpiAdminReadPolicy) -> dict[str, Any]:
    """Retain administrative intent and bind its receipt; confer no approval."""
    submitted = _fpi_admin_rebuild(policy, FpiAdminReadPolicy)
    try:
        result = _client().rpc("append_fpi_admin_read_policy", {
            "p_policy_sha256": submitted.policy_sha256,
            "p_document_json": submitted.document_json,
        }).execute().data
        return validate_fpi_admin_policy_receipt(result, submitted)
    except (CancelledError, MemoryError):
        raise
    except Exception:
        raise RuntimeError("READ_INTEGRITY_ERROR") from None


def capture_fpi_admin_read(request: FpiAdminReadRequest) -> dict[str, Any]:
    """Request one saved database snapshot and verify only its detached receipt."""
    submitted = _fpi_admin_rebuild(request, FpiAdminReadRequest)
    try:
        result = _client().rpc("capture_fpi_admin_read", {
            "p_request_sha256": submitted.request_sha256,
            "p_document_json": submitted.document_json,
        }).execute().data
        return validate_fpi_admin_read_receipt(result, submitted)
    except (CancelledError, MemoryError):
        raise
    except Exception:
        raise RuntimeError("READ_INTEGRITY_ERROR") from None


def _fpi_admin_rows(value: Any, projection: str, maximum: int) -> tuple[dict[str, Any], ...]:
    if type(value) is not list or len(value) > maximum:
        raise ValueError
    keys = set(projection.split(","))
    copies = []
    for row in value:
        if (
            type(row) is not dict or set(row) != keys
            or any(type(key) is not str for key in row)
            or any(type(item) is not str for item in row.values())
        ):
            raise ValueError
        copies.append(row.copy())
    return tuple(copies)


def _fpi_admin_original_batches(
    client: Client, *, table: str, projection: str, identity: str,
    expected_rows: list[dict[str, Any]], document_limit: int,
    byte_budget: list[int], total_limit: int, kind: str | None = None,
) -> tuple[dict[str, Any], ...]:
    expected = {row[identity]: row for row in expected_rows}
    ids = sorted(expected)
    originals: list[dict[str, Any]] = []
    document_key = "event_document_json" if identity == "event_id" else "document_json"
    for offset in range(0, len(ids), _FPI_ADMIN_BATCH_SIZE):
        batch = ids[offset:offset + _FPI_ADMIN_BATCH_SIZE]
        query = client.table(table).select(projection).in_(identity, batch)
        if kind is not None:
            query = query.eq("kind", kind)
        # One sentinel row exposes over-returning transports. Missing pages never retry.
        rows = _fpi_admin_rows(query.limit(len(batch) + 1).execute().data,
                               projection, len(batch) + 1)
        returned = [row[identity] for row in rows]
        if len(set(returned)) != len(returned) or set(returned) - set(batch):
            raise ValueError
        if set(returned) != set(batch):
            raise _FpiAdminDependencyMissing
        for row in rows:
            text = row[document_key]
            if (
                kind is not None and row["kind"] != kind
                or len(text) > document_limit or not text.isascii()
                or len(text) != expected[row[identity]]["document_size"]
            ):
                raise ValueError
            byte_budget[0] += len(text)
            if byte_budget[0] > total_limit:
                raise ValueError
        originals.extend(rows)
    return tuple(originals)


def load_fpi_admin_read(read_id: str) -> FpiAdminReadManifest:
    """Prove only immutable originals named by a saved, permanently ineligible read."""
    if type(read_id) is not str or re.fullmatch(r"[0-9a-f]{64}", read_id) is None:
        raise ValueError("READ_INTEGRITY_ERROR")
    try:
        client = _client()
        rows = _fpi_admin_rows(
            client.table("fpi_admin_reads").select(_FPI_ADMIN_READ_PROJECTION)
            .eq("read_id", read_id).limit(2).execute().data,
            _FPI_ADMIN_READ_PROJECTION, 2,
        )
        if not rows:
            raise _FpiAdminDependencyMissing
        if len(rows) != 1:
            raise ValueError
        row = rows[0]
        manifest = FpiAdminReadManifest(row["manifest_document_json"])
        request = FpiAdminReadRequest(row["request_document_json"])
        document = json.loads(manifest.document_json)
        if (
            row["read_id"] != read_id or manifest.read_id != read_id
            or any(row[key] != getattr(manifest, key) for key in (
                "decision_id", "request_sha256", "read_sha256", "status",
            ))
            or request.read_id != read_id
            or row["policy_sha256"] != document["policy_sha256"]
            or json.loads(request.document_json) != document["request"]
        ):
            raise ValueError
        _fpi_receipt_timestamp(row["read_at"])
        if datetime.fromisoformat(row["read_at"]) != datetime.fromisoformat(manifest.read_at):
            raise ValueError
        captures: tuple[dict[str, Any], ...] = ()
        parses: tuple[dict[str, Any], ...] = ()
        artifacts: tuple[dict[str, Any], ...] = ()
        events: tuple[dict[str, Any], ...] = ()
        if manifest.status == "COMPLETE":
            data = document["data"]
            budget = [0]
            captures = _fpi_admin_original_batches(
                client, table="fpi_captures",
                projection="capture_sha256,document_json,stored_at", identity="capture_sha256",
                expected_rows=data["references"]["captures"], document_limit=7_000_000,
                byte_budget=budget, total_limit=64_000_000,
            )
            parses = _fpi_admin_original_batches(
                client, table="fpi_parse_results",
                projection="parse_id,record_sha256,document_json,stored_at", identity="parse_id",
                expected_rows=data["references"]["parses"], document_limit=4_000_000,
                byte_budget=budget, total_limit=64_000_000,
            )
            for kind in ("PARSER", "SELECTOR"):
                artifacts += _fpi_admin_original_batches(
                    client, table="fpi_implementation_artifacts",
                    projection="kind,artifact_sha256,document_json,stored_at",
                    identity="artifact_sha256",
                    expected_rows=[item for item in data["artifacts"] if item["kind"] == kind],
                    document_limit=7_000_000, byte_budget=budget, total_limit=64_000_000,
                    kind=kind,
                )
            expected_events = []
            for event in data["qualification"]["events"]:
                text = json.dumps(event, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                expected_events.append({
                    "event_id": hashlib.sha256(text.encode("ascii")).hexdigest(),
                    "document_size": len(text),
                })
            events = _fpi_admin_original_batches(
                client, table="fpi_qualification_events",
                projection="event_id,event_document_json", identity="event_id",
                expected_rows=expected_events, document_limit=400_000,
                byte_budget=[0], total_limit=16_000_000,
            )
        return verify_fpi_admin_read_originals(
            manifest, capture_rows=captures, parse_rows=parses,
            artifact_rows=artifacts, event_rows=events,
        )
    except (CancelledError, MemoryError):
        raise
    except _FpiAdminDependencyMissing:
        raise RuntimeError("READ_DEPENDENCY_MISSING") from None
    except Exception:
        raise RuntimeError("READ_INTEGRITY_ERROR") from None


def archive_quote_acquisition_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Append an attempt event with exact identity and an acknowledged receipt."""
    validate_quote_acquisition_event(event)
    unsigned = canonical_json({key: value for key, value in event.items() if key != "event_sha256"})
    fingerprint = event["event_sha256"]
    attempt_id, sequence = event["attempt_id"], event["sequence"]
    try:
        result = _client().rpc("append_quote_acquisition_event", {
            "p_event_sha256": fingerprint, "p_unsigned_json": unsigned,
        }).execute().data
    except Exception:
        raise RuntimeError("Quote attempt archive failed") from None
    if (
        not isinstance(result, dict)
        or set(result) != {"event_sha256", "attempt_id", "sequence", "inserted"}
        or result["event_sha256"] != fingerprint or result["attempt_id"] != attempt_id
        or type(result["sequence"]) is not int or result["sequence"] != sequence
        or type(result["inserted"]) is not bool
    ):
        raise RuntimeError("Quote attempt archive returned an invalid receipt")
    return cast(dict[str, Any], result)


def archive_quote_capture(page: Mapping[str, Any]) -> dict[str, Any]:
    """Append one validated sanitized response; retries preserve the capture identity."""
    validate_quote_page(page)
    fingerprint = page["capture_sha256"]
    unsigned = canonical_json({key: value for key, value in page.items()
                               if key != "capture_sha256"})
    if len(unsigned.encode("utf-8")) > 32 * 1024 * 1024:
        raise ValueError("Serialized quote capture exceeds 32 MiB")
    result = _client().rpc("append_quote_capture", {
        "p_capture_sha256": fingerprint, "p_unsigned_json": unsigned,
    }).execute().data
    if (
        not isinstance(result, dict) or set(result) != {"capture_sha256", "inserted"}
        or result["capture_sha256"] != fingerprint or type(result["inserted"]) is not bool
    ):
        raise RuntimeError("Quote capture archive returned an invalid receipt")
    return cast(dict[str, Any], result)


def archive_quote_snapshot(
    pages: Sequence[Mapping[str, Any]], *, as_of: datetime,
    implementation_sha256: str, client_version: str,
) -> dict[str, Any]:
    """Append derived evidence referencing already archived pages, without qualification."""
    if not 1 <= len(pages) <= 10_000:
        raise ValueError("Quote snapshot requires between 1 and 10000 captures")
    if (not isinstance(implementation_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", implementation_sha256)):
        raise ValueError("Quote implementation fingerprint must be lowercase SHA-256")
    if (not isinstance(client_version, str)
            or not re.fullmatch(r"[a-zA-Z0-9._-]{1,128}", client_version)):
        raise ValueError("Invalid quote client version")
    reference = build_quote_reference(pages, as_of=as_of)
    identity_fields = ("pair", "instrument", "window_start_ns", "window_end_ns")
    if any(page[field] != pages[0][field] for page in pages for field in identity_fields):
        raise ValueError("Quote snapshot captures must have one pair, instrument and window")
    unsigned = canonical_json({
        "version": "quote-snapshot-v1", "implementation_sha256": implementation_sha256,
        "client_version": client_version, "reference": reference,
    })
    encoded = unsigned.encode("utf-8")
    if len(encoded) > 1024 * 1024:
        raise ValueError("Serialized quote snapshot exceeds 1 MiB")
    fingerprint = hashlib.sha256(encoded).hexdigest()
    result = _client().rpc("append_quote_snapshot", {
        "p_snapshot_sha256": fingerprint, "p_unsigned_json": unsigned,
    }).execute().data
    if (
        not isinstance(result, dict)
        or set(result) != {"snapshot_sha256", "inserted", "capture_count"}
        or result["snapshot_sha256"] != fingerprint or type(result["inserted"]) is not bool
        or type(result["capture_count"]) is not int or result["capture_count"] != len(pages)
    ):
        raise RuntimeError("Quote snapshot archive returned an invalid receipt")
    return cast(dict[str, Any], result)


def fetch_universe_registry() -> list[dict[str, Any]]:
    """All rows from ``universe`` (ordered by pair). Service-role read."""

    res = (
        _client()
        .table("universe")
        .select("pair,class,spot_ticker,yield_base,yield_quote,cot_ticker")
        .order("pair")
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def _date_iso(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


def write_signal_row(row: SignalRow) -> None:
    """Upsert signal row with all available metrics."""
    payload: dict[str, Any] = {
        "pair": row.pair,
        "date": _date_iso(row.date),
        "rate_diff_2y": row.rate_diff_2y,
        "rate_diff_10y": row.rate_diff_10y,
        "cot_percentile": row.cot_percentile,
        "realized_vol_20d": row.realized_vol_20d,
        "realized_vol_5d": row.realized_vol_5d,
        "implied_vol_30d": row.implied_vol_30d,
        "spot": row.spot,
        "day_change": row.day_change,
        "day_change_pct": row.day_change_pct,
        "cross_asset_vix": row.cross_asset_vix,
        "cross_asset_dxy": row.cross_asset_dxy,
        "cross_asset_oil": row.cross_asset_oil,
        "cross_asset_us10y": row.cross_asset_us10y,
        "cross_asset_gold": row.cross_asset_gold,
        "cross_asset_copper": row.cross_asset_copper,
        "cross_asset_stoxx": row.cross_asset_stoxx,
        "oi_delta": row.oi_delta,
        "volume_rvol": row.volume_rvol,
        "structural_instability": row.structural_instability,
        "breakeven_inflation_10y": row.breakeven_inflation_10y,
        "rate_diff_10y_real": row.rate_diff_10y_real,
        "rate_z_tactical": row.rate_z_tactical,
        "rate_z_structural": row.rate_z_structural,
        "z_blended": row.z_blended,
        "realized_vol_rank": row.realized_vol_rank,
        "skew_alignment": row.skew_alignment,
        "risk_reversal_25d": row.risk_reversal_25d,
        "fpi_flow": row.fpi_flow,
        "cot_net_pos": row.cot_net_pos,
        "cot_asset_mgr_net": row.cot_asset_mgr_net,
        "cot_lev_money_net": row.cot_lev_money_net,
        "ecb_balance_sheet": row.ecb_balance_sheet,
        "bund_btp_spread": row.bund_btp_spread,
        "boj_policy_rate": row.boj_policy_rate,
        "india_vix": row.india_vix,
        "inr_forward_premium": row.inr_forward_premium,
        "data_quality_notes": row.data_quality_notes,
    }
    _client().table("signals").upsert(payload, on_conflict="pair,date").execute()


def compute_write_hash(inputs: dict[str, Any]) -> str:
    """Return SHA-256 hex digest of sorted JSON-serialized inputs.

    Used for tamper-evident regime call verification.
    """
    canonical = json.dumps(inputs, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _publication_request(
    call: RegimeCall,
    signal_row: SignalRow,
    *,
    rationale: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
    supersedes_call_id: int | None = None,
) -> dict[str, Any]:
    """Validate and detach a complete, finite publication before any I/O."""
    if call.pair not in {"EURUSD", "USDJPY", "USDINR"}:
        raise ValueError("Publication pair is outside the locked universe")
    if (call.pair, call.date) != (signal_row.pair, signal_row.date):
        raise ValueError("Publication call and signal identity must match")
    if call.data_source not in {"live", "backtest"}:
        raise ValueError("Publication source must be live or backtest")
    if any(
        not isinstance(v, str) or not v.strip() for v in (call.model_version, call.strategy_version)
    ):
        raise ValueError("Publication requires explicit model and strategy versions")
    if call.predicted_direction not in {"BULLISH", "BEARISH", "NEUTRAL"}:
        raise ValueError("Publication requires an explicit published direction")
    if supersedes_call_id is not None and (
        isinstance(supersedes_call_id, bool)
        or not isinstance(supersedes_call_id, int)
        or supersedes_call_id <= 0
    ):
        raise ValueError("Publication predecessor must be a positive integer call ID")
    as_of = call.date.isoformat()
    call_payload = asdict(call)
    call_payload["date"] = as_of
    if correlation_id is not None:
        call_payload["correlation_id"] = correlation_id
    signal_payload = asdict(signal_row)
    signal_payload["date"] = as_of
    rationale_payload = (
        dict(rationale)
        if rationale is not None
        else {"confidence_explanation": "Rationale not supplied; signal snapshot retained."}
    )
    if rationale_payload.get("call_id") is not None:
        raise ValueError("Publication rationale cannot claim an existing call ID")
    rationale_payload.pop("call_id", None)
    for key, expected in (("pair", call.pair), ("date", as_of)):
        if key in rationale_payload and rationale_payload[key] != expected:
            raise ValueError("Publication rationale identity must match")
        rationale_payload[key] = expected
    request = {
        "p_call": call_payload,
        "p_signal": signal_payload,
        "p_rationale": rationale_payload,
        "p_supersedes_call_id": supersedes_call_id,
    }
    # Round-tripping also detaches mutable dataclass lists and refuses NaN/infinity.
    return cast(dict[str, Any], json.loads(json.dumps(request, allow_nan=False)))


def publish_regime_call(
    call: RegimeCall,
    signal_row: SignalRow,
    *,
    rationale: Mapping[str, Any] | None = None,
    correlation_id: str | None = None,
    supersedes_call_id: int | None = None,
) -> int:
    """Atomically append call, immutable signal evidence and rationale via one RPC."""
    request = _publication_request(
        call,
        signal_row,
        rationale=rationale,
        correlation_id=correlation_id,
        supersedes_call_id=supersedes_call_id,
    )
    result = _client().rpc("append_regime_publication", request).execute().data
    if isinstance(result, bool) or not isinstance(result, int) or result <= 0:
        raise RuntimeError("Atomic publication returned no durable integer call ID")
    return result


def write_regime_call(
    call: RegimeCall,
    *,
    correlation_id: str | None = None,
    write_hash: str | None = None,
) -> int | str | None:
    """Reject unbound publication; callers must supply immutable signal evidence."""
    raise RuntimeError("Use publish_regime_call with signal evidence and explicit provenance")


def _desk_open_card_payload(card: DeskOpenCardRow) -> dict[str, Any]:
    payload: dict[str, Any] = asdict(card)
    payload["date"] = _date_iso(card.date)
    return payload


def write_desk_open_card(card: DeskOpenCardRow) -> None:
    _client().table("desk_open_cards").upsert(
        _desk_open_card_payload(card), on_conflict="pair,date"
    ).execute()


def write_desk_open_cards_bulk(cards: Sequence[DeskOpenCardRow]) -> None:
    if not cards:
        return
    rows = [_desk_open_card_payload(c) for c in cards]
    _client().table("desk_open_cards").upsert(rows, on_conflict="pair,date").execute()


def write_call_rationale(rows: list[dict[str, Any]]) -> None:
    """Append retrospective rationale without replacing any existing explanation."""
    if not rows:
        return
    client = _client()
    for row in rows:
        call_id = row.get("call_id")
        if isinstance(call_id, bool) or not isinstance(call_id, int) or call_id <= 0:
            raise ValueError("Retrospective rationale requires a durable integer call ID")
        existing = client.table("call_rationale").select("*").eq("call_id", call_id).execute()
        prior = cast(list[dict[str, Any]], existing.data or [])
        if prior:
            if any(prior[0].get(key) != value for key, value in row.items()):
                raise ValueError("Existing rationale is immutable; publish an explicit new version")
            continue
        # A concurrent insertion may raise a uniqueness conflict; it cannot overwrite evidence.
        client.table("call_rationale").insert(dict(row)).execute()


def get_desk_open_cards_for_date(date_str: str) -> list[dict[str, Any]]:
    res = _client().table("desk_open_cards").select("*").eq("date", str(date_str)[:10]).execute()
    return cast(list[dict[str, Any]], res.data or [])


def get_rpc_fx_correlation_matrix() -> dict[str, dict[str, float]]:
    """Pairwise return correlations from Postgres (symmetric half-matrix JSON)."""

    res = _client().rpc("get_fx_correlation_matrix", {}).execute()
    raw = res.data
    if raw is None:
        return {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        return {}
    return _parse_corr_matrix_json(raw)


def _parse_corr_matrix_json(obj: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for k, v in obj.items():
        if not isinstance(v, dict):
            continue
        inner: dict[str, float] = {}
        for k2, v2 in v.items():
            if v2 is None:
                continue
            try:
                inner[str(k2)] = float(v2)
            except (TypeError, ValueError):
                continue
        if inner:
            out[str(k)] = inner
    return out


def get_latest_desk_open_card(pair: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("desk_open_cards")
        .select("*")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return rows[0] if rows else None


def update_desk_open_card_flags(
    pair: str,
    date_str: str,
    *,
    invalidation_triggered: bool | None = None,
    telemetry_status: str | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if invalidation_triggered is not None:
        payload["invalidation_triggered"] = invalidation_triggered
    if telemetry_status is not None:
        payload["telemetry_status"] = telemetry_status
    if not payload:
        return
    (
        _client()
        .table("desk_open_cards")
        .update(payload)
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )


def update_desk_open_card_telemetry_audit(
    pair: str, date_str: str, telemetry_audit_patch: Mapping[str, Any]
) -> None:
    current = (
        _client()
        .table("desk_open_cards")
        .select("telemetry_audit")
        .eq("pair", pair)
        .eq("date", date_str)
        .maybe_single()
        .execute()
    )
    current_row = cast(dict[str, Any] | None, current.data if current is not None else None)
    existing = (
        cast(dict[str, Any], current_row.get("telemetry_audit"))
        if current_row and isinstance(current_row.get("telemetry_audit"), dict)
        else {}
    )
    merged = {**existing, **dict(telemetry_audit_patch)}
    (
        _client()
        .table("desk_open_cards")
        .update({"telemetry_audit": merged})
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )


def get_validation_log_for_call(call_id: int | str) -> dict[str, Any] | None:
    """Read one current canonical evaluation by immutable published identity."""
    if isinstance(call_id, bool) or not isinstance(call_id, (int, str)) or call_id == "":
        raise ValueError("A persisted call_id is required")
    res = (
        _client()
        .table("validation_log")
        .select("*")
        .eq("call_id", call_id)
        .eq("evaluation_version", EVALUATION_VERSION)
        .eq("is_superseded", False)
        .maybe_single()
        .execute()
    )
    return cast(dict[str, Any], res.data) if res and isinstance(res.data, dict) else None


def write_validation_row(row: Mapping[str, Any]) -> None:
    """Atomically append or complete an evaluation through the database contract.

    PostgreSQL serializes writes for a published call, preserves completed
    horizons and validates identity. No direct insert or schema fallback is safe.
    """
    payload = dict(row)
    call_id = payload.get("call_id")
    if call_id is None or isinstance(call_id, bool) or not str(call_id).strip():
        raise ValueError("validation requires a persisted call_id")
    version = payload.setdefault("evaluation_version", EVALUATION_VERSION)
    if version != EVALUATION_VERSION:
        raise ValueError("evaluation_version does not match the canonical calculator")
    _client().rpc("append_validation_evaluation", {"p_payload": payload}).execute()


def write_brief(
    date_str: str,
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    analysis: str,
    primary_driver: str,
) -> None:
    payload = cast(
        dict[str, Any],
        {
            "date": date_str,
            "pair": pair,
            "regime": regime,
            "confidence": confidence,
            "composite": composite,
            "analysis": analysis,
            "primary_driver": primary_driver or None,
        },
    )
    _client().table("brief").upsert(payload, on_conflict="pair,date").execute()


def write_brief_log(
    date_str: str,
    brief_text: str,
    macro_context: str,
    *,
    dollar_dominance: float | None = None,
    idiosyncratic_outlier: str | None = None,
    sentiment_json: Mapping[str, Any] | None = None,
    pair_regimes: Mapping[str, str] | None = None,
    structured_summary: Mapping[str, Any] | None = None,
) -> None:
    """Upsert unified daily summary into `brief_log` (systemic + sentiment pre-baked for UI)."""
    payload: dict[str, Any] = {
        "date": date_str,
        "brief_text": brief_text,
        "macro_context": macro_context or None,
        "dollar_dominance": float(dollar_dominance) if dollar_dominance is not None else None,
        "idiosyncratic_outlier": idiosyncratic_outlier,
        "sentiment_json": dict(sentiment_json) if sentiment_json is not None else None,
    }
    if structured_summary is not None:
        payload["structured_summary"] = dict(structured_summary)
    if pair_regimes is not None:
        payload["pair_regimes"] = dict(pair_regimes)
        for pair, regime in pair_regimes.items():
            col = f"{pair.lower()}_regime"
            if col in {
                "eurusd_regime",
                "usdjpy_regime",
                "usdinr_regime",
            }:
                payload[col] = regime
    _client().table("brief_log").upsert(payload, on_conflict="date").execute()


def get_rpc_calculate_dual_correlation(pair: str, lookback: int) -> float | None:
    """Pearson corr: pair log-returns vs mean of other FX basket log-returns."""

    res = (
        _client()
        .rpc(
            "calculate_fx_basket_correlation",
            {"p_pair": pair, "p_lookback": int(lookback)},
        )
        .execute()
    )
    raw: Any = res.data
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) > 0:
        raw = raw[0]
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def write_macro_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        ev = cast(dict[str, Any], dict(event))
        if isinstance(ev.get("date"), date):
            ev["date"] = _date_iso(ev["date"])
        _client().table("macro_events").upsert(ev, on_conflict="date,event").execute()


def write_ai_request(date_str: str, purpose: str, model: str) -> None:
    _client().rpc(
        "increment_ai_usage", {"p_date": date_str, "p_purpose": purpose, "p_model": model}
    ).execute()


def get_ai_request_count_today(date_str: str) -> int:
    res = _client().table("ai_usage_log").select("request_count").eq("date", date_str).execute()
    rows = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        return 0
    return int(sum(int(r.get("request_count", 0)) for r in rows))


_CURRENT_PUBLICATION_PAIRS = frozenset({"EURUSD", "USDJPY", "USDINR"})


def _publication_read_cutoff(value: date | str) -> str:
    if isinstance(value, datetime):
        raise ValueError("Publication cutoff must be a calendar date, not a timestamp")
    try:
        parsed = value if isinstance(value, date) else date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Publication cutoff must be an ISO calendar date") from exc
    return parsed.isoformat()


def _publication_read_instant(value: datetime | str) -> str:
    try:
        parsed = (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            if isinstance(value, str)
            else value
        )
    except ValueError as exc:
        raise ValueError("Publication availability cutoff must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Publication availability cutoff must include an explicit timezone")
    return parsed.astimezone(UTC).isoformat()


def get_current_live_regime_history(
    pair: str,
    *,
    as_of: date | str,
    session_limit: int = 5000,
    strictly_before: bool = False,
    published_before: datetime | str | None = None,
) -> list[dict[str, Any]]:
    """Return latest live-v2 publication per session, newest session first.

    Raw publications are paged before session deduplication. This matters when
    one session has enough appended versions to fill a Supabase response page.
    """
    if pair not in _CURRENT_PUBLICATION_PAIRS:
        raise ValueError("Current publication pair is outside the locked universe")
    if (
        isinstance(session_limit, bool)
        or not isinstance(session_limit, int)
        or session_limit < 0
    ):
        raise ValueError("session_limit must be a nonnegative integer")
    if session_limit == 0:
        return []

    cutoff = _publication_read_cutoff(as_of)
    query = (
        _client()
        .table("regime_calls")
        .select("*")
        .eq("pair", pair)
        .eq("data_source", "live")
        .eq("strategy_version", "v2")
    )
    query = query.lt("date", cutoff) if strictly_before else query.lte("date", cutoff)
    if published_before is not None:
        # PostgreSQL comparisons exclude NULL created_at values. Decision-state
        # inference therefore uses only publications known before this instant.
        query = query.lt("created_at", _publication_read_instant(published_before))
    query = query.order("date", desc=True).order("id", desc=True)

    selected: list[dict[str, Any]] = []
    seen_sessions: set[str] = set()
    offset = 0
    page_size = 1000
    while len(selected) < session_limit:
        res = query.range(offset, offset + page_size - 1).execute()
        if res is None or not isinstance(res.data, list):
            raise RuntimeError("Current publication history returned an invalid response")
        page = cast(list[dict[str, Any]], res.data)
        for row in page:
            session = str(row.get("date") or "")[:10]
            if not session or session in seen_sessions:
                continue
            seen_sessions.add(session)
            selected.append(row)
            if len(selected) == session_limit:
                break
        if len(page) < page_size:
            break
        offset += page_size
    return selected


def get_current_live_regime_call(
    pair: str,
    *,
    as_of: date | str,
    strictly_before: bool = False,
    published_before: datetime | str | None = None,
) -> dict[str, Any] | None:
    """Return the deterministic current live-v2 call at an explicit cutoff."""
    rows = get_current_live_regime_history(
        pair,
        as_of=as_of,
        session_limit=1,
        strictly_before=strictly_before,
        published_before=published_before,
    )
    return rows[0] if rows else None


def get_publication_signal_for_call(call_id: int) -> dict[str, Any] | None:
    """Read the immutable signal snapshot for exactly one selected call ID."""
    if isinstance(call_id, bool) or not isinstance(call_id, int) or call_id <= 0:
        raise ValueError("Publication evidence requires a positive integer call ID")
    res = (
        _client()
        .table("publication_evidence")
        .select("signal_payload")
        .eq("call_id", call_id)
        .maybe_single()
        .execute()
    )
    data = res.data if res is not None else None
    if data is None:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("signal_payload"), dict):
        raise RuntimeError("Publication evidence contains no valid signal snapshot")
    return cast(dict[str, Any], data["signal_payload"])


def get_latest_regime_call(pair: str) -> dict[str, Any] | None:
    """Compatibility wrapper for descriptive reads, cut off at today's UTC date."""
    return get_current_live_regime_call(pair, as_of=datetime.now(UTC).date())


def get_brief_for_date(pair: str, date_str: str) -> str | None:
    res = (
        _client().table("brief").select("analysis").eq("pair", pair).eq("date", date_str).execute()
    )
    data = cast(list[dict[str, Any]], res.data or [])
    return str(data[0]["analysis"]) if data else None


def get_signal_for_pair_date(pair: str, date_str: str) -> dict[str, Any] | None:
    res = _client().table("signals").select("*").eq("pair", pair).eq("date", date_str).execute()
    data = cast(list[dict[str, Any]], res.data or [])
    return data[0] if data else None


def get_historical_signals(pair: str, limit: int = 1260) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("signals")
        .select(
            "date,rate_diff_2y,rate_diff_10y,breakeven_inflation_10y,"
            "cot_percentile,realized_vol_5d,realized_vol_20d,oi_delta,spot,cross_asset_us10y",
        )
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def delete_pipeline_data_for_date(date_str: str, *, force: bool = False) -> None:
    """Retired: a rollback cannot delete original research observations."""
    raise RuntimeError(
        "Immutable originals cannot be purged, including with force=True. "
        "Publish an explicit versioned correction and retain the original ledger."
    )


def write_pipeline_error(
    step: str,
    error_type: str,
    message: str,
    traceback_str: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Log a structured pipeline exception to ``pipeline_errors``."""
    payload: dict[str, Any] = {
        "step": step,
        "error_type": error_type,
        "message": message,
    }
    if traceback_str is not None:
        payload["traceback"] = traceback_str
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    try:
        _client().table("pipeline_errors").insert(payload).execute()
    except Exception:
        pass


def _log_audit(
    operation: str,
    table_name: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    row_id: Any | None = None,
    correlation_id: str | None = None,
) -> None:
    """Write a single row to ``audit_log``.  Silently ignores errors."""
    payload: dict[str, Any] = {
        "operation": operation,
        "table_name": table_name,
        "old_value": old_value,
        "new_value": new_value,
        "correlation_id": correlation_id,
    }
    if row_id is not None:
        payload["row_id"] = row_id
    try:
        _client().table("audit_log").insert(payload).execute()
    except Exception:
        pass


def get_historical_regime_calls(pair: str, limit: int | None = 5000) -> list[dict[str, Any]]:
    """Read the newest requested calls, oldest first; None retrieves all pages."""
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError("limit must be a nonnegative integer or None")
    if limit == 0:
        return []
    query = (
        _client()
        .table("regime_calls")
        .select(
            "id,date,pair,regime,signal_composite,rate_signal,predicted_direction,"
            "confidence,data_source,strategy_version,model_version"
        )
        .eq("pair", pair)
        .order("date", desc=True)
        .order("id", desc=True)
    )
    rows: list[dict[str, Any]] = []
    while limit is None or len(rows) < limit:
        size = 1000 if limit is None else min(1000, limit - len(rows))
        res = query.range(len(rows), len(rows) + size - 1).execute()
        page = cast(list[dict[str, Any]], res.data or [])
        rows.extend(page)
        if len(page) < size:
            break
    return list(reversed(rows))


def update_macro_event_ai_brief(date_str: str, event: str, ai_brief: str) -> None:
    (
        _client()
        .table("macro_events")
        .update({"ai_brief": ai_brief})
        .eq("date", date_str)
        .eq("event", event)
        .execute()
    )


def list_high_impact_events_needing_brief(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("macro_events")
        .select("*")
        .eq("impact", "HIGH")
        .gte("date", start_iso)
        .lte("date", end_iso)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return [r for r in rows if r.get("ai_brief") in (None, "")]


def write_historical_macro_surprises(rows: list[Mapping[str, Any]]) -> None:
    """Batch upsert historical release rows (consensus vs actual)."""
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for r in rows:
        row = cast(dict[str, Any], dict(r))
        if isinstance(row.get("date"), date):
            row["date"] = _date_iso(row["date"])
        payload_rows.append(row)
    (
        _client()
        .table("historical_macro_surprises")
        .upsert(payload_rows, on_conflict="event_name,date")
        .execute()
    )


def fetch_event_aliases() -> list[dict[str, Any]]:
    res = _client().table("event_aliases").select("canonical_name,alias_name").execute()
    return cast(list[dict[str, Any]], res.data or [])


def get_historical_macro_surprises(event_name: str) -> list[dict[str, Any]]:
    from src.analysis.event_name_normalize import expand_event_names_for_query

    names = expand_event_names_for_query(event_name)
    res = (
        _client()
        .table("historical_macro_surprises")
        .select("date,event_name,surprise_direction,surprise_bps")
        .in_("event_name", names)
        .order("date", desc=True)
        .limit(10000)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def get_historical_macro_surprises_date_universe(limit: int = 50000) -> list[dict[str, Any]]:
    """All (date, event_name) rows for pure-date filtering (multi-release days)."""
    res = (
        _client()
        .table("historical_macro_surprises")
        .select("date,event_name")
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def write_historical_prices(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str | None = None,
) -> None:
    """Reject legacy canonical-close writes before opening a database client.

    Provider bars belong in the append-only observation archive. Promotion to
    ``historical_prices`` remains blocked until a source-specific final-close
    qualification and a migration define that boundary.
    """
    if not rows:
        return
    raise RuntimeError(
        "Direct historical_prices writes are retired. Archive provider observations "
        "with archive_price_observations; canonical closes require an explicit "
        "source-qualification policy and database migration."
    )


def write_historical_yields(rows: list[dict[str, Any]]) -> None:
    """Bulk upsert historical_yields rows on date,series_id."""
    if not rows:
        return
    _client().table("historical_yields").upsert(rows, on_conflict="date,series_id").execute()


def get_rpc_historical_analogs(
    pair: str,
    as_of_date: str,
    current_trend: float,
    current_comp: float,
    *,
    limit_rows: int = 3,
) -> list[dict[str, Any]]:
    """Run ``match_historical_analogs`` in Postgres (no deep history fetch in Python)."""

    res = (
        _client()
        .rpc(
            "match_historical_analogs",
            {
                "target_pair": pair,
                "as_of_date": as_of_date,
                "current_trend": current_trend,
                "current_comp": current_comp,
                "limit_rows": limit_rows,
            },
        )
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def get_exact_historical_price_for_date(
    pair: str, date_str: str
) -> dict[str, Any] | None:
    """Read an exact dated close for validation; never fill missing sessions."""
    if pair not in _CURRENT_PUBLICATION_PAIRS:
        raise ValueError("Historical validation price requires a supported pair")
    if not isinstance(date_str, str):
        raise ValueError("Historical price date must be YYYY-MM-DD")
    try:
        requested = date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError("Historical price date must be YYYY-MM-DD") from exc
    if requested.isoformat() != date_str:
        raise ValueError("Historical price date must be YYYY-MM-DD")
    response = (
        _client()
        .table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .eq("date", date_str)
        .maybe_single()
        .execute()
    )
    if response is None:
        raise RuntimeError("Historical price query returned no response")
    raw = response.data
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Historical price query returned an invalid row")
    if raw.get("pair") != pair or raw.get("date") != date_str:
        raise ValueError("Historical price identity does not match the requested session")
    return dict(raw)


def get_historical_price_for_date(pair: str, date_str: str) -> dict[str, Any] | None:
    """Return a single historical price row for ``pair`` on ``date_str``.

    Prefers ``close``; falls back to the latest available price on or before
    ``date_str`` when an exact match is missing (forward-fill for weekends).
    """
    client = _client()
    # Exact match first
    res = (
        client.table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .eq("date", str(date_str)[:10])
        .maybe_single()
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)

    # Fallback: nearest earlier date (weekend / holiday gap)
    res2 = (
        client.table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .lte("date", str(date_str)[:10])
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if res2 is not None:
        raw = res2.data
        if isinstance(raw, list) and raw:
            return cast(dict[str, Any], raw[0])
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def _validation_log_has_t5_for_call(call_id: Any, call_date: str, pair: str) -> bool:
    """Return True when a current (non-superseded) validation_log row exists."""
    client = _client()

    def _by_call_id(include_superseded_filter: bool) -> Any:
        q = (
            client.table("validation_log")
            .select("brier_score_t5")
            .eq("call_id", call_id)
            .not_.is_("brier_score_t5", "null")
        )
        if include_superseded_filter:
            q = q.eq("is_superseded", False)
        return q.maybe_single().execute()

    def _by_date_pair(include_superseded_filter: bool) -> Any:
        q = (
            client.table("validation_log")
            .select("brier_score_t5")
            .eq("date", call_date)
            .eq("pair", pair)
            .not_.is_("brier_score_t5", "null")
        )
        if include_superseded_filter:
            q = q.eq("is_superseded", False)
        return q.maybe_single().execute()

    if call_id is not None:
        try:
            vres = _by_call_id(include_superseded_filter=True)
            if vres is not None and vres.data is not None:
                return True
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "column validation_log.is_superseded does not exist" in msg:
                try:
                    vres = _by_call_id(include_superseded_filter=False)
                    if vres is not None and vres.data is not None:
                        return True
                except Exception:
                    pass
            elif "column validation_log.call_id does not exist" not in msg:
                pass
        except Exception:
            pass

    try:
        vres = _by_date_pair(include_superseded_filter=True)
        if vres is not None and vres.data is not None:
            return True
    except APIError as exc:
        msg = str(getattr(exc, "message", "")) or str(exc)
        if "column validation_log.is_superseded does not exist" in msg:
            try:
                vres = _by_date_pair(include_superseded_filter=False)
                if vres is not None and vres.data is not None:
                    return True
            except Exception:
                pass
        else:
            pass
    except Exception:
        pass

    return False


def get_unvalidated_regime_calls(limit: int | None = None) -> list[dict[str, Any]]:
    """Return calls with at least one horizon still missing, oldest first.

    A T+5 result is not a completed T+20 evaluation. Brier cannot indicate
    maturity either: an abstention has no directional Brier score. The caller
    checks whether the missing horizon has matured before fetching its price.
    ``limit`` bounds returned incomplete calls, not the initial database page.
    """
    if limit is not None and limit <= 0:
        return []
    query = (
        _client()
        .table("regime_calls")
        .select("id,date,pair,regime,rate_signal,predicted_direction,confidence")
        .order("date", desc=False)
        .order("id", desc=False)
    )
    unvalidated: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        res = query.range(offset, offset + page_size - 1).execute()
        calls = cast(list[dict[str, Any]], res.data or [])
        for call in calls:
            existing = get_validation_log_for_call(call["id"])
            same_call = existing is not None and existing.get("call_id") == call.get("id")
            complete = (
                existing is not None
                and same_call
                and all(
                    existing.get(key) is not None
                    for key in ("log_return_t5_bps", "log_return_t20_bps")
                )
            )
            if not complete:
                unvalidated.append(call)
                if limit is not None and len(unvalidated) >= limit:
                    return unvalidated
        if len(calls) < page_size:
            return unvalidated
        offset += page_size


def get_historical_prices(pair: str, limit: int = 10000) -> list[dict[str, Any]]:
    """Return the latest ``limit`` rows for the pair, oldest-first (for time-series walks)."""
    res = (
        _client()
        .table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def write_research_analogs(rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        return
    payload_rows = [cast(dict[str, Any], dict(r)) for r in rows]
    (
        _client()
        .table("research_analogs")
        .upsert(payload_rows, on_conflict="pair,as_of_date,rank")
        .execute()
    )


def write_simulation_results(rows: list[dict[str, Any]]) -> None:
    """Bulk insert simulation_results rows."""
    if not rows:
        return
    _client().table("simulation_results").insert(rows).execute()


def get_latest_research_analogs(pair: str, as_of_date: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("research_analogs")
        .select(
            "as_of_date,pair,rank,match_date,match_score,forward_30d_return,regime_stability,context_label,current_trend_5d,matched_trend_5d,current_composite",
        )
        .eq("pair", pair)
        .eq("as_of_date", as_of_date)
        .order("rank", desc=False)
        .limit(3)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def write_event_risk_matrices(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = cast(dict[str, Any], dict(row))
        if isinstance(payload.get("date"), date):
            payload["date"] = _date_iso(payload["date"])
        payload_rows.append(payload)
    (
        _client()
        .table("event_risk_matrices")
        .upsert(payload_rows, on_conflict="date,pair,event_name")
        .execute()
    )


def get_event_risk_matrix(date_str: str, pair: str, event_name: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("event_risk_matrices")
        .select(
            "date,pair,event_name,active_regime,sample_size,median_mie_multiplier,"
            "beat_median_return,miss_median_return,inline_median_return,asymmetry_ratio,"
            "asymmetry_direction,t1_exhaustion_p2_5,t1_exhaustion_p16,t1_exhaustion_p84,"
            "t1_exhaustion_p97_5,t1_tail_risk_p95,t1_tail_risk_p05",
        )
        .eq("date", date_str)
        .eq("pair", pair)
        .eq("event_name", event_name)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return rows[0] if rows else None


def get_strategy_ledger_entry(
    ledger_date: date | str,
    pair: str,
    regime: str,
    primary_driver: str,
) -> dict[str, Any] | None:
    iso = _date_iso(ledger_date)
    res = (
        _client()
        .table("strategy_ledger")
        .select("*")
        .eq("date", iso)
        .eq("pair", pair)
        .eq("regime", regime)
        .eq("primary_driver", primary_driver)
        .maybe_single()
        .execute()
    )
    if res is None:
        return None
    raw = res.data
    if not isinstance(raw, dict):
        return None
    return cast(dict[str, Any], raw)


def write_ledger_entry(row: dict[str, Any]) -> None:
    payload = cast(dict[str, Any], dict(row))
    if isinstance(payload.get("date"), date):
        payload["date"] = _date_iso(payload["date"])
    (
        _client()
        .table("strategy_ledger")
        .upsert(payload, on_conflict="date,pair,regime,primary_driver")
        .execute()
    )


def get_open_ledger_entries(pair: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("strategy_ledger")
        .select("*")
        .eq("pair", pair)
        .is_("t5_hit", "null")
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def update_ledger_entries(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = cast(dict[str, Any], dict(row))
        if isinstance(payload.get("date"), date):
            payload["date"] = _date_iso(payload["date"])
        payload_rows.append(payload)
    (
        _client()
        .table("strategy_ledger")
        .upsert(payload_rows, on_conflict="date,pair,regime,primary_driver")
        .execute()
    )


def research_memo_exists(link_url: str) -> bool:
    """Return True if a research_memo with this link_url already exists."""
    res = (
        _client()
        .table("research_memos")
        .select("id")
        .eq("link_url", link_url)
        .maybe_single()
        .execute()
    )
    return res is not None and res.data is not None


def write_research_memo(
    *,
    date_str: str,
    title: str,
    raw_content: str,
    ai_thesis_summary: list[str],
    link_url: str,
) -> None:
    payload: dict[str, Any] = {
        "date": str(date_str)[:10],
        "title": title,
        "raw_content": raw_content,
        "ai_thesis_summary": ai_thesis_summary,
        "link_url": link_url,
    }
    _client().table("research_memos").upsert(payload, on_conflict="link_url").execute()


def _pg_conn(max_retries: int = 5) -> Any:
    """Raw Postgres connection for bulk backfill writes (pg8000)."""
    import ssl
    import time

    import pg8000.native

    ctx = ssl._create_unverified_context()
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "SUPABASE_DB_PASSWORD must be set in the environment. "
            "Get it from Supabase Dashboard → Project Settings → Database → Connection string."
        )
    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return pg8000.native.Connection(
                host=host,
                database="postgres",
                user="postgres",
                password=password,
                ssl_context=ctx,
                timeout=30,
            )
        except Exception as e:
            last_err = e
            logger.warning("DB connection attempt %d/%d failed: %s", attempt + 1, max_retries, e)
            time.sleep(min(2**attempt, 30))
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"Failed to connect to database after {max_retries} attempts")


def bulk_write_backfill_results(
    pair: str,
    results: Sequence[tuple[SignalRow, RegimeCall]],
) -> None:
    """Append versioned replay calls; completed prefixes are safe to retry."""
    identities: set[tuple[str, date, str, str, str | None]] = set()
    for signal_row, call in results:
        if call.pair != pair or call.data_source != "backtest":
            raise ValueError(
                "Historical publication requires the requested pair and backtest source"
            )
        _publication_request(call, signal_row)
        identity = (
            call.pair,
            call.date,
            call.data_source,
            call.strategy_version,
            call.model_version,
        )
        if identity in identities:
            raise ValueError("Historical batch contains duplicate publication identities")
        identities.add(identity)
    for signal_row, call in results:
        publish_regime_call(call, signal_row)
    logger.info("Appended %d versioned replay publications for %s", len(results), pair)


def get_latest_research_memo_thesis_bullets() -> list[str]:
    """Latest memo thesis only (daily desk briefs must not load raw_content)."""

    res = (
        _client()
        .table("research_memos")
        .select("ai_thesis_summary")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        return []
    raw = rows[0].get("ai_thesis_summary")
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out[:5]


# ---------------------------------------------------------------------------
# Round 3 Phase 2 — Aggregate stats read/write
# ---------------------------------------------------------------------------


def _normalize_validation_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a legacy validation_log row to the modern schema.

    Legacy schema stores returns as decimals (``actual_return_5d``) and
    correctness in ``correct_5d``.  Modern schema uses bps
    (``log_return_t5_bps``) and horizon-specific keys.  This helper maps
    the legacy fields so that ``aggregate.py`` can consume either schema.
    """
    out = dict(row)

    # Map legacy 5d fields → modern T+5 fields
    ret_5d = row.get("actual_return_5d")
    if ret_5d is not None and "log_return_t5_bps" not in row:
        out["log_return_t5_bps"] = float(ret_5d) * 10_000.0

    corr_5d = row.get("correct_5d")
    if corr_5d is not None and "correct_t5" not in row:
        out["correct_t5"] = bool(corr_5d)

    if "actual_direction" in row and "actual_direction_t5" not in row:
        out["actual_direction_t5"] = row["actual_direction"]

    # Compute Brier score on-the-fly if missing but we have confidence + correctness
    conf = row.get("confidence")
    if conf is not None and "brier_score_t5" not in row:
        if out.get("correct_t5") is True:
            out["brier_score_t5"] = (float(conf) - 1.0) ** 2
        elif out.get("correct_t5") is False:
            out["brier_score_t5"] = float(conf) ** 2

    # Legacy schema has no separate T+20 columns — leave them absent
    return out


def get_validation_log_for_stats(
    pair_filter: str | None = None,
    lookback_days: int | None = None,
    as_of_date: date | None = None,
) -> list[dict[str, Any]]:
    """Read all published calls joined by ID to their current evaluation.

    Missing evaluations stay in the population with null outcomes. The read-only
    view owns the join so backend and public readers cannot disagree on coverage.
    """
    q = (
        _client()
        .table("validation_observations")
        .select("*")
        .eq("evaluation_version", EVALUATION_VERSION)
        .eq("population_version", "published-calls-v1")
        .order("id")
    )
    if pair_filter:
        q = q.eq("pair", pair_filter)
    anchor = as_of_date or date.today()
    q = q.lte("date", anchor.isoformat())
    if lookback_days is not None and lookback_days > 0:
        cutoff = anchor - timedelta(days=lookback_days - 1)
        q = q.gte("date", cutoff.isoformat())
    rows: list[dict[str, Any]] = []
    page_size = 1000
    while True:
        res = q.range(len(rows), len(rows) + page_size - 1).execute()
        page = cast(list[dict[str, Any]], res.data or [])
        rows.extend(page)
        if len(page) < page_size:
            return rows


def write_validation_stats(row: Mapping[str, Any]) -> None:
    """Persist one exact evidence-group snapshot without overwriting other groups."""
    payload = dict(row)
    keys = (
        "data_source",
        "strategy_version",
        "model_version",
        "evaluation_version",
        "population_version",
    )
    if any(not isinstance(payload.get(k), str) or not payload[k].strip() for k in keys):
        raise ValueError("validation stats require explicit evidence-group metadata")
    window = payload.get("window_days")
    if isinstance(window, bool) or not isinstance(window, int) or window < 0:
        raise ValueError("validation stats require a nonnegative window_days")
    _client().table("validation_stats").upsert(
        payload,
        on_conflict=(
            "as_of_date,pair,data_source,strategy_version,"
            "model_version,evaluation_version,window_days,population_version"
        ),
    ).execute()


def get_latest_validation_stats_per_pair() -> list[dict[str, Any]]:
    """Read the latest snapshot for each pair under the current live model only."""
    out: list[dict[str, Any]] = []
    for pair in ("EURUSD", "USDJPY", "USDINR", "ALL"):
        res = (
            _client()
            .table("validation_stats")
            .select("*")
            .eq("pair", pair)
            .eq("data_source", "live")
            .eq("strategy_version", "v2")
            .eq("model_version", "2.0-live")
            .eq("evaluation_version", EVALUATION_VERSION)
            .eq("window_days", 0)
            .eq("population_version", "published-calls-v1")
            .order("as_of_date", desc=True)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        if rows:
            out.append(rows[0])
    return out


def write_pipeline_run(row: Mapping[str, Any]) -> None:
    """Replace the dated health snapshot in one database upsert."""
    payload = cast(dict[str, Any], dict(row))
    raw_date = str(payload.get("date") or "")
    payload["date"] = date.fromisoformat(raw_date).isoformat()
    _client().table("pipeline_runs").upsert(payload, on_conflict="date").execute()


def get_pipeline_runs_for_dates(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    """Fetch pipeline_runs rows in a date range, oldest first."""
    res = (
        _client()
        .table("pipeline_runs")
        .select("*")
        .gte("date", start_iso)
        .lte("date", end_iso)
        .order("date", desc=False)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def get_pipeline_run_for_date(date_str: str) -> dict[str, Any] | None:
    """Fetch a single pipeline_runs row for a date."""
    res = (
        _client()
        .table("pipeline_runs")
        .select("*")
        .eq("date", str(date_str)[:10])
        .maybe_single()
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def count_signals_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("signals")
        .select("id", count=CountMethod.exact)
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def count_regime_calls_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("regime_calls")
        .select("id", count=CountMethod.exact)
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def get_regime_calls_dqs_for_date(date_str: str) -> list[float]:
    res = (
        _client()
        .table("regime_calls")
        .select("data_quality_score")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    scores: list[float] = []
    for r in rows:
        v = r.get("data_quality_score")
        if v is not None:
            try:
                scores.append(float(v))
            except (TypeError, ValueError):
                pass
    return scores


def count_validation_log_for_date(date_str: str) -> int:
    """Count current (non-superseded) validation_log rows for a date."""
    try:
        res = (
            _client()
            .table("validation_log")
            .select("id", count=CountMethod.exact)
            .eq("date", str(date_str)[:10])
            .eq("is_superseded", False)
            .execute()
        )
        return getattr(res, "count", 0) or 0
    except APIError as exc:
        msg = str(getattr(exc, "message", "")) or str(exc)
        if "column validation_log.is_superseded does not exist" in msg:
            res = (
                _client()
                .table("validation_log")
                .select("id", count=CountMethod.exact)
                .eq("date", str(date_str)[:10])
                .execute()
            )
            return getattr(res, "count", 0) or 0
        raise


def brief_log_exists_for_date(date_str: str) -> bool:
    res = (
        _client().table("brief_log").select("id").eq("date", str(date_str)[:10]).limit(1).execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return bool(rows)


def macro_events_with_ai_briefs_for_date(date_str: str) -> tuple[int, int]:
    """Return (total_high_impact_events, events_with_ai_briefs) for date."""
    res = (
        _client()
        .table("macro_events")
        .select("ai_brief")
        .eq("date", str(date_str)[:10])
        .eq("impact", "HIGH")
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    total = len(rows)
    with_brief = sum(1 for r in rows if r.get("ai_brief") not in (None, ""))
    return total, with_brief


def get_pipeline_errors_for_date(date_str: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("pipeline_errors")
        .select("step,error_type,message")
        .eq("run_date", str(date_str)[:10])
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])
