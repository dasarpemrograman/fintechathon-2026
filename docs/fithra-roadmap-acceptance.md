# Fithra roadmap acceptance

18 October 2026, branch `feat/fithra-roadmap-ready-tasks`, starting commit `6a67924`. This is a fresh takeover of the existing implementation. Numbered checks below record technical acceptance; package status remains **In review** until Wisa accepts the handoff. R07.4 and the final R19.4 dependency gate remain open.

## Evidence policy and readiness

The current specifications under `openspec/specs/` and `api/openapi.yaml` define acceptance. Both archived proposals, designs, task lists and verification reports were read as implementation context. The 16/17 October missing-credential findings and earlier 18 October failures are historical. [The latest live report](live-acceptance-results.md) accepts only the three declared coffee, bare-PCB and dried-mango lanes and the cleaned-up Calendar lifecycle. Those provider checks were not repeated here; normal Calendar writes remain disabled.

Readiness was assessed per subtask. R01 uses the reproduced local runtime. R04/R16 use the existing R18 command/job guarantees, exercised by HTTP replay, recovery and metering tests. R07 uses R04 plus R05 source evidence and R06 calculation interfaces, all covered by the fresh regression suite. R10 uses immutable analysis inputs, R08 cash and R09 stress regressions. R13 uses the existing requirement, cash, artifact and R15 timeline interfaces. No unfinished implementation owned by Wisa or Faiz was added to unblock these tasks.

R19 fixture inventory, lifecycle reproduction and reset tests can run independently. Final integrated acceptance still requires the cross-owner handoff and R17 recovery evidence listed below. Another owner's unchecked box alone was not treated as a missing dependency.

## Fresh verification

Executed against the feature code and regression tests through `684b3dc` (auth `3c5dd9d`/`dcc635e`, extraction `57cad58`/`684b3dc`, usage `debaf70`, numeric UI `078399d`, Compose journey `48c36c8`), using Python 3.12.14, Node 24.19.0, uv 0.12.23, PostgreSQL 17 and the pinned Linux application images on Docker Desktop. Python/database tests and final browser acceptance run sequentially.

| Check | Result |
| --- | --- |
| Frozen dependencies | `uvx --from uv==0.12.23 uv sync --frozen` and `npm ci` pass |
| Contract and generation | `scripts/validate_contract.py`: 146 operations, 14 request and 10 response examples; `scripts/check_generated.py`: exact generated-type equality |
| Full backend integration | `python -m pytest -q` in the Linux API container: **188 tests and 934 subtests pass**, one existing Starlette/httpx deprecation warning |
| Operation inventory | Successful HTTP responses observed for **146/146** canonical operations, including role and foreign-tenant cases |
| Extraction | Actual UTF-8, native PDF, scanned PDF, PNG and JPEG processing/download checks; English, Indonesian and Chinese OCR/text candidates; 12 fixture hashes verified |
| Builds | Production Next.js build and pinned API/web images build successfully |
| Actual-service browser suite | `FINCATHON_BROWSER_COMPOSE=1 npx playwright test`: **17/17 pass**, including new normal-account/session and numeric lineage journeys |
| Seed/restart persistence | Two consecutive reseeds and a full Compose stop/start preserve **1,701 immutable snapshots**, **7 original hashes**, **14 workspaces**, all 12 role memberships and 12 fixture hashes. A disposable unrelated user's workspace and session survive restart unchanged; the control is cleaned up afterward. |
| Offline runtime | Demo Docker network is internal; an actual API public TCP egress attempt is blocked; browser journeys use synthetic providers |
| Whitespace | `git diff --check` passes |

Run logs stay under ignored `.local/fithra-*`; credentials and session controls remain private and are excluded from committed evidence. The first host extraction attempt failed in macOS `preexec_fn` resource-limit setup, so acceptance uses the documented Linux container sandbox. The first all-service build hit a duplicate shared-image export; explicit `build api web` passed. A browser startup attempt ran before container readiness and was discarded. An early lineage assertion incorrectly expected a file behind a manual excerpt; it now uses the document-backed base case. An OCR fixture was adjusted to test an unambiguous visible date pattern rather than depend on one OCR engine reading a currency glyph identically. Captured failed-run logs are retained separately; the unsuccessful attempts described here are not counted as passes.

