"""Check request guards in a disposable database on the parent-owned local server.

Imports are limited to the inspected pure FPI codecs and parse fixture helper.
MIGRATION_SQL permits the parent's in-memory negative control without file edits.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
SPEC = importlib.util.spec_from_file_location(
    "fpi_parse_fixtures", ROOT / "scripts/repair/verify-fpi-parse-db.py"
)
assert SPEC is not None and SPEC.loader is not None
HELPER: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
RECORD = importlib.import_module("src.research.fpi_parse_record")
DB = "fxfpitime_" + uuid.uuid4().hex
BASE: list[str] = [*HELPER.BASE, "-v", "VERBOSITY=verbose"]
MIGRATION_PATH = ROOT / "supabase/migrations/20260928000013_fpi_storage_timeouts.sql"
MIGRATION_SQL: str | None = None
NAMES = ("append_fpi_capture", "append_fpi_artifact", "append_fpi_parse_result")
TABLES = (
    "fpi_captures",
    "fpi_implementation_artifacts",
    "fpi_parse_results",
    "fpi_parsed_memberships",
)
GUARD = """    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION 'FPI storage requires an inherited bounded statement timeout';
    END IF;
"""
CHECKS: list[str] = []


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = subprocess.run(
        BASE + ["-d", database], input=statement.encode(), capture_output=True, timeout=45
    )
    diagnostic = result.stderr.decode()
    if error is None:
        assert result.returncode == 0, diagnostic[:600]
    else:
        assert result.returncode != 0 and error in diagnostic, diagnostic[:600]
    return result.stdout.decode().strip()


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def definitions(source: str) -> dict[str, str]:
    matches = re.findall(
        r"(CREATE OR REPLACE FUNCTION public\.(append_fpi_\w+)\([\s\S]*?\$\$;)", source
    )
    assert len(matches) == len({name for _, name in matches})
    return {name: definition for definition, name in matches}


def verify_source(migration: str) -> None:
    originals: dict[str, str] = {}
    for filename in (
        "20260927000010_fpi_capture_storage.sql",
        "20260927000011_fpi_parse_storage.sql",
    ):
        originals.update(
            definitions((ROOT / "supabase/migrations" / filename).read_text(encoding="utf-8"))
        )
    replacements = definitions(migration)
    assert set(replacements) == set(originals) == set(NAMES)
    for name, replacement in replacements.items():
        assert replacement.count(GUARD) == 1, name
        assert replacement.count("\nSET lock_timeout = '10s'") == 1, name
        assert "BEGIN\n" + GUARD in replacement, name
        assert (
            replacement.replace(GUARD, "", 1).replace("\nSET lock_timeout = '10s'", "", 1)
            == originals[name]
        ), name
    residual = migration
    for replacement in replacements.values():
        residual = residual.replace(replacement, "", 1)
    residual = re.sub(r"--[^\n]*", "", residual)
    assert residual.split() == ["BEGIN;", "COMMIT;"]
    CHECKS.append("exact original definitions preserved after removing only guard and lock setting")


def state() -> str:
    parts = [
        f"'{table}',(SELECT coalesce(jsonb_agg(to_jsonb(r) "
        f"ORDER BY to_jsonb(r)::text),'[]') FROM {table} r)"
        for table in TABLES
    ]
    return sql("SELECT jsonb_build_object(" + ",".join(parts) + ")")


def catalog() -> dict[str, Any]:
    return dict(
        json.loads(
            sql(
                "SELECT jsonb_build_object('functions',(SELECT jsonb_agg("
                "jsonb_build_array(oid::regprocedure::text,proowner,proacl,"
                "prosecdef,proconfig,prosrc) "
                "ORDER BY oid) FROM pg_proc WHERE pronamespace='public'::regnamespace),"
                "'tables',(SELECT jsonb_agg(jsonb_build_array(relname,relacl,relrowsecurity) "
                "ORDER BY relname) FROM pg_class WHERE relnamespace='public'::regnamespace),"
                "'triggers',(SELECT jsonb_agg(to_jsonb(t) ORDER BY oid) FROM pg_trigger t "
                "WHERE NOT tgisinternal),'policies',(SELECT jsonb_agg(to_jsonb(p) ORDER BY oid) "
                "FROM pg_policy p))"
            )
        )
    )


def fixture(sequence: int) -> tuple[str, str, str]:
    artifact = RECORD.build_fpi_artifact(kind="PARSER", body=f"synthetic {sequence}".encode())
    parsed, sources = HELPER.synthetic_parse(artifact.artifact_sha256, sequence=sequence)
    record = RECORD.build_fpi_parse_record(parsed, source_evidence_documents=sources)
    return (
        "SELECT public.append_fpi_capture("
        + literal(parsed.capture.capture_sha256)
        + ","
        + literal(parsed.capture.document_json)
        + ");",
        "SELECT public.append_fpi_artifact("
        + literal(artifact.artifact_sha256)
        + ","
        + literal(artifact.document_json)
        + ");",
        "SELECT public.append_fpi_parse_result("
        + literal(record.parse_id)
        + ","
        + literal(record.record_sha256)
        + ","
        + literal(record.document_json)
        + ");",
    )


def request(query: str, timeout: int = 30000, *, error: str | None = None) -> str:
    return sql(f"SET statement_timeout={timeout}; SET ROLE service_role; " + query, error=error)


def insert_retry(query: str, timeout: int = 30000) -> None:
    receipt = json.loads(request(query, timeout))
    assert receipt["inserted"] is True
    assert json.loads(request(query, timeout)) == {**receipt, "inserted": False}


class Session:
    """Persistent connection: settings and each request cross separate psql commands."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.process = subprocess.Popen(
            BASE + ["-d", DB], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.output: queue.Queue[bytes] = queue.Queue()

        def read_output() -> None:
            assert self.process.stdout is not None
            for line in iter(self.process.stdout.readline, b""):
                if line.strip():
                    self.output.put(line.strip())

        self.reader = threading.Thread(target=read_output, daemon=True)
        self.reader.start()
        self.send(
            "SET statement_timeout='30s'; SET application_name="
            + literal(label)
            + "; SELECT 'READY';"
        )
        assert self.read() == "READY"

    def send(self, query: str) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write((query + "\n").encode())
        self.process.stdin.flush()

    def read(self) -> str:
        return self.output.get(timeout=15).decode()

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *args: Any) -> None:
        if self.process.poll() is None:
            self.send("ROLLBACK;\n\\q")
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process.wait(timeout=10)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                stream.close()
        self.reader.join(timeout=10)


