# Developer onboarding

Start from a checkout with a working Docker daemon and compatible Docker Compose plugin. The first build downloads the pinned images, packages and verified OCR assets. Host Python, Node and uv are unnecessary for this route.

## Start the offline demo

Windows PowerShell:

```powershell
.\dev.ps1 up
```

Linux shell:

```sh
./dev up
```

Open **http://127.0.0.1:3000/** and choose **Enter demo**. English is the default interface language. This is synthetic offline data, not live trade evidence. Startup prepares missing local files, builds, migrates, starts the API/worker/web and seeds the existing demo. It announces readiness only after the worker-aware API, web and seeded identities respond. Existing credentials and data are preserved.

On Windows, a usable native Docker CLI is preferred. Otherwise the launcher uses Docker in the default WSL distribution. It does not install or switch distributions, change global WSL settings, or install Docker. An owned hidden WSL helper keeps the app available after the command returns. The Windows loopback URL is checked before success.

New Windows configuration files are restricted to the current user before builds or services start. Partial preparation failures also restrict any files just created; retries preserve their values. Existing operator files and permissions remain unchanged.

## Stop and diagnose

Use `.\dev.ps1 stop` / `./dev stop` to stop only this checkout's selected Compose project. Volumes and credentials remain. Use `.\dev.ps1 doctor` / `./dev doctor` for read-only prerequisite, ownership, mode, API/worker and web diagnostics.

- Missing Docker/daemon: start Docker Desktop, or configure/start Docker with Compose in default WSL, then rerun `doctor`.
- Incompatible Compose: update the Compose plugin to support the checked project configuration. The launcher never installs software automatically.
- Occupied port: explicitly stop its owner or choose documented explicit ports below. The launcher does not kill a port owner or silently change the origin.
- Another checkout owns the same project name: choose a distinct `COMPOSE_PROJECT_NAME`; never stop it through the wrong checkout.
- A different mode is already running: stop it explicitly before starting the requested mode.
- Missing secret with existing data: restore the original `.local/db-password` and matching runtime/encryption key from your backup. Do not delete volumes or generate replacement credentials.
- Failed build, migration, seed or readiness: inspect the named private log in `.local/dev/<project>/`, run `doctor`, then retry. Startup does not reset data.
- WSL session timeouts with `vmbus_alloc_ring` allocation failures in the kernel log: see the [observed host diagnosis and recovery](wsl-recovery.md). Global WSL repair is separate from application startup.

## Normal local account

Windows:

```powershell
.\dev.ps1 stop
.\dev.ps1 up -Mode normal
.\dev.ps1 account
```

Linux:

```sh
./dev stop
./dev up --mode normal
./dev account
```

Enter your email, display name and organization, then a password of at least twelve characters at the hidden prompt. Use an interactive terminal. Password arguments, redirected password input and shared defaults are unsupported. Existing accounts are not reset. Sign into the ordinary app afterward; demo shortcuts are disabled in normal mode.

## Explicit isolated projects and ports

The default Compose project is `allexport`. For another checkout or acceptance run, set a distinct `COMPOSE_PROJECT_NAME` and free explicit loopback ports before invoking the launcher:

```powershell
$env:COMPOSE_PROJECT_NAME='allexport-example'
$env:ALLEXPORT_WEB_PORT='3002'
$env:ALLEXPORT_API_PORT='8002'
.\dev.ps1 up
```

```sh
COMPOSE_PROJECT_NAME=allexport-example ALLEXPORT_WEB_PORT=3002 ALLEXPORT_API_PORT=8002 ./dev up
```

Keep the same project/port environment for later commands. Changing an existing installation's database password file or volume identity is not a port-switch operation. A deliberately different web origin needs matching Google redirect registration before future OAuth; Calendar remains optional and disabled by default.

## Later development and integrations

The launchers build the existing pinned images. Repeating `up` reuses a matching healthy instance when source/configuration has not changed, and rebuilds/rechecks after changes. This is a first-run path, not a new hot-reload server.

Keep provider keys in the ignored `.env` only when you need live features. Initial demo startup needs none, and successful local startup does not claim provider acceptance. See [native runtime, tests and lifecycle](local-runtime.md), [demo walkthrough](demo-walkthrough.md), and [optional live setup](live-acceptance.md). Existing native-toolchain and managed-cloud commands remain available in those references.
