# Proposal

## Why

ALLExport already has an OpenAPI scaffold, but its assumptions and acceptance criteria have no OpenSpec record, and response payloads are not exercised by examples. Establish the contract baseline and close validation gaps before any service or client implementation relies on it.

## What Changes

- Establish `api/openapi.yaml` as the sole normative wire contract, with OpenSpec describing behavioral requirements and acceptance scenarios rather than copying its schemas.
- Preserve generalized export workflows, sandbox/deal entry and producer/reseller profiles, decimal money, explicit unknowns, tenant-derived authority and independent approval/agreement/payment/closure states.
- Add representative accepted-job, partial-analysis, blocked-readiness, pending-receipt and error responses in the canonical YAML, and validate request and response examples through local references.
- Constrain response-envelope statuses by endpoint/HTTP outcome so accepted work cannot claim completion and blocked results cannot imply readiness.
- Extend regression checks and CI evidence for response validation, malformed example handling and status contradictions.
- Record runtime-only invariants and deferred operational/integration APIs without claiming they are implemented.

This proposal authorizes no application implementation. The existing scaffold is observed baseline work; only the validation gaps and documented contract refinements are future tasks. Any schema tightening must be called out as a compatibility change, even though no consumers currently exist.

## Capabilities

### New Capabilities

- `canonical-api-contract`: Authority, versioning, generalized transaction inputs and command/result semantics of the contract-only deliverable.
- `contract-validation`: Offline structural validation, embedded request/response example checks and meaningful regression evidence.

### Modified Capabilities

None. The project currently has no published OpenSpec capability specs.

## Impact

A later apply would affect `api/openapi.yaml`, `scripts/validate_contract.py`, `tests/test_contract.py`, the existing contract CI workflow if needed, and explanatory documentation. Python remains contract tooling only. No backend, UI, database, SDK, auth provider, external integration or billing flow is introduced. Existing runtime requirements remain descriptive until separately implemented and tested.
