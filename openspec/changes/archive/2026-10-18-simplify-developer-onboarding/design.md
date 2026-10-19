# Design

## Context

See `proposal.md` for motivation and the two delta specs for required behavior. Read-only inspection found these existing pieces:

- `compose.yaml` already declares pinned application images, migration ordering, worker-aware API health, persistent volumes and loopback ports. Its database secret file must exist before startup.
- `compose.demo.yaml` supplies synthetic mode, an internal application network, a fixed gateway and a seed service. A developer currently has to select and invoke these pieces separately.
- `scripts/local_prepare.py` generates a secret and host database settings but assumes a Unix Docker socket. `scripts/dev.py` needs host Python/Node and Linux `/proc`/process-group semantics.
- `scripts/bootstrap_account.py` already enforces the local password policy and a hidden prompt. Normal authentication and tenant membership need no replacement.
- The recent Windows run required the existing WSL Docker engine, path translation, and an owned foreground WSL session to keep that engine's services available. Those machine-specific steps exist outside the repository's standard entry path today.

This change adds a developer entry point around the existing runtime. It does not change browser onboarding or wire/database contracts.

## Goals / Non-Goals

**Goals:** A copied first-run command succeeds on Windows PowerShell with a usable native Docker CLI or default WSL Docker engine, and on a Linux Docker host; a second run is safe; missing prerequisites have short recovery instructions; local application work survives stop/restart. The first demo needs no personal credentials.

**Non-Goals:** Installing Docker/WSL, changing system-wide shell execution or network settings, changing dependency versions, enabling live providers, issuing OAuth grants, resetting databases, or introducing a registration API. Host-language hot reload and the managed-cloud wrapper remain advanced workflows.

## Decisions

### 1. Compose owns the application lifecycle

Add root `dev` and `dev.ps1` launchers with the same four operations: `up`, `stop`, `doctor`, and `account`. Default `up` selects demo; explicit normal mode uses `./dev up --mode normal` or `.\dev.ps1 up -Mode normal`. Keep platform scripts thin: argument handling, locating the checkout, choosing the Docker backend, and calling the existing Compose graph.

Use a small shared Python bootstrap helper executed in the already pinned Python container image to prepare files and perform common readiness checks. No host Python, Node, uv or globally installed project CLI is required for the default path. Bootstrap is not a privileged orchestration container: do not mount the Docker socket into it. The host launcher retains control of Docker commands.

A host-first launcher was rejected because it reproduces the toolchain and Linux process-management failures seen on this machine. A new development platform or package manager would add setup work without replacing functionality Compose already supplies.

### 2. Bootstrap is conservative and repeatable

Resolve the checkout from the launcher location; never hardcode `/workspace`, a username, a date directory or this chat's local paths. Validate the selected Compose configuration before writes. Use argument arrays and correct quoting for paths containing spaces.

After prerequisites pass, create `.local/` and its database password only when starting genuinely new storage. Copy `.env.example` only if `.env` is missing. Use cryptographic randomness, private POSIX permissions or current-user Windows ACLs, and preserve existing environment files, database credentials and installation encryption material. Never print generated values. If existing storage has lost a required secret or installation key, stop with restore instructions instead of generating a replacement over it.

New configuration keeps Calendar disabled. Existing explicit operator configuration is preserved; the launcher never adds an enablement flag or acceptance reference. Demo execution still rejects live delivery even when the developer's environment contains live settings.

### 3. Reuse the real offline demo as the first useful result

`up` performs named stages: preflight, prepare, build, migrate/start, seed, and readiness. Compose runs the existing frozen builds, migrations and domain seed. Seeding is idempotent and runs only in demo mode; startup does not invoke reset or delete volumes. A matching healthy instance can be reported and reused without rebuilding or reseeding unnecessarily.

Success requires API database/worker health, a responsive web service, and available seeded demo identities/workspaces. Check the declared loopback bindings and verify host reachability where the platform adapter supports it; the Windows/WSL acceptance run must prove the Windows browser can reach the printed origin. Print `http://127.0.0.1:3000`, the selected mode, the synthetic-data notice and short stop/diagnostic commands. Missing provider keys are optional notices, not failed demo prerequisites or live-pass claims.

