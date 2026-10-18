# Local implementation verification

Latest review: [18 October verification](../openspec/changes/archive/2026-10-18-implement-export-workspace-with-seeded-demo/verification.md) and [live acceptance results](live-acceptance-results.md) record 74/74 tasks complete, passing real Calendar lifecycle and all declared search/source/FX/model checks. General Calendar writes remain disabled. The evidence below is the historical 16 October implementation record; its missing-credential observations are superseded by the latest review.

Recorded 16 October 2026 for `implement-export-workspace-with-seeded-demo`. The local application and isolated offline demo are implemented. Live-provider coverage and real Google Calendar acceptance remain blocked and are not counted as passed. No hosted deployment or production readiness is claimed.

## Executed checks

| Check | Result |
| --- | --- |
| Frozen Python and Node installs | Passed: `uv sync --frozen`, `npm ci`; committed dependency locks used |
| Canonical contract | 146 operations; 14 request examples and 10 response examples validated |
| Generated client | TypeScript types match a fresh OpenAPI generation |
| Unit, PostgreSQL, adapter and HTTP checks | 167 tests and 909 subtests passed |
| Canonical operation matrix | Successful HTTP responses for all 146 operations: 86 reads, 58 POSTs and 2 PATCHes; role, malformed-input, missing-resource and tenant checks included |
| Browser acceptance | 10 journeys passed against actual PostgreSQL/API/worker services, with no intercepted browser API replies |
| Web and container builds | Next.js standalone build and API/web image builds passed |
| Database migrations | PostgreSQL migration `0006` is at head; empty-storage upgrade and forward persistence checked |
| Restart | All 1,698 immutable snapshots and seven original-document hashes matched before/after a complete Compose restart |
| Reseeding | Two consecutive Compose seed runs preserved the same snapshot digest and originals |
| Namespace reset | Actual calculator-policy regeneration completed after private recovery dumps; separate normal workspace/history/original-file control remained unchanged; mixed ownership and live Calendar dependencies block reset |
| OpenSpec | Strict validation passed for the active change and both existing specs |

The Python suite emits one Starlette/httpx deprecation warning. This does not skip checks. GitHub CI is configured for the deterministic checks; a remote workflow execution is not claimed. Live probes are a separately gated job and cannot inherit an offline pass.

Private execution logs and metadata are under ignored `.local/`, including `unit-tests.log`, `browser-tests.log`, `operation-coverage.json`, `contract-checks.log`, restart/reseed fingerprints and the provider probe report. They contain no provider secret values. Recovery dumps and installation credentials remain private and are not release artifacts.

## Coverage by feature and source acceptance

| Product features / source cases | Implementation evidence |
| --- | --- |
| F01–F02; AT01–AT03 | Generalized producer/reseller entry, sandbox conversion and retained lineage; ID/CN and KE→DE fixtures, multiple goods/shipments, PostgreSQL persistence and browser editing |
| F03–F05/F07; AT04–AT09, AT43, AT46–AT47 | English/Indonesian/Chinese extraction and OCR fixtures, source spans/hashes, conflicting candidates, explicit review/expiry, query privacy, publisher deduplication and outward-China planning; provider-shaped failures and synthetic/cache labels |
| F06/F08; AT10–AT20 | Decimal economics, W/M minimum USD350, all-in coverage, unknown tax/expense separation, producer cash versus overhead, invoice reimbursement, FX direction/shocks, conservative sub-cent cash rounding and dated cash goldens |
| F09–F12; AT21–AT30 | Buyer stress, immutable joint terms, owner constraints, stage/entity/instrument/currency/tenor/security/document/recourse screening, net draws, assigned collections/reserve release, preparation packs and bound localized drafts |
| F13–F14; AT31–AT35, AT38–AT41, AT48 | Separate review/agreement/funds states, measured goods, evidenced external shipment exceptions, fixed/relative dates and business calendars, receipt verification/reversal, actual charges, immutable baselines and real HTTP closure |
| AT36–AT37 | Offline Calendar preview/hash approval/outbox delivery, stable event identity, provider-shaped ETags, visible synthetic external-edit conflict and revocation; internal timeline remains independent |
| AT42/AT44 | Atomic idempotency, live membership changes, every protected operation's role matrix, tenant reads/references/files/jobs/artifacts, concurrent organizational cash reservation and stale-job handling |
| AT45 | Live acceptance remains blocked; unit mocks and synthetic receipts do not satisfy this gate |
| Generalized product/country cases | Nonhistorical KE→DE inputs, CN→AE multi-shipment case, explicit unknown authority coverage and unsupported instrument/source limitations |
| Browser continuity and monetization | Actual worker progress, financial comparison, draft download, goods correction/role denial, pending/verified/reversed receipts, successful and blocked closure, research usage preview, editable opening cash, keyboard navigation and 390 px layout; entitlement expiry preserves permitted manual work |

