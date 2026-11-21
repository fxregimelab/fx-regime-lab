"""Exercise quote capture -> constructor -> central writer -> isolated PostgreSQL.

Synthetic responses only. The parent owns the existing socket runtime lifecycle.
No .env loading, network/provider requests, production connections or service startup.
"""
from __future__ import annotations

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
DB = "fxquote_" + uuid.uuid4().hex
BASE = ["wsl", "-d", "Ubuntu-24.04", "--", "/usr/lib/postgresql/17/bin/psql",
        "-h", "/home/shreyash/.local/state/fxregime-repair/socket", "-p", "55437",
        "-X", "-qAt", "-v", "ON_ERROR_STOP=1"]
CHECKS: list[str] = []
DAY_NS = 86_400_000_000_000
START = 1777593600000000000
AS_OF = datetime(2026, 5, 3, tzinfo=UTC)
IMPLEMENTATION = hashlib.sha256(b"explicit synthetic implementation label").hexdigest()


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    # Binary pipes avoid Windows newline translation changing authoritative text.
    result = subprocess.run(BASE + ["-d", database], input=statement.encode("utf-8"),
                            capture_output=True, timeout=90)
    stderr = result.stderr.decode("utf-8")
    if error is not None:
        assert result.returncode != 0 and error in stderr, stderr
        assert "SENSITIVE_SENTINEL" not in stderr, stderr
    else:
        assert result.returncode == 0, stderr
    return result.stdout.decode("utf-8").strip()


def text_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rpc_sql(kind: str, unsigned: str, digest: str | None = None) -> str:
    assert kind in {"capture", "snapshot"}
    return (f"SELECT public.append_quote_{kind}("
            f"{text_literal(digest or fingerprint(unsigned))},{text_literal(unsigned)});")


def canonical(value: object) -> str:
    from src.research.quote_capture import canonical_json
    return canonical_json(value)


def capture(*, pair: str = "EURUSD", body: bytes | None = None, index: int = 0,
            cursor: str | None = None, minute: int = 0) -> dict:
    from src.research.quote_capture import capture_quote_page
    instrument = {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}[pair]
    params = {"timestamp.gte": str(START), "timestamp.lt": str(START+DAY_NS),
              "sort": "timestamp", "order": "asc", "limit": "50000"}
    if cursor is not None:
        params["cursor"] = cursor
    if body is None:
        body = (b'{"status":"OK","results":[{"participant_timestamp":1777593600000000001,'
                b'"bid_price":1.10000000000000000001,"ask_price":1.10000000000000000003}]}')
    return capture_quote_page(
        pair=pair, instrument=instrument, window_start_ns=START, window_end_ns=START+DAY_NS,
        page_index=index, requested_at=AS_OF-timedelta(hours=2)+timedelta(minutes=minute),
        received_at=AS_OF-timedelta(hours=2)+timedelta(minutes=minute, seconds=1),
        status_code=200, body=body, request_params=params,
        response_headers={"content-type": "application/json", "x-request-id": f"synthetic-{minute}"})


def unsigned_capture(page: dict) -> dict:
    return {key: value for key, value in page.items() if key != "capture_sha256"}


def envelope(pages: list[dict], **changes: object) -> dict:
    from src.research.quote_reference import build_quote_reference
    return {"version": "quote-snapshot-v1", "implementation_sha256": IMPLEMENTATION,
            "client_version": "synthetic-db-verifier-v1",
            "reference": build_quote_reference(pages, as_of=AS_OF), **changes}


def archive_state() -> str:
    return sql("SELECT json_build_array("
               "(SELECT coalesce(jsonb_agg(to_jsonb(c) ORDER BY capture_sha256),'[]') FROM quote_captures c),"
               "(SELECT coalesce(jsonb_agg(to_jsonb(s) ORDER BY snapshot_sha256),'[]') FROM quote_snapshots s),"
               "(SELECT coalesce(jsonb_agg(to_jsonb(p) ORDER BY snapshot_sha256,ordinal),'[]') FROM quote_snapshot_pages p));")


def rejected(kind: str, value: object, *, raw: str | None = None, digest: str | None = None) -> None:
    before = archive_state()
    sql(rpc_sql(kind, canonical(value) if raw is None else raw, digest), error=f"Quote {kind} rejected")
    assert archive_state() == before


