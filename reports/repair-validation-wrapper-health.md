# Validation coverage through the scheduled wrapper

The scheduler now requires one explicit completed validation scan. A completed scan with missing mature outcomes may continue to aggregation and durable health recording, while its final status remains degraded. Missing, skipped, duplicated or failed validation reports are rejected. A bare OK label without scan evidence is no longer accepted.

Seven focused scheduler tests passed. A process-local negative control restored the previous OK-only check and reproduced the original failure for both legacy and staged outputs: the wrapper stopped before aggregation when a completed scan reported missing outcomes. That negative control changed no repository files. The repaired tests verify aggregate execution, the saved degraded status, validation completion bookkeeping and suppression of success heartbeats.

Parent re-verification passed the full wrapper gate (45 tests collected), including the actual local Prefect wrapper/staged integration cases. The integrated pipeline gate passed with 694 tests collected. Full Ruff and MyPy passed, with MyPy checking 183 source files. Both daily flows now return ValidationRunResult coverage evidence. This is local acceptance of the wrapper repair; production execution and source availability remain separate requirements.

GitNexus could not find the new helper in its current index. The single actual caller, run_pipeline, and both return contracts were inspected directly. No production scheduler run, external notice or deployment was performed.
