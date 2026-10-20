# R19 technical acceptance

18 October 2026. Branch `feat/R19/offline-demo-journeys`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## Reproduction evidence

On the integrated head, two reseeds and a Compose stop/start preserved 1,701 immutable snapshots, 7 original hashes, 14 workspaces and 12 memberships. A disposable unrelated account, workspace and session survived unchanged and were cleaned up afterward. Runtime API egress was blocked on the internal demo network. The original fixture inventory has ten hash-locked assets; R04 independently adds two synthetic OCR assets. These fingerprints describe the retained integrated run, not newly generated IDs for this branch.

## R19: seeded demo and evaluator journeys

| ID | Acceptance evidence |
| --- | --- |
| R19.1 | Hash-locked manifest/source inventory, fixed 2026-10-16 business reference date, all four roles across three isolated organizations, ten entry workspaces plus four causal checkpoints, KE→DE and CN→AE multi-line/multi-shipment fixtures. |
| R19.2 | Seeded acceptance and actual-service browser journeys reproduce analysis, negotiation, timely/late finance, drafts, blocked/corrected goods, receipt verification/reversal, buyer-paid/internal-reconciling and successful closure. Goldens remain independently specified. |
| R19.3 | `test_seed_replay_does_not_duplicate_resources`, scoped reset tests preserving unrelated records, mixed ownership/history refusal and retained/live Calendar dependency refusal. Fresh reseed/restart fingerprints supplement these transactional regressions. |
| R19.4 | Offline evaluator journeys are exercised and the walkthrough is updated, but **final integrated acceptance remains blocked** by R07.4 and Wisa's R17.3/R17.4 recovery evidence and review. This run does not perform another owner's disaster-recovery work. |

The Compose browser helper now invokes ordinary Compose for the running services; it no longer requires the managed-cloud proxy wrapper. The demo network is internal, and a real public TCP connection attempt from the API is refused. Synthetic Calendar tests make no Google writes. No live-provider credentials are needed for these journeys.

## Handoff and limitations

**R19.4 remains blocked:** R07.4 requires Faiz/Wisa handoff review, and R17.3/R17.4 require Wisa’s isolated PostgreSQL/private-file/key recovery rehearsal and evidence. Offline evaluator checks pass; final integrated acceptance remains open. No recovery work owned by another engineer was added.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
