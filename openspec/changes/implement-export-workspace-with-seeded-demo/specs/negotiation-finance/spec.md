# Negotiation and Finance

## Purpose

Help exporters compare terms and funding alternatives, then prepare evidence-linked commercial drafts and financing packs without taking external trade actions.

## ADDED Requirements

### Requirement: Joint terms comparison
Users SHALL compare baseline, buyer-focused, supplier/production-input-focused, financing and combined scenarios using the same immutable calculation inputs. Ranking SHALL follow explicit owner constraints and expose required agreements, residual risks and changed fields.

#### Scenario: Combined negotiation improves liquidity
- **WHEN** a scenario changes buyer deposit and supplier payment timing together
- **THEN** contribution and dated cash are recalculated together and remain hypothetical until relevant parties agree

### Requirement: Published financing fit
Financing screening SHALL evaluate entity jurisdiction, stage, amount, currency, instrument, tenor, recourse, security, documents and earliest draw against sourced terms. Missing pricing SHALL remain unknown; hypothetical pricing SHALL be explicitly labeled.

#### Scenario: Post-shipment product cannot fund production
- **WHEN** a product cannot draw until after shipment but the shortage precedes shipment
- **THEN** it is marked incompatible for that gap and the earlier deficit remains visible

#### Scenario: Published lender rate is absent
- **WHEN** a product page provides eligibility but no rate
- **THEN** cost remains quote-required or uses a separately labeled user assumption

### Requirement: Net proceeds and debt economics
Funding scenarios SHALL distinguish nominal principal, usable draw, withheld fees, interest, repayment, assigned receivables and reserve release. Loan principal SHALL NOT become contribution revenue, and the same buyer receipt SHALL NOT be counted twice.

#### Scenario: Synthetic loan covers baseline gap
- **WHEN** 60 million is drawn before day-14 baseline costs, with 1 million withheld, 1.2 million interest and 60 million repayment after the day-54 receipt
- **THEN** usable draw is 59 million, minimum cash is 7 million, contribution is 23.8 million and final cash is 73.8 million

#### Scenario: Same loan arrives late
- **WHEN** that loan is first available on day 15
- **THEN** day-14 minimum remains -46 million and the earlier funding condition is not satisfied

### Requirement: Financing application preparation
The application SHALL produce a versioned preparation pack with business profile, amount/tenor/purpose, funds-use schedule, scenarios, provider-required versus recommended documents, source dates and gaps. Application-ready SHALL NOT imply submission, lender approval or disbursement.

#### Scenario: Preparation checklist is complete
- **WHEN** an authorized reviewer confirms the declared pack inputs and checklist
- **THEN** the pack can become application-ready with provider links and evidence
- **AND** no lender application is transmitted

### Requirement: Controlled commercial artifacts
Recommendations, buyer/supplier messages, agreements and clause/amendment drafts SHALL bind current scenario, analysis, evidence and template hashes. Numeric/date fields SHALL match calculated data; legal and missing fields SHALL remain explicit placeholders. Sending and signing SHALL remain user actions outside this app.

#### Scenario: Draft amount differs from calculated scenario
- **WHEN** generated prose changes a price, quantity or payment date
- **THEN** rendering validation rejects the discrepancy and the artifact cannot become reviewed

#### Scenario: Evidence changes after owner review
- **WHEN** a source or selected scenario changes a reviewed draft basis
- **THEN** its prior hash and content remain available but review is stale for new action
