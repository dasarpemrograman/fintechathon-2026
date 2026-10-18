# Fincathon

A local export workspace for producer and reseller exporters: evidence, deterministic economics, financing scenarios, draft preparation, execution records and reconciliation.

The application uses Next.js, a Python API and worker, PostgreSQL and private content-addressed document storage. [api/openapi.yaml](api/openapi.yaml) is the single source of truth for the wire contract; runtime validators and generated TypeScript types derive from it.

Start with [local setup and lifecycle commands](docs/local-runtime.md), then follow the [synthetic demo walkthrough](docs/demo-walkthrough.md). The demo uses explicit demo mode, isolated tenants and fixed synthetic fixtures. Its internal services run on a Docker network with outbound access disabled.

For optional live-provider configuration, copy [.env.example](.env.example) to `.env` and fill in your credentials locally. The API, worker and provider probes load it; Compose passes it to backend services. The offline demo needs no provider keys. See [environment configuration](docs/local-runtime.md#environment-configuration) for precedence and restart behavior.

```sh
UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen
npm --cache /workspace/.cache/npm ci
.venv/bin/python scripts/local_prepare.py
python scripts/compose_cloud.py --demo build
python scripts/compose_cloud.py --demo up -d
python scripts/compose_cloud.py --demo run --rm seed
```

The managed-cloud wrapper preserves the environment's proxy and CA. On a regular Docker host use `docker compose -f compose.yaml -f compose.demo.yaml` instead. Open http://127.0.0.1:3000. Stop with the same Compose invocation followed by `stop`; retain volumes when removing containers. Never use volume deletion to reset demo data.

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
