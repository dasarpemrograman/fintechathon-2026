# Local Lifecycle Delta

## MODIFIED Requirements

### Requirement: Reproducible local lifecycle
A documented single-command local workflow SHALL prepare missing configuration, migrate storage, start web/API/worker dependencies, seed demo data and verify readiness using pinned dependencies and verified downloads. Repeated startup and restart SHALL preserve credentials and non-demo user data. Stop SHALL affect only the selected project runtime without deleting volumes; destructive reset SHALL remain limited to explicit demo-owned records.

#### Scenario: Fresh checkout is prepared
- **WHEN** documented local setup and startup commands complete on the supported toolchain
- **THEN** an authenticated representative UI/API journey succeeds and the application remains usable after service restart

#### Scenario: Startup is repeated after developer work
- **WHEN** the developer runs the same startup command after modifying local application data
- **THEN** existing credentials, original files and non-demo history survive without an implicit reset
- **AND** a matching healthy runtime is reused rather than duplicated

#### Scenario: Developer stops the local stack
- **WHEN** the developer invokes the documented stop command
- **THEN** only project-owned services and any project-owned runtime helper stop
- **AND** database/file volumes and unrelated processes remain intact
