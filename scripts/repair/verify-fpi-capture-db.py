"""Exercise the real FPI builder and central writer against isolated PostgreSQL.

Only authored synthetic bytes are used. The parent owns the socket-only PostgreSQL
runtime; this verifier creates and drops one uniquely named scratch database.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
DB = "fxfpi_" + uuid.uuid4().hex
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
LATEST = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"
MONTHLY = "https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx"
START = datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)
CHECKS: list[str] = []


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    """Run exact UTF-8 through binary pipes and enforce redacted failures."""
    result = subprocess.run(
        BASE + ["-d", database],
        input=statement.encode("utf-8"),
        capture_output=True,
        timeout=120,
    )
    stderr = result.stderr.decode("utf-8")
    if error is None:
        assert result.returncode == 0, stderr
    else:
        assert result.returncode != 0 and error in stderr, stderr
        assert "SENSITIVE_SENTINEL" not in stderr, stderr
        assert "U0VOU0lUSVZFX1NFTlRJTkVM" not in stderr, stderr
    return result.stdout.decode("utf-8").strip()


def text_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rpc_sql(document_json: str, digest: str | None = None) -> str:
    identity = digest or fingerprint(document_json)
    return (
        "SELECT public.append_fpi_capture("
        f"{text_literal(identity)},{text_literal(document_json)});"
    )


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build(
    body: bytes = b"synthetic FPI response\x00\xff",
    *,
    source_url: str = LATEST,
    minute: int = 0,
    status: int = 200,
):
    from src.research.fpi_capture import build_fpi_capture

    return build_fpi_capture(
        body=body,
        source_url=source_url,
        requested_at=START + timedelta(minutes=minute),
        retrieved_at=START + timedelta(minutes=minute, seconds=1),
        http_status=status,
    )


def archive_state() -> str:
    return sql(
        "SELECT json_build_array(count(*),encode(sha256(convert_to("
        "coalesce(string_agg(to_jsonb(row_value)::text,E'\\n' ORDER BY capture_sha256),''),"
        "'UTF8')),'hex')) FROM fpi_captures row_value;"
    )


def rejected(document: object, *, raw: str | None = None, digest: str | None = None) -> None:
    before = archive_state()
    encoded = canonical(document) if raw is None else raw
    sql(rpc_sql(encoded, digest), error="FPI capture rejected")
    assert archive_state() == before


def stored_document(identity: str) -> tuple[str, dict]:
    row = json.loads(
        sql(
            "SELECT json_build_array(document_json,document) FROM fpi_captures "
            f"WHERE capture_sha256={text_literal(identity)};"
        )
    )
    return row[0], row[1]


def verify_writer() -> tuple[object, dict, dict]:
    from src.db import writer

    capture = build()
    original = copy.deepcopy(capture)
    sent: list[tuple[str, dict]] = []

    def rpc(method: str, parameters: dict) -> MagicMock:
        assert method == "append_fpi_capture"
        assert set(parameters) == {"p_capture_sha256", "p_document_json"}
        sent.append((method, copy.deepcopy(parameters)))

        def execute() -> MagicMock:
            statement = (
                "SET TIME ZONE 'Asia/Kolkata'; SET DateStyle='SQL, DMY'; "
                "SET ROLE service_role; "
                + rpc_sql(parameters["p_document_json"], parameters["p_capture_sha256"])
            )
            return MagicMock(data=json.loads(sql(statement)))

        return MagicMock(execute=execute)

    client = MagicMock()
    client.rpc.side_effect = rpc
    with patch.object(writer, "_client", return_value=client):
        first = writer.archive_fpi_capture(capture)
        retry = writer.archive_fpi_capture(capture)

    assert capture == original
    assert first["capture_sha256"] == capture.capture_sha256
    assert first["inserted"] is True
    assert retry == {**first, "inserted": False}
    assert first["stored_at"].endswith(("+00:00", "Z"))
    assert len(sent) == 2 and client.table.call_count == 0
    exact_text, document = stored_document(capture.capture_sha256)
    assert exact_text == capture.document_json
    assert document == json.loads(capture.document_json)
    assert bytes.fromhex(
        sql(
            "SELECT encode(decode(document->>'body_base64','base64'),'hex') "
            f"FROM fpi_captures WHERE capture_sha256={text_literal(capture.capture_sha256)};"
        )
    ) == b"synthetic FPI response\x00\xff"
    assert sql(
        "SELECT stored_at::text FROM fpi_captures "
        f"WHERE capture_sha256={text_literal(capture.capture_sha256)};"
    ).startswith(first["stored_at"].replace("T", " ").removesuffix("+00:00"))
    CHECKS.append(
        "actual Python builder -> central writer -> service-role RPC preserves exact JSON and bytes; "
        "retry retains identity/stored_at and receipt stays UTC under non-UTC TimeZone and non-ISO DateStyle"
    )
    return capture, document, first


def verify_boundaries() -> None:
    empty = build(b"", source_url=MONTHLY, minute=2, status=503)
    maximum = build(b"z" * 5_000_000, source_url=MONTHLY, minute=3, status=599)
    for capture in (empty, maximum):
        result = json.loads(sql("SET ROLE service_role; " + rpc_sql(capture.document_json)))
        assert result["inserted"] is True
        stored_text, stored = stored_document(capture.capture_sha256)
        assert stored_text == capture.document_json
        assert stored["body_size"] in {0, 5_000_000}
        assert base64.b64decode(stored["body_base64"], validate=True) in {b"", b"z" * 5_000_000}

    too_large = {
        **json.loads(maximum.document_json),
        "body_base64": base64.b64encode(b"z" * 5_000_001).decode("ascii"),
        "body_size": 5_000_001,
        "raw_sha256": hashlib.sha256(b"z" * 5_000_001).hexdigest(),
    }
    rejected(too_large)
    rejected({}, raw=" " * 7_000_001)
    CHECKS.append(
        "empty error evidence and the exact 5,000,000-byte boundary round-trip; oversized body and document reject"
    )


def replace_number_lexeme(text: str, field: str, replacement: str) -> str:
    original = json.loads(text)[field]
    needle = f'"{field}":{original}'
    assert needle in text
    return text.replace(needle, f'"{field}":{replacement}', 1)


def verify_malformed(good: object, document: dict) -> None:
    rejected(document, digest="0" * 64)
    for invalid in [None, [], "SENSITIVE_SENTINEL", 123, True]:
        rejected(invalid)
    rejected({**document, "extra": "SENSITIVE_SENTINEL"})
    missing = {**document}
    del missing["version"]
    rejected(missing)
    rejected(document, raw=good.document_json[:-1] + ',"version":"SENSITIVE_SENTINEL"}')
    rejected(document, raw='{"body_base64":"U0VOU0lUSVZFX1NFTlRJTkVM","broken":')
    rejected(document, raw=good.document_json[:-1] + ',"extra":"\\u0000"}')

    for key, values in {
        "version": [None, True, "v2"],
        "source_url": [None, MONTHLY + "?x=1", "http://www.fpi.nsdl.co.in/web/Reports/Latest.aspx", "https://pilot.fpi.nsdl.co.in/Reports/Latest.aspx"],
        "http_status": [True, "200", 99, 600, -1],
        "body_size": [True, "26", -1, 5_000_001],
        "requested_at": [None, True, "2026-01-02T03:04:05Z", "2026-01-02T03:04:05+05:30", "2026-02-30T03:04:05+00:00", "0000-01-01T00:00:00+00:00"],
        "retrieved_at": [None, "2026-01-02T03:04:05.1234567+00:00", "2099-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"],
        "raw_sha256": [None, "A" * 64, "0" * 64, "bad"],
        "body_base64": [None, True, "A", "AA", "AA=", "AA===", "AB==", "YW Jj", "SENSITIVE_SENTINEL"],
    }.items():
        for value in values:
            rejected({**document, key: value})

    for field, lexemes in {"http_status": ["2e2", "200.0"], "body_size": ["2.6e1", "26.0"]}.items():
        for lexeme in lexemes:
            raw = replace_number_lexeme(good.document_json, field, lexeme)
            rejected(document, raw=raw)

    wrong_order = {**document, "requested_at": "2026-01-03T00:00:00+00:00"}
    rejected(wrong_order)
    rejected({**document, "body_size": document["body_size"] + 1})
    CHECKS.append(
        "direct SQL rejects malformed/duplicate JSON, extra or missing fields, primitive-type errors, URL variants, "
        "invalid/future/reversed times, exponent/decimal integer lexemes, noncanonical Base64 including nonzero padding bits, "
        "size/raw/document hash mismatches; errors disclose no sentinel payload"
    )


def verify_retained_text_conflict() -> None:
    capture = build(b"retained conflict synthetic bytes", minute=12)
    document = json.loads(capture.document_json)
    sql(
        "INSERT INTO fpi_captures(capture_sha256,document_json,document,source_url,requested_at,"
        "retrieved_at,raw_sha256,body_size,http_status) VALUES("
        f"{text_literal(capture.capture_sha256)},'{{\"retained\":\"conflict\"}}','{{}}',"
        f"{text_literal(document['source_url'])},{text_literal(document['requested_at'])},"
        f"{text_literal(document['retrieved_at'])},{text_literal(document['raw_sha256'])},"
        f"{document['body_size']},{document['http_status']});"
    )
    rejected(document)
    CHECKS.append(
        "an injected retained-text mismatch at a requested identity rejects without replacing the retained row"
    )


def verify_concurrency() -> None:
    capture = build(b"concurrent synthetic bytes", minute=10)
    barrier = threading.Barrier(2)

    def worker(_: int) -> dict:
        barrier.wait(timeout=10)
        result = sql(
            "BEGIN; SET LOCAL TIME ZONE 'Pacific/Honolulu'; SET LOCAL ROLE service_role; "
            + rpc_sql(capture.document_json)
            + " SELECT pg_sleep(0.2); COMMIT;"
        )
        return json.loads(result.splitlines()[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert sorted(item["inserted"] for item in results) == [False, True]
    assert results[0]["capture_sha256"] == results[1]["capture_sha256"]
    assert results[0]["stored_at"] == results[1]["stored_at"]
    assert all(item["stored_at"].endswith("+00:00") for item in results)

    retry = build(b"concurrent synthetic bytes", minute=11)
    assert retry.capture_sha256 != capture.capture_sha256
    assert json.loads(sql("SET ROLE service_role; " + rpc_sql(retry.document_json)))["inserted"] is True
    assert sql(
        "SELECT count(*) FROM fpi_captures WHERE raw_sha256="
        f"{text_literal(json.loads(capture.document_json)['raw_sha256'])};"
    ) == "2"
    CHECKS.append(
        "simultaneous exact retries produce one insert and one stable UTC receipt; same bytes at a later retrieval append a distinct capture"
    )


def verify_permissions() -> None:
    assert sql("SELECT relrowsecurity FROM pg_class WHERE oid='public.fpi_captures'::regclass;") == "t"
    assert sql(
        "SELECT string_agg(column_name||':'||data_type,',' ORDER BY ordinal_position) "
        "FROM information_schema.columns WHERE table_schema='public' AND table_name='fpi_captures';"
    ) == (
        "capture_sha256:text,document_json:text,document:jsonb,source_url:text,"
        "requested_at:timestamp with time zone,retrieved_at:timestamp with time zone,"
        "raw_sha256:text,body_size:integer,http_status:integer,stored_at:timestamp with time zone"
    )
    assert sql(
        "SELECT string_agg(indexname,',' ORDER BY indexname) FROM pg_indexes "
        "WHERE schemaname='public' AND tablename='fpi_captures';"
    ) == "fpi_captures_pkey,fpi_captures_raw_sha256,fpi_captures_source_retrieved"
    assert sql(
        "SELECT count(*) FROM pg_trigger WHERE tgrelid='public.fpi_captures'::regclass "
        "AND NOT tgisinternal AND tgenabled='O';"
    ) == "2"
    owner_count = sql("SELECT count(*) FROM fpi_captures;")
    assert sql("SET ROLE service_role; SELECT count(*) FROM fpi_captures;") == owner_count
    for role in ["anon", "authenticated"]:
        sql(f"SET ROLE {role}; SELECT * FROM fpi_captures;", error="permission denied")
        sql(f"SET ROLE {role}; " + rpc_sql("{}"), error="permission denied")
    for role in ["anon", "authenticated", "service_role"]:
        sql(f"SET ROLE {role}; INSERT INTO fpi_captures DEFAULT VALUES;", error="permission denied")
        sql(f"SET ROLE {role}; UPDATE fpi_captures SET body_size=body_size;", error="permission denied")
        sql(f"SET ROLE {role}; DELETE FROM fpi_captures;", error="permission denied")
        sql(f"SET ROLE {role}; TRUNCATE fpi_captures;", error="permission denied")
    for operation in [
        "UPDATE fpi_captures SET body_size=body_size",
        "DELETE FROM fpi_captures",
        "TRUNCATE fpi_captures",
    ]:
        sql(operation + ";", error="immutable")

    sql("GRANT SELECT ON fpi_captures TO anon,authenticated;")
    for role in ["anon", "authenticated"]:
        assert sql(f"SET ROLE {role}; SELECT count(*) FROM fpi_captures;") == "0"
    sql("REVOKE SELECT ON fpi_captures FROM anon,authenticated;")

    helpers = [
        "reject_fpi_capture_mutation()",
        "fpi_capture_unique_json('{}')",
        "fpi_capture_keys('{}',ARRAY[]::text[])",
        "fpi_capture_time('null')",
    ]
    for role in ["anon", "authenticated", "service_role"]:
        for helper in helpers:
            sql(f"SET ROLE {role}; SELECT public.{helper};", error="permission denied")
    assert sql(
        "SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace "
        "AND (proname LIKE 'fpi_capture_%' OR proname IN ('append_fpi_capture','reject_fpi_capture_mutation')) "
        "AND 'search_path=pg_catalog, public'=ANY(proconfig);"
    ) == "5"
    assert sql(
        "SELECT prosecdef FROM pg_proc WHERE pronamespace='public'::regnamespace "
        "AND proname='append_fpi_capture';"
    ) == "t"
    CHECKS.append(
        "RLS and explicit revocations withstand broad default grants; service role has SELECT/exact RPC only; "
        "anonymous/authenticated remain blind after accidental SELECT; helpers are private, search paths fixed, and owner mutations fail"
    )


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql(
            "CREATE TABLE historical_prices(pair text,date date,close numeric);"
            "INSERT INTO historical_prices VALUES('USDINR','2026-01-02',85.1);"
            "CREATE TABLE validation_log(id integer PRIMARY KEY,note text);"
            "INSERT INTO validation_log VALUES(1,'validation sentinel');"
            "CREATE TABLE validation_evaluations(id integer PRIMARY KEY,note text);"
            "INSERT INTO validation_evaluations VALUES(1,'evaluation sentinel');"
        )
        preserved_tables = [
            "historical_prices",
            "regime_calls",
            "signals",
            "call_rationale",
            "validation_log",
            "validation_evaluations",
        ]
        preserved = {
            table: sql(f"SELECT jsonb_agg(to_jsonb(row_value) ORDER BY to_jsonb(row_value)::text) FROM {table} row_value;")
            for table in preserved_tables
        }
        permission_probe = (
            "SELECT jsonb_agg(jsonb_build_array(role_name,table_name,privilege_name,"
            "has_table_privilege(role_name,table_name,privilege_name)) "
            "ORDER BY role_name,table_name,privilege_name) FROM "
            "(VALUES ('anon','regime_calls','SELECT'),('authenticated','signals','UPDATE'),"
            "('service_role','call_rationale','INSERT')) probe(role_name,table_name,privilege_name);"
        )
        preserved_permissions = sql(permission_probe)
        sql(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role;"
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;"
        )
        migration = (
            ROOT / "supabase/migrations/20260927000010_fpi_capture_storage.sql"
        ).read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        print("RUN: Python writer bridge", flush=True)
        good, document, _ = verify_writer()
        print("RUN: byte and size boundaries", flush=True)
        verify_boundaries()
        print("RUN: malformed direct SQL", flush=True)
        verify_malformed(good, document)
        print("RUN: concurrency and retry identity", flush=True)
        verify_concurrency()
        print("RUN: retained-text conflict", flush=True)
        verify_retained_text_conflict()
        print("RUN: permissions and populated reapplication", flush=True)
        verify_permissions()
        before = archive_state()
        sql(migration)
        assert archive_state() == before
        for table, original in preserved.items():
            assert sql(
                f"SELECT jsonb_agg(to_jsonb(row_value) ORDER BY to_jsonb(row_value)::text) FROM {table} row_value;"
            ) == original
        assert sql(permission_probe) == preserved_permissions
        CHECKS.append(
            "fresh/empty/populated migration application preserves every capture, unrelated table/role privileges, "
            "and the price/call/signal/rationale/validation/evaluation sentinels"
        )
        for check in CHECKS:
            print("PASS:", check)
        print("REPAIR_FPI_CAPTURE_DB_VERIFIED")
    finally:
        assert DB.startswith("fxfpi_") and len(DB) == 38
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
