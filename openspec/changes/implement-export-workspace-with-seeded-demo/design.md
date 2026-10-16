# Design

## Context

See `proposal.md` for scope and motivation. The repository contains OpenAPI draft 2.1.1, Python contract tooling, 35 passing contract tests and no application code, package manifests, migrations or service configuration. The contract change was archived with two main capability specs and an advisory warning (`$dynamicRef` preflight) plus a closure-test suggestion. This proposal includes both follow-ups.

The user confirmed a complete local application with an offline seeded demo plus live adapters whose real acceptance requires credentials/access. This is not authorization to deploy a hosted production service or execute external trade actions. The newer General/Business attachments supersede the historical commodity/country/single-shipment scope in the system specification. Product features F01–F14 and its numeric/state acceptance cases guide coverage, not assumptions of delivered behavior.

## Goals / Non-Goals

**Goals:** Implement every current application operation and the additional operational surfaces needed for a complete local workflow. Use one set of domain services for demo, normal local operation and live evidence. Make results reproducible across process restarts and explain what was verified.

**Non-Goals:** Hosted deployment, payment checkout, lender submission/approval/disbursement, automatic trade messages, actual booking/payment/customs execution, bank integration, universal regulatory coverage or an unsupported production-readiness claim. Operational recording and readiness evaluation are included. Optional Calendar live enablement is conditional on verified access; its offline simulation is included.

## Decisions

### 1. Modular application with a small local service set

Use Next.js/React/TypeScript for the browser, FastAPI/Python 3.12 for HTTP, SQLAlchemy/Alembic with PostgreSQL 17 for persistence, and a separate Python worker using the same domain package. Target Node 24, pin exact compatible dependencies/tool versions during apply, and commit frozen lockfiles. Python is preferred for Decimal calculations and document tooling; TypeScript handles presentation and generated API types. A TypeScript-only backend was considered but would add a separate decimal implementation and require redoing established Python tooling.

Proposed layout:

```text
api/openapi.yaml                 canonical wire source, draft 2.2
apps/web/                        Next.js UI and server-side browser session proxy
services/api/                    FastAPI routes, auth and contract validation
services/worker/                 durable job/outbox runner
packages/domain/                 Python calculations and workflow services
packages/adapters/               live and synthetic evidence/model/calendar adapters
packages/contracts/              generated TypeScript types and canonical loader tooling
migrations/                      Alembic schema/data migrations
fixtures/demo/                   versioned synthetic manifest, source files, expectations
scripts/                         setup, generation, seed/reset and verification entry points
tests/                           unit, PostgreSQL integration, adapters and browser journeys
compose.yaml                     postgres, api, worker and web
compose.demo.yaml                explicit demo mode, synthetic adapters and persistent volumes
```

This layout is planned, not created by this proposal. Use the existing checkout; do not create a worktree merely for local setup. A PostgreSQL job queue using row locks/leases and a transactional outbox avoids a separate Redis dependency without collapsing workers into in-process HTTP tasks. SQLite is unsuitable for the proposed locking/concurrency acceptance tests.

### 2. Contract first, then validated consumers

Extend `api/openapi.yaml` before route/UI implementation. Preserve existing operations and error semantics; advance the pre-adoption draft API to 2.2.0 and snapshot schema_version to 2.2, retaining a tested 2.1-to-2.2 migration and original immutable snapshots. Add explicit nullable unknowns, not invented migrated evidence. No consumer compatibility with 2.1 is assumed.

Add typed surfaces for the following groups; exact methods, wire shapes and limits belong only in OpenAPI:

| Group | Needed behavior absent or incomplete in the current draft |
| --- | --- |
| Identity and organizations | Login/logout/current session; demo-only identity entry; organization/member selection and authorized membership management |
| Workspace/deal browsing | Tenant-scoped cursor-paginated lists, immutable revision/history reads, archive and user-owned export |
| Evidence and documents | Authorized original-content downloads, evidence/manual quotation ingestion, candidate fact review, rule/source registration and conflicts |
| Economics | Invoice/revenue basis, cost components and actual replacements, FX observations, own-cash reservations, obligation/allocation editing and typed buyer-risk results |
| Execution | Requirement applicability/fulfillment review, goods inspection/corrective evidence, shipment/booking records and externally performed exceptions |
| Finance and artifacts | Company profile, funding schedule/assigned receivable inputs, finance-pack contents and authenticated artifact downloads |
| Operations | Job cancellation, usage preview/history, capability readiness, audit/reconciliation exports and retention/archive controls |
| Calendar | OAuth connection lifecycle, calendar selection, projection preview/approval and conflict resolution |

