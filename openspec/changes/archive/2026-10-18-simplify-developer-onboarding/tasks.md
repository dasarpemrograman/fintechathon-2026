# Tasks

## 1. Establish the developer command and prerequisite checks

- [x] 1.1 Add the root POSIX and PowerShell entry points with matching `up`, `stop`, `doctor`, and `account` behavior, documented mode syntax, checkout-relative paths and explicit Compose project support; verify argument/help/exit behavior and paths containing spaces without host Python, Node or uv on PATH.
- [x] 1.2 Implement native Docker and Windows default-WSL backend preflight plus read-only diagnostics and ownership/port/mode conflict detection; verify controlled missing-tool/daemon/Compose-feature and unrelated-service cases leave the machine unchanged, and document supported backends and recovery commands alongside the implementation.

## 2. Deliver the credential-free first launch

- [x] 2.1 Add the shared container-executed bootstrap for missing private configuration and database secrets; verify first-run permissions, preservation of existing `.env`/credentials/encryption material, no secret output or image inclusion, and refusal to replace secrets for existing storage.
- [x] 2.2 Wire the existing pinned Compose build, migration, worker, web and seed services into default demo startup with staged output and bounded readiness checks; verify a real seeded HTTP/demo login journey, internal-network isolation, and nonzero diagnostic results for seed, migration and worker failures instead of false readiness.
- [x] 2.3 Replace README's primary setup sequence with the prerequisite and OS-appropriate one-command demo path, expected URL/mode and stop command; retain linked native/cloud/provider references and verify the copied instructions against a clean checkout with no API keys or personal account.

## 3. Preserve explicit normal-mode and lifecycle behavior

- [x] 3.1 Add explicit normal-mode startup and safe repeated-start behavior without implicit mode changes or reseeding real work; verify normal demo-shortcut rejection, same-mode reuse, changed-mode conflict, unchanged credentials and persisted non-demo records, and document the deliberate mode-switch sequence.
- [x] 3.2 Expose the existing normal account bootstrap through the launcher with an interactive hidden password prompt; verify authenticated API/browser login and organization membership, weak-password handling, noninteractive refusal, duplicate-account preservation and absence of passwords in arguments/logs/files, with a short normal-mode setup example.
- [x] 3.3 Implement project-owned stop and Windows WSL keeper identity/lifetime handling; verify the Windows URL remains reachable after the launching command returns, stop affects only matching owned services/helpers, unrelated instances survive, and volumes/configuration remain intact, with stop/recovery guidance.

## 4. Retain end-to-end onboarding evidence

- [x] 4.1 Exercise the shipped quickstart on the supported Windows/WSL and Linux paths using isolated Compose projects and fresh storage, then repeat startup and stop/restart with edited data; retain observed prerequisite, readiness, identity, persistence and secret-redaction results without claiming untested platform support.
- [x] 4.2 Run the applicable existing contract, fixture/seed, authentication, demo isolation and lifecycle regressions plus strict OpenSpec validation; record executed counts and remaining limitations, and verify only onboarding/lifecycle behavior changed and all unrelated developer data remains preserved.

## Workflow follow-up

- Review this proposal before requesting implementation through the apply workflow.
- Verify implementation evidence and sync/archive the change through the corresponding workflows after its tasks are complete.
