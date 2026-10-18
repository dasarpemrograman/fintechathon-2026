# R16 technical acceptance

18 October 2026. Branch `feat/R16/deterministic-usage-allowances`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## R16: usage and entitlement behavior

| ID | Acceptance evidence |
| --- | --- |
| R16.1 | `test_pilot_provisioning.py` invokes the real operator CLI for Free, Deal Pass, Pro, Team and explicit institutional terms; checks catalog version, Deal Pass's 90-day expiry and unknown institutional price. Missing institutional limits/terms are rejected. Usage preview is exercised by HTTP and browser discovery checks. |
| R16.2 | `test_pending_provider_work_reserves_allowance_but_manual_matching_does_not`; duplicate/cached-document and interrupted-job tests; normal-mode manually reviewed finance matching through HTTP. Pending provider work reserves allowance, failed work releases it and successful work is metered once. |
| R16.3 | Included-before-add-on/monthly reset/expiry and active-deal limits in `test_entitlements.py`; membership allowance/server checks; expired admission preserves deterministic/manual work, existing reads and exports. Archive/closure free active slots. |
| R16.4 | CLI provisioning produces `provisionPilotEntitlement` audit records with the local operator identity. Browser settings/preview and structured admission errors explain restrictions. No checkout, automatic overage or changes to trade economics were introduced. |

Confirmed fix: pending deterministic matching of manually reviewed finance products incorrectly reserved an enriched run. Pending accounting now follows the existing server-set deterministic flag, matching admission and metering behavior.

## Handoff and limitations

No missing implementation prerequisite was found for these numbered subtasks. Existing prerequisite interfaces were exercised by the retained integration tests. Wisa’s package review remains necessary before declaring the package Done.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
