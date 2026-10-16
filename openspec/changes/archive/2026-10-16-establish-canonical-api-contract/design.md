# Design

## Context

See `proposal.md` for motivation and the two capability deltas for acceptance behavior. The existing repo has a 45-operation, 155-schema OpenAPI 3.1 draft, five request examples, Python validation tooling, 17 contract tests and CI. No runtime service exists. Exploration found zero response examples and no response-example traversal in the validator. Shared envelopes also admit all four statuses independently of operation/HTTP outcome.

This design is included because response semantics cut across the contract, validator, tests and compatibility documentation. The current scaffold is a starting point, not work that needs to be recreated.

## Goals / Non-Goals

**Goals:** Make response semantics testable using the same canonical file and keep future consumer generation subordinate to it. Preserve existing successful request examples and negative regressions.

**Non-Goals:** Runtime money calculations, persistence, authorization enforcement, backend stack selection, live providers, new operational routes and billing/OAuth implementations. No generated DTO or second machine-readable schema source.

## Decisions

1. **Separate behavioral requirements from wire definitions.** OpenSpec records observable requirements and scenarios; OpenAPI owns exact shapes. Full schema copies in Markdown were rejected because they would create competing sources. Existing product and implementation-limit documentation remains explanatory.

2. **Tighten endpoint response semantics in OpenAPI.** Use endpoint/outcome-specific schema constraints or reusable compositions, preserving strict object behavior under JSON Schema 2020-12. Accepted async HTTP responses use `accepted`; successful synchronous creation uses `completed`; ordinary reads use `completed`, with `partial` permitted for partial analysis/run results. Readiness and closure additionally permit `blocked`, with conditional consistency between envelope and nested gate. GET run retrieval can complete while its nested run remains queued/running: retrieving a record is distinct from completing the job. Error responses retain their separate schema. Reusing the unrestricted envelope everywhere was rejected because contradictory outcomes currently validate.

3. **Place representative response examples beside their media-type schemas.** Include the five outcome families named in the proposal. Reuse local component references where appropriate; keep the concrete examples in OpenAPI. External fixtures that repeat the normative example payloads were rejected. Expected-invalid test mutations remain in tests and are never presented as valid API examples.

4. **Extend validation through local references.** Resolve local request-body/response/example references before examining media-type examples; validate inline and referenced schemas without extracting a component name from the last path segment. Support media-type `example` and named `examples`; schema-level example annotations are not claimed as covered. Reject external example values/references and detect reference cycles with actionable diagnostics. Reuse the installed JSON Schema tooling; no new validation framework is needed.

5. **Exercise the validator, not only individual schemas.** In-memory mutations test invalid response examples, bad references and status contradictions without editing the canonical document during tests. Retain all existing regressions. Counts distinguish operations, request examples and response examples. Existing local commands and CI remain the verification entry points.

6. **Treat tightening as an explicit draft revision.** Record the changed response-status acceptance and the absence of known consumers. During apply, update the API draft patch version from 2.1.0 to 2.1.1; leave snapshot schema_version 2.1 because domain snapshots do not change. This is a pre-adoption draft refinement, not a promise of compatibility for consumers relying on previously accepted contradictory statuses. Future adopted breaking changes need an explicit migration/version decision.

## Risks / Trade-offs

- Schema-valid examples can still describe impossible business states. Mitigation: test structural contradictions that can be represented locally and keep arithmetic, tenant access, state transitions and provider behavior explicitly runtime-only.
- Conditional/composed response schemas can become difficult to generate clients from. Mitigation: prefer simple reusable restrictions and validate strict-object composition; SDK generation is deferred until a stack is selected.
- References can form cycles or point to example data rather than schemas. Mitigation: use context-aware resolution, retain the document as the reference root and reject unsupported cases with a diagnostic.
- OpenSpec baseline requirements describe desired behavior beyond the current checks. Mitigation: leave implementation tasks unchecked and do not archive the change until a later apply supplies evidence.

## Migration Plan

No deployment or data migration is needed. On a later apply, refine response constraints and examples, extend validator traversal, add regression tests and update explanatory documentation. Run the existing validator and complete test suite. Revert those affected files together if a regression occurs; retain the planning record for revision. Do not apply, archive, regenerate clients or change application code during this proposal workflow.
