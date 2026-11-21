# Private readiness module review

Contract: `docs/PRIVATE_READINESS_CONTRACT.md` revision 2, 1 October 2026. This review covers only `pipeline/src/private_desk/readiness.py` and `pipeline/tests/test_private_desk_readiness.py`.

## Result

The pure readiness assessor is implemented and its focused gate passes. It accepts an offset-aware decision clock, validates the saved report without mutating it, and returns only JSON-safe data. Global schema, universe, row-structure, report-clock and context-clock failures set `global_hold` and hold the desk. Daily price failures stay with the affected pair. The overall status is `CURRENT`, `PARTIAL`, or `HOLD` as required by revision 2.

The completed-bar rule uses the previous UTC calendar day and walks Saturday or Sunday back to Friday. It is deliberately conservative. It does not certify an FX provider session boundary or a holiday calendar. A holiday can therefore produce a hold.

The assessor reads no file, environment variable, network service, database, model, or runtime state. Its imports are limited to `__future__`, `datetime`, `re`, and `typing`. Docker and the heavier Hermes runtime were not needed or started.

## Controls covered

- `schema_version == private-fx-v1` and the canonical seven-pair universe are required.
- `pair_reports` must contain exactly one object per pair; missing, duplicate, foreign, malformed, or extra rows cause a global hold.
- `generated_at` and `current_context_updated_at` must be offset-aware, no later than the decision clock, and no more than 48 hours old. Exactly 48 hours is accepted.
- Each pair requires `data_coverage.status == VALID`, interval `1d`, and matching canonical `candidate.as_of` and `data_coverage.last_bar` dates.
- A date after the completed cutoff is incomplete; an older date is stale. Both hold only that pair when global controls pass.
- `weekday_lag` counts weekdays in `(observed, expected]`. The calculation is constant-time over full weeks plus at most six residual days, so a year-1 to year-9999 negative control does not walk millions of dates.
- Malformed source dates are returned as `null`, not echoed. Unknown or malformed clocks produce `null` age rather than zero.
- Candidate status, direction, probability and expected return are neither promoted nor rewritten. The input remains unchanged.

## Direct verification

Run from `D:/Projects/fxregimelab/pipeline`:

```text
python -c "import subprocess,sys; r=subprocess.run([sys.executable,'-m','pytest','tests/test_private_desk_readiness.py','-q']); sys.exit(r.returncode) if r.returncode else print('PRIVATE_READINESS_MODULE_OK')"
49 passed in 0.16s
PRIVATE_READINESS_MODULE_OK

python -m ruff check src/private_desk/readiness.py tests/test_private_desk_readiness.py
All checks passed!

python -m mypy src/private_desk/readiness.py tests/test_private_desk_readiness.py
Success: no issues found in 2 source files
```

The tests include current and exact-48-hour controls; non-UTC offsets; missing, naive, stale and future clocks; wrong schema and universe; missing, duplicate, foreign and malformed rows; unavailable coverage; wrong intervals; malformed, mismatched, stale and incomplete dates; weekend cutoffs; all-pairs hold and one-pair partial states; input immutability; JSON serialization; unchanged abstention; and the giant date-span guard.

## GitNexus and manual trace

Impact analysis was attempted before creation for `assess_readiness`, `_parse_clock`, `_parse_date`, `_expected_completed_bar_date`, `_weekday_lag`, and `_hold_reason`. Each target was absent from the current index and returned risk `UNKNOWN`; this is not evidence of graph safety.

After implementation, `gitnexus detect-changes --repo fx-regime-lab --scope all` reported 99 changed files, 740 changed symbols, 293 affected processes, and critical repository-wide risk. The shared checkout already contained those broad changes, and the new untracked files are not isolated by that result. No critical risk is attributed to this leaf from that aggregate scan.

Manual trace: `assess_readiness` is the only public entry point. It calls five private helpers in the same module and uses standard-library types only. The focused test module imports and exercises the entry point directly. API integration is owned and reviewed by root; it was not edited here.

## Independent reread

Contract reread: the output fields, global-versus-pair scope, exact 48-hour boundary, UTC weekday cutoff, immutable input and JSON-safe response match revision 2.

Bug hunt: unexpected report and nested field types fail closed without reading or leaking provider content. Future clocks remain visible as negative ages while holding globally; malformed clocks remain `null`. Malformed dates are sanitized to `null`. The decision clock rejects naive or impossible earliest-calendar values rather than inventing a cutoff.

Polish and performance: reason codes are stable and paired with plain messages. Global reasons stay in `reasons`; pair reasons stay in the corresponding `pair_checks` row. Weekday lag is bounded independently of the date span.

## Final hashes

```text
pipeline/src/private_desk/readiness.py
9258e307fbcb27bca75a0b46c9d45806edffe17f3ae2dff3fef4e6b4dd50d15b

pipeline/tests/test_private_desk_readiness.py
286fab972c6f83801b2025ba2a7c4163ab29f436697e6fbb0cd16a3a27812a99
```

## Remaining limits

This result is a focused module self-check. It does not accept the API projection, saved-byte preservation, authentication, CSRF, export, service restart, live endpoint behavior, full pipeline suite, provider timing, holiday handling, forecasting quality, model success, profitability, R5 completion, deployment, or automatic Unlazy approval. Gate G2 and root integration remain subject to independent review.