## R01: accounts, organizations and roles

| ID | Acceptance evidence |
| --- | --- |
| R01.1 | `test_storage_access.py::test_real_password_session_expiry_and_membership`; HTTP logout rejects the old bearer while a second session survives; `browser/auth.spec.ts` provisions a disposable normal account, signs in, switches organizations, reloads and logs out through real services. |
| R01.2 | `test_workflow_commands.py::test_membership_updates_apply_to_existing_sessions_and_last_owner_is_retained`; all protected operations' four-role matrix in `test_operation_matrix.py`; browser production reviewer can inspect goods but cannot verify funds/receipts. Final-owner removal is rejected. |
| R01.3 | Operation matrix and storage/pipeline checks exercise tenant-scoped resources, documents, runs, artifacts, exports and foreign references; the same ID never grants another tenant access. |
| R01.4 | Normal-mode demo rejection and old-demo-session refusal in HTTP/storage tests; browser HttpOnly/Strict cookies, empty client token storage, origin denial and revoked-token checks. [Local provisioning](local-runtime.md) retains a hidden password prompt. |

Confirmed fix: the browser logout proxy omitted the contract-required empty JSON object. It now sends the canonical request, waits for server revocation and retains a visible retry state on failure. No wire change was required. Session/organization changes clear the previous portfolio and discard late list responses; usage and membership views remount for the selected organization. The normal-account browser regression verifies a private workspace disappears and Team allowances change to Free when selecting the second organization.

## R04: upload, extraction and review

| ID | Acceptance evidence |
| --- | --- |
| R04.1 | `test_document_pipeline.py::test_supported_original_types_round_trip_through_authorized_http` uploads text/PDF/PNG/JPEG through real handlers, processes each and compares original download bytes and hashes. Storage tests reject oversized, malformed and path-traversal inputs; tenant matrix covers downloads. |
| R04.2 | `test_document_extraction.py`: actual English text/native PDF/image/scanned PDF, Indonesian text/OCR and Chinese text/OCR with locators, original-language spans and unreviewed candidates. Pipeline failure/retry tests preserve originals. |
| R04.3 | Conflicting quantities remain separate in `test_conflicting_candidates_and_archived_exports_preserve_originals`; Chinese currency/date ambiguity and net-30 anchor tests retain unknowns. Manual evidence stays subject to explicit authorized review. |
| R04.4 | `test_effective_dates_and_expiry_invalidate_reviews_without_editing_history` and immutable numeric-source regression; browser evidence/review controls call the API and show processing/review state. Original downloads remain unchanged. |

Confirmed fix: scanned-PDF processing discarded OCR region locators while retaining text. PDF locators now retain both the page and OCR word boxes. Parser cache identity advances to `extract-2`; a regression proves old `extract-1` results remain stored but cannot satisfy a current lookup, so prior cached output cannot hide the fix. Existing history is not rewritten. New explicitly synthetic Indonesian/Chinese image fixtures are hash-locked; existing fixture bytes and natural keys are unchanged. OCR output remains fallible review material, never commercial agreement or verified payment.

## R07: numeric lineage

| ID | Acceptance evidence |
| --- | --- |
| R07.1 | `test_numeric_output_keeps_the_original_source_revision_after_conflict`, economics/golden tests and `browser/lineage.spec.ts` trace formula, stored input revision, native cash amount, source mode/expiry/hash and original-file bytes. Structured blockers retain explicit reasons/actions rather than inferred missing facts. |
| R07.2 | The pipeline test changes a used source to conflicted, retrieves the old analysis and exact old evidence revision, proves byte-for-byte historical equality and refuses a new approval based on that stale analysis. Scenario/workspace revision reads remain tenant-authorized. |
| R07.3 | The extracted `numeric-lineage.tsx` exposes the previously count-only fixed input revisions and historical metadata, including unknowns, assumptions, conflicts, validity and synthetic/cached source modes. It labels historical review as insufficient for new action and offers authorized original downloads. The new browser journey uses keyboard controls at 390 px. |
| R07.4 | **Open handoff:** Faiz must review the calculated-input trace and Wisa the source-reference handoff. The trace and same-state screenshots are available below; no human review is claimed. |

