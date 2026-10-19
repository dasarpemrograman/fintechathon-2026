# Verification: implement-export-workspace-with-seeded-demo

Reviewed 18 October 2026 (Asia/Jakarta), local branch `work`, base HEAD `aaeb66d8a553d52c887b339dff17d61ffc2585a9`, including all uncommitted fixes.

**74/74 tasks complete. No outstanding critical issues, implementation warnings, or suggestions established.** Tasks 11.5 and 12.3 have real scoped acceptance evidence. Nothing was committed, pushed, or archived.

## Scorecard

| Dimension | Result |
|---|---|
| Completeness | **74/74 tasks**, all configured artifacts available; **57 added/modified requirements and 85 scenarios** across 11 capabilities have evidence mappings. No removed/renamed requirements or unavailable tracking files. |
| Correctness | **181 backend tests and 918 subtests pass**; successful canonical HTTP coverage **146/146**. All 14 earlier browser journeys have passing evidence; the four Calendar/callback browser regressions were rerun after the fixes and pass. Real Calendar lifecycle and declared source acceptance passed. |
| Coherence | Modular services, canonical contract, tenant authorization, Decimal engines, jobs/outbox, synthetic isolation, and separate live-write gates remain intact. New changes address observed provider normalization and local network behavior. |

## Tasks closed

**11.5 — Calendar:** Real OAuth completed for the dedicated acceptance calendar. The approved single-event lifecycle exercised real insert, discarded-response retry without duplicates, update, external-edit/ETag conflict, approved deletion, and grant revocation. Event cleanup was verified; the connection is revoked, encrypted credentials were removed, future app sync returns 409, and the internal timeline remains intact. Google's linked-app search shows no Fincathon grant. General Calendar writes remain disabled.

The first run found a real defect: Google returned an equivalent instant with a different UTC offset, which strict JSON equality treated as a conflict. The fix compares aware instants while preserving timezone, all-day, ownership, projection, privacy, and reminder semantics. Payloads now explicitly disable reminders and use private visibility and transparent availability. The rerun passed insert/retry/update/conflict/delete. An extra immediate-token-invalidation harness assertion was not met after revocation; that raw failure is retained. Follow-up Google grant-list and local refusal checks complete the specified revocation contract; no unobserved HTTP 401 is claimed.

**12.3 — sources:** Brave, FX, and Gemini pass their real application adapters. The manifest declares precise test goods for Indonesia→Singapore coffee (HS6 candidate 090111), China→Singapore bare FR-4 printed circuit boards (853400), and Kenya→Germany plain dried mango (080450). **9 real searches, 18 fetched/parsed sources, and 3 FX pairs** are retained with URL/time/hash evidence. Review includes three market observations, three finance-fit comparisons, and twelve rule, logistics, and nomenclature assessments.

The review rejects the PCB prototype promotion as a 1,000-board comparator, distinguishes ICO indicators from executable coffee quotes, and keeps the dried-mango FOB range indicative. Finance review preserves LC, credit-line, pre/post-shipment, and unknown-pricing restrictions. No unsupported tariff rate, shipment clearance, freight quote, lender approval, or fresh-fruit certificate requirement is invented.

See [live-acceptance-results.md](../../../../docs/live-acceptance-results.md) for source links, exact goods, scope limits, and the Calendar history. [verification-evidence.md](verification-evidence.md) maps requirements and scenarios.

## Fresh checks

| Check | Result |
|---|---|
| Full Python/PostgreSQL suite | **181 passed; 918 subtests passed**. One existing Starlette/httpx deprecation warning. |
| Successful canonical operations | **146/146**, captured from the full suite. |
| Calendar browser regressions | **4 passed** after the fixes. Earlier full browser run: 13 passed plus the isolated Calendar helper rerun passed. |
| Contract | **146 operations; 14 request examples; 10 response examples** validated. |
| Strict OpenSpec validation | Active change and two main specs: **3 passed, 0 failed**. Apply state: `all_done`. |
| Public retrieval regressions | **9 tests / 7 subtests passed**, including dual-stack choice, mixed private-address refusal, TLS/proxy behavior, PDF recognition, and rejection of other binary content. Included in the full suite. |
| Source acceptance | **9 searches / 18 source pages / 3 FX pairs passed**, followed by hash-backed applicability/comparison review and a successful model response. |
| Build/types/fixtures | Pinned API image rebuilt after code fixes. Prior production web build, fresh generated-type equality, and all 10 fixture hashes passed; web source/wire contract unchanged. |
| Offline lifecycle | Earlier isolated internal-network demo journeys, blocked public egress, restart fingerprints, and reseed fingerprints passed. Relevant browser regressions rerun on that stack. |
| Whitespace/syntax | `git diff --check` and compilation of changed adapters/acceptance scripts pass. |

The fetcher validates every DNS answer and prefers public IPv4 on dual-stack WSL, where public IPv6 answers may lack a usable route. A bounded PDF served as generic binary is accepted only with its PDF signature; other binary content is rejected. TLS hostname verification, public-IP checks, redirect validation, and size/time limits remain enabled.

## Evidence and limits

Sanitized artifacts: `calendar-live-acceptance.json`, `calendar-grant-revoked.png`, `acceptance-source-probes.json`, `acceptance-source-review.json`, and `live-provider-probes.json`. Private logs include `.local/live-closure-tests.log`, `.local/live-closure-operation-coverage.json`, `.local/live-closure-calendar-browser.log`, source probe/retry logs, and the failed first Calendar attempt. Credentials and original source bodies remain private and excluded from the source backup.

Acceptance covers the three illustrative goods/routes in the manifest, not a customer's unstated specifications or universal regulatory coverage. Commercial rates, eligibility, national classification detail, and shipment predicates can remain explicit unknowns. The extra Calendar access-token timing observation is recorded. No fresh remote CI or disaster-recovery restore is claimed, and no production-readiness claim is made.

**Assessment: both acceptance blockers are resolved. Ready for archive review; not archived.**
