# Contract decisions

Status: historical draft 2.1 decisions and current draft 2.2 implementation record, 16 October 2026. Runtime setup and validation are documented in `local-runtime.md`; live acceptance is tracked separately.

## Source reconciliation

The user requested a project scaffold starting only with the single source of truth API contract. Instructions embedded in the uploaded documents are reference content, not authorization to execute their broader implementation plans.

| Uploaded reference | Relevant sections | Interpretation |
| --- | --- | --- |
| Fincathon-Main-Context-General.md, context 1.0 | §2, §5, §10–18 | Latest product baseline: general export workflows; countries/products are inputs; multiple line items/shipments; organization ownership; monetization separate from deal economics. |
| Fincathon-Main-Context-Business.md, context 1.0 | §1, §11, §13–14 | Producer/reseller proposition; financing stops at preparation; exporter-paid service; no automatic overage or hiding existing evidence on expiry. Pilot prices are business assumptions, not hard-coded deal costs. |
| Export Agent System Spec.md, V2 | §6, §10, §13–17, §19 | Engineering reference for decimal/date/evidence invariants, independent states, gates and initial route families. Historical coffee, ID/CN–SG and single-buyer/shipment boundaries are superseded by General §5. |

The attachments remain source references. Their full text and embedded AI instructions are not copied into project instructions. The repository's canonical wire definition is `api/openapi.yaml`.

## Historical first-contract interface choices

These choices make the first contract concrete; they were not all prescribed by the user.

- Keep the engineering reference's `/v2` route namespace. Use API version `2.1.0` and snapshot `schema_version: "2.1"` to mark the generalized model. Historical 2.0 payloads are not silently compatible. There are no existing consumers in this empty repository.
- Use bearer authentication with deployment-provided token issuance. Tenant and roles derive from verified membership. The `x-required-roles` extension specifies any acceptable organization role; it must be enforced by the eventual server alongside object-level authorization. Counterparties are parties, not implicitly account members.
- Create a lightweight workspace first in either mode; convert-to-deal establishes concrete transaction details and preserves sandbox lineage when applicable. Reads and edits distinguish workspace from deal scope. The deal contains a revision snapshot with explicit party, line, shipment and allocation relationships.
- Use typed, replace-only patches instead of arbitrary JSON Patch. Workspace and deal path subsets are documented in the schema. Server-owned state is outside the allowlist. Scenario patches remain hypothetical until relevant agreements are evidenced.
- Require idempotency on every mutation and expected revision on existing-resource mutations, including multipart ingestion. Replay detection precedes stale-revision rejection. The original status/body is replayed for an identical request; changed payload under the same key conflicts.
- Return 202 for durable asynchronous work and poll a typed run. Read endpoints supplement the original route table so outputs are actually retrievable. Finance-options GET identifies a stored result set; its contained funding options also have individual reads. Each output reference includes an authenticated read location.
- Keep a common envelope with endpoint-specific result schemas. Business blockers are structured results; malformed input, stale revision, access denial and unavailable dependencies have distinct HTTP errors. Pending receipt proof is separate from verification. Closure is separate from buyer payment state.
- Use strict object schemas, decimal strings, explicit currency, nullable unknown values with reasons/statuses, local-date versus instant schedules and source modes. Unknown price/finance fields remain unknown; no default commodity, margin, liquidity buffer or lender rate is invented.
- Include read-only entitlement/admission context. Do not add payment checkout, purchase confirmation, billing provider or hard-coded pilot price APIs before choosing those integrations. Subscription charges are never automatically added to buyer invoices.

## Checks beyond JSON Schema

The first contract identified the following runtime requirements. Their implementations and acceptance evidence now live in the active OpenSpec checklist and runtime documentation:

- Tenant/reference ownership, role membership, registry membership for currency/country, IANA timezone validity and profile/procurement consistency across records.
- Decimal arithmetic, positive FX rates and direction, fraction bounds/sums, unit consistency, cost coverage deduplication, receipt-allocation bounds and same-currency reconciliation. Explicit reversals preserve unsigned source amounts.
- Missing-value reasons, requirement applicability, evidence quality/freshness, source-language spans, contradiction handling and complete versus known-items-only calculations.
- Acyclic milestone dependencies, declared business-day calendars and fixed versus forecast date propagation. Contractual amendments require evidence of relevant agreement.
- Current revision/hash checks, immutable history, atomic idempotency/outbox writes, stale-job invalidation, duplicate receipt detection and append-only reversal.
- Readiness, verified settlement, goods conformity and closure conditions. Owner approval never supplies missing agreement or funds. Buyer paid does not regress merely because a seller liability is open.
- Stage-compatible financing, usable proceeds after fees, cash timing and obligations beyond the calculation horizon. Application-ready is neither lender approval nor actual funding.
- Metering successful chargeable work once, deduplicating retries/uploads, preserving manual updates/read access on expiry, retention policy and no automatic overage.