def verify_writer() -> tuple[list[dict], dict]:
    from src.db import writer
    from src.research.quote_reference import build_quote_reference

    first_body = (b'{"status":"OK","results":[{"participant_timestamp":1777593600000000001,'
                  b'"bid_price":1.10000000000000000001,"ask_price":1.10000000000000000003}],'
                  b'"next_url":"https://api.massive.com/v3/quotes/C:EUR-USD?cursor=opaque-private-cursor"}')
    pages = [capture(body=first_body, minute=10), capture(index=1, cursor="opaque-private-cursor", minute=11)]
    original = copy.deepcopy(pages)
    sent: list[tuple[str, dict]] = []

    def rpc(method: str, parameters: dict) -> MagicMock:
        kind = method.removeprefix("append_quote_")
        assert method == "append_quote_" + kind and kind in {"capture", "snapshot"}
        assert set(parameters) == {f"p_{kind}_sha256", "p_unsigned_json"}
        sent.append((method, copy.deepcopy(parameters)))

        def execute() -> MagicMock:
            return MagicMock(data=json.loads(sql("SET ROLE service_role; " + rpc_sql(
                kind, parameters["p_unsigned_json"], parameters[f"p_{kind}_sha256"]))))
        return MagicMock(execute=execute)

    client = MagicMock()
    client.rpc.side_effect = rpc
    with patch.object(writer, "_client", return_value=client):
        for page in pages:
            first = writer.archive_quote_capture(page)
            assert first == {"capture_sha256": page["capture_sha256"], "inserted": True}
            assert writer.archive_quote_capture(page) == {**first, "inserted": False}
            stored = json.loads(sql("SELECT document FROM quote_captures WHERE capture_sha256=" + text_literal(page["capture_sha256"]) + ";"))
            assert stored == unsigned_capture(page)
            stored_text = json.loads(sql("SELECT to_json(unsigned_json) FROM quote_captures WHERE capture_sha256=" + text_literal(page["capture_sha256"]) + ";"))
            assert stored_text == canonical(unsigned_capture(page))
        result = writer.archive_quote_snapshot(pages, as_of=AS_OF, implementation_sha256=IMPLEMENTATION,
                                               client_version="synthetic-db-verifier-v1")
        assert result["inserted"] is True and result["capture_count"] == 2
        retry = writer.archive_quote_snapshot(pages, as_of=AS_OF, implementation_sha256=IMPLEMENTATION,
                                              client_version="synthetic-db-verifier-v1")
        assert retry == {**result, "inserted": False}
    assert pages == original and client.table.call_count == 0
    expected = envelope(pages)
    assert json.loads(sql("SELECT document FROM quote_snapshots WHERE snapshot_sha256=" + text_literal(result["snapshot_sha256"]) + ";")) == expected
    assert json.loads(sql("SELECT to_json(unsigned_json) FROM quote_snapshots WHERE snapshot_sha256=" + text_literal(result["snapshot_sha256"]) + ";")) == canonical(expected)
    assert expected["reference"] == build_quote_reference(pages, as_of=AS_OF)
    assert expected["reference"]["open"] == "1.10000000000000000002"
    assert expected["reference"]["source_occurrence_count"] == 2
    assert expected["reference"]["duplicate_count"] == 1
    assert expected["reference"]["validation_eligible"] is False
    lineage = json.loads(sql("SELECT json_agg(capture_sha256 ORDER BY ordinal) FROM quote_snapshot_pages WHERE snapshot_sha256=" + text_literal(result["snapshot_sha256"]) + ";"))
    assert lineage == [page["capture_sha256"] for page in pages]
    for _, parameters in sent:
        assert "opaque-private-cursor" not in parameters["p_unsigned_json"]
    CHECKS.append("actual Python capture and exact Decimal constructor -> central writer -> service-role SQL -> unchanged text, output and ordered lineage; exact retries")
    return pages, expected