def verify_cancellation(query: str, table: str) -> None:
    witness = table == "fpi_parsed_memberships"
    if witness:
        sql(
            "CREATE SEQUENCE timeout_result_attempt; "
            "CREATE FUNCTION witness_result_attempt() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN PERFORM nextval('timeout_result_attempt'); RETURN NEW; END $$; "
            "CREATE TRIGGER timeout_result_attempt AFTER INSERT ON fpi_parse_results "
            "FOR EACH ROW EXECUTE FUNCTION witness_result_attempt();"
        )
    before = state()
    with Session("timeout-holder") as holder, Session("timeout-waiter") as waiter:
        holder.send(f"BEGIN; LOCK TABLE public.{table} IN ACCESS EXCLUSIVE MODE; SELECT 'HELD';")
        assert holder.read() == "HELD"
        waiter.send("SET statement_timeout='3000ms'; SET ROLE service_role; SELECT 'ARMED';")
        assert waiter.read() == "ARMED"
        start = time.monotonic()
        waiter.send(query)
        # Observe an actual ungranted relation lock, rather than infer it from elapsed time.
        while True:
            observed = sql(
                "SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
                "WHERE a.datname=current_database() AND a.application_name='timeout-waiter' "
                "AND NOT l.granted AND l.relation=" + literal("public." + table) + "::regclass"
            )
            if observed == "1":
                break
            assert time.monotonic() - start < 2.5, "No observed blocked relation lock"
            assert waiter.process.poll() is None, "Waiter ended before lock observation"
        assert waiter.process.wait(timeout=12) != 0
        elapsed = time.monotonic() - start
        assert waiter.process.stderr is not None
        diagnostic = waiter.process.stderr.read().decode()
        assert (
            "57014" in diagnostic and "canceling statement due to statement timeout" in diagnostic
        )
        assert elapsed < 10, elapsed
        holder.send("ROLLBACK; SELECT 'RELEASED';")
        assert holder.read() == "RELEASED"
    assert state() == before
    if witness:
        # Sequence advancement survives rollback and proves the result INSERT was reached.
        assert sql("SELECT last_value,is_called FROM timeout_result_attempt") == "1|t"
        sql(
            "DROP TRIGGER timeout_result_attempt ON fpi_parse_results; "
            "DROP FUNCTION witness_result_attempt(); DROP SEQUENCE timeout_result_attempt;"
        )
    insert_retry(query)


