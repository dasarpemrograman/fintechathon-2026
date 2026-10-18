# Canonical Contract Runtime Delta

## MODIFIED Requirements

### Requirement: Authority and mutation preconditions
The server SHALL enforce authenticated tenant/reviewer authority, mutation idempotency, expected revisions for existing resources and the server-owned patch allowlist. Public authentication entry points SHALL be explicitly identified in the contract and SHALL NOT grant access before credentials or demo-only eligibility are verified.

#### Scenario: Client attempts to self-verify payment
- **WHEN** receipt creation or a fact patch attempts to set verification or buyer-payment state directly
- **THEN** the wire schema rejects that authority field or protected patch path

#### Scenario: Mutation is replayed
- **WHEN** the same actor repeats an operation with an identical canonical request and idempotency key
- **THEN** the specified server behavior is to replay the original status and body before rejecting a now-stale revision
- **AND** a different request with the same key is specified to conflict

#### Scenario: Runtime crosses the contract boundary
- **WHEN** an otherwise schema-valid mutation references another tenant or an unauthorized reviewer
- **THEN** the server rejects it before committing state or external work

## ADDED Requirements

### Requirement: Complete operational interfaces
The canonical contract SHALL cover authenticated collections/history, document and fact review, evidence/rule ingestion, requirement/goods decisions, actual charges, obligations, cash reservations, shipment exceptions, usage/audits and Calendar connection/preview lifecycle before consumers are implemented. Every declared operation SHALL have a tested implementation or an explicit feature-disabled response.

#### Scenario: A user lists and reviews workspace evidence
- **WHEN** the UI needs paginated collections and a review action absent from the prior draft
- **THEN** typed inputs, references, limits, errors, revision scope and outputs are defined in OpenAPI before the API/UI consume them

### Requirement: Runtime conforms to the canonical schemas
Requests and responses SHALL be validated against the canonical contract, with generated client types and a drift check. Domain constraints beyond JSON Schema SHALL be server-enforced. Demo/real execution scope SHALL be server-owned, and migration from draft snapshot 2.1 to 2.2 SHALL be explicit and tested.

#### Scenario: Handler returns an invalid successful payload
- **WHEN** a handler emits an incorrect decimal, missing required field or contradictory success status
- **THEN** contract verification fails and the response is not silently advertised as valid success

#### Scenario: A prior snapshot is loaded
- **WHEN** a persisted 2.1 snapshot is migrated for the 2.2 runtime
- **THEN** the original is retained and versioned migration supplies explicit unknowns instead of silently inventing evidence
