"""Transactional workflow tests exercise services and canonical response schemas."""

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
import unittest
import sqlalchemy as sa
from services.api import store, auth, commands
from services.api.settings import settings
from services.api.review_handlers import receipt_command
from services.api.reconciliation import reconcile_command
from services.api.handlers import write_operation
from packages.domain.demo import financial_case, MANIFEST
from packages.contracts.runtime import validate_response


class WorkflowCommandTests(unittest.TestCase):
    def setUp(self):
        self.conn = store.engine.connect()
        self.tx = self.conn.begin()
        self.identity = auth.bootstrap(
            self.conn,
            store.uid("flow") + "@example.test",
            "workflow-only-password",
            "Owner",
            "Workflow Test",
        )
        self.context = {
            "tenant": self.identity["organization_id"],
            "actor": self.identity["user_id"],
            "roles": ["owner"],
            "scope": "real",
            "dataset": None,
            "request_id": store.uid("request"),
        }
        self.workspace = commands.new_workspace(
            self.conn,
            self.context,
            {
                "mode": "deal",
                "business_profile": "reseller",
                "seller_domicile": "ID",
                "dispatch_country": "ID",
                "destination_country": "SG",
                "reporting_currency": "IDR",
                "owner_timezone": "Asia/Jakarta",
                "product": {"description": "Coffee"},
            },
        )
        case = next(c for c in MANIFEST["cases"] if c["key"] == "id-reseller")
        body, *_ = financial_case(
            case, datetime(2026, 10, 16, tzinfo=timezone.utc), "unused"
        )
        # Fixture values are synthetic; this isolated normal-scope test has no source assertions.
        import json

        body = json.loads(
            json.dumps(body).replace("demo_id_reseller_", store.uid("fixture") + "_")
        )
        self.evidence = {
            **store.meta(self.context["tenant"], self.context["actor"], "evidence"),
            "review_status": "confirmed",
            "valid_until": None,
            "mode": "user_provided",
        }
        store.save(
            self.conn,
            self.context["tenant"],
            "evidence",
            self.evidence,
            parent=self.workspace["id"],
        )
        body = json.loads(json.dumps(body).replace("unused", self.evidence["id"]))
        self.deal = commands.convert_deal(self.conn, self.context, self.workspace, body)

    def tearDown(self):
        self.tx.rollback()
        self.conn.close()

    def record(self, obligation, amount):
        return receipt_command(
            self.conn,
            self.context,
            "recordReceipt",
            self.deal,
            {
                "received_amount": {"amount": amount, "currency": "IDR"},
                "value_date": "2026-10-16",
                "allocations": [
                    {
                        "obligation_id": obligation["id"],
                        "amount": {"amount": amount, "currency": "IDR"},
                    }
                ],
                "evidence_ids": [self.evidence["id"]],
            },
        )["result"]

    def verify(self, receipt, disposition="verified"):
        return receipt_command(
            self.conn,
            self.context,
            "verifyReceipt",
            self.deal,
            {
                "receipt_id": receipt["id"],
                "disposition": disposition,
                "evidence_ids": [self.evidence["id"]],
                "settled_at": "2026-10-16T10:00:00Z",
            },
        )["result"]

    def test_pending_partial_verified_and_reversal_are_distinct(self):
        obligation = commands.children(
            self.conn, self.context["tenant"], "obligation", self.deal
        )[0]
        receipt = self.record(obligation, "1")
        self.assertEqual(
            store.get(
                self.conn, self.context["tenant"], "obligation", obligation["id"]
            )["status"],
            "proposed",
        )
        verified = self.verify(receipt)
        self.assertEqual(
            store.get(
                self.conn, self.context["tenant"], "obligation", obligation["id"]
            )["status"],
            "partially_settled",
        )
        self.verify(verified, "reversed")
        self.assertEqual(
            store.get(
                self.conn, self.context["tenant"], "obligation", obligation["id"]
            )["status"],
            "open",
        )
        self.assertEqual(
            store.get(self.conn, self.context["tenant"], "receipt", receipt["id"])[
                "status"
            ],
            "pending",
        )
        with self.assertRaises(store.DomainError):
            self.verify(receipt)

    def test_buyer_paid_does_not_resolve_seller_liabilities(self):
        seller = next(p["id"] for p in self.deal["parties"] if "seller" in p["roles"])
        for obligation in commands.children(
            self.conn, self.context["tenant"], "obligation", self.deal
        ):
            if obligation["payee_party_id"] == seller:
                self.verify(self.record(obligation, obligation["amount"]["amount"]))
        self.assertEqual(self.deal["states"]["buyer_payment"], "paid")
        self.assertEqual(self.deal["states"]["internal_closure"], "reconciling")
        self.assertTrue(
            any(
                o["status"] == "open"
                for o in commands.children(
                    self.conn, self.context["tenant"], "obligation", self.deal
                )
            )
        )

    def test_overallocated_and_duplicate_proof_fail(self):
        obligation = commands.children(
            self.conn, self.context["tenant"], "obligation", self.deal
        )[0]
        receipt = self.record(obligation, "1")
        with self.assertRaises(store.DomainError):
            self.record(obligation, "1")

    def test_joint_scenario_changes_reproject_terms_and_costs_without_writes(self):
        before = commands.children(
            self.conn, self.context["tenant"], "obligation", self.deal
        )
        proposal = deepcopy(self.deal)
        proposal["payment_terms"][0]["amount"]["amount"] = "56000000"
        proposal["procurement"]["purchase_lines"][0]["unit_cost"]["amount"] = "9000000"
        resources = {
            "cost_line": commands.children(
                self.conn, self.context["tenant"], "cost_line", self.deal
            ),
            "obligation": before,
        }
        costs, obligations = commands.analysis_inputs(
            self.conn,
            self.context,
            proposal,
            resources,
            [{"path": "/payment_terms"}, {"path": "/procurement"}],
        )
        self.assertEqual(
            next(
                o for o in obligations if o["id"] == proposal["payment_terms"][0]["id"]
            )["amount"]["amount"],
            "56000000",
        )
        self.assertEqual(costs[0]["rate"]["amount"], "9000000")
        self.assertEqual(
            before,
            commands.children(
                self.conn, self.context["tenant"], "obligation", self.deal
            ),
        )

    def test_reservations_cannot_exceed_shared_ledger(self):
        cash = self.deal["constraints"]["cash_snapshot"]
        write_operation(
            self.conn,
            self.context,
            "verifyCashResources",
            self.deal,
            {
                "cash_snapshot_hash": store.digest(cash),
                "evidence_ids": [self.evidence["id"]],
            },
        )
        body = {
            "action": "reserve",
            "reservation_id": None,
            "amount": {"amount": "40000000", "currency": "IDR"},
            "cash_snapshot_hash": store.digest(cash),
        }
        write_operation(self.conn, self.context, "reserveCash", self.deal, body)
        with self.assertRaises(store.DomainError):
            write_operation(self.conn, self.context, "reserveCash", self.deal, body)

    def test_role_and_session_revocation(self):
        with self.assertRaises(store.DomainError):
            auth.require_role(
                {"roles": ["production_procurement"]}, ["finance_reviewer"]
            )
        user = (
            self.conn.execute(
                sa.select(store.users).where(
                    store.users.c.id == self.identity["user_id"]
                )
            )
            .mappings()
            .one()
        )
        login = auth.create_session(self.conn, user)
        context = auth.authenticate(self.conn, "Bearer " + login["access_token"])
        context.update(actor=self.identity["user_id"], request_id="request_test")
        write_operation(self.conn, context, "logout", None, {})
        with self.assertRaises(store.DomainError):
            auth.authenticate(self.conn, "Bearer " + login["access_token"])

    def test_photographs_without_measurements_cannot_establish_goods_conformity(self):
        from services.api.review_handlers import execute_review

        with self.assertRaises(store.DomainError) as caught:
            execute_review(
                self.conn,
                self.context,
                "reviewGoods",
                self.deal,
                {
                    "evidence_ids": [self.evidence["id"]],
                    "shipment_id": None,
                    "status": "ready",
                    "inspection_basis": "photos_only",
                    "measurements": [],
                    "reviewed_specification_hash": store.digest(
                        self.deal["line_items"]
                    ),
                },
            )
        self.assertEqual(caught.exception.code, "MEASURED_INSPECTION_REQUIRED")

    def test_blocked_external_shipment_retains_its_unmet_conditions(self):
        from services.api.review_handlers import execute_review

        body = {
            "shipment_id": self.deal["shipments"][0]["id"],
            "kind": "in_transit",
            "occurred_at": "2026-08-01T12:00:00Z",
            "evidence_ids": [self.evidence["id"]],
            "exception_reason": None,
        }
        with self.assertRaises(store.DomainError) as caught:
            execute_review(
                self.conn, self.context, "recordShipmentEvent", self.deal, body
            )
        self.assertEqual(caught.exception.code, "EXCEPTION_REQUIRED")
        body["exception_reason"] = (
            "External shipment occurred despite unresolved controls."
        )
        result = execute_review(
            self.conn, self.context, "recordShipmentEvent", self.deal, body
        )["result"]
        self.assertTrue(result["unmet_conditions"])
        self.assertEqual(result["exception_reason"], body["exception_reason"])
        self.assertEqual(self.deal["states"]["shipment"], "exception")

    def test_buyer_stress_preserves_actual_receipts_and_fixed_supplier_dates(self):
        scenario = {
            **store.meta(self.context["tenant"], self.context["actor"], "scenario"),
            "base_revision": {"id": self.deal["id"], "revision": self.deal["revision"]},
            "patches": [],
            "funding_option_ids": [],
            "assumption_ids": [],
            "status": "hypothetical",
        }
        store.save(
            self.conn,
            self.context["tenant"],
            "scenario",
            scenario,
            parent=self.deal["id"],
        )
        seller = next(p["id"] for p in self.deal["parties"] if "seller" in p["roles"])
        obligations = commands.children(
            self.conn, self.context["tenant"], "obligation", self.deal
        )
        buyer = next(o for o in obligations if o["payee_party_id"] == seller)
        self.verify(self.record(buyer, "1"))
        original_receipts = deepcopy(
            commands.children(self.conn, self.context["tenant"], "receipt", self.deal)
        )
        original_obligations = deepcopy(
            commands.children(
                self.conn, self.context["tenant"], "obligation", self.deal
            )
        )
        results = {}
        for kind, fraction in [
            ("on_time", "1"),
            ("delayed", "1"),
            ("partial", "0.5"),
            ("disputed", "0"),
            ("unpaid", "0"),
        ]:
            results[kind] = reconcile_command(
                self.conn,
                self.context,
                "calculateBuyerRisk",
                self.deal,
                {
                    "scenario_id": scenario["id"],
                    "kind": kind,
                    "receipt_fraction": fraction,
                    "delay_days": 30 if kind == "delayed" else 0,
                },
            )["result"]
            self.assertIn(
                "STRESS_NOT_PROBABILITY", [w["code"] for w in results[kind]["warnings"]]
            )
        self.assertEqual(results["on_time"]["remaining_exposure"]["amount"], "0.00")
        self.assertEqual(
            results["partial"]["remaining_exposure"]["amount"], "79999999.50"
        )
        self.assertEqual(
            results["unpaid"]["remaining_exposure"]["amount"], "159999999.00"
        )
        self.assertEqual(
            results["disputed"]["remaining_exposure"],
            results["unpaid"]["remaining_exposure"],
        )
        self.assertGreater(
            results["delayed"]["cash_metrics"]["horizon_end"],
            results["on_time"]["cash_metrics"]["horizon_end"],
        )
        self.assertEqual(
            commands.children(self.conn, self.context["tenant"], "receipt", self.deal),
            original_receipts,
        )
        self.assertEqual(
            commands.children(
                self.conn, self.context["tenant"], "obligation", self.deal
            ),
            original_obligations,
        )

    def test_membership_updates_apply_to_existing_sessions_and_last_owner_is_retained(
        self,
    ):
        from fastapi.testclient import TestClient
        from services.api.app import app
        import test_document_pipeline as document_fixture

        another = auth.bootstrap(
            self.conn,
            store.uid("member") + "@example.test",
            "membership-test-password",
            "Another User",
            "Other Organization",
        )
        owner_user = (
            self.conn.execute(
                sa.select(store.users).where(
                    store.users.c.id == self.identity["user_id"]
                )
            )
            .mappings()
            .one()
        )
        other_user = (
            self.conn.execute(
                sa.select(store.users).where(store.users.c.id == another["user_id"])
            )
            .mappings()
            .one()
        )
        owner_token = auth.create_session(self.conn, owner_user)["access_token"]
        other_token = auth.create_session(self.conn, other_user)["access_token"]
        with patch.object(store, "engine", document_fixture.Engine(self.conn)):
            client = TestClient(app)

            def post(path, body, token=owner_token):
                return client.post(
                    "/v2/" + path,
                    json=body,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Idempotency-Key": store.uid("member_command"),
                    },
                )

            path = "organizations/" + self.context["tenant"] + "/memberships"
            refused = post(
                path,
                {"user_id": self.identity["user_id"], "roles": ["finance_reviewer"]},
            )
            self.assertEqual(refused.status_code, 409, refused.text)
            allowed = post(
                path,
                {"user_id": another["user_id"], "roles": ["production_procurement"]},
            )
            self.assertEqual(allowed.status_code, 200, allowed.text)
            self.assertEqual(allowed.json()["result"]["user_id"], another["user_id"])
            selected = post(
                "auth/organization",
                {"organization_id": self.context["tenant"]},
                other_token,
            )
            self.assertEqual(selected.status_code, 200, selected.text)
            receipt_body = {
                "expected_revision": self.deal["revision"],
                "receipt_id": "receipt_absent",
                "disposition": "verified",
                "evidence_ids": [self.evidence["id"]],
                "reason": "Authorization test",
                "settled_at": None,
            }
            denied = post(
                "deals/" + self.deal["id"] + "/receipt-verifications",
                receipt_body,
                other_token,
            )
            self.assertEqual(denied.status_code, 403, denied.text)
            promoted = post(
                path, {"user_id": another["user_id"], "roles": ["finance_reviewer"]}
            )
            self.assertEqual(promoted.status_code, 200, promoted.text)
            permitted = post(
                "deals/" + self.deal["id"] + "/receipt-verifications",
                receipt_body,
                other_token,
            )
            self.assertEqual(permitted.status_code, 404, permitted.text)
            removed = post(path, {"user_id": another["user_id"], "roles": []})
            self.assertEqual(removed.status_code, 200, removed.text)
            session = client.get(
                "/v2/auth/session", headers={"Authorization": "Bearer " + other_token}
            )
            self.assertEqual(session.status_code, 200, session.text)
            self.assertIsNone(session.json()["result"]["organization_id"])
            self.assertEqual(
                client.get(
                    "/v2/workspaces", headers={"Authorization": "Bearer " + other_token}
                ).status_code,
                403,
            )

    def test_new_counterparty_acceptance_cannot_bind_an_older_revision(self):
        from services.api.review_handlers import execute_review

        party = next(p["id"] for p in self.deal["parties"] if "buyer" in p["roles"])
        with self.assertRaises(store.DomainError) as caught:
            execute_review(
                self.conn,
                self.context,
                "recordAgreement",
                self.deal,
                {
                    "party_id": party,
                    "accepted_revision": self.deal["revision"] - 1,
                    "evidence_ids": [self.evidence["id"]],
                },
            )
        self.assertEqual(caught.exception.code, "ACCEPTED_REVISION")

    def test_manually_reviewed_finance_products_screen_through_http_without_usage_charge(
        self,
    ):
        import json
        import test_finance_preparation as finance_fixture
        import test_document_pipeline as document_fixture
        from services.worker.jobs import process
        from fastapi.testclient import TestClient
        from services.api.app import app

        fixture = finance_fixture.FinancePreparationTests()
        fixture.setUp()
        product = json.loads(
            json.dumps(fixture.product).replace(
                '"proof"', json.dumps(self.evidence["id"])
            )
        )
        product["eligible_instruments"] = ["milestone"]
        user = (
            self.conn.execute(
                sa.select(store.users).where(
                    store.users.c.id == self.identity["user_id"]
                )
            )
            .mappings()
            .one()
        )
        token = auth.create_session(self.conn, user)["access_token"]
        headers = {"Authorization": "Bearer " + token}
        root = "deals/" + self.deal["id"]

        def process_id(identifier):
            row = dict(
                self.conn.execute(
                    sa.select(store.jobs).where(store.jobs.c.id == identifier)
                )
                .mappings()
                .one()
            )
            self.conn.execute(
                store.jobs.update()
                .where(store.jobs.c.id == identifier)
                .values(state="running", attempts=row["attempts"] + 1)
            )
            return process(row)

        with patch.object(store, "engine", document_fixture.Engine(self.conn)):
            client = TestClient(app)

            def post(path, body):
                return client.post(
                    "/v2/" + path,
                    json=body,
                    headers={
                        **headers,
                        "Idempotency-Key": store.uid("finance_command"),
                    },
                )

            recorded = post(
                root + "/finance-products",
                {"expected_revision": self.deal["revision"], "financeProduct": product},
            )
            self.assertEqual(recorded.status_code, 200, recorded.text)
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            accepted = post(
                root + "/analyses",
                {
                    "expected_revision": current["revision"],
                    "scenario_id": None,
                    "scope": "full",
                    "execution": "deterministic",
                },
            )
            self.assertEqual(accepted.status_code, 202, accepted.text)
            run = process_id(accepted.json()["result"]["run"]["id"])
            self.assertEqual(run["status"], "succeeded")
            analysis_ref = next(
                ref for ref in run["output_refs"] if ref["kind"] == "analysis"
            )
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            request = json.loads(
                json.dumps(fixture.request).replace(
                    '"proof"', json.dumps(self.evidence["id"])
                )
            )
            request["company"]["seller_party_id"] = next(
                p["id"] for p in current["parties"] if "seller" in p["roles"]
            )
            request.update(
                expected_revision=current["revision"], analysis_id=analysis_ref["id"]
            )
            admitted = post(root + "/finance-options", request)
            self.assertEqual(admitted.status_code, 202, admitted.text)
            self.assertFalse(admitted.json()["result"]["run"]["usage"]["chargeable"])
            matched = process_id(admitted.json()["result"]["run"]["id"])
            self.assertEqual(matched["status"], "succeeded")
            options = client.get("/v2/" + root + "/finance-options", headers=headers)
            self.assertEqual(options.status_code, 200, options.text)
            self.assertEqual(
                options.json()["result"]["items"][0]["fit"], "potentially_suitable"
            )
            self.assertEqual(
                commands.all_records(self.conn, self.context["tenant"], "usage"), []
            )
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            proposed = fixture.option()
            proposed.pop("id")
            proposed.update(
                product_id=recorded.json()["result"]["id"],
                fit_reasons=["Reviewed declared criteria."],
                failed_predicates=[],
                unknown_predicates=[],
                earliest_draw_milestone_id=None,
                assumptions=[],
                external_facility_evidence_ids=[self.evidence["id"]],
            )
            proposed = json.loads(
                json.dumps(proposed).replace('"proof"', json.dumps(self.evidence["id"]))
            )
            proposed["schedule"][0]["schedule"]["due"]["instant"] = (
                "2026-10-28T12:00:00Z"
            )
            proposed["schedule"][1]["schedule"]["due"]["instant"] = (
                "2026-12-09T12:00:00Z"
            )
            proposed["schedule"][2]["schedule"]["due"]["instant"] = (
                "2026-12-09T12:01:00Z"
            )
            for index, event in enumerate(proposed["schedule"]):
                event["sequence"] = index
            created = post(
                root + "/funding-options",
                {"expected_revision": current["revision"], "fundingOption": proposed},
            )
            self.assertEqual(created.status_code, 200, created.text)
            option_id = created.json()["result"]["id"]
            self.assertTrue(
                all(
                    event["status"] == "proposed"
                    for event in created.json()["result"]["schedule"]
                )
            )
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            constraints = deepcopy(current["constraints"])
            constraints["credit_tenor_limit_days"] = None
            changed = client.patch(
                "/v2/" + root + "/facts",
                json={
                    "expected_revision": current["revision"],
                    "patches": [
                        {
                            "op": "replace",
                            "path": "/constraints",
                            "value": constraints,
                            "reason": "No additional credit-tenor cap for this preparation case.",
                            "evidence_ids": [self.evidence["id"]],
                            "agreement_required_from": [],
                        }
                    ],
                },
                headers={**headers, "Idempotency-Key": store.uid("owner_constraint")},
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            selected = post(
                root + "/scenarios",
                {
                    "expected_revision": current["revision"],
                    "base_revision": {
                        "id": current["id"],
                        "revision": current["revision"],
                    },
                    "patches": [],
                    "funding_option_ids": [option_id],
                },
            )
            self.assertEqual(selected.status_code, 202, selected.text)
            scenario = selected.json()["result"]["scenario"]
            analyzed = process_id(selected.json()["result"]["job"]["run"]["id"])
            self.assertEqual(analyzed["status"], "succeeded")
            current = client.get("/v2/" + root, headers=headers).json()["result"][
                "deal"
            ]
            prepared = post(
                root + "/finance-packs",
                {
                    "expected_revision": current["revision"],
                    "funding_option_id": option_id,
                    "scenario_id": scenario["id"],
                    "evidence_ids": [self.evidence["id"]],
                },
            )
            self.assertEqual(prepared.status_code, 202, prepared.text)
            completed = process_id(prepared.json()["result"]["run"]["id"])
            self.assertEqual(
                completed["status"], "succeeded", completed.get("blockers")
            )
            pack_ref = next(
                ref for ref in completed["output_refs"] if ref["kind"] == "finance_pack"
            )
            pack = client.get(pack_ref["href"], headers=headers)
            self.assertEqual(pack.status_code, 200, pack.text)
            self.assertEqual(
                pack.json()["result"]["preparation_status"], "application_ready"
            )
            self.assertTrue(pack.json()["result"]["funds_use_schedule"])
            final = client.get("/v2/" + root, headers=headers).json()["result"]["deal"]
            self.assertEqual(
                final["states"]["funding_preparation"], "application_ready"
            )
            self.assertEqual(final["states"]["execution_gate"], "blocked")
            self.assertEqual(
                commands.all_records(self.conn, self.context["tenant"], "usage"), []
            )

    def test_delayed_milestones_move_relative_forecasts_without_changing_fixed_dates(
        self,
    ):
        from services.api.review_handlers import execute_review
        from packages.domain.economics import resolve_schedule

        fixed = {
            "kind": "fixed",
            "due": {"instant": "2026-10-20T12:00:00Z", "timezone": "UTC"},
        }
        anchor = execute_review(
            self.conn,
            self.context,
            "recordMilestone",
            self.deal,
            {
                "milestone_id": None,
                "kind": "arrival",
                "schedule": fixed,
                "date_kind": "forecast",
                "value": fixed["due"],
                "evidence_ids": [],
            },
        )["result"]
        relative = {
            "kind": "event_relative",
            "anchor_milestone_id": anchor["id"],
            "offset_days": 30,
            "day_basis": "calendar",
            "business_calendar_id": None,
        }
        first = resolve_schedule(relative, {anchor["id"]: anchor}, {})
        updated = execute_review(
            self.conn,
            self.context,
            "recordMilestone",
            self.deal,
            {
                "milestone_id": anchor["id"],
                "kind": "arrival",
                "schedule": fixed,
                "date_kind": "forecast",
                "value": {"instant": "2026-10-30T12:00:00Z", "timezone": "UTC"},
                "evidence_ids": [],
            },
        )["result"]
        self.assertEqual(
            (resolve_schedule(relative, {anchor["id"]: updated}, {}) - first).days, 10
        )
        self.assertEqual(updated["schedule"], fixed)
        with self.assertRaises(store.DomainError) as caught:
            execute_review(
                self.conn,
                self.context,
                "recordMilestone",
                self.deal,
                {
                    "milestone_id": anchor["id"],
                    "kind": "arrival",
                    "schedule": {"kind": "fixed", "due": updated["forecast"]},
                    "date_kind": "forecast",
                    "value": updated["forecast"],
                    "evidence_ids": [],
                },
            )
        self.assertEqual(caught.exception.code, "CONTRACT_SCHEDULE_PRESERVED")

    def test_actual_delivery_does_not_verify_acceptance_payment_anchor(self):
        from services.api.review_handlers import execute_review
        from packages.domain.economics import resolve_schedule

        due = {"instant": "2026-10-10T09:00:00Z", "timezone": "Asia/Jakarta"}
        fixed = {"kind": "fixed", "due": due}

        def record(kind, date_kind, value, identifier=None, evidence_ids=None):
            return execute_review(
                self.conn,
                self.context,
                "recordMilestone",
                self.deal,
                {
                    "milestone_id": identifier,
                    "kind": kind,
                    "schedule": fixed,
                    "date_kind": date_kind,
                    "value": value,
                    "evidence_ids": evidence_ids or [],
                },
            )["result"]

        acceptance = record("acceptance", "forecast", due)
        payment = {
            "kind": "event_relative",
            "anchor_milestone_id": acceptance["id"],
            "offset_days": 30,
            "day_basis": "calendar",
            "business_calendar_id": None,
        }
        arrival = record("arrival", "actual", due, evidence_ids=[self.evidence["id"]])
        milestones = {row["id"]: row for row in [arrival, acceptance]}
        self.assertEqual(arrival["verified_by"], self.context["actor"])
        self.assertIsNone(acceptance["actual"])
        self.assertIsNone(acceptance["verified_by"])
        forecast_due = resolve_schedule(payment, milestones, {})
        self.assertEqual(forecast_due.date().isoformat(), "2026-11-09")

        actual = {"instant": "2026-10-12T09:00:00Z", "timezone": "Asia/Jakarta"}
        with self.assertRaises(store.DomainError) as caught:
            record("acceptance", "actual", actual, acceptance["id"])
        self.assertEqual(caught.exception.code, "EVENT_EVIDENCE")
        unchanged = store.get(
            self.conn, self.context["tenant"], "milestone", acceptance["id"]
        )
        self.assertIsNone(unchanged["actual"])
        acceptance = record(
            "acceptance", "actual", actual, acceptance["id"], [self.evidence["id"]]
        )
        milestones[acceptance["id"]] = acceptance
        self.assertEqual(acceptance["verified_by"], self.context["actor"])
        self.assertEqual(acceptance["forecast"], due)
        self.assertEqual(acceptance["schedule"], fixed)
        self.assertEqual(arrival["actual"], due)
        self.assertEqual(
            resolve_schedule(payment, milestones, {}).date().isoformat(), "2026-11-11"
        )

    def test_fee_deduction_and_buyer_writeoff_are_evidenced_and_cash_is_not_invented(
        self,
    ):
        import test_document_pipeline as fixture
        from services.worker.jobs import process
        from fastapi.testclient import TestClient
        from services.api.app import app
        from packages.domain.economics import compute

        user = (
            self.conn.execute(
                sa.select(store.users).where(
                    store.users.c.id == self.identity["user_id"]
                )
            )
            .mappings()
            .one()
        )
        token = auth.create_session(self.conn, user)["access_token"]
        headers = {"Authorization": "Bearer " + token}
        root = "/v2/deals/" + self.deal["id"]
        with patch.object(store, "engine", fixture.Engine(self.conn)):
            client = TestClient(app)

            def current():
                return client.get(root, headers=headers).json()["result"]["deal"]

            def post(suffix, body):
                return client.post(
                    root + suffix,
                    json={"expected_revision": current()["revision"], **body},
                    headers={**headers, "Idempotency-Key": store.uid("adjustment")},
                )

            job = post(
                "/analyses",
                {"scenario_id": None, "scope": "full", "execution": "deterministic"},
            )
            self.assertEqual(job.status_code, 202, job.text)
            identifier = job.json()["result"]["run"]["id"]
            row = dict(
                self.conn.execute(
                    sa.select(store.jobs).where(store.jobs.c.id == identifier)
                )
                .mappings()
                .one()
            )
            self.conn.execute(
                store.jobs.update()
                .where(store.jobs.c.id == identifier)
                .values(state="running", attempts=1)
            )
            process(row)
            seller = next(
                p["id"] for p in self.deal["parties"] if "seller" in p["roles"]
            )
            buyer = next(
                o
                for o in commands.children(
                    self.conn, self.context["tenant"], "obligation", self.deal
                )
                if o["payee_party_id"] == seller
            )
            amount = str(int(buyer["amount"]["amount"]) - 2000)
            receipt = self.record(buyer, amount)
            receipt_command(
                self.conn,
                self.context,
                "verifyReceipt",
                self.deal,
                {
                    "receipt_id": receipt["id"],
                    "disposition": "verified",
                    "evidence_ids": [self.evidence["id"]],
                    "settled_at": "2026-10-16T12:00:00Z",
                },
            )
            adjustment = {
                "obligation_id": buyer["id"],
                "kind": "fee",
                "amount": {"amount": "2000", "currency": "IDR"},
                "reason": "Agreed bank deduction on this buyer transfer",
                "agreement_evidence_ids": [self.evidence["id"]],
            }
            response = post(
                "/reconcile",
                {
                    "actual_evidence_ids": [self.evidence["id"]],
                    "adjustments": [adjustment],
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            updated = store.get(
                self.conn, self.context["tenant"], "obligation", buyer["id"]
            )
            self.assertEqual(updated["amount"], buyer["amount"])
            self.assertEqual(updated["status"], "settled")
            self.assertEqual(updated["settlement_deductions"], [adjustment])
            fees = [
                c
                for c in commands.children(
                    self.conn, self.context["tenant"], "cost_line", self.deal
                )
                if c["category"] == "bank_fee"
            ]
            self.assertEqual(len(fees), 1)
            self.assertEqual(fees[0]["actual_amount"]["amount"], "2000")
            duplicate = post(
                "/reconcile",
                {
                    "actual_evidence_ids": [self.evidence["id"]],
                    "adjustments": [adjustment],
                },
            )
            self.assertEqual(duplicate.status_code, 409, duplicate.text)
            outstanding = next(
                o
                for o in commands.children(
                    self.conn, self.context["tenant"], "obligation", self.deal
                )
                if o["payee_party_id"] == seller and o["id"] != buyer["id"]
            )
            writeoff = {
                **adjustment,
                "kind": "write_off",
                "obligation_id": outstanding["id"],
                "amount": outstanding["amount"],
                "reason": "Reviewed unrecoverable buyer balance",
            }
            response = post(
                "/reconcile",
                {
                    "actual_evidence_ids": [self.evidence["id"]],
                    "adjustments": [writeoff],
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                current()["states"]["buyer_payment"], "resolved_with_writeoff"
            )
            deal = current()
            result = compute(
                deal,
                commands.children(self.conn, self.context["tenant"], "cost_line", deal),
                commands.children(
                    self.conn, self.context["tenant"], "obligation", deal
                ),
                [],
                [],
                [],
                receipts=commands.children(
                    self.conn, self.context["tenant"], "receipt", deal
                ),
            )
            self.assertEqual(
                result["before_financing"]["contribution"]["amount"], "-68002000.00"
            )
            self.assertFalse(
                any(
                    e["source_ref"] and e["source_ref"]["id"] == outstanding["id"]
                    for e in result["cash_metrics"]["event_balances"]
                )
            )

    def test_reimbursement_claim_is_capped_and_does_not_become_sales_revenue(self):
        from services.api.settlement_adjustments import adjust
        from packages.domain.economics import compute

        tenant = self.context["tenant"]
        buyer = next(
            row
            for row in commands.children(self.conn, tenant, "obligation", self.deal)
            if row["payee_party_id"] == self.deal["parties"][0]["id"]
        )
        cost = deepcopy(commands.children(self.conn, tenant, "cost_line", self.deal)[0])
        cost.update(
            **store.meta(tenant, self.context["actor"], "cost_line"),
            component_key="actual-buyer-advance",
            covered_components=["actual-buyer-advance"],
            treatment="reimbursable_advance",
            actual_amount={"amount": "5000", "currency": "IDR"},
            cash_treatment="paid_before_snapshot",
            payment_term_ids=[],
        )
        store.save(self.conn, tenant, "cost_line", cost, parent=self.deal["id"])

        def contribution():
            return compute(
                self.deal,
                commands.children(self.conn, tenant, "cost_line", self.deal),
                commands.children(self.conn, tenant, "obligation", self.deal),
                [],
                [],
                [],
            )["before_financing"]["contribution"]

        before = contribution()
        adjustment = {
            "obligation_id": buyer["id"],
            "kind": "reimbursement",
            "cost_line_id": cost["id"],
            "amount": {"amount": "3000", "currency": "IDR"},
            "agreement_evidence_ids": [self.evidence["id"]],
            "reason": "Recovery of the actual buyer-borne outlay",
        }
        adjust(
            self.conn,
            self.context,
            self.deal,
            buyer,
            adjustment,
            [self.evidence["id"]],
            0,
        )
        claims = [
            row
            for row in commands.children(self.conn, tenant, "obligation", self.deal)
            if row.get("reimbursement_cost_line_id") == cost["id"]
        ]
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["amount"]["amount"], "3000")
        self.assertEqual(contribution(), before)
        with self.assertRaises(store.DomainError) as error:
            adjust(
                self.conn,
                self.context,
                self.deal,
                buyer,
                adjustment,
                [self.evidence["id"]],
                0,
            )
        self.assertEqual(error.exception.code, "REIMBURSEMENT_DUPLICATE")

    def test_foreign_actual_requires_a_reviewed_executed_fx_reference(self):
        from services.api.review_handlers import execute_review

        tenant = self.context["tenant"]
        cost = commands.children(self.conn, tenant, "cost_line", self.deal)[0]
        body = {
            "cost_line_id": cost["id"],
            "amount": {"amount": "350", "currency": "USD"},
            "evidence_ids": [self.evidence["id"]],
            "reason": "Reviewed actual bank-converted charge",
        }
        with self.assertRaises(store.DomainError) as error:
            execute_review(
                self.conn, self.context, "recordActualCharge", self.deal, body
            )
        self.assertEqual(error.exception.code, "ACTUAL_FX_REQUIRED")
        fx = execute_review(
            self.conn,
            self.context,
            "recordFx",
            self.deal,
            {
                "observation": {
                    "base_currency": "USD",
                    "quote_currency": "IDR",
                    "rate": "15000",
                    "as_of": "2026-10-16T12:00:00Z",
                    "evidence_ids": [self.evidence["id"]],
                    "mode": "user_provided",
                }
            },
        )["result"]
        body["fx_observation_id"] = fx["id"]
        actual = execute_review(
            self.conn, self.context, "recordActualCharge", self.deal, body
        )["result"]
        self.assertEqual(actual["actual_fx_observation_id"], fx["id"])
        self.assertEqual(actual["actual_amount"]["amount"], "350")
        fx["quote_currency"] = "EUR"
        store.save(self.conn, tenant, "fx_observation", fx, parent=self.deal["id"])
        with self.assertRaises(store.DomainError) as error:
            execute_review(
                self.conn, self.context, "recordActualCharge", self.deal, body
            )
        self.assertEqual(error.exception.code, "ACTUAL_FX_PAIR")

    def test_reversing_partial_settlement_does_not_expand_an_approved_writeoff(self):
        from packages.domain.economics import compute

        tenant = self.context["tenant"]
        seller = next(p["id"] for p in self.deal["parties"] if "seller" in p["roles"])
        buyer = next(
            row
            for row in commands.children(self.conn, tenant, "obligation", self.deal)
            if row["payee_party_id"] == seller and row["amount"]["amount"] == "32000000"
        )
        receipt = self.verify(self.record(buyer, "10000000"))
        reviewed = store.get(self.conn, tenant, "obligation", buyer["id"])
        reviewed.update(
            status="written_off",
            write_off_amount={"amount": "22000000", "currency": "IDR"},
            settlement_deductions=[
                {
                    "obligation_id": buyer["id"],
                    "kind": "write_off",
                    "amount": {"amount": "22000000", "currency": "IDR"},
                    "reason": "Reviewed loss of the uncollected balance only",
                    "agreement_evidence_ids": [self.evidence["id"]],
                }
            ],
        )
        store.save(self.conn, tenant, "obligation", reviewed, parent=self.deal["id"])
        receipt_command(
            self.conn,
            self.context,
            "verifyReceipt",
            self.deal,
            {
                "receipt_id": receipt["id"],
                "disposition": "reversed",
                "evidence_ids": [self.evidence["id"]],
                "settled_at": None,
            },
        )
        actual = store.get(self.conn, tenant, "obligation", buyer["id"])
        self.assertEqual(actual["write_off_amount"]["amount"], "22000000")
        self.assertEqual(actual["status"], "partially_settled")
        self.assertNotEqual(self.deal["states"]["buyer_payment"], "paid")
        result = compute(
            self.deal,
            commands.children(self.conn, tenant, "cost_line", self.deal),
            commands.children(self.conn, tenant, "obligation", self.deal),
            [],
            [],
            [],
            receipts=commands.children(self.conn, tenant, "receipt", self.deal),
        )
        forecast = next(
            row
            for row in result["cash_metrics"]["event_balances"]
            if row["source_ref"]["id"] == buyer["id"]
        )
        self.assertEqual(forecast["amount"]["amount"], "10000000.00")
        self.assertEqual(
            result["before_financing"]["contribution"]["amount"], "38000000.00"
        )
