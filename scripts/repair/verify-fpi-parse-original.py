"""Offline original-report bridge through the real private FPI parse database.

The parent owns the task-local PostgreSQL runtime. This verifier creates only a
unique disposable database and never sends provider requests or uses credentials.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
CAPTURE_DIR = Path("C:/Users/sakha/.agent-reach/fxregimelab-fpi-evidence")
DB = "fxfpioriginal_" + uuid.uuid4().hex
BASE = [
    "wsl",
    "-d",
    "Ubuntu-24.04",
    "--",
    "/usr/lib/postgresql/17/bin/psql",
    "-h",
    "/home/shreyash/.local/state/fxregime-repair/socket",
    "-p",
    "55437",
    "-X",
    "-qAt",
    "-v",
    "ON_ERROR_STOP=1",
]


def _original_parse_sql(statement: str, *, database: str = DB) -> str:
    result = subprocess.run(
        BASE + ["-d", database],
        input=statement.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )
    if result.returncode:
        # Do not print a statement or server context that might contain private HTML.
        raise RuntimeError("Original FPI parse SQL verification failed")
    return result.stdout.decode("utf-8").strip()


def _original_parse_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _original_parser_bundle() -> bytes:
    files = {}
    for name in ("fpi_parser.py", "fpi_observation.py"):
        body = (ROOT / "pipeline/src/research" / name).read_bytes()
        files[name] = {
            "sha256": hashlib.sha256(body).hexdigest(),
            "body_base64": base64.b64encode(body).decode("ascii"),
        }
    return json.dumps(
        {
            "format": "fpi-local-verification-bundle-v1",
            "purpose": "retention verification, not qualified runner evidence",
            "files": files,
            "python": sys.version,
            "dependencies": {
                name: importlib.metadata.version(name) for name in ("beautifulsoup4", "soupsieve")
            },
            "html_parser": "html.parser",
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def verify_original_fpi_parse_bridge() -> None:
    from src.db import writer
    from src.research.fpi_capture import FpiCapture, build_fpi_capture
    from src.research.fpi_parse_record import (
        FpiArtifact,
        FpiParseRecord,
        build_fpi_artifact,
        build_fpi_parse_record,
        restore_fpi_parse_record,
        validate_fpi_artifact,
    )
    from src.research.fpi_selection import FpiParsedDay, FpiParseResult

    spec = importlib.util.spec_from_file_location(
        "original_fpi_source_verifier", ROOT / "pipeline/scripts/verify_fpi_source_capture.py"
    )
    assert spec is not None and spec.loader is not None
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    inputs = []
    for name in ("latest", "monthly"):
        days, retrieved_at = original._verify_capture(CAPTURE_DIR, name)
        expected = original._CAPTURES[name]
        receipt = json.loads((CAPTURE_DIR / expected["receipt"]).read_bytes())
        # Pinned receipt retains seven digits. Python truncation floors request
        # start; the source verifier separately ceilings retrieval completion.
        requested_at = datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00"))
        capture = build_fpi_capture(
            body=(CAPTURE_DIR / expected["html"]).read_bytes(),
            source_url=expected["source_url"],
            requested_at=requested_at,
            retrieved_at=retrieved_at,
            http_status=200,
        )
        inputs.append((capture, days))
    assert [len(days) for _, days in inputs] == [1, 18]
    assert inputs[0][1][0].observation.document_json == inputs[1][1][-1].observation.document_json
    assert inputs[0][1][0].observation.net_hundredths_cr == -655271
    artifact_bytes = _original_parser_bundle()
    artifact = build_fpi_artifact(kind="PARSER", body=artifact_bytes)

    calls = []

    def original_rpc(method: str, parameters: dict[str, str]) -> MagicMock:
        fields = {
            "append_fpi_capture": ("p_capture_sha256", "p_document_json"),
            "append_fpi_artifact": ("p_artifact_sha256", "p_document_json"),
            "append_fpi_parse_result": ("p_parse_id", "p_record_sha256", "p_document_json"),
        }
        assert method in fields and set(parameters) == set(fields[method])
        calls.append(method)
        arguments = ",".join(_original_parse_literal(parameters[key]) for key in fields[method])

        def execute() -> MagicMock:
            result = _original_parse_sql(
                "SET ROLE service_role; SELECT public." + method + "(" + arguments + ");"
            )
            return MagicMock(data=json.loads(result))

        return MagicMock(execute=execute)

    _original_parse_sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        _original_parse_sql(
            (ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8")
        )
        for name in (
            "20260927000010_fpi_capture_storage.sql",
            "20260927000011_fpi_parse_storage.sql",
        ):
            _original_parse_sql((ROOT / "supabase/migrations" / name).read_text(encoding="utf-8"))
        with patch.object(writer, "_client", return_value=MagicMock(rpc=original_rpc)):
            first_artifact = writer.archive_fpi_artifact(artifact)
            assert first_artifact["inserted"] is True
            assert writer.archive_fpi_artifact(artifact) == {**first_artifact, "inserted": False}
            saved_artifact = _original_parse_sql(
                "SET ROLE service_role; SELECT document_json FROM fpi_implementation_artifacts "
                "WHERE kind='PARSER' AND artifact_sha256="
                + _original_parse_literal(artifact.artifact_sha256)
                + ";"
            )
            retained_artifact = FpiArtifact(artifact.artifact_sha256, saved_artifact)
            validate_fpi_artifact(retained_artifact)
            assert retained_artifact == artifact
            assert base64.b64decode(json.loads(saved_artifact)["body_base64"]) == artifact_bytes
            for capture, parsed in inputs:
                writer.archive_fpi_capture(capture)
                result = FpiParseResult(
                    capture,
                    artifact.artifact_sha256,
                    "fpi-inr-observation-v1",
                    datetime.now(UTC),
                    tuple(
                        FpiParsedDay(
                            day.observation.document_json, day.source_evidence.evidence_sha256
                        )
                        for day in parsed
                    ),
                )
                source_documents = tuple(day.source_evidence.document_json for day in parsed)
                record = build_fpi_parse_record(result, source_evidence_documents=source_documents)
                first = writer.archive_fpi_parse_result(
                    result, source_evidence_documents=source_documents
                )
                assert first["inserted"] is True
                assert writer.archive_fpi_parse_result(
                    result, source_evidence_documents=source_documents
                ) == {
                    **first,
                    "inserted": False,
                }
                stored = json.loads(
                    _original_parse_sql(
                        "SET ROLE service_role; "
                        "SELECT json_build_array(p.record_sha256,p.document_json,"
                        "c.document_json) FROM fpi_parse_results p JOIN fpi_captures c "
                        "ON c.capture_sha256=p.capture_sha256 WHERE p.parse_id="
                        + _original_parse_literal(result.parse_id)
                        + ";"
                    )
                )
                readback = FpiParseRecord(result.parse_id, stored[0], stored[1])
                assert readback == record
                restored = restore_fpi_parse_record(
                    readback, FpiCapture(capture.capture_sha256, stored[2])
                )
                assert restored == result
                assert (
                    tuple(
                        day["source_evidence_document_json"]
                        for day in json.loads(stored[1])["days"]
                    )
                    == source_documents
                )
                assert _original_parse_sql(
                    "SET ROLE service_role; SELECT count(*) FROM fpi_parsed_memberships "
                    "WHERE parse_id="
                    + _original_parse_literal(result.parse_id)
                    + ";"
                ) == str(len(parsed))
        assert len(calls) == 8
        assert (
            _original_parse_sql(
                "SET ROLE service_role; SELECT count(*) FROM fpi_parsed_memberships;"
            )
            == "19"
        )
        print("FPI_ORIGINAL_PARSE_DATABASE_ROUNDTRIP_VERIFIED")
    finally:
        assert re.fullmatch(r"fxfpioriginal_[0-9a-f]{32}", DB)
        _original_parse_sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    verify_original_fpi_parse_bridge()
