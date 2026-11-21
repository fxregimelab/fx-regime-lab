"""Verify private observation archival in an isolated task-local PostgreSQL DB.

Uses only the existing Unix socket runtime. Does not read .env, start services,
contact providers, or connect to a production database.
"""
from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
import subprocess
import sys
import threading
import uuid
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
DB = "fxobservation_" + uuid.uuid4().hex
BASE = ["wsl", "-d", "Ubuntu-24.04", "--", "/usr/lib/postgresql/17/bin/psql",
        "-h", "/home/shreyash/.local/state/fxregime-repair/socket", "-p", "55437",
        "-X", "-qAt", "-v", "ON_ERROR_STOP=1"]
CHECKS: list[str] = []


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = subprocess.run(BASE + ["-d", database], input=statement, text=True,
                            capture_output=True, timeout=45, encoding="utf-8")
    if error is not None:
        assert result.returncode != 0 and error in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def literal(value: object) -> str:
    return "'" + json.dumps(value, allow_nan=False).replace("'", "''") + "'::jsonb"


def append(rows: object) -> str:
    return f"SELECT public.append_price_observations({literal(rows)});"


def sample(**changes: object) -> dict:
    return {"pair": "EURUSD", "date": "2026-05-01", "open": 1.12,
            "high": 1.15, "low": 1.10, "close": 1.13, "volume": 0,
            "provider": "polygon", "instrument": "C:EURUSD",
            "retrieved_at": "2026-05-02T01:00:00Z",
            "provider_timestamp": "2026-05-01T00:00:00Z",
            "session_timezone": None, "session_definition": None,
            "window_start": None, "window_end": None,
            "provider_metadata": {"request_id": "fixture-only", "adjusted": True,
                                  "raw_timestamp_ms": 1777593600000,
                                  "date_label_policy": "timestamp_utc_date"},
            "volume_source": None, "volume_instrument": None, **changes}