[Before](audits/fithra-roadmap/lineage-before.png) shows the existing closed checkpoint's formula panel with input counts. [After](audits/fithra-roadmap/lineage-after.png) shows the same state with expandable fixed inputs; [opened input](audits/fithra-roadmap/lineage-input.png) shows the historical inspector. The inspector always calls `GET /v2/inputs/{id}/revisions/{revision}` from the analysis reference; it does not substitute a current mutable record. The browser regression independently reads the same revision and compares the source download's SHA-256 with the displayed evidence hash.

### Stored synthetic trace for handoff

The retained [trace receipt](audits/fithra-roadmap/trace.json) records one baseline analysis from this run: `analysis_4211fc31672e9546894067f9`, contribution **IDR 26,000,000.00** and minimum cash **-52,000,000.00**. Its contribution formula refers to Deal `deal_f3cd6fc3a46ff42f27698fe5` revision **26** and evidence `evidence_812e26fe2485211c7ddaa167` revision **1**. These exact revisions are retrievable through the authorized input-revision endpoint.

The source locator is “Fixture manifest and declared schedules,” with explicit `synthetic_demo` mode. Its original document is `document_3f6b392b6ebb8d67f82c1721`; SHA-256 is `707e5794000f5df7a318357c1e2d20d8de510855c29f3837395156fdcbcd521b`. The browser download regression independently hashes the authorized bytes. Real parsed character/region spans and changed-source history are separately exercised in `test_document_pipeline.py` and `test_document_extraction.py`. This receipt is a synthetic run example, not live evidence or a replacement for Faiz/Wisa's review.

## R10: negotiation and scenarios

| ID | Acceptance evidence |
| --- | --- |
| R10.1 | `test_scenario_comparison.py` and `test_joint_scenario_changes_reproject_terms_and_costs_without_writes` exercise immutable baseline/buyer/supplier-production/joint alternatives and retain required counterparties. |
| R10.2 | Joint payment/procurement regression verifies changed buyer deposit and supplier unit costs are reprojected into obligations/costs without mutating baseline resources; dated economics/golden tests cover full deposit/balance schedules and producer inputs. |
| R10.3 | Constraint checks/ranking cover margin, cash buffer, allowed changes, delivery dates/timezones, credit tenor, missing anchors and stale results. Ranking uses disclosed deterministic metrics and never implies agreement. |
| R10.4 | Actual-service browser funding/scenario journey displays API-derived contribution/minimum/timing, creates a bound draft and retains hypothetical terms; domain assertions compare unchanged live inputs and residual exposure. |

Existing working calculation and scenario behavior was reused. Decimal arithmetic, verified receipt history and immutable source revisions were preserved.

## R13: requirements, goods and readiness

| ID | Acceptance evidence |
| --- | --- |
| R13.1 | Canonical operation matrix exercises requirement ingestion/applicability/fulfillment review. `review_handlers.py` and `workflow.py` retain predicates, responsible parties, source/evidence versions and current-review conditions. |
| R13.2 | `test_photographs_without_measurements_cannot_establish_goods_conformity` and browser production inspection/correction show measured quantity/specification evidence and retained discrepancies. |
| R13.3 | Workflow and seeded checkpoint tests distinguish owner review, current counterparty agreement, available/verified funds, documents and goods. An owner approval cannot satisfy the unfunded baseline, and buyer-paid/nonconforming goods remain blocked. |
| R13.4 | Real browser/API blocked-goods and successful closed paths, stale agreement/approval regressions and blocked-external-shipment history. Exceptions retain unmet conditions and do not confer retrospective readiness. |

The separate business state dimensions and server-derived gates required no replacement implementation.

