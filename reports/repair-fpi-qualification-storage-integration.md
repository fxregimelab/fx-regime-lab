# Durable qualification integration — packet27

Packet27 is accepted locally on28 September2026. Full repair goal stays active.

The parent froze docs/FPI_QUALIFICATION_STORAGE_CONTRACT.md before launching disjoint Python writer and SQL ledger workers. Qualification commands retain their pre-I/O identity. The database serializes accepted transitions across scopes, assigns order, checks expected predecessors and captures the exact historical heads for a date resolution. These records remain administrative assertions: they cannot authenticate parser execution or stand in for saved decision reads.

The task-local PostgreSQL17.11 instance initially failed to start without the explicit test options because the default socket directory was absent. No worker ran dependent checks then. The parent restarted it with the existing project socket, port55437 and empty listen_addresses. A real SQL query confirmed all three properties before authorizing the database worker. No Docker/heavy Hermes component or automatic startup was enabled. Parent owns shutdown after scratch-database checks.

Parent review and the deliberate SQL guard-removal negative control passed. No production data or credentials are used; source/parse fixtures are explicitly synthetic. No commit, push or deployment is authorized by this verification.

Parent explicitly reconciled a staging difference with the packet25 execution-trust design: this packet retains administrative ACCEPT intent before the protected verifier exists. It supplies no eligibility bit or consumer. The eventual acceptance/read layer must require exact protected parse verification and observed active release state independently, including for preexisting ledger events. That requirement remains unmet; no test fixture may substitute for production authority.

## Parent timeout counterexample

Actual PostgreSQL17 test: a temporary function with function-local statement_timeout30ms and pg_sleep120ms returned successfully with outer timeout0. The same function failed with cancellation when the outer request timeout was30ms. Marker FUNCTION_TIMEOUT_INEFFECTIVE_CONTROL_VERIFIED. Temporary functions were connection-scoped and no permanent schema changed. The contract now requires an inherited pre-request timeout and a real cancellation control, instead of claiming the function SET arms a total runtime bound. An inherited setting alone cannot authenticate nested-call timer state; deployed connection setup remains required. PostgreSQL documents statement timeout as beginning when the command reaches the server: [client connection settings](https://www.postgresql.org/docs/17/runtime-config-client.html#GUC-STATEMENT-TIMEOUT).

## Independent acceptance evidence

Parent leaf27.1 re-verification passed285 tests, comprising149 writer cases and136 qualification cases; output SHA-256aa972b683bab149cb0db17a33a0d55e5fe1eff71c6ea7fffb499e58f69b34fd4. A separate valid/wrong/valid receipt test confirms that a fully rehashed WITHDRAW event cannot satisfy a submitted ACCEPT command: FPI_QUALIFICATION_WRONG_COMMAND_RECEIPT_CONTROL_VERIFIED. The writer preserves fixed error messages and cancellation. Its preexisting bytes were preserved apart from the new import and function.

Parent leaf27.2 re-verification passed all eight real database groups; output SHA-2562c5a4044de2634a3bb5d99b00ebab4517784a00c796fab1ad7078da07637c17a. An in-memory migration with only its expected-predecessor guard removed failed the same verifier in the order phase, after its strict-input phase passed. On-disk migration unchanged; scratch database removed. Marker FPI_QUALIFICATION_SQL_PREDECESSOR_NEGATIVE_CONTROL_VERIFIED. Full detail: reports/repair-fpi-qualification-db.md.

After interruption, saved successful gates were inspected before any repeat. The native worker handles and matching test processes were absent, so the parent completed the missing database report and reverified current files. Actual PostgreSQL health was confirmed before DB checks. Afterward, zero scratch databases and zero other clients were confirmed; the server was stopped and no-server status verified. No automated startup was added.

Final full pipeline R2 passed with1,781 tests independently collected, output SHA-25633750fad223d55b899db191f86b61b48807eb7493a050b926e3509bed10d97c7. Full Ruff and MyPy225 pass; standalone DB verifier Ruff/MyPy also pass. Frontend unchanged, so packet19 remains its latest receipt. No whole-register, release or forecasting-skill acceptance is claimed.

Final ledger measurement:179 met, six root unmet, zero abandoned; both packet27 leaves VERIFIED, wave complete and exact leases released. Relevant skills supplied concrete checks: Unlazy acceptance/ownership evidence, domain modeling for intent versus eligibility, GitNexus impact coverage review, diagnosing-bugs positive/negative timeout controls, and Humanscope reporting. No completion claim for the full repair objective.
