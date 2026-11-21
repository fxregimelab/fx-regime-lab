"""Exercise only a new scratch DB on the task's isolated WSL PostgreSQL socket.

Prerequisite: manual task-local PostgreSQL startup. No production credentials,
network endpoint, service startup, or repository .env file is read.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from src.validation.calculator import calculate_horizon  # noqa: E402
from src.db import writer  # noqa: E402
from src.validation.aggregate import run_aggregate_stats  # noqa: E402

EVALUATION_VERSION = "published-direction-v1"  # Frozen historical contract, independent of current producer.

DB = "fxrepair_" + uuid.uuid4().hex
BASE = ["wsl", "-d", "Ubuntu-24.04", "--", "/usr/lib/postgresql/17/bin/psql",
        "-h", "/home/shreyash/.local/state/fxregime-repair/socket", "-p", "55437",
        "-X", "-qAt", "-v", "ON_ERROR_STOP=1"]


def sql(statement: str, *, database: str = DB, error: str | None = None) -> str:
    result = subprocess.run(BASE + ["-d", database], input=statement, text=True,
                            capture_output=True, timeout=30)
    if error is not None:
        assert result.returncode != 0 and error in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def payload(call_id: int, horizon: str) -> dict[str, object]:
    pair, direction, confidence, day = {
        1: ("EURUSD", "BEARISH", 0.7, "2026-05-01"),
        2: ("USDJPY", "BULLISH", 0.6, "2026-05-04"),
        3: ("USDINR", "NEUTRAL", None, "2026-05-05"),
        4: ("EURUSD", "BEARISH", 0.7, "2026-05-06"),
    }[call_id]
    stats = calculate_horizon(100, 99 if horizon == "t5" else 101, direction, confidence, pair)
    return {"call_id": call_id, "pair": pair, "call_date": day,
            "evaluation_version": EVALUATION_VERSION,
            f"log_return_{horizon}_bps": stats["log_return_bps"],
            f"correct_{horizon}": stats["correct"],
            f"brier_score_{horizon}": stats["brier_score"],
            f"actual_direction_{horizon}": stats["realized_direction"],
            f"log_return_net_bps_{horizon}": stats["log_return_net_bps"],
            f"correct_net_{horizon}": stats["correct_net"],
            f"cost_bps_{horizon}": stats["cost_bps"]}


def append(row: dict[str, object]) -> str:
    encoded = json.dumps(row, allow_nan=False).replace("'", "''")
    return f"SELECT public.append_validation_evaluation('{encoded}'::jsonb);"


def main() -> None:
    sql(f'CREATE DATABASE "{DB}";', database="postgres")
    try:
        sql((ROOT / "scripts/repair/validation-db-fixture.sql").read_text())
        migration = (ROOT / "supabase/migrations/20260927000001_validation_evaluation_contract.sql").read_text()
        sql(migration)
        sql(migration)  # Repeatable without changing existing evidence.
        sql((ROOT / "supabase/migrations/20260505000002_validation_stats.sql").read_text())
        sql("CREATE TABLE public.signals(id serial PRIMARY KEY);")
        sql((ROOT / "supabase/migrations/20260526000000_v2_1_honest_metrics.sql").read_text())
        cohort_migration = (ROOT / "supabase/migrations/20260927000002_validation_cohorts.sql").read_text()
        sql("INSERT INTO validation_stats(as_of_date,pair,t5_win_rate) VALUES ('2026-09-01','EURUSD',0.99);")
        sql(cohort_migration)
        sql(cohort_migration)
        assert sql("SELECT evaluation_version FROM validation_stats LIMIT 1;") == "legacy-unversioned"
        for source, model, window in [("live","2.0-live",0),("backtest","2.0-live",0),("live","2.1",0),("live","2.0-live",90)]:
            sql(f"""INSERT INTO validation_stats(as_of_date,pair,data_source,strategy_version,model_version,evaluation_version,window_days,t5_win_rate)
              VALUES ('2026-09-01','EURUSD','{source}','v2','{model}','published-direction-v1',{window},0.5)
              ON CONFLICT(as_of_date,pair,data_source,strategy_version,model_version,evaluation_version,window_days)
              DO UPDATE SET t5_win_rate=excluded.t5_win_rate;""")
        assert sql("SELECT count(*) FROM validation_stats;") == "5"
        population_migration = (ROOT / "supabase/migrations/20260927000003_published_validation_population.sql").read_text(encoding="utf-8")
        sql(population_migration)
        sql(population_migration)
        assert sql("SELECT count(*) FROM validation_observations;") == "4"
        assert sql("SELECT count(*) FROM validation_observations WHERE evaluation_present;") == "0"
        assert sql("SELECT count(*) FROM validation_stats WHERE population_version='evaluation-records-v1';") == "5"
        t5 = payload(1, "t5")
        first = json.loads(sql(append(t5)))
        same = json.loads(sql(append(t5)))
        assert first == same, "Duplicate write was not idempotent"
        assert json.loads(sql(append({**t5, "call_id": "1"}))) == first
        assert first["data_source"] == "backtest" and first["strategy_version"] == "v2"
        assert first["model_version"] == "2.0-live"
        assert first["correct_t5"] is True and first["log_return_net_bps_t5"] > 0

        sql(append({**t5, "pair": "USDJPY"}), error="does not match")
        sql(append({**t5, "confidence": 0.99}), error="metadata mismatch")
        sql(append({**t5, "data_source": "live"}), error="metadata mismatch")
        sql(append({**t5, "call_id": 999}), error="does not exist")
        sql(append({**t5, "surprise_column": 1}), error="Unknown evaluation field")
        sql(append({**t5, "log_return_t5_bps": 55}), error="Completed horizon is immutable")
        sql(append({**t5, "log_return_t5_bps": None}), error="Completed horizon is immutable")
        sql(append({**t5, "evaluation_version": "legacy-unversioned"}), error="supported evaluation version")
        sql(f"UPDATE validation_log SET cost_bps_t5=99 WHERE id={first['id']};", error="immutable")
        sql(f"DELETE FROM validation_log WHERE id={first['id']};", error="immutable")
        sql("SET ROLE anon; " + append(t5), error="permission denied")
        sql("SET ROLE authenticated; " + append(t5), error="permission denied")
        assert json.loads(sql("SET ROLE service_role; " + append(t5)))["id"] == first["id"]

        # Cause an insertion failure after supersession, then observe rollback.
        sql("""CREATE FUNCTION reject_test_insert() RETURNS trigger LANGUAGE plpgsql AS $$
          BEGIN IF NEW.log_return_t20_bps IS NOT NULL THEN RAISE EXCEPTION 'injected insert failure'; END IF;
          RETURN NEW; END $$;
          CREATE TRIGGER reject_test_insert BEFORE INSERT ON validation_log
          FOR EACH ROW EXECUTE FUNCTION reject_test_insert();""")
        sql(append(payload(1, "t20")), error="injected insert failure")
        assert sql(f"SELECT is_superseded FROM validation_log WHERE id={first['id']};") == "f"
        assert sql("SELECT count(*) FROM validation_log WHERE call_id=1;") == "2"
        sql("DROP TRIGGER reject_test_insert ON validation_log;")
        completed = json.loads(sql(append(payload(1, "t20"))))
        assert completed["log_return_t5_bps"] == first["log_return_t5_bps"]
        assert completed["cost_bps_t5"] == first["cost_bps_t5"]
        assert completed["log_return_t20_bps"] is not None
        sql(f"UPDATE validation_log SET is_superseded=false WHERE id={first['id']};", error="immutable")

        # Hold the parent lock while another connection tries the other horizon.
        process = subprocess.Popen(BASE + ["-d", DB], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert process.stdin is not None
        process.stdin.write("BEGIN; " + append(payload(2, "t5")) + " SELECT pg_sleep(1); COMMIT;")
        process.stdin.close()
        assert process.stdout is not None
        assert json.loads(process.stdout.readline())["log_return_t5_bps"] is not None
        sql(append(payload(2, "t20")))
        process.wait(timeout=20)
        assert process.stderr is not None
        assert process.returncode == 0, process.stderr.read()
        row = json.loads(sql("SELECT to_jsonb(v) FROM validation_log v WHERE call_id=2 AND NOT is_superseded;"))
        assert row["log_return_t5_bps"] is not None and row["log_return_t20_bps"] is not None
        neutral = json.loads(sql(append(payload(3, "t5"))))
        assert all(neutral[k] is None for k in ("correct_t5", "brier_score_t5", "log_return_net_bps_t5", "correct_net_t5"))
        # Preserve v1 verification independently of the current v2 application producer.
        persisted = json.loads(sql(append(payload(4, "t5"))))
        assert persisted["correct_t5"] is True and persisted["data_source"] == "backtest"
        client = MagicMock()
        # Actual aggregate -> writer -> all payload columns in PostgreSQL.
        # Same date/pair is deliberately duplicated: identity must be call ID.
        sql("""INSERT INTO regime_calls(date,pair,predicted_direction,regime,confidence,strategy_version,data_source)
            VALUES ('2026-05-01','EURUSD','BULLISH','TRENDING',0.6,'v2','backtest'),
                   ('2026-08-31','EURUSD','BULLISH','TRENDING',0.6,'v2','backtest');""")
        assert sql("SELECT count(*) FROM validation_observations;") == "6"
        assert sql("SELECT count(*) FROM validation_observations WHERE evaluation_present;") == "4"
        missing = json.loads(sql("SELECT to_jsonb(v) FROM validation_observations v WHERE call_id=5;"))
        assert missing["evaluation_id"] is None and missing["correct_t5"] is None
        assert missing["log_return_t5_bps"] is None and missing["predicted_direction"] == "BULLISH"
        assert missing["population_version"] == "published-calls-v1"
        evidence = json.loads(sql("SELECT json_agg(v) FROM validation_observations v;"))
        client.reset_mock()
        with patch.object(writer, "_client", return_value=client), patch.object(
            writer, "get_validation_log_for_stats", return_value=evidence
        ):
            aggregates = run_aggregate_stats(as_of_date=date(2026, 9, 1))
        writes = client.table.return_value.upsert.call_args_list
        assert len(writes) == len(aggregates) and len(writes) > 1
        for write in writes:
            snapshot = write.args[0]
            columns = list(snapshot)
            assert all(column.replace("_", "").isalnum() for column in columns)
            encoded = json.dumps(snapshot, allow_nan=False).replace("'", "''")
            column_sql = ",".join(columns)
            conflict = write.kwargs["on_conflict"]
            updates = ",".join(f"{c}=excluded.{c}" for c in columns if c not in conflict.split(","))
            sql(f"INSERT INTO validation_stats({column_sql}) SELECT {column_sql} FROM jsonb_populate_record(NULL::validation_stats,'{encoded}'::jsonb) ON CONFLICT({conflict}) DO UPDATE SET {updates};")
        saved = json.loads(sql("SELECT to_jsonb(v) FROM validation_stats v WHERE pair='EURUSD' AND data_source='backtest' AND model_version='2.0-live' AND evaluation_version='published-direction-v1' AND window_days=0 AND population_version='published-calls-v1';"))
        assert saved["t5_directional_calls"] == 2 and saved["t5_win_rate"] == 1
        assert saved["t5_total_calls"] == 4 and saved["t5_missing_evaluation_calls"] == 2
        assert saved["t5_pending_calls"] == 1 and saved["t5_missing_outcome_calls"] == 1
        assert saved["t5_mean_signed_gross_return_bps"] > 0
        assert saved["t5_probability_score_calls"] == 2
        assert saved["t5_rolling_90d_accuracy"] is None
        assert sql("SELECT count(*) FROM validation_stats WHERE evaluation_version='legacy-unversioned';") == "1"
        assert sql("SELECT count(*) FROM validation_stats WHERE population_version='evaluation-records-v1';") == "5"
        # The public view respects caller RLS instead of bypassing it as owner.
        sql("""GRANT SELECT ON regime_calls, validation_log TO anon, authenticated;
            ALTER TABLE regime_calls ENABLE ROW LEVEL SECURITY;
            ALTER TABLE validation_log ENABLE ROW LEVEL SECURITY;
            CREATE POLICY fixture_call_scope ON regime_calls FOR SELECT TO anon,authenticated USING (pair='EURUSD');
            CREATE POLICY fixture_eval_scope ON validation_log FOR SELECT TO anon,authenticated USING (true);""")
        assert sql("SET ROLE anon; SELECT count(*) FROM validation_observations;") == "4"
        assert sql("SET ROLE authenticated; SELECT count(*) FROM validation_observations WHERE pair='USDJPY';") == "0"
        assert sql("SELECT has_table_privilege('anon','validation_observations','INSERT,UPDATE,DELETE');") == "f"
        sql("SET ROLE anon; DELETE FROM validation_observations;", error="cannot delete from view")
        sql((ROOT / "scripts/repair/test-validation-db.sql").read_text())
        print("VALIDATION_DATABASE_VERIFIED")
    finally:
        # DB is a locally generated identifier with a fixed scratch prefix.
        assert DB.startswith("fxrepair_") and len(DB) == 41
        sql(f'DROP DATABASE "{DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
