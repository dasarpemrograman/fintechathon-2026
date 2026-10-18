# evidence-ingestion Specification

## Purpose

Turn source documents and researched public evidence into traceable, reviewable facts without granting uploaded or fetched content authority over the application.

## Requirements

### Requirement: Document preservation and extraction
The application SHALL store original supported text, PDF and image uploads with hashes, limits and tenant ownership. Extraction SHALL preserve original-language spans, page/region locators, units and ambiguity; translation SHALL NOT replace original evidence.

#### Scenario: Ambiguous Chinese contract
- **WHEN** extraction finds an unclear currency or a net-30 clause without a payment anchor
- **THEN** original Chinese spans and candidate interpretations remain available
- **AND** the application does not silently choose a currency or due date

#### Scenario: Scanned source needs OCR
- **WHEN** an allowed scanned PDF or image is ingested
- **THEN** the configured OCR path produces locatable candidates or an explicit processing limitation
- **AND** neither outcome is presented as reviewed facts automatically

### Requirement: Autonomous contextual discovery
Users SHALL start budgeted discovery from known product/jurisdiction facts without uploads. Discovery SHALL search and fetch relevant official, market, logistics, FX and finance evidence using approved non-confidential fields and jurisdiction-appropriate languages.

#### Scenario: Public research from sandbox
- **WHEN** a sandbox has only a product hypothesis and destination
- **THEN** the worker begins relevant discovery and retains missing inputs as questions
- **AND** buyer identities, bank details and private contract text are excluded from public queries

### Requirement: Provenance and source quality
Evidence SHALL retain source identity, mode, retrieval/effective dates, raw hash, applicability, limitations and reviewer status. Syndicated sources SHALL be deduplicated; snippets, retail prices and incompatible quantities SHALL NOT become verified executable quotations.

#### Scenario: Search snippet lacks fetched support
- **WHEN** a search result cannot be fetched or supports only a retail listing with mismatched MOQ
- **THEN** the claim shows its limitation or comparator exclusion and does not become a confirmed B2B price

#### Scenario: Quotation covers several cost components
- **WHEN** a quotation is normalized
- **THEN** covered components, validity and applicable shipment scope remain explicit for cost deduplication

### Requirement: Reviewed facts and requirements
Conflicting extracted or researched values SHALL remain separate until an authorized review resolves them. Requirement cards SHALL record jurisdiction/product predicates, responsible party, source version, review and fulfillment evidence instead of copying unrelated jurisdiction rules.

#### Scenario: Supplier and buyer quantities conflict
- **WHEN** two source documents disagree on a quantity affecting calculation or conformity
- **THEN** both candidates and their spans remain visible and dependent readiness stays unresolved

### Requirement: Adapter outcomes and live evidence
Live adapters SHALL return attributed outcomes and retrieval receipts; unavailable, expired, rate-limited and cached results SHALL remain distinguishable. A live acceptance claim SHALL require actual search, official-source, FX, finance and market/logistics receipts for declared coverage.

#### Scenario: Required provider credentials are absent
- **WHEN** a live discovery category needs unavailable credentials or access
- **THEN** the run retains completed work, reports the precise blocker and does not substitute demo data as live

#### Scenario: Live lane acceptance is evaluated
- **WHEN** the release check examines declared product and jurisdiction coverage
- **THEN** provider response/time/source hashes and parsed observations prove actual retrieval
- **AND** unsupported charges or requirements remain unknown even when HTTP requests succeeded

### Requirement: Untrusted content isolation
Fetched and uploaded content SHALL NOT change roles, balances, tool permissions or endpoints. Retrieval SHALL enforce public HTTPS destinations and redirect/DNS checks; document processing SHALL be isolated with size/type/time limits and sanitized rendering.

#### Scenario: Source requests privileged action
- **WHEN** a document contains instructions to reveal secrets, approve payments or fetch a private address
- **THEN** those instructions do not execute and no privileged state or private request is created
