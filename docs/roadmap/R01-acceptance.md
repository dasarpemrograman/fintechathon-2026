# R01 technical acceptance

18 October 2026. Branch `feat/R01/session-and-tenant-access`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## R01: accounts, organizations and roles

| ID | Acceptance evidence |
| --- | --- |
| R01.1 | `test_storage_access.py::test_real_password_session_expiry_and_membership`; HTTP logout rejects the old bearer while a second session survives; `browser/auth.spec.ts` provisions a disposable normal account, signs in, switches organizations, reloads and logs out through real services. |
| R01.2 | `test_workflow_commands.py::test_membership_updates_apply_to_existing_sessions_and_last_owner_is_retained`; all protected operations' four-role matrix in `test_operation_matrix.py`; browser production reviewer can inspect goods but cannot verify funds/receipts. Final-owner removal is rejected. |
| R01.3 | Operation matrix and storage/pipeline checks exercise tenant-scoped resources, documents, runs, artifacts, exports and foreign references; the same ID never grants another tenant access. |
| R01.4 | Normal-mode demo rejection and old-demo-session refusal in HTTP/storage tests; browser HttpOnly/Strict cookies, empty client token storage, origin denial and revoked-token checks. [Local provisioning](../local-runtime.md) retains a hidden password prompt. |

Confirmed fix: the browser logout proxy omitted the contract-required empty JSON object. It now sends the canonical request, waits for server revocation and retains a visible retry state on failure. No wire change was required. Session/organization changes clear the previous portfolio and discard late list responses; usage and membership views remount for the selected organization. The normal-account browser regression verifies a private workspace disappears and Team allowances change to Free when selecting the second organization.

## Handoff and limitations

No missing implementation prerequisite was found for these numbered subtasks. Existing prerequisite interfaces were exercised by the retained integration tests. Wisa’s package review remains necessary before declaring the package Done.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
