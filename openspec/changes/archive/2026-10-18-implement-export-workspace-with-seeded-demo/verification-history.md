# Verification: implement-export-workspace-with-seeded-demo

## Task 12.3 and Gemini free-tier diagnosis — 18 October 2026

**Latest result: the replacement key supplied by the user succeeds.** The actual bounded-model adapter returned a schema-valid explanation selection. The combined live provider probe now passes **Brave, Frankfurter FX and Gemini**, and API/worker/web were restarted in normal mode with the working key inherited by their processes. No key value was saved to repository configuration files. Persistent environment configuration still needs the working replacement; the exposed chat key should be rotated. Sanitized evidence is `.local/supplied-key-model-check.json` and the latest `.local/live-provider-probes.json`.

A follow-up fetch of Indonesia Eximbank's actual trade-finance product page also succeeds and retains an attributed source hash, time and title in `.local/live-source-retries.json`. The ITC reference page returns an authorization/access failure. CN/KE source access and product-specific commercial applicability, current comparable prices and other declared-lane review gaps remain unresolved. This clears the model-access blocker but does **not** complete every condition of task 12.3; its checkbox remains open. Earlier model failures below are historical observations of the previously configured key.

After the user published the replacement configuration, environment revision **15** reports current ready model variables and enforced networking. API, worker and web were restarted in normal mode. A fresh supported-model call still fails with `MODEL_PAYMENT_REQUIRED` and the same synthesized depleted-prepaid-credit diagnosis. The key is supplied by the runtime rather than a dotenv fallback. Brave and FX still pass. Evidence: `.local/published-model-check.json` and `.local/live-provider-probes.json`. This confirms the published runtime can make the request; it does not reveal or independently establish which Google project owns the key. Creating another key in the same depleted paid project does not change that project's billing tier.

The current model configuration uses Google's documented OpenAI compatibility base URL, `https://generativelanguage.googleapis.com/v1beta/openai/`, with `gemini-flash-lite-latest`. A minimal request through that endpoint, a native Gemini `generateContent` request and a request for the explicitly free-tier-listed `gemini-3.1-flash-lite` all returned HTTP 402 with `RESOURCE_EXHAUSTED` and a depleted-prepaid-credit message. This establishes the provider's reported key/project billing-state blocker; it does not establish that a paid model is required or prove the console's actual tier. The console/API state may disagree. No model alias or billing setting was changed.

