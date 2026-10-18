# seeded-demo Specification

## Purpose

Let evaluators reproduce the full local export workflow without provider credentials while exercising the real persistence, calculation, job and authorization paths.

## Requirements

### Requirement: Explicit offline mode
The seeded demo SHALL run without provider credentials or outbound network requests after dependencies are installed. It SHALL use the normal API, storage, worker, engines and UI with synthetic adapters, persistent demo labeling and dataset-scoped provenance; synthetic evidence SHALL NOT satisfy readiness in a real workspace.

#### Scenario: Demo is used with outbound access denied
- **WHEN** a fresh seeded local instance is exercised with external calls prohibited
- **THEN** documented demonstration journeys complete through real persisted application operations without hidden provider calls

#### Scenario: Synthetic evidence is referenced outside demo scope
- **WHEN** a real workspace attempts to rely on a seeded quotation or reviewed demo receipt
- **THEN** the reference is rejected or excluded from real readiness rather than treated as actual evidence

### Requirement: Versioned repeatable seed
The seed SHALL have stable natural keys, a versioned manifest and a fixed configurable business reference date. Reseeding SHALL be idempotent, preserve user-owned records and reproduce documented initial values and derived outputs. Runtime job/session clocks SHALL remain real; deterministic business-date controls SHALL be demo/test-only.

#### Scenario: Seed command runs twice
- **WHEN** an unchanged demo manifest is applied twice
- **THEN** no duplicate tenant, deal, event, receipt, artifact or usage charge is created and expected checksums/counts stay stable

### Requirement: Representative data coverage
Fixtures SHALL cover producer/reseller and sandbox/deal entry, at least two isolated tenants and all reviewer roles, historical ID/CN paths plus a nonhistorical product/lane, and multiple line items/shipments. Demo sources SHALL include text, PDF, scanned/OCR and ambiguous original-language examples with no personal customer data.

#### Scenario: Evaluator switches roles and tenants
- **WHEN** demo users open the seeded role-specific views
- **THEN** permitted actions differ correctly and attempts to access another tenant's documents, jobs or receipts fail

#### Scenario: Historical fixture is not a product boundary
- **WHEN** the evaluator opens the generalized producer fixture outside ID/CN–SG and a multi-shipment fixture
- **THEN** both use the same editable workflows and engines without commodity-specific application code

### Requirement: Complete walkthrough states
Demo fixtures and walkthroughs SHALL demonstrate exploration/conversion, source review, profitable-but-cash-negative analysis, negotiation/financing, controlled draft review, blocked/corrected goods readiness, partial/verified/reversed receipts and buyer-paid/internal-reconciling closure. Staged states SHALL have reproducible causal history rather than decorative UI flags.

#### Scenario: User follows the successful lifecycle
- **WHEN** the walkthrough resolves agreements, resources, conformity and documents through authorized actions
- **THEN** readiness changes only after those conditions are met and final closure follows reconciled obligations

#### Scenario: User follows a blocked lifecycle
- **WHEN** critical costs, agreement, funds or goods evidence remain unresolved
- **THEN** outputs stay partial or blocked even if the owner reviews the plan

### Requirement: Golden economics and failure cases
The demo SHALL include independently specified numeric golden expectations and adversarial fixtures for stale revisions, source outage, duplicate/reversed receipts, changed quotes and delayed finance. Seed values SHALL remain clearly synthetic, including simulated lender terms and regulatory cards.

#### Scenario: Baseline and funding alternative are calculated
- **WHEN** the baseline and synthetic timely-loan fixtures are evaluated
- **THEN** observed outputs match the documented 26/-52/57 million baseline and 23.8/7/0 million funded contribution/minimum/shortfall respectively

### Requirement: Reset is scoped and recoverable
Reset SHALL require explicit demo selection, verify demo ownership and dependencies, and affect only the chosen dataset namespace. It SHALL refuse non-demo or mixed-ownership destructive operations and SHALL leave non-demo records and shared infrastructure intact.

#### Scenario: User-owned deal exists beside demo data
- **WHEN** a demo reset is requested
- **THEN** only eligible demo-owned records are reset and the unrelated deal and files survive
- **AND** a dependency crossing into user-owned data blocks the reset with an explanation

### Requirement: Demonstration acceptance is observable
Browser/API checks SHALL prove the documented workflows, persistence after restart, seed repeatability, role isolation and safe reset. The run report SHALL distinguish offline demo success from unrun, failed or passed live acceptance and SHALL NOT claim production readiness.

#### Scenario: Demo checks pass without live credentials
- **WHEN** all offline journeys pass but live providers are unconfigured
- **THEN** the report marks the demo ready and lists live gates as blocked rather than passed
