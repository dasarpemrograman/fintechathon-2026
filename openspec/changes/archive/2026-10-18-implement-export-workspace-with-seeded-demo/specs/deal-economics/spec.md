# Deal Economics

## Purpose

Provide deterministic and explainable export economics that distinguish economic contribution, buyer charges, available cash and uncertainty over time.

## ADDED Requirements

### Requirement: Exact decimal and FX calculations
Calculations SHALL use decimal arithmetic, preserve source precision and native currency amounts, and apply explicit rounding policies. Conversions SHALL record direction, date and source; invalid amounts, unsupported units and invalid margin constraints SHALL fail domain validation.

#### Scenario: FX rate changes
- **WHEN** an unlocked currency exposure is recalculated under a new referenced rate
- **THEN** all affected values change consistently while original amounts and prior snapshots remain available

#### Scenario: Invalid target margin
- **WHEN** a target margin is at least one or a source amount is nonfinite or signed where prohibited
- **THEN** the engine returns a structured input error instead of an invented price

### Requirement: Cost coverage and payer treatment
Costing SHALL separate payer, economic bearer, coverage, reimbursement, recoverable tax and economic expense. Quote-based freight SHALL use applicable minimums, dimensions, units and tariff rules; unknown costs SHALL remain unknown rather than disappear or duplicate covered charges.

#### Scenario: Synthetic W/M tariff with minimum
- **WHEN** gross weight is 2000 kg, volume is 3 cubic metres, rate is USD100 per W/M and minimum is USD350
- **THEN** the main freight charge is USD350 before separately applicable charges

#### Scenario: Buyer charge paid in advance by seller
- **WHEN** seller pays a buyer-borne charge that is covered by a reimbursement obligation
- **THEN** cash consumption is shown without counting the charge twice as seller expense or buyer invoice revenue

### Requirement: Producer cost and funding separation
Producer costs SHALL account for materials, labor, process, attributable overhead, yield and capacity. Prior-paid inventory and allocated overhead SHALL remain economic costs; batch cash funding SHALL reflect actual payment timing rather than only deal allocation.

#### Scenario: Producer regression fixture
- **WHEN** the declared CNY fixture has revenue 70000, economic cost 53000 and cash cost 50000 with starting cash 20000 and buffer 3000
- **THEN** contribution is 17000, minimum cash is -16000, shortfall is 19000 and final cash is 40000 under its dated schedule

### Requirement: Two-sided pricing and numeric lineage
Pricing SHALL expose seller floor and normalized destination comparables separately, with assumptions, rejected observations and evidence/formula lineage. Unsupported PPP multipliers and unsupported credit/default probabilities SHALL NOT be invented.

#### Scenario: Seller floor exceeds market observations
- **WHEN** the calculated floor is above comparable market prices
- **THEN** the application displays the economic conflict rather than forcing a profitable-looking recommendation

### Requirement: Dated cash and declared completeness
Cash calculations SHALL include event sequence, buffers, outside commitments, verified actuals, forecasts and full outstanding-obligation/debt horizon. Unknown material inputs SHALL produce a known-items-only result rather than a complete minimum funding requirement.

#### Scenario: Profitable reseller still cannot fund order
- **WHEN** the synthetic baseline starts with 50 million, receives 32 million and pays 50 million on day 0, pays 78 million on day 14 and 6 million on day 24, then receives 128 million on day 54
- **THEN** contribution is 26 million, minimum cash is -52 million, buffer shortfall is 57 million and required own funds are 107 million for a 5 million buffer

#### Scenario: Same-day order is unknown
- **WHEN** receipt and payment sequence on a date cannot be established
- **THEN** a debit-first stress case and uncertainty warning accompany the result

### Requirement: Buyer payment stress scenarios
Users SHALL compare on-time, delayed, partial, disputed and unpaid buyer receipts without changing verified actuals. Stress results SHALL show amount, duration, remaining exposure and fixed lender/supplier obligations without claiming an unsupported probability.

#### Scenario: Buyer receipt shifts beyond loan maturity
- **WHEN** a hypothetical buyer payment is delayed while loan maturity remains fixed
- **THEN** the forecast extends through repayment and exposes any new funding gap