def verify_malformed(page: dict, snap: dict) -> None:
    unsigned = unsigned_capture(page)
    for kind, value in [("capture", unsigned), ("snapshot", snap)]:
        rejected(kind, value, digest="0"*64)
        for invalid in [None, [], "SENSITIVE_SENTINEL", 123, True]:
            rejected(kind, invalid)
        rejected(kind, {**value, "extra": "SENSITIVE_SENTINEL"})
        missing = copy.deepcopy(value)
        del missing["version"]
        rejected(kind, missing)
        rejected(kind, value, raw=canonical(value)[:-1]+',"version":"duplicate"}')
        rejected(kind, value, raw='{"SENSITIVE_SENTINEL":')
    for key, values in {
        "version": [None, True, "v2"], "provider": [None, "unknown"],
        "pair": [None, "GBPUSD"], "instrument": [None, "C:USD-JPY"],
        "window_start_ns": [True, START, "01", str(START+1)],
        "window_end_ns": [None, str(START+1)],
        "page_index": [True, -1, 0.5, "0"], "http_status": [True, 99, 600, "200"],
        "raw_size_bytes": [True, -1, 16777217, "1"],
        "requested_at": [1, None, "2026-05-03T00:00:00", "2026-05-03T00:00:00Z", "2026-02-30T00:00:00+00:00"],
        "received_at": [True, "2099-01-01T00:00:00+00:00", "2026-05-01T00:00:00+00:00"],
        "raw_body_sha256": [None, "A"*64, "bad"], "body_sha256": [None, "0"*64],
        "request_cursor_sha256": [False, "0"*64], "next_cursor_sha256": [False, "bad"],
        "body_text": [True, None, "SENSITIVE_SENTINEL"],
        "issues": [None, {}, ["unknown"], ["invalid_json", "invalid_json"], ["invalid_json", "invalid_utf8"]],
        "response_headers": [None, {"authorization": "SENSITIVE_SENTINEL"}, {"content-type": 1}],
        "request_parameters": [None, {}, {**unsigned["request_parameters"], "token": "SENSITIVE_SENTINEL"},
                               {**unsigned["request_parameters"], "limit": "050"},
                               {**unsigned["request_parameters"], "limit": "50001"},
                               {**unsigned["request_parameters"], "order": "desc"}],
    }.items():
        for value in values:
            rejected("capture", {**unsigned, key: value})
    for body, issues, next_hash in [
        ('{"broken":"SENSITIVE_SENTINEL"', [], None),
        ('{"broken":"SENSITIVE_SENTINEL"', ["invalid_json", "invalid_cursor"], None),
        ('{"broken":"SENSITIVE_SENTINEL"', ["invalid_json"], "0"*64),
        ('{"next_url":"https://other.example/SENSITIVE_SENTINEL"}', [], "0"*64),
        ('{"next_url":"[INVALID_CURSOR]"}', [], None),
        ('{}', ["invalid_cursor"], None), ('{}', [], "0"*64),
        ('{"x":1,"x":2}', [], None),
    ]:
        rejected("capture", {**unsigned, "body_text": body, "body_sha256": fingerprint(body),
                              "issues": issues, "next_cursor_sha256": next_hash})
    for key, values in {"implementation_sha256": [None, True, "X"*64],
                        "client_version": [None, True, "", "x"*129, "invalid space", "é"]}.items():
        for value in values:
            rejected("snapshot", {**snap, key: value})
    for key, values in {
        "series_id": ["other", None], "algorithm_version": ["other", None],
        "pair": ["GBPUSD", "USDJPY"], "instrument": ["C:USD-JPY"],
        "validation_eligible": [True, "false", None], "project_maturity": ["accepted"],
        "provider_finality": ["final"], "as_of": [True, "2099-01-01T00:00:00+00:00"],
        "acquisition_complete": [None, "true"], "ambiguous_open": [1],
        "source_occurrence_count": [True, -1, 0.5], "open": [1.1, True, "NaN"],
        "first_timestamp_ns": [1, True, "1.1"],
        "exclusion_reasons": [None, [], [True, "coverage_policy_unverified"]],
        "input_sha256": [None, "0"*64], "capture_sha256": [[], [None], ["0"*64]],
    }.items():
        for value in values:
            rejected("snapshot", {**snap, "reference": {**snap["reference"], key: value}})
    rejected("snapshot", {**snap, "reference": {**snap["reference"], "unexpected": True}})
    rejected("snapshot", {**snap, "reference": {**snap["reference"], "acquisition_complete": False}})
    rejected("snapshot", {**snap, "reference": {**snap["reference"], "capture_sha256": [page["capture_sha256"]]*10001}})
    # Exact UTF-8 limits are checked before JSON interpretation.
    rejected("snapshot", snap, raw=" "*1048577)
    rejected("capture", unsigned, raw=" "*33554433)
    CHECKS.append("strict direct-RPC shape/type/identity/timestamp/hash/metadata/cursor/issue/lineage checks and UTF-8 byte limits reject atomically without source disclosure")


