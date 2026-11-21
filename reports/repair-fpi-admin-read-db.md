# Saved administrative FPI reads: database verification

These results are from a disposable local PostgreSQL 17 database. The parent started and checked the socket-only runtime. The verifier drops its database in a finally block. No production data, provider request, credential, deployment or consumer activation was used.

Migration 14 adds private immutable policies and saved reads. The capture RPC uses a decision lock, committed retry lookup and one evidence/INSERT statement. Its sampled clock, membership scope, diagnostics, originals, heads and witnesses share that statement snapshot. Every result remains UNVERIFIED and ineligible.

The downstream audit inspected migrations 10–13, original capture/parse verifiers, the existing reference builder and qualification-v2 codec, central writer entry points, the legacy selector and staged signal consumer. Existing writer, scheduler/staged selection and replay meanings remain unchanged. New RPCs and helpers were absent from GitNexus: impact UNKNOWN; no rebuild of its index. Private helper/table grants and immutable owner/application behavior are exercised below; no prior grants were weakened.

Migration SHA-256: `fd659bc33ea8f637f43a4904c9b2dfd4fb5f35659945b72e60168c0a413352fe`.
Verifier SHA-256: `81c222c995aef179cb135228358fa02d06c4e3a277667f9a712c4f1248d38814`.
Retained-read/retry checks: 65. Expected SQL refusals: 51.

## Executed database scenarios

- SR01-04,15,22: pinned empty complete/reference/view bytes, independent original references, complete endpoints/parsers, stale sentinel and immutable retry
- SR08-09,19: deterministic clock failures, year bounds/clamping, corrupted projections/documents rejected
- SR20-22: strict input/refused authority, inherited timeout/isolation, private helpers, immutable owner/service boundaries and populated reapply
- SR05-06: Monthly lower-bound support without alternative expansion; both closed diagnostic boundaries, old candidate-capture failure and nonrecursive failure-only capture
- SR11,14: equal/decreasing ordinal history, current plus historical resolution witness closure, explicit absence and future-event clock refusal
- SR16-17,25-26: all eleven dimensions at bound and over bound, immutable overflow retry, decoder guard positive control, staged precedence and actual plans
- SR12-13,15,18,24: observed transaction/decision barriers, atomic full parse visibility/rollback, concurrent identity, actual cancellation and same-identity recovery
- SR07,10,12,18: old-stored uncommitted failures with both scope outcomes; withdrawal lock independence; within-statement committed parse exclusion; read-time cancellation/rollback/retry
- SR17: actual 100KB/200KB/1MB valid artifact timings, twelve-parser shared capture and counted single validation per original

SR19 covers authoritative SQL projection/original corruption here. Returned-row omission, forged Python types and provider pagination in SR19–20 belong to codec/writer integration. SR23 is the parent's independent negative control. This leaf does not claim those separate gates, a live read's origin, trusted execution/acquisition or usable FPI features.

## Measured bounds and plans

Each listed fixture bound passed exactly, then failed at bound minus one with the expected dimension and without partial data. Capped count probes report AT_LEAST; complete bounded unions and byte sums report EXACT. Production limits remain those in the contract. Reduced limits are scratch migration text only.

```json
{
  "fixture_bounds": {
    "ARTIFACTS": 9,
    "CANDIDATES": 5,
    "CAPTURES": 7,
    "EVENTS": 3,
    "HEADS": 12,
    "MANIFEST_BYTES": 21204,
    "ORIGINAL_BYTES": 30772,
    "PARSES": 9,
    "QUALIFICATION_BYTES": 5194,
    "REFERENCE_BYTES": 9205,
    "SUPPORT_MEMBERSHIPS": 5
  },
  "plans_timings_counters": [
    {
      "case_only_control_rejected": true,
      "guarded_decoder_plan_sha256": "49711f4658eaec4c25ac70139e3648662c113d3fdd060164b634914d6b284b05"
    },
    {
      "execution_ms": 80.006,
      "plan_sha256": "d4025a2903cfd67267061671f112f7f577def0fe8d301538f464200f690398ff",
      "planning_ms": 7.845
    },
    {
      "actual_index_used": true,
      "index": "fpi_admin_membership_date_id",
      "plan_sha256": "d2ab64afe7d6c23d0c57702465cd4203066436bd443bdb90fb13214204b6ed2f"
    },
    {
      "actual_index_used": true,
      "index": "fpi_admin_failure_time_id",
      "plan_sha256": "c09782f6ed6004d594f39ca372f284fbf0e665c80cd01e7954b043edc2a33a2b"
    },
    {
      "valid_artifact_body_bytes": 100000,
      "validation_wall_seconds": 0.132
    },
    {
      "valid_artifact_body_bytes": 200000,
      "validation_wall_seconds": 0.1347
    },
    {
      "valid_artifact_body_bytes": 1000000,
      "validation_wall_seconds": 0.3283
    },
    {
      "max_calls_per_original": 1,
      "unique_original_validations": 58
    }
  ]
}
```

Canonical golden hashes: COMPLETE empty manifest `4fbffecbbc0f2d14a9d7277a129a13027621b2faeb6e7bb58cf9e6a3d8a4e930`; ARTIFACTS overflow manifest `9d7d848b2d447258744b736143c945e4fca4e2c40215ce42e05de68cd989e3b4`. Expected objects are authored from original fixtures independently of SQL output.

The G1 ledger records its actual command result. G2, cross-language loader integration, broader repair acceptance and release remain the parent's work.
