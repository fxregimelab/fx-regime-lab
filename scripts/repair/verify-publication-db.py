"""Verify atomic publication in a disposable local PostgreSQL database.

Requires the manually started task-local WSL server. Never reads credentials,
.env files, production endpoints, or starts/stops a runtime. This fixture is not
an assertion that the full historical migration chain is safe to deploy.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import fields
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import threading
import uuid

ROOT = Path(__file__).resolve().parents[2]
# Import serialization code without generating files outside this packet's scope.
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
DB = "fxpublication_" + uuid.uuid4().hex
BASE = [
    "wsl", "-d", "Ubuntu-24.04", "--", "/usr/lib/postgresql/17/bin/psql",
    "-h", "/home/shreyash/.local/state/fxregime-repair/socket", "-p", "55437",
    "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
]
CHECKS: list[str] = []


def run(statement: str, database: str = DB) -> subprocess.CompletedProcess[str]:
    return subprocess.run(BASE + ["-d", database], input=statement, text=True,
                          capture_output=True, timeout=45, encoding="utf-8")


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = run(statement, database)
    if error is not None:
        assert result.returncode != 0 and error in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def literal(value: object) -> str:
    return "'" + json.dumps(value, allow_nan=False, ensure_ascii=True).replace("'", "''") + "'::jsonb"


def publication(model: str = "repair-v1", *, source: str = "live",
                day: str = "2026-09-01", pair: str = "EURUSD") -> tuple[dict, dict, dict]:
    call = {
        "pair": pair, "date": day, "regime": "TRENDING", "confidence": 0.7,
        "signal_composite": 1.0, "rate_signal": "BULLISH", "primary_driver": "rate",
        "entry_timing": "ENTER", "position_size": "HALF", "stop_level": 1.0,
        "data_quality_score": 0.8, "stress_level": "GREEN", "predicted_direction": "BULLISH",
        "directional_bias": "LONG", "conviction": 3, "cot_signal": "NEUTRAL",
        "vol_signal": "NEUTRAL", "oi_signal": "NEUTRAL", "rr_signal": "NEUTRAL",
        "special_signal_value": None, "special_signal_label": None, "regime_category": "RATE_DRIVEN",
        "model_version": model, "strategy_version": "v2", "data_source": source,
    }
    numeric_fields = (
        "rate_diff_2y rate_diff_10y cot_percentile realized_vol_20d realized_vol_5d "
        "implied_vol_30d spot day_change day_change_pct cross_asset_vix cross_asset_dxy "
        "cross_asset_oil cross_asset_us10y cross_asset_gold cross_asset_copper cross_asset_stoxx "
        "oi_delta volume_rvol breakeven_inflation_10y rate_diff_10y_real rate_z_tactical "
        "rate_z_structural z_blended realized_vol_rank skew_alignment risk_reversal_25d "
        "days_since_cot fpi_flow cot_net_pos cot_asset_mgr_net cot_lev_money_net ecb_balance_sheet "
        "bund_btp_spread boj_policy_rate india_vix inr_forward_premium"
    ).split()
    signal = {key: None for key in numeric_fields}
    signal.update({"pair": pair, "date": day, "spot": 1.2, "structural_instability": False,
                   "days_since_cot": 2, "risk_reversal_source": "PENDING_REAL_DATA",
                   "data_quality_notes": ["full signal notes retained", "apostrophe: O'Reilly", "Unicode: EUR/JPY"]})
    rationale = {"pair": pair, "date": day, "layer1_reasoning": "Observed test rationale",
                 "layer2_reasoning": "Positioning", "layer3_reasoning": "Execution",
                 "primary_driver_detail": "Rate differential", "confidence_explanation": "Test confidence",
                 "contrarian_flags": ["TEST_ONLY"]}
    return call, signal, rationale


def append(call: object, signal: object, rationale: object, predecessor: int | None = None) -> str:
    prior = "NULL" if predecessor is None else str(predecessor)
    return f"SELECT public.append_regime_publication({literal(call)},{literal(signal)},{literal(rationale)},{prior});"


def snapshot(table: str, condition: str = "true") -> str:
    assert table in {"regime_calls", "signals", "call_rationale", "publication_evidence", "signal_projection_history"}
    return sql(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM public.{table} t WHERE {condition};")


def concurrent(rows: list[tuple[dict, dict, dict]]) -> list[subprocess.CompletedProcess[str]]:
    barrier = threading.Barrier(len(rows))

    def worker(row: tuple[dict, dict, dict]) -> subprocess.CompletedProcess[str]:
        barrier.wait(timeout=10)
        # Keep the winning transaction open so the second worker must wait.
        return run("BEGIN; " + append(*row) + " SELECT pg_sleep(0.4); COMMIT;")

    with ThreadPoolExecutor(max_workers=len(rows)) as pool:
        return list(pool.map(worker, rows))


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8-sig"))
        originals = {table: snapshot(table) for table in ("regime_calls", "signals", "call_rationale")}
        migration = (ROOT / "supabase/migrations/20260927000004_atomic_publication.sql").read_text(encoding="utf-8-sig")
        sql(migration)
        sql(migration)
        for table, original in originals.items():
            assert snapshot(table) == original, f"Migration changed original {table}"
        assert sql("SELECT directional_bias FROM regime_calls WHERE id=1;") == "Long"
        assert sql("SELECT to_regclass('public.old_regime_date_pair') IS NULL;") == "t"
        assert sql("SELECT to_regclass('public.retain_regime_pair') IS NOT NULL;") == "t"
        assert sql("SELECT count(*) FROM pg_constraint WHERE conrelid='public.regime_calls'::regclass AND contype='p';") == "1"
        CHECKS.append("Migration reapplied; original rows and unrelated indexes preserved")

        row = publication()
        first = int(sql(append(*row, predecessor=1)))
        assert first != 1
        assert int(sql(append(*row, predecessor=1))) == first
        retry = copy.deepcopy(row)
        retry[0].update({"id": 999999, "created_at": "1900-01-01", "correlation_id": "retry-trace",
                         "write_hash": "caller-untrusted", "signal_composite": 1})
        retry[1].update({"id": 99999, "created_at": "1900-01-01"})
        retry[2].update({"call_id": 99999, "id": 99999, "created_at": "1900-01-01"})
        assert int(sql(append(*retry, predecessor=1))) == first
        assert sql(f"SELECT call_id FROM call_rationale WHERE call_id={first};") == str(first)
        evidence = json.loads(snapshot("publication_evidence", f"call_id={first}"))[0]
        assert evidence["signal_payload"] == row[1]
        assert evidence["call_payload"] == row[0]
        assert evidence["rationale_payload"] == row[2]
        assert evidence["supersedes_call_id"] == 1 and len(evidence["payload_hash"]) == 64
        history = json.loads(snapshot("signal_projection_history"))
        assert len(history) == 1 and history[0]["signal_payload"] == json.loads(originals["signals"])[0]
        assert history[0]["operation"] == "UPDATE" and "call_id" not in history[0]
        CHECKS.append("Atomic publication, full evidence, server rationale identity and semantic retry")

        for index, field, changed in [(0, "confidence", 0.8), (1, "spot", 1.3), (2, "layer1_reasoning", "Changed")]:
            conflict = copy.deepcopy(row)
            conflict[index][field] = changed
            sql(append(*conflict, predecessor=1), error="content conflict")
        sql(append(*row), error="content conflict")
        legacy = publication("legacy")
        sql(append(*legacy), error="Legacy publication lacks evidence")
        live_projection = snapshot("signals")
        replay = publication(source="backtest")
        replay[1]["spot"] = 9.9
        replay_id = int(sql(append(*replay, predecessor=first)))
        assert replay_id != first and snapshot("signals") == live_projection
        assert snapshot("regime_calls", "id=1") == originals["regime_calls"]
        assert snapshot("call_rationale", "call_id=1") == originals["call_rationale"]
        for model, strategy in [("repair-v2", "v2"), ("repair-v2", "v3")]:
            version = publication(model)
            version[0]["strategy_version"] = strategy
            int(sql(append(*version, predecessor=first)))
        assert sql("SELECT count(*) FROM regime_calls WHERE pair='EURUSD' AND date='2026-09-01';") == "5"
        CHECKS.append("Call/signal/rationale/predecessor conflicts; legacy refusal; independent cohorts and replay projection isolation")

        bad_cases = []
        for field, value in [("pair", "GBPUSD"), ("data_source", "synthetic"),
                             ("strategy_version", " "), ("model_version", None),
                             ("model_version", {}), ("predicted_direction", "LONG"),
                             ("predicted_direction", None), ("confidence", "NaN"),
                             ("confidence", None), ("confidence", 1.1),
                             ("conviction", 2.5), ("conviction", 6),
                             ("signal_composite", "Infinity"), ("date", "2026-02-30")]:
            bad = list(publication("bad"))
            bad[0][field] = value
            bad_cases.append(bad)
        for field, value in [("pair", "USDJPY"), ("date", None), ("spot", "NaN"),
                             ("spot", True), ("data_quality_notes", "lost array"),
                             ("oi_delta", 2.5), ("days_since_cot", 0.5),
                             ("data_quality_notes", [False]), ("structural_instability", "false"),
                             ('spot); DROP TABLE public.signals;--', 1)]:
            bad = list(publication("bad"))
            bad[1][field] = value
            bad_cases.append(bad)
        for index, value in [(0, None), (0, []), (1, None), (1, []), (2, [])]:
            bad = list(publication("bad"))
            bad[index] = value
            bad_cases.append(bad)
        for field, value in [("pair", "USDJPY"), ("date", "2026-01-01"),
                             ("contrarian_flags", [1]), ("layer1_reasoning", {})]:
            bad = list(publication("bad"))
            bad[2][field] = value
            bad_cases.append(bad)
        before_bad = snapshot("regime_calls")
        for bad in bad_cases:
            result = run(append(*bad))
            assert result.returncode != 0, f"Invalid publication accepted: {bad}"
        assert snapshot("regime_calls") == before_bad
        sql(append(*publication("bad-prior"), predecessor=999999), error="Predecessor does not exist")
        sql(append(*publication("bad-prior", day="2026-09-02"), predecessor=1), error="Predecessor pair/date")
        sql(append(*publication("bad-prior", pair="USDJPY"), predecessor=1), error="Predecessor pair/date")
        CHECKS.append(f"Rejected {len(bad_cases)} malformed payloads and invalid predecessor cases without rows")

        for pair in ("USDJPY", "USDINR"):
            other = publication("pair-check", pair=pair)
            other[0].update({"id": 999999, "created_at": "1900-01-01", "correlation_id": "first-trace"})
            other[1]["spot"] = 145.0 if pair == "USDJPY" else 83.0
            other[2].update({"call_id": 999999, "id": 999999, "created_at": "1900-01-01"})
            other_id = int(sql(append(*other)))
            assert other_id != 999999
            assert sql(f"SELECT correlation_id FROM regime_calls WHERE id={other_id};") == "first-trace"
            assert sql(f"SELECT call_id FROM call_rationale WHERE call_id={other_id};") == str(other_id)
        without_rationale = publication("no-rationale", day="2026-09-02")
        no_rationale_id = int(sql(append(without_rationale[0], without_rationale[1], None)))
        assert sql(f"SELECT confidence_explanation FROM call_rationale WHERE call_id={no_rationale_id};") == "Rationale not supplied; signal snapshot retained."
        minimal_rationale = {"confidence_explanation": "Rationale not supplied; signal snapshot retained."}
        assert int(sql(append(without_rationale[0], without_rationale[1], minimal_rationale))) == no_rationale_id
        assert int(sql(append(without_rationale[0], without_rationale[1], None).replace("'null'::jsonb", "NULL"))) == no_rationale_id
        CHECKS.append("All three pairs publish; server IDs and default rationale cannot be overridden")

        # Actual dataclasses and production request builder, with no API client or environment access.
        from src.db.writer import _publication_request
        from src.types import RegimeCall, SignalRow

        writer_call, writer_signal, writer_rationale = publication("python-writer", day="2026-09-03")
        writer_call["date"] = date.fromisoformat(writer_call["date"])
        writer_signal["date"] = date.fromisoformat(writer_signal["date"])
        request = _publication_request(RegimeCall(**writer_call), SignalRow(**writer_signal),
                                       rationale=writer_rationale, correlation_id="python-writer-trace")
        writer_id = int(sql(append(request["p_call"], request["p_signal"], request["p_rationale"],
                                   request["p_supersedes_call_id"])))
        writer_evidence = json.loads(snapshot("publication_evidence", f"call_id={writer_id}"))[0]
        assert writer_evidence["signal_payload"] == request["p_signal"]
        assert sql(f"SELECT directional_bias FROM regime_calls WHERE id={writer_id};") == "LONG"
        assert writer_evidence["call_payload"] == {k: v for k, v in request["p_call"].items() if k != "correlation_id"}
        for table, dataclass in (("regime_calls", RegimeCall), ("signals", SignalRow)):
            schema_fields = set(sql(f"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='{table}';").splitlines())
            assert {field.name for field in fields(dataclass)} <= schema_fields
        assert sql("SELECT days_since_cot=2 AND risk_reversal_source='PENDING_REAL_DATA' FROM signals WHERE date='2026-09-03';") == "t"
        CHECKS.append("Actual Python writer request publishes every dataclass field into complete fixture and evidence")

        tables = ("regime_calls", "publication_evidence", "call_rationale", "signals", "signal_projection_history")
        before_failure = {table: snapshot(table) for table in tables}
        sql("""CREATE FUNCTION public.fixture_fail_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN
            IF NOT EXISTS(SELECT 1 FROM public.regime_calls WHERE id=NEW.call_id) THEN
              RAISE EXCEPTION 'test did not reach after-call boundary';
            END IF;
            RAISE EXCEPTION 'fixture failure after call insert';
          END $$;
          CREATE TRIGGER fixture_fail_evidence BEFORE INSERT ON public.publication_evidence
            FOR EACH ROW EXECUTE FUNCTION public.fixture_fail_evidence();""")
        sql(append(*publication("rollback-after-call")), error="fixture failure after call insert")
        sql("DROP TRIGGER fixture_fail_evidence ON public.publication_evidence; DROP FUNCTION public.fixture_fail_evidence();")
        for table, original in before_failure.items():
            assert snapshot(table) == original, f"After-call failure changed {table}"
        sql("""CREATE FUNCTION public.fixture_fail_projection() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN RAISE EXCEPTION 'fixture failure after projection'; END $$;
          CREATE TRIGGER fixture_fail_projection AFTER UPDATE ON public.signals
            FOR EACH ROW EXECUTE FUNCTION public.fixture_fail_projection();""")
        sql(append(*publication("rollback-after-projection")), error="fixture failure after projection")
        sql("DROP TRIGGER fixture_fail_projection ON public.signals; DROP FUNCTION public.fixture_fail_projection();")
        for table, original in before_failure.items():
            assert snapshot(table) == original, f"After-projection failure changed {table}"
        CHECKS.append("Injected failures after call insert and projection replacement roll back every publication table")

        repeat = publication("concurrent-same", day="2026-09-06")
        results = concurrent([repeat, copy.deepcopy(repeat)])
        assert all(result.returncode == 0 for result in results), [result.stderr for result in results]
        ids = [result.stdout.strip().splitlines()[0] for result in results]
        assert ids[0] == ids[1]
        assert sql("SELECT count(*) FROM regime_calls WHERE date='2026-09-06';") == "1"
        competing = publication("concurrent-conflict", day="2026-09-07")
        changed = copy.deepcopy(competing)
        changed[1]["spot"] = 1.9
        results = concurrent([competing, changed])
        assert sum(result.returncode == 0 for result in results) == 1
        assert sum("content conflict" in result.stderr for result in results) == 1
        assert sql("SELECT count(*) FROM regime_calls WHERE date='2026-09-07';") == "1"
        # Different identities on the same date both survive and projection matches one complete publication.
        variants = [publication("concurrent-v1", day="2026-09-08"), publication("concurrent-v2", day="2026-09-08")]
        variants[0][1]["spot"] = 1.5
        variants[1][1]["spot"] = 1.6
        results = concurrent(variants)
        assert all(result.returncode == 0 for result in results), [result.stderr for result in results]
        assert sql("SELECT count(*) FROM regime_calls WHERE date='2026-09-08';") == "2"
        assert sql("SELECT count(*) FROM signal_projection_history WHERE date='2026-09-08';") == "1"
        assert sql("SELECT spot IN (1.5,1.6) FROM signals WHERE date='2026-09-08';") == "t"
        CHECKS.append("Concurrent identical retries converge, conflicts reject, and independent versions serialize projection")

        projection_before_direct = json.loads(snapshot("signals", "date='2026-09-01' AND pair='EURUSD'"))[0]
        sql("SET ROLE service_role; UPDATE signals SET spot=1.55 WHERE date='2026-09-01' AND pair='EURUSD';")
        assert sql("SELECT signal_payload=" + literal(projection_before_direct) + " FROM signal_projection_history ORDER BY id DESC LIMIT 1;") == "t"
        projection_before_delete = json.loads(snapshot("signals", "date='2026-09-01' AND pair='EURUSD'"))[0]
        sql("SET ROLE service_role; DELETE FROM signals WHERE date='2026-09-01' AND pair='EURUSD';")
        assert sql("SELECT operation='DELETE' AND signal_payload=" + literal(projection_before_delete) + " FROM signal_projection_history ORDER BY id DESC LIMIT 1;") == "t"
        for table, key in [("regime_calls", "id"), ("publication_evidence", "call_id"),
                           ("call_rationale", "id"), ("signal_projection_history", "id")]:
            sql(f"UPDATE public.{table} SET {key}={key};", error="immutable")
            sql(f"DELETE FROM public.{table};", error="immutable")
        CHECKS.append("Direct projection UPDATE/DELETE preserves complete prior rows; originals and all evidence tables reject mutation")

        for role in ("anon", "authenticated"):
            sql(f"SET ROLE {role}; " + append(*row, predecessor=1), error="permission denied")
            for table in ("regime_calls", "publication_evidence", "call_rationale", "signal_projection_history"):
                assert sql(f"SELECT has_table_privilege('{role}','public.{table}','INSERT,UPDATE,DELETE,TRUNCATE');") == "f"
                sql(f"SET ROLE {role}; INSERT INTO public.{table} DEFAULT VALUES;", error="permission denied")
        for table in ("regime_calls", "publication_evidence", "signal_projection_history"):
            sql(f"SET ROLE service_role; INSERT INTO public.{table} DEFAULT VALUES;", error="permission denied")
        assert int(sql("SET ROLE service_role; " + append(*row, predecessor=1))) == first
        role_row = publication("service-created", day="2026-09-09")
        role_id = int(sql("SET ROLE service_role; " + append(*role_row)))
        assert sql(f"SELECT count(*) FROM publication_evidence WHERE call_id={role_id};") == "1"
        assert sql(f"SET ROLE service_role; SELECT count(*) FROM publication_evidence WHERE call_id={role_id};") == "1"
        assert sql("SELECT prosecdef AND proconfig @> ARRAY['search_path=pg_catalog, public'] FROM pg_proc WHERE oid='public.append_regime_publication(jsonb,jsonb,jsonb,integer)'::regprocedure;") == "t"
        sql("CREATE SCHEMA fixture_attacker AUTHORIZATION service_role;")
        assert int(sql("SET ROLE service_role; SET search_path=fixture_attacker; " + append(*role_row))) == role_id
        CHECKS.append("Service-only execution, direct protected writes denied, and fixed function search path verified")

        # Reapply after publication to ensure populated evidence and history survive unchanged.
        before_reapply = {table: snapshot(table) for table in tables}
        sql(migration)
        for table, original in before_reapply.items():
            assert snapshot(table) == original, f"Reapplication changed {table}"
        CHECKS.append("Migration reapplied after populated publication evidence without changing a row")
        # A deliberately inconsistent scratch pre-migration state must fail closed.
        sql("""DROP INDEX public.regime_calls_publication_identity;
            INSERT INTO public.regime_calls(pair,date,regime,confidence,signal_composite,rate_signal,
              predicted_direction,model_version,strategy_version,data_source)
            SELECT pair,date,regime,confidence,signal_composite,rate_signal,
              predicted_direction,model_version,strategy_version,data_source
            FROM public.regime_calls WHERE id=1;""")
        before_duplicate_failure = {table: snapshot(table) for table in tables}
        sql(migration, error="could not create unique index")
        for table, original in before_duplicate_failure.items():
            assert snapshot(table) == original, f"Failed migration changed {table}"
        CHECKS.append("Duplicate historical identities abort migration without deleting or rewriting evidence")
        for check in CHECKS:
            print("PASS " + check)
        print("PUBLICATION_DB_VERIFIED")
    finally:
        assert DB.startswith("fxpublication_") and len(DB) == 46
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
