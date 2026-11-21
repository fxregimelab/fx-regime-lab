"""Verify six request boundaries in one disposable, socket-only PostgreSQL DB.

No work runs at import. The parent may override MIGRATION_SQL before main().
Fixtures are synthetic; this does not certify deployed PostgREST request timers.
"""

from __future__ import annotations

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
DB = "fxstoragetime_" + uuid.uuid4().hex
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
    "-v",
    "VERBOSITY=verbose",
]
MIGRATION_PATH = ROOT / "supabase/migrations/20260928000015_storage_request_timeouts.sql"
MIGRATION_SQL: str | None = None
SOURCES = {
    "append_validation_evaluation": "20260927000006_validation_price_evidence.sql",
    "append_regime_publication": "20260927000004_atomic_publication.sql",
    "append_price_observations": "20260927000007_price_observations.sql",
    "append_quote_capture": "20260927000008_quote_capture_storage.sql",
    "append_quote_snapshot": "20260927000008_quote_capture_storage.sql",
    "append_quote_acquisition_event": "20260927000009_quote_acquisition_events.sql",
}
TABLES = (
    "regime_calls",
    "signals",
    "call_rationale",
    "publication_evidence",
    "signal_projection_history",
    "validation_log",
    "validation_stats",
    "historical_prices",
    "price_observations",
    "quote_captures",
    "quote_snapshots",
    "quote_snapshot_pages",
    "quote_acquisition_events",
)
IMMUTABLE = (
    "regime_calls",
    "publication_evidence",
    "signal_projection_history",
    "validation_log",
    "price_observations",
    "quote_captures",
    "quote_snapshots",
    "quote_snapshot_pages",
    "quote_acquisition_events",
)
GUARD = """    -- The caller must arm the timer before the top-level request arrives.
    IF (SELECT setting::bigint FROM pg_settings WHERE name = 'statement_timeout')
       NOT BETWEEN 1 AND 30000 THEN
        RAISE EXCEPTION USING
            MESSAGE='Storage requires an inherited bounded statement timeout', ERRCODE='22023';
    END IF;
"""
CHECKS: list[str] = []
COUNTS: dict[str, int] = {}


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = subprocess.run(
        BASE + ["-d", database], input=statement.encode(), capture_output=True, timeout=45
    )
    diagnostic = result.stderr.decode()
    # Do not expose raw SQL, document bodies or private input from error CONTEXT.
    codes = re.findall(r"(?:ERROR|FATAL):\s+([A-Z0-9]{5}):", diagnostic)
    if error is None:
        assert result.returncode == 0, f"Unexpected database failure; SQLSTATE={codes}"
    else:
        assert result.returncode != 0 and error in codes, (
            f"Expected SQLSTATE={error}; received={codes}; exit={result.returncode}"
        )
    return result.stdout.decode().strip()


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def document(value: Any) -> str:
    return literal(json.dumps(value, allow_nan=False)) + "::jsonb"


def request(query: str, timeout: int = 30000, *, error: str | None = None) -> str:
    return sql(f"SET statement_timeout={timeout}; SET ROLE service_role; " + query, error=error)


def definitions(source: str) -> dict[str, str]:
    matches = re.findall(
        r"(CREATE OR REPLACE FUNCTION public\.(append_\w+)\([\s\S]*?\$\$;)", source
    )
    assert len(matches) == len({name for _, name in matches})
    return {name: definition for definition, name in matches}