def verify_diagnostics() -> None:
    from src.db import writer
    bodies = [b'{"status":"OK","results":[]}', b"invalid-json \xff synthetic",
              b"failure\x00text", b'{"status":"OK","results":[],"note":"\\u0000\\ud800"}',
              b'{"status":"OK","results":[],"\\u0000":1}',
              b'{"status":"OK","results":[],"\\ud800":1}',
              b'{"status":"OK","results":[{"participant_timestamp":1777593600000000001,"bid_price":1e1000000,"ask_price":1e1000000}]}',
              b'{"status":"OK","results":[{"participant_timestamp":1777593600000000001,"bid_price":1.2,"ask_price":1.1}]}']
    for index, body in enumerate(bodies):
        page = capture(body=body, minute=20+index)
        doc = unsigned_capture(page)
        assert json.loads(sql(rpc_sql("capture", canonical(doc))))["inserted"] is True
        snap = envelope([page])
        assert json.loads(sql(rpc_sql("snapshot", canonical(snap))))["inserted"] is True
        assert json.loads(sql("SELECT document FROM quote_captures WHERE capture_sha256=" + text_literal(page["capture_sha256"]) + ";")) == doc
        assert snap["reference"]["validation_eligible"] is False
        assert doc["raw_body_sha256"] == hashlib.sha256(body).hexdigest()
        assert doc["raw_size_bytes"] == len(body)
        if b"\x00" in body:
            assert "\x00" not in doc["body_text"] and "\\u0000" in doc["body_text"]
        if b"\x00" in body or b"\\u0000" in body or b"\\ud800" in body:
            assert "text_storage_escaped" in doc["issues"]
            assert snap["reference"]["acquisition_complete"] is False
    for pair in ["USDJPY", "USDINR"]:
        page = capture(pair=pair, minute=30)
        sql(rpc_sql("capture", canonical(unsigned_capture(page))))
        sql(rpc_sql("snapshot", canonical(envelope([page]))))
    repeated = capture(minute=35)
    sql(rpc_sql("capture", canonical(unsigned_capture(repeated))))
    diagnostic = envelope([repeated, repeated])
    saved = json.loads(sql(rpc_sql("snapshot", canonical(diagnostic))))
    assert saved["capture_count"] == 2
    assert diagnostic["reference"]["acquisition_complete"] is False
    assert sql("SELECT count(*) FROM quote_snapshot_pages WHERE snapshot_sha256=" + text_literal(saved["snapshot_sha256"]) + ";") == "2"
    maximum = envelope([repeated] * 10000)
    maximum_result = json.loads(sql(rpc_sql("snapshot", canonical(maximum))))
    assert maximum_result["capture_count"] == 10000
    assert sql("SELECT count(*) FROM quote_snapshot_pages WHERE snapshot_sha256=" + text_literal(maximum_result["snapshot_sha256"]) + ";") == "10000"
    assert json.loads(sql(rpc_sql("snapshot", canonical(maximum))))["inserted"] is False
    # SQL hashes exact UTF-8 text, without asserting Python canonical formatting.
    utf8_doc = unsigned_capture(capture(minute=38))
    utf8_doc["response_headers"]["x-request-id"] = "synthetic-é-λ"
    utf8_text = json.dumps(utf8_doc, ensure_ascii=False, indent=1)
    utf8_result = json.loads(sql(rpc_sql("capture", utf8_text)))
    assert utf8_result["capture_sha256"] == fingerprint(utf8_text)
    assert json.loads(sql("SELECT to_json(unsigned_json) FROM quote_captures WHERE capture_sha256=" + text_literal(utf8_result["capture_sha256"]) + ";")) == utf8_text
    # Intraday evidence stays archivable and explicitly incomplete.
    page = capture(minute=36)
    page["requested_at"] = "2026-05-01T01:00:00+00:00"
    page["received_at"] = "2026-05-01T01:00:01+00:00"
    page["capture_sha256"] = fingerprint(canonical(unsigned_capture(page)))
    sql(rpc_sql("capture", canonical(unsigned_capture(page))))
    snap = envelope([page])
    assert snap["reference"]["acquisition_complete"] is False
    sql(rpc_sql("snapshot", canonical(snap)))
    # Service callers need existing captures; writer never silently uploads one.
    missing = capture(minute=37)
    rejected("snapshot", envelope([missing]))
    with patch.object(writer, "_client") as factory:
        try:
            writer.archive_quote_snapshot([repeated, capture(pair="USDJPY")], as_of=AS_OF,
                                          implementation_sha256=IMPLEMENTATION, client_version="test")
        except ValueError:
            pass
        else:
            raise AssertionError("mixed identity reached SQL")
        factory.assert_not_called()
    CHECKS.append("all three locked pairs, invalid UTF-8/JSON, NUL/surrogate escapes, huge source exponents, crossed quotes, empty/intraday/incomplete/repeated-page evidence and 10000-page boundary persist without qualification; raw fingerprints/sizes and exact UTF-8 retained; missing captures and mixed identity reject")


