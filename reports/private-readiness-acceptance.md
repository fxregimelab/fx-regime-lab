# Private desk request-time freshness review

1 October 2026. This bounded change checks the age and structure of saved research when the authenticated API is requested. It holds stale candidates without changing the saved report. It does not qualify the strategy or create a trade.

The old API served a six-day-old candidate without an operating freshness assessment. A deterministic endpoint control failed before the change. The new pure assessment requires aware UTC report/context clocks, a maximum age of 48 hours, the complete declared universe, and consistent daily observation dates. The price date must equal the preceding completed UTC weekday. This is a conservative cadence assumption, not a verified FX session or holiday calendar. A global report/context failure holds the desk; a pair-only price failure holds that pair.

The API clears direction, the UI's alternative bias field, execution levels and numeric probability/return fields for held candidates. It preserves historical results and original saved bytes. Unreadable or structurally corrupt reports return a generic 503. Export uses the enclosing pair identity. Refresh failure remains visible separately from data age.

Independent agent review found four defects in the first integration: the alternative bias escaped the hold; malformed portfolio rows could crash export; a nested trade could override its pair; and partial freshness hid a failed refresh. Seven negative controls reproduced these failures, then passed after correction. Additional malformed-history controls caught three earlier failures. The final correction review reported no remaining consequential finding within this scope. This is bounded code review, not human source labelling or strategy acceptance.

Final direct verification: **99 focused tests passed**, **2,600 full pipeline tests passed**, Ruff passed, and MyPy passed on **263 source files**. The final checks transcript is [private-readiness-checks.txt](private-readiness-checks.txt), SHA-256 `f7fdf90d514c2fad7ee26bdbe2349f3da231df4aaa2213ae09cc055cbb1ad5ff`. Offline replay reproduced daily/reference/session/bid-ask, vintage/release, portfolio and policy evidence in 15.15 seconds, with no network or AI call.

The existing manual launcher restarted the idle service once. PID **12220** serves **http://127.0.0.1:8765/** on loopback. Real HTTP checks confirmed unauthenticated 401 responses, authenticated report/status, invalid-CSRF 403, 2,000 CSV rows and post-logout 401. Browser verification showed CURRENT with the text “Input age checks pass; this does not validate a trade.” All seven saved candidates remain ABSTAIN with unavailable probabilities. No paid refresh was requested.

Runtime evidence: `.private-fx/readiness/baseline.json`, SHA-256 `01a08f3cdf519558482c3960cad71a8957aab5261b3259b96acf7b2fcd3d7e1c`; `.private-fx/readiness/after.json`, SHA-256 `21289f5c873802b9239cd8dd6804acc55ef4fd584810484e6b38dc9f5a9573ba`. The saved report remains `a15080e656b5ee021855719a116d6293ddf0bf5f7a2819389e52db08b9377f43`. UI, TASK, README, engine and report orchestration remained unchanged during this packet.

Final source hashes:

| File | SHA-256 |
|---|---|
| readiness.py | 9258e307fbcb27bca75a0b46c9d45806edffe17f3ae2dff3fef4e6b4dd50d15b |
| api.py | f8fc19e75cc0c10dd83495944a6049094e553198612b6a740317728cd4141d16 |
| test_private_desk_readiness.py | 286fab972c6f83801b2025ba2a7c4163ab29f436697e6fbb0cd16a3a27812a99 |
| test_private_desk_readiness_api.py | c8b24035e3b310a2ccca8161c50ad9aab9c869eb618c1cf678258b7b6d8d0c64 |
| test_private_desk_api.py | dc8a91df605886efcede602a151f4f79281abc780b4f83e0797c1c645592b7ab |

GitNexus could not read the index because of a database reader/version mismatch. Graph impact remains unknown. The shared checkout's aggregate CLI scan reported CRITICAL scope across unrelated changes; it does not certify this packet's safety. Private endpoint callers, UI fallback fields, export and CLI paths were traced directly. No commit, push, deployment, migration, production write, broker order or heavy-runtime startup occurred.

The Unlazy ledger records **two manual gates met and four formal gates pending**, with no abandonment. Direct checks are distinct from checker certification. The [Unlazy skill](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) says: “Only the user's explicit, inspected approval may cross that boundary.” No checker approval was fabricated; implementation and direct verification continued within the owner's authorization.

Remaining limits: an idle browser does not poll this assessment and needs another request/reload; refresh jobs remain in memory; a forward paper journal is not added; full source-hash replay is separate from request-time structural checks; holidays and exact market-session completion are not certified. R1–R5 and public repairs remain open.

The owner's latest amendment restores USD/JPY, retains EUR/GBP as an additional research cross, and asks for 3–5 entries per week, at most five concurrent positions and at most two positions in a correlated risk group. That expansion and measured risk/frequency/hedge research are the next packet. This receipt describes the seven-pair checkpoint before that amendment is implemented.
