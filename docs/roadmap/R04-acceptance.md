# R04 technical acceptance

18 October 2026. Branch `feat/R04/scanned-document-provenance`; package owner Fithra, reviewer Wisa. Numbered checks record technical verification; **In review** remains the package state until Wisa accepts the handoff. This delivery reuses the existing implementation and changes only confirmed gaps in this package.

## Evidence scope

Current `openspec/specs/` and `api/openapi.yaml` govern acceptance. Archived proposals, designs and verification reports supply historical context; an old unchecked item is not proof of missing functionality. The latest scoped live acceptance in [live results](../live-acceptance-results.md) was retained, not rerun. These changes introduce no wire contract or provider write.

The original integration head `0fe72249bd3f2ff2e6b580748fc6ae012505837d` passed **188 backend tests, 934 subtests and 18 real-service browser journeys**, contract validation (146 operations), generated-type equality and production build: [retained CI run](https://github.com/dasarpemrograman/fintechathon-2026/actions/runs/39109764877). That is integration evidence, not a claim that every test exists on this smaller branch. The package PR's checks run against its exact split head before acceptance. Backend and browser suites share a database and run sequentially.

## R04: upload, extraction and review

| ID | Acceptance evidence |
| --- | --- |
| R04.1 | `test_document_pipeline.py::test_supported_original_types_round_trip_through_authorized_http` uploads text/PDF/PNG/JPEG through real handlers, processes each and compares original download bytes and hashes. Storage tests reject oversized, malformed and path-traversal inputs; tenant matrix covers downloads. |
| R04.2 | `test_document_extraction.py`: actual English text/native PDF/image/scanned PDF, Indonesian text/OCR and Chinese text/OCR with locators, original-language spans and unreviewed candidates. Pipeline failure/retry tests preserve originals. |
| R04.3 | Conflicting quantities remain separate in `test_conflicting_candidates_and_archived_exports_preserve_originals`; Chinese currency/date ambiguity and net-30 anchor tests retain unknowns. Manual evidence stays subject to explicit authorized review. |
| R04.4 | `test_effective_dates_and_expiry_invalidate_reviews_without_editing_history` and immutable numeric-source regression; browser evidence/review controls call the API and show processing/review state. Original downloads remain unchanged. |

Confirmed fix: scanned-PDF processing discarded OCR region locators while retaining text. PDF locators now retain both the page and OCR word boxes. Parser cache identity advances to `extract-2`; a regression proves old `extract-1` results remain stored but cannot satisfy a current lookup, so prior cached output cannot hide the fix. Existing history is not rewritten. New explicitly synthetic Indonesian/Chinese image fixtures are hash-locked; existing fixture bytes and natural keys are unchanged. OCR output remains fallible review material, never commercial agreement or verified payment.

## Handoff and limitations

No missing implementation prerequisite was found for these numbered subtasks. Existing prerequisite interfaces were exercised by the retained integration tests. Wisa’s package review remains necessary before declaring the package Done.

Credentials and raw run logs remain in ignored `.local/`; committed screenshots/receipts contain synthetic data. Existing untracked user skills and configuration are excluded. This report distinguishes retained integration evidence from the current PR checks.
