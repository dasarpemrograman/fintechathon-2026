# R10 technical acceptance

18 October 2026. Branch `feat/R10/immutable-scenario-comparison`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## Merge dependency

This PR targets `feat/R07/immutable-numeric-lineage`: its immutable value renderer is introduced by R07. Merge R07 first, then retarget/replay this package onto `work`. The existing R06/R08/R09 calculation and stress behavior is exercised by regression tests; no unfinished owner work is implemented here.

## R10: negotiation and scenarios

| ID | Acceptance evidence |
| --- | --- |
| R10.1 | `test_scenario_comparison.py` and `test_joint_scenario_changes_reproject_terms_and_costs_without_writes` exercise immutable baseline/buyer/supplier-production/joint alternatives and retain required counterparties. |
| R10.2 | Joint payment/procurement regression verifies changed buyer deposit and supplier unit costs are reprojected into obligations/costs without mutating baseline resources; dated economics/golden tests cover full deposit/balance schedules and producer inputs. |
| R10.3 | Constraint checks/ranking cover margin, cash buffer, allowed changes, delivery dates/timezones, credit tenor, missing anchors and stale results. Ranking uses disclosed deterministic metrics and never implies agreement. |
| R10.4 | `browser/scenarios.spec.ts` creates a joint buyer deposit/balance and supplier-date alternative through the actual editor/worker, inspects its exact stored base and before/after values, cash horizon/schedule and remaining exposure, and verifies unchanged live payment/procurement terms. The funding/draft journey remains covered. |

Existing working calculation and scenario behavior was reused. Decimal arithmetic, verified receipt history and immutable source revisions were preserved. The comparison summary needed a confirmed UI fix: `scenario-details.tsx` now retrieves the immutable scenario and its declared base revision, exposes changed values side by side, and displays the existing server-derived timing, unknowns and residual risk. [Original comparison](../audits/fithra-roadmap/scenario-before.png) and [expanded comparison](../audits/fithra-roadmap/scenario-after.png) show the same stored synthetic proposal; the original frontend was built from `6a67924`. Opening the details sends only authorized reads.

## Handoff and limitations

No missing implementation prerequisite was found for these numbered subtasks. Existing prerequisite interfaces were exercised by the retained integration tests. Wisa’s package review remains necessary before declaring the package Done.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
