"""Verify public immutable input reads on the task-local PostgreSQL server only."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "publication_db_fixture", ROOT / "scripts/repair/verify-publication-db.py"
)
assert spec is not None and spec.loader is not None
db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db)


def main() -> None:
    db.sql(f'CREATE DATABASE "{db.DB}";', database="postgres")
    try:
        db.sql((ROOT / "scripts/repair/publication-db-fixture.sql").read_text(encoding="utf-8"))
        db.sql((ROOT / "supabase/migrations/20260927000004_atomic_publication.sql").read_text(encoding="utf-8"))
        migration = (ROOT / "supabase/migrations/20260927000005_publication_signal_read_view.sql").read_text(encoding="utf-8")
        db.sql(migration)
        db.sql(migration)

        expected: dict[int, dict] = {}
        for pair in ("EURUSD", "USDJPY", "USDINR"):
            row = db.publication("visible-v1", pair=pair)
            row[0]["correlation_id"] = "PRIVATE-TRACE"
            row[2]["layer1_reasoning"] = "PRIVATE-RATIONALE"
            call_id = int(db.sql(db.append(*row)))
            expected[call_id] = row[1]
        original_id = min(expected)
        revision = db.publication("visible-v2")
        revision[1]["spot"] = 1.7
        revised_id = int(db.sql(db.append(*revision, predecessor=original_id)))
        expected[revised_id] = revision[1]
        for row in (
            db.publication("hidden-backtest", source="backtest"),
            db.publication("hidden-future", day="2099-01-01"),
        ):
            db.sql(db.append(*row))
        other_strategy = db.publication("hidden-strategy")
        other_strategy[0]["strategy_version"] = "v3"
        db.sql(db.append(*other_strategy))

        # Replacing the current projection must not change either preserved version.
        db.sql("UPDATE public.signals SET spot=9.9 WHERE pair='EURUSD' AND date='2026-09-01';")
        for role in ("anon", "authenticated", "service_role"):
            result = db.sql(f"SET ROLE {role}; SELECT jsonb_agg(to_jsonb(v) ORDER BY call_id) FROM public.live_publication_signals v;")
            rows = json.loads(result)
            assert {r["call_id"] for r in rows} == set(expected), (role, rows)
            for r in rows:
                assert set(r) == {"call_id", "pair", "date", "signal_payload"}
                assert r["signal_payload"] == expected[r["call_id"]]
                assert (r["pair"], r["date"]) == (r["signal_payload"]["pair"], r["signal_payload"]["date"])
            assert "PRIVATE-" not in result
            assert db.sql(f"SET ROLE {role}; SELECT count(*) FROM public.live_publication_signals WHERE call_id=1;") == "0"
            for statement in (
                "INSERT INTO public.live_publication_signals(call_id) VALUES (9999)",
                "UPDATE public.live_publication_signals SET pair='GBPUSD'",
                "DELETE FROM public.live_publication_signals",
            ):
                rejected = db.run(f"SET ROLE {role}; {statement};")
                assert rejected.returncode != 0 and (
                    "permission denied" in rejected.stderr
                    or "not automatically updatable" in rejected.stderr
                ), rejected.stderr
            assert db.sql(f"SELECT has_table_privilege('{role}','public.live_publication_signals','INSERT,UPDATE,DELETE,TRUNCATE');") == "f"
        print("PASS exact call snapshots remain stable across versions and changed current projections")
        print("PASS public roles see only live v2 locked-pair nonfuture evidence; legacy inputs remain absent")
        print("PASS public view excludes private fields and rejects writes for all application roles")

        # Even if a Supabase installation grants SELECT by default, evidence RLS
        # cannot expose the private call/rationale payload through direct reads.
        db.sql("GRANT SELECT ON public.publication_evidence TO anon,authenticated;")
        for role in ("anon", "authenticated"):
            assert db.sql(f"SET ROLE {role}; SELECT count(*) FROM public.publication_evidence;") == "0"
        before = db.sql("SELECT jsonb_agg(to_jsonb(v) ORDER BY call_id) FROM public.live_publication_signals v;")
        db.sql(migration)
        assert db.sql("SELECT jsonb_agg(to_jsonb(v) ORDER BY call_id) FROM public.live_publication_signals v;") == before
        options = db.sql("SELECT reloptions FROM pg_class WHERE oid='public.live_publication_signals'::regclass;")
        assert "security_barrier=true" in options and "security_invoker=false" in options
        print("PASS direct evidence RLS remains private and view reapplication preserves all snapshots")
        print("PUBLICATION_READ_DB_VERIFIED")
    finally:
        assert db.DB.startswith("fxpublication_") and len(db.DB) == 46
        db.sql(f'DROP DATABASE "{db.DB}" WITH (FORCE);', database="postgres")


if __name__ == "__main__":
    main()
