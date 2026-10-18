# Verification evidence mapping

Static requirement and scenario evidence; passing tests are not proof of credential-dependent lifecycle acceptance. Browser assertions and detailed test suites supplement these primary anchors.

## Requirement implementation locations

| Capability | Requirement | Implementation |
| --- | --- | --- |
| calendar-projection | Optional authorized connection | `packages/adapters/calendar.py`, `packages/adapters/calendar_policy.py` |
| calendar-projection | Approved projection preview | `packages/adapters/calendar.py`, `packages/adapters/calendar_policy.py` |
| calendar-projection | Owned event identity and retry safety | `packages/adapters/calendar.py`, `packages/adapters/calendar_policy.py` |
| calendar-projection | Revocation and demo isolation | `packages/adapters/calendar.py`, `packages/adapters/calendar_policy.py` |
| canonical-api-contract | Authority and mutation preconditions | `services/api/app.py`, `packages/contracts/runtime.py`, `services/api/commands.py`, `packages/domain/migration.py` |
| canonical-api-contract | Complete operational interfaces | `services/api/app.py`, `packages/contracts/runtime.py`, `services/api/commands.py`, `packages/domain/migration.py` |
| canonical-api-contract | Runtime conforms to the canonical schemas | `services/api/app.py`, `packages/contracts/runtime.py`, `services/api/commands.py`, `packages/domain/migration.py` |
| contract-validation | Structural failures are actionable | `scripts/validate_contract.py`, `packages/contracts/runtime.py`, `.github/workflows/contract.yml` |
| contract-validation | Examples demonstrate relevant outcomes | `scripts/validate_contract.py`, `packages/contracts/runtime.py`, `.github/workflows/contract.yml` |
| contract-validation | Verification remains bounded and reproducible | `scripts/validate_contract.py`, `packages/contracts/runtime.py`, `.github/workflows/contract.yml` |
| deal-economics | Exact decimal and FX calculations | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| deal-economics | Cost coverage and payer treatment | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| deal-economics | Producer cost and funding separation | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| deal-economics | Two-sided pricing and numeric lineage | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| deal-economics | Dated cash and declared completeness | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| deal-economics | Buyer payment stress scenarios | `packages/domain/economics.py`, `packages/domain/pricing.py`, `services/api/review_handlers.py` |
| durable-operations | Atomic mutation replay | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| durable-operations | Durable bounded jobs | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| durable-operations | Usage and entitlements stay separate from economics | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| durable-operations | Auditable sensitive operations | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| durable-operations | Reproducible local lifecycle | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| durable-operations | Observable readiness and release evidence | `services/api/app.py`, `services/api/commands.py`, `services/worker/jobs.py`, `scripts/dev.py` |
| evidence-ingestion | Document preservation and extraction | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| evidence-ingestion | Autonomous contextual discovery | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| evidence-ingestion | Provenance and source quality | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| evidence-ingestion | Reviewed facts and requirements | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| evidence-ingestion | Adapter outcomes and live evidence | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| evidence-ingestion | Untrusted content isolation | `packages/domain/discovery.py`, `packages/adapters/documents.py`, `packages/adapters/network.py`, `packages/adapters/providers.py`, `services/worker/jobs.py` |
| execution-reconciliation | Derived action gates | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| execution-reconciliation | Requirements and goods review | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| execution-reconciliation | Timeline propagation preserves agreements | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| execution-reconciliation | External actions remain evidenced records | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| execution-reconciliation | Settlement is verified and reversible | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| execution-reconciliation | Actuals and closure stay independent of buyer payment | `packages/domain/workflow.py`, `services/api/review_handlers.py`, `services/api/reconciliation.py`, `packages/domain/dates.py` |
| negotiation-finance | Joint terms comparison | `packages/domain/comparison.py`, `packages/domain/finance.py`, `packages/domain/financing.py`, `packages/domain/artifacts.py` |
| negotiation-finance | Published financing fit | `packages/domain/comparison.py`, `packages/domain/finance.py`, `packages/domain/financing.py`, `packages/domain/artifacts.py` |
| negotiation-finance | Net proceeds and debt economics | `packages/domain/comparison.py`, `packages/domain/finance.py`, `packages/domain/financing.py`, `packages/domain/artifacts.py` |
| negotiation-finance | Financing application preparation | `packages/domain/comparison.py`, `packages/domain/finance.py`, `packages/domain/financing.py`, `packages/domain/artifacts.py` |
| negotiation-finance | Controlled commercial artifacts | `packages/domain/comparison.py`, `packages/domain/finance.py`, `packages/domain/financing.py`, `packages/domain/artifacts.py` |
| seeded-demo | Explicit offline mode | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Versioned repeatable seed | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Representative data coverage | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Complete walkthrough states | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Golden economics and failure cases | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Reset is scoped and recoverable | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| seeded-demo | Demonstration acceptance is observable | `packages/domain/demo.py`, `packages/domain/demo_stages.py`, `packages/domain/demo_reset.py`, `compose.demo.yaml` |
| workspace-access | Authentication and organization membership | `services/api/auth.py`, `services/api/store.py`, `services/api/commands.py` |
| workspace-access | Tenant and reviewer isolation | `services/api/auth.py`, `services/api/store.py`, `services/api/commands.py` |
| workspace-access | Persistent exploration and deal conversion | `services/api/auth.py`, `services/api/store.py`, `services/api/commands.py` |
| workspace-access | General transaction relationships | `services/api/auth.py`, `services/api/store.py`, `services/api/commands.py` |
| workspace-access | Revision and history integrity | `services/api/auth.py`, `services/api/store.py`, `services/api/commands.py` |
| workspace-ui | Complete browser workflow | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |
| workspace-ui | Evidence behind decisions | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |
| workspace-ui | Jobs and actionable failures | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |
| workspace-ui | Review and comparison controls | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |
| workspace-ui | Accessible localized presentation | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |
| workspace-ui | Entitlement and demo transparency | `apps/web/app/components/workspace.tsx`, `apps/web/app/api/session/route.ts`, `apps/web/app/api/gateway/[...path]/route.ts` |