def verify_source(migration: str) -> None:
    replacements = definitions(migration)
    assert set(replacements) == set(SOURCES), "Exactly six public replacements required"
    for name, replacement in replacements.items():
        original = definitions(
            (ROOT / "supabase/migrations" / SOURCES[name]).read_text(encoding="utf-8")
        )[name]
        assert replacement.count(GUARD) == 1, name
        assert "BEGIN\n" + GUARD in replacement, name
        assert replacement.count("\nSET lock_timeout = '10s'") == 1, name
        assert (
            replacement.replace(GUARD, "", 1).replace("\nSET lock_timeout = '10s'", "", 1)
            == original
        ), name
    residual = migration
    for replacement in replacements.values():
        residual = residual.replace(replacement, "", 1)
    assert re.sub(r"--[^\n]*", "", residual).split() == ["BEGIN;", "COMMIT;"]
    CHECKS.append("six exact source bodies preserved, including migration06 version dispatcher")


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
                "FROM pg_policy p),'constraints',(SELECT jsonb_agg(to_jsonb(c) ORDER BY oid) "
                "FROM pg_constraint c WHERE connamespace='public'::regnamespace))"
            )
        )
    )


def load_fixture(filename: str) -> Any:
    # These four files were inspected: imports/definitions only, work guarded by main.
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_"), ROOT / "scripts/repair" / filename
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Session:
    """Separate psql commands arm the timer before a top-level request is sent."""

    def __init__(self, label: str) -> None:
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


class Case:
    def __init__(self, name: str, query: str, table: str, kind: str) -> None:
        self.name, self.query, self.table, self.kind = name, query, table, kind


def insert_retry(case: Case, timeout: int = 30000) -> Any:
    receipt = json.loads(request(case.query, timeout))
    retained = state()
    retry = json.loads(request(case.query, timeout))
    if case.kind == "quote":
        assert receipt["inserted"] is True and retry == {**receipt, "inserted": False}
    elif case.kind == "price":
        assert receipt["inserted_count"] == 2 and receipt["existing_count"] == 0
        assert retry == {**receipt, "inserted_count": 0, "existing_count": 2}
    else:
        assert retry == receipt
    assert state() == retained, case.name
    COUNTS["insert_retry_pairs"] = COUNTS.get("insert_retry_pairs", 0) + 1
    return receipt


def validation(call_id: int, version: str, horizon: str = "t5") -> str:
    from src.validation.calculator import calculate_horizon

    close = 1.19 if horizon == "t5" else 1.21
    stats = calculate_horizon(1.2, close, "BULLISH", 0.7, "EURUSD")
    row: dict[str, Any] = {
        "call_id": call_id,
        "pair": "EURUSD",
        "call_date": "2026-05-01",
        "evaluation_version": version,
    }
    for target, key in {
        f"log_return_{horizon}_bps": "log_return_bps",
        f"correct_{horizon}": "correct",
        f"brier_score_{horizon}": "brier_score",
        f"actual_direction_{horizon}": "realized_direction",
        f"log_return_net_bps_{horizon}": "log_return_net_bps",
        f"correct_net_{horizon}": "correct_net",
        f"cost_bps_{horizon}": "cost_bps",
    }.items():
        row[target] = stats[key]
    if version == "publication-snapshot-v2":
        row["entry_price_evidence"] = {
            "kind": "publication_signal",
            "call_id": call_id,
            "pair": "EURUSD",
            "date": "2026-05-01",
            "price": 1.2,
            "source": "publication_evidence.signal_payload.spot",
        }
        row[f"price_evidence_{horizon}"] = {
            "kind": "historical_close",
            "pair": "EURUSD",
            "date": "2026-05-08" if horizon == "t5" else "2026-05-29",
            "price": close,
            "source": "historical_prices.close",
        }
    return "SELECT public.append_validation_evaluation(" + document(row) + ");"


