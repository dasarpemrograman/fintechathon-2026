# Workspace Access

## Purpose

Give exporter organizations authenticated access to persisted export workspaces and immutable transaction history with enforceable tenant and role boundaries.

## ADDED Requirements

### Requirement: Authentication and organization membership
Users SHALL authenticate before accessing organization resources. Tenant and permitted roles SHALL come from verified membership; expired or revoked sessions SHALL be rejected. Demo identity selection SHALL be available only in explicit local demo mode.

#### Scenario: Valid member signs in
- **WHEN** an active member authenticates and selects an organization they belong to
- **THEN** subsequent reads and writes use that verified membership
- **AND** a client-supplied tenant identifier cannot expand access

#### Scenario: Demo entry attempted outside demo mode
- **WHEN** a request uses the demo identity entry route with demo mode disabled
- **THEN** the server refuses the request without issuing a session

### Requirement: Tenant and reviewer isolation
All resource references, uploads, jobs and exports SHALL enforce object-level tenant access. Owner, export admin, finance reviewer and production/procurement roles SHALL have explicitly allowed actions; external counterparties SHALL NOT implicitly gain review authority.

#### Scenario: Another tenant's evidence identifier is used
- **WHEN** a user reads or mutates a resource using an identifier belonging to another tenant
- **THEN** the operation is denied without revealing the resource or accepting the reference

#### Scenario: Unauthorized reviewer verifies payment
- **WHEN** an export admin without the required review role submits receipt verification
- **THEN** the operation is rejected and no settlement state changes

### Requirement: Persistent exploration and deal conversion
Sandbox and deal workspaces SHALL persist product/jurisdiction facts and exporter profile without requiring a buyer or document. Conversion SHALL preserve sandbox evidence, assumptions and revision lineage without upgrading indicative evidence into confirmed quotations.

#### Scenario: Exploration becomes a concrete transaction
- **WHEN** a sandbox with incomplete research is converted after a buyer inquiry
- **THEN** the deal retains its source revision and incomplete evidence labels after process restart

### Requirement: General transaction relationships
Deals SHALL support multiple parties, product lines, shipments, payment obligations and explicit allocations. Producer fulfillment SHALL represent inputs, yield, capacity and economic/cash costs independently of reseller finished-goods purchases.

#### Scenario: Producer uses previously paid inventory
- **WHEN** a producer allocates inventory to two shipment lines
- **THEN** economic cost remains visible without inventing a new supplier payment or duplicating the allocation

### Requirement: Revision and history integrity
Fact changes SHALL create immutable revisions, preserve contradictions and invalidate affected analyses, drafts and approvals. The server SHALL reject stale mutations rather than overwrite newer facts or historical agreements.

#### Scenario: Freight quote changes after review
- **WHEN** a newer freight quotation changes an approved cost basis
- **THEN** a new revision and invalidation record are created
- **AND** the original reviewed snapshot remains retrievable
