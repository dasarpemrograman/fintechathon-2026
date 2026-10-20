# Developer onboarding verification

Observed locally on 18 October 2026 for `simplify-developer-onboarding`.

## Environment and scope

The host is **Windows 10 IoT Enterprise LTSC**. The PowerShell launcher used Docker in the default Ubuntu WSL distribution; the POSIX launcher was exercised directly in that Linux environment. Docker Engine reported 29.6.1 and Compose 5.3.1. Both source checkout paths contained spaces.

Fresh source-only copies used separate projects `allexport-onboard-linux` (3012/8012) and `allexport-onboard-windows` (3013/8013), with new named storage. Neither copy received the original `.env`, `.local`, Git history, host virtual environment or node_modules. The explicit acceptance ports avoided the existing application's 3000/8000 origin. Normal first-use commands retain those default ports.

## First launch and readiness

- `bash dev up` and `dev.ps1 up` completed preparation, pinned builds, database health, installation-key checks, migrations/service startup, demo seeding and bounded readiness.
- Windows loopback remained reachable after the PowerShell command returned. A browser on Windows signed into the seeded demo and displayed synthetic workspaces, including the persisted acceptance control.
- Demo HTTP session login worked without provider keys or a personal account. Public TCP egress from the demo API was blocked; Calendar live delivery remained false.
- Host Python/Node/npm/uv traps on the POSIX execution path were not invoked. The shipped launchers execute application runtimes in containers.
- The shell entry point has Git mode 100755 and an explicit LF checkout rule.

## Configuration and isolation

- Private files created on a native Linux filesystem had mode 600. Windows `.env`, database password and keeper metadata ACLs granted only the current Windows user full control, without inherited access rules.
- Existing environment, database password and installation encryption material were preserved. Missing database secrets and missing runtime storage for an initialized installation were refused without replacement credentials.
- Docker image inspection confirmed `/app/.env` and `/app/.local/db-password` were absent. The existing build-context exclusions remain in force.
- Missing CLI/daemon/Compose, unavailable Compose wait support and invalid configuration were tested with controlled command adapters. No application configuration was generated on these failures. Native Windows adapter preflight was also tested with four controlled failure cases.
- Actual foreign-checkout ownership, active-mode conflict and occupied Linux ports were refused. An actual Windows-only TCP listener was refused before configuration creation. No port owner was stopped.
- Controlled migration, seed and worker-readiness failures produced nonzero exit status and the responsible private stage log, with no ready announcement. Stopping the real demo worker until its heartbeat expired made `doctor` return nonzero.

## Normal accounts and lifecycle

- Explicit stop/start into normal mode succeeded; demo shortcut login was refused.
- The account command was exercised through a pseudo-terminal: weak passwords failed, a valid account was created, a duplicate failed without reset, and redirected/noninteractive invocation failed.
- The password was not echoed and was supplied only through terminal input. The harness kept it in memory; no password argument or convenience file was created.
- Login through the web session endpoint succeeded with an HttpOnly cookie and an owner organization membership. A normal sandbox workspace was created through the authenticated web gateway.
- Edited demo records and normal account/workspace records survived container recreation and stop/restart. Repeated matching healthy startup used the reuse path. Registry and workspace fingerprints were compared before/after.
- Mode switching exposed two lifecycle defects during development: PostgreSQL service aliases were lost when Compose replaced the network, and recently closed ports could be mistaken for occupied ports. Owned container recreation with retained volumes and reuse-aware socket probes corrected these cases; the restart smoke passed afterward.
- WSL keeper identity compares PID, process name, checkout, project and UTC start ticks, including PowerShell's parsed JSON date behavior. Repeated startup reused the keeper. Stop retained it while unrelated containers were running. It did not shut down WSL or Docker.
- Both acceptance stacks were stopped at the end; their volumes and private files were retained. The original application and unrelated services remained running. Original account/registry/workspace fingerprints and private-file hashes matched the baseline, and Calendar remained disabled.

## Executed checks

- Full Python unittest discovery against a separate migrated PostgreSQL test database: **191 tests passed** in 107.282 seconds. This included the existing contract, authentication, seed/fixture, isolation, domain and lifecycle regressions plus the then-current onboarding tests.
- After adding stage-failure coverage and final port handling, the focused onboarding suite: **11 tests passed**, including grouped prerequisite and failure-stage cases.
- OpenAPI validation: **146 operations, 14 request examples and 10 response examples** passed.
- Bash syntax, PowerShell AST parsing, working-tree/staged whitespace checks and strict OpenSpec validation passed.

No API contract, database migration, dependency version, demo fixture or live provider workflow changed. The normal bootstrap now adds terminal/mode/duplicate checks around the existing account policy; optional integration consent remains separate.

## Evidence boundaries

Windows/WSL and direct Linux-shell execution were observed on this machine. A native Windows Docker daemon was unavailable: its adapter received syntax and controlled preflight checks, not a full Docker Desktop startup acceptance. No separate physical Linux machine or macOS machine was tested. Local onboarding success does not claim new live-provider or Google Calendar acceptance.

## Verification warning W1 follow-up

The Windows failure-path permission warning is fixed. The WSL adapter now invokes the shared preflight/preparation phase separately, applies Windows ACLs before build/service startup, and protects partially created files in `finally`. The native Docker adapter also protects files created during a partial preparation failure. Existing operator files, permissions and credential values are preserved.

- `pwsh -NoProfile -File tests/test_developer_onboarding_windows.ps1`: **7 launcher cases passed**, covering WSL build failure/retry, partial preparation/retry, existing-file/ACL preservation, native partial preparation and native build failure. Assertions check current-user-only ACLs before build, retained exit statuses, unchanged password values and no password output.
- The current **11 Python onboarding tests passed**, now also exercising the internal preparation-only boundary without builds or a ready announcement.
- A fresh isolated checkout using the actual WSL Docker backend deliberately failed its build after preparation. Both new files already had protected Windows ACLs. A subsequent attempt retained their values and ACLs, but encountered the previously observed WSL service connection timeout; no successful application restart is claimed for that attempt.
- PowerShell parsing, Bash syntax, strict OpenSpec validation and whitespace checks passed. Original environment and credential hashes still matched the baseline. No production schema or application behavior changed in this follow-up.

## Final Windows/WSL repair acceptance

The host session failure was investigated and repaired separately from the application launchers; see [the diagnosis and applied host configuration](wsl-recovery.md). After the final configuration, the fresh Windows launch, real two-attempt build-failure/retry, demo and normal-data stop/restart checks all passed. The full Python suite passed **192 tests in 100.308 seconds**, the Windows adapter suite passed **7 launcher cases**, and OpenAPI validation passed **146 operations / 14 request examples / 10 response examples**.

**120/120 new WSL sessions passed**, including a round under a bounded 512 MiB test allocation and a round after a clean WSL reboot. No allocation-failure or vsock-accept timeout messages appeared in the final repaired boot during these checks. The earlier WSL timeout during the real retry is superseded by two successful executions of that expected-failure test.

The actual checkout then passed `dev.ps1 up -Mode normal` at 3000/8000 with its managed lifetime helper. The original record fingerprints and credential hashes matched the baseline, Calendar stayed disabled, and the unrelated PostgreSQL service was restored and healthy. Fresh acceptance services were stopped with volumes retained. No separate native Windows Docker daemon or other physical platform acceptance is claimed.
