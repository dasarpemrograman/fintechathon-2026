# R17 history and archival implementation

Implemented and checked on 19 October 2026 against the local Compose demo. This increment addresses established browser/history gaps in the workspace-access, workspace-ui and durable-operations specifications. The broader R17 recovery acceptance remains open.

## Changes

Exploration and Deal history now offer separate immutable revision selectors, side-by-side changed sections and expandable exact snapshots. Converted explorations retain their source revision reference. Viewing or comparing a revision does not change current facts, evidence reviews or approvals.

Audit reads accept the canonical optional `workspace_id` filter. The server authorizes that workspace before returning its own and its linked Deal's audit records. The browser no longer presents the organization's unrelated audit records as the current transaction's history. Entries expose actor, purpose, time, revision, data mode, before/after hashes and request/job correlation. New workspace creation audits retain their parent and created revision; historical records lacking parent metadata remain in the organization-wide audit collection.

Revision collections now enforce their declared page sizes and use numeric revision cursors. Historical reads remain available after corrections and archival. The browser loads revision and audit pages on demand and displays loading, empty and error states.

Owner/export-admin controls provide deliberate archival and reactivation through the existing API, with current revision checks. Archived cards stay discoverable. Their evidence/history/export reads remain available; mutations are rejected, and reactivation follows the existing entitlement policy. The walkthrough distinguishes a JSON export from a full database/file/key backup.

## Executed verification

- HTTP foundation, workflow, storage access and historical-schema suites: **36 tests and 5 subtests passed**, including 13 numerically paginated workspace revisions, exact original snapshot preservation, workspace/Deal audit inclusion, exclusion of unrelated workspace records and foreign-tenant history/audit refusal.
- Contract, examples, response semantics and runtime validation suites: **42 tests and 232 subtests passed**.
- Browser history journeys against actual web/API/PostgreSQL services: **2 passed**. Coverage includes immutable exploration comparison, separate Deal/workspace history, scoped audit, archive/reactivate, mutation refusal while archived and retained export/revision reads.
- Production Next.js build and TypeScript checks passed. Canonical OpenAPI validates all **146 operations**, 14 request examples and 10 response examples. Regenerated TypeScript definitions match a fresh generation.
- `dev.ps1 doctor` confirms web/API/database/matching worker and seeded identities ready after service recreation.

The backend integration suites run with `APP_MODE=normal` in a one-off container so their normal-workspace fixtures match the process mode. The running browser stack retains explicit demo mode. One existing Starlette/httpx deprecation warning remains.

## Remaining R17 acceptance

This increment does not close the numbered R17 package checks. R17.3 and R17.4 still require the specified isolated database/private-file/encryption-key backup-and-restore rehearsal and recorded recovery limits. No fresh disaster-recovery restore or package reviewer sign-off is claimed. Existing retained originals and historical audit records were not rewritten to invent missing metadata.