def fixtures(
    sequence: int, helpers: tuple[Any, Any, Any, Any], *, revisions: bool = False
) -> list[Case]:
    publication, price, quote, acquisition = helpers
    cases = []
    for version in ("published-direction-v1", "publication-snapshot-v2"):
        call_id = int(
            request(
                publication.append(
                    *publication.publication(f"timeout-{sequence}-{version}", day="2026-05-01")
                )
            )
        )
        first = validation(call_id, version)
        if revisions:
            request(first)
        cases.append(
            Case(
                version,
                validation(call_id, version, "t20") if revisions else first,
                "validation_log",
                "validation",
            )
        )
    cases.append(
        Case(
            "publication",
            publication.append(
                *publication.publication(f"timeout-publication-{sequence}", day="2026-05-01")
            ),
            "regime_calls",
            "publication",
        )
    )
    rows = [
        price.sample(provider_metadata={"request_id": f"timeout-{sequence}-{i}"}) for i in range(2)
    ]
    cases.append(Case("price", price.append(rows), "price_observations", "price"))
    page = quote.capture(minute=sequence)
    cases.append(
        Case(
            "capture",
            quote.rpc_sql("capture", quote.canonical(quote.unsigned_capture(page))),
            "quote_captures",
            "quote",
        )
    )
    # Separate prerequisite capture: every snapshot request starts with retained lineage.
    prerequisite = quote.capture(minute=sequence + 100)
    request(quote.rpc_sql("capture", quote.canonical(quote.unsigned_capture(prerequisite))))
    snapshot = quote.envelope([prerequisite], client_version=f"timeout-{sequence}")
    cases.append(
        Case(
            "snapshot",
            quote.rpc_sql("snapshot", quote.canonical(snapshot)),
            "quote_snapshots",
            "quote",
        )
    )
    cases.append(
        Case(
            "acquisition",
            acquisition.rpc(acquisition.event(acquisition.common())),
            "quote_acquisition_events",
            "quote",
        )
    )
    return cases


def verify_refusals(cases: list[Case]) -> None:
    before = state()
    for case in cases:
        for timeout in (0, 30001):
            request(case.query, timeout, error="22023")
            assert state() == before, case.name
            COUNTS["unchanged_refusals"] = COUNTS.get("unchanged_refusals", 0) + 1


def verify_scope(cases: list[Case]) -> None:
    tables = sorted(
        {case.table for case in cases} | {"publication_evidence", "quote_snapshot_pages"}
    )
    sql(
        "CREATE FUNCTION check_timeout_scope() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF current_setting('lock_timeout') <> '10s' THEN "
        "RAISE EXCEPTION 'wrong local lock timeout'; END IF; RETURN NEW; END $$;"
        + "".join(
            f"CREATE TRIGGER timeout_scope BEFORE INSERT ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION check_timeout_scope();"
            for table in tables
        )
    )
    try:
        with Session("timeout-scope") as session:
            session.send("SET lock_timeout='77ms'; SET ROLE service_role; SELECT 'CONFIGURED';")
            assert session.read() == "CONFIGURED"
            for case in cases:
                session.send(case.query + " SHOW lock_timeout; SHOW statement_timeout;")
                json.loads(session.read())
                assert session.read() == "77ms" and session.read() == "30s"
                session.send(
                    "SET statement_timeout=0; DO $probe$ BEGIN "
                    + case.query.replace("SELECT public.", "PERFORM public.", 1)
                    + " RAISE EXCEPTION 'guard did not reject'; "
                    "EXCEPTION WHEN SQLSTATE '22023' THEN "
                    "IF current_setting('lock_timeout') <> '77ms' THEN "
                    "RAISE EXCEPTION 'lock setting leaked'; END IF; END $probe$; "
                    "SHOW statement_timeout; SET statement_timeout='30s'; SELECT 'RESTORED';"
                )
                assert session.read() == "0" and session.read() == "RESTORED"
                COUNTS["scope_paths"] = COUNTS.get("scope_paths", 0) + 2
    finally:
        sql(
            "".join(f"DROP TRIGGER timeout_scope ON {table};" for table in tables)
            + "DROP FUNCTION check_timeout_scope();"
        )
    CHECKS.append(
        "10s lock scope observed on writes; caller settings restored on success and refusal"
    )