The current patch union is scoped: `/product` and workspace countries do not map directly to deal line/shipment fields. Preserve separate allowlists; do not add generic arbitrary JSON mutation. New server-owned fields include execution scope and demo dataset identity. Close existing modeling gaps such as explicit seller invoice totals, shared organization cash reservations, collection traversal for asynchronous outputs and actual-charge lineage before calculations depend on them.

Generate frontend types with a pinned OpenAPI TypeScript generator; fail CI on generated drift. FastAPI publishes the canonical document, not its autogenerated alternative. Use full JSON Schema 2020-12 validation at request/response boundaries; generated types do not replace runtime conditionals. Internal Python domain types are not independent wire DTO schemas. Map handler response validation failures to sanitized server errors and failing tests.

Mark public authentication entry points and revision scope explicitly in OpenAPI. Refine existing blanket tests to validate this explicit auth exception while ensuring every resource route remains authenticated. Login/session creation is not an existing-deal revision mutation. Feature-disabled Calendar returns a declared unavailable response; no declared endpoint can silently return a successful stub.

Reject unsupported `$dynamicRef` explicitly before retrieval in this increment, including unused components; do not invent partial dynamic-anchor semantics. Preserve existing local `$ref` handling and legitimate recursive schema structure. Add a full closure response example and validate/mutate it through the actual operation schema.

### 3. Authentication, storage and immutable history

Use local email/password authentication with Argon2id hashes and opaque expiring/revocable bearer sessions whose tokens are hashed in PostgreSQL. Bootstrap normal local accounts through a secure CLI; no committed default passwords. Next.js holds browser sessions in HttpOnly SameSite cookies and proxies bearer calls server-side; check origin/CSRF for cookie-authenticated mutations, use Secure cookies over HTTPS and loopback HTTP only for local development. Tokens stay out of localStorage/logs. Direct API tests use bearer auth. Owners manage organization memberships; self-registration/email delivery is not required for the local target.

Demo identity selection issues the same session type for allowlisted seed users only when explicit demo mode is active. It is disabled in normal mode and cannot mint arbitrary tenants/roles. Demo Compose binds user-facing services to loopback by default; exposing a shared demo requires a separate access decision.

Store normalized tenant-owned parties, obligations, receipts, reservations, evidence metadata and command records; retain immutable JSONB wire snapshots and raw decimal strings. Use PostgreSQL NUMERIC without a forced scale for arithmetic storage, never floating point. Every cross-object relation checks tenant ownership, with scoped queries and composite constraints where applicable. Reserve/release shared own funds atomically to avoid allocating the same cash to several deals.

Retain raw files in a content-addressed filesystem volume for local operation, accessed only through authorized API downloads; use a storage interface for later object storage. Validate MIME/size/hash, quarantine processing and escape rendered content. Do not expose storage paths or let filenames select filesystem destinations. Archive records rather than silently hard-delete evidence needed by obligations/audit. A local authenticated export and documented retention/deletion procedure are included; hosted retention guarantees are not invented.

### 4. Durable jobs, outboxes and metering

HTTP mutations atomically authenticate/authorize, compare revisions, claim idempotency identity, append revision/events, reserve resources and enqueue durable work. Replay lookup precedes stale-revision rejection; reuse with a changed canonical body returns conflict. Store original status/body and canonical request digest with tenant/actor/operation identity.

Workers claim rows using `FOR UPDATE SKIP LOCKED`, lease expiry, heartbeats and bounded retries. Provider effects are at least once; stable identities and outbox receipts make repeated delivery safe. A job binds its input snapshot/evidence/rule/calculator versions and cannot replace a newer revision on completion. Cancellation stops new work, preserves committed output and marks unfinished work. Provider timeouts/rate limits retain partial results.

An atomic usage ledger records successful chargeable job identity once. Preview workloads before admission. Retry/internal failure/deterministic recalculation, duplicate uploads without reprocessing, existing reads/exports and manual obligation/receipt actions do not consume enriched runs. Keep subscription entitlements separate from commodity/finance economics. Implement the documented Free/Deal Pass/Pro/Team allowances as versioned configurable policy, with test/admin provisioning and demo simulation; no payment checkout or automatic overage. Expiry preserves permitted ongoing records/actions. Emit structured request/job logs, queue metrics, provider status and stale-artifact counters without secrets or hidden chain-of-thought.

