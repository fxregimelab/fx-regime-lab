# Implementation Spec: [SIGNAL_NAME] Signal Pipeline

## Context
Add a new daily signal for the 3-pair framework. Must pass institutional validity, independence, data availability, and regime relevance tests.

## Files
- CREATE: `pipeline/src/signals/[name].py`
- MODIFY: `pipeline/src/db/writer.py` (if new table needed)
- MODIFY: `pipeline/src/scheduler/orchestrator.py` (add to flow)

## Technical Requirements
- `from __future__ import annotations` at top
- `np.float64` explicitly for all math
- 260-trading-day rolling percentile, clipped [0, 100]
- Causal windows only (today vs t-1 history)
- fetch() → compute() → write via db/writer → return dict
- Module docstring: inputs, outputs, failure modes

## Acceptance Criteria
- [ ] Signal dict has: value, percentile, direction, regime
- [ ] Upsert uses on_conflict='date,pair'
- [ ] All API calls wrapped in try/except
- [ ] `cd pipeline && pytest` passes
- [ ] `cd pipeline && ruff check .` passes
- [ ] `cd pipeline && mypy .` passes

## Execution Plan
1. Scaffold signal module with fetch/compute/write structure
2. Implement 260-day percentile logic
3. Wire into orchestrator at correct position
4. Write tests with synthetic data
5. Run full test suite