## Scenario evidence

These are primary evidence anchors, not a claim of one independent passing test per assertion. Calendar provider regressions use mocks; the real approved lifecycle now also has retained receipts in docs/live-acceptance-results.md and the local output artifacts. Declared source-lane acceptance also passed after source review; commercial unknowns remain explicit.

| Capability | Scenario | Primary evidence / limit |
| --- | --- | --- |
| calendar-projection | No calendar is connected | Mapped deterministic evidence: tests/test_operation_matrix.py:97 — test_every_read_route_has_canonical_success_or_owned_missing_resource_error |
| calendar-projection | Approved projection changes before delivery | Mapped deterministic evidence: tests/test_calendar_projection.py:279 — test_changed_milestone_cannot_reuse_preview_approval |
| calendar-projection | Provider accepted insert before worker stopped | Mapped deterministic evidence: tests/test_calendar_outbox.py:200 — test_crash_after_insert_reuses_provider_id_and_records_one_external_event |
| calendar-projection | External event was changed | Mapped deterministic evidence: tests/test_calendar_outbox.py:255 — test_external_edit_conflicts_and_nonowned_delete_fails |
| calendar-projection | Token is revoked | Mapped deterministic evidence: tests/test_calendar_outbox.py:397 — test_remote_revocation_outage_still_removes_local_access |
| canonical-api-contract | Client attempts to self-verify payment | Mapped deterministic evidence: tests/test_contract.py:179 — test_receipt_input_cannot_self_verify |
| canonical-api-contract | Mutation is replayed | Mapped deterministic evidence: tests/test_http_foundation.py:154 — test_stale_revision_replay_returns_original_command_receipt |
| canonical-api-contract | Runtime crosses the contract boundary | Mapped deterministic evidence: tests/test_operation_matrix.py:30 — test_every_protected_operation_enforces_current_membership_roles |
| canonical-api-contract | A user lists and reviews workspace evidence | Mapped deterministic evidence: tests/test_operation_matrix.py:97 — test_every_read_route_has_canonical_success_or_owned_missing_resource_error |
| canonical-api-contract | Handler returns an invalid successful payload | Mapped deterministic evidence: tests/test_http_foundation.py:104 — test_invalid_response_is_sanitized_and_transaction_rolled_back |
| canonical-api-contract | A prior snapshot is loaded | Mapped deterministic evidence: tests/test_snapshot_migration.py:12 — test_original_retained_and_unknown_invoice_not_invented |
| contract-validation | Route key is repeated | Mapped deterministic evidence: tests/test_contract.py:40 — test_yaml_duplicate_keys_fail |
| contract-validation | Reference is external or broken | Mapped deterministic evidence: tests/test_example_validation.py:81 — test_external_and_missing_references_fail_locally |
| contract-validation | Unused component declares an external dynamic reference | Mapped deterministic evidence: tests/test_example_validation.py:147 — test_unused_dynamic_references_fail_before_retrieval |
| contract-validation | Local dynamic reference is unsupported or unresolved | Mapped deterministic evidence: tests/test_example_validation.py:147 — test_unused_dynamic_references_fail_before_retrieval |
| contract-validation | Queued discovery result | Mapped deterministic evidence: tests/test_responses.py:142 — test_canonical_accepted_job_and_queued_run_read |
| contract-validation | Blocked shipment stage | Mapped deterministic evidence: tests/test_responses.py:195 — test_canonical_blocked_readiness_rejects_completed_envelope |
| contract-validation | Receipt proof recorded | Mapped deterministic evidence: tests/test_responses.py:176 — test_canonical_pending_receipt_cannot_have_verifier_or_be_verified |
| contract-validation | Complete closure response is mutated | Mapped deterministic evidence: tests/test_responses.py:206 — test_complete_closure_operation_payload |
| contract-validation | Contract checks pass | Mapped deterministic evidence: tests/test_example_validation.py:165 — test_counts_are_separate |
| deal-economics | FX rate changes | Mapped deterministic evidence: tests/test_demo_goldens.py:80 — test_fx_and_freight_shock_affect_all_unlocked_exposures |
| deal-economics | Invalid target margin | Mapped deterministic evidence: tests/test_economics.py:126 — test_decimal_currency_and_fx_constraints |
| deal-economics | Synthetic W/M tariff with minimum | Mapped deterministic evidence: tests/test_economics.py:110 — test_wm_air_and_fcl_use_explicit_quote_basis |
| deal-economics | Buyer charge paid in advance by seller | Mapped deterministic evidence: tests/test_pricing_treatment.py:54 — test_reimbursement_is_not_revenue_and_is_not_twice_buyer_total |
| deal-economics | Producer regression fixture | Mapped deterministic evidence: tests/test_demo_goldens.py:56 — test_producer_and_reseller_full_engine_goldens |
| deal-economics | Seller floor exceeds market observations | Mapped deterministic evidence: tests/test_pricing_treatment.py:92 — test_comparator_exclusions_normalization_and_floor_market_conflict |
| deal-economics | Profitable reseller still cannot fund order | Mapped deterministic evidence: tests/test_economics.py:50 — test_golden_baseline_and_timely_late_financing |
| deal-economics | Same-day order is unknown | Mapped deterministic evidence: tests/test_economics.py:140 — test_unknown_sequence_uses_debit_first |
| deal-economics | Buyer receipt shifts beyond loan maturity | Mapped deterministic evidence: tests/test_financing_settlement.py:52 — test_net_loan_preserves_goldens_and_late_buyer_misses_fixed_maturity |
| durable-operations | Concurrent funds reservation | Mapped deterministic evidence: tests/test_cash_concurrency.py:10 — test_two_transactions_cannot_reserve_the_same_organizational_funds |
| durable-operations | Client retries after response loss | Mapped deterministic evidence: tests/test_http_foundation.py:154 — test_stale_revision_replay_returns_original_command_receipt |
| durable-operations | Worker stops during discovery | Mapped deterministic evidence: tests/test_job_recovery.py:53 — test_three_interrupted_claims_exhaust_budget_without_charge |
| durable-operations | Inputs change while analysis runs | Mapped deterministic evidence: tests/test_job_recovery.py:68 — test_older_input_completion_retains_output_without_replacing_head |
| durable-operations | Entitlement expires during an existing deal | Mapped deterministic evidence: tests/test_entitlements.py:47 — test_included_before_addon_then_expiry_preserves_deterministic_and_manual_work |
| durable-operations | Reviewer reverses a receipt | Mapped deterministic evidence: tests/test_workflow_commands.py:113 — test_pending_partial_verified_and_reversal_are_distinct |
| durable-operations | Fresh checkout is prepared | Fresh verification database migrated and seeded; authenticated demo browser/API journeys pass; registry/workspace fingerprints survive restart. Existing pinned dependency images reused; no new frozen install in this verification. |
| durable-operations | Live credentials are missing | Mapped deterministic evidence: tests/test_http_foundation.py:226 — test_diagnostics_are_tenant_scoped_and_admin_only |
| evidence-ingestion | Ambiguous Chinese contract | Mapped deterministic evidence: tests/test_document_extraction.py:25 — test_chinese_original_script_and_ambiguity_are_preserved |
| evidence-ingestion | Scanned source needs OCR | Mapped deterministic evidence: tests/test_document_extraction.py:9 — test_actual_text_native_pdf_and_scanned_sources |
| evidence-ingestion | Public research from sandbox | Mapped deterministic evidence: tests/test_discovery_planning.py:8 — test_outward_china_uses_export_and_destination_import_separately |
| evidence-ingestion | Search snippet lacks fetched support | Mapped deterministic evidence: tests/test_pricing_treatment.py:92 — test_comparator_exclusions_normalization_and_floor_market_conflict |
| evidence-ingestion | Quotation covers several cost components | Mapped deterministic evidence: tests/test_cost_coverage.py:31 — test_shared_liability_is_allocated_once_and_flexible_costs_can_move |
| evidence-ingestion | Supplier and buyer quantities conflict | Mapped deterministic evidence: tests/test_document_pipeline.py:315 — test_conflicting_candidates_and_archived_exports_preserve_originals |
| evidence-ingestion | Required provider credentials are absent | Mapped deterministic evidence: tests/test_provider_adapters.py:70 — test_success_partial_auth_rate_limit_and_outage_receipts |
| evidence-ingestion | Live lane acceptance is evaluated | Executed: Brave/Gemini/FX pass; nine scoped searches, eighteen retrieved/parsed source pages, three FX pairs, three market observations and three finance-fit reviews are retained for the precise test goods in config/live-acceptance-scopes-v1.json. Review/exclusions: docs/live-acceptance-results.md. |
| evidence-ingestion | Source requests privileged action | Mapped deterministic evidence: tests/test_model_tasks.py:8 — test_privileged_instructions_extra_numbers_and_invented_references_fail |
| execution-reconciliation | Owner approves plan before buyer funds arrive | Mapped deterministic evidence: tests/test_seeded_acceptance.py:37 — test_four_checkpoint_histories_have_causal_and_independent_states |
| execution-reconciliation | Goods fail agreed specification | Mapped deterministic evidence: tests/test_workflow_commands.py:250 — test_photographs_without_measurements_cannot_establish_goods_conformity |
| execution-reconciliation | Arrival forecast changes | Mapped deterministic evidence: tests/test_workflow_commands.py:721 — test_delayed_milestones_move_relative_forecasts_without_changing_fixed_dates |
| execution-reconciliation | Actual acceptance is the payment anchor | Mapped deterministic evidence: tests/test_workflow_commands.py:788 — test_actual_delivery_does_not_verify_acceptance_payment_anchor |
| execution-reconciliation | Shipment occurred outside the app while blocked | Mapped deterministic evidence: tests/test_workflow_commands.py:272 — test_blocked_external_shipment_retains_its_unmet_conditions |
| execution-reconciliation | Duplicate proof and later reversal | Mapped deterministic evidence: tests/test_workflow_commands.py:113 — test_pending_partial_verified_and_reversal_are_distinct |
| execution-reconciliation | Buyer paid while freight invoice is open | Mapped deterministic evidence: tests/test_workflow_commands.py:147 — test_buyer_paid_does_not_resolve_seller_liabilities |
| execution-reconciliation | All declared obligations are resolved | Mapped deterministic evidence: tests/test_seeded_acceptance.py:70 — test_full_actual_http_closure_payload_and_tenant_denial |
| negotiation-finance | Combined negotiation improves liquidity | Mapped deterministic evidence: tests/test_workflow_commands.py:173 — test_joint_scenario_changes_reproject_terms_and_costs_without_writes |
| negotiation-finance | Post-shipment product cannot fund production | Mapped deterministic evidence: tests/test_finance_preparation.py:81 — test_stage_instrument_entity_tenor_and_currency_fit_are_independent |
| negotiation-finance | Published lender rate is absent | Mapped deterministic evidence: tests/test_finance_preparation.py:106 — test_missing_rate_and_unreviewed_security_stay_unknown |
| negotiation-finance | Synthetic loan covers baseline gap | Mapped deterministic evidence: tests/test_economics.py:50 — test_golden_baseline_and_timely_late_financing |
| negotiation-finance | Same loan arrives late | Mapped deterministic evidence: tests/test_economics.py:50 — test_golden_baseline_and_timely_late_financing |
| negotiation-finance | Preparation checklist is complete | Mapped deterministic evidence: tests/test_finance_preparation.py:172 — test_ready_pack_is_preparation_and_missing_required_document_blocks_it |
| negotiation-finance | Draft amount differs from calculated scenario | Mapped deterministic evidence: tests/test_artifacts.py:8 — test_template_binds_exact_scenario_amounts_dates_and_missing_legal_terms |
| negotiation-finance | Evidence changes after owner review | Mapped deterministic evidence: tests/test_document_pipeline.py:392 — test_effective_dates_and_expiry_invalidate_reviews_without_editing_history |
| seeded-demo | Demo is used with outbound access denied | Executed: separate internal-network Docker demo with provider credentials excluded and public TCP egress blocked; all fourteen browser journeys have passing evidence (initial 13 plus targeted Calendar helper rerun). |
| seeded-demo | Synthetic evidence is referenced outside demo scope | Mapped deterministic evidence: tests/test_storage_access.py:69 — test_tenant_lookup_and_registry_integrity |
| seeded-demo | Seed command runs twice | Mapped deterministic evidence: tests/test_seeded_acceptance.py:138 — test_seed_replay_does_not_duplicate_resources |
| seeded-demo | Evaluator switches roles and tenants | Mapped deterministic evidence: tests/test_operation_matrix.py:30 — test_every_protected_operation_enforces_current_membership_roles |
| seeded-demo | Historical fixture is not a product boundary | Mapped deterministic evidence: tests/test_contract.py:44 — test_both_modes_and_profiles_general_countries |
| seeded-demo | User follows the successful lifecycle | Mapped deterministic evidence: tests/test_seeded_acceptance.py:70 — test_full_actual_http_closure_payload_and_tenant_denial |
| seeded-demo | User follows a blocked lifecycle | Mapped deterministic evidence: tests/test_seeded_acceptance.py:37 — test_four_checkpoint_histories_have_causal_and_independent_states |
| seeded-demo | Baseline and funding alternative are calculated | Mapped deterministic evidence: tests/test_demo_goldens.py:56 — test_producer_and_reseller_full_engine_goldens |
| seeded-demo | User-owned deal exists beside demo data | Mapped deterministic evidence: tests/test_demo_reset.py:10 — test_namespace_preflight_preserves_unrelated_and_blocks_mixed_ownership |
| seeded-demo | Demo checks pass without live credentials | Mapped deterministic evidence: tests/test_provider_adapters.py:201 — test_synthetic_and_cached_receipts_keep_their_own_modes |
| workspace-access | Valid member signs in | Mapped deterministic evidence: tests/test_storage_access.py:40 — test_real_password_session_expiry_and_membership |
| workspace-access | Demo entry attempted outside demo mode | Mapped deterministic evidence: tests/test_storage_access.py:60 — test_demo_shortcut_disabled |
| workspace-access | Another tenant's evidence identifier is used | Mapped deterministic evidence: tests/test_storage_access.py:69 — test_tenant_lookup_and_registry_integrity |
| workspace-access | Unauthorized reviewer verifies payment | Mapped deterministic evidence: tests/test_operation_matrix.py:30 — test_every_protected_operation_enforces_current_membership_roles |
| workspace-access | Exploration becomes a concrete transaction | Mapped deterministic evidence: tests/test_document_pipeline.py:315 — test_conflicting_candidates_and_archived_exports_preserve_originals |
| workspace-access | Producer uses previously paid inventory | Mapped deterministic evidence: tests/test_demo_goldens.py:121 — test_prior_paid_economic_overhead_has_no_new_cash_event |
| workspace-access | Freight quote changes after review | Mapped deterministic evidence: tests/test_document_pipeline.py:392 — test_effective_dates_and_expiry_invalidate_reviews_without_editing_history |
| workspace-ui | User completes a deal journey | Mapped deterministic evidence: tests/browser/workspace.spec.ts:92 — BROWSER:seeded database journey uses the browser, API and worker |
| workspace-ui | User inspects an incomplete freight estimate | Mapped deterministic evidence: tests/test_cost_coverage.py:45 — test_unknown_cost_is_blocked_and_reference_fx_cannot_change_native_capacity |
| workspace-ui | Analysis provider fails after partial work | Mapped deterministic evidence: tests/test_job_recovery.py:91 — test_cancellation_preserves_committed_outputs |
| workspace-ui | Ordinary admin views receipt proof | Mapped deterministic evidence: tests/test_operation_matrix.py:30 — test_every_protected_operation_enforces_current_membership_roles |
| workspace-ui | Local-date deadline is displayed | Mapped deterministic evidence: tests/browser/workspace.spec.ts:3 — BROWSER:funding dates preserve local dates and declared timezones; unique per-run marker and exactly-one card assertion pass in the fresh local browser suite (.local/verify-local-browser.log); earlier two-run evidence remains historical. |
| workspace-ui | Allowance is exhausted | Mapped deterministic evidence: tests/test_entitlements.py:47 — test_included_before_addon_then_expiry_preserves_deterministic_and_manual_work |

## Local rerun — 18 October 2026

Current source anchors were rechecked (80 Python scenario anchors). Full backend: 178 tests and 918 subtests passed; 146/146 successful canonical operations. Browser: initial 13 passed/1 Windows helper timeout, then that Calendar case passed with the ignored local Docker helper harness. Real Calendar lifecycle and complete source acceptance remain unverified. See verification.md for current receipts and limits.

## Live completion — 18 October 2026

Tasks 11.5 and 12.3 passed, 74/74 complete. Calendar real insert/response-loss retry/update/ETag conflict/delete/revocation are retained. Google Account grant absence, removed local credentials, refused future sync and intact timeline complete revocation evidence; immediate old-token invalidation was an extra harness expectation, not falsely reported as observed. A real UTC-offset comparison defect was fixed with a regression. Live retrieval also covers all declared source scopes, with source hashes, normalized observations, finance-fit distinctions, exact HS6 candidates, and explicit pricing/control unknowns. Fresh backend regression: 181 tests and 918 subtests; targeted Calendar browser regression: four passed.