def verify_concurrency_and_atomicity(pages: list[dict], snap: dict) -> None:
    # Parent insert occurs before membership rows; force failure on the second row.
    candidate = {**snap, "client_version": "rollback-synthetic"}
    before = archive_state()
    sql("""CREATE FUNCTION fail_quote_membership() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.ordinal=1 THEN RAISE EXCEPTION 'injected membership failure'; END IF;
        RETURN NEW; END $$;
        CREATE TRIGGER fail_membership BEFORE INSERT ON quote_snapshot_pages
        FOR EACH ROW EXECUTE FUNCTION fail_quote_membership();""")
    sql(rpc_sql("snapshot", canonical(candidate)), error="Quote snapshot rejected")
    assert archive_state() == before
    sql("DROP TRIGGER fail_membership ON quote_snapshot_pages; DROP FUNCTION fail_quote_membership();")
    for kind, doc in [("capture", unsigned_capture(capture(minute=45))),
                      ("snapshot", {**snap, "client_version": "concurrent-synthetic"})]:
        barrier = threading.Barrier(2)

        def worker(_: int) -> dict:
            barrier.wait(timeout=10)
            output = sql("BEGIN; SET LOCAL ROLE service_role; " + rpc_sql(kind, canonical(doc)) + " SELECT pg_sleep(0.2); COMMIT;")
            return json.loads(output.splitlines()[0])

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        assert results[0][f"{kind}_sha256"] == results[1][f"{kind}_sha256"]
        assert sorted(result["inserted"] for result in results) == [False, True]
    # An independent source correction leaves the original exact text intact.
    original_hash = pages[0]["capture_sha256"]
    original_text = sql("SELECT unsigned_json FROM quote_captures WHERE capture_sha256=" + text_literal(original_hash) + ";")
    corrected = capture(body=b'{"status":"OK","results":[]}', minute=46)
    sql(rpc_sql("capture", canonical(unsigned_capture(corrected))))
    assert corrected["capture_sha256"] != original_hash
    assert sql("SELECT unsigned_json FROM quote_captures WHERE capture_sha256=" + text_literal(original_hash) + ";") == original_text
    CHECKS.append("concurrent exact capture/snapshot retries have one insert and one stable retry; injected second-membership failure rolls back snapshot and all membership rows; corrections append")