## R16: usage and entitlement behavior

| ID | Acceptance evidence |
| --- | --- |
| R16.1 | `test_pilot_provisioning.py` invokes the real operator CLI for Free, Deal Pass, Pro, Team and explicit institutional terms; checks catalog version, Deal Pass's 90-day expiry and unknown institutional price. Missing institutional limits/terms are rejected. Usage preview is exercised by HTTP and browser discovery checks. |
| R16.2 | `test_pending_provider_work_reserves_allowance_but_manual_matching_does_not`; duplicate/cached-document and interrupted-job tests; normal-mode manually reviewed finance matching through HTTP. Pending provider work reserves allowance, failed work releases it and successful work is metered once. |
| R16.3 | Included-before-add-on/monthly reset/expiry and active-deal limits in `test_entitlements.py`; membership allowance/server checks; expired admission preserves deterministic/manual work, existing reads and exports. Archive/closure free active slots. |
| R16.4 | CLI provisioning produces `provisionPilotEntitlement` audit records with the local operator identity. Browser settings/preview and structured admission errors explain restrictions. No checkout, automatic overage or changes to trade economics were introduced. |

Confirmed fix: pending deterministic matching of manually reviewed finance products incorrectly reserved an enriched run. Pending accounting now follows the existing server-set deterministic flag, matching admission and metering behavior.

## R19: seeded demo and evaluator journeys

| ID | Acceptance evidence |
| --- | --- |
| R19.1 | Hash-locked manifest/source inventory, fixed 2026-10-16 business reference date, all four roles across three isolated organizations, ten entry workspaces plus four causal checkpoints, KE→DE and CN→AE multi-line/multi-shipment fixtures. |
| R19.2 | Seeded acceptance and actual-service browser journeys reproduce analysis, negotiation, timely/late finance, drafts, blocked/corrected goods, receipt verification/reversal, buyer-paid/internal-reconciling and successful closure. Goldens remain independently specified. |
| R19.3 | `test_seed_replay_does_not_duplicate_resources`, scoped reset tests preserving unrelated records, mixed ownership/history refusal and retained/live Calendar dependency refusal. Fresh reseed/restart fingerprints supplement these transactional regressions. |
| R19.4 | Offline evaluator journeys are exercised and the walkthrough is updated, but **final integrated acceptance remains blocked** by R07.4 and Wisa's R17.3/R17.4 recovery evidence and review. This run does not perform another owner's disaster-recovery work. |

The Compose browser helper now invokes ordinary Compose for the running services; it no longer requires the managed-cloud proxy wrapper. The demo network is internal, and a real public TCP connection attempt from the API is refused. Synthetic Calendar tests make no Google writes. No live-provider credentials are needed for these journeys.

## Remaining handoffs and limits

| Dependency | Owner | Next evidence |
| --- | --- | --- |
| R07.4 calculated/source handoff | Faiz and Wisa | Review immutable calculated-input/source trace and the R07 browser change. |
| R17.3/R17.4 isolated backup/restore | Wisa | Execute and record the separate PostgreSQL/private-file/key recovery rehearsal. The archived verification explicitly did not establish this. |
| Package review and final R19.4 acceptance | Wisa, with dependent feature owners | Accept this technical evidence and complete the missing core recovery/handoff reviews before declaring the integrated package Done. |

Native macOS host extraction/launcher limitations are handed to Faiz under R18; they do not block the passing Linux Compose path documented here. No new hosted deployment, payments, lending submission, trade-message delivery, carrier booking or expanded source/regulatory coverage is claimed.

The installed PR skills contain examples for other repositories (`make generate`, `packages/api-client`, `scripts/check-docs.mjs`, `backend/tests/test_contract.py` and `/analyze` with `suggested_reply`). Those paths/operations do not exist here. This PR uses the actual Fincathon contract/type scripts, full backend suite, Compose health and real analysis POST/browser-worker smoke, plus `.github/workflows/contract.yml`. No nonexistent check is reported green, and existing untracked user skill/config files are excluded from staging.
