# Local runtime foundation

Run from the existing repository checkout. Toolchain pins are in `.python-version` and `.node-version`; runtime dependencies use `uv.lock` and `package-lock.json`. Do not create a worktree for setup.

```sh
UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen
npm --cache /workspace/.cache/npm ci
.venv/bin/python scripts/local_prepare.py
.venv/bin/python -m alembic upgrade head
npm run types
.venv/bin/python scripts/check_generated.py
```

`local_prepare.py` starts the project PostgreSQL container on loopback port 15432 and waits for readiness. It generates private database settings under ignored `.local/`; no database password is committed or printed. The container volume persists across restart. Do not delete that volume to reset demonstration data.

The API foundation can run with `.venv/bin/python -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000`. The separate worker entry point is `.venv/bin/python -m services.worker`. Application and demo acceptance are tracked separately in the active OpenSpec tasks; starting these processes alone does not establish that all workflows work.

Bootstrap a normal local account with `.venv/bin/python scripts/bootstrap_account.py --email owner@example.test --name Owner --organization Exporter`; enter the password at its hidden prompt. There is no committed default account password. Demo identity entry requires explicit `APP_MODE=demo` and allowlisted seeded users; an old demo session is invalid in normal mode.

The database has dedicated resource tables by kind, tenant-scoped registry/reference foreign keys, immutable resource snapshots, password/session tables and transactional command/job/outbox/usage state. Native monetary values use unscaled PostgreSQL NUMERIC plus original wire strings. History-bearing down migrations deliberately refuse destructive deletion; use a verified backup or a forward migration.

Uploaded originals are limited to 10 MiB each, with a 16 MiB request ceiling, supported UTF-8/PDF/PNG/JPEG signatures and bounded processing. Original bytes are content-addressed, private and verified again on download. Filenames never select storage paths. API downloads require record ownership; a hash grants no access. Text/PDF/image processors have resource/time limits; OCR uses pinned Git-verified language assets and preserves original-language text/locators. PDFs are limited to 100 pages and extracted pages to 200000 characters. These are configured workload limits, not permanent product coverage claims.

`.local/encryption-key` encrypts authentication replay receipts and connector secrets. Keep it with a protected backup if those records must survive migration; it is never an API response. Password-bearing request hashes are keyed so they do not create a fast offline password oracle. Login tokens remain opaque and revocable.

## Browser and process lifecycle

```sh
npm run build
.venv/bin/python scripts/dev.py start --demo
.venv/bin/python scripts/dev.py status
.venv/bin/python scripts/dev.py stop
```

The launcher binds API 8000 and web 3000 to 127.0.0.1, waits for HTTP readiness and records owned process IDs and process start identities under `.local/`. Logs also stay there. Stop retains PostgreSQL and original files; restart reuses them. Omit `--demo` for normal authentication mode. The standalone Next.js build includes static assets. Browser bearer tokens are stored only in an HttpOnly, same-site cookie; the server proxy adds Authorization and checks exact mutation origins. Use the documented 127.0.0.1 origin, or configure `WEB_ORIGIN` for a deliberate alternative.

`docker compose up --build -d` declares the normal PostgreSQL/migration/API/worker/web stack with persistent volumes and loopback published ports. `docker compose -f compose.yaml -f compose.demo.yaml up --build -d` enables demo entry explicitly. Use the same files with `run --rm seed` to seed, `stop`/`start` for restart and `down` to remove containers while retaining named volumes. Do not use `down -v` as a demo reset. The cloud-specific `compose.cloud.yaml` preserves host proxy build arguments and uses host networking during builds; it does not disable TLS validation. The managed-cloud wrapper `python scripts/compose_cloud.py --demo build` resolves the managed proxy for build networking and installs the inherited public CA; TLS verification stays enabled. Use `python scripts/compose_cloud.py --demo up -d`, then `python scripts/compose_cloud.py --demo run --rm seed`. Fresh database migration, seed, API, worker and web startup have been exercised with this stack. The demo override places application services on an internal network with no outbound route. A fixed-destination gateway alone publishes loopback ports 3000/8000; it cannot select arbitrary proxy destinations. Normal mode uses the base stack and requires local account provisioning. Do not run host and Compose application servers on the same ports.

For OCR, `scripts/install_ocr.py` fetches the pinned tessdata Git commit and verifies each Git blob before installing language assets. `tesseract` and `pdftoppm` must be installed on the host. Container images declare those packages. Supported languages are English, Indonesian and simplified Chinese; extraction yields unreviewed candidates, not verified trade facts.

Public-source retrieval accepts HTTPS only, pins validated public IPs while preserving original Host/TLS SNI, rechecks redirects, bounds size/time and retains the inherited proxy/CA configuration. Private/link-local addresses, authentication walls and rate limits produce explicit failures. Declared caps are 12 queries, 20 pages, 40 actions and 2 provider retries; provider execution and source coverage remain separately tracked. Live search requires `BRAVE_SEARCH_API_KEY`. A configurable model requires `FINCATHON_MODEL_BASE_URL`, `FINCATHON_MODEL_ID` and `FINCATHON_MODEL_API_KEY`; no model output is allowed to approve, settle, book or submit anything. Google Calendar additionally requires registered `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`. Do not put secret values in commands, source, fixtures or reports.

## Model privacy and bounded outputs

