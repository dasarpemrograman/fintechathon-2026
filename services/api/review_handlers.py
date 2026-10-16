"""Explicit review commands; state is derived from persisted evidence and records."""

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import sqlalchemy as sa
from services.api import store, commands
from services.api.store import DomainError, meta, digest, save, get, issue
from packages.domain.economics import number, validate_allocations, compute
from packages.domain.settlement import due_amount, approved_loss, collectible_amount


def execute_review(conn, context, operation, parent, body):
    from services.api.handlers import env, verify_parent

    tenant = context["tenant"]
    actor = context["actor"]
    dataset = parent["dataset_id"]

    def persist(kind, data, identifier=None):
        row = {**meta(tenant, actor, kind, identifier), **data}
        save(conn, tenant, kind, row, parent=parent["id"], dataset=dataset)
        return row

    def evidence(ids, source=None):
        commands.evidence_refs(conn, tenant, parent, ids, source)

    if operation in {"reviewEvidence", "reviewWorkspaceEvidence"}:
        row = verify_parent(conn, context, "evidence", body["evidence_id"], parent)
        row["review_status"] = body["disposition"]
        save(conn, tenant, "evidence", row, parent=parent["id"], dataset=dataset)
        return env(context, row, parent)
    if operation == "verifyCashResources":
        snapshot = parent["constraints"]["cash_snapshot"]
        if (
            snapshot
            and parent["execution_scope"] == "real"
            and datetime.fromisoformat(snapshot["as_of"].replace("Z", "+00:00"))
            > store.now()
        ):
            raise DomainError(
                "FUTURE_CASH_SNAPSHOT",
                "Future scenario cash cannot be verified as an actual opening bank balance.",
            )
        if not snapshot or digest(snapshot) != body["cash_snapshot_hash"]:
            raise DomainError(
                "STALE_CASH_SNAPSHOT", "Cash snapshot changed before review.", 409
            )
        evidence(body["evidence_ids"])
        if any(
            get(conn, tenant, "evidence", identifier)["review_status"] != "confirmed"
            for identifier in body["evidence_ids"]
        ):
            raise DomainError(
                "UNREVIEWED_CASH_EVIDENCE",
                "Cash source evidence requires explicit review.",
            )
        row = persist(
            "approval",
            {
                "purpose": "cash_resources",
                "revision_ref": {"id": parent["id"], "revision": parent["revision"]},
                "analysis_hash": body["cash_snapshot_hash"],
                "artifact_hash": None,
                "evidence_digest": digest(body["evidence_ids"]),
                "actor_id": actor,
                "decision": "approved",
                "evidence_ids": body["evidence_ids"],
            },
        )
        evidence(body["evidence_ids"], row["id"])
        from sqlalchemy.dialects.postgresql import insert

        values = {
            "tenant_id": tenant,
            "currency": snapshot["available"]["currency"],
            "available": number(snapshot["available"]["amount"]),
            "snapshot_hash": digest(snapshot),
        }
        conn.execute(
            insert(store.cash)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["tenant_id", "currency"],
                set_={
                    "available": values["available"],
                    "snapshot_hash": values["snapshot_hash"],
                },
            )
        )
        return env(context, row, parent)
    if operation == "recordMarketObservation":
        value = deepcopy(body["observation"])
        evidence(value["evidence_ids"])
        if value["review_status"] == "confirmed" and any(
            get(conn, tenant, "evidence", i)["review_status"] != "confirmed"
            for i in value["evidence_ids"]
        ):
            raise DomainError(
                "MARKET_SOURCE_UNREVIEWED",
                "Confirm source applicability before accepting a comparator.",
            )
        return env(context, persist("market_observation", value), parent)
    if operation in {"recordFinanceProduct", "recordFundingOption"}:
        kind = (
            "finance_product"
            if operation == "recordFinanceProduct"
            else "funding_option"
        )
        value = deepcopy(
            body["financeProduct" if kind == "finance_product" else "fundingOption"]
        )
        evidence(
            value["source_ids"]
            if kind == "finance_product"
            else value["external_facility_evidence_ids"]
        )
        commands.validate_embedded_evidence(conn, tenant, parent, value)
        if kind == "funding_option":
            from packages.domain.financing import validate_assignments

            validate_assignments(
                parent, value, commands.children(conn, tenant, "obligation", parent)
            )
            value["status"] = "proposed"
            for event in value["schedule"]:
                event["status"] = "proposed"
            if value["product_id"]:
                verify_parent(
                    conn, context, "finance_product", value["product_id"], parent
                )
        return env(context, persist(kind, value), parent)
    if operation == "recordCostLine":
        line = deepcopy(body["line"])
        if line["actual_amount"] is not None:
            raise DomainError(
                "ACTUAL_REVIEW_REQUIRED",
                "Record actuals through the financial review command.",
            )
        commands.validate_allocation_targets(parent, line["allocations"])
        evidence(line["evidence_ids"])
        if not {line["payer_party_id"], line["economic_bearer_party_id"]} <= {
            p["id"] for p in parent["parties"]
        }:
            raise DomainError(
                "COST_PARTY_REFERENCE",
                "Cost payer and economic bearer must be declared deal parties.",
            )
        if line.get("freight_input") and line["freight_input"]["shipment_id"] not in {
            s["id"] for s in parent["shipments"]
        }:
            raise DomainError(
                "FREIGHT_SHIPMENT_REFERENCE",
                "Quoted freight must reference a shipment in this deal.",
            )
        if body["cost_line_id"]:
            verify_parent(conn, context, "cost_line", body["cost_line_id"], parent)
        row = persist("cost_line", line, body["cost_line_id"])
        parent["cost_line_ids"] = list(
            dict.fromkeys(parent["cost_line_ids"] + [row["id"]])
        )
        parent["states"]["analysis"] = "needs_input"
        return env(context, row, parent)
    if operation == "recordActualCharge":
        row = verify_parent(conn, context, "cost_line", body["cost_line_id"], parent)
        evidence(body["evidence_ids"])
        if body["amount"]["currency"] != parent["reporting_currency"]:
            validate_actual_fx(
                conn,
                context,
                parent,
                body.get("fx_observation_id"),
                body["amount"]["currency"],
            )
            row["actual_fx_observation_id"] = body["fx_observation_id"]
        else:
            row.pop("actual_fx_observation_id", None)
        row["actual_amount"] = body["amount"]
        row["evidence_ids"] += body["evidence_ids"]
        row["actual_evidence_ids"] = body["evidence_ids"]
        save(conn, tenant, "cost_line", row, parent=parent["id"], dataset=dataset)
        parent["states"]["analysis"] = "needs_input"
        return env(context, row, parent)
    if operation == "recordFx":
        observation = deepcopy(body["observation"])
        observation["mode"] = (
            "synthetic_demo" if parent["execution_scope"] == "demo" else "user_provided"
        )
        if number(observation["rate"]) <= 0:
            raise DomainError("INVALID_FX", "FX rate must be positive.")
        evidence(observation["evidence_ids"])
        return env(context, persist("fx_observation", observation), parent)
    if operation == "recordObligation":
        value = body["obligation"]
        evidence(value["evidence_ids"])
        commands.validate_allocation_targets(parent, value["allocations"])
        parties = {p["id"] for p in parent["parties"]}
        if not {value["payer_party_id"], value["payee_party_id"]} <= parties:
            raise DomainError("PARTY_REFERENCE", "Obligation parties must be declared.")
        if body["obligation_id"]:
            previous = verify_parent(
                conn, context, "obligation", body["obligation_id"], parent
            )
            if previous["status"] in {
                "partially_settled",
                "settled",
                "written_off",
                "disputed",
            }:
                raise DomainError(
                    "SETTLEMENT_HISTORY_PRESERVED",
                    "Settled or disputed obligations require an explicit adjustment; history cannot be reset.",
                    409,
                )
        return env(
            context,
            persist("obligation", {**value, "status": "open"}, body["obligation_id"]),
            parent,
        )
    if operation == "recordRequirement":
        value = deepcopy(body["requirement"])
        if value["owner_party_id"] not in {p["id"] for p in parent["parties"]}:
            raise DomainError(
                "REQUIREMENT_OWNER", "Requirement owner must be a declared deal party."
            )
        evidence(value["evidence_ids"] + value["fulfillment_evidence_ids"])
        value["reviewer_id"] = (
            actor if value["fulfillment_status"] == "verified" else None
        )
        if (
            value["fulfillment_status"] == "verified"
            and not value["fulfillment_evidence_ids"]
        ):
            raise DomainError(
                "FULFILLMENT_EVIDENCE",
                "Verified requirements need fulfillment evidence.",
            )
        row = persist("requirement", value)
        parent["requirement_ids"].append(row["id"])
        return env(context, row, parent)
    if operation == "reviewRequirement":
        row = verify_parent(
            conn, context, "requirement", body["requirement_id"], parent
        )
        evidence(body["evidence_ids"])
        if (
            body["fulfillment_status"] == "verified"
            or body["applicability"] == "not_applicable"
        ) and not body["evidence_ids"]:
            raise DomainError("REVIEW_EVIDENCE", "Review requires supporting evidence.")
        row.update(
            applicability=body["applicability"],
            fulfillment_status=body["fulfillment_status"],
            reviewer_id=actor,
            fulfillment_evidence_ids=body["evidence_ids"],
        )
        save(conn, tenant, "requirement", row, parent=parent["id"], dataset=dataset)
        return env(context, row, parent)
    if operation == "reviewGoods":
        evidence(body["evidence_ids"])
        if body["shipment_id"] and body["shipment_id"] not in {
            s["id"] for s in parent["shipments"]
        }:
            raise DomainError(
                "SHIPMENT_REFERENCE", "Inspection shipment must belong to the deal."
            )
        if body["status"] == "ready":
            if body.get("inspection_basis") not in {
                "physical_measurements",
                "laboratory_report",
                "documentary_inspection",
            } or not body.get("measurements"):
                raise DomainError(
                    "MEASURED_INSPECTION_REQUIRED",
                    "Photos and unmeasured claims cannot establish conformity.",
                )
            for measurement in body["measurements"]:
                evidence(measurement["evidence_ids"])
                if not measurement["evidence_ids"] or any(
                    get(conn, tenant, "evidence", identifier)["review_status"]
                    != "confirmed"
                    for identifier in measurement["evidence_ids"]
                ):
                    raise DomainError(
                        "INSPECTION_EVIDENCE_REVIEW",
                        "Each measurement needs reviewed supporting evidence.",
                    )
                if measurement["line_item_id"] not in {
                    line["id"] for line in parent["line_items"]
                }:
                    raise DomainError(
                        "INSPECTION_LINE_REFERENCE",
                        "Measurement must reference a declared goods line.",
                    )
            targets = {line["id"]: line["quantity"] for line in parent["line_items"]}
            if body["shipment_id"]:
                shipment = next(
                    s for s in parent["shipments"] if s["id"] == body["shipment_id"]
                )
                targets = {
                    line["line_item_id"]: line["quantity"] for line in shipment["lines"]
                }
            for line in parent["line_items"]:
                if line["id"] not in targets:
                    continue
                measured = next(
                    (
                        m
                        for m in body["measurements"]
                        if m["line_item_id"] == line["id"]
                        and m["attribute"] == "quantity"
                        and m["unit"] == line["unit"]
                    ),
                    None,
                )
                if not measured or number(measured["value"]) < number(
                    targets[line["id"]]
                ):
                    raise DomainError(
                        "INSUFFICIENT_INSPECTED_QUANTITY",
                        "Measured quantity must cover the declared inspection scope.",
                    )
                for attribute in line["product"].get("attributes", []):
                    matches = [
                        m
                        for m in body["measurements"]
                        if m["line_item_id"] == line["id"]
                        and m["attribute"] == attribute["name"]
                        and m["unit"] == attribute["unit"]
                    ]

                    def conforms(m):
                        comparison = attribute.get("comparison", "eq")
                        if comparison == "eq":
                            return m["value"] == attribute["value"]
                        actual = number(m["value"])
                        limit = number(attribute["value"])
                        return (
                            actual <= limit if comparison == "lte" else actual >= limit
                        )

                    if not any(conforms(m) for m in matches):
                        raise DomainError(
                            "SPECIFICATION_UNMEASURED",
                            "Each declared attribute requires matching measured inspection evidence.",
                        )
        if body["reviewed_specification_hash"] != digest(parent["line_items"]):
            raise DomainError(
                "STALE_SPECIFICATION",
                "Goods review does not match current product specifications.",
                409,
            )
        row = persist(
            "goods_review",
            {k: v for k, v in body.items() if k != "expected_revision"}
            | {"deal_id": parent["id"]},
        )
        parent["states"]["goods"] = body["status"]
        parent["states"]["execution_gate"] = "blocked"
        return env(context, row, parent)
    if operation == "recordShipmentEvent":
        evidence(body["evidence_ids"])
        if (
            parent["execution_scope"] == "real"
            and datetime.fromisoformat(body["occurred_at"].replace("Z", "+00:00"))
            > store.now()
        ):
            raise DomainError(
                "FUTURE_SHIPMENT_EVENT",
                "An externally performed event cannot be recorded in the future.",
            )
        if body["shipment_id"] not in {s["id"] for s in parent["shipments"]}:
            raise DomainError(
                "SHIPMENT_REFERENCE", "Shipment is not part of this deal."
            )
        from packages.domain.workflow import readiness

        gate, blockers = readiness(conn, context, parent, "shipment")
        if blockers and not body["exception_reason"]:
            raise DomainError(
                "EXCEPTION_REQUIRED",
                "An externally performed blocked action requires an exception explanation.",
            )
        row = persist(
            "shipment_event",
            {k: v for k, v in body.items() if k != "expected_revision"}
            | {"deal_id": parent["id"], "unmet_conditions": blockers},
        )
        parent["states"]["shipment"] = (
            "exception"
            if blockers
            else "booked"
            if body["kind"] == "booking"
            else body["kind"]
        )
        return env(context, row, parent)
    if operation.startswith("review") and operation.endswith("Fact"):
        row = verify_parent(
            conn, context, "fact_candidate", body["candidate_id"], parent
        )
        row["status"] = (
            "confirmed"
            if body["disposition"] == "confirmed"
            else "conflicted"
            if body["disposition"] == "conflicted"
            else "unreviewed"
        )
        row["reviewer_id"] = actor
        row["value"]["status"] = row["status"]
        row["review_disposition"] = body["disposition"]
        row["review_reason"] = body["reason"]
        save(conn, tenant, "fact_candidate", row, parent=parent["id"], dataset=dataset)
        if body["patch"]:
            if body["disposition"] != "confirmed":
                raise DomainError(
                    "FACT_UNCONFIRMED",
                    "Only confirmed candidates can supply a fact patch.",
                )
            commands.patch_facts(
                conn,
                context,
                parent,
                [body["patch"]],
                "deal" if "workspace_id" in parent else "workspace",
            )
        return env(context, row, parent)
    if operation == "recordApproval" and body["purpose"] == "calendar_write":
        previews = commands.children(conn, tenant, "calendar_preview", parent)
        preview = next(
            (p for p in previews if p["projection_hash"] == body["analysis_hash"]), None
        )
        if not preview:
            raise DomainError(
                "CALENDAR_PREVIEW_REQUIRED",
                "Select a reviewed Calendar projection.",
                409,
            )
        from packages.adapters.calendar import projection

        _, current = projection(
            conn,
            context,
            parent,
            {
                "connection_id": preview["connection_id"],
                "milestone_ids": [e["milestone_id"] for e in preview["events"]],
                "action": preview["events"][0]["action"]
                if preview["events"]
                else "insert",
            },
        )
        if current != preview["projection_hash"]:
            raise DomainError(
                "STALE_CALENDAR_APPROVAL",
                "Preview no longer matches current selected fields.",
                409,
            )
        row = persist(
            "approval",
            {k: v for k, v in body.items() if k != "expected_revision"}
            | {
                "revision_ref": {"id": parent["id"], "revision": parent["revision"]},
                "actor_id": actor,
            },
        )
        return env(context, row, parent)
    if operation == "recordApproval":
        parent["snapshot_hash"] = commands.current_fact_hash(conn, tenant, parent)
        analyses = commands.children(conn, tenant, "analysis", parent)
        analysis = next(
            (
                a
                for a in reversed(analyses)
                if a["snapshot_hash"] == body["analysis_hash"]
            ),
            None,
        )
        if (
            not analysis
            or analysis.get("base_deal_hash") != parent["snapshot_hash"]
            or body["evidence_digest"] != analysis["evidence_digest"]
            or not commands.analysis_view(conn, tenant, parent, analysis)[
                "current_for_use"
            ]
        ):
            raise DomainError(
                "STALE_REVIEW", "Analysis/evidence hashes are not current.", 409
            )
        if body["purpose"] == "draft" and not body["artifact_hash"]:
            raise DomainError(
                "ARTIFACT_REVIEW_REQUIRED",
                "Draft approval must bind a selected artifact hash.",
            )
        if body["artifact_hash"] and not any(
            a["content_hash"] == body["artifact_hash"]
            and a["analysis_id"] == analysis["id"]
            and a["state"] != "superseded"
            for a in commands.children(conn, tenant, "artifact", parent)
        ):
            raise DomainError(
                "STALE_ARTIFACT", "Artifact does not bind the current analysis.", 409
            )
        row = persist(
            "approval",
            {k: v for k, v in body.items() if k != "expected_revision"}
            | {
                "revision_ref": {"id": parent["id"], "revision": parent["revision"]},
                "actor_id": actor,
                "evidence_ids": analysis["input_evidence_ids"],
            },
        )
        if body["purpose"] == "plan":
            parent["states"]["commercial_terms"] = (
                "owner_reviewed" if body["decision"] == "approved" else "proposed"
            )
        return env(context, row, parent)
    if operation == "recordAgreement":
        evidence(body["evidence_ids"])
        if body["party_id"] not in {p["id"] for p in parent["parties"]}:
            raise DomainError(
                "PARTY_REFERENCE", "Counterparty is not declared in this deal."
            )
        if body["accepted_revision"] != parent["revision"]:
            raise DomainError(
                "ACCEPTED_REVISION",
                "New acceptance records must bind the currently reviewed revision.",
                409,
            )
        row = persist(
            "agreement",
            {k: v for k, v in body.items() if k != "expected_revision"}
            | {
                "reviewed_by": actor,
                "accepted_milestone_hash": digest(
                    [
                        {
                            "id": m["id"],
                            "kind": m["kind"],
                            "schedule": m["schedule"],
                            "agreed": m["agreed"],
                        }
                        for m in commands.children(conn, tenant, "milestone", parent)
                    ]
                ),
            },
        )
        parent["states"]["commercial_terms"] = "awaiting_counterparties"
        return env(context, row, parent)
    if operation in {"recordReceipt", "verifyReceipt"}:
        return receipt_command(conn, context, operation, parent, body)
    if operation == "reserveCash":
        ledger = (
            conn.execute(
                sa.select(store.cash)
                .where(
                    store.cash.c.tenant_id == tenant,
                    store.cash.c.currency == body["amount"]["currency"],
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if not ledger or ledger["snapshot_hash"] != body["cash_snapshot_hash"]:
            raise DomainError(
                "CASH_SNAPSHOT_STALE",
                "A current organizational cash snapshot is required.",
                409,
            )
        if body["action"] == "release":
            row = verify_parent(
                conn, context, "reservation", body["reservation_id"], parent
            )
            if row["amount"] != body["amount"]:
                raise DomainError(
                    "RESERVATION_AMOUNT",
                    "Release must identify the recorded reservation amount and currency.",
                )
            row["status"] = "released"
            save(conn, tenant, "reservation", row, parent=parent["id"], dataset=dataset)
        else:
            reserved = sum(
                number(r["amount"]["amount"])
                for r in commands.all_records(conn, tenant, "reservation")
                if r["status"] == "reserved"
                and r["amount"]["currency"] == body["amount"]["currency"]
            )
            if number(body["amount"]["amount"]) + reserved > ledger["available"]:
                raise DomainError(
                    "CASH_ALREADY_COMMITTED",
                    "These organizational funds are already allocated.",
                    409,
                )
            row = persist(
                "reservation",
                {
                    "deal_id": parent["id"],
                    "amount": body["amount"],
                    "status": "reserved",
                    "cash_snapshot_hash": body["cash_snapshot_hash"],
                },
            )
        return env(context, row, parent)
    if operation == "recordMilestone":
        evidence(body["evidence_ids"])
        from zoneinfo import ZoneInfo

        if body["date_kind"] == "actual" and parent["execution_scope"] == "real":
            value = body["value"]
            future = (
                datetime.fromisoformat(value["instant"].replace("Z", "+00:00"))
                > store.now()
                if "instant" in value
                else value["date"]
                > store.now().astimezone(ZoneInfo(value["timezone"])).date().isoformat()
            )
            if future:
                raise DomainError(
                    "FUTURE_ACTUAL_MILESTONE",
                    "Record a forecast for an event that has not happened yet.",
                )
        identifier = body["milestone_id"]
        existing = (
            verify_parent(conn, context, "milestone", identifier, parent)
            if identifier
            else None
        )
        value = existing or {
            **meta(tenant, actor, "milestone"),
            "deal_id": parent["id"],
            "kind": body["kind"],
            "schedule": body["schedule"],
            "proposed": None,
            "agreed": None,
            "forecast": None,
            "actual": None,
            "evidence_ids": [],
            "verified_by": None,
        }
        if body["date_kind"] in {"agreed", "actual"} and not body["evidence_ids"]:
            raise DomainError(
                "EVENT_EVIDENCE", "Agreed and actual events require evidence."
            )
        if (
            existing
            and body["date_kind"] in {"forecast", "actual"}
            and body["schedule"] != existing["schedule"]
        ):
            raise DomainError(
                "CONTRACT_SCHEDULE_PRESERVED",
                "Forecast/actual updates cannot amend the contractual schedule.",
            )
        value.update(schedule=body["schedule"], kind=body["kind"])
        value[body["date_kind"]] = body["value"]
        value["evidence_ids"] += body["evidence_ids"]
        value["verified_by"] = (
            actor if body["date_kind"] == "actual" else value["verified_by"]
        )
        # Validate dependency cycles before persistence.
        from packages.domain.economics import resolve_schedule

        milestones = {
            m["id"]: m for m in commands.children(conn, tenant, "milestone", parent)
        }
        milestones[value["id"]] = value
        from packages.domain.economics import validate_date_graph

        validate_date_graph(milestones)
        if (
            body["schedule"]["kind"] == "event_relative"
            and body["schedule"]["day_basis"] == "business"
        ):
            calendar = get(
                conn,
                tenant,
                "business_calendar",
                body["schedule"]["business_calendar_id"],
                False,
            )
            if calendar is None:
                raise DomainError(
                    "BUSINESS_CALENDAR_MISSING",
                    "Select a known organization business-day calendar.",
                )
        save(conn, tenant, "milestone", value, parent=parent["id"], dataset=dataset)
        parent["states"]["analysis"] = "needs_input"
        return env(context, value, parent)
    if operation in {"reconcileDeal", "closeDeal", "calculateBuyerRisk"}:
        from services.api.reconciliation import reconcile_command

        return reconcile_command(conn, context, operation, parent, body)
    raise DomainError(
        "OPERATION_UNAVAILABLE", "Review command is not yet implemented.", 503
    )


def receipt_command(conn, context, operation, parent, body):
    from services.api.handlers import env, verify_parent

    tenant = context["tenant"]
    actor = context["actor"]
    dataset = parent["dataset_id"]
    if operation == "recordReceipt":
        commands.evidence_refs(conn, tenant, parent, body["evidence_ids"])
        total = number(body["received_amount"]["amount"])
        allocated = Decimal(0)
        seen = set()
        for allocation in body["allocations"]:
            obligation = verify_parent(
                conn, context, "obligation", allocation["obligation_id"], parent
            )
            if allocation["obligation_id"] in seen:
                raise DomainError(
                    "DUPLICATE_ALLOCATION", "Receipt repeats an obligation allocation."
                )
            seen.add(allocation["obligation_id"])
            if (
                allocation["amount"]["currency"] != body["received_amount"]["currency"]
                or obligation["amount"]
                and allocation["amount"]["currency"] != obligation["amount"]["currency"]
            ):
                raise DomainError(
                    "CURRENCY_MISMATCH",
                    "Receipt allocations must use the settled obligation currency.",
                )
            allocated += number(allocation["amount"]["amount"])
        if allocated > total:
            raise DomainError(
                "OVERALLOCATED_RECEIPT", "Allocations exceed received amount."
            )
        for prior in commands.children(conn, tenant, "receipt", parent):
            if (
                prior["evidence_ids"] == body["evidence_ids"]
                and prior["received_amount"] == body["received_amount"]
                and prior["value_date"] == body["value_date"]
            ):
                raise DomainError(
                    "DUPLICATE_RECEIPT",
                    "This settlement evidence is already recorded.",
                    409,
                )
        row = {
            **meta(tenant, actor, "receipt"),
            "received_amount": body["received_amount"],
            "value_date": body["value_date"],
            "allocations": body["allocations"],
            "evidence_ids": body["evidence_ids"],
            "status": "pending",
            "verified_by": None,
            "supersedes": None,
            "settled_at": None,
        }
        save(conn, tenant, "receipt", row, parent=parent["id"], dataset=dataset)
        seller_ids = {
            party["id"] for party in parent["parties"] if "seller" in party["roles"]
        }
        if parent["states"]["buyer_payment"] != "paid" and any(
            get(conn, tenant, "obligation", allocation["obligation_id"])[
                "payee_party_id"
            ]
            in seller_ids
            for allocation in body["allocations"]
        ):
            parent["states"]["buyer_payment"] = "verification_pending"
        return env(context, row, parent)
    if any(
        r.get("supersedes") == body["receipt_id"]
        for r in commands.children(conn, tenant, "receipt", parent)
    ):
        raise DomainError(
            "RECEIPT_SUPERSEDED", "Receipt has already been reviewed or reversed.", 409
        )
    if (
        parent["execution_scope"] == "real"
        and body.get("settled_at")
        and datetime.fromisoformat(body["settled_at"].replace("Z", "+00:00"))
        > store.now()
    ):
        raise DomainError(
            "FUTURE_SETTLEMENT", "An actual settlement instant cannot be in the future."
        )
    previous = verify_parent(conn, context, "receipt", body["receipt_id"], parent)
    commands.evidence_refs(conn, tenant, parent, body["evidence_ids"])
    if previous["status"] not in (
        {"verified"} if body["disposition"] == "reversed" else {"pending"}
    ):
        raise DomainError(
            "RECEIPT_STATE",
            "Receipt verification disposition does not match its current state.",
            409,
        )
    if body["disposition"] == "reversed":
        for allocation in previous["allocations"]:
            liability = verify_parent(
                conn, context, "obligation", allocation["obligation_id"], parent
            )
            if liability["status"] == "written_off" and not liability.get(
                "write_off_amount"
            ):
                raise DomainError(
                    "WRITE_OFF_REVIEW_REQUIRED",
                    "Bind the historical write-off amount with reviewed evidence before reversing its settlement.",
                    409,
                )
    row = deepcopy(previous)
    row.update(
        **meta(tenant, actor, "receipt"),
        status=body["disposition"],
        verified_by=actor,
        evidence_ids=body["evidence_ids"],
        supersedes=previous["id"],
        settled_at=body.get("settled_at"),
    )
    if (
        body["disposition"] == "verified"
        and row["received_amount"]["currency"] != parent["reporting_currency"]
    ):
        validate_actual_fx(
            conn,
            context,
            parent,
            body.get("fx_observation_id"),
            row["received_amount"]["currency"],
        )
        row["fx_observation_id"] = body["fx_observation_id"]
    save(conn, tenant, "receipt", row, parent=parent["id"], dataset=dataset)
    refresh_settlement_states(conn, context, parent, open_proposed=True)
    parent["states"]["internal_closure"] = "reconciling"
    return env(context, row, parent)


def refresh_settlement_states(conn, context, parent, open_proposed=False):
    tenant = context["tenant"]
    dataset = parent["dataset_id"]
    receipts = commands.children(conn, tenant, "receipt", parent)
    superseded = {r["supersedes"] for r in receipts if r["supersedes"]}
    verified = [
        r for r in receipts if r["status"] == "verified" and r["id"] not in superseded
    ]
    sellers = {p["id"] for p in parent["parties"] if "seller" in p["roles"]}
    obligations = commands.children(conn, tenant, "obligation", parent)
    buyer_ids = {row["id"] for row in obligations if row["payee_party_id"] in sellers}
    buyer_paid = bool(buyer_ids)
    written_off = False
    buyer_partial = False
    for obligation in obligations:
        if obligation["status"] == "written_off" and not obligation.get(
            "write_off_amount"
        ):
            if obligation["payee_party_id"] in sellers:
                written_off = True
            continue
        paid = sum(
            (
                number(a["amount"]["amount"])
                for r in verified
                for a in r["allocations"]
                if a["obligation_id"] == obligation["id"]
            ),
            Decimal(0),
        )
        if obligation["amount"] is None:
            status = "open"
        else:
            loss = approved_loss(obligation)
            owed = collectible_amount(obligation)
            if paid > owed:
                raise DomainError(
                    "OVERSETTLED_OBLIGATION",
                    "Verified allocations exceed the obligation.",
                )
            status = (
                "written_off"
                if paid == owed and loss > 0
                else "settled"
                if paid == owed
                else "partially_settled"
                if paid or loss > 0
                else "proposed"
                if not open_proposed and obligation["status"] == "proposed"
                else "open"
            )
        if obligation["status"] != status:
            obligation["status"] = status
            save(
                conn,
                tenant,
                "obligation",
                obligation,
                parent=parent["id"],
                dataset=dataset,
            )
        if obligation["payee_party_id"] in sellers:
            buyer_paid &= status in {"settled", "written_off"}
            written_off |= approved_loss(obligation) > 0
            buyer_partial |= paid > 0
    pending = any(
        row["status"] == "pending"
        and row["id"] not in superseded
        and any(
            allocation["obligation_id"] in buyer_ids
            for allocation in row["allocations"]
        )
        for row in receipts
    )
    parent["states"]["buyer_payment"] = (
        "not_due"
        if not buyer_ids
        else "verification_pending"
        if not buyer_paid and not buyer_partial and pending
        else (
            "resolved_with_writeoff"
            if buyer_paid and written_off
            else "paid"
            if buyer_paid
            else "partially_paid"
            if buyer_partial
            else "due"
        )
    )


def validate_actual_fx(conn, context, parent, identifier, native):
    from services.api.handlers import verify_parent

    if not identifier:
        raise DomainError(
            "ACTUAL_FX_REQUIRED",
            "Record and select a reviewed executed conversion for this foreign-currency actual; a current reference rate is not an executed rate.",
        )
    row = verify_parent(conn, context, "fx_observation", identifier, parent)
    if {row["base_currency"], row["quote_currency"]} != {
        native,
        parent["reporting_currency"],
    }:
        raise DomainError(
            "ACTUAL_FX_PAIR",
            "Executed conversion must match native and reporting currencies.",
        )
    if not row["evidence_ids"] or any(
        get(conn, context["tenant"], "evidence", i)["review_status"] != "confirmed"
        for i in row["evidence_ids"]
    ):
        raise DomainError(
            "ACTUAL_FX_REVIEW",
            "Executed conversion needs confirmed bank/source evidence.",
        )