### 5. Evidence and live adapters

Use provider-neutral interfaces for search, public retrieval, FX, document/model tasks, market/logistics/finance sources and Calendar. Implement a Brave search adapter and Frankfurter v2 reference FX adapter, with configurable jurisdiction-aware official-source registry and public retrieval/normalization. Never assume an authenticated ocean freight API or bank integration exists. Quotation upload and reviewed actuals remain valid paths; missing coverage produces a quote request. Use reviewed versioned requirement cards; retrieving a changed authority page creates review work rather than silently promoting a legal conclusion.

Text/PDF extraction uses local parsers; image/scanned-PDF OCR uses an isolated Tesseract process with explicit English/Indonesian/Chinese language assets installed and verified during setup. Preserve page/region spans and original text. Extraction and optional model translation emit schema-validated candidates. An OpenAI-compatible server-side model adapter is configured through an explicit endpoint/model and private credential binding; provider-specific compatibility/access must be tested before enablement. Public search never receives private buyer/bank/contract data. Model tasks are bounded extraction, summary or explanation tied to known IDs; they have no direct balance, verification or outgoing-trade tool.

The public fetcher enforces HTTPS, DNS/IP and every redirect, rejects private/link-local/file targets, limits response size/time/type and uses the supported environment proxy/CA trust. Model/search secrets stay server-side. Live results persist retrieval time, request/provider ID when present, raw hash and normalized observations. Source terms/licensing, freshness and applicability remain part of acceptance; status 200 is not sufficient.

Credential-free mode uses synthetic adapters over bundled source files, never a browser mock API. Real uploaded documents still traverse the same extraction/review code. Offline draft generation uses deterministic templates bound to canonical values; live model assistance remains distinguishable. Separate seed/adapter policy prevents synthetic evidence from satisfying real-workspace gates.

### 6. Deterministic economics and workflow

Use one Python Decimal engine at precision at least 50, preserving source strings and explicitly applying rounding at declared output/instrument boundaries. Golden fixtures use HALF_UP to two places, including IDR for arithmetic regression; actual settlement uses its declared instrument policy. No JavaScript business arithmetic. Native currencies, FX direction/date/source, units and formula inputs stay available for drill-down.

Compute component/quote coverage, applicable minimums, producer yield/inventory allocation, buyer extras, recoverable tax and reimbursement separately. Economic cost and payment schedules are distinct. Floor includes sales-dependent charges correctly; margin differs from markup and zero revenue has undefined margin. Comparable exclusions are recorded, not normalized through an unsupported universal factor.

Cash uses dated/sequenced operating and financing events, outside commitments, buffer, actual-versus-forecast distinction and an obligation-complete horizon. Unknown same-day order yields debit-first stress. Principal affects cash, not contribution; fee-withheld loans use net proceeds. Receivable financing splits assigned settlement/reserve so the buyer receipt is not counted again. Partial, late, dispute and nonpayment scenarios expose exposure without invented credit probabilities.

Workflow services derive independent analysis/commercial/funding/goods/shipment/payment/closure dimensions and stage-specific gates. Approvals bind current hashes and purpose; counterparty agreement and settlement review require separate evidence. New facts invalidate dependent snapshots/artifacts, not history. Timeline dependencies preserve fixed deadlines, date-only semantics and actual versus forecast anchors. Goods nonconformity and unresolved critical requirements block relevant actions. Actual charges replace corresponding estimates once with variance history. Receipt verification/reversal is append-only and tenant/role-scoped; buyer paid can coexist with internal reconciling.

### 7. Browser experience

Use a workspace/deal list and guided entry, then a consistent deal shell with Overview, Evidence, Economics, Scenarios/Finance, Drafts, Readiness, Timeline and Reconciliation sections. Organization/user settings expose membership, usage and optional Calendar. Keep warnings and pending work visible beside primary results rather than hidden in logs. The UI implements all F01–F14 through these grouped screens; it does not need fourteen disconnected modules.

Default explanations are Bahasa Indonesia; source text retains its language and commercial drafts can be English. Display currencies/units and user/source timezones explicitly. Provide responsive tables, keyboard navigation and labeled controls. Poll persisted runs with bounded intervals/cancellation, expose partial outputs, and refresh on revision conflict rather than overwrite. Every visible business action hits the same authenticated API used by tests. Browser state is cache/presentation only.

