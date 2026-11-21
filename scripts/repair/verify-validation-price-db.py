"""Exercise price evidence against a disposable, task-local PostgreSQL database.

No production endpoint, credentials, .env, or runtime startup is used. Fixtures
prove this forward contract, not the full historical deployment chain.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import threading
import uuid
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "pipeline"))
from src.validation.calculator import calculate_horizon  # noqa: E402
from src.validation.calendar import add_trading_days  # noqa: E402
from src.validation.evaluator import evaluate_call  # noqa: E402
from src.db import writer  # noqa: E402

DB = "fxprice_" + uuid.uuid4().hex
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


def append(row: dict) -> str:
    return f"SELECT public.append_validation_evaluation({literal(row)});"


def payload(call_id: int, spot: float, *, horizon: str = "t5", close: float = 1.19,
            direction: str = "BULLISH", pair: str = "EURUSD") -> dict:
    day = date(2026, 5, 1)
    stats = calculate_horizon(spot, close, direction, 0.7, pair)
    row = {"call_id": call_id, "pair": pair, "call_date": str(day),
           "evaluation_version": "publication-snapshot-v2",
           "entry_price_evidence": {"kind": "publication_signal", "call_id": call_id,
                                    "pair": pair, "date": str(day), "price": spot,
                                    "source": "publication_evidence.signal_payload.spot"},
           f"price_evidence_{horizon}": {"kind": "historical_close", "pair": pair,
                                       "date": str(add_trading_days(day, 5 if horizon == "t5" else 20)),
                                       "price": close, "source": "historical_prices.close"}}
    for target, source in {f"log_return_{horizon}_bps": "log_return_bps",
                           f"correct_{horizon}": "correct", f"brier_score_{horizon}": "brier_score",
                           f"actual_direction_{horizon}": "realized_direction",
                           f"log_return_net_bps_{horizon}": "log_return_net_bps",
                           f"correct_net_{horizon}": "correct_net", f"cost_bps_{horizon}": "cost_bps"}.items():
        row[target] = stats[source]
    return row


def snapshot(table: str) -> str:
    assert table in {"validation_log", "validation_stats"}
    return sql(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY id),'[]'::jsonb) FROM {table} t;")


def main() -> None:
    spec = importlib.util.spec_from_file_location("publication_fixture", ROOT / "scripts/repair/verify-publication-db.py")
    assert spec is not None and spec.loader is not None
    publication_fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publication_fixture)
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        fixture = (ROOT / "scripts/repair/validation-db-fixture.sql").read_text(encoding="utf-8")
        sql(fixture[fixture.index("CREATE TABLE public.validation_log"):fixture.index("INSERT INTO public.regime_calls")])
        sql("CREATE TABLE historical_prices(pair text, date date, close float8, PRIMARY KEY(pair,date));")
        migrations = ["20260927000001_validation_evaluation_contract.sql", "20260505000002_validation_stats.sql",
                      "20260526000000_v2_1_honest_metrics.sql", "20260927000002_validation_cohorts.sql",
                      "20260927000003_published_validation_population.sql", "20260927000004_atomic_publication.sql"]
        # Resolve the publication migration's real name rather than assuming a suffix.
        migrations[-1] = next((ROOT / "supabase/migrations").glob("20260927000004_*.sql")).name
        for name in migrations:
            sql((ROOT / "supabase/migrations" / name).read_text(encoding="utf-8"))
        historical = payload(1, 1.2)
        historical = {k: v for k, v in historical.items() if "evidence" not in k}
        historical.update(evaluation_version="published-direction-v1", call_date="2026-09-01")
        # Legacy call has confidence 0.6; v1 semantics intentionally do not recompute its score.
        sql(append(historical))
        sql("INSERT INTO validation_stats(as_of_date,pair,t5_win_rate) VALUES ('2026-09-01','EURUSD',0.99);")
        old_rows, old_stats = snapshot("validation_log"), snapshot("validation_stats")
        migration = (ROOT / "supabase/migrations/20260927000006_validation_price_evidence.sql").read_text(encoding="utf-8")
        sql(migration)
        sql(migration)
        assert snapshot("validation_stats") == old_stats
        new_old_rows = json.loads(snapshot("validation_log"))
        for row in new_old_rows:
            for key in ("entry_price_evidence", "price_evidence_t5", "price_evidence_t20"):
                assert row.pop(key) is None
        assert new_old_rows == json.loads(old_rows)
        assert json.loads(sql(append(historical)))["evaluation_version"] == "published-direction-v1"
        assert sql("SELECT evaluation_present FROM validation_observations WHERE call_id=1;") == "f"
        CHECKS.append("repeatable migration preserves old rows and statistics; v1 dispatch retained")

        ids = []
        for model, spot, direction, pair in [("price-a", 1.2, "BULLISH", "EURUSD"),
                                             ("price-b", 1.18, "BULLISH", "EURUSD"),
                                             ("price-c", 1.2, "BEARISH", "EURUSD"),
                                             ("neutral", 1.2, "NEUTRAL", "USDINR"),
                                             ("parallel", 1.2, "BULLISH", "USDJPY")]:
            call, signal, rationale = publication_fixture.publication(model, pair=pair, day="2026-05-01")
            call["predicted_direction"] = direction
            signal["spot"] = spot
            ids.append(int(sql(publication_fixture.append(call, signal, rationale))))
        first_id, second_id, short_id, neutral_id, parallel_id = ids
        sql("INSERT INTO historical_prices VALUES ('EURUSD','2026-05-08',1.19),('EURUSD','2026-05-29',1.21),"
            "('USDINR','2026-05-08',1.19),('USDJPY','2026-05-08',1.19),('USDJPY','2026-05-29',1.21);")
        sql("UPDATE signals SET spot=999;")
        row = payload(first_id, 1.2)
        sql(append({**row, "evaluation_version": "invented-v3"}), error="supported evaluation version")
        sql(append({**row, "confidence": 0.8}), error="Published metadata mismatch")
        sql(append({**row, "actual_return_20d": 42}), error="Horizon fields without a market return")
        sql(append({**payload(1, 1.2), "call_date": "2026-09-01"}), error="Original publication entry evidence required")
        bad = copy.deepcopy(row)
        bad["entry_price_evidence"]["call_id"] = second_id
        sql(append(bad), error="Entry evidence does not match")
        bad = copy.deepcopy(row)
        bad["entry_price_evidence"]["price"] = 1.18
        sql(append(bad), error="Entry evidence does not match")
        for key, value in [("date", "2026-05-07"), ("date", "2026-5-8"), ("pair", "USDJPY"),
                           ("source", "provider-invented"), ("extra", 1)]:
            bad = copy.deepcopy(row)
            bad["price_evidence_t5"][key] = value
            sql(append(bad), error="Endpoint evidence identity or horizon mismatch")
        for value in [0, -1, True, "NaN", "Infinity", None]:
            bad = copy.deepcopy(row)
            bad["price_evidence_t5"]["price"] = value
            sql(append(bad), error="Finite positive endpoint evidence price required")
        sql(append(row).replace('"price": 1.19', '"price": 1e1000'), error="Finite positive endpoint evidence price required")
        sql(append(payload(first_id, 1.2, close=1.17)), error="Endpoint evidence does not match historical close")
        sql(append(row).replace('"price": 1.19', '"price": 1.19000000000000001'),
            error="Endpoint evidence does not match historical close")
        sql("UPDATE historical_prices SET date='2026-05-07' WHERE pair='EURUSD' AND date='2026-05-08';")
        sql(append(row), error="Endpoint evidence does not match historical close")
        sql("UPDATE historical_prices SET date='2026-05-08' WHERE pair='EURUSD' AND date='2026-05-07';")
        sql("UPDATE historical_prices SET close='NaN' WHERE pair='EURUSD' AND date='2026-05-08';")
        sql(append(row), error="Endpoint evidence does not match historical close")
        sql("UPDATE historical_prices SET close=1.19 WHERE pair='EURUSD' AND date='2026-05-08';")
        for key, value in [("log_return_t5_bps", 42), ("correct_t5", True), ("brier_score_t5", 0.1),
                           ("actual_direction_t5", "UP"), ("cost_bps_t5", 7),
                           ("cost_bps_t5", 0.2000000001),
                           ("log_return_net_bps_t5", 9), ("correct_net_t5", True),
                           ("actual_return_5d", 7), ("correct_5d", True), ("brier_5d", 0.1),
                           ("log_return_t5_bps", "NaN"), ("brier_score_t5", True)]:
            sql(append({**row, key: value}), error="Metric inconsistent with price evidence")
        first = json.loads(sql(append(row)))
        assert json.loads(sql(append(row))) == first
        second = json.loads(sql(append(payload(second_id, 1.18))))
        assert first["log_return_t5_bps"] < 0 < second["log_return_t5_bps"]
        short = json.loads(sql(append(payload(short_id, 1.2, direction="BEARISH"))))
        assert short["correct_t5"] is True and short["log_return_net_bps_t5"] > 0
        neutral = json.loads(sql(append(payload(neutral_id, 1.2, direction="NEUTRAL", pair="USDINR"))))
        assert neutral["correct_t5"] is None and neutral["brier_score_t5"] is None
        CHECKS.append("entry ownership, exact dates, finite prices, metric consistency, short and neutral scores")

        sql("DELETE FROM historical_prices WHERE pair='EURUSD' AND date='2026-05-08';")
        assert json.loads(sql(append(row))) == first
        bad = copy.deepcopy(row)
        bad["price_evidence_t5"]["price"] = 1.20
        sql(append(bad), error="Completed horizon is immutable")
        sql(append({**row, "correct_t5": True}), error="Completed horizon is immutable")
        sql("""CREATE FUNCTION reject_price_test_insert() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN IF NEW.log_return_t20_bps IS NOT NULL THEN RAISE EXCEPTION 'injected failure'; END IF;
          RETURN NEW; END $$; CREATE TRIGGER reject_price_test BEFORE INSERT ON validation_log
          FOR EACH ROW EXECUTE FUNCTION reject_price_test_insert();""")
        before = snapshot("validation_log")
        t20 = payload(first_id, 1.2, horizon="t20", close=1.21)
        sql(append(t20), error="injected failure")
        assert snapshot("validation_log") == before
        sql("DROP TRIGGER reject_price_test ON validation_log;")
        completed = json.loads(sql(append(t20)))
        assert completed["price_evidence_t5"] == first["price_evidence_t5"]
        assert completed["log_return_t5_bps"] == first["log_return_t5_bps"]
        sql("DELETE FROM historical_prices WHERE pair='EURUSD';")
        assert json.loads(sql(append(t20))) == completed
        assert json.loads(sql(append(row))) == completed
        CHECKS.append("completed evidence survives endpoint correction/deletion; revisions atomic and immutable")

        barrier = threading.Barrier(2)

        def worker(horizon: str) -> str:
            barrier.wait(timeout=10)
            current = payload(parallel_id, 1.2, pair="USDJPY", horizon=horizon,
                              close=1.19 if horizon == "t5" else 1.21)
            return sql("BEGIN; " + append(current) + " SELECT pg_sleep(0.5); COMMIT;")

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(worker, ["t5", "t20"]))
        parallel = json.loads(sql(f"SELECT to_jsonb(v) FROM validation_log v WHERE call_id={parallel_id} AND NOT is_superseded;"))
        assert parallel["price_evidence_t5"] and parallel["price_evidence_t20"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(worker, ["t5", "t5"]))
        assert sql(f"SELECT count(*) FROM validation_log WHERE call_id={parallel_id};") == "2"
        CHECKS.append("simultaneous horizons and simultaneous duplicate retries serialize without lost updates")

        for role in ["anon", "authenticated"]:
            sql(f"SET ROLE {role}; " + append(row), error="permission denied")
        assert json.loads(sql("SET ROLE service_role; " + append(row))) == completed
        for role in ["anon", "authenticated", "service_role"]:
            sql(f"SET ROLE {role}; SELECT public.append_validation_evaluation_v1({literal(historical)});", error="permission denied")
            sql(f"SET ROLE {role}; DELETE FROM validation_log;", error="permission denied")
            sql(f"SET ROLE {role}; TRUNCATE validation_log;", error="permission denied")
        sql("UPDATE validation_log SET entry_price_evidence='{}';", error="immutable")
        sql("DELETE FROM validation_log;", error="immutable")
        assert sql("SELECT count(*) FROM validation_observations;") == "6"
        assert sql("SELECT count(*) FROM validation_observations WHERE evaluation_present;") == "5"
        assert sql("SELECT count(*) FROM validation_observations WHERE evaluation_version<>'publication-snapshot-v2';") == "0"
        assert sql("SELECT count(*) FROM validation_log WHERE evaluation_version='published-direction-v1';") == "1"
        assert snapshot("validation_stats") == old_stats
        sql("""GRANT SELECT ON regime_calls,validation_log TO anon,authenticated;
          ALTER TABLE regime_calls ENABLE ROW LEVEL SECURITY;
          ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
          CREATE POLICY price_call_scope ON regime_calls FOR SELECT TO anon,authenticated USING(pair='EURUSD');
          CREATE POLICY price_eval_scope ON validation_log FOR SELECT TO anon,authenticated USING(true);""")
        assert sql("SET ROLE anon; SELECT count(*) FROM validation_observations;") == "4"
        assert sql("SET ROLE authenticated; SELECT count(*) FROM validation_observations WHERE pair='USDJPY';") == "0"
        CHECKS.append("restricted RPC and ledger privileges; v2-only all-call view respects caller RLS")
        # First writes must obey maturity even if a future storage row exists.
        call, signal, rationale = publication_fixture.publication("future", day="2099-05-01")
        future_id = int(sql(publication_fixture.append(call, signal, rationale)))
        future = payload(future_id, 1.2)
        future["call_date"] = "2099-05-01"
        future["entry_price_evidence"]["date"] = "2099-05-01"
        target = str(add_trading_days(date(2099, 5, 1), 5))
        future["price_evidence_t5"]["date"] = target
        sql(f"INSERT INTO historical_prices VALUES ('EURUSD','{target}',1.19);")
        sql(append(future), error="Endpoint horizon has not matured")
        # Values around both strict deadband thresholds exercise Python/SQL parity.
        for index, bps in enumerate([-5.000001, -5.0, -4.999999, 0.0, 4.999999, 5.0, 5.000001]):
            call, signal, rationale = publication_fixture.publication(f"deadband-{index}", day="2026-05-01")
            call_id = int(sql(publication_fixture.append(call, signal, rationale)))
            close = 1.2 * math.exp(bps / 10000)
            sql(f"INSERT INTO historical_prices VALUES ('EURUSD','2026-05-08',{close!r}) "
                "ON CONFLICT(pair,date) DO UPDATE SET close=excluded.close;")
            result = json.loads(sql(append(payload(call_id, 1.2, close=close))))
            assert result["actual_direction_t5"] == calculate_horizon(1.2, close, "BULLISH", 0.7, "EURUSD")["realized_direction"]
        CHECKS.append("future horizon rejection and Python/SQL parity around both 5 bps deadband boundaries")
        # Actual producer and writer, with only the transport redirected locally.
        call, signal, rationale = publication_fixture.publication("evaluator-integration", day="2026-05-01")
        integration_id = int(sql(publication_fixture.append(call, signal, rationale)))
        durable_call = json.loads(sql(f"SELECT to_jsonb(c) FROM regime_calls c WHERE id={integration_id};"))
        sql("INSERT INTO historical_prices VALUES ('EURUSD','2026-05-08',1.19),('EURUSD','2026-05-29',1.21) "
            "ON CONFLICT(pair,date) DO UPDATE SET close=excluded.close;")
        observed_dates: list[date] = []

        def read_entry(call_id: int) -> dict:
            assert call_id == integration_id
            return json.loads(sql(f"SELECT signal_payload FROM publication_evidence WHERE call_id={call_id};"))

        def read_price(pair: str, target: date) -> dict:
            assert pair == "EURUSD"
            observed_dates.append(target)
            return json.loads(sql(f"SELECT to_jsonb(h) FROM historical_prices h WHERE pair='EURUSD' AND date='{target}';"))

        persisted_rows: list[dict] = []

        def rpc(method: str, params: dict) -> MagicMock:
            assert method == "append_validation_evaluation"
            return MagicMock(execute=lambda: persisted_rows.append(json.loads(sql(append(params["p_payload"])))))

        client = MagicMock()
        client.rpc.side_effect = rpc
        with patch.object(writer, "_client", return_value=client):
            produced = evaluate_call(durable_call, date(2026, 5, 8), None, read_entry=read_entry, read_price=read_price)
            assert produced is not None
            writer.write_validation_row(produced)
            assert observed_dates == [date(2026, 5, 8)]
            first_produced = persisted_rows[-1]
            sql("UPDATE historical_prices SET close=999 WHERE pair='EURUSD' AND date='2026-05-08';")
            produced = evaluate_call(durable_call, date(2026, 5, 29), first_produced,
                                     read_entry=read_entry, read_price=read_price)
            assert produced is not None
            writer.write_validation_row(produced)
            assert observed_dates == [date(2026, 5, 8), date(2026, 5, 29)]
            assert persisted_rows[-1]["price_evidence_t5"] == first_produced["price_evidence_t5"]
            never = MagicMock(side_effect=AssertionError("Completed call reread price evidence"))
            assert evaluate_call(durable_call, date(2026, 5, 29), persisted_rows[-1],
                                 read_entry=never, read_price=never) is None
        CHECKS.append("actual evaluator -> writer -> SQL, including aliases, partial completion and no-read completed retry")
        for check in CHECKS:
            print("PASS:", check)
        print("VALIDATION_PRICE_DB_VERIFIED")
    finally:
        assert DB.startswith("fxprice_") and len(DB) == 40
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
