# Proposal

## Why

Fincathon currently has a validated API contract but no running application. Implement the exporter workflow behind that contract and provide a reproducible seeded demo so users can evaluate real persisted behavior without credentials, while preserving separate evidence for live integrations.

## What Changes

- Deliver a local web application covering the fourteen product feature groups: exploration, producer/reseller fulfillment, discovery, document review, requirements, costing/pricing, numeric lineage, dated cash, buyer-risk stress cases, negotiation, financing preparation, drafts, execution gates and reconciliation.
- Add authenticated organizations, role checks, immutable revisions, transactional commands, durable jobs, document storage, audits and entitlement/usage enforcement.
- Implement deterministic decimal engines and evidence-backed decisions; keep agreement, owner approval, verified funds, shipment readiness and internal closure independent.
- Add a repeatable offline demo using the same API, database, worker and UI as normal operation, with conspicuous synthetic provenance, deterministic reference dates, isolated tenants, staged walkthroughs and safe reset.
- Implement provider-neutral live search, controlled retrieval, reference FX, extraction/model and finance/market/logistics evidence adapters. Real live acceptance remains required for live claims; absent credentials produce explicit blockers rather than synthetic success. Include optional Google Calendar connection/preview/sync, disabled until real acceptance passes.
- Extend the canonical contract for authentication, collections, evidence/operational review, actuals, audit and Calendar connection management before implementing their consumers. **BREAKING:** advance the pre-adoption draft/snapshot contract to 2.2 with explicit migration notes rather than silently replacing 2.1 payloads.
- Resolve the archived verification warning about dynamic references and add a complete closure-response regression.

Confirmed target: complete local app plus offline seeded demo and separately validated live adapters. Hosted deployment, payment checkout, loan submission, trade-message sending, actual booking/payment/customs execution and claims of production readiness are outside this change.

## Capabilities

### New Capabilities

- `workspace-access`: Authentication, organizations, tenant roles and persistent sandbox/deal revisions.
- `evidence-ingestion`: Document extraction, autonomous discovery, source receipts, provenance and reviewed facts.
- `deal-economics`: Cost coverage, producer/reseller economics, pricing, FX and dated cash/stress calculations.
- `negotiation-finance`: Comparable scenarios, financing fit/economics, application packs and controlled drafts.
- `execution-reconciliation`: Requirements/goods review, milestones, readiness, receipts, actuals and closure.
- `workspace-ui`: Usable end-to-end exporter workspace, traceable decisions and accessible error states.
- `durable-operations`: Durable jobs/outboxes, replay/concurrency guarantees, usage, audits and local lifecycle.
- `calendar-projection`: Optional authorized connection, preview and one-way owned-event synchronization.
- `seeded-demo`: Reproducible synthetic data, deterministic replay, safe reset and demo acceptance journeys.

### Modified Capabilities

- `canonical-api-contract`: Replace the contract-only runtime limitation with actual server enforcement and define the additional operational surfaces contract-first.
- `contract-validation`: Enforce local-only dynamic-reference policy and add complete closure response coverage while retaining existing examples and negative cases.

## Impact

A later apply adds `apps/web`, `services/api`, `services/worker`, shared domain/adapters, database migrations, seed fixtures, local orchestration and integration/browser tests. Proposed stack: Next.js/TypeScript, Python/FastAPI and PostgreSQL with a database-backed job queue. `api/openapi.yaml` remains the sole wire-schema source; Python is extended from tooling into the backend. Existing contract checks remain required. This command creates planning artifacts only; application implementation starts with a later apply.
