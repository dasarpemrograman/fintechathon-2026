# Execution and Reconciliation

## Purpose

Keep export execution decisions aligned with actual agreements, evidence, money and obligations through goods readiness, shipment events and final reconciliation.

## ADDED Requirements

### Requirement: Derived action gates
The server SHALL derive stage-specific readiness from current agreed terms, required verified/available resources, quotation scope, goods conformity, applicable requirements and documents. Generic risk acceptance or owner approval SHALL NOT override a missing critical condition.

#### Scenario: Owner approves plan before buyer funds arrive
- **WHEN** plan review is current but required funds are not verified
- **THEN** commercial review can remain approved while procurement or shipment stays blocked with actionable conditions

### Requirement: Requirements and goods review
Authorized reviewers SHALL record requirement applicability/fulfillment and goods inspections with evidence, source versions and unresolved discrepancies. Photos alone SHALL NOT establish all quality properties; mismatches SHALL block applicable gates until corrected or a relevant agreed specification revision is evidenced.

#### Scenario: Goods fail agreed specification
- **WHEN** quality evidence shows nonconforming goods
- **THEN** shipment readiness is blocked until corrective evidence or accepted revised specifications are reviewed

### Requirement: Timeline propagation preserves agreements
The timeline SHALL distinguish proposed, agreed, forecast and actual dates, local dates/timezones and fixed/event-relative formulas. Dependency cycles and undeclared business-day calendars SHALL be rejected; forecast changes SHALL NOT silently amend contracts.

#### Scenario: Arrival forecast changes
- **WHEN** buyer payment is arrival plus 30 days and a fixed supplier deadline remains unchanged
- **THEN** buyer forecast and cash projections move while the supplier deadline and original agreement remain intact

#### Scenario: Actual acceptance is the payment anchor
- **WHEN** delivery is reported but acceptance is not verified
- **THEN** arrival does not falsely establish the actual acceptance-based payment due date

### Requirement: External actions remain evidenced records
Users SHALL record booking, shipment and externally performed exception events with evidence and authorized review. The app SHALL NOT automatically book, pay or file customs declarations, and events performed despite blockers SHALL remain exceptions rather than retrospective approvals.

#### Scenario: Shipment occurred outside the app while blocked
- **WHEN** an authorized user records evidence that goods already shipped
- **THEN** the event and unmet conditions remain in history without fabricating prior readiness

### Requirement: Settlement is verified and reversible
Transfer proof SHALL create pending verification. Authorized settlement review SHALL preserve amount, currency, value date and allocations, prevent duplicate settlement, and append partial/rejected/reversed outcomes. Fee deductions and write-offs SHALL require explicit supported adjustments.

#### Scenario: Duplicate proof and later reversal
- **WHEN** the same receipt is retried and a verified settlement is subsequently reversed
- **THEN** retry does not settle twice, reversal appends history and outstanding balances are recomputed

### Requirement: Actuals and closure stay independent of buyer payment
Reconciliation SHALL preserve initial/latest approved baselines, replace estimates with matching actual obligations once, and expose quantity, price, freight, FX, funding and timing variances. Closure SHALL require resolved liabilities, reimbursements and material disputes; buyer paid SHALL remain independent.

#### Scenario: Buyer paid while freight invoice is open
- **WHEN** buyer obligations are fully settled but the seller's freight liability is unresolved
- **THEN** buyer remains paid, internal state remains reconciling and closure returns structured blockers

#### Scenario: All declared obligations are resolved
- **WHEN** reviewed actuals and supported settlements resolve closure conditions
- **THEN** the deal closes with a reproducible reconciliation hash and final contribution
