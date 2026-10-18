# Fincathon roadmap: Fithra, Wisa and Faiz

Planning baseline: 18 October 2026, commit `ed437ff`.

This roadmap divides the export workspace into features owned by three engineers with equal technical skills. Each owner covers the complete feature: browser experience, API, domain logic, persistence, tests and documentation. Each feature has a second engineer responsible for review and its handoff to dependent features.

## Current baseline and task status

The [archived implementation checklist](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/tasks.md) and [latest verification](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification.md) report **74/74 implementation tasks complete**. This roadmap assigns ongoing ownership and a team takeover of that implementation. Owners should reuse the existing code, reproduce the relevant behavior, and fix or scope any gaps they establish.

Unchecked items below mean **pending team verification and acceptance**, not evidence that a feature is missing. For each package, track `To review → In progress → In review → Done`, or `Blocked` with its dependency and next action. A task can be completed with verified existing behavior; code changes are necessary only when a gap is found. Link the evidence and any resulting issue or PR beside the task before checking it off.

The latest live report accepts only the three declared goods/routes: Indonesia→Singapore green coffee, China→Singapore bare printed circuit boards, and Kenya→Germany plain dried mango. Calendar acceptance passed, its test event and grant were removed, and normal live writes remain disabled. Older blocker descriptions in verification history are historical; use [the latest live results](docs/live-acceptance-results.md) when deciding what still needs work. Application tests were not rerun to produce this roadmap.

