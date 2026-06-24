# FX Regime Lab — v1.0 Public Launch Checklist

> Aligned with `IDENTITY.md`: public macro research platform, real data only, institutional terminal aesthetic.

---

## Pre-Launch Blockers (Must Fix)

- [x] **Rolling 90-day accuracy computation** — backend + DB migration
- [x] **Rolling 90-day accuracy display** — landing page + performance page + terminal
- [x] **Macro event AI briefs re-enabled** — orchestrator no longer skips
- [x] **SEO foundation** — sitemap.xml, Schema.org Dataset structured data
- [x] **Apply DB duplicate-fix migration** — done via Management API
- [ ] **Re-deploy Prefect** — `cd pipeline && python -m prefect deploy --prefect-file prefect.yaml` to inject env vars
- [ ] **Verify next scheduled run** — 09:00 UTC daily, monitor for errors

## Data Quality Gates

- [ ] **14 consecutive days of pipeline runs without errors**
- [ ] **EUR/USD 90-day accuracy visible and updating daily**
- [ ] **All 3 pairs have 30+ days of validated history**
- [ ] **No NULL epidemic in signals table** (spot, cross-asset fields populated)
- [ ] **Validation engine running daily** (T+5/T+20 backfill complete)

## Frontend Verification

- [x] **Landing page** — 90-day accuracy ticker live
- [x] **Performance page** — rolling accuracy columns in PairBreakdownTable
- [x] **Terminal page** — 90D accuracy in SignalCard
- [x] **Sitemap** — `/sitemap.xml` route working
- [x] **Structured data** — Schema.org Dataset JSON-LD on landing page
- [ ] **OG images** — social preview cards for `/`, `/terminal`, `/performance`
- [ ] **Lighthouse score ≥ 85** on mobile (performance, accessibility, SEO)
- [ ] **Responsive audit** — no horizontal overflow, readable on 375px width

## Discoverability

- [x] **robots.txt** — allows indexing of public pages, blocks `/terminal/` for generic crawlers
- [x] **sitemap.xml** — all public routes included
- [ ] **Google Search Console** — submit sitemap, verify ownership
- [ ] **LinkedIn/Twitter preview cards** — test with debugger tools

## Post-Launch Monitoring

- [ ] **Daily accuracy alert** — Slack/email if EUR/USD 90-day drops below 50%
- [ ] **Pipeline failure alert** — Slack + email on any run error
- [ ] **Weekly accuracy review** — manual check every Monday

## Documentation Updates

- [x] **AGENTS.md** — test count updated (878+), success metric added
- [ ] **TASK.md** — update sprint status to "v1.0 Launch"
- [ ] **README.md** — public-facing description for GitHub visitors

---

*Created: 2026-05-15*
*Next review: after 14 consecutive successful pipeline runs*
