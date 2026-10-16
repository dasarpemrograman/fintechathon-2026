# Apply verification

Verified in the current cloud workspace on 16 October 2026.

- Applied API draft revision 2.1.1; the 45-operation route inventory and domain snapshot schema version 2.1 are preserved.
- `python scripts/validate_contract.py`: valid OpenAPI, 45 operations, 5 request examples and 5 response examples checked.
- `python -m unittest discover -s tests -v`: all 35 tests passed, including the original 17 regressions.
- Response regressions reject contradictory accepted/completed or blocked/ready envelopes, invalid nested amounts, pending receipts with verifier identities and invalid examples injected into a document copy.
- Reference traversal tests exercise inline/local request bodies, responses, schemas and examples; broken, external and cyclic reference chains fail. CLI failure returns nonzero with example context.
- The README setup commands were exercised in a fresh ignored `.venv` using the pinned tooling requirements.
- Existing CI invokes the same validation and test commands. `git diff --check` passed; untracked project files were also checked with no-index whitespace inspection because the repository has no initial commit.
- `openspec validate establish-canonical-api-contract --strict` passed.

All results concern the wire contract and validation tooling. No application server, database, live integration, authorization implementation or financial calculation engine was added or verified. CI itself was inspected locally, not executed by GitHub Actions. The change is applied locally and has not been archived, committed, pushed or deployed.

## OpenSpec verify review

Change: `establish-canonical-api-contract`. Scope: completeness, correctness and coherence of the contract-only increment. This review reran the checks and inspected the implementation against all 12 added requirements and 23 scenarios across both capability specs. No implementation files or task statuses were changed during verification.

| Dimension | Result |
| --- | --- |
| Completeness | All four planning artifacts available; 10/10 tracked tasks marked complete. Implementation evidence exists for all 12 requirements, with the reference-policy gap below. |
| Correctness | 35 tests passed; 45 operations and all 5 request / 5 response examples validated. 11 requirement mappings aligned; structural-reference requirement partially aligned. All 23 scenarios reviewed using tests, contract inspection and the additional multi-shipment probe below. |
| Coherence | Six design decisions checked against the implementation. Canonical wire schemas remain in OpenAPI; response constraints, example traversal and draft versioning follow the design. Reference-policy divergence noted below. |

No applicable verification dimension was skipped. Runtime service behavior, external integrations and hosted GitHub Actions execution are outside this contract-only deliverable and are not validated by these results.

### Requirement and scenario evidence

| Capability / requirement | Evidence and scenario assessment |
| --- | --- |
| Canonical / Single wire definition | `api/openapi.yaml`, README and decision record: wire definitions remain canonical; OpenSpec records requirements without duplicate schemas. |
| Canonical / General export entry | Existing both-mode/profile and upload-free entry tests; additional read-only probe validated two line items and two shipments through `ConvertToDealRequest` using KE/DE. This extra probe is not a persistent regression test. |
| Canonical / Money and unknown values | Money rejection tests; canonical partial-analysis example and nested-amount regression distinguish known-items results and missing inputs. |
| Canonical / Authority and mutation preconditions | Authority-field, protected-patch and revision/idempotency declaration tests; replay behavior is explicitly specified in OpenAPI, with runtime enforcement deferred. |
| Canonical / Response status matches outcome | Operation outcome tests, accepted-job/queued-run read test, partial-analysis checks and readiness contradictions. Closure condition is tested in isolation; see suggestion below. |
| Canonical / Business authority dimensions | Payment/closure independence regression, pending receipt and verifier checks; financing/drafting boundaries explicitly stated in the contract. Actual lender or trade actions are not implemented. |
| Canonical / Compatibility | Confirmed API 2.1.1 and Workspace/Deal schema_version 2.1; decision record documents narrowed status compatibility and no known consumers. |
| Validation / Structural failures | Duplicate-key, external/broken `$ref` and cyclic-chain tests pass. `$dynamicRef` bypass is reproduced below. |
| Validation / Request and response examples | Inline/referenced schema, response, request-body and Example Object traversal tests; invalid nested money identifies operation/status/example. |
| Validation / Relevant outcomes | Canonical accepted-job, partial-analysis, blocked-readiness, pending-receipt and structured-error examples all visited and validated. |
| Validation / Negative payloads | Invalid amounts, contradictory envelopes and invalid in-memory examples rejected; original protected-field, money and payment/closure checks retained. |
| Validation / Bounded reproducibility | Local validator and all 35 tests rerun; CI definition invokes the same commands; dependency requirements pinned. No application-readiness claim. |

### Findings

**WARNING — External dynamic references bypass the local-reference policy.**

At `scripts/validate_contract.py:131`, preflight recognizes only `$ref`. JSON Schema 2020-12 also supports `$dynamicRef`. In a read-only document copy, adding this unused component still returned successful validation with all existing counts:

```yaml
components:
  schemas:
    ExternalDynamicRefProbe:
      $dynamicRef: https://example.invalid/remote-schema
```

This contradicts the `contract-validation` requirement to reject references outside the canonical document. The present canonical file contains no such dynamic reference, and the probe made no network request. Recommendation: reject unsupported `$dynamicRef` explicitly, or validate its local-only semantics, and add regression cases for external and unresolved local dynamic references. Preserve recursive schema semantics when doing so.

**SUGGESTION — Exercise a complete closure response.**

`tests/test_responses.py:69` validates only `ClosureResponse.allOf` with an otherwise incomplete object. This proves the nested gate conditional, but cannot catch integration errors involving the full required Deal and Gate payload. Recommendation: validate a complete closure response against the operation's actual schema, then mutate the gate/envelope statuses and blockers. Keep the payload in the canonical document if it becomes a normative example.

### Verification outcome

No critical issues. One warning and one suggestion remain. The change is eligible for archive with these noted improvements under the advisory verify workflow; this is not a claim of flawless reference-policy enforcement. Nothing was archived, committed, pushed or deployed by verification.
