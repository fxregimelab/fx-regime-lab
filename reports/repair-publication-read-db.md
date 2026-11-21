# Public immutable signal reads — local repair

The new `live_publication_signals` view lets a public reader fetch the exact signal snapshot by the already selected call ID. It exposes only call ID, pair, date and signal JSON. Rationale, correlation metadata and the call's internal execution fields remain outside this view.

The view includes only live v2 calls for the three locked pairs whose session date is not in the future. A legacy call without evidence has no row. Replacing the mutable `signals` projection cannot alter the snapshot or cause a reader to borrow a different model's inputs.

This is an intentional owner-rights view over a private evidence table. Its fixed projection, source filters and security barrier form the public boundary. All application roles receive SELECT only; the join view is also not automatically writable. The underlying evidence table keeps its row security. Local tests explicitly grant SELECT on that table to anonymous/authenticated roles and verify that direct reads still return no private rows.

The parent ran `python scripts/repair/verify-publication-read-db.py`, then independently reran it through the Unlazy gate. Four grouped real PostgreSQL checks passed: exact version-bound snapshots despite changed projections; live/source/strategy/date eligibility and absent legacy evidence; public fields/write denial; and underlying privacy plus repeated migration. The disposable fixture includes the prior atomic publication migration and all three pairs. The first test attempt expected a permission message but PostgreSQL rejected an INSERT earlier because the join view is not writable. The corrected test accepts either rejection and separately verifies that no write privilege exists.

GitNexus MCP could not read its index version; matching CLI found no existing symbol for this new view. No existing function was changed in this leaf. Runtime health was verified on the task-local PostgreSQL Unix socket before testing. Runtime shutdown and integrated reader checks are recorded in the checkpoint.

These checks do not prove the full historical migration chain, browser rendering or deployed behavior. Python decision-time selection and public query/UI integration are separately owned leaves under `docs/PUBLICATION_READER_CONTRACT.md`.