The user intends to replace the API key. Use an eligible Free Tier project's key in the environment setting `FINCATHON_MODEL_API_KEY`, then restart services and rerun the probes. The base URL is already correct. [Google's billing guidance](https://ai.google.dev/gemini-api/docs/billing) explains that depleted paid projects do not automatically fall back to Free Tier. A key can be selected from a separate Free Tier project without changing billing on other projects.

The application now recognizes Gemini's prepaid-credit response in either object or array form and gives synthesized Free Tier guidance. It retains the provider response hash and safe limitations in failed probe receipts without copying the provider error body. Relevant provider/model checks pass: **11 tests and 2 subtests**.

Task 12.3 progressed beyond connectivity: `scripts/probe_live_sources.py` executed nine public queries and bounded candidate retrievals for provisional ID–SG coffee, CN–SG manufactured-components and KE–DE dried-mango scopes. Five category checks retrieved source receipts: Indonesian export guidance, Singapore import guidance for two scopes, German plant-protection guidance, and Maersk Indonesia route information. These are generic references requiring scope review, not accepted product-specific rules or executable quotes. The German retrieved page concerns private travellers, so it cannot establish commercial dried-mango import requirements. China customs candidates used HTTP and were refused by the HTTPS-only policy; Kenya customs and Indonesia Eximbank attempts failed DNS resolution; ITC candidates failed DNS or returned unavailable content. No blocked source was relabeled as passed.

Attributed URLs, decoded source hashes, timestamps, parsed title/product-term observations and exact fetch failures are retained in `.local/live-source-probes.json`; original bytes are private under `.local/live-source-receipts/`. This partial probe exits 2 and explicitly reports `coverage_acceptance: false`. Finance, comparable market data, product-specific commercial applicability and model acceptance remain incomplete, so **12.3 stays unchecked**. The probe is a reproducible partial evidence collector, not a shortcut to accepting every lane.

## Current blocker follow-up — 18 October 2026

All **12 OpenSpec 1.14.3 skills** are installed and their manifests validated. The CLI is available on PATH; Codex uses `$openspec-verify-change` rather than generated `/ospx:*` commands. The full workflow profile is saved in the current user's OpenSpec configuration. New skills are retained in this checkout.

**The FX TLS blocker is fixed.** Public retrieval now supplies a dedicated pinned transport that verifies the original source hostname after an HTTP CONNECT tunnel while connecting to the validated public IP. HTTPS proxy certificates are verified against the proxy hostname separately. Original Host headers, inherited proxy selection and CA trust, public-address validation, redirect checks and decoded size/time budgets remain enforced. The HTTP Core dependency is explicitly pinned in `pyproject.toml` and the updated lockfile. Low-level handshake tests cover direct, HTTP-proxy and HTTPS-proxy paths, plus propagated certificate failures.

Fresh application-adapter probes pass for **Brave and Frankfurter FX**. The configured model still returns HTTP 402, now reported explicitly as **`MODEL_PAYMENT_REQUIRED`** with no provider body or credential output. It requires funded account access or another funded configured endpoint. Google consent and the dedicated Calendar ID have not been supplied; an account email alone does not authorize Calendar access. Live delivery remains disabled and tasks 11.5/12.3 remain unchecked. Full source coverage acceptance also remains unexecuted.

Validation: **177 Python tests and 916 subtests pass**, followed by **14 focused retrieval/provider tests and 7 subtests** covering the final changes. The existing Starlette/httpx deprecation warning remains. All 12 skill manifests, strict OpenSpec validation, frozen lock consistency and whitespace checks pass. The earlier 14 passing browser journeys and production build remain applicable; no frontend changes were made in this follow-up. No real Google event writes were attempted. PostgreSQL started for verification was stopped afterward, preserving data.

See [live acceptance setup](../../../docs/live-acceptance.md) for the precise user actions: model account credits/configuration, OAuth client/API/test-user setup, a dedicated empty Calendar ID and browser consent. Private current evidence is in `.local/blockers-tests.log` and `.local/live-provider-probes.json`. No archive, commit or push was performed.

## Earlier fix follow-up — 18 October 2026

**Current assessment: the confirmed adapter defect and both reported warnings are addressed. Real Calendar acceptance (11.5) and full live source/provider acceptance (12.3) remain incomplete, so the change is not ready to archive.** Earlier findings below describe the implementation before these fixes.

- The bounded provider helper now removes obsolete `Content-Encoding` and `Content-Length` headers after decoding. Gzip search and model responses retain their valid output and decoded response hashes; oversized decompressed bodies still fail at the existing 2 MiB limit. Regressions exercise the actual shared adapter with mocked compressed HTTP responses.
- Fixed funding schedules render date-only values without converting them to instants, and display the declared timezone. Instant schedules are formatted in their declared timezone. The browser regression creates a funding option through the actual API with both local-date and instant schedule forms.
- The workflow regression records verified arrival separately from forecast acceptance, refuses actual acceptance without evidence, and verifies that only evidenced acceptance changes the acceptance-anchored payment projection. Delivery preserves the unverified acceptance state and its forecast; the contractual schedule remains unchanged.

Validation: the full Python suite passed **174 tests and 913 subtests**, with the existing Starlette/httpx deprecation warning. The additional compressed-model regression was then verified in an **8-test focused run**, including the final acceptance-anchor regression. Successful HTTP operation coverage remains **146/146**. All **14 browser journeys pass** against actual local services, including the new date/timezone case. Canonical validation, generated types, the production web build, formatting checks and strict OpenSpec validation pass. Python and browser suites ran sequentially against the shared database. Services and PostgreSQL started for verification were stopped afterward, preserving stored data.

Fresh live evidence: Brave now **passes through the actual application adapter** with a retained hashed receipt. The configured model returns HTTP **402**; its valid compressed-response behavior passes the deterministic regression, but the provider account response still blocks real model acceptance. FX retrieval fails TLS certificate verification with an **IP address mismatch** on the validated pinned address through the configured proxy. HTTP Core's proxy tunnel selects the IP as TLS server name, so the retrieval path needs compatible hostname-preserving proxy/SNI support. TLS verification and public-address pinning remain enforced. No billing configuration, network bypass or trust weakening was introduced.

Tasks 11.5 and 12.3 remain unchecked. Google readiness/configuration does not supply an authorized test-account session or Calendar lifecycle receipts, and successful Brave connectivity alone does not satisfy official-source, finance, market/logistics and model coverage acceptance. Application fixes cannot manufacture those external acceptance results.

Private evidence: `.local/fix-full-tests.log`, `.local/fix-build.log`, `.local/fix-browser.log`, and `.local/live-provider-probes.json`. No archive, commit, push or hosted deployment is performed.

## Verification before fixes — 18 October 2026

**Assessment: not ready to archive. Three blocking items remain: a newly confirmed compressed-response defect, real Calendar acceptance (11.5), and live source/provider acceptance (12.3). Two previously reported warnings remain.** This assessment supersedes the older summaries below. The original Calendar acceptance-enforcement defect is resolved in the current working tree.

The `/ospx:verify` command/skill is not installed in this checkout. Verification used the cached OpenSpec CLI, the repository's checks, static review of the existing requirement/scenario mapping, and a new deterministic provider reproduction. OpenSpec reports 72/74 tasks complete across 11 delta specs; planning-artifact completeness does not establish implementation acceptance. This is a revalidation of the existing review and Calendar follow-up, not a claim of a new independent exhaustive audit of every scenario.

### New correctness finding: compressed live-provider responses fail

`packages/adapters/providers.py:65–82` consumes `response.iter_bytes()`, which HTTPX has already decompressed, then constructs another `httpx.Response` with the original `Content-Encoding` header. The constructor attempts decompression again and raises `httpx.DecodingError` for valid gzip JSON. Both Brave search and the configured model call this helper. The outer handlers convert the exception into `SEARCH_UNAVAILABLE` or `MODEL_UNAVAILABLE`, hiding a successful provider response.

Evidence: the direct Brave credential request returned HTTP 200 and a search result. A direct HTTPX streamed Brave response also returned HTTP 200 with `Content-Encoding: gzip` and decoded successfully. The application's search adapter instead raised `DecodingError`. A deterministic `httpx.MockTransport` response containing valid gzip JSON reproduces the same error with zero external requests. Reproduce with `.venv/bin/python .local/ospx-gzip-repro.py`; private evidence is `.local/ospx-gzip-repro.json`.

Action: preserve decoded-body semantics when rebuilding the response by removing obsolete content-encoding/content-length metadata, or consume raw bytes with an explicit decoded-size bound. Keep the existing 2 MiB decompressed-response limit. Add a meaningful compressed-response regression covering the shared helper and rerun the actual adapter probes. Do not treat successful direct credential checks as passing application integration.

### Remaining acceptance and scenario gaps

- **Task 11.5:** Google client ID, client secret and redirect URI are present. Client ID and redirect URI formats pass basic checks. A deliberately invalid authorization-code exchange returned HTTP 400 `invalid_grant`; this neither proves the registered redirect matches nor completes user consent or Calendar access. No real insert/update/delete, retry/conflict or revocation receipts exist. Operator live enablement and acceptance reference remain unset; preserve the disabled gate and leave 11.5 unchecked.
- **Task 12.3:** Brave and model configuration are now present; earlier missing-configuration observations below are historical. The repository's fresh live probe still exits 2 with `SEARCH_UNAVAILABLE`, `SOURCE_NETWORK_UNAVAILABLE` and `MODEL_UNAVAILABLE`. The compressed-response defect is confirmed for Brave and affects the model's shared helper; the precise FX and model failures have not independently been established. Official-source, finance and market/logistics applicability, freshness and coverage acceptance remain unexecuted. Leave 12.3 unchecked.
- **Warning: fixed funding dates.** `apps/web/app/components/workspace.tsx:1400–1403` still renders fixed schedules only when `due.instant` exists; valid `due.date` falls through to the relative-event label. Render the local date and declared timezone, with a date-only browser regression.
- **Warning: acceptance-based payment anchor.** Existing arrival-forecast propagation coverage remains, but no direct regression was found for reported delivery with unverified acceptance followed by verified acceptance. Add the scenario's forecast-versus-actual assertions; this remains a coverage gap rather than a confirmed calculation defect.

The API admission, worker processing and queued Calendar delivery now share the operator acceptance policy. The Calendar tests cover disabled admission/delivery, missing enablement inputs, demo isolation, exact OAuth redirect/state binding, replay refusal, encrypted refresh credentials, ETags and retry identity. Browser callback tests exercise the actual local services with the explicit offline adapter; they do not establish real Google acceptance.

### Current execution evidence

| Check | Fresh result |
| --- | --- |
| OpenSpec strict validation | Active change and both main specs pass: 3 passed, 0 failed |
| Canonical contract | 146 operations, 14 request examples and 10 response examples validated |
| Generated types / production build | Generated types match; Next.js production build passes and includes the OAuth callback route |
| Fixture assets | All 10 synthetic asset checks pass |
| Python / PostgreSQL | 171 tests and 913 subtests pass; one existing Starlette/httpx deprecation warning |
| Successful operation coverage | 146/146 canonical operations observed with successful HTTP statuses |
| Browser acceptance | Isolated rerun: all 13 journeys pass against actual local PostgreSQL/API/worker/web services, including three OAuth callback cases |
| Live adapter probes | Exit 2; three unavailable errors recorded above, no coverage acceptance |
| Compression reproduction | Valid gzip JSON deterministically raises `DecodingError`; zero external requests |

The first Python attempt ran before PostgreSQL was started and produced connection-related failures; the full suite was rerun after local PostgreSQL readiness and migration upgrade. The first browser attempt overlapped the Python suite against the same database and returned 11 passed / 2 job-state timeouts; the separate browser rerun passed all 13 tests. These unsuccessful attempts are retained rather than counted as passing evidence. Run these suites sequentially when sharing the local database. Application services and the local database started for verification were stopped afterward, preserving their stored data.

Private logs use `.local/ospx-verify-*`; provider probe receipts are `.local/live-provider-probes.json`. This run did not repeat frozen installs, Docker application image builds, network-isolation acceptance, restart/reseed fingerprint acceptance, reset or disaster-recovery acceptance, or remote CI. Earlier evidence below is historical. No hosted deployment or production-readiness claim follows. No application fixes, checkbox changes, archive, commit or push are performed by this verification.

## Calendar follow-up — 18 October 2026

Original critical issue 1 is resolved in the working tree. Normal-mode users can initiate Google consent, return through `/oauth/calendar/callback`, and select a connected calendar. The browser callback clears code/state from history, sends the exchange through the authenticated same-origin gateway, and handles cancellation, missing sessions and replayed state. Session cookies retain `SameSite=Strict`; tokens remain encrypted server-side.

Live Calendar sync now requires shared operator enablement, a retained acceptance reference and Google configuration. API admission, worker processing and outbox delivery check the same policy; delivery receipts record the reference. A disabled gate blocks previously queued delivery without contacting the provider. Demo runtimes cannot deliver live events even when operator live settings are enabled. OAuth connection and selection remain available for acceptance preparation without enabling event writes.

Validation: the final full Python suite passed **171 tests and 913 subtests** (one existing Starlette/httpx deprecation warning); the focused Calendar suite passed 14 tests and 4 subtests; all **13 actual-service browser journeys** passed, including three new callback cases. All 146 canonical operations retained successful HTTP coverage. The Next.js production build includes the callback route, canonical validation still covers 146 operations / 14 request examples / 10 response examples, and generated types match. The backend live OAuth exchange was tested with a mocked Google token endpoint; browser callback tests use the explicit offline adapter and actual API/database. No real Google event writes or completed real-account acceptance are claimed.

Critical issues 2 and 3 below remain open (real Calendar and live-provider acceptance), as do both original warnings. Tasks 11.5 and 12.3 stay unchecked. At the start of this fix, the selected runtime exposed no Google credential variables or active cloud bindings; credentials configured elsewhere do not establish access in this process. See `docs/local-runtime.md` for exact redirect setup, normal-mode connection and isolated acceptance instructions.

## Original verification — 17 October 2026

Reviewed 17 October 2026 (Asia/Jakarta), against commit `aaeb66d`, schema `spec-driven`.

**Assessment: 3 critical issues and 2 warnings. Resolve the critical issues before archiving.** Local deterministic checks pass, but live acceptance is incomplete and Calendar's server-side enablement does not enforce that acceptance. This review changes no application code or task checkboxes and does not archive the change.

## Scorecard

| Dimension | Result |
| --- | --- |
| Completeness | 72/74 tasks complete; all 11 delta specs readable, containing 57 added/modified requirements and 85 scenarios. Implementation locations found for all capability groups; Calendar acceptance enforcement is incomplete. No removed or renamed requirements. |
| Correctness | Fresh contract, API, PostgreSQL, adapter and browser checks pass. Requirement mapping and scenario review found the Calendar enforcement defect and funding-date display divergence below. Scenario coverage is partially verified: the actual-acceptance payment-anchor case lacks a direct regression; real lane/provider and Google lifecycle acceptance remain unverified. |
| Coherence | The Next.js/FastAPI/PostgreSQL/worker layout, canonical schemas, Decimal engines, durable storage/jobs and synthetic fixtures follow the design. The live Calendar enablement decision is not enforced in the backend. File naming and package/test organization follow repository patterns. |

`openspec status` reports planning artifacts complete; it does not establish task or release completion. `openspec instructions apply --json` reports 72 complete, 2 remaining, with no unavailable tracking files. No artifacts were intentionally skipped.

## Critical issues

1. **Live Calendar delivery does not enforce the acceptance gate.**

   `specs/calendar-projection/spec.md:10` requires live sync to remain unavailable until configured access and real integration acceptance are verified. `services/api/handlers.py:331` reports every normal-mode capability blocked with “Live acceptance has not been recorded.” However, `packages/adapters/calendar.py:430` checks projection approval without checking live capability acceptance, and `packages/adapters/calendar.py:546` / `:589` can deliver a live outbox event using a connected account and token without consulting that blocked state. The browser hides normal-mode controls, but the backend paths do not enforce the same restriction.

   Reproduction used the existing outbox fixture, a rollback transaction, normal mode and `httpx.MockTransport`. Capabilities reported Calendar `blocked`; delivery nevertheless issued a mocked `POST` and returned `delivered: true`. There were **zero real external calls**, and the fixture transaction was rolled back. Private reproduction: `.local/verify-calendar-acceptance.py` and `.local/verify-calendar-acceptance.json`.

   **Action:** define an explicit, auditable operator-controlled acceptance/enablement state and enforce it when admitting live sync and again before external delivery. Keep OAuth acceptance setup and synthetic demonstration available as appropriate. Add regression coverage proving configured credentials, valid projection approval and a connected account cannot bypass a disabled live-sync gate, including already queued events. Make capability reporting use the same state.

2. **Task 11.5 remains incomplete: real Google Calendar acceptance.**

   `tasks.md:105` requires actual OAuth and approved insert/update/delete, retry/conflict and revocation receipts. Those checks were not executed. Mocked provider and offline browser results do not satisfy this task.

   **Action:** configure an approved test account/client/redirect through environment settings, execute the declared lifecycle and retain provider receipts. Leave the task unchecked until that evidence exists.

3. **Task 12.3 remains incomplete: real source/provider coverage.**

   `tasks.md:111` requires attributed real search, official-source, FX, finance, market/logistics and configured-model acceptance for declared product/jurisdiction coverage. The fresh connectivity probe exits 2: Brave is blocked by missing `BRAVE_SEARCH_API_KEY`; the model is blocked by missing `FINCATHON_MODEL_BASE_URL`, `FINCATHON_MODEL_ID` and `FINCATHON_MODEL_API_KEY`; Frankfurter fails with `SOURCE_DNS_UNAVAILABLE`. Real lane/source coverage has not been accepted.

   **Action:** supply configuration securely, resolve the FX access failure, and collect the scoped retrieval, applicability, freshness and observation evidence required by Gate B. A successful connectivity probe alone is insufficient. Keep this task unchecked until acceptance completes.

## Warnings

1. **Fixed date-only funding events are displayed as relative events.**

   `apps/web/app/components/workspace.tsx:1400` renders a date only when a fixed schedule contains `due.instant`. A valid fixed schedule with `due.date` instead falls through to “Relatif terhadap peristiwa,” hiding the contractual date and timezone. The canonical `FixedSchedule` accepts either TemporalValue form (`api/openapi.yaml:9563`). This diverges from the workspace UI's explicit date/timezone presentation requirement. The separate internal milestone timeline already handles date-only values correctly.

   **Action:** render fixed `due.date` and its declared timezone without converting it to an instant; reserve the relative-event label for event-relative schedules. Add a browser case with a date-only funding draw or repayment.

2. **No direct regression found for “Actual acceptance is the payment anchor.”**

   `specs/execution-reconciliation/spec.md:32` distinguishes reported delivery from verified acceptance. Existing date tests cover local dates, cycles, calendars and changing arrival forecasts; `tests/test_workflow_commands.py:721` specifically tests forecast propagation. No direct test was found that records arrival while acceptance remains unverified and checks the acceptance-based actual payment date. This is a coverage gap, not a demonstrated incorrect calculation.

   **Action:** add a regression with separate arrival and acceptance milestones, a payment anchored to acceptance, and forecast versus verified-actual assertions before and after acceptance review.

## Fresh execution evidence

These results were reproduced from the pushed checkout in the restarted environment; the previous ignored execution logs were unavailable.

| Check | Result |
| --- | --- |
| Toolchain and frozen installs | Node 24.19.0, uv 0.12.23; `uv sync --frozen` and `npm ci` passed with writable caches under `/workspace/.cache` |
| PostgreSQL/migrations | Pinned PostgreSQL 17 image started; migration upgrade passed; current revision `0006 (head)` |
| OCR and synthetic assets | Pinned Git-blob-verified OCR assets installed; all 10 fixture asset checks passed |
| Canonical OpenAPI | 146 operations, 14 request examples and 10 response examples validated |
| Type generation | Fresh generated TypeScript matches the committed types |
| Python checks | **167 passed, 909 subtests passed**, 1 Starlette/httpx deprecation warning; no failed or skipped tests reported |
| Actual HTTP operation coverage | **146/146** canonical operations observed with a successful status; role, tenant, malformed-input and missing-resource checks run in the suite |
| Web build | Next.js production/standalone build passed |
| Browser acceptance | **10/10 passed** against actual PostgreSQL, API and worker services; no browser API response interception |
| Restart/reseed | API/worker/web stopped, PostgreSQL restarted, services restarted with seed, then seed invoked again; all **1,239 immutable snapshots and 10 stored files** retained identical fingerprints, with zero queued/running jobs at each comparison; health returned ready |
| Reset boundaries | Existing PostgreSQL tests passed for scoped reset, retained unrelated records, mixed ownership refusal and live Calendar dependency refusal; destructive production reset was not performed |
| OpenSpec | Strict validation passed for the active change and both main specs: 3 passed, 0 failed |
| Calendar acceptance-gate probe | Confirmed missing backend enforcement with a mocked provider; this is defect evidence, not live acceptance |
| Live connectivity | Exit 2: missing Brave/model configuration and FX DNS failure; Calendar lifecycle unexecuted |

Fresh browser coverage includes Calendar synthetic delivery/conflict/revocation, research usage preview and synthetic receipts, payment verification/reversal, narrow-screen keyboard access, opening-cash review invalidation, persisted edits, finance comparison, draft download, production role restrictions and blocked/successful reconciliation.

Logs and reproduction scripts remain ignored under `.local/verify-*`; credentials and database URLs are not included in this report. Restart fingerprints are `.local/verify-restart-before.json`, `.local/verify-restart-after.json` and `.local/verify-reseed-after.json`.

## Requirement and scenario mapping

The counts below enumerate every requirement/scenario heading in the readable delta specs. They are inventory counts, not a claim that each requirement has an independent passing test or that live acceptance passed. The mapped test modules ran in the fresh suite; code and tests were reviewed against the scenario conditions. The unresolved cases are identified above.

| Delta capability | Requirements / scenarios | Implementation evidence | Test evidence and limitations |
| --- | --- | --- | --- |
| canonical-api-contract | 3 / 6 | `api/openapi.yaml`; `packages/contracts/runtime.py`; `services/api/app.py`; `packages/domain/migration.py` | `test_contract.py`, `test_runtime_contract.py`, `test_http_foundation.py`, `test_snapshot_migration.py`, `test_operation_matrix.py`: authority fields, replay, tenant boundary, invalid response rollback, typed operations and retained 2.1 snapshots |
| contract-validation | 3 / 9 | `scripts/validate_contract.py`; `scripts/check_generated.py` | `test_contract.py`, `test_example_validation.py`, `test_responses.py`: duplicate keys, external/missing/cyclic references, unused dynamic references, full closure example mutations and separate check counts |
| workspace-access | 5 / 7 | `services/api/auth.py`, `store.py`, `commands.py`, `storage.py`; database migrations | `test_storage_access.py`, `test_http_foundation.py`, `test_document_pipeline.py`, `test_operation_matrix.py`: sessions/membership, normal-mode demo refusal, tenant resources, persistent generalized entry and immutable source revisions |
| evidence-ingestion | 6 / 9 | `packages/adapters/documents.py`, `extract_runner.py`, `network.py`, `providers.py`; `packages/domain/discovery.py`, `model_tasks.py`; `services/worker/jobs.py` | Document extraction/pipeline, discovery planning, provider adapter, public retrieval and model-task suites: original spans, actual OCR, ambiguity, query privacy, source exclusions, budgets and bounded failures. Real lane acceptance remains unverified (critical issue 3). |
| deal-economics | 6 / 9 | `packages/domain/economics.py`, `cost_coverage.py`, `pricing.py`, `cash_availability.py` | Economics, demo goldens, pricing treatment, native cash and cost coverage suites: exact arithmetic, W/M minimum, reimbursement, producer overhead, market/floor conflict, same-day ordering, shocks and delayed receipts |
| negotiation-finance | 5 / 8 | `packages/domain/comparison.py`, `finance.py`, `financing.py`, `artifacts.py` | Scenario comparison, finance preparation, financing settlement and artifact suites: combined terms, stage/instrument fit, unknown rates/recourse, net draw, assigned reserve, preparation limits and bound templates |
| execution-reconciliation | 6 / 8 | `packages/domain/workflow.py`, `dates.py`, `settlement.py`, `variance.py`; `services/api/review_handlers.py`, `settlement_adjustments.py`, `reconciliation.py` | Workflow command, date projection, seeded acceptance and variance suites: independent gates, goods, preserved agreements, evidenced external exceptions, verified/reversed settlement, actuals and closure. Direct acceptance-anchor regression not found (warning 2). |
| durable-operations | 6 / 8 | `services/api/commands.py`, `store.py`; `services/worker/jobs.py`, `heartbeat.py`, `liveness.py`; `packages/domain/entitlements.py` | HTTP foundation, cash concurrency, job recovery, entitlements, liveness and document pipeline suites: atomic replay/reservation, exhausted leases, stale results, cancellation, once-only metering, retention and diagnostics; fresh restart additionally checked |
| workspace-ui | 6 / 6 | `apps/web/app/components/`; `apps/web/app/api/` | Both browser suites: API-backed editing, worker state, source labels, role restrictions, comparisons/reviews, demo/usage transparency, keyboard/narrow layouts. Funding date-only presentation diverges (warning 1). |
| seeded-demo | 7 / 10 | `packages/domain/demo.py`, `demo_stages.py`, `demo_reset.py`; `fixtures/demo/`; `compose.demo.yaml`; seed/reset scripts | Demo golden, seeded acceptance, reset, storage/access and browser suites: staged causal histories, multiple lanes/profiles, repeatability, isolated roles, refused mixed ownership and synthetic/live distinction. Fresh restart and reseeding preserve fingerprints. |
| calendar-projection | 4 / 5 | `packages/adapters/calendar.py`; `migrations/schema_v3.py`, `schema_v5.py`; `apps/web/app/components/calendar-panel.tsx` | Calendar projection/outbox suites and offline browser journey: encrypted/revocable credentials, hash approvals, owned identity, ambiguous insert retry and ETag conflicts. Live enablement enforcement fails (critical issue 1); real OAuth/event lifecycle not verified (critical issue 2). |

## Design adherence and limits

The nine design decisions are represented by the declared package/service layout, canonical runtime validation and generated types, tenant-scoped immutable storage, leased PostgreSQL jobs/outboxes, bounded evidence adapters, Decimal workflow engines, localized browser controls, versioned causal seed fixtures and separate acceptance reporting. The original contract remains the sole wire-schema source; FastAPI serves it directly. Synthetic success is visibly distinguished from live evidence.

This run used the documented host launcher with a PostgreSQL container. It did **not** repeat Docker API/web image builds or execute the browser under the internal-network Compose override; the 16 October report records those earlier checks. Current Compose inspection shows the internal demo network and fixed-destination loopback gateway, but inspection alone is not a fresh network-isolation acceptance run. Complete disaster-recovery restoration and remote GitHub CI execution were also not rerun. No hosted deployment or production-readiness conclusion follows from these results.

**Final assessment:** 3 critical issues and 2 warnings found. Complete the live acceptance tasks and enforce the backend Calendar gate before archiving. Scenario Coverage is partially unverified for the actual-acceptance anchor and credential-dependent live checks; fresh Docker image-build/network-isolation and disaster-recovery acceptance were not executed in this review. The deterministic local checks that ran passed. No application fixes, task completion changes, archive, commit or push were performed by this verification.