`R01`–`R21` are new roadmap package IDs. The original grouped `F01`–`F14` coverage remains in the [feature matrix](docs/verification.md#coverage-by-feature-and-source-acceptance); these IDs do not redefine those source feature numbers.

## Ownership and workload

Scope points are initial relative size estimates: **3 = medium**, **5 = large**. They measure the breadth of ownership, not days or measured remaining implementation effort. All three engineers start with seven packages and 31 points. Rebalance after baseline verification if the discovered work differs significantly.

| Engineer | Owned packages | Points | Reviews |
| --- | --- | ---: | --- |
| Fithra | R01, R04, R07, R10, R13, R16, R19 | 31 | Faiz's packages |
| Wisa | R02, R05, R08, R11, R14, R17, R20 | 31 | Fithra's packages |
| Faiz | R03, R06, R09, R12, R15, R18, R21 | 31 | Wisa's packages |

| ID | Feature or supporting capability | Owner | Reviewer | Points | Milestone |
| --- | --- | --- | --- | ---: | --- |
| R01 | Accounts, organizations and roles | Fithra | Wisa | 5 | 1 |
| R02 | Exploration workspace and deal conversion | Wisa | Faiz | 3 | 1 |
| R03 | Producer and reseller fulfillment | Faiz | Fithra | 5 | 1 |
| R04 | Document upload, extraction and fact review | Fithra | Wisa | 5 | 1 |
| R05 | Discovery, public evidence and bounded model assistance | Wisa | Faiz | 5 | 1 |
| R06 | Costing, freight, pricing and FX | Faiz | Fithra | 5 | 1 |
| R07 | Numeric lineage and evidence drill-down | Fithra | Wisa | 3 | 1 |
| R08 | Dated cash flow and shared funds | Wisa | Faiz | 5 | 2 |
| R09 | Buyer payment stress and exposure | Faiz | Fithra | 3 | 2 |
| R10 | Negotiation and scenario comparison | Fithra | Wisa | 5 | 2 |
| R11 | Financing fit, economics and preparation packs | Wisa | Faiz | 5 | 2 |
| R12 | Commercial drafts and artifact review | Faiz | Fithra | 5 | 2 |
| R13 | Requirements, goods and execution readiness | Fithra | Wisa | 5 | 2 |
| R14 | Receipts, actuals, reconciliation and closure | Wisa | Faiz | 5 | 2 |
| R15 | Timeline and external shipment records | Faiz | Fithra | 3 | 2 |
| R16 | Usage, allowances and entitlement behavior | Fithra | Wisa | 3 | 2 |
| R17 | Audit, export, archival and recovery | Wisa | Faiz | 3 | 1 |
| R18 | Durable commands, jobs and diagnostics | Faiz | Fithra | 5 | 1 |
| R19 | Seeded demo and evaluator journeys | Fithra | Wisa | 5 | 3 |
| R20 | Contract, CI and integrated acceptance | Wisa | Faiz | 5 | 3 |
| R21 | Optional Google Calendar projection | Faiz | Fithra | 5 | 3 |

## Delivery sequence

Milestones describe acceptance order, not fixed calendar dates. Existing implementations and agreed contracts allow work in parallel; a dependency means its behavior must be accepted before the dependent package is closed.

| Milestone | Fithra | Wisa | Faiz | Exit condition |
| --- | --- | --- | --- | --- |
| 0 — Reproduce the baseline | Review access, extraction, lineage and gate evidence | Review entry, cash, finance and reconciliation evidence | Review fulfillment, calculations, jobs and Calendar evidence | Each owner can run the local app, identify their existing implementation/tests and record verified behavior, gaps and blockers. |
| 1 — Establish trusted inputs | R01, R04, R07 | R02, R05, R17 | R03, R06, R18 | Authorized users can create and reload a workspace, review traceable evidence, enter producer/reseller terms and inspect reproducible costs. |
| 2 — Complete the decision and execution journey | R10, R13, R16 | R08, R11, R14 | R09, R12, R15 | A deal can progress through cash analysis, stress, scenarios, drafts, readiness, verified settlement and conditional closure with actionable blocked cases. |
| 3 — Demonstrate and accept the integrated app | R19 | R20 | R21 | Offline journeys, feature evidence, integrated checks and optional Calendar behavior are reviewed; live acceptance is reported for its exact scope. |

Start the R20 acceptance inventory during milestone 0 and maintain it throughout; its final integration gate closes in milestone 3. Start with the documented [local runtime](docs/local-runtime.md) and [demo walkthrough](docs/demo-walkthrough.md). Run Python and browser suites sequentially when they share the same database, as documented in the verification history.

## Feature tasks

Each package inherits the completion rules at the end of this document. The paths below are starting points for locating existing behavior, not exclusive ownership of an entire shared file.

### R01: Accounts, organizations and roles

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** baseline local runtime.

Source: [workspace access](openspec/specs/workspace-access/spec.md). Start in `services/api/auth.py`, `services/api/store.py`, `apps/web/app/api/session/route.ts` and `apps/web/app/api/gateway/[...path]/route.ts`.

- [ ] R01.1 Verify normal account bootstrap, login, logout, session expiry/revocation and organization selection through API and browser.
- [ ] R01.2 Verify membership changes and owner, export admin, finance reviewer and production/procurement permissions; close gaps between browser controls and server authorization.
- [ ] R01.3 Check that documents, resources, jobs, artifacts and exports reject another tenant's identifiers and unauthorized references.
- [ ] R01.4 Verify HttpOnly browser sessions and mutation origin checks; confirm allowlisted demo entry works only in explicit demo mode and document local account provisioning.

**Acceptance:** authorized users retain their intended access after reload; forged roles, expired sessions and cross-tenant requests cannot read or mutate protected resources.

### R02: Exploration workspace and deal conversion

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R01.

Source: [workspace access](openspec/specs/workspace-access/spec.md). Start in `apps/web/app/components/deal-entry.tsx`, `workspace.tsx`, `services/api/handlers.py` and `services/api/commands.py`.

- [ ] R02.1 Exercise sandbox and concrete-deal entry for producer and reseller profiles without requiring an upload or an already known buyer for exploration.
- [ ] R02.2 Check workspace/deal listing, editing, pagination and reload persistence with general products, countries, parties, line items and shipments.
- [ ] R02.3 Verify sandbox-to-deal conversion preserves its original evidence, assumptions and revision lineage without promoting indicative facts to confirmed quotations.
- [ ] R02.4 Resolve entry, empty-state and stale-revision errors; retain explicit missing inputs and cover a nonhistorical lane in the user walkthrough.

**Acceptance:** a user can explore, convert and reopen a generalized deal without losing evidence or silently acquiring confirmed facts.

### R03: Producer and reseller fulfillment

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R02.

Sources: [workspace access](openspec/specs/workspace-access/spec.md), [deal economics](openspec/specs/deal-economics/spec.md). Start in `deal-entry.tsx`, `financial-entry.tsx`, `packages/domain/economics.py` and `packages/domain/dependencies.py`.

- [ ] R03.1 Verify reseller finished-goods purchases, supplier terms and allocations across multiple product lines and shipments.
- [ ] R03.2 Verify producer input quantities, unit costs, labor/process costs, overhead, usable yield and declared production capacity in forms and persisted calculations.
- [ ] R03.3 Check that previously paid inventory and allocated overhead remain economic costs without a duplicate projected payment; reject incompatible units and over-allocation.
- [ ] R03.4 Exercise producer and reseller fixtures, including the CNY producer result: contribution 17,000, minimum cash -16,000 and final cash 40,000.

**Acceptance:** both fulfillment models use explicit inputs and allocations, and distinguish economic cost from the timing of cash funding.

### R04: Document upload, extraction and fact review

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** R01, R18.

Source: [evidence ingestion](openspec/specs/evidence-ingestion/spec.md). Start in `packages/adapters/documents.py`, `extract_runner.py`, `extraction_cache.py`, `services/api/storage.py` and the evidence/review browser controls.

- [ ] R04.1 Verify authorized UTF-8, PDF, PNG and JPEG upload/download with original hashes, size/type limits and private storage.
- [ ] R04.2 Exercise actual native-text and scanned/OCR paths in English, Indonesian and Chinese; retain page/region locators, original-language spans and explicit processing failures.
- [ ] R04.3 Verify conflicting candidates, ambiguous currency/payment anchors and manual quotation evidence stay unreviewed until an authorized decision.
- [ ] R04.4 Verify reviewed fact changes create revisions, invalidate affected outputs and approvals, preserve original downloads, and expose actionable review states in the browser.

**Acceptance:** a reviewed fact can be traced to its unchanged original source; extraction alone cannot establish commercial agreement or payment verification.

### R05: Discovery, public evidence and bounded model assistance

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R02, R18.

Source: [evidence ingestion](openspec/specs/evidence-ingestion/spec.md). Start in `packages/domain/discovery.py`, `planning.py`, `model_tasks.py`, `packages/adapters/providers.py`, `network.py`, `pinned_transport.py` and `discovery-panel.tsx`.

- [ ] R05.1 Exercise budgeted official, market, logistics, finance and FX research from known product/lane inputs; keep private identities, bank data and contract bodies out of public queries.
- [ ] R05.2 Verify HTTPS retrieval, public-address pinning, redirects, proxy/TLS behavior, type/size/time limits, deduplication and attributed source receipts.
- [ ] R05.3 Review source normalization and rule-card candidates for applicability, language, freshness, coverage and exclusions; distinguish live, cached, synthetic, partial and unavailable outcomes.
- [ ] R05.4 Verify bounded model responses use allowed evidence IDs and cannot approve or mutate privileged state; document the current three-lane acceptance and any newly established gaps.

**Acceptance:** discovery produces reviewable evidence and limitations. A fetched page or search snippet cannot silently become a verified requirement, executable quote or accepted new product/lane.

### R06: Costing, freight, pricing and FX

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R03; reviewed/manual input interfaces from R04 and R05.

Sources: [deal economics](openspec/specs/deal-economics/spec.md), [calculation policy](docs/calculations.md). Start in `packages/domain/economics.py`, `pricing.py`, `cost_coverage.py`, `context_values.py` and `financial-entry.tsx`.

- [ ] R06.1 Verify Decimal money, source precision, units, FX direction/date/source and rounding; keep browser monetary values derived from the API.
- [ ] R06.2 Check payer versus economic bearer, recoverable tax, reimbursement, quote component coverage and actual-cost replacement without double-counting.
- [ ] R06.3 Exercise LCL W/M, air and FCL quotation rules, including the documented 2,000 kg / 3 m³ / USD100 W/M / USD350 minimum result of USD350.
- [ ] R06.4 Verify seller floor versus market comparables, exclusion reasons, unknown charges and floor-above-market conflicts in calculations and the browser.

**Acceptance:** known contribution and pricing are reproducible, unsupported totals remain partial, and reference FX does not establish spendable foreign funds.

### R07: Numeric lineage and evidence drill-down

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** R04, R05, R06.

Sources: [evidence ingestion](openspec/specs/evidence-ingestion/spec.md), [workspace UI](openspec/specs/workspace-ui/spec.md). Start in domain analysis outputs, immutable revision reads and `apps/web/app/components/workspace.tsx`.

- [ ] R07.1 Follow representative prices, costs, cash results and blockers to their formula, exact input revisions, evidence IDs, hashes and original source spans.
- [ ] R07.2 Verify that historical analyses resolve historical inputs and remain retrievable after a quote, fact or scenario changes.
- [ ] R07.3 Verify drill-down clearly labels assumptions, unknowns, conflicts, expiry, synthetic/cached mode and stale reviews, including permitted original-file downloads.
- [ ] R07.4 Review handoffs with Faiz for calculated fields and Wisa for source references; retain a documented trace from a displayed decision back to evidence.

**Acceptance:** users can explain a material number or blocker from stored evidence without relying on the latest mutable input or an unsupported model explanation.

### R08: Dated cash flow and shared funds

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R03, R06, R15; command guarantees from R18.

Sources: [deal economics](openspec/specs/deal-economics/spec.md), [durable operations](openspec/specs/durable-operations/spec.md). Start in `packages/domain/economics.py`, `cash_availability.py`, `services/api/commands.py` and the financial entry/timeline views.

- [ ] R08.1 Verify cash snapshots, outside commitments, minimum buffers, dated obligations, native currencies and complete liability horizons.
- [ ] R08.2 Check debit-first ordering when same-day sequence is unknown, conservative rounding and known-items-only results when material cost/timing is missing.
- [ ] R08.3 Exercise concurrent organization cash reservation/release; ensure another deal cannot use the same available funds and reservations do not masquerade as payments.
- [ ] R08.4 Reproduce the IDR baseline: contribution 26m, minimum cash -52m, buffer shortfall 57m, required own funds 107m and final cash 76m; expose the result and missing-input states in the UI.

**Acceptance:** a profitable deal can remain visibly unfunded; forecasts, verified resources and shared funds reservations retain their distinct meanings.

### R09: Buyer payment stress and exposure

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R08, R15.

Source: [deal economics](openspec/specs/deal-economics/spec.md). Start in `packages/domain/economics.py`, scenario outputs and the exposure views in `workspace.tsx`.

- [ ] R09.1 Exercise on-time, delayed, partial, disputed and unpaid buyer scenarios with explicit amount and timing assumptions.
- [ ] R09.2 Check that stress changes only unsettled forecasts, retains verified receipt history and keeps supplier deadlines and loan maturities fixed unless explicitly changed.
- [ ] R09.3 Show negative-cash duration, remaining receivable exposure, native-currency limitations and missing assumptions without inventing default probabilities.
- [ ] R09.4 Verify a buyer payment delayed beyond loan maturity exposes the new funding gap through the full horizon and can be compared from the browser.

**Acceptance:** stress comparisons explain cash and exposure consequences without changing actual payments or presenting assumptions as a credit forecast.

### R10: Negotiation and scenario comparison

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** R07, R08, R09.

Source: [negotiation and finance](openspec/specs/negotiation-finance/spec.md). Start in `packages/domain/comparison.py`, `economics.py`, `scenario-editor.tsx` and the scenario comparison views.

- [ ] R10.1 Exercise immutable buyer, supplier/production-input and combined term scenarios against the same baseline and evidence revisions.
- [ ] R10.2 Verify deposit/balance, supplier timing and production changes recalculate together rather than leaving inconsistent obligations or totals.
- [ ] R10.3 Check ranking against explicit owner constraints: margin, liquidity buffer, delivery deadline, allowed changes and credit tenor; retain unknowns and required counterparties.
- [ ] R10.4 Verify comparison shows contribution, cash minimum, timing, residual risk and changed fields; selected hypothetical terms cannot silently amend the live deal.

**Acceptance:** a user can compare baseline and joint alternatives, identify the relevant agreements, and retain the unchanged historical baseline.

### R11: Financing fit, economics and preparation packs

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R05, R08, R10.

Source: [negotiation and finance](openspec/specs/negotiation-finance/spec.md). Start in `packages/domain/finance.py`, `financing.py`, `finance-entry.tsx` and finance-pack generation.

- [ ] R11.1 Verify sourced product fit by jurisdiction, entity, instrument, stage, currency, amount, tenor, security, recourse and documents; keep unpublished pricing unknown.
- [ ] R11.2 Exercise net loan draws, withheld fees, interest, principal, assigned receivables and reserve release without double-counting the buyer receipt.
- [ ] R11.3 Reproduce timely funding at contribution 23.8m / minimum cash 7m / final cash 73.8m, and the day-15 draw retaining the earlier -46m minimum.
- [ ] R11.4 Verify a versioned pack contains requested terms, native-currency funds-use schedules, provider-required/recommended documents, sources and gaps; expose incompatible or incomplete products in the browser.

**Acceptance:** post-shipment funding cannot solve a pre-shipment gap, and application-ready means a prepared pack with no lender submission, approval or verified disbursement implied.

### R12: Commercial drafts and artifact review

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R07, R10; R11 for finance-related content.

Source: [negotiation and finance](openspec/specs/negotiation-finance/spec.md). Start in `packages/domain/artifacts.py`, review handlers and browser artifact/review controls.

- [ ] R12.1 Exercise recommendations, buyer/supplier messages, agreements and clause/amendment drafts using the current analysis/scenario/evidence/template hashes.
- [ ] R12.2 Verify exact calculated prices, quantities and dates; keep missing legal terms as placeholders and internal contribution/supplier details out of unrelated counterparty drafts.
- [ ] R12.3 Check Indonesian/English rendering, authorized downloads, immutable artifacts and review becoming stale after its underlying evidence or terms change.
- [ ] R12.4 Verify deliberate artifact review is scoped to the exact content and remains distinct from counterparty acceptance and execution permission; keep delivery/signing outside the app.

**Acceptance:** downloaded artifacts are labeled drafts, reproduce their bound inputs and cannot inherit a current review from different content.

### R13: Requirements, goods and execution readiness

**Status:** In review; [technical evidence](docs/roadmap/R13-acceptance.md). Numbered technical checks complete; Wisa’s package review remains required.

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** R04, R05, R08, R12, R15.

Source: [execution and reconciliation](openspec/specs/execution-reconciliation/spec.md). Start in `packages/domain/workflow.py`, `services/api/review_handlers.py`, `review-controls.tsx` and readiness/goods screens.

- [x] R13.1 Verify requirement applicability and fulfillment review retain product/lane predicates, responsible parties, source versions and supporting evidence. [Evidence](docs/roadmap/R13-acceptance.md).
- [x] R13.2 Exercise measured goods inspection, declared specifications, discrepancies and corrective evidence; a photograph alone cannot establish conformity. [Evidence](docs/roadmap/R13-acceptance.md).
- [x] R13.3 Verify separate owner review, relevant counterparty agreement, available/verified resources, goods and document conditions feed server-derived stage gates. [Evidence](docs/roadmap/R13-acceptance.md).
- [x] R13.4 Exercise blocked and successful procurement/production/shipment paths; show actionable conditions and preserve stale approval/history without allowing a generic risk acceptance to bypass critical blockers. [Evidence](docs/roadmap/R13-acceptance.md).

**Acceptance:** approved-but-unfunded and buyer-paid-but-nonconforming cases remain blocked at the appropriate stage until their specific missing conditions are resolved.

### R14: Receipts, actuals, reconciliation and closure

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R06, R08, R13, R15.

Source: [execution and reconciliation](openspec/specs/execution-reconciliation/spec.md). Start in `services/api/reconciliation.py`, `settlement_adjustments.py`, `packages/domain/settlement.py`, `variance.py` and payment/closure screens.

- [ ] R14.1 Exercise pending proof, authorized verification, partial allocation, duplicate prevention and append-only reversal with amount/currency/value-date history.
- [ ] R14.2 Check actual charges replace matching estimates once, preserve initial/latest-approved baselines and produce quantity, price, freight, FX, funding and timing variances.
- [ ] R14.3 Verify evidenced bank-fee deductions, reimbursements and write-offs; reversing a receipt must not silently enlarge an approved write-off.
- [ ] R14.4 Exercise buyer-paid/internal-reconciling and fully closed journeys through API and browser; confirm open seller liabilities, disputed items and unreviewed actuals produce closure blockers.

**Acceptance:** buyer payment and internal closure remain independent; closure reflects verified remaining balances, actual costs and supported resolution evidence.

### R15: Timeline and external shipment records

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R02, R03.

Source: [execution and reconciliation](openspec/specs/execution-reconciliation/spec.md). Start in `packages/domain/dates.py`, workflow/review handlers and the built-in timeline views.

- [ ] R15.1 Verify fixed and event-relative milestones, proposed/agreed/forecast/actual dates, declared timezones and business-day calendars; reject dependency cycles.
- [ ] R15.2 Exercise changed arrival forecasts and verified acceptance anchors: forecasts may move while fixed supplier deadlines and agreements remain intact.
- [ ] R15.3 Check local-date funding and milestone displays preserve the date and timezone; reported delivery cannot automatically verify contractual acceptance.
- [ ] R15.4 Verify booking/shipment records require evidence and blocked external actions retain their exception reason and unmet conditions without retroactive readiness.

**Acceptance:** the built-in timeline remains authoritative for its recorded app state and usable without Calendar; recording an external shipment does not perform a carrier booking or clear blockers.

### R16: Usage, allowances and entitlement behavior

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** R01, R18.

Sources: [durable operations](openspec/specs/durable-operations/spec.md), [pilot allowances](docs/local-runtime.md#pilot-allowances). Start in `packages/domain/entitlements.py`, `config/plans-v1.json`, `scripts/set_plan.py` and usage/settings views.

- [ ] R16.1 Verify workload/allowance previews and versioned Free, Deal Pass, Pro, Team and explicitly provisioned institutional terms.
- [ ] R16.2 Check admission reserves pending workload and successful chargeable work is metered once; failures, retries, cached duplicate uploads and deterministic recalculation do not add charges.
- [ ] R16.3 Exercise included-pool/add-on expiry and user/active-deal limits; existing evidence, exports and permitted manual obligation/receipt actions remain accessible on expiry.
- [ ] R16.4 Verify usage screens explain restrictions and provisioning is audited; subscription policy stays separate from deal economics and introduces no hidden overage purchase.

**Acceptance:** the organization can see and explain its consumption and admission decisions without losing permitted ongoing deal work.

### R17: Audit, export, archival and recovery

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** R01, R02, R18.

Sources: [durable operations](openspec/specs/durable-operations/spec.md), [recovery procedure](docs/local-runtime.md#export-archival-and-recovery). Start in storage/command history, authenticated export handlers, migrations and runtime documentation.

- [ ] R17.1 Verify actor/tenant/action/revision/hash audit records and authenticated history/export reads preserve required evidence without exposing secrets.
- [ ] R17.2 Exercise archival and dependency-aware retention, including original documents and historical schema-2.1 projections; clarify that JSON export alone is not a full backup.
- [ ] R17.3 Rehearse the documented PostgreSQL plus private-file/encryption-key backup and restore in a separate isolated database/volume; verify original hashes and authorized historical reads.
- [ ] R17.4 Record the restore version, commands, result and recovery limits privately where needed, and update the public runbook with reproducible sanitized instructions.

**Acceptance:** the team can retrieve a deal's history and demonstrate a complete isolated recovery. Prior verification did not establish a fresh disaster-recovery restore, so that evidence must be produced before closing R17.3.

### R18: Durable commands, jobs and diagnostics

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R01 and baseline storage.

Source: [durable operations](openspec/specs/durable-operations/spec.md). Start in `services/api/commands.py`, `services/worker/jobs.py`, `heartbeat.py`, `liveness.py`, adapter budgets and runtime scripts.

- [ ] R18.1 Exercise atomic state/revision/idempotency/job writes: identical retries replay the original response before stale-revision rejection, while changed requests under the same key conflict.
- [ ] R18.2 Verify job claims, leases, heartbeats, bounded retry exhaustion, cancellation and stale-result preservation across worker interruption/restart.
- [ ] R18.3 Verify transactional outbox identities and receipts supply reliable delivery primitives; hand the Calendar-specific provider semantics to R21 and the metering rules to R16.
- [ ] R18.4 Check matching-mode worker health, tenant-scoped diagnostics, safe failure correlation and browser progress/partial/retry/conflict states; document startup, stop and restart behavior.

**Acceptance:** loss of an HTTP response or worker process does not duplicate state, chargeable work or external identities, and unfinished or stale work cannot appear completed/current.

### R19: Seeded demo and evaluator journeys

**Owner:** Fithra · **Reviewer:** Wisa · **Depends on:** accepted core packages R01–R18; R21 for the optional Calendar journey.

Sources: [seeded demo](openspec/specs/seeded-demo/spec.md), [walkthrough](docs/demo-walkthrough.md). Start in `packages/domain/demo.py`, `demo_stages.py`, `demo_reset.py`, `fixtures/demo/`, seed/reset scripts and browser journeys.

- [ ] R19.1 Verify versioned fixture hashes, deterministic business dates, all reviewer roles, at least ten entry workspaces, general lanes and multiple line/shipment cases.
- [ ] R19.2 Reproduce exploration, profitable-but-cash-negative analysis, negotiation, financing, drafts, blocked/corrected goods, receipts, reconciling and closed checkpoints through real services.
- [ ] R19.3 Exercise reseeding twice, restart persistence and namespace reset with an unrelated user record; reject mixed ownership and retained/live Calendar dependencies.
- [ ] R19.4 Run complete and blocked evaluator journeys with runtime outbound access denied, persistent synthetic labels, keyboard/narrow-screen use and an updated concise walkthrough.

**Acceptance:** the evaluator can reproduce causal successful and blocked histories without provider credentials, and demo evidence cannot satisfy real-workspace readiness.

### R20: Contract, CI and integrated acceptance

**Owner:** Wisa · **Reviewer:** Faiz · **Depends on:** each feature owner supplies acceptance evidence; final closure follows R19 and the R21 optional capability report.

Sources: [canonical contract](openspec/specs/canonical-api-contract/spec.md), [contract validation](openspec/specs/contract-validation/spec.md), [latest verification](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification.md). Start in `api/openapi.yaml`, `packages/contracts/`, validation/generation scripts, `.github/workflows/contract.yml` and operation/browser coverage.

- [ ] R20.1 Maintain a feature-to-requirement/test evidence inventory, including the canonical operation baseline, generated-type drift and deliberate API/snapshot compatibility decisions.
- [ ] R20.2 Run integrated contract, domain, PostgreSQL, adapter and real-service browser checks after feature handoffs; verify pinned installs, builds and the current operation inventory.
- [ ] R20.3 Review CI setup and retain actual remote CI results when a branch/PR run exists; report local evidence separately from any unexecuted remote checks.
- [ ] R20.4 Publish the reviewed team acceptance report with exact commit, environment, executed checks, feature gaps, offline readiness, scoped live evidence and optional Calendar enablement state.

**Acceptance:** every owned feature has reviewed evidence and no unresolved critical acceptance failure. The report distinguishes verified existing behavior, fixes, blocked external checks and deliberately excluded product scope.

### R21: Optional Google Calendar projection

**Owner:** Faiz · **Reviewer:** Fithra · **Depends on:** R01, R15, R18.

Sources: [Calendar projection](openspec/specs/calendar-projection/spec.md), [OAuth/runtime guide](docs/local-runtime.md#google-calendar-oauth), [live acceptance](docs/live-acceptance-results.md#calendar-lifecycle). Start in `packages/adapters/calendar.py`, `calendar_policy.py`, `calendar-panel.tsx` and `apps/web/app/oauth/calendar/callback/`.

- [ ] R21.1 Verify connection, callback recovery, selected writable calendar, actor-bound single-use OAuth state, encrypted credentials and revocation without leaking tokens.
- [ ] R21.2 Exercise selected milestone previews, exact projection-hash approval, local-date/timezone semantics and private/reminder-free payloads excluding attendees and confidential trade terms by default.
- [ ] R21.3 Verify owned stable event identity, ambiguous-insert retry, equivalent UTC-offset handling, approved update/delete and external-edit/ETag conflicts without changing deal terms.
- [ ] R21.4 Reproduce the offline journey and inspect retained real acceptance; if new live verification is needed, arrange fresh account-owner consent and approved event changes, then retain receipts and cleanup evidence. Preserve the operator enablement/reference checks at API, worker and delivery boundaries.

**Acceptance:** the app remains usable without Calendar. Synthetic delivery is never reported as a live pass; a previously accepted and now revoked test connection cannot silently reconnect or enable normal live writes.

## Dependencies and handoffs

| Handoff | Provider → consumer | Required output |
| --- | --- | --- |
| Entry and access | Fithra R01 → Wisa R02 → Faiz R03 | Authorized tenant/profile context, stable workspace/deal IDs and revisions, explicit lines/shipments/allocations. |
| Source to reviewed input | Wisa R05 + Fithra R04 → Faiz R06 + Fithra R07 | Original locators/hashes, source modes, applicability, review status, native values/units and declared quote coverage. |
| Calculations to decisions | Faiz R06/R15 → Wisa R08 → Faiz R09 → Fithra R10 | Reproducible costs, date semantics, complete/partial cash results, stress assumptions and immutable scenario references. |
| Decisions to artifacts | Fithra R10 → Wisa R11 + Faiz R12 | Scenario/analysis/evidence hashes, exact amounts/dates, owner constraints and required counterparty agreements. |
| Review to closure | Fithra R13 + Faiz R15 → Wisa R14 | Current gate conditions, requirement/goods evidence, independent agreement/funds states and verified actual-event anchors. |
| Reliable external effects | Faiz R18 → Faiz R21; Faiz R18 → Fithra R16 | Stable job/outbox identity, retries/partial outputs, admission/metering events and diagnostics. |
| Integrated demonstration | All feature owners → Fithra R19 + Wisa R20 | Feature-specific fixtures, regression evidence, known limitations and a reproducible user journey. |

## Working together without repeated conflicts

- Work in small feature branches/PRs identified by the roadmap ID. Keep one primary owner for each package; its reviewer checks both the behavior and the dependency handoff.
- Coordinate edits to shared integration files before starting: `apps/web/app/components/workspace.tsx`, `services/api/handlers.py`, `review_handlers.py`, `services/worker/jobs.py`, `api/openapi.yaml`, migration versions and the demo manifest. Agree who lands overlapping changes first and update the next branch afterward.
- Every feature owner proposes their own necessary contract change in `api/openapi.yaml` before changing consumers, regenerates types and supplies compatibility notes. Wisa coordinates the integrated contract evidence under R20; this does not transfer every API task to Wisa.
- Coordinate migration ordering, fixture IDs and shared database use. Keep feature-specific UI/domain changes together and integrate against the latest accepted interfaces.
- Each owner addresses their feature's loading, empty, error, partial, stale, role and accessibility states. Bahasa Indonesia remains the default explanation language, with original source language retained and supported English drafts available.
- Review workload and blocked dependencies after each milestone. Reassign a whole package or an explicitly numbered subtask when necessary, keeping a named owner and reviewer.

## Completion rules for every package

A package is Done when its numbered tasks have evidence and its reviewer accepts the result:

1. The user flow persists through the real API/database/worker as applicable and survives reload; browser state alone is insufficient.
2. Behavior matches the linked current capability specs and canonical API. Money uses exact domain arithmetic; unknowns, reference FX, source modes and independent review/agreement/payment/closure states retain their meanings.
3. Authorization, tenant isolation, revision/history integrity and relevant invalid/blocked cases are covered. Any changed behavior has focused regression evidence and passes its dependent checks.
4. Relevant UI behavior is usable by keyboard and at narrow widths, with clear labels, units/timezones and actionable failures.
5. Setup, usage and source limitations are documented; the task links the checked commit, relevant result and any follow-up issue/PR.
6. External provider evidence states exact scope and time. Unavailable credentials, consent or coverage remain explicit blockers; passing offline checks cannot close an unexecuted live check.

This roadmap covers the existing local app, demo and scoped integrations. Hosted deployment, payment checkout, loan submission/approval, sending/signing trade messages, actual carrier booking/payment/customs execution and expanded regulatory coverage require a separate scoped decision before becoming delivery tasks.

## Context documents

Read in this order when taking ownership:

1. [README](README.md): product summary, stack and entry points.
2. [Implementation proposal](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/proposal.md) and [design](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/design.md): original feature themes, architecture and acceptance gates.
3. [Current capability specifications](openspec/specs/): behavioral requirements; the individual source links appear under each package.
4. [Archived tasks](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/tasks.md) and [requirement/scenario evidence](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification-evidence.md): existing implementation and regression anchors.
5. [Calculation policy](docs/calculations.md) and [contract decisions](docs/contract-decisions.md): money, evidence, authority and versioning decisions.
6. [Local runtime](docs/local-runtime.md) and [demo walkthrough](docs/demo-walkthrough.md): reproduction and operating procedures.
7. [Latest verification](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification.md), [live setup](docs/live-acceptance.md) and [live results](docs/live-acceptance-results.md): latest acceptance, prerequisites and limits. Earlier [verification history](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification-history.md) explains resolved findings.

Prepared from the repository Markdown context outside skill directories, including current specs and both archived changes. The original uploaded General/Business/System documents are referenced by the contract decision record; their full text is not present in this checkout. This roadmap uses the committed project scope and records a proposed team allocation rather than attributing past implementation to an engineer.
