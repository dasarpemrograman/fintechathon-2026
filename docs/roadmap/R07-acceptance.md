# R07 technical acceptance

18 October 2026. Branch `feat/R07/immutable-numeric-lineage`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## R07: numeric lineage

| ID | Acceptance evidence |
| --- | --- |
| R07.1 | `test_numeric_output_keeps_the_original_source_revision_after_conflict`, economics/golden tests and `browser/lineage.spec.ts` trace formula, stored input revision, native cash amount, source mode/expiry/hash and original-file bytes. Structured blockers retain explicit reasons/actions rather than inferred missing facts. |
| R07.2 | The pipeline test changes a used source to conflicted, retrieves the old analysis and exact old evidence revision, proves byte-for-byte historical equality and refuses a new approval based on that stale analysis. Scenario/workspace revision reads remain tenant-authorized. |
| R07.3 | The extracted `numeric-lineage.tsx` exposes the previously count-only fixed input revisions and historical metadata, including unknowns, assumptions, conflicts, validity and synthetic/cached source modes. It labels historical review as insufficient for new action and offers authorized original downloads. The new browser journey uses keyboard controls at 390 px. |
| R07.4 | **Open handoff:** Faiz must review the calculated-input trace and Wisa the source-reference handoff. The trace and same-state screenshots are available below; no human review is claimed. |

[Before](../audits/fithra-roadmap/lineage-before.png) shows the existing closed checkpoint's formula panel with input counts. [After](../audits/fithra-roadmap/lineage-after.png) shows the same state with expandable fixed inputs; [opened input](../audits/fithra-roadmap/lineage-input.png) shows the historical inspector. The inspector always calls `GET /v2/inputs/{id}/revisions/{revision}` from the analysis reference; it does not substitute a current mutable record. The browser regression independently reads the same revision and compares the source download's SHA-256 with the displayed evidence hash.

### Stored synthetic trace for handoff

The retained [trace receipt](../audits/fithra-roadmap/trace.json) records one baseline analysis from this run: `analysis_4211fc31672e9546894067f9`, contribution **IDR 26,000,000.00** and minimum cash **-52,000,000.00**. Its contribution formula refers to Deal `deal_f3cd6fc3a46ff42f27698fe5` revision **26** and evidence `evidence_812e26fe2485211c7ddaa167` revision **1**. These exact revisions are retrievable through the authorized input-revision endpoint.

The source locator is “Fixture manifest and declared schedules,” with explicit `synthetic_demo` mode. Its original document is `document_3f6b392b6ebb8d67f82c1721`; SHA-256 is `707e5794000f5df7a318357c1e2d20d8de510855c29f3837395156fdcbcd521b`. The browser download regression independently hashes the authorized bytes. Real parsed character/region spans and changed-source history are separately exercised in `test_document_pipeline.py` and `test_document_extraction.py`. This receipt is a synthetic run example, not live evidence or a replacement for Faiz/Wisa's review.

## Handoff and limitations

**R07.4 remains blocked:** Faiz must review calculated-input lineage and Wisa must review source references. The stored trace and screenshots prepare that review; they do not constitute human acceptance. Existing R04/R05 source and R06 calculation behavior was verified in the retained integration suite.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
