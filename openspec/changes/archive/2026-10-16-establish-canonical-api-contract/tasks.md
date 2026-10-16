# Tasks

These tasks describe a future apply. The existing scaffold is baseline; no implementation task is complete merely because the planning artifacts exist.

## 1. Constrain response outcomes

- [x] 1.1 Restrict async 202 envelopes to accepted and synchronous creation/read envelopes to their documented outcomes in `api/openapi.yaml`; add tests accepting valid statuses and rejecting accepted/completed contradictions, and verify structural validation and those tests pass.
- [x] 1.2 Add readiness/closure envelope-to-gate consistency and partial-analysis status constraints; verify blocked-gate/completed-envelope and partial-analysis/complete-envelope contradictions are rejected while valid blocked and partial payloads pass.
- [x] 1.3 Update the API draft version to 2.1.1 and `docs/contract-decisions.md` with the exact status tightening and no-known-consumers migration assessment; verify snapshot schema_version stays 2.1 and all existing request regressions still pass.

## 2. Validate embedded responses

- [x] 2.1 Extend `scripts/validate_contract.py` to validate inline and locally referenced request/response media-type example(s) against inline or referenced schemas; verify tests cover valid examples, invalid nested money, unresolved references, unsupported external examples and cyclic reference diagnostics.
- [x] 2.2 Report separate request/response example counts and operation/direction/status/example diagnostics; verify an invalid response example in an in-memory document copy fails with its location and the CLI exits nonzero on validation failure.
- [x] 2.3 Update the README's validation description and run commands; verify the documented commands work with `requirements-contract.txt` and accurately describe the checked example locations without implying runtime validation.

## 3. Demonstrate representative outcomes

- [x] 3.1 Add accepted-job, partial-analysis, blocked-readiness, pending-receipt and structured-error media-type response examples to `api/openapi.yaml`; verify each family is visited by the validator and contains schema-valid evidence/status references.
- [x] 3.2 Add regressions that mutate canonical response examples to invalid nested amounts, verifier/status contradictions representable in the schema and contradictory envelopes; verify each invalid mutation fails and the original examples pass without duplicated normative fixtures.

## 4. Verify the complete contract increment

- [x] 4.1 Run `python scripts/validate_contract.py` and `python -m unittest discover -s tests -v` with the pinned environment; verify nonzero request and response example counts, all retained regressions execute and all checks pass.
- [x] 4.2 Confirm `.github/workflows/contract.yml` invokes the same validated commands, `git diff --check` is clean and the change introduces no app/server/provider code; record contract-only evidence before considering the change complete.