### 8. Seed manifest and walkthroughs

The manifest uses deterministic natural keys, stable fixture hashes, a fixed configurable business reference date (`2026-10-16` initially), explicit timezones and relative event offsets. Auth/session/job timestamps use the real clock; the fixture clock cannot be enabled in normal mode. Every seeded resource/file is tagged with server-owned demo scope, dataset/version and source mode. Source documents use invented organizations and prominent synthetic markings.

| Dataset | Purpose and required states |
| --- | --- |
| ID reseller, coffee example | Baseline economics and buyer/supplier/finance alternatives, both sandbox and deal entry |
| CN producer, manufactured-goods example | Production inputs, prior-paid overhead and cash/economic separation, both entry modes |
| ID producer, spices to NL | Independent production/rule assumptions, both entry modes |
| CN reseller, ceramics to AE | Supplier terms and at least two line items/shipments, both entry modes |
| KE producer, dried fruit to DE | Nonhistorical lane/product; explicit classification/requirements unknowns, both entry modes |
| Adversarial/staged variants | Conflicting Chinese terms, source outage, stale review, nonconforming goods, delayed loan, partial/duplicate/reversed receipt, buyer-paid/internal-reconciling and closed |

At least three synthetic organizations support the declared domiciles, with isolated owner, admin, finance and production reviewers. The entry matrix has at least ten reproducible workspace cases, not a new product boundary. Include text, native PDF and scanned/image sources with extraction gold spans; seeded OCR/model observations are labeled synthetic even when actual local processing is used. Stage fixtures use the same domain commands and explicit event history rather than setting protected flags directly. Full causal history supports reset/replay.

The README walkthrough starts from clean exploration and also offers checkpoints for review/blocked/paid/reconciled states. Evaluators can edit facts, run jobs, compare financing, generate/download drafts, resolve gates and verify/reverse receipts. A case cannot cross from demo to real by relabeling its evidence; users create a new real workspace with independently reviewed evidence.

Seed twice without duplicates; store a manifest version and expected counts/hashes. Reset is a separate explicitly selected demo command, not a startup side effect. It verifies namespace, ownership and dependency closure before a transaction deletes/rebuilds eligible demo rows and files; mixed ownership blocks reset. Never drop the database, delete shared volumes or erase a user deal as a reset shortcut.

### 9. Acceptance gates and coverage

**Gate A — offline application/demo:** Frozen installation, migrations, seed twice, API/worker/browser startup, complete and blocked journeys, role/tenant isolation, service restart, safe reset and golden engines must pass with runtime outbound calls denied. Browser tests use Playwright and the real PostgreSQL/API/worker; no intercepted fake API responses. Seeded synthetic adapters are the explicit boundary. Component tests supplement this gate.

**Gate B — live core:** Actual search-provider call, official source retrieval for declared origin/destination/product coverage, live FX for used currencies, finance source retrieval and at least one market/logistics observation need retained receipts. Include historical ID/CN–SG regression coverage plus a declared nonhistorical example where sources are available. Every unavailable source remains a visible limitation; missing credential/access is a failed/blocked live gate, never a pass from offline fixtures. Model-assisted capabilities require a real supported model call before being advertised as live. Provider-shaped tests remain useful but do not meet this gate.

**Gate C — optional Calendar:** Real OAuth, approved insert/update/delete, retries/ETag conflict and revocation must pass before live sync enablement. The rest of the app remains usable without it.

The full local app can be demonstrated while Gate B/C prerequisites are missing, but the final report must separately state offline readiness, adapter implementation status and live validation blockers. Do not mark credential-dependent live-validation tasks complete if they did not run. This proposal supplies neither credentials nor permission to call third parties during planning.

Golden expectations are independently specified inputs/outputs, not values generated from the implementation under test:

| Synthetic fixture | Required outputs |
| --- | --- |
| ID reseller: revenue 160m, economic cost 134m, starting cash 50m, buffer 5m | Contribution 26m; minimum -52m; shortfall 57m; required own funds 107m; final cash 76m |
| Buyer deposit 56%, unchanged costs | Minimum 5.6m; shortfall 0; required own funds 49.4m |
| Buyer deposit 55% | Minimum 4m; shortfall 1m |
| Buyer 20/50/30, middle receipt before day-14 debit | Minimum 28m; required own funds 27m |
| Freight +20% | Contribution 22.8m; minimum -55.2m; shortfall 60.2m |
| USD exposures at 15000 instead of 16000 | Contribution 17m; minimum -53m; shortfall 58m |
| Buyer balance day 84 instead of 54 | Minimum -52m; negative interval length 70 days |
| Timely loan 60m, withheld fee 1m, interest 1.2m | Contribution 23.8m; minimum 7m; shortfall 0; final cash 73.8m |
| Loan first available day 15 | Minimum -46m; shortfall 51m; earlier gap remains |
| CN producer: revenue 70000, cash cost 50000, overhead allocation 3000 | Contribution 17000; minimum -16000; shortfall 19000; required own funds 39000; final cash 40000 |

