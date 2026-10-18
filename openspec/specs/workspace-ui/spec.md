# workspace-ui Specification

## Purpose

Make the complete export decision workflow usable through a browser while exposing the evidence, uncertainty and action prerequisites behind each result.

## Requirements

### Requirement: Complete browser workflow
Members SHALL navigate persisted workspace/deal lists, entry forms, evidence/fact review, costs/pricing/cash, scenarios/finance, drafts, requirements/goods, timeline, receipts and reconciliation through role-appropriate screens. Every supported action SHALL call the real API rather than update browser-only business state.

#### Scenario: User completes a deal journey
- **WHEN** a user edits facts, runs analysis, reviews a scenario and records a receipt through the UI
- **THEN** the same state is observable through authorized API reads and after browser/server restart

### Requirement: Evidence behind decisions
Users SHALL drill from a material number or readiness condition to its formula, inputs, source/assumption, applicable revision and freshness. Unknown, conflicted, cached, synthetic and stale results SHALL be visibly distinguishable from current reviewed evidence.

#### Scenario: User inspects an incomplete freight estimate
- **WHEN** the displayed cash forecast excludes an unknown freight charge
- **THEN** the interface shows the known-items limitation and links to the missing-input request

### Requirement: Jobs and actionable failures
The UI SHALL show durable job progress, partial outputs, retry/cancellation state, structured errors and stale-revision conflicts. A blocked action SHALL explain unmet conditions; a successful request SHALL NOT imply completed background work or business readiness.

#### Scenario: Analysis provider fails after partial work
- **WHEN** a run retains some evidence but another source is unavailable
- **THEN** users can inspect completed outputs and the specific failure without a fabricated success screen

### Requirement: Review and comparison controls
Users SHALL compare scenario contribution, cash minimum, timing and risk together, inspect draft placeholders, and deliberately confirm scoped review actions. Role restrictions, agreement requirements and payment verification SHALL remain visible and server-enforced.

#### Scenario: Ordinary admin views receipt proof
- **WHEN** a user lacks settlement verification authority
- **THEN** receipt evidence remains viewable as permitted but verification is unavailable and a direct unauthorized request still fails

### Requirement: Accessible localized presentation
The UI SHALL support keyboard navigation, labeled controls, readable tables, usable narrow layouts and explicit loading/empty/error states. Bahasa Indonesia SHALL be the default explanation language, with original source text retained and English commercial drafts available; money/dates SHALL follow declared units and timezone.

#### Scenario: Local-date deadline is displayed
- **WHEN** a date-only deadline is viewed from another timezone
- **THEN** its contractual local date is preserved and its timezone is stated rather than shifted as an instant

### Requirement: Entitlement and demo transparency
The UI SHALL preview chargeable work and allowance before new provider jobs, retain existing evidence/exports and manual updates on expiry, and display a persistent synthetic-demo banner in demo mode. It SHALL NOT silently initiate overage purchases or present sample lender/rule data as current verified advice.

#### Scenario: Allowance is exhausted
- **WHEN** the user requests new enriched work after allowance is used
- **THEN** admission explains the restriction while existing records and permitted manual receipt/obligation actions remain usable