def verify_scope(queries: tuple[str, str, str]) -> None:
    # The scratch triggers observe the actual configuration inside each RPC's write path.
    sql(
        "CREATE FUNCTION check_timeout_scope() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF current_setting('lock_timeout') <> '10s' THEN "
        "RAISE EXCEPTION 'wrong local lock timeout'; END IF; RETURN NEW; END $$;"
        + "".join(
            f"CREATE TRIGGER timeout_scope BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION check_timeout_scope();"
            for table in TABLES
        )
    )
    try:
        with Session("timeout-scope") as session:
            session.send("SET lock_timeout='77ms'; SELECT 'CONFIGURED';")
            assert session.read() == "CONFIGURED"
            for query in queries:
                session.send(
                    "SET ROLE service_role; "
                    + query
                    + " SHOW lock_timeout; SHOW statement_timeout;"
                )
                assert json.loads(session.read())["inserted"]
                assert session.read() == "77ms"
                assert session.read() == "30s"
                session.send(
                    "SET statement_timeout=0; DO $probe$ BEGIN "
                    + query.replace("SELECT public.", "PERFORM public.", 1)
                    + " RAISE EXCEPTION 'guard did not reject'; "
                    "EXCEPTION WHEN SQLSTATE '22023' THEN "
                    "IF current_setting('lock_timeout') <> '77ms' THEN "
                    "RAISE EXCEPTION 'lock setting leaked'; END IF; END $probe$; "
                    "SET statement_timeout='30s'; SELECT 'RESTORED';"
                )
                assert session.read() == "RESTORED"
    finally:
        sql(
            "".join(f"DROP TRIGGER timeout_scope ON {table};" for table in TABLES)
            + "DROP FUNCTION check_timeout_scope();"
        )
    CHECKS.append(
        "10s lock setting observed inside writes; caller setting restored on success/refusal"
    )


