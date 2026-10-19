# Fincathon

A local export workspace for producer and reseller exporters: evidence, deterministic economics, financing scenarios, draft preparation, execution records and reconciliation.

The application uses Next.js, a Python API and worker, PostgreSQL and private content-addressed document storage. [api/openapi.yaml](api/openapi.yaml) is the single source of truth for the wire contract; runtime validators and generated TypeScript types derive from it.

Install Docker with a working daemon and compatible Compose plugin, then clone and open this checkout. On Windows the launcher can also use Docker in your default WSL distribution. No host Python, Node, uv, API keys or personal account is needed for the first demo.

Windows PowerShell:

```powershell
.\dev.ps1 up
```

Linux shell:

```sh
./dev up
```

Open **http://127.0.0.1:3000/** and choose **Enter demo**. The interface uses English and a minimal green design system; original evidence retains its source language. This is a seeded synthetic offline demo; its application network has no outbound access. Startup creates only missing local configuration and preserves existing data. Stop with `.\dev.ps1 stop` or `./dev stop`; diagnose with `doctor` in place of `stop`.

See [developer onboarding](docs/developer-onboarding.md) for prerequisites, recovery, explicit normal mode and hidden-password account setup. Follow the [demo walkthrough](docs/demo-walkthrough.md), or use the advanced [native toolchain and managed-cloud commands](docs/local-runtime.md). Optional live-provider credentials belong in the ignored `.env`; [environment configuration](docs/local-runtime.md#environment-configuration) explains precedence and restart behavior. Calendar writes remain disabled initially.

```sh
.venv/bin/python scripts/validate_contract.py
npm run types
.venv/bin/python scripts/check_generated.py
.venv/bin/python -m pytest -q
FINCATHON_BROWSER_COMPOSE=1 npx playwright test
```

Tests need the prepared local PostgreSQL database, installed OCR assets and, for browser journeys, the running demo stack. See the setup guide for prerequisites and normal-mode account provisioning. Calculations and independent expected values are documented in [calculation notes](docs/calculations.md).

The declared local live acceptance passed on 18 October 2026: see [exact scopes, source comparisons and Calendar cleanup](docs/live-acceptance-results.md). Calendar delivery remains disabled by default.

The local implementation and offline checks are recorded in [the verification report](docs/verification.md) and [OpenSpec checklist](openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/tasks.md). Offline test success does not establish live provider access. Live search, configured model and Calendar validation require separate configuration, credentials and recorded provider acceptance. The app prepares drafts and records externally performed trade actions; it does not send trade messages, book shipments, pay, file declarations or submit financing applications.

Change the canonical YAML before changing wire behavior, regenerate types, and run contract checks. [Contract decisions](docs/contract-decisions.md) document reference policy and compatibility rules without defining a second schema.
