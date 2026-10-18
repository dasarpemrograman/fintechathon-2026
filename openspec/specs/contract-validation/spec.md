# contract-validation Specification

## Purpose

Provide repeatable offline evidence that the canonical API contract and its embedded examples are structurally valid and reject contradictory wire payloads.

## Requirements

### Requirement: Structural failures are actionable
Contract validation SHALL reject duplicate YAML keys, invalid OpenAPI/JSON Schema and unresolved/external references, including `$dynamicRef`. It SHALL handle supported local dynamic references with correct scope or reject them explicitly before any retrieval. Failures SHALL return nonzero with a location/reference diagnostic.

#### Scenario: Route key is repeated
- **WHEN** the same YAML mapping contains duplicate route keys
- **THEN** validation fails rather than silently replacing the earlier route

#### Scenario: Reference is external or broken
- **WHEN** a schema or response points outside the document or to a missing local target
- **THEN** validation fails without fetching another source

#### Scenario: Unused component declares an external dynamic reference
- **WHEN** an otherwise valid document includes an unused schema with an external `$dynamicRef`
- **THEN** offline validation fails before any network request

#### Scenario: Local dynamic reference is unsupported or unresolved
- **WHEN** a schema uses a local dynamic reference the validator cannot resolve with correct semantics
- **THEN** validation rejects it explicitly rather than counting it as checked

### Requirement: Request and response examples are checked
Validation SHALL check embedded media-type request and response examples against their applicable schemas, including examples and schemas reached through local references. Invalid examples SHALL fail validation with operation, direction, HTTP status where relevant, and example identification.

#### Scenario: Referenced response has an invalid amount
- **WHEN** a locally referenced response example contains a numeric monetary amount where a decimal string is required
- **THEN** validation fails and identifies that response example

#### Scenario: Valid request example
- **WHEN** an embedded workspace request example satisfies its referenced schema
- **THEN** validation accepts it and includes it in request example counts

### Requirement: Examples demonstrate relevant outcomes
The canonical document SHALL contain accepted-job, partial-analysis, blocked-readiness, pending-receipt, complete closure-response and error examples. Each SHALL validate against its full operation schema. Output SHALL report separate operation/request-example/response-example counts without claiming zero checks as coverage.

#### Scenario: Queued discovery result
- **WHEN** the accepted-job example is validated
- **THEN** it demonstrates a 202 accepted envelope, typed run metadata and an authenticated polling location

#### Scenario: Blocked shipment stage
- **WHEN** the blocked-readiness example is validated
- **THEN** it contains unresolved critical conditions and structured blockers without granting shipment readiness

#### Scenario: Receipt proof recorded
- **WHEN** the receipt creation response example is validated
- **THEN** the receipt remains pending and has no verifier identity

#### Scenario: Complete closure response is mutated
- **WHEN** a valid full closure response is changed to contradict its gate/envelope or omit required Deal fields
- **THEN** validation against the actual operation schema rejects it without extracting only a conditional fragment

### Requirement: Negative payloads prove rejection
Contract regressions SHALL exercise invalid request and response payloads, including contradictory accepted/completed statuses and invalid nested response fields. The suite SHALL preserve checks for protected patches, money representation and independent payment/closure states.

#### Scenario: Accepted job marked complete
- **WHEN** a test changes an accepted-job envelope to completed
- **THEN** the response validator rejects it

#### Scenario: Invalid example introduced
- **WHEN** a test introduces a schema-invalid response example in an in-memory contract copy
- **THEN** validation returns failure instead of counting the example as passed

### Requirement: Verification remains bounded and reproducible
Local commands and CI SHALL validate the same canonical file with pinned tooling. Reports SHALL distinguish contract checks, runtime authorization/arithmetic, browser/service tests and credential-dependent live acceptance. Contract success alone SHALL NOT imply application or integration readiness; offline success SHALL NOT mark unexecuted live checks passed.

#### Scenario: Contract checks pass
- **WHEN** structural validation, all embedded examples and contract regressions pass
- **THEN** the report states contract verification succeeded without claiming the application or providers work