def snapshot(table: str) -> str:
    assert table in {"price_observations", "historical_prices", "regime_calls", "signals", "call_rationale"}
    return sql(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {table} t;")


def rejected(rows: object, message: str) -> None:
    before = snapshot("price_observations")
    sql(append(rows), error=message)
    assert snapshot("price_observations") == before


def verify_writer() -> None:
    from src.core.price_archive import prepare_price_observations
    from src.db import writer
    from src.types import SpotBar

    rows = [sample(provider="yahoo", instrument="EURUSD=X",
                   provider_metadata={"index_timezone": "Europe/London", "raw_index": "2026-05-01T00:00:00+01:00"}),
            sample(provider="alphavantage", instrument="EUR/USD",
                   provider_metadata={"last_refreshed": "2026-05-01", "from_symbol": "EUR", "to_symbol": "USD"})]
    bars = []
    for row in rows:
        typed = copy.deepcopy(row)
        typed["date"] = date.fromisoformat(typed["date"])
        for key in ["retrieved_at", "provider_timestamp", "window_start", "window_end"]:
            if typed[key] is not None:
                typed[key] = datetime.fromisoformat(typed[key])
        bars.append(SpotBar(**typed))
    prepared = prepare_price_observations({"EURUSD": bars}, as_of=date(2026, 5, 2),
                                          cutoff=datetime.fromisoformat("2026-05-03T00:00:00+00:00"))
    assert prepared.missing_metadata_count == prepared.invalid_count == prepared.future_count == 0
    assert prepared.unknown_session_count == 2
    rows = list(prepared.observations)
    original = copy.deepcopy(rows)

    def rpc(method: str, parameters: dict) -> MagicMock:
        assert method == "append_price_observations"
        assert parameters == {"p_observations": original}
        # Actual writer payload crosses actual JSON encoding and the PostgreSQL RPC.
        def execute() -> MagicMock:
            result = json.loads(sql("SET ROLE service_role; " + append(parameters["p_observations"])))
            return MagicMock(data=result)
        return MagicMock(execute=execute)

    client = MagicMock()
    client.rpc.side_effect = rpc
    with patch.object(writer, "_client", return_value=client):
        first = writer.archive_price_observations(rows)
        assert first["inserted_count"] == 2 and first["existing_count"] == 0
        client.rpc.assert_called_once()
        assert client.table.call_count == 0
        for row, observation_id in zip(original, first["observation_ids"], strict=True):
            assert json.loads(sql(f"SELECT observation FROM price_observations WHERE id={observation_id};")) == row
        client.reset_mock()
        retry = writer.archive_price_observations(rows)
        assert retry["observation_ids"] == first["observation_ids"]
        assert retry["inserted_count"] == 0 and retry["existing_count"] == 2
        client.rpc.assert_called_once()
    assert rows == original
    CHECKS.append("actual SpotBar preparation -> Python writer serialization -> service RPC -> exact metadata and retry IDs")


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        sql((ROOT / "supabase/migrations/20260927000004_atomic_publication.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE historical_prices(pair text, date date, close float8, PRIMARY KEY(pair,date)); "
            "INSERT INTO historical_prices VALUES ('EURUSD','2026-05-01',1.11);")
        preserved = {table: snapshot(table) for table in ["historical_prices", "regime_calls", "signals", "call_rationale"]}
        # Simulate broad defaults, which the archive migration must revoke explicitly.
        sql("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role; "
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon,authenticated,service_role;")
        migration = (ROOT / "supabase/migrations/20260927000007_price_observations.sql").read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        assert json.loads(sql(append([]))) == {"observation_ids": [], "inserted_count": 0, "existing_count": 0}
        first = json.loads(sql("SET ROLE service_role; " + append([sample(), sample()])))
        assert first["inserted_count"] == 1 and first["existing_count"] == 1
        assert first["observation_ids"][0] == first["observation_ids"][1]
        first_id = first["observation_ids"][0]
        assert json.loads(sql(f"SELECT observation FROM price_observations WHERE id={first_id};")) == sample()
        scaled = sample(volume=0.0)
        scaled["provider_metadata"]["raw_timestamp_ms"] = 1777593600000.0
        assert json.loads(sql(append([scaled])))["observation_ids"] == [first_id]
        limit = json.loads(sql(append([sample()] * 5000)))
        assert limit["existing_count"] == 5000 and limit["observation_ids"] == [first_id] * 5000
        corrected = sample(close=1.14)
        retrieved = sample(retrieved_at="2026-05-02T02:00:00Z")
        variants = json.loads(sql(append([corrected, retrieved, sample()])))
        assert variants["inserted_count"] == 2 and variants["existing_count"] == 1
        assert variants["observation_ids"][2] == first_id
        assert len(set(variants["observation_ids"])) == 3
        assert json.loads(sql(f"SELECT observation FROM price_observations WHERE id={first_id};")) == sample()
        revised_metadata = sample(provider_metadata={**sample()["provider_metadata"], "request_id": "second-response"})
        assert json.loads(sql(append([revised_metadata])))["inserted_count"] == 1
        CHECKS.append("exact retries, numeric canonical hashes, ordered duplicate IDs, corrections and later retrievals preserved")

        for value in [None, {}, 1, "rows"]:
            rejected(value, "must be an array")
        rejected([sample()] * 5001, "exceeds 5000")
        rejected([None], "must be an object")
        rejected([sample(secret="not-accepted")], "exactly the contract fields")
        missing = sample()
        del missing["session_definition"]
        rejected([missing], "exactly the contract fields")
        for key in ["pair", "provider", "instrument", "date", "retrieved_at"]:
            for value in [None, True, {}, " "]:
                rejected([sample(**{key: value})], "Required observation string")
        for key, value in [("pair", "GBPUSD"), ("provider", "invented")]:
            rejected([sample(**{key: value})], "Unsupported observation pair or provider")
        rejected([sample(date="2026-5-01")], "YYYY-MM-DD")
        rejected([sample(date="2026-02-30")], "date/time field value out of range")
        for key in ["open", "high", "low", "close", "volume"]:
            for value in [None, True, "NaN", "Infinity", "1.0", {}, []]:
                rejected([sample(**{key: value})], "Finite observation number required")
            rejected([sample(**{key: -1})], "Invalid observation price or volume")
            sql(append([sample()]).replace(f'"{key}": {json.dumps(sample()[key])}', f'"{key}": 1e1000'),
                error="Finite observation number required")
        for key in ["open", "high", "low", "close"]:
            rejected([sample(**{key: 0})], "Invalid observation price or volume")
        for changes in [{"low": 1.14}, {"high": 1.11}, {"open": 2}, {"close": 0.9}]:
            rejected([sample(**changes)], "OHLC ordering")
        # Rounding cannot hide an exact ordering error.
        sql(append([sample()]).replace('"low": 1.1', '"low": 1.120000000000000001'), error="OHLC ordering")
        CHECKS.append("strict shape, field allowlist, pair/provider/date, finite numbers, positive OHLC, nonnegative volume")

        for key in ["retrieved_at", "provider_timestamp", "window_start", "window_end"]:
            for value in ["2026-05-01T00:00:00", "2026-05-01", "infinity", 1, True]:
                message = "Required observation string" if key == "retrieved_at" and not isinstance(value, str) else "ISO offset"
                rejected([sample(**{key: value})], message)
        for key in ["retrieved_at", "provider_timestamp"]:
            rejected([sample(**{key: "2099-01-01T00:00:00Z"})], "Future observation timestamp")
        rejected([sample(provider_timestamp="2026-05-02T02:00:00Z")], "Provider timestamp follows retrieval")
        rejected([sample(window_start="2026-05-01T00:00:00Z")], "Invalid observation window")
        rejected([sample(window_end="2026-05-02T00:00:00Z")], "Invalid observation window")
        rejected([sample(window_start="2026-05-02T00:00:00Z", window_end="2026-05-02T00:00:00Z")], "Invalid observation window")
        rejected([sample(window_start="2026-05-03T00:00:00Z", window_end="2026-05-04T00:00:00Z")], "Invalid observation window")
        opened = sample(window_start="2026-05-01T00:00:00+00:00", window_end="2099-01-01T00:00:00Z")
        assert json.loads(sql(append([opened])))["inserted_count"] == 1
        zoned = sample(retrieved_at="2026-05-02T06:30:00+05:30", provider_timestamp=None)
        zoned_id = json.loads(sql("SET TIME ZONE 'Pacific/Honolulu'; " + append([zoned])))["observation_ids"][0]
        assert json.loads(sql("SET TIME ZONE 'Asia/Kolkata'; " + append([zoned])))["observation_ids"] == [zoned_id]
        for key in ["session_timezone", "session_definition", "volume_source", "volume_instrument"]:
            rejected([sample(**{key: True})], "metadata must be a nonblank string or null")
        rejected([sample(provider_metadata=[])], "must be an object")
        rejected([sample(provider_metadata={"api_key": "not-accepted"})], "Unknown provider_metadata field")
        rejected([sample(provider_metadata={"raw_index": {"nested": "not-accepted"}})], "must be scalar")
        accepted_pairs = [sample(pair="USDJPY", instrument="JPY=X", provider="yahoo", volume=125,
                                 volume_source="cme", volume_instrument="6J=F", provider_metadata={}),
                          sample(pair="USDINR", instrument="USD/INR", provider="alphavantage", provider_timestamp=None,
                                 provider_metadata={"provider_timezone": "UTC", "last_refreshed": None})]
        assert json.loads(sql(append(accepted_pairs)))["inserted_count"] == 2
        CHECKS.append("aware timestamps independent of DB timezone; future retrieval rejected; honest null sessions and open windows retained")

        sequence_before = sql("SELECT last_value FROM price_observations_id_seq;")
        rejected([sample(instrument="batch-before-invalid"), sample(close=-1)], "Invalid observation price or volume")
        assert sql("SELECT last_value FROM price_observations_id_seq;") == sequence_before
        sql("""CREATE FUNCTION fail_second_observation() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF NEW.instrument='injected-failure' THEN RAISE EXCEPTION 'injected storage failure'; END IF;
            RETURN NEW; END $$;
            CREATE TRIGGER fail_second_observation BEFORE INSERT ON price_observations
            FOR EACH ROW EXECUTE FUNCTION fail_second_observation();""")
        rejected([sample(instrument="rollback-first"), sample(instrument="injected-failure")], "injected storage failure")
        sql("DROP TRIGGER fail_second_observation ON price_observations;")
        CHECKS.append("whole batch validated before allocation; injected mid-write failure rolls back every archive insert")

        barrier = threading.Barrier(2)
        parallel_rows = [sample(instrument="concurrent-a"), sample(instrument="concurrent-b")]

        def worker(reverse: bool) -> dict:
            barrier.wait(timeout=10)
            rows = parallel_rows[::-1] if reverse else parallel_rows
            result = sql("BEGIN; SET LOCAL ROLE service_role; " + append(rows) + " SELECT pg_sleep(0.3); COMMIT;")
            return json.loads(result.splitlines()[0])

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(worker, [False, True]))
        assert outcomes[0]["observation_ids"] == outcomes[1]["observation_ids"][::-1]
        assert sum(result["inserted_count"] for result in outcomes) == 2
        assert sum(result["existing_count"] for result in outcomes) == 2
        assert sql("SELECT count(*) FROM price_observations WHERE instrument LIKE 'concurrent-%';") == "2"
        CHECKS.append("simultaneous duplicate retries and reversed overlapping batches return same IDs without deadlocks")

        for role in ["anon", "authenticated"]:
            sql(f"SET ROLE {role}; SELECT * FROM price_observations;", error="permission denied")
            sql(f"SET ROLE {role}; " + append([sample()]), error="permission denied")
        count = sql("SELECT count(*) FROM price_observations;")
        assert sql("SET ROLE service_role; SELECT count(*) FROM price_observations;") == count
        assert sql("SELECT relrowsecurity FROM pg_class WHERE oid='public.price_observations'::regclass;") == "t"
        for role in ["anon", "authenticated", "service_role"]:
            for mutation in ["INSERT INTO price_observations DEFAULT VALUES", "UPDATE price_observations SET pair='USDJPY'",
                             "DELETE FROM price_observations", "TRUNCATE price_observations"]:
                sql(f"SET ROLE {role}; {mutation};", error="permission denied")
            sql(f"SET ROLE {role}; SELECT nextval('price_observations_id_seq');", error="permission denied")
            sql(f"SET ROLE {role}; SELECT public.reject_price_observation_mutation();", error="permission denied")
            sql(f"SET ROLE {role}; SELECT public.publication_canonical_json('{{}}');", error="permission denied")
        for mutation in ["UPDATE price_observations SET pair='USDJPY'", "DELETE FROM price_observations", "TRUNCATE price_observations"]:
            sql(mutation + ";", error="immutable")
        assert sql("SELECT count(*) FROM pg_proc WHERE oid IN ('public.append_price_observations(jsonb)'::regprocedure,"
                   "'public.reject_price_observation_mutation()'::regprocedure) AND 'search_path=pg_catalog, public'=ANY(proconfig);") == "2"
        # Defense in depth: accidental SELECT grants still reveal no rows under RLS.
        sql("GRANT SELECT ON price_observations TO anon,authenticated;")
        assert sql("SET ROLE anon; SELECT count(*) FROM price_observations;") == "0"
        assert sql("SET ROLE authenticated; SELECT count(*) FROM price_observations;") == "0"
        sql("REVOKE SELECT ON price_observations FROM anon,authenticated;")
        CHECKS.append("private RLS and explicit read/execute grants; application direct writes and owner mutation/truncate rejected")

        verify_writer()
        before_reapply = snapshot("price_observations")
        sql(migration)
        assert snapshot("price_observations") == before_reapply
        for table, before in preserved.items():
            assert snapshot(table) == before, table
        CHECKS.append("populated migration reapplication preserves all observations and existing historical/publication rows")
        for check in CHECKS:
            print("PASS:", check)
        print("PRICE_OBSERVATION_DB_VERIFIED")
    finally:
        assert DB.startswith("fxobservation_") and len(DB) == 46
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
