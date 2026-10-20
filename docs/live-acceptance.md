# Live acceptance setup

**Current local result (18 October 2026):** tasks 11.5 and 12.3 passed for the declared test goods and routes. See [retained results and scope limits](live-acceptance-results.md). Brave, FX and Gemini pass. The test event and OAuth grant were removed, and normal Calendar writes remain disabled.

Connectivity checks are separate from coverage acceptance. Run `.venv/bin/python scripts/probe_live_providers.py` to retain sanitized results in `.local/live-provider-probes.json`. A partial result exits 2; it does not enable Calendar or complete OpenSpec tasks 11.5/12.3.

## OpenSpec skills

All 12 OpenSpec 1.14.3 workflows are installed under `.agents/skills/`, including `openspec-verify-change`, onboarding and bulk archive. Codex uses skills rather than generated `/ospx:*` slash commands; invoke `$openspec-verify-change` to request verification. The current environment also exposes the `openspec` CLI on PATH.

To reinstall all workflows with an installed OpenSpec CLI:

```sh
openspec config set workflows '["propose","explore","new","continue","apply","update","ff","sync","archive","bulk-archive","verify","onboard"]'
openspec config set profile custom
openspec update --force
```

The profile setting is global to the current user's OpenSpec configuration; `update` installs it into this checkout. Reinstall the CLI separately when moving to another machine.

## Model account

Configure a model key from an eligible project for the selected provider. For Gemini, use the documented compatibility base URL (`https://generativelanguage.googleapis.com/v1beta/openai/`) and a model available to that project. Save credentials only in the protected local `.env` and restart services after changing them.

Use [AI Studio API Keys](https://aistudio.google.com/api-keys) to manage Gemini keys and review the project's eligible tier. Billing and quota behavior depend on the provider account; see [Google's billing documentation](https://ai.google.dev/gemini-api/docs/billing). Acceptance documentation does not retain an operator's account or billing history.

The app reads these settings:

- `ALLEXPORT_MODEL_BASE_URL`: API base, excluding `/chat/completions`.
- `ALLEXPORT_MODEL_ID`: a model available to the account.
- `ALLEXPORT_MODEL_API_KEY`: credential binding for that endpoint's domain.

Do not paste keys into chat or commit them. Restart services after changing environment settings. A successful bounded-model response is still only connectivity evidence; task 12.3 also requires real source applicability, attribution and coverage evidence.

## Google consent and test calendar

The account owner must perform the Google consent step. An email address and client configuration alone cannot grant Calendar access.

1. In the Google Cloud project for the configured OAuth client, enable **Google Calendar API**. Use an OAuth **Web application** client. While the consent app is in Testing, add the intended Google account as a test user.
2. Register exactly `http://127.0.0.1:3000/oauth/calendar/callback` as an authorized redirect URI and configure the same `GOOGLE_REDIRECT_URI`. The browser must reach that local app origin; forward cloud port 3000 to local port 3000 if needed. A different origin requires updating both the registered URI and runtime setting.
3. In that Google account, create a dedicated empty acceptance calendar. Copy its Calendar ID from **Settings → Integrate calendar**. Provide the calendar ID, not an access token. Keep the main calendar out of acceptance testing.
4. Use the normal app in an isolated acceptance tenant/instance. The offline demo cannot perform real consent or event delivery. Provision its local app login with `scripts/bootstrap_account.py`; its password prompt is hidden. This local login is separate from the Google account. Create a test Deal with generic milestones, then use its optional Calendar panel to connect Google and complete consent in your browser. Tokens remain encrypted server-side.
5. Select the dedicated Calendar ID. Connection and selection create no events. Keep `ALLEXPORT_CALENDAR_LIVE_ENABLED` unset during this preparation.

Once consent and the dedicated calendar are available, the acceptance run can be prepared with a test-run reference, exact projection preview and current scoped approval. In the isolated test instance, exercise owned-event insert, update, delete, ambiguous retry deduplication, external-edit/ETag conflict and revocation, retaining provider receipts. Enablement for this test instance is not release acceptance. Leave task 11.5 unchecked until the complete lifecycle evidence exists, and keep general live delivery disabled until then.

## Public-source coverage

Brave and reference FX now pass through their application adapters. Public retrieval retains public-IP validation and pinning, original-host TLS verification, inherited HTTP(S) proxy routing, redirect revalidation and bounded decoded size/time. The proxy transport is covered by direct, HTTP CONNECT and HTTPS-proxy handshake tests; invalid certificates remain errors.

To close task 12.3, agree on the product and origin/destination scope, then retain real official-rule, finance, market/logistics, FX and model receipts with applicability, freshness and comparison evidence. Successful search/FX probes alone do not accept every seeded lane or unsupported country/product combination.
