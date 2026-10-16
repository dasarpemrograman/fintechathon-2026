# Calendar Projection

## Purpose

Project selected app milestones into an optional external calendar without making that calendar authoritative for contractual terms or export readiness.

## ADDED Requirements

### Requirement: Optional authorized connection
Users SHALL explicitly connect a calendar using OAuth, a selected writable calendar and minimum workable scope. Stored refresh credentials SHALL be encrypted and revocable. Live sync SHALL remain unavailable until configured access and real integration acceptance are verified.

#### Scenario: No calendar is connected
- **WHEN** a user evaluates or executes a deal without a calendar connection
- **THEN** the built-in timeline and gates remain fully usable

### Requirement: Approved projection preview
The application SHALL preview selected milestone fields, timezone/date semantics and create/update/delete effects before the first write or a material change. A current scoped approval SHALL bind the exact projection hash; attendees and confidential contract/pricing fields SHALL be excluded by default.

#### Scenario: Approved projection changes before delivery
- **WHEN** a milestone revision invalidates an approved calendar payload
- **THEN** the stale write is refused and a fresh preview/approval is required

### Requirement: Owned event identity and retry safety
Sync SHALL use stable app-owned event identity, transactional outbox delivery, provider ETags and recorded projection versions. Retries SHALL NOT duplicate events; external edits SHALL produce conflicts instead of silently overwriting user changes or amending deal terms.

#### Scenario: Provider accepted insert before worker stopped
- **WHEN** the job retries after an ambiguous insert response
- **THEN** it resolves the same owned event rather than creating a second event

#### Scenario: External event was changed
- **WHEN** an ETag no longer matches during update
- **THEN** the user sees a conflict and no contract or agreement is changed automatically

### Requirement: Revocation and demo isolation
Revocation SHALL disable future sync while preserving the built-in timeline. Offline demonstrations SHALL use a labeled synthetic calendar adapter with no OAuth or external writes and SHALL NOT satisfy live Calendar acceptance.

#### Scenario: Token is revoked
- **WHEN** provider access fails after revocation
- **THEN** sync reports the authorization failure without corrupting milestones or repeatedly retrying indefinitely
