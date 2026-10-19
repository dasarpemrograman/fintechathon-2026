# Proposal

## Why

A new developer currently has to choose between host and cloud-specific instructions, prepare secrets and PostgreSQL manually, install separate toolchains, and provision an account before seeing the app. The recent Windows setup also needed Linux-compatible execution and an owned WSL keepalive; these should be handled by a repeatable entry point rather than rediscovered for each machine.

## What Changes

- Add one documented command after cloning: `./dev up` on a supported POSIX shell or `.\dev.ps1 up` on Windows. Docker with a compatible Compose plugin is the only required application runtime; no host Python, Node, uv, API keys, or Google login are needed for first launch.
- Default to the existing seeded, outbound-isolated demo. Build pinned images, prepare missing local configuration, migrate, start API/worker/web, and seed through existing services. Print the local URL and explicit demo status only after readiness succeeds.
- Keep normal mode an explicit `up --mode normal` choice. Expose an `account` command that runs the existing hidden-password bootstrap inside the container. Provider configuration and Calendar consent remain optional later steps.
- Add `doctor` for actionable prerequisites/readiness diagnostics and `stop` for project-owned shutdown without deleting data. Running `up` again preserves credentials, stored work, and unrelated services; it must not silently change the mode of an existing running instance.
- Make the README start with this short path. Keep native toolchain development, managed-cloud setup, and live integration instructions as linked advanced paths.

## Capabilities

### New Capabilities

- `developer-onboarding`: Credential-free first launch, explicit runtime modes, recoverable diagnostics, and local developer account provisioning through a small command interface.

### Modified Capabilities

- `durable-operations`: Extend reproducible local lifecycle requirements to cover the one-command entry point, safe repeated startup, and project-scoped shutdown.

## Impact

Expected implementation touches root launcher scripts, shared bootstrap/readiness helpers, Compose lifecycle wiring, README, and local runtime documentation. Reuse the existing migrations, seed, health checks, account bootstrap, pinned images, and offline network boundary. No application wire-schema or database-schema change is expected.

This proposal covers developer environment onboarding. Product signup, a new end-user wizard, automatic Docker installation, dependency upgrades, hosted deployment, and automatic provider/OAuth enablement are outside this change. This workflow creates planning artifacts only; implementation requires a subsequent apply request.