The configured model adapter receives only completeness, blocker codes, opaque allowed evidence IDs and allowlisted section/metric names for explanation selection. It receives no party identities, bank details, document bodies or monetary inputs in this task. It has no mutation or trade tools. Task-specific JSON validation rejects extra fields, invented references and injected instructions; one repair attempt is allowed. Offline explanations select deterministic sections without a provider call. Documents produce unreviewed deterministic candidates and require human source review. `execution=enrich` is an explicit provider request, never an alias for a live-validated result. Template drafts support `id` and `en`; unsupported languages return an explicit limitation rather than mislabeled English output.

Cash reservation commands lock the organization/currency ledger in the same transaction as reservation creation or release. They require the current reviewed snapshot hash and subtract commitments plus active reservations before admitting new reservations. Execution gates subtract reservations belonging to other Deals from available own funds in the same native currency; the analytical forecast remains bound to its declared cash snapshot. Releasing a reservation does not record a payment or change historical cash snapshots.

Calendar writes use a transactional outbox with at-least-once attempts. A stable provider event identity and owned-event receipt make a retry after an insert deduplicate. Existing external edits cause an ETag conflict; another review is required. Unowned events cannot be changed or deleted. Provider exceptions are bounded and never change the internal milestone timeline. This behavior is tested with provider-shaped responses; real OAuth and event lifecycle validation remain unexecuted.

## Readiness and diagnostics

`GET /health` checks PostgreSQL and the matching-mode worker's recent heartbeat in the private shared runtime volume. It returns 503 when the worker heartbeat is absent or stale; process startup alone is insufficient. Start API and worker together. Job leases/heartbeats remain database-backed and independent of this process-liveness signal.

Owners and export admins can read `GET /v2/diagnostics` for their organization's queue states, expired leases, run blocker/warning code counts and stale analysis count. Inspect a failed run by its recorded run ID, then search the private worker log for `job_failure job=<id>`; diagnostics include the originating request ID, exception class and function/line frames, without exception messages, source bodies, credentials or request payloads. Queued output retains input revision/hash references. Provider missing-configuration and outage blockers remain in run records; a successful offline run cannot change live probe evidence. Review old artifacts against their stored analysis/evidence hashes before using them.

Interrupted jobs recover through 90-second database leases with a heartbeat during processing. Three claimed attempts exhaust the retry budget, including interrupted attempts. Exhausted jobs retain a failed run and require an explicit new request; they do not silently loop forever or consume an enriched-run allowance. Queued cancellation prevents claim; cancellation after commit preserves completed outputs. A result computed from an older revision remains accessible with `STALE_INPUT` and cannot replace the current analysis state.

Externally performed booking/shipment events are records, not commands sent to a carrier. If a stage is blocked, recording an actual event requires an exception reason and retains the unmet conditions at that time. Recording it does not clear requirement, funding or goods blockers. Goods marked ready require measured quantity and declared specifications supported by reviewed evidence; photographs alone cannot establish conformity.

## Pilot allowances

`config/plans-v1.json` preserves the versioned business pilot limits and unvalidated price baselines. It does not activate checkout. A local operator can run `.venv/bin/python scripts/set_plan.py --organization <id> --plan pro`; the command records an audit event without payment. Deal Pass defaults to its declared 90-day window. Monthly included pools reset independently from expiring add-ons, included units are consumed first, and there is no automatic overage. Add-ons require an expiry with an explicit offset. Institutional provisioning requires `--runs`, `--pages`, `--users`, `--active-deals` and a reviewed `--terms-reference`; it never invents a quoted price.

Admission reserves pending workload against the organization allowance. Successful provider work and newly extracted pages are charged once by run identity; cached duplicate documents, deterministic arithmetic, failed/retried work and manual receipts do not add enriched-run charges. Expiry stops new gated provider/artifact work while preserving historical reads and permitted manual obligations/receipt updates. Archive or closure frees an active Deal slot without deleting its history.

## Export, archival and recovery

Authenticated workspace/Deal exports contain the current snapshot, evidence metadata and immutable resource history. Original uploaded bytes remain separate authorized downloads; the JSON export alone is not a complete database/file backup. Archive retains all history and originals. Namespace reset performs dependency preflight and refuses mixed ownership; it does not delete real workspaces or global files.

For local disaster recovery, stop application writers and back up PostgreSQL, the entire private runtime volume (including originals and the encryption key), and the exact application/migration version together. Use a private directory with `umask 077`. `docker compose exec -T postgres pg_dump -U fincathon -d fincathon` can write a logical dump directly to a protected local file; never print it into chat or commit it. Restore into a separate empty database/volume, apply forward migrations and verify original file hashes and authenticated historical reads before switching the runtime. Do not overwrite the running database as an import step. Historical schema-2.1 projections preserve their original snapshot and explicit unknowns.

Calendar OAuth requests only `calendar.events.owned`, uses actor-bound single-use ten-minute state, and encrypts access/refresh credentials under the private installation key. Expiring tokens refresh through Google's token endpoint and stay encrypted. Revocation consumes pending states, removes local access and attempts provider grant revocation; a provider outage produces `REMOTE_REVOCATION_UNCONFIRMED` while local access remains removed. Review remaining Google account grants if that warning appears. A connection with owned events cannot silently switch to another calendar; create a new connection. Real-account acceptance is still required before treating this adapter as live validated.

Controlled drafts distinguish internal recommendations/finance packs from counterparty messages, agreements, clause revisions and amendments. Counterparty templates omit internal contribution/cash metrics and unrelated supplier terms. They retain exact analysis/scenario hashes, declared prices and dates, with explicit original-agreement/clause/effective-date placeholders rather than invented legal terms. Downloads require the same organization/object authorization as their source Deal.
