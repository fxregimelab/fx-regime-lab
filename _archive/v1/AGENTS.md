# FX Regime Lab — project context (humans & AI assistants)

This file is the canonical map of the repository. Read it before large edits, refactors, or automation changes.

## Purpose

Daily **G10 FX regime** research pipeline: pull public market data (FX, yields, COT, INR-related series), merge into a master dataset, render a **morning brief** (text + interactive HTML with Plotly/iframes), optionally **deploy** to GitHub Pages as `index.html`. **Public product URL:** [fxregimelab.com](https://fxregimelab.com) on **Cloudflare Pages** (live dashboard + site); GitHub Pages remains a static brief channel until cutover (see [contaxt files/PLAN.md](contaxt%20files/PLAN.md) Phase 0).

Nothing here is investment advice; research and learning only.

## Layout (high level)

| Path | Role |
|------|------|
| `run.py` | Preferred orchestrator: `fx`→`cot`→`inr`→`vol`→`oi`→`rr`→`merge`→`text`→`macro`→`ai`→`substack`→`html`→`validate`→`deploy`. |
| `run_all.py` | **Deprecated** legacy orchestrator (subset of steps + `deploy.py` + `runs/` archive). Prefer `run.py`. |
| `pipeline.py` | Layer 1: FX + yield ETL, spreads, writes `data/`. |
| `cot_pipeline.py` | Layer 2: CFTC COT positioning → `data/`. |
| `inr_pipeline.py` | INR-specific metrics → `data/`. |
| `macro_pipeline.py` | Optional macro helpers (not in default `run_all` chain unless wired elsewhere). |
| `morning_brief.py` | Text brief → `briefs/brief_YYYYMMDD.txt`. |
| `create_html_brief.py` | HTML brief + `charts/*.html` iframes → `briefs/brief_YYYYMMDD.html`. |
| `deploy.py` | Copies latest brief to repo-root `index.html`, rewrites `../charts/` → `charts/`, `../static/` → `static/`, then git commit/push. |
| `scripts/publish_brief_for_site.py` | Copies latest `briefs/brief_*.html` → `site/brief/latest.html` (path rewrites), syncs `charts/` → `site/charts/`, `static/` → `site/static/` for **fxregimelab.com** (Cloudflare). Run in CI before `deploy.py`. |
| `config.py` | Shared constants and configuration. |
| `create_charts_plotly.py` | Plotly chart builders used by the HTML pipeline. |
| `check_latest.py` | Data freshness / sanity checks. |
| `core/` | `paths.py` (`ROOT`, `DATA_DIR`, `BRIEFS_DIR`, `CHARTS_DIR`, `PAGES_DIR`, helpers), `utils.py`. |
| `site/` | Public **fxregimelab.com** shell (UI v2: light editorial + canvas). Includes `brief/latest.html` (published from pipeline), `site/charts/`, `site/static/` copies for same-origin brief; see `docs/FX_REGIME_LAB_UI_PROMPT_V2.md`. |
| `charts/` | Generated interactive HTML fragments + `registry.py`, `base.py`, `workspace.py` (tracked for GitHub Pages). |
| `static/` | CSS/assets referenced by briefs (`static/styles.css` after deploy patch). |
| `logos/` | Brand PNGs (some gitignored exceptions reversed in `.gitignore` for CI). |
| `pages/` | **Standalone** narrative/export HTML cards (Chart.js “FX Regime Lab” style), *not* the daily brief. Built by `scripts/dev/build_*.py`. |
| `scripts/dev/` | One-off builders, phase checks, stress tests, verification scripts (all `os.chdir` to repo root). |
| `docs/` | Long-form planning; **index:** `docs/README.md`; **pipeline ops:** `docs/PIPELINE_AUDIT_AND_OPERATIONS.md` (`G10_FX_FRAMEWORK_MASTER_PLAN.md`, `FX_REGIME_ROADMAP.md`, etc.). |
| `.github/workflows/` | e.g. `daily_brief.yml` — CI pipeline (needs `FRED_API_KEY` secret). |

## Generated / local-only (usually not in git)

Per `.gitignore`: `data/`, `briefs/`, `runs/`, `.venv/`, `__pycache__/`, `.env`. Exception: `charts/` is **intentionally tracked** for Pages. `runs/` may hold `pipeline.log` and bat logs.

## Path constants

Use `core.paths` for anything that needs `ROOT` or standard folders — avoids hard-coding and survives moves of this file’s documented layout.

## Deploy, GitHub Pages, and fxregimelab.com

- **Canonical public site (target):** [https://fxregimelab.com](https://fxregimelab.com) — **Cloudflare Pages** (dashboard `/dashboard`, brief `/brief`, etc.; see PLAN Phase 0).
- **GitHub Pages** (`deploy.py` still can push repo-root `index.html`): `https://shreyash3007.github.io/G10-FX-Regime-Detection-Framework/` — **legacy mirror** for the Plotly brief. **Canonical public product** is Cloudflare (`fxregimelab.com`, `site/`). Sunset GitHub Pages after a sustained period of clean `/brief` + `/dashboard` on Cloudflare (see PLAN Phase 0.8).
- **Source of truth for repo-root HTML:** `index.html` (copy of latest brief with path fixes after `deploy.py`).
- **Brief originals**: `briefs/brief_YYYYMMDD.html` use `../charts/` and `../static/` because they live one level down.

**Orchestrator (`run.py` `STEPS`):** `fx` → `cot` → `inr` → `vol` → `oi` → `rr` → `merge` → `text` → `macro` → `ai` → `substack` → `html` → `validate` → `deploy`. There is no `create_dashboards.py`; charts are produced via `create_html_brief.py` / `create_charts_plotly.py`.

## Standalone pages (`pages/`)

If this repository is published with **GitHub Pages from the repo root**, these files are served under the **`/pages/`** path (for example `…/pages/eur_reconnection_journey.html`), not at the root URL. Update any bookmarks or social posts that pointed at the old root-level `.html` paths.

Builders (run from repo root with `python scripts/dev/<script>.py`):

- `build_jpy.py` → `pages/jpy_correlation_flip.html` (reads `pages/eur_reconnection_journey.html` for embedded logo).
- `build_eur.py` → `pages/eur_reconnection_journey.html` (reads `pages/jpy_correlation_flip.html` for logo).
- `build_usdinr.py` → `pages/usdinr_regime_shift.html` (reads EUR page for logo).
- `build_hormuz.py` → `pages/hormuz_countdown.html` (reads JPY page for logo).

Order matters on a clean clone: ensure template/logo source exists (often run JPY → EUR → USDINR, or copy an existing page into `pages/` first).

## Dev / QA scripts (`scripts/dev/`)

Examples:

- `check_phase1.py`, `check_phase23.py`, `check_phase3.py` — HTML/CSS idempotency and marker checks (invoke `create_html_brief.py`).
- `check_brand_v2.py` — regenerates brief and asserts brand-v2 HTML/CSS markers.
- `stress_test.py` — multi-phase presence checks on latest `briefs/brief_*.html`, generated pair chart files, and retired-workspace guards.
- `verify_html.py`, `verify_full.py` — content checks against **latest** brief (and CSV for `verify_full`).
- `verify_data_supabase_brief.py` — optional last-row CSV vs Supabase `signals` spot-check (manual; requires `.env` for DB).
- `check_counts.py`, `idempotency_diff.py` — legacy/debug helpers (some hardcoded brief dates inside).

All assume they are run as `python scripts/dev/<name>.py` (they set cwd to repo root).

## Optional / auxiliary

- `ai_brief.py`, `notion_sync.py` — integrations; not part of the default `run_all.py` sequence unless you wire them.
- `reports/` — auxiliary outputs if used by local workflows.

## Setup (short)

1. Python 3.9+, `pip install -r requirements.txt`
2. `.env` with `FRED_API_KEY=...`
3. `python run.py` (`run_all.py` is deprecated)

## Maintenance notes

- Prefer **small, focused diffs**; do not rename `charts/` or repo-root `index.html` without updating `deploy.py` and CI.
- README’s narrative is user-facing; **this file** is the structural source of truth after the `pages/` + `scripts/dev/` reorganisation (spring 2026).