Amounts in this table use the full dated schedules from the uploaded system spec §20 and General §13; fixture manifests will spell out every event and sequence. Initial FX of 16000 is synthetic. No market price, tariff, lender offering or country rule is asserted by these fixtures.

Feature and behavioral coverage:

| Product / source acceptance | Owning capability and required evidence |
| --- | --- |
| F01–F02; AT01–AT03 | workspace-access + seeded-demo; generalized entry matrix, persistence and lineage |
| F03–F05/F07; AT04–AT09, AT43, AT45–AT47 | evidence-ingestion + execution-reconciliation; actual extraction spans, source limitations, prompt-injection/tenant boundaries and live receipts |
| F06/F08; AT10–AT20 | deal-economics; golden and negative decimal/unit/coverage/cash tests |
| F09–F12; AT21–AT30 | negotiation-finance + deal-economics; stage/receivable/late-funds scenarios and rendered draft validation |
| F13–F14; AT31–AT35, AT38–AT41, AT48 | execution-reconciliation; blocked/success lifecycles, date graph and paid-versus-closed tests |
| Optional Calendar; AT36–AT37 | calendar-projection; offline replay plus separate real integration evidence |
| Concurrency/access; AT42, AT44 | workspace-access + durable-operations; PostgreSQL concurrent API requests and cross-tenant tests |
| Browser/monetization/demo continuity | workspace-ui + durable-operations + seeded-demo; browser journeys, admission/expiry and safe-reset tests |

AT01's historical eight paths are regression cases, not the permanent product scope. Country-specific authority checks such as AT46 must use the relevant rule/source evidence, never a country-label swap.

## Risks / Trade-offs

- Broad scope can produce a collection of shallow screens. Mitigation: implement vertical slices against real storage/services and require the complete browser journeys before declaring the local app done.
- JSON Schema-to-type generation can lose conditional constraints. Mitigation: retain canonical runtime request/response validation and explicit cross-field domain tests; generated types are convenience only.
- Provider access, licenses, model privacy or regional restrictions can block live acceptance. Mitigation: isolate the dependent capability, retain precise blockers and continue offline work; do not silently substitute demo evidence or mark live tasks done.
- Historical sources/rule cards can be stale. Mitigation: record source versions, dates, reviewed applicability and limits; only scope-backed coverage can be enabled.
- Local document/OCR processing adds language/runtime dependencies. Mitigation: pinned setup with verification, bounded sandboxed processors and real extraction tests; report a failing dependency rather than bypassing OCR.
- Demo reset can damage user data if ownership is ambiguous. Mitigation: namespace tags, dependency preflight, transaction/backup discipline, refusal on mixed ownership and explicit preservation tests.
- Optional calendar/network effects may complete before a crash. Mitigation: outbox identities, provider receipt lookup, ETags and retries tested against ambiguous outcomes.

## Migration Plan

Apply in dependency order: contract refinements and archived follow-ups; toolchain/services and migrations; auth/revision/job foundation; evidence; engines; negotiation/drafting; execution; UI; seeded journeys; live acceptance and optional Calendar. Each slice lands its tests and documentation alongside code.

There is no existing application database. Introduce versioned migrations and a non-destructive 2.1 snapshot importer test for future users of the draft. Retain original snapshots and seed manifest versions. Avoid irreversible down-migrations that discard receipt/audit history; use tested backup/restore or forward fixes once user data exists. Rollback demo fixtures by dataset version after dependency checks, not by dropping volumes. No deployment or publication occurs during this proposal.

## Open Questions

Only external readiness inputs remain: provider credentials, allowed domains/licensing and OAuth client/selected calendar values. These do not change the architecture or offline acceptance criteria; the corresponding live tasks remain blocked until they are supplied securely and tested. Exact dependency patches and provider-supported model IDs will be pinned/validated at implementation time rather than asserted from this planning session.