def verify_permissions() -> None:
    tables = ["quote_captures", "quote_snapshots", "quote_snapshot_pages"]
    for table in tables:
        assert sql(f"SELECT relrowsecurity FROM pg_class WHERE oid='public.{table}'::regclass;") == "t"
        assert sql(f"SET ROLE service_role; SELECT count(*) FROM {table};") == sql(f"SELECT count(*) FROM {table};")
        for role in ["anon", "authenticated"]:
            sql(f"SET ROLE {role}; SELECT * FROM {table};", error="permission denied")
        for role in ["anon", "authenticated", "service_role"]:
            for mutation in [f"INSERT INTO {table} DEFAULT VALUES", f"UPDATE {table} SET capture_sha256=capture_sha256" if table != "quote_snapshots" else f"UPDATE {table} SET snapshot_sha256=snapshot_sha256", f"DELETE FROM {table}", f"TRUNCATE {table} CASCADE"]:
                sql(f"SET ROLE {role}; {mutation};", error="permission denied")
            sql(f"SET ROLE {role}; COPY {table} FROM STDIN;\n\\.\n", error="permission denied")
        for mutation in [f"UPDATE {table} SET capture_sha256=capture_sha256" if table != "quote_snapshots" else f"UPDATE {table} SET snapshot_sha256=snapshot_sha256", f"DELETE FROM {table}", f"TRUNCATE {table} CASCADE"]:
            sql(mutation+";", error="immutable")
        sql(f"GRANT SELECT ON {table} TO anon,authenticated;")
        for role in ["anon", "authenticated"]:
            assert sql(f"SET ROLE {role}; SELECT count(*) FROM {table};") == "0"
        sql(f"REVOKE SELECT ON {table} FROM anon,authenticated;")
    for role in ["anon", "authenticated"]:
        for kind in ["capture", "snapshot"]:
            sql(f"SET ROLE {role}; " + rpc_sql(kind, "{}"), error="permission denied")
    for role in ["anon", "authenticated", "service_role"]:
        for helper in ["reject_quote_storage_mutation()", "quote_storage_unique_json('{}')",
                       "quote_storage_keys('{}',ARRAY[]::text[])", "quote_storage_time('null')",
                       "quote_storage_identity('{}')"]:
            sql(f"SET ROLE {role}; SELECT public.{helper};", error="permission denied")
    assert sql("SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace AND "
               "(proname LIKE 'quote_storage_%' OR proname LIKE 'append_quote_%' OR proname='reject_quote_storage_mutation') "
               "AND 'search_path=pg_catalog, public'=ANY(proconfig);") == "7"
    assert sql("SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname LIKE 'append_quote_%' AND prosecdef;") == "2"
    CHECKS.append("all three tables private under RLS; exact service-role read/RPC grants only; direct writes and owner UPDATE/DELETE/TRUNCATE refused; helpers private and search paths fixed")


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE historical_prices(pair text, date date, close numeric); "
            "INSERT INTO historical_prices VALUES ('EURUSD','2026-05-01',1.11); "
            "CREATE TABLE validation_log(id integer PRIMARY KEY, note text); "
            "INSERT INTO validation_log VALUES (1,'immutable validation sentinel'); "
            "CREATE TABLE validation_evaluations(id integer PRIMARY KEY, note text); "
            "INSERT INTO validation_evaluations VALUES (1,'accepted evaluation sentinel');")
        preserved_tables = ["historical_prices", "regime_calls", "signals", "call_rationale", "validation_log", "validation_evaluations"]
        preserved = {table: sql(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM {table} t;") for table in preserved_tables}
        sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;")
        migration = (ROOT / "supabase/migrations/20260927000008_quote_capture_storage.sql").read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        print("RUN: Python writer bridge", flush=True)
        pages, snap = verify_writer()
        print("RUN: malformed direct SQL calls", flush=True)
        verify_malformed(pages[0], snap)
        print("RUN: source diagnostics and boundary cases", flush=True)
        verify_diagnostics()
        print("RUN: concurrency and rollback", flush=True)
        verify_concurrency_and_atomicity(pages, snap)
        print("RUN: permissions and populated reapplication", flush=True)
        verify_permissions()
        before = archive_state()
        sql(migration)
        assert archive_state() == before
        for table, original in preserved.items():
            assert sql(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM {table} t;") == original
        CHECKS.append("fresh isolated migration and populated reapplication preserve every quote row and original call/signal/rationale/price/validation/evaluation sentinel")
        for check in CHECKS:
            print("PASS:", check)
        print("REPAIR_QUOTE_STORAGE_DB_VERIFIED")
    finally:
        assert DB.startswith("fxquote_") and len(DB) == 40
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
