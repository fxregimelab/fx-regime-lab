"""Real PostgreSQL checks in one disposable database; parent owns runtime lifecycle."""

from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
SPEC = importlib.util.spec_from_file_location(
    "fpi_parse_harness", ROOT / "scripts/repair/verify-fpi-parse-db.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPER: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
ORIGINAL_SQL = HELPER.sql
DB = "fxfpiqual_" + uuid.uuid4().hex
Q = importlib.import_module("src.research.fpi_qualification")
WRITER = importlib.import_module("src.db.writer")
RECORD = importlib.import_module("src.research.fpi_parse_record")
MIGRATION_PATH = ROOT / "supabase/migrations/20260928000012_fpi_qualification_storage.sql"
CHECKS: list[str] = []
REJECTIONS = 0


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    return str(ORIGINAL_SQL("SET statement_timeout='30s'; " + statement,
                            database=database, error=error))


HELPER.sql = sql


def statement(command: Any = None, *, raw: str | None = None, identity: str | None = None) -> str:
    document = command.document_json if raw is None else raw
    key = HELPER.digest(document) if identity is None else identity
    return "SELECT public.append_fpi_qualification(" + ",".join(
        HELPER.literal(value) for value in (key, document)
    ) + ");"


def bridge() -> MagicMock:
    client = MagicMock()

    def rpc(method: str, parameters: dict[str, Any]) -> MagicMock:
        if method == "append_fpi_qualification":
            assert set(parameters) == {"p_command_id", "p_document_json"}
            query = statement(raw=parameters["p_document_json"],
                              identity=parameters["p_command_id"])
        else:
            query = HELPER.rpc_statement(method, parameters)

        def execute() -> MagicMock:
            return MagicMock(data=json.loads(sql(
                "SET TIME ZONE 'Asia/Kolkata'; SET DateStyle='SQL, DMY'; SET ROLE service_role; "
                + query
            )))

        return MagicMock(execute=execute)

    client.rpc.side_effect = rpc
    return client


def command(scope: str, target: str, action: str = "ACCEPT", **kwargs: Any) -> Any:
    return Q.FpiQualificationCommand(scope, target, action, "ADMIN_REVIEW", "a" * 64, **kwargs)


def append(value: Any) -> dict[str, Any]:
    with patch.object(WRITER, "_client", return_value=bridge()):
        result: dict[str, Any] = WRITER.append_fpi_qualification(value)
    return result


def state() -> str:
    return sql("SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY event_ordinal)::text,'[]') "
               "FROM fpi_qualification_events e")


def reject(value: Any = None, *, raw: str | None = None, identity: str | None = None) -> None:
    global REJECTIONS
    before = state()
    sql("SET ROLE service_role; " + statement(value, raw=raw, identity=identity),
        error="FPI qualification rejected")
    assert state() == before
    REJECTIONS += 1


class Session:
    """A bounded interactive psql connection with observable transaction barriers."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.process = subprocess.Popen(
            HELPER.BASE + ["-d", DB], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.output: queue.Queue[bytes] = queue.Queue()

        def reader() -> None:
            assert self.process.stdout is not None
            for line in iter(self.process.stdout.readline, b""):
                if line.strip():
                    self.output.put(line.strip())

        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()
        self.send("SET statement_timeout='30s'; SET application_name="
                  + HELPER.literal(label) + "; SELECT 'READY';")
        assert self.read() == "READY"

    def send(self, query: str) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write((query + "\n").encode())
        self.process.stdin.flush()

    def read(self) -> str:
        return self.output.get(timeout=20).decode()

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=10)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()
        self.thread.join(timeout=10)

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def blocked(session: Session, key: int = 946027, subkey: int = 1) -> None:
    deadline = time.monotonic() + 9
    query = (
        "SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
        "WHERE l.locktype='advisory' AND NOT l.granted AND l.classid=" + str(key)
        + " AND l.objid=" + str(subkey) + " AND a.datname=current_database() "
        "AND a.application_name=" + HELPER.literal(session.label)
    )
    while time.monotonic() < deadline:
        if sql(query) == "1":
            return
        assert session.process.poll() is None, "Expected a live blocked database writer"
    raise AssertionError("No observed advisory lock barrier")


def members() -> list[dict[str, Any]]:
    return list(json.loads(sql(
        "SELECT json_agg(json_build_object('membership_id',m.membership_id,"
        "'value_sha256',m.value_sha256,'parser_sha256',p.parser_sha256,"
        "'reporting_date',to_char(m.reporting_date,'YYYY-MM-DD')) ORDER BY m.membership_id) "
        "FROM fpi_parsed_memberships m JOIN fpi_parse_results p USING(parse_id)"
    )))


def basis(day: str) -> tuple[str, ...]:
    return tuple(m["membership_id"] for m in members() if m["reporting_date"] == day)


def fixture(parser: Any, sequence: int, *, store: bool = True) -> Any:
    parsed, sources = HELPER.synthetic_parse(parser.artifact_sha256, sequence=sequence)
    with patch.object(WRITER, "_client", return_value=bridge()):
        WRITER.archive_fpi_capture(parsed.capture)
        if store:
            WRITER.archive_fpi_parse_result(parsed, source_evidence_documents=sources)
    return RECORD.build_fpi_parse_record(parsed, source_evidence_documents=sources)


def head(scope: str, target: str) -> str | None:
    result = sql("SELECT event_id FROM fpi_qualification_events WHERE scope="
                 + HELPER.literal(scope) + " AND target=" + HELPER.literal(target)
                 + " ORDER BY event_ordinal DESC LIMIT 1")
    return result or None


def resolution(member: dict[str, Any]) -> Any:
    day = member["reporting_date"]
    return command("date", day, "RESOLVE", chosen_membership_id=member["membership_id"],
                   basis_membership_ids=basis(day), expected_prior_event_id=head("date", day))


def view() -> Any:
    from datetime import date

    rows = members()
    universe = tuple(Q.FpiQualificationMember(
        row["membership_id"], row["value_sha256"], row["parser_sha256"],
        date.fromisoformat(row["reporting_date"]),
    ) for row in rows)
    targets = {(scope, row[field]) for row in rows for scope, field in (
        ("membership", "membership_id"), ("value", "value_sha256"),
        ("parser", "parser_sha256"), ("date", "reporting_date"),
    )}
    events = {event.event_id: event for event in (
        Q.decode_fpi_qualification_event(row["event_document_json"])
        for row in json.loads(state())
    )}
    heads = tuple(Q.FpiQualificationHead(scope, target, head(scope, target))
                  for scope, target in targets)
    selected = {item.event_id for item in heads if item.event_id is not None}
    for identity in tuple(selected):
        witness = events[identity].witness
        if witness is not None:
            selected.update(item.event_id for item in witness.heads if item.event_id is not None)
    return Q.FpiQualificationView(universe, heads, tuple(events[key] for key in selected))


def verify_strict(member: dict[str, Any]) -> None:
    valid = command("membership", member["membership_id"])
    good = json.loads(valid.document_json)
    malformed: list[str] = []
    wrong_values: tuple[Any, ...] = (None, True, 12, {}, [])
    patch_value: dict[str, Any]
    for key in good:
        missing = copy.deepcopy(good)
        del missing[key]
        malformed.append(HELPER.canonical(missing))
        for wrong in wrong_values:
            changed = {**good, key: wrong}
            if changed != good:
                malformed.append(HELPER.canonical(changed))
    for key in ("recorded_at", "event_ordinal", "unknown"):
        malformed.append(HELPER.canonical({**good, key: "SENSITIVE_SENTINEL"}))
    for patch_value in (
        {"scope": "MEMBERSHIP"}, {"target": "A" * 64}, {"action": "RESOLVE"},
        {"reason_code": "lowercase"}, {"reason_code": "A" * 65},
        {"evidence_sha256": ""}, {"expected_prior_event_id": ""},
        {"chosen_membership_id": "0" * 64}, {"basis_membership_ids": ["0" * 64]},
    ):
        malformed.append(HELPER.canonical({**good, **patch_value}))
    malformed += [" " + valid.document_json, valid.document_json + "\n",
                  valid.document_json[:-1] + ',"scope":"membership"}',
                  "[" * 40 + "0" + "]" * 40, " " * 300001,
                  valid.document_json.replace("ADMIN_REVIEW", "SENSITIVE_SENTINEL\\u0000")]
    for raw in malformed:
        reject(raw=raw)
    reject(valid, identity="0" * 64)
    for scope, target in (("membership", "0" * 64), ("value", "0" * 64),
                          ("parser", "0" * 64)):
        reject(command(scope, target))
    resolved = json.loads(resolution(member).document_json)
    for patch_value in (
        {"target": "2026-02-30"}, {"target": "0000-01-01"}, {"target": "2026-1-1"},
        {"action": "ACCEPT"}, {"chosen_membership_id": None}, {"basis_membership_ids": []},
        {"basis_membership_ids": [member["membership_id"]] * 2},
        {"basis_membership_ids": ["0" * 64] * 4097},
    ):
        reject(raw=HELPER.canonical({**resolved, **patch_value}))
    for isolation in ("REPEATABLE READ", "SERIALIZABLE"):
        sql("BEGIN ISOLATION LEVEL " + isolation + "; " + statement(valid),
            error="FPI qualification rejected")
    CHECKS.append("strict malformed/type/key/date/hash/canonical matrix and isolation rejection")


def verify_order(member: dict[str, Any], other: dict[str, Any]) -> None:
    first_command = command("membership", member["membership_id"])
    first = append(first_command)
    assert first["inserted"]
    assert append(first_command) == {**first, "inserted": False}
    reject(command("membership", member["membership_id"], "WITHDRAW"))
    reject(command("membership", other["membership_id"],
                   expected_prior_event_id=first["event_id"]))
    reject(command("membership", other["membership_id"], expected_prior_event_id="f" * 64))
    # A transaction keeps the global qualification lock after its RPC has returned.
    other_command = command("membership", other["membership_id"])
    with Session("qual-holder") as holder, Session("qual-waiter") as waiter:
        holder.send("BEGIN; SET LOCAL ROLE service_role; " + statement(other_command))
        receipt = json.loads(holder.read())
        successor = command("membership", other["membership_id"], "WITHDRAW",
                            expected_prior_event_id=receipt["event_id"])
        waiter.send("SET ROLE service_role; " + statement(successor))
        blocked(waiter)
        assert head("membership", other["membership_id"]) is None
        holder.send("COMMIT; SELECT 'COMMITTED';")
        assert holder.read() == "COMMITTED"
        new = json.loads(waiter.read())
        assert new["event_ordinal"] > receipt["event_ordinal"]
    # Exact retries wait behind the same lock and return the retained document.
    with Session("retry-holder") as holder, Session("retry-waiter") as waiter:
        holder.send("BEGIN; SELECT pg_advisory_xact_lock(946027,1); SELECT 'HELD';")
        assert holder.read() == "HELD"
        waiter.send("SET ROLE service_role; " + statement(first_command))
        blocked(waiter)
        holder.send("COMMIT; SELECT 'RELEASED';")
        assert holder.read() == "RELEASED"
        assert json.loads(waiter.read()) == {**first, "inserted": False}
    # A different scope must block, and rollback permits a successor of the old head.
    with Session("rollback-holder") as holder, Session("other-scope") as waiter:
        doomed = command("membership", member["membership_id"], "QUARANTINE",
                         expected_prior_event_id=first["event_id"])
        holder.send("BEGIN; SET LOCAL ROLE service_role; " + statement(doomed))
        lost = json.loads(holder.read())
        waiter.send("SET ROLE service_role; "
                    + statement(command("parser", member["parser_sha256"])))
        blocked(waiter)
        holder.send("ROLLBACK; SELECT 'ROLLED_BACK';")
        assert holder.read() == "ROLLED_BACK"
        parser = json.loads(waiter.read())
        assert parser["event_ordinal"] > lost["event_ordinal"]
        assert lost["event_id"] not in state()
    assert append(first_command) == {**first, "inserted": False}
    for action in ("WITHDRAW", "QUARANTINE"):
        value = command("membership", member["membership_id"], action,
                        expected_prior_event_id=first["event_id"])
        if action == "WITHDRAW":
            winner = append(value)
        else:
            reject(value)
    append(command("membership", member["membership_id"],
                   expected_prior_event_id=winner["event_id"]))
    CHECKS.append("observed lock barriers: cross-scope serialization, fresh post-lock head, "
                  "exact retry, rollback and unused ordinal, stale/root/foreign predecessors")


def verify_clocks(member: dict[str, Any]) -> None:
    for times in (("2026-02-01 12:00:00+00",) * 3,
                  ("2026-02-03 12:00:00.000001+00", "2026-02-02 12:00:00.12+00",
                   "2026-02-01 12:00:00+00")):
        events = []
        for index, clock in enumerate(times):
            sql("CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() RETURNS timestamptz "
                "LANGUAGE sql VOLATILE SET search_path=pg_catalog,public AS $$ SELECT "
                + HELPER.literal(clock) + "::timestamptz $$;")
            if index == 1:
                value = resolution(member)
            else:
                value = command("membership", member["membership_id"],
                                "ACCEPT" if index == 0 else "WITHDRAW",
                                expected_prior_event_id=head("membership", member["membership_id"]))
            event = Q.decode_fpi_qualification_event(append(value)["event_document_json"])
            events.append(event)
            if index == 1:
                old = view()
                assert Q.date_resolution(old, member_date(member))[0] == "RESOLVED"
        assert events[0].event_ordinal < events[1].event_ordinal < events[2].event_ordinal
        assert Q.date_resolution(old, member_date(member))[0] == "RESOLVED"
        assert Q.date_resolution(view(), member_date(member))[0] == "TARGET_UNQUALIFIED"
        assert events[1].witness.heads[0].event_id == events[0].event_id
    sql("CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() RETURNS timestamptz "
        "LANGUAGE sql VOLATILE SET search_path=pg_catalog,public AS $$ "
        "SELECT clock_timestamp() $$;")
    append(command("membership", member["membership_id"],
                   expected_prior_event_id=head("membership", member["membership_id"])))
    CHECKS.append("actual tied/backward clock ACCEPT-RESOLVE-WITHDRAW decodes and Python views "
                  "preserve historical witness while current state withdraws")


def member_date(member: dict[str, Any]) -> Any:
    from datetime import date

    return date.fromisoformat(member["reporting_date"])


def verify_resolution(member: dict[str, Any], parser: Any) -> None:
    for scope, field in (("value", "value_sha256"), ("parser", "parser_sha256")):
        target = member[field]
        append(command(scope, target, "QUARANTINE", expected_prior_event_id=head(scope, target)))
        reject(resolution(member))
        append(command(scope, target, expected_prior_event_id=head(scope, target)))
    append(resolution(member))
    pending = fixture(parser, 100, store=False)
    stale = resolution(member)
    # Parse commits while resolution waits for the qualification lock: the fresh
    # snapshot must include this newly committed, unqualified alternate candidate.
    with Session("before-holder") as holder, Session("before-resolution") as waiter:
        holder.send("BEGIN; SELECT pg_advisory_xact_lock(946027,1); SELECT 'HELD';")
        assert holder.read() == "HELD"
        waiter.send("SET ROLE service_role; " + statement(stale))
        blocked(waiter)
        sql("SET ROLE service_role; " + HELPER.parse_statement(json.loads(pending.document_json)))
        holder.send("COMMIT; SELECT 'RELEASED';")
        assert holder.read() == "RELEASED"
        assert waiter.process.wait(timeout=20) != 0
        assert waiter.process.stderr is not None
        assert b"FPI qualification rejected" in waiter.process.stderr.read()
    old_resolution = view()
    assert Q.date_resolution(old_resolution, member_date(member))[0] == "STALE_RESOLUTION"
    reject(stale)
    complete = resolution(member)
    assert len(complete.basis_membership_ids) >= 2
    after = fixture(parser, 101, store=False)
    # A scratch-only INSERT trigger blocks after the resolution SELECT has
    # completed. Its advisory wait is observed before committing another parse.
    sql("CREATE FUNCTION pause_resolution_insert() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF NEW.scope='date' THEN PERFORM pg_advisory_xact_lock(946027,2); "
        "END IF; RETURN NEW; END $$; CREATE TRIGGER pause_resolution_insert "
        "BEFORE INSERT ON fpi_qualification_events FOR EACH ROW "
        "EXECUTE FUNCTION pause_resolution_insert();")
    try:
        with Session("after-holder") as holder, Session("after-resolution") as waiter:
            holder.send("BEGIN; SELECT pg_advisory_xact_lock(946027,2); SELECT 'HELD';")
            assert holder.read() == "HELD"
            waiter.send("SET ROLE service_role; " + statement(complete))
            blocked(waiter, subkey=2)
            sql("SET ROLE service_role; " + HELPER.parse_statement(json.loads(after.document_json)))
            holder.send("COMMIT; SELECT 'RELEASED';")
            assert holder.read() == "RELEASED"
            receipt = json.loads(waiter.read())
            event = Q.decode_fpi_qualification_event(receipt["event_document_json"])
            assert event.command == complete
            assert event.command.basis_membership_ids != basis(member["reporting_date"])
            assert Q.date_resolution(view(), member_date(member))[0] == "STALE_RESOLUTION"
            assert append(complete) == {**receipt, "inserted": False}
    finally:
        sql("DROP TRIGGER pause_resolution_insert ON fpi_qualification_events; "
            "DROP FUNCTION pause_resolution_insert();")
    append(resolution(member))
    CHECKS.append("value/parser blocks, full unqualified alternate-parser basis, observed "
                  "pre-snapshot and post-snapshot parse commits, stable stale witness and retry")


def verify_permissions_and_failure(member: dict[str, Any]) -> None:
    table = "public.fpi_qualification_events"
    assert sql("SELECT relrowsecurity FROM pg_class WHERE oid='" + table + "'::regclass") == "t"
    for role in ("anon", "authenticated", "service_role"):
        for action in ("INSERT INTO " + table + " DEFAULT VALUES", "DELETE FROM " + table,
                       "UPDATE " + table + " SET target=target", "TRUNCATE " + table):
            sql("SET ROLE " + role + "; " + action, error="permission denied")
        for operation in ("nextval('public.fpi_qualification_ordinal')",
                          "setval('public.fpi_qualification_ordinal',1)",
                          "public.fpi_qualification_clock()"):
            sql("SET ROLE " + role + "; SELECT " + operation, error="permission denied")
        if role != "service_role":
            sql("SET ROLE " + role + "; SELECT * FROM " + table, error="permission denied")
            sql("SET ROLE " + role + "; " + statement(resolution(member)),
                error="permission denied")
    for action in ("DELETE FROM " + table, "UPDATE " + table + " SET target=target",
                   "TRUNCATE " + table + " CASCADE"):
        sql(action, error="immutable")
    sql("GRANT SELECT ON " + table + " TO anon,authenticated")
    for role in ("anon", "authenticated"):
        assert sql("SET ROLE " + role + "; SELECT count(*) FROM " + table) == "0"
    sql("REVOKE SELECT ON " + table + " FROM anon,authenticated")
    assert sql("SELECT count(*) FROM pg_proc WHERE proname='append_fpi_qualification' "
               "AND prosecdef AND provolatile='v' "
               "AND 'search_path=pg_catalog, public'=ANY(proconfig)") == "1"
    assert sql("SELECT count(*) FROM pg_proc p,aclexplode(p.proacl) a "
               "WHERE p.proname IN ('append_fpi_qualification','fpi_qualification_clock') "
               "AND a.grantee=0") == "0"
    sql("CREATE FUNCTION fail_qualification_insert() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'SENSITIVE_SENTINEL'; END $$; CREATE TRIGGER fail_insert "
        "AFTER INSERT ON fpi_qualification_events FOR EACH ROW "
        "EXECUTE FUNCTION fail_qualification_insert();")
    next_command = command("membership", member["membership_id"], "WITHDRAW",
                           expected_prior_event_id=head("membership", member["membership_id"]))
    try:
        reject(next_command)
    finally:
        sql("DROP TRIGGER fail_insert ON fpi_qualification_events; "
            "DROP FUNCTION fail_qualification_insert();")
    assert append(next_command)["inserted"]
    CHECKS.append("application/anonymous writes, reads, sequence/helper access, owner mutation "
                  "and truncate refuse; inserted-event failure rolls back with private error")


def verify_concurrent_inserts(parser: Any) -> None:
    fixture(parser, 200)
    fresh = next(row for row in members() if head("membership", row["membership_id"]) is None)
    initial = command("membership", fresh["membership_id"])
    with Session("insert-holder") as holder, Session("identical-insert") as waiter:
        holder.send("BEGIN; SET LOCAL ROLE service_role; " + statement(initial))
        first = json.loads(holder.read())
        waiter.send("SET ROLE service_role; " + statement(initial))
        blocked(waiter)
        holder.send("COMMIT; SELECT 'COMMITTED';")
        assert holder.read() == "COMMITTED"
        assert json.loads(waiter.read()) == {**first, "inserted": False}
    for predecessor in (None, first["event_id"]):
        if predecessor is None:
            fresh = next(row for row in members()
                         if head("membership", row["membership_id"]) is None)
        else:
            fresh = next(row for row in members() if row["membership_id"] == initial.target)
        winner_command = command("membership", fresh["membership_id"], "WITHDRAW",
                                 expected_prior_event_id=predecessor)
        loser = command("membership", fresh["membership_id"], "QUARANTINE",
                        expected_prior_event_id=predecessor)
        with Session("conflict-holder") as holder, Session("conflict-waiter") as waiter:
            holder.send("BEGIN; SET LOCAL ROLE service_role; " + statement(winner_command))
            winner = json.loads(holder.read())
            waiter.send("SET ROLE service_role; " + statement(loser))
            blocked(waiter)
            holder.send("COMMIT; SELECT 'COMMITTED';")
            assert holder.read() == "COMMITTED"
            assert waiter.process.wait(timeout=20) != 0
            assert waiter.process.stderr is not None
            assert b"FPI qualification rejected" in waiter.process.stderr.read()
            assert head("membership", fresh["membership_id"]) == winner["event_id"]
    CHECKS.append("observed concurrent initial identical retry, distinct null-root conflict "
                  "and competing successors leave exactly one retained winner")


def verify_timeout(member: dict[str, Any]) -> None:
    value = command("membership", member["membership_id"], "QUARANTINE",
                    expected_prior_event_id=head("membership", member["membership_id"]))
    before = state()
    for timeout in ("0", "30001"):
        sql("SET statement_timeout=" + HELPER.literal(timeout) + "; " + statement(value),
            error="FPI qualification rejected")
    sql("CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() RETURNS timestamptz "
        "LANGUAGE plpgsql VOLATILE SET search_path=pg_catalog,public AS $$ BEGIN "
        "PERFORM pg_sleep(0.2); RETURN clock_timestamp(); END $$;")
    try:
        sql("SET statement_timeout='50ms'; " + statement(value),
            error="canceling statement due to statement timeout")
        assert state() == before
        # Positive control proves the same scratch delay succeeds with enough time.
        assert append(value)["inserted"]
    finally:
        sql("CREATE OR REPLACE FUNCTION public.fpi_qualification_clock() RETURNS timestamptz "
            "LANGUAGE sql VOLATILE SET search_path=pg_catalog,public AS $$ "
            "SELECT clock_timestamp() $$;")
    assert sql("SHOW statement_timeout") == "30s"
    assert sql("SHOW lock_timeout") == "0"
    CHECKS.append("unbounded/overlong inherited timeouts reject; genuinely armed 50ms outer "
                  "timer cancels scratch delay and rolls back, 30s positive control passes")


def main() -> None:
    sql(f'CREATE DATABASE "{DB}"', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES "
            "TO anon,authenticated,service_role; ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON SEQUENCES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS "
            "TO anon,authenticated,service_role;")
        for filename in ("20260927000010_fpi_capture_storage.sql",
                         "20260927000011_fpi_parse_storage.sql"):
            sql((ROOT / "supabase/migrations" / filename).read_text(encoding="utf-8"))
        original = sql("SELECT jsonb_agg(jsonb_build_array(relname,relacl::text) "
                       "ORDER BY relname) FROM pg_class WHERE relnamespace='public'::regnamespace")
        migration = MIGRATION_PATH.read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        parser = RECORD.build_fpi_artifact(kind="PARSER", body=b"synthetic parser qualification A")
        alternative = RECORD.build_fpi_artifact(kind="PARSER", body=b"synthetic parser B")
        with patch.object(WRITER, "_client", return_value=bridge()):
            WRITER.archive_fpi_artifact(parser)
            WRITER.archive_fpi_artifact(alternative)
        fixture(parser, 1)
        member, other = members()
        print("RUN strict SQL boundaries", flush=True)
        verify_strict(member)
        print("RUN transaction order and observed locks", flush=True)
        verify_order(member, other)
        print("RUN tied/backward clock historical views", flush=True)
        verify_clocks(member)
        print("RUN snapshot visibility and resolution", flush=True)
        verify_resolution(member, alternative)
        print("RUN competing initial commands and successors", flush=True)
        verify_concurrent_inserts(parser)
        originals = HELPER.archive_state()
        print("RUN immutability permissions rollback and reapply", flush=True)
        verify_permissions_and_failure(member)
        verify_timeout(member)
        before = state()
        sequence = sql("SELECT last_value,is_called FROM fpi_qualification_ordinal")
        sql(migration)
        assert state() == before
        assert sql("SELECT last_value,is_called FROM fpi_qualification_ordinal") == sequence
        assert HELPER.archive_state() == originals
        assert sql("SELECT jsonb_agg(jsonb_build_array(relname,relacl::text) ORDER BY relname) "
                   "FROM pg_class WHERE relnamespace='public'::regnamespace "
                   "AND relname NOT LIKE 'fpi_qualification_%'") == original
        CHECKS.append("fresh/empty/populated migration reapplication preserves rows, sequence, "
                      "original evidence and unrelated ACLs")
        for check in CHECKS:
            print("PASS:", check)
        print(f"COUNTS: {len(CHECKS)} scenario groups; {REJECTIONS} unchanged-row rejections")
        print("FPI_QUALIFICATION_DB_VERIFIED")
    finally:
        assert DB.startswith("fxfpiqual_") and len(DB) == 42
        sql(f'DROP DATABASE "{DB}" WITH (FORCE)', database="postgres")


if __name__ == "__main__":
    main()
