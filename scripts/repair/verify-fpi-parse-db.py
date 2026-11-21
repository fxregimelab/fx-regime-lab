"""Verify private parse storage using the real codec/writer and local PostgreSQL.

The parent starts and checks the socket-only runtime. This program creates only
its own random scratch database and drops it in finally, including on failure.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import queue
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
DB = "fxfpiparse_" + uuid.uuid4().hex
BASE = ["wsl", "-d", "Ubuntu-24.04", "--", "/usr/lib/postgresql/17/bin/psql",
        "-h", "/home/shreyash/.local/state/fxregime-repair/socket", "-p", "55437",
        "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=terse"]
TABLES = ("fpi_implementation_artifacts", "fpi_parse_results", "fpi_parsed_memberships")
START = datetime(2026, 1, 3, 12, tzinfo=UTC)
CHECKS: list[str] = []


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = subprocess.run(BASE + ["-d", database], input=statement.encode("utf-8"),
                            capture_output=True, timeout=120)
    stderr = result.stderr.decode("utf-8")
    if error is None:
        assert result.returncode == 0, stderr[:1000]
    else:
        assert result.returncode != 0 and error in stderr, stderr[:1000]
        assert "SENSITIVE_SENTINEL" not in stderr and "U0VOU0lUSVZF" not in stderr
    return result.stdout.decode("utf-8").strip()


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def rpc_statement(method: str, parameters: dict) -> str:
    names = {
        "append_fpi_capture": ("p_capture_sha256", "p_document_json"),
        "append_fpi_artifact": ("p_artifact_sha256", "p_document_json"),
        "append_fpi_parse_result": ("p_parse_id", "p_record_sha256", "p_document_json"),
    }
    assert method in names and set(parameters) == set(names[method])
    return f"SELECT public.{method}(" + ",".join(literal(parameters[key]) for key in names[method]) + ");"


def parse_statement(document: dict, *, raw: str | None = None) -> str:
    text = canonical(document) if raw is None else raw
    return rpc_statement("append_fpi_parse_result", {"p_parse_id": document.get("parse_id", "0" * 64),
        "p_record_sha256": digest(text), "p_document_json": text})


def archive_state() -> list[str]:
    return [sql("SELECT encode(sha256(convert_to(coalesce(string_agg(to_jsonb(r)::text,"
                f"E'\\n' ORDER BY to_jsonb(r)::text),''),'UTF8')),'hex') FROM {table} r;")
            for table in (*TABLES, "fpi_captures")]


def bridge_client() -> MagicMock:
    client = MagicMock()

    def rpc(method: str, parameters: dict) -> MagicMock:
        def execute() -> MagicMock:
            return MagicMock(data=json.loads(sql("SET TIME ZONE 'Asia/Kolkata'; SET DateStyle='SQL, DMY'; "
                "SET ROLE service_role; " + rpc_statement(method, parameters))))
        return MagicMock(execute=execute)

    client.rpc.side_effect = rpc
    return client


def synthetic_parse(parser_sha256: str, *, sequence: int = 0, count: int = 2, failed: bool = False):
    from src.research.fpi_capture import build_fpi_capture
    from src.research.fpi_observation import FPI_ROUTES, build_fpi_observation
    from src.research.fpi_selection import FpiParsedDay, FpiParseResult

    capture = build_fpi_capture(body=f"authored synthetic capture {sequence}".encode(),
        source_url="https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx", requested_at=START,
        retrieved_at=START + timedelta(seconds=1), http_status=503 if failed else 200)
    days = []
    sources = []
    for offset in range(0 if failed else count):
        day = (date(2025, 12, 1) if count > 3 else date(2026, 1, 1)) + timedelta(days=offset)
        categories = {}
        usd = {}
        for category, routes in FPI_ROUTES.items():
            categories[category] = {
                "routes": {route: {"purchases_cr": "10.00", "sales_cr": "3.00", "net_cr": "7.00"}
                           for route in routes},
                "subtotal": {"purchases_cr": f"{10 * len(routes)}.00",
                             "sales_cr": f"{3 * len(routes)}.00", "net_cr": f"{7 * len(routes)}.00"}}
            usd[category] = {"routes_net_usd_million": {route: "0.70" for route in routes},
                             "subtotal_net_usd_million": f"{70 * len(routes) // 100}.{70 * len(routes) % 100:02d}"}
        observation = build_fpi_observation(reporting_date=day, categories=categories,
            total={"purchases_cr": "170.00", "sales_cr": "51.00", "net_cr": "119.00"},
            source_url="https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx", raw_sha256="0" * 64,
            parser_version="synthetic", retrieved_at=START, first_seen_at=START)
        source = canonical({"version": "nsdl-fpi-source-evidence-v1", "reporting_date": day.isoformat(),
            "usd_units": "USD_MILLION", "conversion_rate_units": "INR_PER_USD",
            "conversion_rate_inr_per_usd": "80.1234", "categories": usd, "total_net_usd_million": "11.90"})
        sources.append(source)
        days.append(FpiParsedDay(observation.document_json, digest(source)))
    parse = FpiParseResult(capture, parser_sha256, "fpi-inr-observation-v1", START + timedelta(seconds=2),
                           tuple(days), "HTTP_ERROR" if failed else None)
    return parse, tuple(sources)


def resign(document: dict) -> dict:
    """Recompute all pure identities independently to reach deep SQL checks."""
    value = copy.deepcopy(document)
    value["parse_id"] = digest(canonical([value["capture_sha256"], value["parser_sha256"], value["definition_version"]]))
    for member in value["days"]:
        member["value_sha256"] = digest(member["document_json"])
        member["source_evidence_sha256"] = digest(member["source_evidence_document_json"])
        member["membership_id"] = digest(canonical([value["parse_id"], member["value_sha256"], member["source_evidence_sha256"]]))
    value["content_sha256"] = digest(canonical({"parse_id": value["parse_id"], "recorded_at": value["recorded_at"],
        "failure_reason": value["failure_reason"], "days": [{"document_json": day["document_json"],
            "source_evidence_sha256": day["source_evidence_sha256"]} for day in value["days"]]}))
    return value


def rejected(document: dict, *, raw: str | None = None) -> None:
    before = archive_state()
    sql("SET ROLE service_role; " + parse_statement(document, raw=raw), error="FPI parse rejected")
    assert archive_state() == before


def verify_parse_storage():
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_artifact, build_fpi_parse_record, restore_fpi_parse_record

    artifact = build_fpi_artifact(kind="PARSER", body=b"retained synthetic implementation\x00\xff\n")
    client = bridge_client()
    with patch.object(writer, "_client", return_value=client):
        first = writer.archive_fpi_artifact(artifact)
        assert writer.archive_fpi_artifact(artifact) == {**first, "inserted": False}
        selector = build_fpi_artifact(kind="SELECTOR", body=b"retained synthetic implementation\x00\xff\n")
        assert writer.archive_fpi_artifact(selector)["inserted"]
        parse, sources = synthetic_parse(artifact.artifact_sha256)
        writer.archive_fpi_capture(parse.capture)
        receipt = writer.archive_fpi_parse_result(parse, source_evidence_documents=sources)
        assert writer.archive_fpi_parse_result(parse, source_evidence_documents=sources) == {**receipt, "inserted": False}
    assert first["inserted"] and receipt["inserted"] and not client.table.called
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    assert sql("SELECT document_json FROM fpi_parse_results WHERE parse_id=" + literal(parse.parse_id)) == record.document_json
    assert receipt["membership_ids"] == [parse.membership_id(day) for day in parse.days]
    assert restore_fpi_parse_record(record, parse.capture) == parse
    retained = json.loads(sql("SELECT json_agg(json_build_array(document_json,source_evidence_document_json) "
        "ORDER BY reporting_date) FROM fpi_parsed_memberships WHERE parse_id=" + literal(parse.parse_id)))
    assert retained == [[day.document_json, source] for day, source in zip(parse.days, sources, strict=True)]
    CHECKS.append("actual codec -> central writer -> service-role SQL retains exact artifact/INR/USD text and all pure identities; stable UTC retries")
    return artifact, parse, sources, record


def verify_malformed(record) -> None:
    good = json.loads(record.document_json)
    for key in ("parse_id", "content_sha256", "capture_sha256", "parser_sha256"):
        rejected({**good, key: "0" * 64})
    for key, values in {"version": [None, 1, "future"], "definition_version": ["future"],
        "recorded_at": ["2099-01-01T00:00:00+00:00", "2026-01-03T12:00:00+00:00", "2026-01-03T12:00:02.0000001+00:00", "2026-01-03T12:00:02.000000+00:00"],
        "failure_reason": ["SENSITIVE_SENTINEL raw error", True, "A" * 65, "HTTP_ERROR"],
        "days": [[], {}, None, good["days"] * 16, list(reversed(good["days"])), [good["days"][0]] * 2]}.items():
        for value in values:
            malformed = {**good, key: value}
            rejected(resign(malformed) if isinstance(malformed["days"], list) else malformed)
    rejected({**good, "extra": "SENSITIVE_SENTINEL"})
    rejected(good, raw=record.document_json[:-1] + ',"version":"fpi-parse-record-v1"}')
    rejected(good, raw=" " + record.document_json)
    rejected(good, raw=record.document_json.replace('"version":', '"bad":"\\u0000","version":', 1))
    rejected(good, raw=record.document_json.replace('"version":', '"bad":"\\ud800","version":', 1))
    rejected(good, raw=" " * 4_000_001)
    mutations = [
        ("document_json", lambda d: d["total"].update(net_cr="119.02")),
        ("document_json", lambda d: d["categories"]["Equity"]["routes"]["Stock Exchange"].update(purchases_cr="-10.00")),
        ("document_json", lambda d: d["categories"]["Equity"]["routes"]["Stock Exchange"].update(net_cr="7.02")),
        ("document_json", lambda d: d["categories"]["Equity"]["subtotal"].update(purchases_cr="20.02", net_cr="14.02")),
        ("document_json", lambda d: d["total"].update(purchases_cr="170.05", net_cr="119.05")),
        ("document_json", lambda d: d["total"].update(purchases_cr="1.70e2")),
        ("document_json", lambda d: d["total"].update(sales_cr=51)),
        ("document_json", lambda d: d["total"].update(net_cr="-0.00")),
        ("document_json", lambda d: d["categories"].pop("AIFs")),
        ("source_evidence_document_json", lambda d: d.update(reporting_date="2026-01-02")),
        ("source_evidence_document_json", lambda d: d.update(conversion_rate_inr_per_usd="0.0000")),
        ("source_evidence_document_json", lambda d: d.update(conversion_rate_inr_per_usd=80.1234)),
        ("source_evidence_document_json", lambda d: d.update(total_net_usd_million="11.95")),
        ("source_evidence_document_json", lambda d: d["categories"]["Equity"].update(subtotal_net_usd_million="1.42")),
        ("source_evidence_document_json", lambda d: d["categories"]["Equity"]["routes_net_usd_million"].update(extra="0.00")),
    ]
    for field, mutate in mutations:
        malformed = copy.deepcopy(good)
        nested = json.loads(malformed["days"][0][field])
        mutate(nested)
        malformed["days"][0][field] = canonical(nested)
        rejected(resign(malformed))
    for field in ("document_json", "source_evidence_document_json"):
        malformed = copy.deepcopy(good)
        malformed["days"][0][field] = malformed["days"][0][field][:-1] + ',"version":"duplicate"}'
        rejected(resign(malformed))
    for wrong_day in ("2026-1-1", "2026-02-30", "2026-01-04", "0000-01-01"):
        malformed = copy.deepcopy(good)
        malformed["days"][0]["reporting_date"] = wrong_day
        for field in ("document_json", "source_evidence_document_json"):
            nested = json.loads(malformed["days"][0][field])
            nested["reporting_date"] = wrong_day
            malformed["days"][0][field] = canonical(nested)
        rejected(resign(malformed))
    CHECKS.append("direct SQL rejects forged identities, duplicate keys/dates, partial/failure mixtures, types, time/size limits, noncanonical text and independently rehashed INR/USD defects without writes")


def verify_rounding_boundaries(artifact) -> None:
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_parse_record

    # Every probe has a fresh, retained capture and an absent parse identity.
    # Rehashing deliberately bypasses hash rejection and reaches numeric checks.
    cases = [("gross_net", 1, True), ("gross_net", 2, False),
             ("inr_subtotal", 1, True), ("inr_subtotal", 2, False),
             ("inr_total", 4, True), ("inr_total", 5, False),
             ("usd_subtotal", 1, True), ("usd_subtotal", 2, False),
             ("usd_total", 4, True), ("usd_total", 5, False)]
    for sequence, (kind, hundredths, accepted) in enumerate(cases, 100):
        parse, sources = synthetic_parse(artifact.artifact_sha256, sequence=sequence)
        with patch.object(writer, "_client", return_value=bridge_client()):
            writer.archive_fpi_capture(parse.capture)
        document = json.loads(build_fpi_parse_record(parse, source_evidence_documents=sources).document_json)
        field = "source_evidence_document_json" if kind.startswith("usd") else "document_json"
        nested = json.loads(document["days"][0][field])
        if kind == "gross_net":
            nested["categories"]["Equity"]["routes"]["Stock Exchange"]["net_cr"] = f"7.{hundredths:02d}"
        elif kind == "inr_subtotal":
            nested["categories"]["Equity"]["subtotal"].update(purchases_cr=f"20.{hundredths:02d}", net_cr=f"14.{hundredths:02d}")
        elif kind == "inr_total":
            nested["total"].update(purchases_cr=f"170.{hundredths:02d}", net_cr=f"119.{hundredths:02d}")
        elif kind == "usd_subtotal":
            nested["categories"]["Equity"]["subtotal_net_usd_million"] = f"1.{40 + hundredths:02d}"
        else:
            nested["total_net_usd_million"] = f"11.{90 + hundredths:02d}"
        document["days"][0][field] = canonical(nested)
        document = resign(document)
        assert sql("SELECT count(*) FROM fpi_parse_results WHERE parse_id=" + literal(document["parse_id"])) == "0"
        if accepted:
            assert json.loads(sql("SET ROLE service_role; " + parse_statement(document)))["inserted"]
        else:
            rejected(document)
    CHECKS.append("fresh independently rehashed positive/negative controls distinguish exact gross/net, INR child/total and USD child/total rounding boundaries")


def verify_dependencies_and_rollback(artifact) -> None:
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_artifact, build_fpi_parse_record

    client = bridge_client()
    parse, sources = synthetic_parse(artifact.artifact_sha256, sequence=10)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    rejected(json.loads(record.document_json))
    selector = build_fpi_artifact(kind="SELECTOR", body=b"selector only")
    with patch.object(writer, "_client", return_value=client):
        writer.archive_fpi_capture(parse.capture)
        writer.archive_fpi_artifact(selector)
    absent = replace(parse, parser_sha256="0" * 64)
    selected = replace(parse, parser_sha256=selector.artifact_sha256)
    for candidate in (absent, selected):
        rejected(json.loads(build_fpi_parse_record(candidate, source_evidence_documents=sources).document_json))
    # Real failure during the second membership INSERT proves rollback after the
    # result row and first member have been attempted, not just validation before writes.
    sql("CREATE FUNCTION reject_second_member() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
        "IF NEW.reporting_date='2026-01-02'::date THEN RAISE EXCEPTION 'injected'; END IF; RETURN NEW; END $$;"
        "CREATE TRIGGER reject_second BEFORE INSERT ON fpi_parsed_memberships FOR EACH ROW EXECUTE FUNCTION reject_second_member();")
    try:
        rejected(json.loads(record.document_json))
    finally:
        sql("DROP TRIGGER reject_second ON fpi_parsed_memberships; DROP FUNCTION reject_second_member();")
    assert json.loads(sql("SET ROLE service_role; " + parse_statement(json.loads(record.document_json))))["inserted"]
    failed, empty = synthetic_parse(artifact.artifact_sha256, sequence=11, failed=True)
    with patch.object(writer, "_client", return_value=client):
        writer.archive_fpi_capture(failed.capture)
        receipt = writer.archive_fpi_parse_result(failed, source_evidence_documents=empty)
    assert receipt["membership_ids"] == []
    assert sql("SELECT count(*) FROM fpi_parsed_memberships WHERE parse_id=" + literal(failed.parse_id)) == "0"
    CHECKS.append("absent capture/PARSER and SELECTOR-only dependencies reject; forced second-member failure rolls back the result and every member; complete failed parse stores no members")


def verify_concurrency(artifact) -> None:
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_parse_record

    parse, sources = synthetic_parse(artifact.artifact_sha256, sequence=20)
    with patch.object(writer, "_client", return_value=bridge_client()):
        writer.archive_fpi_capture(parse.capture)
    document = json.loads(build_fpi_parse_record(parse, source_evidence_documents=sources).document_json)
    barrier = threading.Barrier(2)

    def attempt(candidate: dict) -> dict:
        barrier.wait(timeout=10)
        output = sql("BEGIN; SET LOCAL ROLE service_role; " + parse_statement(candidate) + " SELECT pg_sleep(0.2); COMMIT;")
        return json.loads(output.splitlines()[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(attempt, [document, document]))
    assert sorted(receipt["inserted"] for receipt in receipts) == [False, True]
    assert receipts[0]["stored_at"] == receipts[1]["stored_at"]
    assert receipts[0]["membership_ids"] == receipts[1]["membership_ids"]
    changed = resign({**document, "recorded_at": "2026-01-03T12:00:03+00:00"})
    rejected(changed)
    # Competing, individually valid results under a fresh parse identity.
    parse, sources = synthetic_parse(artifact.artifact_sha256, sequence=21)
    with patch.object(writer, "_client", return_value=bridge_client()):
        writer.archive_fpi_capture(parse.capture)
    first = json.loads(build_fpi_parse_record(parse, source_evidence_documents=sources).document_json)
    second = resign({**first, "recorded_at": "2026-01-03T12:00:03+00:00"})
    barrier = threading.Barrier(2)

    def conflict(candidate: dict):
        try:
            return attempt(candidate)
        except AssertionError as exc:
            assert "FPI parse rejected" in str(exc)
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(conflict, [first, second]))
    assert sum(result is not None for result in results) == 1
    retained = sql("SELECT document_json FROM fpi_parse_results WHERE parse_id=" + literal(parse.parse_id))
    assert retained in (canonical(first), canonical(second))
    rejected(second if retained == canonical(first) else first)
    CHECKS.append("concurrent exact retries return one stable result/complete membership receipt; conflicting valid recordings produce one winner and one unchanged rejection")


def verify_paused_writer(artifact) -> None:
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_parse_record

    parse, sources = synthetic_parse(artifact.artifact_sha256, sequence=30)
    with patch.object(writer, "_client", return_value=bridge_client()):
        writer.archive_fpi_capture(parse.capture)
    record = build_fpi_parse_record(parse, source_evidence_documents=sources)
    process = subprocess.Popen(BASE + ["-d", DB], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    output: queue.Queue[bytes] = queue.Queue()

    def reader() -> None:
        assert process.stdout is not None
        for line in iter(process.stdout.readline, b""):
            output.put(line)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    visibility = ("SET ROLE service_role; SELECT json_build_array("
        "(SELECT count(*) FROM fpi_parse_results WHERE parse_id=" + literal(parse.parse_id) + "),"
        "(SELECT count(*) FROM fpi_parsed_memberships WHERE parse_id=" + literal(parse.parse_id) + "));")
    try:
        def rpc(method: str, parameters: dict) -> MagicMock:
            assert method == "append_fpi_parse_result"

            def execute() -> MagicMock:
                assert process.stdin is not None
                process.stdin.write(("BEGIN; SET LOCAL ROLE service_role; " + rpc_statement(method, parameters)
                    + " SELECT 'PARSE_READY_UNCOMMITTED';\n").encode("utf-8"))
                process.stdin.flush()
                receipt = json.loads(output.get(timeout=20).decode("utf-8"))
                assert output.get(timeout=20).strip() == b"PARSE_READY_UNCOMMITTED"
                # Receipt exists in the real writer connection, while a different
                # connection sees none of the uncommitted rows.
                assert json.loads(sql(visibility)) == [0, 0]
                process.stdin.write(b"COMMIT; SELECT 'PARSE_COMMITTED';\n")
                process.stdin.flush()
                assert output.get(timeout=20).strip() == b"PARSE_COMMITTED"
                assert json.loads(sql(visibility)) == [1, 2]
                return MagicMock(data=receipt)

            return MagicMock(execute=execute)

        client = MagicMock()
        client.rpc.side_effect = rpc
        with patch.object(writer, "_client", return_value=client):
            receipt = writer.archive_fpi_parse_result(parse, source_evidence_documents=sources)
        assert receipt["record_sha256"] == record.record_sha256
        assert process.stdin is not None
        process.stdin.write(b"\\q\n")
        process.stdin.flush()
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        thread.join(timeout=10)
    CHECKS.append("real central-writer transaction pauses after RPC receipt using a bounded session handshake; separate service reader sees [0,0] before commit and [1,2] after commit")


def verify_permissions() -> None:
    for table in TABLES:
        assert sql(f"SELECT relrowsecurity FROM pg_class WHERE oid='public.{table}'::regclass") == "t"
        assert sql(f"SELECT count(*) FROM pg_class c,aclexplode(c.relacl) a WHERE c.oid='public.{table}'::regclass AND a.grantee=0") == "0"
        assert sql(f"SELECT count(*) FROM {table}") == sql(f"SET ROLE service_role; SELECT count(*) FROM {table}")
        for role in ("anon", "authenticated"):
            sql(f"SET ROLE {role}; SELECT * FROM {table}", error="permission denied")
        for role in ("anon", "authenticated", "service_role"):
            for action in (f"INSERT INTO {table} DEFAULT VALUES", f"UPDATE {table} SET document_json=document_json", f"DELETE FROM {table}", f"TRUNCATE {table}"):
                sql(f"SET ROLE {role}; {action}", error="permission denied")
        for action in (f"UPDATE {table} SET document_json=document_json", f"DELETE FROM {table}", f"TRUNCATE {table} CASCADE"):
            sql(action, error="immutable")
        sql(f"GRANT SELECT ON {table} TO anon,authenticated")
        for role in ("anon", "authenticated"):
            assert sql(f"SET ROLE {role}; SELECT count(*) FROM {table}") == "0"
        sql(f"REVOKE SELECT ON {table} FROM anon,authenticated")
    for role in ("anon", "authenticated"):
        for function in ("append_fpi_artifact('','')", "append_fpi_parse_result('','','')"):
            sql(f"SET ROLE {role}; SELECT public.{function}", error="permission denied")
    functions = sql("SELECT oid::regprocedure::text FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname LIKE 'fpi_parse_%' ORDER BY proname").splitlines()
    assert len(functions) == 6
    for function in functions:
        for role in ("anon", "authenticated", "service_role"):
            assert sql(f"SELECT has_function_privilege('{role}',{literal(function)},'EXECUTE')") == "f"
    assert sql("SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace AND "
        "(proname LIKE 'fpi_parse_%' OR proname IN ('append_fpi_artifact','append_fpi_parse_result')) "
        "AND 'search_path=pg_catalog, public'=ANY(proconfig)") == "8"
    assert sql("SELECT count(*) FROM pg_proc WHERE proname IN ('append_fpi_artifact','append_fpi_parse_result') AND prosecdef") == "2"
    assert sql("SELECT count(*) FROM pg_proc p,aclexplode(p.proacl) a WHERE p.pronamespace='public'::regnamespace AND "
        "(p.proname LIKE 'fpi_parse_%' OR p.proname IN ('append_fpi_artifact','append_fpi_parse_result')) AND a.grantee=0") == "0"
    CHECKS.append("explicit grants, RLS, fixed search paths and private helpers withstand broad defaults; owner UPDATE/DELETE/TRUNCATE fail on every new table")


def verify_artifacts(artifact) -> None:
    from src.db import writer
    from src.research.fpi_parse_record import build_fpi_artifact

    good = json.loads(artifact.document_json)
    malformed = [{**good, "body_size": 0}, {**good, "body_size": True}, {**good, "kind": "OTHER"},
        {**good, "body_base64": "AB=="}, {**good, "artifact_sha256": "0" * 64}, {**good, "extra": "SENSITIVE_SENTINEL"}]
    for value in malformed:
        before = archive_state()
        sql("SET ROLE service_role; " + rpc_statement("append_fpi_artifact", {
            "p_artifact_sha256": artifact.artifact_sha256, "p_document_json": canonical(value)}), error="FPI artifact rejected")
        assert archive_state() == before
    for value in (artifact.document_json.replace(f'"body_size":{good["body_size"]}', f'"body_size":{good["body_size"]}.0'),
                  artifact.document_json.replace(f'"body_size":{good["body_size"]}', f'"body_size":{good["body_size"]}e0'),
                  artifact.document_json[:-1] + ',"kind":"PARSER"}', " " * 7_000_001):
        sql(rpc_statement("append_fpi_artifact", {"p_artifact_sha256": artifact.artifact_sha256,
            "p_document_json": value}), error="FPI artifact rejected")
    maximum = build_fpi_artifact(kind="PARSER", body=b"z" * 5_000_000)
    with patch.object(writer, "_client", return_value=bridge_client()):
        assert writer.archive_fpi_artifact(maximum)["inserted"]
    assert sql("SELECT body_size FROM fpi_implementation_artifacts WHERE artifact_sha256=" + literal(maximum.artifact_sha256)) == "5000000"
    oversized_body = b"z" * 5_000_001
    oversized = {**json.loads(maximum.document_json), "body_size": len(oversized_body),
                 "body_base64": base64.b64encode(oversized_body).decode("ascii"),
                 "artifact_sha256": hashlib.sha256(oversized_body).hexdigest()}
    sql(rpc_statement("append_fpi_artifact", {"p_artifact_sha256": oversized["artifact_sha256"],
        "p_document_json": canonical(oversized)}), error="FPI artifact rejected")
    complete, sources = synthetic_parse(artifact.artifact_sha256, sequence=300, count=31)
    with patch.object(writer, "_client", return_value=bridge_client()):
        writer.archive_fpi_capture(complete.capture)
        assert len(writer.archive_fpi_parse_result(complete, source_evidence_documents=sources)["membership_ids"]) == 31
    CHECKS.append("artifact binary bytes and both declared kinds round-trip; exact five-million-byte bound passes; malformed schema/base64/hash/integer lexemes and oversized documents reject")


def main() -> None:
    sql(f'CREATE DATABASE "{DB}"', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE unrelated_sentinel(id integer PRIMARY KEY,note text); INSERT INTO unrelated_sentinel VALUES(1,'preserve'); GRANT SELECT ON unrelated_sentinel TO anon; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;")
        preserved = sql("SELECT jsonb_agg(to_jsonb(r)) FROM unrelated_sentinel r")
        original_tables = {table: sql(f"SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)::text) FROM {table} r")
                           for table in ("regime_calls", "signals", "call_rationale")}
        original_acl = sql("SELECT jsonb_agg(jsonb_build_array(relname,relacl::text) ORDER BY relname) FROM pg_class "
            "WHERE oid IN ('regime_calls'::regclass,'signals'::regclass,'call_rationale'::regclass,'unrelated_sentinel'::regclass)")
        sql((ROOT / "supabase/migrations/20260927000010_fpi_capture_storage.sql").read_text(encoding="utf-8"))
        capture_acl_query = ("SELECT jsonb_agg(jsonb_build_array(proname,proacl::text) ORDER BY proname) FROM pg_proc "
            "WHERE pronamespace='public'::regnamespace AND (proname LIKE 'fpi_capture_%' OR proname IN ('append_fpi_capture','reject_fpi_capture_mutation'))")
        capture_acl = sql(capture_acl_query)
        migration = (ROOT / "supabase/migrations/20260927000011_fpi_parse_storage.sql").read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        print("RUN: real codec and writer bridge", flush=True)
        artifact, _, _, _ = verify_parse_storage()
        from src.db import writer
        from src.research.fpi_parse_record import build_fpi_parse_record

        unstored, sources = synthetic_parse(artifact.artifact_sha256, sequence=99)
        with patch.object(writer, "_client", return_value=bridge_client()):
            writer.archive_fpi_capture(unstored.capture)
        record = build_fpi_parse_record(unstored, source_evidence_documents=sources)
        print("RUN: malformed SQL and numeric controls", flush=True)
        verify_malformed(record)
        print("RUN: independently rehashed rounding boundaries", flush=True)
        verify_rounding_boundaries(artifact)
        print("RUN: dependencies, failure preservation and rollback", flush=True)
        verify_dependencies_and_rollback(artifact)
        print("RUN: retry/conflict concurrency", flush=True)
        verify_concurrency(artifact)
        print("RUN: paused writer and concurrent reader", flush=True)
        verify_paused_writer(artifact)
        print("RUN: artifact size boundaries", flush=True)
        verify_artifacts(artifact)
        print("RUN: privacy and immutable reapplication", flush=True)
        verify_permissions()
        before = archive_state()
        sql(migration)
        assert archive_state() == before
        assert sql("SELECT jsonb_agg(to_jsonb(r)) FROM unrelated_sentinel r") == preserved
        assert sql("SELECT has_table_privilege('anon','unrelated_sentinel','SELECT')") == "t"
        assert sql(capture_acl_query) == capture_acl
        assert sql("SELECT jsonb_agg(jsonb_build_array(relname,relacl::text) ORDER BY relname) FROM pg_class "
            "WHERE oid IN ('regime_calls'::regclass,'signals'::regclass,'call_rationale'::regclass,'unrelated_sentinel'::regclass)") == original_acl
        for table, contents in original_tables.items():
            assert sql(f"SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)::text) FROM {table} r") == contents
        CHECKS.append("fresh, empty and populated reapplication preserves exact records, capture rows and unrelated table privileges")
        for check in CHECKS:
            print("PASS:", check)
        print("REPAIR_FPI_PARSE_DB_VERIFIED")
    finally:
        assert DB.startswith("fxfpiparse_") and len(DB) == 43
        sql(f'DROP DATABASE "{DB}" WITH (FORCE)', database="postgres")


if __name__ == "__main__":
    main()

