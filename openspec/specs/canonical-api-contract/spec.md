# canonical-api-contract Specification

## Purpose

Give Fincathon consumers one authoritative wire contract for export workflows while keeping behavioral requirements and runtime implementation claims distinct.

## Requirements

### Requirement: Single wire definition
The project SHALL define routes, wire schemas, examples and command/result semantics in `api/openapi.yaml` using OpenAPI 3.1 and JSON Schema 2020-12. OpenSpec SHALL record behavior and acceptance scenarios without maintaining duplicate DTOs, enums or endpoint tables.

#### Scenario: Consumer needs a wire schema
- **WHEN** a client, server validator or API reference is prepared
- **THEN** its wire definitions are derived from the canonical OpenAPI document
- **AND** explanatory Markdown and OpenSpec do not replace that definition

### Requirement: General export entry
The contract SHALL support sandbox and deal entry for producer and reseller profiles without requiring an upload or restricting products, countries or currencies to historical fixtures. General identifiers SHALL NOT imply verified regulatory or integration coverage.

#### Scenario: Producer explores a new lane
- **WHEN** a producer supplies a product description and a nonhistorical country pair in sandbox mode
- **THEN** the creation payload is structurally valid without a buyer or upload
- **AND** unresolved facts and coverage remain explicit

#### Scenario: Deal has multiple fulfillment units
- **WHEN** a deal contains multiple line items and shipments
- **THEN** the wire model can represent their relationships and explicit monetary allocations without a single-shipment restriction

### Requirement: Money and unknown values remain explicit
Source amounts SHALL be unsigned decimal strings with currencies; signed metrics SHALL use explicit signed schemas. Unknown values SHALL carry a reason or status rather than becoming numeric zero. The contract SHALL distinguish complete calculations from known-items-only results.

#### Scenario: Floating point source amount
- **WHEN** a monetary input uses a JSON number, exponent or negative source amount
- **THEN** schema validation rejects the payload

#### Scenario: Partial funding analysis
- **WHEN** required cost or obligation inputs remain unknown
- **THEN** the response can represent partial analysis and missing inputs without claiming a complete funding requirement

### Requirement: Authority and mutation preconditions
The contract SHALL derive tenant and reviewer authority from authenticated membership, require idempotency keys for mutations and expected revisions for existing-resource mutations, and forbid patches to server-owned state. Runtime enforcement SHALL remain explicitly unimplemented in this contract-only deliverable.

#### Scenario: Client attempts to self-verify payment
- **WHEN** receipt creation or a fact patch attempts to set verification or buyer-payment state directly
- **THEN** the wire schema rejects that authority field or protected patch path

#### Scenario: Mutation is replayed
- **WHEN** the same actor repeats an operation with an identical canonical request and idempotency key
- **THEN** the specified server behavior is to replay the original status and body before rejecting a now-stale revision
- **AND** a different request with the same key is specified to conflict

### Requirement: Response status matches outcome
Response schemas SHALL constrain envelope status to outcomes permitted by the operation and HTTP status. A 202 response SHALL use `accepted`; synchronous reads SHALL NOT use `accepted`; a blocked readiness or closure result SHALL NOT claim execution readiness. Partial analysis SHALL remain expressible.

#### Scenario: Accepted work claims completion
- **WHEN** a 202 job response envelope uses `completed`
- **THEN** schema validation rejects it

#### Scenario: Readiness has unresolved critical conditions
- **WHEN** a readiness response reports a blocked gate
- **THEN** its envelope reports `blocked` with structured blockers
- **AND** a contradictory completed-ready representation is rejected by the response schema

#### Scenario: Analysis has partial inputs
- **WHEN** an analysis output reports partial completeness
- **THEN** its envelope can report `partial` with warnings and unresolved inputs

### Requirement: Business authority dimensions remain separate
The contract SHALL distinguish owner review, counterparty agreement, execution readiness, receipt verification, buyer payment and internal closure. Financing SHALL stop at preparation, generated trade artifacts SHALL remain drafts, and Calendar SHALL remain an optional approved projection.

#### Scenario: Buyer settled while seller liability is open
- **WHEN** verified buyer payment is complete and a seller invoice remains unresolved
- **THEN** the model permits buyer payment to remain paid while internal closure is reconciling

#### Scenario: Financing pack generated
- **WHEN** an application pack is prepared
- **THEN** the result does not imply lender approval, disbursement or submission

### Requirement: Compatibility is declared
The contract SHALL declare its API and snapshot versions and identify schema tightening or breaking changes before consumers adopt them. It SHALL NOT claim compatibility with historical payloads or implementation readiness from schema validation alone.

#### Scenario: Allowed response statuses are narrowed
- **WHEN** this proposal is applied to the draft contract
- **THEN** the decision record identifies the status tightening and whether any consumers require migration
- **AND** the validation report limits its claims to contract behavior