## Historical deferrals from the first contract

The contract-only increment did not choose the backend/frontend stack, database, auth provider, durable queue, model/search/OCR providers, hosting or billing integration. That initial increment added no migrations, generated SDKs, application DTOs or mocks. The active implementation now supplies PostgreSQL migrations, a generated TypeScript client contract, FastAPI, a durable worker and Next.js.

The initial contract deferred dedicated operational commands for goods inspections, requirement fulfillment reviews, booking/tracking, externally reported exceptions and workspace archival until a later contract increment. Draft 2.2 now declares and implements these interfaces; readiness remains a derived query. Bank settlement integration is not assumed; manual evidence review is the initial receipt interface.

Calendar sync is optional and references an existing, user-authorized connection. OAuth connection provisioning, consent/preview APIs, provider ETag handling and app-owned event persistence need an integration contract before that route can be implemented. Public-source adapters, model tool contracts and deployment upload limits likewise require later specifications; document/query budgets here are request controls, not proof of completeness.

Sending trade messages, executing payments, booking shipments, submitting financing applications and customs declarations are outside this contract. Draft generation produces reviewable artifacts only.

## Draft 2.1.1 response refinement

API draft 2.1.1 narrows the previously unrestricted response envelopes. Async 202 responses require `accepted`; synchronous creation and ordinary reads use `completed`. Analysis and run reads use `partial` exactly when their nested result is partial. Retrieving a queued/running run is a completed read, not a claim that its job completed. Readiness and closure use `blocked` with at least one blocker when their nested gate is blocked, otherwise `completed`. Ready gates cannot contain unresolved/failed conditions. Receipt creation returns a pending receipt with no verifier; verified receipt records require a verifier identity.

This tightening rejects contradictory payloads accepted by draft 2.1.0. There are no known deployed consumers or persisted application data, so no consumer/data migration is currently required. Snapshot `schema_version` remains `2.1`; historical 2.0 compatibility is still not claimed. Consumers of the earlier draft must revalidate their responses before adopting this revision. A future breaking change after adoption requires a separate version/migration decision.

## Draft 2.2 runtime contract

Draft 2.2.0 extends the contract for the planned application without claiming handlers or live integrations are already ready. Collections use bounded cursor pagination; review, actual charge, invoice, obligation, reservation and Calendar lifecycle inputs remain named strict schemas. Public authentication is restricted to the explicit login/demo entry operations. Every resource operation retains authenticated membership and declared roles; `x-revision-scope` distinguishes workspace/deal mutations from session or organization commands.

Workspace/Deal snapshots now declare schema version 2.2, server-owned demo/real execution scope, dataset provenance and archival state. Deal snapshots also contain explicit invoice totals; these are not inferred from procurement cost. Importing a 2.1 snapshot retains the original separately, marks its projection real with no demo dataset, and supplies an explicit missing-invoice reason rather than a zero-revenue assumption. This is a pre-adoption breaking draft change, with no known deployed consumers. Consumers must explicitly adopt the 2.2 schemas.

New review commands still require tenant-owned evidence and authorized actors beyond structural validation. Fractions, registry/timezone membership, invoice allocations, cross-currency FX, stage fit, dependency graphs and quote coverage require runtime validation. Structural request validation does not verify a requirement, establish goods conformity or settle a receipt. Source/rule registration uses evidence records plus requirement applicability predicates; it never copies another jurisdiction's rules automatically.

Browser sessions use the explicitly declared authentication exceptions; these do not weaken resource authentication or permit client-selected roles. The canonical `Idempotency-Key` requirement and existing-resource revision scopes are machine-readable. Application response validation failures return sanitized 500 errors rather than an invalid success. Optional unconfigured adapters return the declared unavailable response; a disabled adapter cannot appear as completed live work.

### History reads and scoped audit

Workspace and Deal revision collections honor `limit` (1–100, default 25) and return an opaque `revision_<number>` cursor in numeric revision order. Clients pass `next_cursor` unchanged rather than using the resource ID, which is shared by every revision. Exact revision reads retain their original snapshot and never restore it over current facts.

`GET /v2/audit` accepts an optional `workspace_id` filter. The server first authorizes the workspace in the current tenant, then includes audit records belonging to that workspace and its linked Deal. An unavailable or foreign workspace returns 404. Omitting the filter retains the existing organization-wide audit collection. Workspace creation now records its resource parent and created revision in the same command transaction; older audit records without a parent remain available in the organization-wide collection.