def verify_cancellation(case: Case) -> None:
    # A sequence survives rollback. Blocking AFTER INSERT proves actual write execution.
    sql(
        "CREATE SEQUENCE timeout_write_attempt; "
        "CREATE FUNCTION witness_write_attempt() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN PERFORM nextval('timeout_write_attempt'); "
        "PERFORM pg_advisory_xact_lock(731311); RETURN NEW; END $$; "
        f"CREATE TRIGGER timeout_attempt AFTER INSERT ON {case.table} "
        "FOR EACH ROW EXECUTE FUNCTION witness_write_attempt();"
    )
    before = state()
    try:
        with Session("timeout-holder") as holder, Session("timeout-waiter") as waiter:
            holder.send(
                "BEGIN; DO $$ BEGIN PERFORM pg_advisory_xact_lock(731311); END $$; SELECT 'HELD';"
            )
            assert holder.read() == "HELD"
            # Keep the connection after cancellation to check caller scope restoration too.
            waiter.send(
                "\\set ON_ERROR_STOP off\nSET lock_timeout='77ms'; "
                "SET statement_timeout='3000ms'; SET ROLE service_role; SELECT 'ARMED';"
            )
            assert waiter.read() == "ARMED"
            start = time.monotonic()
            waiter.send(
                case.query
                + "\n\\echo SQLSTATE :SQLSTATE\nSHOW lock_timeout; SHOW statement_timeout;"
            )
            while True:
                blocked = sql(
                    "SELECT count(*) FROM pg_locks l JOIN pg_stat_activity a USING(pid) "
                    "WHERE a.datname=current_database() AND a.application_name='timeout-waiter' "
                    "AND NOT l.granted AND l.locktype='advisory' AND l.objid=731311"
                )
                if blocked == "1":
                    break
                assert time.monotonic() - start < 2.7, f"No observed blocked lock: {case.name}"
            assert waiter.read() == "SQLSTATE 57014", case.name
            assert waiter.read() == "77ms" and waiter.read() == "3s"
            assert time.monotonic() - start < 10
            holder.send("ROLLBACK; SELECT 'RELEASED';")
            assert holder.read() == "RELEASED"
        assert state() == before, f"Partial evidence after cancellation: {case.name}"
        assert sql("SELECT last_value,is_called FROM timeout_write_attempt") == "1|t"
    finally:
        sql(
            f"DROP TRIGGER timeout_attempt ON {case.table}; DROP FUNCTION witness_write_attempt(); "
            "DROP SEQUENCE timeout_write_attempt;"
        )
    insert_retry(case)
    COUNTS["observed_57014_write_rollbacks"] = COUNTS.get("observed_57014_write_rollbacks", 0) + 1
    print(
        f"PASS: {case.name}: observed lock, SQLSTATE57014, "
        "attempted write rolled back, retry succeeded",
        flush=True,
    )


def verify_semantics(helpers: tuple[Any, Any, Any, Any]) -> None:
    publication = helpers[0]
    original = publication.publication("timeout-identity-a", day="2026-05-01")
    first = int(request(publication.append(*original)))
    retained = state()
    changed = ({**original[0], "confidence": 0.8}, *original[1:])
    request(publication.append(*changed), error="P0001")
    assert state() == retained
    successor = ({**original[0], "model_version": "timeout-identity-b"}, *original[1:])
    second_query = publication.append(*successor, predecessor=first)
    second = int(request(second_query))
    assert second != first and int(request(second_query)) == second
    assert sql(
        f"SELECT supersedes_call_id FROM publication_evidence WHERE call_id={second}"
    ) == str(first)
    assert sql(f"SELECT confidence FROM regime_calls WHERE id={first}") == "0.7"
    before = state()
    request(publication.append(*successor), error="P0001")
    assert state() == before
    for version in ("published-direction-v1", "publication-snapshot-v2"):
        call_id = int(
            request(
                publication.append(
                    *publication.publication(f"timeout-semantic-{version}", day="2026-05-01")
                )
            )
        )
        first_row = json.loads(request(validation(call_id, version)))
        completed = json.loads(request(validation(call_id, version, "t20")))
        assert completed["log_return_t5_bps"] == first_row["log_return_t5_bps"]
        assert completed["log_return_t20_bps"] is not None
        assert completed["evaluation_version"] == version
        assert json.loads(request(validation(call_id, version))) == completed
        before = state()
        conflict = validation(call_id, version).replace('"correct_t5": false', '"correct_t5": true')
        assert conflict != validation(call_id, version)
        request(conflict, error="P0001")
        assert state() == before
        assert (
            sql(
                f"SELECT count(*),count(*) FILTER (WHERE is_superseded) "
                f"FROM validation_log WHERE call_id={call_id}"
            )
            == "2|1"
        )
    CHECKS.append(
        "both validation versions retain completed horizons and reject conflicts; "
        "publication identity/supersession retained"
    )