def verify_permissions(queries: tuple[str, str, str]) -> None:
    before = state()
    probes: list[str] = []
    for role in ("anon", "authenticated", "service_role"):
        for table in TABLES:
            actions = [
                f"INSERT INTO {table} DEFAULT VALUES",
                f"UPDATE {table} SET document_json=document_json",
                f"DELETE FROM {table}",
                f"TRUNCATE {table}",
            ]
            if role != "service_role":
                actions.append(f"SELECT * FROM {table}")
            for action in actions:
                probes.append(
                    f"SET ROLE {role}; DO $$ BEGIN {action}; "
                    "RAISE EXCEPTION 'unexpected permission'; "
                    "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$; RESET ROLE;"
                )
        if role != "service_role":
            for query in queries:
                probes.append(
                    f"SET ROLE {role}; DO $$ BEGIN "
                    + query.replace("SELECT public.", "PERFORM public.", 1)
                    + " RAISE EXCEPTION 'unexpected execute'; "
                    "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$; RESET ROLE;"
                )
    for table in TABLES:
        for action in (
            f"UPDATE {table} SET document_json=document_json",
            f"DELETE FROM {table}",
            f"TRUNCATE {table} CASCADE",
        ):
            probes.append(
                "DO $$ BEGIN " + action + "; RAISE EXCEPTION 'missing immutable guard'; "
                "EXCEPTION WHEN raise_exception THEN IF SQLERRM NOT LIKE '%immutable%' "
                "OR SQLERRM='missing immutable guard' THEN RAISE; END IF; END $$;"
            )
    sql("SET statement_timeout='30s'; " + "\n".join(probes))
    assert state() == before
    assert (
        sql(
            "SELECT count(*) FROM pg_proc p,aclexplode(p.proacl) a "
            "WHERE p.pronamespace='public'::regnamespace AND a.grantee=0 "
            "AND p.proname IN (" + ",".join(map(literal, NAMES)) + ")"
        )
        == "0"
    )
    CHECKS.append("three RPCs service-role only; private immutable tables reject direct writes")


def main() -> None:
    migration = (
        MIGRATION_PATH.read_text(encoding="utf-8") if MIGRATION_SQL is None else MIGRATION_SQL
    )
    verify_source(migration)
    sql(f'CREATE DATABASE "{DB}"', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        for filename in (
            "20260927000010_fpi_capture_storage.sql",
            "20260927000011_fpi_parse_storage.sql",
        ):
            sql((ROOT / "supabase/migrations" / filename).read_text(encoding="utf-8"))
        baseline = fixture(910)
        print("RUN: same valid baseline calls accept timeout zero", flush=True)
        for query in baseline:
            insert_retry(query, 0)
        CHECKS.append("all three original RPCs insert and retry with timeout0")
        originals, original_catalog = state(), catalog()
        sql(migration)
        sql(migration)
        assert state() == originals
        changed_catalog = catalog()
        for old, new in zip(
            original_catalog.pop("functions"), changed_catalog.pop("functions"), strict=True
        ):
            assert old[:4] == new[:4]
            if old[0].split("(")[0] in NAMES:
                assert new[4] == [*old[4], "lock_timeout=10s"]
                assert new[5].replace(GUARD, "", 1) == old[5]
            else:
                assert old == new
        assert original_catalog == changed_catalog
        for query in baseline:
            for timeout in (0, 30001):
                request(query, timeout, error="22023")
                assert state() == originals
            assert json.loads(request(query))["inserted"] is False
        print("RUN: guard refusals and valid insertion for every RPC", flush=True)
        for name, query in zip(NAMES, fixture(911), strict=True):
            before = state()
            for timeout in (0, 30001):
                request(query, timeout, error="22023")
                assert state() == before, name
            insert_retry(query)
        CHECKS.append(
            "each RPC refuses0/30001 without effects;30s inserts and exact retries succeed"
        )
        verify_scope(fixture(912))
        print("RUN: real lock waits canceled by PostgreSQL request timers", flush=True)
        for query, table in zip(fixture(913), (TABLES[0], TABLES[1], TABLES[3]), strict=True):
            verify_cancellation(query, table)
        CHECKS.append(
            "three observed blocked table locks canceled with57014; no partial writes; "
            "release then positive insertion/retry, including parse result/member rollback"
        )
        verify_permissions(baseline)
        retained, retained_catalog = state(), catalog()
        sql(migration)
        assert state() == retained and catalog() == retained_catalog
        CHECKS.append("populated reapply preserves evidence, function/table ACLs, RLS and triggers")
        for check in CHECKS:
            print("PASS:", check)
        print(f"COUNTS: {len(CHECKS)} scenario groups")
        print("FPI_STORAGE_TIMEOUTS_VERIFIED")
    finally:
        assert DB.startswith("fxfpitime_") and len(DB) == 42
        sql(f'DROP DATABASE "{DB}" WITH (FORCE)', database="postgres")


if __name__ == "__main__":
    main()
