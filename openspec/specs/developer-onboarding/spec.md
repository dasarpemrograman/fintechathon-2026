# developer-onboarding Specification

## Purpose

Let a developer reach a working, clearly labeled local application from a checkout with minimal prerequisites, recoverable failures, and preserved local data.

## Requirements

### Requirement: One-command credential-free first launch
The documented developer entry point SHALL prepare and start the seeded demo with one command after checkout. The first-launch path SHALL require only the supported host shell and a working container runtime with compatible orchestration tooling. It SHALL NOT require host application-language runtimes, provider keys, or a personal account to reach the demo.

#### Scenario: Windows developer starts from a clean checkout
- **WHEN** the developer runs the documented PowerShell entry point with a supported working container backend and no host application toolchain or provider credentials
- **THEN** the app is prepared, migrated, started and seeded without additional setup commands
- **AND** the output identifies the local URL and synthetic demo mode

#### Scenario: POSIX developer starts from a checkout containing spaces
- **WHEN** the developer runs the documented shell entry point from a checkout whose path contains spaces
- **THEN** the same demo journey succeeds without editing repository paths or installing a host application toolchain

### Requirement: Actionable prerequisite checks
Startup SHALL check required tools, daemon access, compatible orchestration configuration, and conflicting local runtime state before changing application data. Failure SHALL return nonzero with the failed check and a specific recovery action. Diagnostics SHALL NOT install software, alter global machine settings, or terminate unrelated services automatically.

#### Scenario: Container backend is unavailable
- **WHEN** the runtime command, daemon, or required orchestration feature is unavailable
- **THEN** startup explains the missing prerequisite and the relevant recovery action before generating credentials or starting services

#### Scenario: Another process owns a required port
- **WHEN** a required local port belongs to an unrelated process
- **THEN** startup identifies the port conflict without killing that process or silently selecting another application origin

### Requirement: Preserve local configuration and secrets
First launch SHALL generate only missing installation configuration and private local credentials. Existing configuration and credentials SHALL be preserved and excluded from version control, images and diagnostic output. Missing secrets for existing persistent storage SHALL produce recovery guidance rather than silently replacing credentials. Initial setup SHALL leave live Calendar writes disabled.

#### Scenario: Developer already has a populated environment file
- **WHEN** onboarding runs against an existing checkout with configured secrets
- **THEN** those values and the installation encryption material remain unchanged and are not printed
- **AND** onboarding does not enable live Calendar delivery

#### Scenario: Existing database has lost its password file
- **WHEN** persistent application storage exists but its required local secret is missing
- **THEN** startup stops with restore/recovery guidance without generating a replacement password or deleting the storage

### Requirement: Explicit runtime mode
The first-launch default SHALL be the labeled offline demo, with synthetic providers and outbound isolation. Normal operation SHALL require an explicit mode choice. Repeated startup SHALL reuse a matching healthy runtime and SHALL NOT silently switch an already-running runtime's mode. Provider configuration and Google consent SHALL remain separate optional steps.

#### Scenario: Developer selects normal mode
- **WHEN** the developer explicitly starts normal mode
- **THEN** demo identity shortcuts are unavailable and the app uses normal authentication
- **AND** absent provider credentials do not prevent local deterministic workflows or become synthetic live success

#### Scenario: Requested mode differs from a running instance
- **WHEN** a developer requests startup in a different mode from the existing running project
- **THEN** the command explains the current mode and the explicit stop/start sequence without replacing the running instance automatically

### Requirement: Secure local developer account command
Normal-mode onboarding SHALL offer a documented account-provisioning command using the existing local account policy. Password entry SHALL be hidden and SHALL NOT be supplied in command arguments, printed, or saved as a plaintext convenience file. Provisioning SHALL NOT reset an existing account implicitly or introduce a default shared password.

#### Scenario: Developer provisions a normal-mode owner
- **WHEN** the developer supplies account and organization details and enters a valid password at the hidden prompt
- **THEN** the existing authentication flow accepts that account and its verified organization membership

#### Scenario: Requested account already exists
- **WHEN** provisioning encounters an existing account
- **THEN** it explains the conflict without changing that account's credentials or memberships

### Requirement: Honest readiness and recovery
The entry point SHALL report preparation stages and distinguish a starting or failed component from a usable app. Demo readiness SHALL require completed migration and seeding, responsive web/API services, and a current matching worker heartbeat. Failure SHALL retain private diagnostic logs and identify a recovery command without claiming that live integrations passed.

#### Scenario: Worker or seed fails
- **WHEN** containers start but the worker heartbeat is stale or seeding fails
- **THEN** startup exits nonzero with the responsible stage and diagnostic location instead of announcing the app ready

#### Scenario: Local environment is diagnosed
- **WHEN** the developer runs the documented diagnostic command
- **THEN** it reports prerequisite and runtime state without changing persisted application data or exposing secrets