The relevant tests are in `tests/test_operation_matrix.py`, `tests/operation_actions.py`, the domain/adapter/PostgreSQL suites, and `tests/browser/`. Expected fixture values are defined independently of the calculator in the golden tests and `fixtures/demo/`.

Representative synthetic values:

| Scenario | Contribution | Minimum cash | Final cash |
| --- | ---: | ---: | ---: |
| IDR baseline | 26,000,000 | -52,000,000 | 76,000,000 |
| Timely IDR60m loan, IDR1m withheld and IDR1.2m interest | 23,800,000 | 7,000,000 | 73,800,000 |
| Same loan drawn late | 23,800,000 | -46,000,000 | 73,800,000 |
| CNY producer | 17,000 | -16,000 | 40,000 |

Receipt corrections do not enlarge agreed losses: after an IDR10m partial payment and an approved IDR22m write-off against a nominal IDR32m obligation, reversing the payment reopens IDR10m and preserves the approved IDR22m loss. A historical write-off without an explicit amount needs review. Current closure checks the actual remaining balance as well as status.

Foreign actuals require their reviewed executed conversion; later reference rates cannot rewrite them or create native-currency funds. Allocated/multiple invoices without an independently established unit price remain unknown in the corresponding variance dimension. Application preparation cannot become ready while recourse is unknown.

## Offline isolation and limitations

`compose.demo.yaml` places API, worker, database and web on an internal Docker network without an Internet route. A fixed-destination gateway publishes only loopback ports 3000/8000. Offline search, FX, model and Calendar use explicitly synthetic fixtures. Synthetic sources cannot authorize a real-scope deal.

Supported original uploads are UTF-8 text, PDF, PNG and JPEG within the documented limits. Public PDF retrieval records a partial source requiring bounded document ingestion; it does not turn PDF bytes into a verified rule. Template drafts support Indonesian and English. Reference FX is valuation, not bank conversion or available foreign currency. Source registry entries are candidate authorities, not approved country-rule packs. Coverage and unknowns remain visible.

The app prepares documents and records externally performed trade actions. It does not send trade messages, execute payments, book transport, submit lending applications or file customs declarations. Optional Calendar is a separately approved projection containing generic titles/dates and no attendees by default.

## Live blockers

| Dependency | Observed status and required next evidence |
| --- | --- |
| Brave | `BRAVE_SEARCH_API_KEY` is absent. Actual licensed search and attributed source retrieval remain unexecuted. |
| Frankfurter v2 | Live probe failed with `SOURCE_DNS_UNAVAILABLE`. Resolve the environment's DNS/network allowance and retain a real attributed FX receipt. |
| Configured model | `FINCATHON_MODEL_BASE_URL`, `FINCATHON_MODEL_ID` and `FINCATHON_MODEL_API_KEY` are absent. Bounded adapter/model-task tests pass; a real provider response has not been accepted. |
| Official, market, logistics and finance coverage | Real jurisdiction/product-specific source acceptance has not run. Configure the required public destinations and retain applicability, freshness, quotation/comparability and publisher evidence. A connectivity probe alone is insufficient. |
| Google Calendar | No approved test-account OAuth/event lifecycle acceptance was executed. Requires registered client/redirect configuration, consent and actual approved insert/update/delete, retry/conflict and revocation receipts. The normal browser projection remains disabled pending this acceptance. |

The cloud configuration draft is saved for review. Saving a draft does not activate its setup/start instructions, credentials or network domains; review/save/publish it in the environment configuration interface. Supply secret values through environment credential configuration, never source files or chat.

OpenSpec tasks 11.5 and 12.3 deliberately remain incomplete. Use the [runtime guide](local-runtime.md) and [demo walkthrough](demo-walkthrough.md) to reproduce the local result.