Do not introduce a fixed startup-duration promise: first image downloads and OCR asset verification depend on network and caches. Use bounded readiness waits after builds complete and retain stage-specific logs on failure.

### 4. Normal mode and account provisioning are explicit

`up --mode normal` selects the existing normal stack and does not seed or enable demo identities. `account` requires normal mode and an interactive terminal, then invokes the existing bootstrap inside the API container. Account name, email and organization can be prompted or passed through existing nonsensitive options; the password must use the hidden prompt, never an argument, log, default or generated convenience file.

Reuse existing password/session/organization behavior. An existing account produces a clear conflict rather than a reset. The README explains that provider keys go in `.env` later and Calendar consent is separate. Account creation, deterministic calculations and local evidence review do not depend on Brave, Gemini or Google availability.

### 5. Runtime ownership and failure recovery are visible

Prefer the native Docker CLI when its daemon and Compose configuration work. On Windows without that backend, use the default WSL distribution only when its Docker/Compose preflight succeeds; do not install or switch distributions automatically. Translate the checkout path with the selected distribution's own path tools.

If this backend needs a foreground WSL keeper, create it hidden, record its PID plus start identity under ignored `.local/`, and reuse it. `stop` may terminate only a matching keeper it owns, after stopping this project's Compose services. It must not shut down WSL, stop Docker globally, kill unrelated port owners or prune containers/volumes. If no usable backend exists, return an actionable diagnostic and leave the machine unchanged.

Record the chosen backend/project/mode, not credentials. Respect an explicit `COMPOSE_PROJECT_NAME` for isolated developer/test instances, and verify Compose ownership labels and the canonical checkout directory before reusing or stopping existing services. A same-named stack from another checkout is a conflict, not an owned runtime.

Refuse an implicit mode change on an already-running instance; show the explicit stop/start commands. Do not overwrite a healthy user instance or silently move ports. Failure preserves data and private logs. A later `up` resumes normal preparation; `doctor` is read-only and separates tool/configuration, daemon, migration, seed, web, API and worker results.

### 6. Document one default route and retain advanced options

Start README with: prerequisite, clone/open checkout, one OS-appropriate `up` command, expected URL/demo status, and `stop`. Link normal account setup and optional live integration steps afterward. Move current host-toolchain and cloud-specific examples out of the primary quickstart while retaining their reference documentation.

An automated onboarding harness should exercise the launchers as a developer would, without host application runtimes on PATH. Use fresh isolated project volumes for acceptance, verify real HTTP/demo login and persisted state, and test invalid prerequisites with controlled command adapters. Do not run reset acceptance against a developer's existing stack. The supported Windows/WSL and Linux paths need retained smoke evidence; additional platform compatibility must be labeled according to evidence actually obtained.

## Risks / Trade-offs

- First builds need registry/package access even though demo runtime is offline → report build-stage failures separately and retain the current pinned download/asset verification.
- Small platform wrappers can drift → keep shared file/bootstrap/readiness behavior containerized and use the same command-contract tests against both wrappers.
- WSL lifecycle or path translation can leave an apparently started app unreachable → verify the actual Windows loopback origin and keeper ownership in the Windows smoke run.
- Lost local secrets can strand existing data → detect storage/configuration inconsistency and stop with recovery guidance; never regenerate over an established installation.
- A simple first launch is not a complete hot-reload environment → clearly link advanced native development and the existing test commands without making them first-run requirements.

## Migration Plan

Add the new entry points and helpers alongside existing commands. Existing checkouts keep their `.env`, private files, volumes and account data. A project already running in another mode receives an explicit conflict/recovery message. Switch README's default instructions only after fresh and repeat-run smoke checks pass. Rollback consists of reverting the launcher/documentation change and using the existing Compose commands; no schema rollback, secret replacement or data deletion is needed.
