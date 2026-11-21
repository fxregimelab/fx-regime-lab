# Price request boundaries

Polygon requests now use the UTC calendar date. Requests-based adapters record retrieval immediately after the response returns, before JSON decoding and our transformation. Yahoo adapters record the download-return time once; all rows in a batch share it, and the asynchronous path captures it inside the download thread. This is application receipt evidence. Yahoo's download already transforms its response internally, so this timestamp is not claimed as the raw network receipt or market publication time.

Provider download and parsing failures log their exception class without interpolating exception text. That prevents request URLs and query credentials in an HTTPError from entering these adapter logs. The outer asynchronous gather also logs only the class of a failed task. Third-party internal logging and other fetcher modules still require their own security review.

The Yahoo frame parser accepts an explicit adjustment flag. Existing live callers retain the True default; unadjusted historical acquisition can pass False without falsely labeling its rows adjusted. No parser timestamp proves a completed market session, no raw-response manifest is created by this change, and no observation becomes a qualified close.

Ten new regressions failed before implementation. They exposed exception-message URL leakage, a local/UTC date mismatch, later parsing clocks replacing the response receipt, inconsistent row receipt times and missing unadjusted metadata support. After the repair, the declared gate passed all 57 focused tests. Scoped Ruff and MyPy passed. MyPy first exposed four test typing defects; they were corrected and the declared gate reverified.

GitNexus reported CRITICAL impact: 33–66 direct indexed dependents across seven processes for the parser and request paths. The graph includes unrelated same-name UI symbols. Actual sync/async callers and archive serialization were inspected; current fallback tests verify compatibility. Integrated regression acceptance is owned by the packet checkpoint. No real credential, provider request, production write or deployment was used.
