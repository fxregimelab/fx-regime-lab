# Atomic publication database repair — leaf9.2

The candidate migration implements one atomic publication entry point. Local PostgreSQL verification is complete for the bounded fixture described below. This is not production acceptance or a rehearsal of the full historical migration chain.

Base source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`. The surrounding repair work remains uncommitted. This packet changes only its assigned migration, fixture, verifier, and this report. It does not read credentials, call Supabase, commit, deploy, start a runtime, or disable a protection trigger.

## Publication behavior

`public.append_regime_publication(p_call jsonb, p_signal jsonb, p_rationale jsonb, p_supersedes_call_id integer default null)` returns a positive integer call ID. A transaction lock on pair/date serializes publications across versions before selecting the full identity: pair, date, data source, strategy version, and model version.

Identical domain payloads return the original ID. A changed call, signal, rationale, or predecessor at that identity raises a conflict requiring a new model version. A legacy identity without evidence is refused. A predecessor must already exist on the same pair/date. The migration never updates or deletes an original observation.

The database computes SHA256 from normalized JSON; numeric forms such as `1` and `1.0` hash identically. Correlation IDs, client write hashes, internal IDs, and creation/update timestamps do not affect that hash. Operational correlation/write-hash values may be stored on the call, but cannot dictate its identity or database IDs. Rationale pair/date and call ID are server controlled. Null rationale produces the same explicit default used by the Python writer.

Each new call receives immutable, complete call/signal/rationale JSON in `publication_evidence`. Only live publications update `signals`. A separate history trigger captures the entire previous signal projection on every UPDATE or DELETE, including direct writes outside the RPC. Those snapshots do not claim to be the original inputs of a legacy call. All call, evidence, rationale, projection, and history changes commit together or roll back together.

Call, evidence, rationale, and projection history UPDATE/DELETE operations are blocked. RPC execution is limited to `service_role`. Direct call/evidence/history writes are revoked from that role and from public/anonymous/authenticated roles; retrospective rationale INSERT remains possible without permitting replacement. Evidence and history have explicit service-role read policies. Security-definer functions use a fixed search path and qualified relations. Insert column names are obtained from PostgreSQL's schema catalog for fixed table names, never interpolated from caller JSON.

The migration drops only old uniqueness keys consisting of pair/date, retaining unrelated indexes and primary keys, then creates the full publication identity unique index. One separately reviewed compatibility repair replaces the exact historical `regime_calls_directional_bias_values` constraint: it accepts both existing `Long`/`Short`/`Neutral` values and current producer `LONG`/`SHORT`/`NEUTRAL` values. The old values remain unchanged. Duplicate historical publication identities abort the migration instead of being deduplicated.

## Fixture and verification

Run from the repository root:

```powershell
python scripts/repair/verify-publication-db.py
```

The verifier uses only the manually started WSL PostgreSQL 17 server at `/home/shreyash/.local/state/fxregime-repair/socket`, port `55437`. It creates a randomly named scratch database and drops it in `finally`. It does not discover configuration or connect to a network database.

The independent fixture includes integer call IDs, every current `RegimeCall` and `SignalRow` dataclass field, complete rationale columns, a legacy call with a title-case directional bias, a legacy rationale, and a preexisting signal projection. No dataclass projection fields are intentionally absent in the final fixture. The verifier checks that coverage against the actual dataclass definitions and feeds the actual Python `writer._publication_request` output into PostgreSQL.

The fixture was checked against `docs/DB_STATUS.md` and the historical foundation, execution-schema, stream-A, blended-Z, regime-category, V2 schema, and v2.1 honest-metrics migrations. It includes the v2.1 `days_since_cot`, `risk_reversal_source`, and `data_quality_notes` fields, the actual regime-category enum, execution enums, conviction/confidence checks, and the original title-case directional-bias check before migration. `z_blended` uses the historical `real` type. The initial migration's UUID IDs differ from the later documented integer deployment schema; this fixture deliberately follows the required integer deployment contract. It does not reproduce unrelated tables, RLS policies, audit triggers, or every historical schema transition.

The successful verifier prints `PUBLICATION_DB_VERIFIED` after twelve grouped checks:

- Migration reapplication preserves original rows and unrelated indexes.
- Publication keeps complete snapshots, applies server rationale identity, and makes semantic retries idempotent.
- Call, signal, rationale, and predecessor conflicts fail; legacy identities are refused; independent model/strategy/source cohorts coexist; replay leaves live signals unchanged.
- Thirty-three malformed payloads and invalid predecessors fail without inserting calls.
- All three pairs publish, caller IDs cannot override server IDs, and null rationale has a deterministic stored default.
- The actual Python writer request fits the schema and retains every dataclass field in evidence; an uppercase directional bias succeeds while the legacy title-case row stays unchanged.
- Failures injected after call insertion and after projection replacement roll back all publication tables.
- Concurrent identical retries converge, changed content conflicts, and separate versions both survive with serialized signal history.
- Direct projection UPDATE/DELETE preserves prior rows; calls, evidence, rationale, and history reject mutation.
- Role execution/write permissions, service reads, and fixed search paths hold.
- Reapplication after publication preserves populated evidence and history.
- Duplicate historical identities abort migration without changing existing rows.

## Remaining acceptance boundaries

Full historical migration rehearsal and a real deployment remain separate gates. In particular, the fixture does not resolve every discrepancy between historical migrations and the documented deployed schema. Existing read paths must select the intended publication cohort now that pair/date can identify several immutable calls. The parent integration owns that reader audit, broader pipeline checks, and release decisions.
