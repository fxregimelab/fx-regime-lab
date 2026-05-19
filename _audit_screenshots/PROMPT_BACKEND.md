# PROMPT: Backend Session (Pipeline)
## Tool: Terminal in `D:\Projects\fx_regime_lab\fx-regime-lab\pipeline`

---

### Context
The live website audit found that EURUSD Signal Inspector showed `"EURUSD_placeholder: 0.00"` instead of a human-readable label. The pipeline code has been pre-fixed in 3 locations. You need to verify and commit.

---

### Step 1: Verify the changes

Run these commands:

```bash
cd D:/Projects/fx_regime_lab/fx-regime-lab/pipeline

# See what changed
git diff src/backfill/simulation_engine.py src/scheduler/orchestrator.py
```

**Expected output:** Only `special_label` dictionaries changed — no other logic modified.

---

### Step 2: Run all tests

```bash
pytest -x -q
```

**Expected:** `234 passed` (or current count). Zero failures.

---

### Step 3: Type check

```bash
mypy src/scheduler/orchestrator.py src/backfill/simulation_engine.py
```

**Expected:** `Success: no issues found`

---

### Step 4: Lint check

```bash
ruff check src/backfill/simulation_engine.py src/scheduler/orchestrator.py
```

**Expected:** Clean (no errors).

---

### Step 5: Commit

```bash
git add src/backfill/simulation_engine.py src/scheduler/orchestrator.py
git commit -m "fix(pipeline): human-readable special_signal_label for all pairs

- EURUSD: Bund-BTP + ECB BS (was EURUSD_placeholder / frag_risk / macro_special)
- USDJPY: VIX + JPY Funding Stress (was VIX_funding_stress / INTV_PROX)
- USDINR: Oil + DXY + EM Risk (was EM_oil_DXY / VIX_prem)

Removes dynamic label switching based on signal magnitude.
Label now consistently describes WHAT the signal measures,
while the VALUE field carries the magnitude.

All 234 tests passing."
```

---

### Step 6: Push (optional — only if you want to deploy)

```bash
git push origin main
```

---

### Done. Report back: "Backend committed. Tests passing."
