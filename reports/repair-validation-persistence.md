# Validation persistence repair — 27 September 2026

This packet repairs local validation persistence. It does not certify a production migration, rebuild historical results, or establish forecasting skill.

Base revision: `9fa150538d08ab5a2a6c587976552944f47a724d`. The shared checkout is now `codex/frontend` at the same commit; the reflog records a switch from `repair/evidence-contracts`. Existing changes were preserved. No commit, push or production write was made in this packet.

## What changed

`write_validation_row` now calls one PostgreSQL function. It requires a persisted call ID and uses `published-direction-v1`, the scoring definition declared beside the canonical calculator. Missing migrations and RPC errors propagate. The writer no longer drops unknown columns or marks an old score replaced before making a separate insert request.

The database function locks the published call before reading its current evaluation. It checks the call's identity, copies its published metadata, rejects unknown payload fields and prevents changes to a completed horizon. A later horizon creates a replacement row inside the same transaction. Repeated identical writes return the existing row. If insertion fails, supersession rolls back too.

Old rows retain `legacy-unversioned`. The repair does not relabel their source, change their scores, or replace their current-row flag. New and old evaluations can coexist under different evaluation versions. Current validation and aggregate readers select the canonical version explicitly and fail on incompatible schemas instead of interpreting legacy fields as new scores.

The forward migration restores missing prediction fields, adds horizon-specific net fields and replaces the broken immutability trigger with a whole-record comparison. Only the false-to-true supersession flag can change; added columns receive the same protection. The new privileged function can be called by `service_role`, not `PUBLIC`, `anon` or `authenticated`.

Integration review also corrected batch payloads: dates are JSON strings, deleted `validation_date` is absent, and database-generated timestamps and supersession state are no longer sent by the caller.

## Evidence

Before the writer change, eight of nine new regression cases failed. The passing case already checked ordinary exception propagation. The updated tests exercise the single RPC, identity and version rejection, no lossy fallback, and evaluation-version read filters. Original tests that asserted separate HTTP update/insert calls were replaced by this stronger contract and actual database checks.

`scripts/repair/verify-validation-db.py` creates a uniquely named scratch database on a task-specific Unix socket and deletes only that scratch database afterward. It verified:

- Applying the forward migration twice preserves existing evidence.
- Legacy and corrected evaluations coexist; published source and model metadata are copied without claiming their historical provenance was audited.
- Repeated writes are idempotent. Wrong IDs, pair, metadata, version and unknown fields fail.
- Editing or deleting a score, changing a completed horizon, or reversing supersession fails.
- An injected insert failure rolls back supersession, leaving the original current row readable.
- Two database connections writing different horizons retain both. The first transaction emits its result while holding the parent lock before the second write begins.
- Neutral calls have null correctness, Brier and hypothetical net payoff.
- Anonymous and authenticated roles cannot execute the RPC; the service role can.
- The actual batch producer and Python writer produce a payload accepted by the real SQL function.

Successful runs emit `VALIDATION_DATABASE_VERIFIED`. The Unlazy leaf records command fingerprints and parent re-verification. This is an integer-ID, post-cleanup schema fixture based on repository documentation, not a clone of production or a full historical migration replay.

## Runtime and remaining boundaries

Docker Desktop was started manually but its backend exited before a healthy engine was available. No Docker-dependent check was accepted. WSL had PostgreSQL clients only. PostgreSQL 17.11 was downloaded from its configured official APT repository and extracted into `/home/shreyash/.local/state/fxregime-repair`; no package service or automatic startup was installed. A foreground server was started on a local Unix socket, with no TCP listener. SQL confirmed its version and health before testing. Stop the temporary process after all local database checks.

L02 and L03 remain open beyond this packet. Atomic publication of regime calls, other privileged database functions, the incomplete historical baseline, production constraints/permissions, and a migration rehearsal against a sanitized production schema still need work. The new migration must precede use of this writer. Public readers must select and label evaluation cohorts before deployment; this code must not be deployed independently of that repair. Source/model selection within the canonical evaluation cohort is also still open under V07. A copied `live` label is not proof of point-in-time availability.

Existing formulas and cost assumptions are versioned, not statistically validated by these persistence checks. Research calibration, market calendars, immutable historical reconciliation and future observation requirements remain in the repair register.
