"""Prove private attempt evidence against the existing socket-only PostgreSQL.

Synthetic responses; real capture, event, constructor and central writer code.
This script owns only its uniquely named scratch database, never runtime startup.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
spec = importlib.util.spec_from_file_location("quote_storage_verifier", ROOT / "scripts/repair/verify-quote-storage-db.py")
assert spec is not None and spec.loader is not None
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
DB = "fxattempt_" + uuid.uuid4().hex
_sql = storage.sql
CHECKS: list[str] = []
REJECTIONS = 0
AS_OF = storage.AS_OF
canonical = storage.canonical
literal = storage.text_literal
fingerprint = storage.fingerprint
FILES = (
    "pipeline/src/research/quote_acquisition.py", "pipeline/src/research/quote_attempt.py",
    "pipeline/src/research/quote_capture.py", "pipeline/src/research/quote_reference.py",
    "pipeline/src/db/writer.py",
)


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    return _sql(statement, database=database, error=error)


storage.sql = sql


def common(*, pair: str = "EURUSD") -> dict:
    from src.research.quote_attempt import CLIENT_VERSION, DEFAULT_LIMITS, quote_runtime_manifest
    manifest, digest = quote_runtime_manifest()
    return {"attempt_id": str(uuid.uuid4()), "pair": pair,
            "instrument": {"EURUSD": "C:EUR-USD", "USDJPY": "C:USD-JPY", "USDINR": "C:USD-INR"}[pair],
            "window_start_ns": str(storage.START), "window_end_ns": str(storage.START+storage.DAY_NS),
            "implementation_sha256": digest, "client_version": CLIENT_VERSION,
            "runtime_manifest_json": manifest, "limits": dict(DEFAULT_LIMITS)}


def event(base: dict, *, previous: dict | None = None, kind: str = "started", **changes: object) -> dict:
    from src.research.quote_attempt import make_quote_acquisition_event
    sequence = 0 if previous is None else previous["sequence"]+1
    instant = AS_OF
    if kind == "started":
        instant -= timedelta(hours=2)
    elif kind == "page_saved":
        instant -= timedelta(hours=2)
        instant += timedelta(minutes=9+sequence, seconds=1)
    return make_quote_acquisition_event(base, sequence=sequence,
                                        previous_event_sha256=None if previous is None else previous["event_sha256"],
                                        kind=kind, occurred_at=changes.pop("occurred_at", instant), **changes)


def unsigned(value: dict) -> dict:
    return {key: item for key, item in value.items() if key != "event_sha256"}


def rpc(value: dict | None = None, *, raw: str | None = None, digest: str | None = None) -> str:
    text = raw if raw is not None else canonical(unsigned(value or {}))
    return "SELECT public.append_quote_acquisition_event(" + literal(digest or fingerprint(text)) + "," + literal(text) + ");"


def append(value: dict) -> dict:
    return json.loads(sql("SET ROLE service_role; " + rpc(value)))


def state() -> str:
    return sql("SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY attempt_id,sequence),'[]') FROM quote_acquisition_events e;")


def rejected(value: dict | None = None, *, raw: str | None = None, digest: str | None = None) -> None:
    global REJECTIONS
    before = state()
    sql(rpc(value, raw=raw, digest=digest), error="Quote acquisition event rejected")
    assert state() == before
    REJECTIONS += 1


def bridge_client() -> MagicMock:
    def call(method: str, parameters: dict) -> MagicMock:
        if method == "append_quote_acquisition_event":
            assert set(parameters) == {"p_event_sha256", "p_unsigned_json"}
            statement = rpc(raw=parameters["p_unsigned_json"], digest=parameters["p_event_sha256"])
        else:
            kind = method.removeprefix("append_quote_")
            assert kind in {"capture", "snapshot"}
            assert set(parameters) == {f"p_{kind}_sha256", "p_unsigned_json"}
            statement = storage.rpc_sql(kind, parameters["p_unsigned_json"], parameters[f"p_{kind}_sha256"])
        assert "opaque-private-cursor" not in parameters["p_unsigned_json"]
        return MagicMock(execute=lambda: MagicMock(data=json.loads(sql("SET ROLE service_role; " + statement))))
    client = MagicMock()
    client.rpc.side_effect = call
    return client


def verify_writer_and_progress() -> tuple[dict, list[dict], list[dict], str]:
    from src.db import writer
    from src.research.quote_reference import build_quote_reference
    base = common()
    pages = [storage.capture(body=b'{"status":"OK","results":[],"next_url":"https://api.massive.com/v3/quotes/C:EUR-USD?cursor=opaque-private-cursor"}', minute=10),
             storage.capture(index=1, cursor="opaque-private-cursor", minute=11)]
    events = [event(base)]
    client = bridge_client()
    with patch.object(writer, "_client", return_value=client):
        for index in range(3):
            if index:
                writer.archive_quote_capture(pages[index-1])
                events.append(event(base, previous=events[-1], kind="page_saved", capture_sha256=pages[index-1]["capture_sha256"]))
            receipt = writer.archive_quote_acquisition_event(events[-1])
            assert receipt == {"event_sha256": events[-1]["event_sha256"], "attempt_id": base["attempt_id"], "sequence": index, "inserted": True}
        snapshot = writer.archive_quote_snapshot(pages, as_of=AS_OF,
                                                implementation_sha256=base["implementation_sha256"], client_version=base["client_version"])
        events.append(event(base, previous=events[-1], kind="finished", status="complete", reason="completed", snapshot_sha256=snapshot["snapshot_sha256"]))
        assert writer.archive_quote_acquisition_event(events[-1])["inserted"] is True
        for item in events:
            assert writer.archive_quote_acquisition_event(item)["inserted"] is False
            stored = sql("SELECT to_json(unsigned_json) FROM quote_acquisition_events WHERE event_sha256="+literal(item["event_sha256"])+";")
            assert json.loads(stored) == canonical(unsigned(item))
            assert json.loads(sql("SELECT document FROM quote_acquisition_events WHERE event_sha256="+literal(item["event_sha256"])+";")) == unsigned(item)
    assert client.table.call_count == 0
    stored_reference = json.loads(sql("SELECT document->'reference' FROM quote_snapshots WHERE snapshot_sha256="+literal(snapshot["snapshot_sha256"])+";"))
    assert stored_reference == build_quote_reference(pages, as_of=AS_OF)
    assert stored_reference["acquisition_complete"] is True and stored_reference["validation_eligible"] is False
    # Zero-response failures need neither capture nor snapshot, for all locked pairs.
    for pair in ("EURUSD", "USDJPY", "USDINR"):
        zero_base = common(pair=pair)
        start = event(zero_base)
        append(start)
        finish = event(zero_base, previous=start, kind="finished", status="failed", reason="request_failed")
        assert append(finish)["inserted"] is True
        assert append(start)["inserted"] is False and append(finish)["inserted"] is False
    CHECKS.append("G1 actual Python event/capture/constructor/writer -> service-role SQL round trip; exact unsigned text and reference; all three pairs and zero-response failures; no price qualification")
    return base, pages, events, snapshot["snapshot_sha256"]


def verify_schema() -> None:
    original = event(common())
    for invalid in (None, [], "SENSITIVE_SENTINEL", 123, True):
        rejected(raw=canonical(invalid))
    rejected(original, digest="0"*64)
    rejected(original, raw=canonical(unsigned(original))[:-1]+',"version":"duplicate"}')
    rejected(raw='{"SENSITIVE_SENTINEL":')
    rejected(original, raw=" "*65537+canonical(unsigned(original)))
    rejected({**original, "extra": "SENSITIVE_SENTINEL"})
    for key in unsigned(original):
        missing = unsigned(original)
        del missing[key]
        rejected(raw=canonical(missing))
    for key, values in {
        "version": [None, True, "v2"], "attempt_id": [None, 123, "bad", original["attempt_id"].upper()],
        "sequence": [None, True, -1, 10002, "0", 0.0, 1],
        "previous_event_sha256": [False, "0"*64, "bad"], "kind": [None, True, "unknown"],
        "occurred_at": [None, "2099-01-01T00:00:00+00:00", "2026-02-30T00:00:00+00:00", "2026-05-03T00:00:00Z", "2026-05-03T00:00:00.000000+00:00"],
        "pair": [None, "GBPUSD"], "instrument": [None, "C:USD-JPY"],
        "window_start_ns": [storage.START, "01", str(storage.START+1), "0"*22],
        "window_end_ns": [None, str(storage.START+1)], "implementation_sha256": [None, "A"*64, "0"*64],
        "client_version": [None, "test"], "capture_sha256": [False, "0"*64], "snapshot_sha256": [False, "0"*64],
        "status": [None, "failed"], "reason": [False, "request_failed", "SENSITIVE_SENTINEL"],
        "limits": [None, [], {}], "runtime_manifest_json": [None, True, "{}", "SENSITIVE_SENTINEL"],
    }.items():
        for value in values:
            try:
                rejected(raw=json.dumps({**unsigned(original), key: value}))
            except AssertionError as failure:
                raise AssertionError(f"Unexpected schema outcome for {key}={value!r}") from failure
    limits = original["limits"]
    for key, maximum in {"max_pages": 10000, "max_page_bytes": 16777216, "max_total_bytes": 268435456,
                         "deadline_seconds": 3600, "request_timeout_seconds": 60}.items():
        for invalid in (None, True, 0, -1, 1.0, "1", maximum+1):
            rejected(raw=json.dumps({**unsigned(original), "limits": {**limits, key: invalid}}))
    rejected({**original, "limits": {**limits, "extra": 1}})
    rejected({**original, "limits": {**limits, "max_total_bytes": 1}})
    rejected(raw=canonical(unsigned(original)).replace('"sequence":0', '"sequence":0e0'))
    rejected(raw=canonical(unsigned(original)).replace('"max_pages":200', '"max_pages":2e2'))
    manifest = json.loads(original["runtime_manifest_json"])
    bad_manifests = [[], None, {**manifest, "extra": "SENSITIVE_SENTINEL"}, {**manifest, "version": None},
                     {**manifest, "client_version": "test"}, {**manifest, "files": {}},
                     {**manifest, "dependencies": {}},
                     {**manifest, "files": {**manifest["files"], FILES[0]: "A"*64}},
                     {**manifest, "files": {**manifest["files"], "/private/path": "0"*64}}]
    for bad_version in (None, True, "", "SENSITIVE_SENTINEL token", "x"*129, "é"):
        bad_manifests.append({**manifest, "dependencies": {"python": bad_version, "aiohttp": "1.0"}})
    texts = [canonical(value) for value in bad_manifests]
    texts += [json.dumps(manifest, indent=1), canonical(manifest)[:-1]+',"version":"quote-runtime-manifest-v1"}']
    for text in texts:
        rejected({**original, "runtime_manifest_json": text, "implementation_sha256": fingerprint(text)})
    # Valid noncanonical outer text remains authoritative exact bytes, while the
    # nested manifest must retain its canonical form.
    text = json.dumps(unsigned(original), indent=1)
    assert json.loads(sql(rpc(raw=text)))["inserted"] is True
    assert json.loads(sql("SELECT to_json(unsigned_json) FROM quote_acquisition_events WHERE event_sha256="+literal(fingerprint(text))+";")) == text
    CHECKS.append("G2 strict types/keys/hashes/timestamps/limits/runtime manifests; duplicate JSON keys and lexical exponent integers reject; exact noncanonical outer bytes preserved; sanitized SQL errors")


def verify_lineage(base: dict, pages: list[dict], events: list[dict], snapshot_hash: str) -> None:
    from src.db import writer
    # Anything after finished, wrong chain, identity changes, out-of-order time.
    rejected({**events[-1], "sequence": 4, "previous_event_sha256": events[-1]["event_sha256"]})
    fresh = {**base, "attempt_id": str(uuid.uuid4())}
    start = event(fresh)
    append(start)
    page = event(fresh, previous=start, kind="page_saved", capture_sha256=pages[0]["capture_sha256"])
    for update in ({"sequence": 2}, {"previous_event_sha256": "0"*64}, {"capture_sha256": "0"*64},
                   {"capture_sha256": pages[1]["capture_sha256"]}, {"occurred_at": (AS_OF-timedelta(hours=3)).isoformat()},
                   {"implementation_sha256": "0"*64}, {"limits": {**fresh["limits"], "max_pages": 199}},
                   {"pair": "USDJPY", "instrument": "C:USD-JPY"}, {"runtime_manifest_json": fresh["runtime_manifest_json"]}):
        rejected({**page, **update})
    absent = common()
    rejected(event(absent, previous=event(absent), kind="finished", status="failed", reason="read_failed"))
    append(page)
    # Page receipt must precede its event (independent of chain clock order).
    early = common()
    early_start = {**event(early), "occurred_at": (AS_OF-timedelta(hours=3)).isoformat()}
    early_start["event_sha256"] = fingerprint(canonical(unsigned(early_start)))
    append(early_start)
    early_page = event(early, previous=early_start, kind="page_saved", capture_sha256=pages[0]["capture_sha256"])
    rejected({**early_page, "occurred_at": (AS_OF-timedelta(hours=2)).isoformat()})
    # Matching snapshot hash alone is insufficient: missing/extra/reordered pages,
    # source version/hash, identity and snapshot time are independently checked.
    finish = event(fresh, previous=page, kind="finished", status="complete", reason="completed", snapshot_sha256=snapshot_hash)
    rejected(finish)  # Existing two-page snapshot versus this one acknowledged page.
    for update in ({"snapshot_sha256": "0"*64}, {"snapshot_sha256": None}, {"reason": "read_failed"},
                   {"status": "failed"}, {"reason": None}, {"reason": "SENSITIVE_SENTINEL"},
                   {"capture_sha256": pages[0]["capture_sha256"]}, {"sequence": 3}):
        rejected({**finish, **update})
    second = event(fresh, previous=page, kind="page_saved", capture_sha256=pages[1]["capture_sha256"])
    append(second)
    with patch.object(writer, "_client", return_value=bridge_client()):
        variants = [([pages[1], pages[0]], AS_OF, fresh["implementation_sha256"], fresh["client_version"]),
                    (pages, AS_OF, "0"*64, fresh["client_version"]),
                    (pages, AS_OF, fresh["implementation_sha256"], "wrong-version"),
                    (pages, AS_OF+timedelta(seconds=1), fresh["implementation_sha256"], fresh["client_version"]),
                    ([pages[0]], AS_OF, fresh["implementation_sha256"], fresh["client_version"])]
        for selected, instant, implementation, client in variants:
            snap = writer.archive_quote_snapshot(selected, as_of=instant, implementation_sha256=implementation, client_version=client)
            rejected(event(fresh, previous=second, kind="finished", status="complete", reason="completed", snapshot_sha256=snap["snapshot_sha256"]))
        # One page with a continuation is diagnostic and cannot complete an attempt.
        diagnostic = writer.archive_quote_snapshot([pages[0]], as_of=AS_OF, implementation_sha256=fresh["implementation_sha256"], client_version=fresh["client_version"])
    diagnostic_base = {**fresh, "attempt_id": str(uuid.uuid4())}
    diag_start = event(diagnostic_base)
    append(diag_start)
    diag_page = event(diagnostic_base, previous=diag_start, kind="page_saved", capture_sha256=pages[0]["capture_sha256"])
    append(diag_page)
    rejected(event(diagnostic_base, previous=diag_page, kind="finished", status="complete", reason="completed", snapshot_sha256=diagnostic["snapshot_sha256"]))
    diag_finish = event(diagnostic_base, previous=diag_page, kind="finished", status="failed", reason="read_failed", snapshot_sha256=diagnostic["snapshot_sha256"])
    append(diag_finish)
    append(event(fresh, previous=second, kind="finished", status="complete", reason="completed", snapshot_sha256=snapshot_hash))
    # Page cap and zero-page snapshot rejection must not depend on the constructor.
    limited = common()
    limited["limits"]["max_pages"] = 1
    limit_start = event(limited)
    append(limit_start)
    limit_page = event(limited, previous=limit_start, kind="page_saved", capture_sha256=pages[0]["capture_sha256"])
    append(limit_page)
    rejected({**unsigned(second), **{key: limited[key] for key in ("attempt_id", "limits")}, "previous_event_sha256": limit_page["event_sha256"]})
    rejected({**finish, "attempt_id": early["attempt_id"], "sequence": 1, "previous_event_sha256": early_start["event_sha256"]})
    # A capture cannot predate the attempt or the preceding page acknowledgement.
    late_base = common()
    late_start = event(late_base, occurred_at=AS_OF)
    append(late_start)
    rejected(event(late_base, previous=late_start, kind="page_saved", occurred_at=AS_OF, capture_sha256=pages[0]["capture_sha256"]))
    late_base = common()
    late_start = event(late_base)
    append(late_start)
    late_page = event(late_base, previous=late_start, kind="page_saved", occurred_at=AS_OF, capture_sha256=pages[0]["capture_sha256"])
    append(late_page)
    rejected(event(late_base, previous=late_page, kind="page_saved", occurred_at=AS_OF, capture_sha256=pages[1]["capture_sha256"]))
    # Enforce observed byte budgets as well as the attempt's declared page cap.
    for aggregate in (False, True):
        budget = common()
        page_sizes = [page["raw_size_bytes"] for page in pages]
        budget["limits"]["max_page_bytes"] = max(page_sizes) if aggregate else min(page_sizes)-1
        budget["limits"]["max_total_bytes"] = sum(page_sizes)-1 if aggregate else max(page_sizes)
        budget_start = event(budget)
        append(budget_start)
        budget_page = event(budget, previous=budget_start, kind="page_saved", capture_sha256=pages[0]["capture_sha256"])
        if aggregate:
            append(budget_page)
            rejected(event(budget, previous=budget_page, kind="page_saved", capture_sha256=pages[1]["capture_sha256"]))
        else:
            rejected(budget_page)
    CHECKS.append("G3 capture index/receipt/identity and exact predecessor checks; ordered snapshot membership, source hash/version/time and completion checks; diagnostic failed snapshots allowed; page cap and terminal finality")


def verify_concurrency() -> None:
    # Competing exact retries overlap while the winner retains its transaction lock.
    for conflict in (False, True):
        base = common()
        start = event(base)
        append(start)
        first = event(base, previous=start, kind="finished", status="failed", reason="request_failed")
        other = event(base, previous=start, kind="finished", status="failed", reason="read_failed") if conflict else first
        barrier = threading.Barrier(2)

        def worker(value: dict) -> str:
            barrier.wait(timeout=20)
            import subprocess
            result = subprocess.run(storage.BASE+["-d", DB],
                                    input=("BEGIN; SET LOCAL ROLE service_role; "+rpc(value)+"SELECT pg_sleep(0.3); COMMIT;").encode(),
                                    capture_output=True, timeout=30)
            if result.returncode:
                assert conflict and "Quote acquisition event rejected" in result.stderr.decode()
                return "conflict"
            return "inserted" if json.loads(result.stdout.decode().splitlines()[0])["inserted"] else "retry"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [first, other]))
        assert sorted(results) == (["conflict", "inserted"] if conflict else ["inserted", "retry"])
        assert sql("SELECT count(*) FROM quote_acquisition_events WHERE attempt_id="+literal(base["attempt_id"])+";") == "2"
        stored = json.loads(sql("SELECT document FROM quote_acquisition_events WHERE attempt_id="+literal(base["attempt_id"])+" AND sequence=1;"))
        assert stored in (unsigned(first), unsigned(other))
    CHECKS.append("G4 overlapping same-attempt terminal writes: exact retry inserts once; differing sequence payloads choose one winner and reject the other without partial changes")


def verify_permissions() -> None:
    table = "quote_acquisition_events"
    assert sql(f"SELECT relrowsecurity FROM pg_class WHERE oid='public.{table}'::regclass;") == "t"
    assert sql(f"SET ROLE service_role; SELECT count(*) FROM {table};") == sql(f"SELECT count(*) FROM {table};")
    for role in ("anon", "authenticated"):
        sql(f"SET ROLE {role}; SELECT * FROM {table};", error="permission denied")
        sql(f"SET ROLE {role}; "+rpc(event(common())), error="permission denied")
    for role in ("anon", "authenticated", "service_role"):
        for command in (f"INSERT INTO {table} DEFAULT VALUES", f"UPDATE {table} SET sequence=sequence", f"DELETE FROM {table}", f"TRUNCATE {table}"):
            sql(f"SET ROLE {role}; {command};", error="permission denied")
        sql(f"SET ROLE {role}; COPY {table} FROM STDIN;\n\\.\n", error="permission denied")
        for helper in ("reject_quote_storage_mutation()", "quote_storage_unique_json('{}')", "quote_storage_keys('{}',ARRAY[]::text[])", "quote_storage_time('null')", "quote_storage_identity('{}')"):
            sql(f"SET ROLE {role}; SELECT public.{helper};", error="permission denied")
    for command in (f"UPDATE {table} SET sequence=sequence", f"DELETE FROM {table}", f"TRUNCATE {table}"):
        sql(command+";", error="immutable")
    sql(f"GRANT SELECT ON {table} TO anon,authenticated;")
    for role in ("anon", "authenticated"):
        assert sql(f"SET ROLE {role}; SELECT count(*) FROM {table};") == "0"
    sql(f"REVOKE SELECT ON {table} FROM anon,authenticated;")
    assert sql("SELECT prosecdef AND 'search_path=pg_catalog, public'=ANY(proconfig) FROM pg_proc WHERE oid='public.append_quote_acquisition_event(text,text)'::regprocedure;") == "t"
    assert sql("SELECT count(*) FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a WHERE p.oid='public.append_quote_acquisition_event(text,text)'::regprocedure AND a.grantee=0;") == "0"
    CHECKS.append("G5 private RLS and exact service-role SELECT/RPC grants; anonymous/authenticated denial; no helper execution or direct writes; owner UPDATE/DELETE/TRUNCATE rejected")


def verify_rollback_reapply(migration: str, preserved: dict[str, str], grants: str) -> None:
    before = state()
    archive_before = storage.archive_state()
    sql("CREATE FUNCTION fail_attempt_insert() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'SENSITIVE_SENTINEL'; END $$; "
        "CREATE TRIGGER fail_attempt_insert AFTER INSERT ON quote_acquisition_events FOR EACH ROW EXECUTE FUNCTION fail_attempt_insert();")
    rejected(event(common()))
    sql("DROP TRIGGER fail_attempt_insert ON quote_acquisition_events; DROP FUNCTION fail_attempt_insert();")
    assert state() == before
    sql(migration)
    assert state() == before and storage.archive_state() == archive_before
    assert sql("SELECT jsonb_agg(jsonb_build_array(oid::regclass::text,relacl::text) ORDER BY oid::regclass::text) FROM pg_class WHERE relname IN ('quote_captures','quote_snapshots','quote_snapshot_pages','regime_calls','signals','call_rationale','historical_prices','validation_log','validation_evaluations');") == grants
    for table, content in preserved.items():
        assert sql(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM {table} t;") == content
    CHECKS.append("G6 post-insert injected failure rolls back; fresh and populated reapplication retain exact attempts/captures/snapshots; unrelated grants and original call/signal/rationale/price/validation/evaluation sentinels unchanged")


def verify_orchestration() -> None:
    from src.db import writer
    from src.research.quote_acquisition import acquire_quotes

    class Response:
        status = 200
        headers = {"content-type": "application/json"}

        def __init__(self, body: bytes):
            self.body = body
            self.closed = False

        async def iter_chunks(self):
            yield self.body[:10]
            yield self.body[10:]

        async def close(self):
            self.closed = True

    class Transport:
        def __init__(self, attempt: str, fail: bool):
            self.attempt = attempt
            self.fail = fail
            self.calls = 0
            self.responses: list[Response] = []

        async def open_page(self, url, *, params, timeout_seconds):
            assert url == "https://api.massive.com/v3/quotes/C:EUR-USD"
            assert timeout_seconds > 0 and params["apiKey"] == "SENSITIVE_SENTINEL"
            # The real runner must have durable start/progress before this request.
            kinds = json.loads(sql("SELECT json_agg(kind ORDER BY sequence) FROM quote_acquisition_events WHERE attempt_id="+literal(self.attempt)+";"))
            assert kinds == (["started"] if self.calls == 0 else ["started", "page_saved"])
            if self.calls:
                assert set(params) == {"cursor", "apiKey"} and params["cursor"] == "opaque-private-cursor"
            self.calls += 1
            if self.fail:
                raise OSError("SENSITIVE_SENTINEL")
            body = (b'{"status":"OK","results":[],"next_url":"https://api.massive.com/v3/quotes/C:EUR-USD?cursor=opaque-private-cursor"}'
                    if self.calls == 1 else b'{"status":"OK","results":[]}')
            response = Response(body)
            self.responses.append(response)
            return response

    for fail in (False, True):
        attempt = str(uuid.uuid4())
        transport = Transport(attempt, fail)
        with patch.object(writer, "_client", return_value=bridge_client()):
            terminal = asyncio.run(acquire_quotes(pair="EURUSD", day=date(2026, 5, 1), api_key="SENSITIVE_SENTINEL",
                                                 attempt_id=attempt, transport=transport, now=lambda: AS_OF, monotonic=lambda: 0.0))
        assert terminal["status"] == ("failed" if fail else "complete"), terminal
        assert terminal["reason"] == ("request_failed" if fail else "completed")
        assert terminal["sequence"] == (1 if fail else 3)
        assert transport.calls == (1 if fail else 2) and all(response.closed for response in transport.responses)
        stored = json.loads(sql("SELECT json_agg(document ORDER BY sequence) FROM quote_acquisition_events WHERE attempt_id="+literal(attempt)+";"))
        assert stored[-1] == unsigned(terminal)
        assert [item["kind"] for item in stored] == (["started", "finished"] if fail else ["started", "page_saved", "page_saved", "finished"])
        if not fail:
            snap = json.loads(sql("SELECT document FROM quote_snapshots WHERE snapshot_sha256="+literal(terminal["snapshot_sha256"])+";"))
            assert snap["reference"]["capture_sha256"] == [item["capture_sha256"] for item in stored if item["kind"] == "page_saved"]
            assert snap["reference"]["acquisition_complete"] is True and snap["reference"]["validation_eligible"] is False
        assert "SENSITIVE_SENTINEL" not in state() and "opaque-private-cursor" not in state()
    CHECKS.append("integration real acquire_quotes with injected two-page and zero-response transports -> actual central writers -> PostgreSQL; durable event-before-request order, snapshot membership and response cleanup; no real network")


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE historical_prices(pair text, close numeric); INSERT INTO historical_prices VALUES('EURUSD',1.11); "
            "CREATE TABLE validation_log(note text); INSERT INTO validation_log VALUES('unchanged validation'); "
            "CREATE TABLE validation_evaluations(note text); INSERT INTO validation_evaluations VALUES('unchanged evaluation');")
        tables = ("historical_prices", "validation_log", "validation_evaluations", "regime_calls", "signals", "call_rationale")
        preserved = {table: sql(f"SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM {table} t;") for table in tables}
        sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO anon,authenticated,service_role;")
        sql((ROOT / "supabase/migrations/20260927000008_quote_capture_storage.sql").read_text(encoding="utf-8"))
        grants = sql("SELECT jsonb_agg(jsonb_build_array(oid::regclass::text,relacl::text) ORDER BY oid::regclass::text) FROM pg_class WHERE relname IN ('quote_captures','quote_snapshots','quote_snapshot_pages','regime_calls','signals','call_rationale','historical_prices','validation_log','validation_evaluations');")
        migration = (ROOT / "supabase/migrations/20260927000009_quote_acquisition_events.sql").read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        print("RUN G1: Python writer bridge and zero-response failures", flush=True)
        base, pages, events, snapshot = verify_writer_and_progress()
        print("RUN G2: malformed envelopes and runtime provenance", flush=True)
        verify_schema()
        print("RUN G3: cross-event and snapshot lineage", flush=True)
        verify_lineage(base, pages, events, snapshot)
        print("RUN G4: competing transactions", flush=True)
        verify_concurrency()
        print("RUN G5: permissions and owner immutability", flush=True)
        verify_permissions()
        print("RUN G6: rollback, populated reapplication and sentinels", flush=True)
        print("RUN integration: actual orchestration and SQL persistence", flush=True)
        verify_orchestration()
        verify_rollback_reapply(migration, preserved, grants)
        for check in CHECKS:
            print("PASS:", check)
        print("REJECTIONS:", REJECTIONS)
        print("RUNTIME_MANIFEST: actual on-disk sources")
        print("POSTGRES:", sql("SHOW server_version;"))
        print("REPAIR_QUOTE_ACQUISITION_DB_VERIFIED")
    finally:
        assert DB.startswith("fxattempt_") and len(DB) == 42
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
