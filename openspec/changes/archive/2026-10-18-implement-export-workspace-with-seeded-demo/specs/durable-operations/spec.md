# Durable Operations

## Purpose

Make local application commands, background work, usage accounting and audit history recoverable, reproducible and observable across failures and process restarts.

## ADDED Requirements

### Requirement: Atomic mutation replay
Revision checks, state changes, idempotency receipts, own-fund reservations and job/outbox creation SHALL commit atomically. Identical retries SHALL replay the original result before stale-revision rejection; changed requests under a reused key SHALL conflict.

#### Scenario: Concurrent funds reservation
- **WHEN** two commands attempt to reserve the same remaining organizational funds
- **THEN** at most one conflicting reservation succeeds and balances remain consistent

#### Scenario: Client retries after response loss
- **WHEN** a mutation committed but its response was lost
- **THEN** the retry returns the original status/body without another state change or charge

### Requirement: Durable bounded jobs
Accepted jobs SHALL persist with input revision, budgets, progress and outputs. Workers SHALL recover abandoned claims, use bounded retries and support cancellation without losing committed partial output. Stale outputs SHALL NOT overwrite newer deal revisions.

#### Scenario: Worker stops during discovery
- **WHEN** a leased job is interrupted and the worker restarts
- **THEN** unfinished work can resume without duplicating committed evidence or external-effect identities

#### Scenario: Inputs change while analysis runs
- **WHEN** a job finishes against an older snapshot
- **THEN** its result is retained as stale history and cannot replace the current analysis or approve action

### Requirement: Usage and entitlements stay separate from economics
Successful chargeable external work SHALL be metered once using job/idempotency identity. Internal failures, retries, deterministic recalculation, duplicate documents requiring no reprocessing, reads/exports and manual obligation/receipt updates SHALL NOT consume extra enriched runs. Admission SHALL prevent hidden overage.

#### Scenario: Entitlement expires during an existing deal
- **WHEN** the plan no longer permits new enriched work
- **THEN** evidence, warnings, exports and permitted existing-obligation/payment recording remain accessible under retention policy

### Requirement: Auditable sensitive operations
Audit records SHALL capture actor, tenant, action, purpose, revisions, hashes, data mode, time and state changes without secrets or hidden chain-of-thought. Sensitive original files and connector tokens SHALL be access-controlled; retention/export/delete behavior SHALL respect dependencies and audit obligations.

#### Scenario: Reviewer reverses a receipt
- **WHEN** an authorized settlement reversal is committed
- **THEN** the verifier, reason, superseded record, evidence and balance effect are auditable without rewriting prior history

### Requirement: Reproducible local lifecycle
A documented local workflow SHALL migrate storage, start web/API/worker dependencies, seed demo data and verify functional readiness. Restart SHALL preserve non-demo user data; destructive reset SHALL be limited to explicit demo-owned records. Setup SHALL use pinned dependencies and verified downloads.

#### Scenario: Fresh checkout is prepared
- **WHEN** documented local setup and startup commands complete on the supported toolchain
- **THEN** an authenticated representative UI/API journey succeeds and the application remains usable after service restart

### Requirement: Observable readiness and release evidence
Health/readiness and operational reports SHALL distinguish database/worker readiness, queue lag, provider failures, stale artifacts and live validation state. Releases SHALL report executed tests and failed/skipped live checks separately instead of treating open ports or demo success as proof of integration readiness.

#### Scenario: Live credentials are missing
- **WHEN** local demo acceptance passes but a required live adapter has not been exercised
- **THEN** the report states demo-ready and live validation blocked, naming the unverified capability
