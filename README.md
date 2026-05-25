# FX Regime Lab

**Open-source research infrastructure for transparent macro regime monitoring.**

> ⚠️ **v2.1 Experimental**: Our signals currently have near-random accuracy.
> We publish this openly as part of our research process. See
> [Limitations](https://fxregimelab.com/limitations).

## What This Is

FX Regime Lab is an experiment in radical transparency for macro research:
- Every signal is computed systematically and published daily
- Every call is logged in an immutable ledger before it resolves
- Every limitation is documented publicly
- All code is open-source

## What This Isn't (Yet)

- A profitable trading strategy
- A market-beating prediction model
- A source of investment advice

## Current Status

| Pair | T+5 Gross Accuracy | 95% CI | Net Accuracy (est.) |
|------|-------------------|--------|---------------------|
| EUR/USD | 49.2% | 42.1% – 56.3% | ~47% |
| USD/JPY | 48.3% | 38.2% – 58.4% | ~46% |
| USD/INR | 41.4% | 35.2% – 47.8% | ~36% |

## Roadmap

- **v2.1** (May 2026): Honest metrics, documented limitations, public launch
- **v3.0** (July 2026): Calibrated probabilities, real RR data, Bayesian betas, HMM regimes
- **v3.5** (Q4 2026): Expand to full G10
- **v4.0** (2027): Open standard for transparent macro research

## Agent Quick Start

```bash
# 1. Health check
./scripts/agent-health-check.sh

# 2. Start file watcher (auto-regenerates maps)
./.agent/scripts/file-watcher.sh start

# 3. Read the manifest
.cat .agent/index.json

# 4. Read the code map
jq '.pipeline.fetchers[]' .agent/maps/CODEMAP.json
```

## For Kimi (Strategy)

1. Read `.agent/index.json` — master manifest
2. Read `.agent/maps/CODEMAP.json` — find files instantly
3. Read `.agent/context/HOTFILES.md` — see what's active
4. Read `TASK.md` — current sprint
5. **Plan** → Write Implementation Spec
6. **Delegate** → `./scripts/kimi-cursor-orchestrator.sh --spec spec.md --yolo`
7. **Verify** → `./scripts/cursor-verify.sh --all`

## For Cursor (Execution)

1. Read `.cursorrules` — hard rules
2. Auto-load `.cursor/rules/*.mdc` — conditional rules
3. Read Implementation Spec from Kimi
4. Execute exactly as written
5. Run tests → report results

## Architecture

```
.agent/                          ← Agent hub
├── index.json                   ← Master manifest
├── maps/
│   ├── CODEMAP.json             ← All files + functions/classes
│   ├── SKILLMAP.json            ← All skills
│   └── RULEMAP.json             ← All rules
├── context/
│   └── HOTFILES.md              ← Recently modified
├── templates/                   ← Spec templates
├── decisions/                   ← Decision trees
├── scripts/
│   ├── regenerate-maps.sh       ← Auto-regenerate maps
│   └── file-watcher.sh          ← Background watcher
└── metrics/                     ← Build logs

.cursor/                         ← Cursor config
├── rules/*.mdc                  ← Auto-applied rules
├── skills/*/SKILL.md            ← Cursor skills
├── subagents/*.json             ← Subagent configs
└── delegation/                  ← Queue, logs, sessions

.kimi/                           ← Kimi config
└── skills/*/SKILL.md            ← Kimi skills
```

## Hard Rules

| Rule | Detail |
|------|--------|
| Pairs | EUR/USD, USD/JPY, USD/INR ONLY |
| DB Writes | `pipeline/src/db/writer.py` ONLY |
| AI Calls | `pipeline/src/ai/client.py` (ON HOLD) |
| Immutable | `regime_calls` + `validation_log` append-only |
| CI/CD | Prefect Cloud only. No GitHub Actions. |
| Tests | `pytest` 234 tests + `npm run build` must pass |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/agent-health-check.sh` | Verify system health |
| `scripts/kimi-cursor-orchestrator.sh` | Master delegation pipeline |
| `scripts/cursor-delegate.sh` | Single-task delegation |
| `scripts/cursor-verify.sh` | Test/build/lint verification |
| `scripts/cursor-warmup.sh` | Pre-warm codebase index |
| `.agent/scripts/regenerate-maps.sh` | Regenerate all maps |
| `.agent/scripts/file-watcher.sh` | Background file watcher |

## Maps (Machine-Readable)

| Map | Command |
|-----|---------|
| **CODEMAP** | `jq '.pipeline.fetchers' .agent/maps/CODEMAP.json` |
| **SKILLMAP** | `jq '.skills[]' .agent/maps/SKILLMAP.json` |
| **RULEMAP** | `jq '.rules[]' .agent/maps/RULEMAP.json` |
