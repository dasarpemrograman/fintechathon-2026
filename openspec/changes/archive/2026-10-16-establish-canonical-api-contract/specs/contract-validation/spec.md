# Contract Validation

## Purpose

Provide repeatable offline evidence that the canonical API contract and its embedded examples are structurally valid and reject contradictory wire payloads.

## ADDED Requirements

### Requirement: Structural failures are actionable
Contract validation SHALL reject duplicate YAML keys, invalid OpenAPI or JSON Schema, unresolved references and references outside the canonical document. It SHALL return a nonzero exit status with a diagnostic that identifies the failing location or reference.

#### Scenario: Route key is repeated
- **WHEN** the same YAML mapping contains duplicate route keys
- **THEN** validation fails rather than silently replacing the earlier route

#### Scenario: Reference is external or broken
- **WHEN** a schema or response points outside the document or to a missing local target
- **THEN** validation fails without fetching another source

### Requirement: Request and response examples are checked
Validation SHALL check embedded media-type request and response examples against their applicable schemas, including examples and schemas reached through local references. Invalid examples SHALL fail validation with operation, direction, HTTP status where relevant, and example identification.

#### Scenario: Referenced response has an invalid amount
- **WHEN** a locally referenced response example contains a numeric monetary amount where a decimal string is required
- **THEN** validation fails and identifies that response example

#### Scenario: Valid request example
- **WHEN** an embedded workspace request example satisfies its referenced schema
- **THEN** validation accepts it and includes it in request example counts

### Requirement: Examples demonstrate relevant outcomes
The canonical document SHALL contain representative accepted-job, partial-analysis, blocked-readiness, pending-receipt and error examples. Validation output SHALL report operation, request-example and response-example counts separately, without presenting zero response checks as response coverage.

#### Scenario: Queued discovery result
- **WHEN** the accepted-job example is validated
- **THEN** it demonstrates a 202 accepted envelope, typed run metadata and an authenticated polling location

#### Scenario: Blocked shipment stage
- **WHEN** the blocked-readiness example is validated
- **THEN** it contains unresolved critical conditions and structured blockers without granting shipment readiness

#### Scenario: Receipt proof recorded
- **WHEN** the receipt creation response example is validated
- **THEN** the receipt remains pending and has no verifier identity

### Requirement: Negative payloads prove rejection
Contract regressions SHALL exercise invalid request and response payloads, including contradictory accepted/completed statuses and invalid nested response fields. The suite SHALL preserve checks for protected patches, money representation and independent payment/closure states.

#### Scenario: Accepted job marked complete
- **WHEN** a test changes an accepted-job envelope to completed
- **THEN** the response validator rejects it

#### Scenario: Invalid example introduced
- **WHEN** a test introduces a schema-invalid response example in an in-memory contract copy
- **THEN** validation returns failure instead of counting the example as passed

### Requirement: Verification remains bounded and reproducible
Local commands and CI SHALL validate the same canonical file and run the same contract regressions with pinned tooling. Reports SHALL distinguish contract checks from runtime authorization, arithmetic, service and integration tests, which are outside this deliverable.

#### Scenario: Contract checks pass
- **WHEN** structural validation, all embedded examples and contract regressions pass
- **THEN** the report states contract verification succeeded without claiming the application or providers work