def verify_permissions(cases: list[Case]) -> None:
    before = state()
    probes = []
    keys = {
        "regime_calls": "id",
        "publication_evidence": "call_id",
        "signal_projection_history": "id",
        "validation_log": "id",
        "price_observations": "id",
        "quote_captures": "capture_sha256",
        "quote_snapshots": "snapshot_sha256",
        "quote_snapshot_pages": "ordinal",
        "quote_acquisition_events": "event_sha256",
    }
    for role in ("anon", "authenticated", "service_role"):
        for table in IMMUTABLE:
            for action in (
                f"INSERT INTO {table} DEFAULT VALUES",
                f"UPDATE {table} SET {keys[table]}={keys[table]}",
                f"DELETE FROM {table}",
                f"TRUNCATE {table}",
            ):
                probes.append(
                    f"SET ROLE {role}; DO $$ BEGIN {action}; "
                    "RAISE EXCEPTION 'unexpected permission'; "
                    "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$; RESET ROLE;"
                )
        if role != "service_role":
            for case in cases:
                probes.append(
                    f"SET ROLE {role}; DO $$ BEGIN "
                    + case.query.replace("SELECT public.", "PERFORM public.", 1)
                    + " RAISE EXCEPTION 'unexpected execute'; "
                    "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$; RESET ROLE;"
                )
        probes.append(
            f"SET ROLE {role}; DO $$ BEGIN "
            "PERFORM public.append_validation_evaluation_v1('{}'::jsonb); "
            "RAISE EXCEPTION 'helper exposed'; "
            "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$; RESET ROLE;"
        )
    for table in IMMUTABLE:
        for action in (f"DELETE FROM {table}", f"UPDATE {table} SET {keys[table]}={keys[table]}"):
            probes.append(
                f"DO $$ BEGIN {action}; RAISE EXCEPTION 'missing immutable guard'; "
                "EXCEPTION WHEN raise_exception THEN IF SQLERRM NOT ILIKE '%immutable%' "
                "OR SQLERRM='missing immutable guard' THEN RAISE; END IF; END $$;"
            )
    sql("SET statement_timeout='30s'; " + "\n".join(probes))
    assert state() == before
    assert (
        sql(
            "SELECT count(*) FROM pg_proc p,aclexplode(p.proacl) a "
            "WHERE p.pronamespace='public'::regnamespace AND a.grantee=0 AND p.proname IN ("
            + ",".join(map(literal, SOURCES))
            + ")"
        )
        == "0"
    )
    COUNTS["permission_immutability_probes"] = len(probes)
    CHECKS.append(
        "application roles cannot mutate immutable evidence; "
        "anon/auth cannot invoke RPCs; v1 helper private"
    )


