# A01 — Public share route repair

Source revision: `9fa1505`; current shared working branch: `codex/frontend`  
Scope: `web/src/pages/api/linkedin-alpha-hook.ts`, `web/src/components/ui/desk-card.tsx`, `web/src/lib/regime-share.ts`, two focused tests, and this report.

## Finding

The public `POST /api/linkedin-alpha-hook` route accepted an anonymous request and used the owner's `OPENROUTER_API_KEY` to call a remote model. At the source revision, the key was read at `web/src/pages/api/linkedin-alpha-hook.ts:23-25`, the remote request ran at lines 38-52, and unverified model prose was returned at lines 62-71. There was no authentication, rate limit, or request budget in the route, so any visitor could consume server-funded model capacity. The model could also add prose or numbers that were not present on the published card.

GitNexus reported one direct API consumer and low route risk. `DeskCard` has one direct caller, `CompareView`, in the compare-page flow. The old `linkedinCardData` prop was not supplied by any current caller; the current caller supplies the displayed pair, spot, confidence, regime, and dominance data directly.

## Repaired behavior

- The share button builds a deterministic note in the browser from values already displayed by `DeskCard`, then writes it to the clipboard after the user's click.
- The formatter accepts only EUR/USD, USD/JPY, and USD/INR. It validates a bounded plain object, rejects extra fields, arrays, control characters, HTML delimiters, non-finite or out-of-range numbers, and any URL other than the pair's canonical HTTPS page.
- Optional numeric lines are omitted when the card does not supply those values. Spot, confidence, and dominance use the same display precision as the card.
- The note identifies the output as public macro research and does not create a squeeze narrative, recommendation, or new numeric claim.
- `POST /api/linkedin-alpha-hook` now returns `410 Gone`. Other methods return `405 Method Not Allowed`. Both paths set `Cache-Control: no-store, max-age=0`; the route contains no environment-key read and no network call.
- No API token is sent to the browser. The action does not publish or send data to an external service.

## Verification

Run from `web`:

```text
node --version
v22.15.0

node --experimental-strip-types --test tests/regime-share.test.ts tests/linkedin-route.test.ts
# tests 6
# pass 6
# fail 0

npx tsc --noEmit
exit 0; no diagnostics

npx biome check src/pages/api/linkedin-alpha-hook.ts src/components/ui/desk-card.tsx src/lib/regime-share.ts tests/regime-share.test.ts tests/linkedin-route.test.ts
Checked 5 files. No fixes applied.
```

The route regression test installs a throwing `globalThis.fetch`, sets `OPENROUTER_API_KEY`, invokes POST, and proves the result is `410` with zero fetch calls. It also checks the GET policy and no-cache headers. Formatter tests cover the canonical output, absence of invented numeric lines, and rejection of a fourth pair, a `javascript:` URL, arrays, HTML, unknown fields, invalid confidence, and incomplete dominance data.

GitNexus `detect_changes` reported high risk for the whole dirty worktree because other active repair leaves modify validation, backfill, and database paths. This leaf's indexed frontend impact remains the previously reported low-risk `DeskCard` compare-page flow. No files outside this leaf's ownership were changed here.

## Limits

This is source and local test evidence. It does not prove deployed behavior, a production HTTP response, browser clipboard permissions, or visual acceptance. The full frontend build and full-repository checks remain with the parent repair. No deployment, external publishing, database write, commit, or push was performed.