def setup() -> None:
    assert (
        sql(
            "SELECT count(*) FROM pg_roles "
            "WHERE rolname IN ('anon','authenticated','service_role')",
            database="postgres",
        )
        == "3"
    )
    # Do not create or alter shared roles: remove the fixture's historical role bootstrap.
    fixture = (ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8")
    sql(fixture[fixture.index("CREATE TABLE public.regime_calls") :])
    fixture = (ROOT / "scripts/repair/validation-db-fixture.sql").read_text(encoding="utf-8")
    sql(
        fixture[
            fixture.index("CREATE TABLE public.validation_log") : fixture.index(
                "INSERT INTO public.regime_calls"
            )
        ]
    )
    sql(
        "CREATE TABLE historical_prices(pair text,date date,close float8,PRIMARY KEY(pair,date)); "
        "INSERT INTO historical_prices VALUES "
        "('EURUSD','2026-05-08',1.19),('EURUSD','2026-05-29',1.21);"
    )
    for filename in (
        "20260927000001_validation_evaluation_contract.sql",
        "20260505000002_validation_stats.sql",
        "20260526000000_v2_1_honest_metrics.sql",
        "20260927000002_validation_cohorts.sql",
        "20260927000003_published_validation_population.sql",
        "20260927000004_atomic_publication.sql",
        "20260927000006_validation_price_evidence.sql",
        "20260927000007_price_observations.sql",
        "20260927000008_quote_capture_storage.sql",
        "20260927000009_quote_acquisition_events.sql",
    ):
        sql((ROOT / "supabase/migrations" / filename).read_text(encoding="utf-8"))


def main() -> None:
    CHECKS.clear()
    COUNTS.clear()
    migration = (
        MIGRATION_PATH.read_text(encoding="utf-8") if MIGRATION_SQL is None else MIGRATION_SQL
    )
    verify_source(migration)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "pipeline"))
    helpers = tuple(
        load_fixture(name)
        for name in (
            "verify-publication-db.py",
            "verify-price-observation-db.py",
            "verify-quote-storage-db.py",
            "verify-quote-acquisition-db.py",
        )
    )
    assert len(helpers) == 4
    sql(f'CREATE DATABASE "{DB}"', database="postgres")
    try:
        setup()
        print("RUN: baseline valid calls with timeout0", flush=True)
        baseline = fixtures(210, helpers)
        for case in baseline:
            insert_retry(case, 0)
        originals, original_catalog = state(), catalog()
        sql(migration)
        sql(migration)
        assert state() == originals
        changed_catalog = catalog()
        for old, new in zip(
            original_catalog.pop("functions"), changed_catalog.pop("functions"), strict=True
        ):
            assert old[:4] == new[:4]
            if old[0].split("(")[0] in SOURCES:
                assert new[4] == [*old[4], "lock_timeout=10s"]
                assert new[5].replace(GUARD, "", 1) == old[5]
            else:
                assert old == new
        assert original_catalog == changed_catalog
        verify_refusals(baseline)
        fresh = fixtures(211, helpers)
        verify_refusals(fresh)
        for case in fresh:
            insert_retry(case)
        CHECKS.append(
            "six RPCs and both validation versions: timeout0 baseline succeeds; "
            "invalid0/30001 refuse fresh/retry unchanged;30s permits insert/retry"
        )
        print("RUN: observed scope and attempted-write cancellations", flush=True)
        verify_scope(fixtures(212, helpers))
        for case in fixtures(213, helpers, revisions=True):
            verify_cancellation(case)
        verify_semantics(helpers)
        verify_permissions(baseline)
        retained, retained_catalog = state(), catalog()
        sql(migration)
        assert state() == retained and catalog() == retained_catalog
        CHECKS.append(
            "populated reapply preserves rows, original functions, grants, RLS, "
            "triggers and constraints"
        )
        for check in CHECKS:
            print("PASS:", check)
        print("COUNTS:", json.dumps(COUNTS, sort_keys=True))
        print("POSTGRES:", sql("SHOW server_version"))
        print("STORAGE_REQUEST_TIMEOUTS_VERIFIED")
    finally:
        assert DB.startswith("fxstoragetime_") and len(DB) == 46
        sql(f'DROP DATABASE "{DB}" WITH (FORCE)', database="postgres")


if __name__ == "__main__":
    main()
