"""Server-derived stage gates over current commercial terms and reviewed evidence."""

from datetime import date, datetime
from decimal import Decimal
import sqlalchemy as sa
from services.api import commands, store
from services.api.store import digest, issue, instant
from packages.domain.economics import number, resolve_schedule


def commercial_hash(deal):
    return digest(
        {
            k: deal.get(k)
            for k in [
                "business_profile",
                "seller_domicile",
                "line_items",
                "shipments",
                "parties",
                "payment_terms",
                "procurement",
                "invoices",
            ]
        }
    )


def readiness(conn, context, deal, stage):
    tenant = context["tenant"]
    conditions = []
    children = lambda kind: commands.children(conn, tenant, kind, deal)
    if deal["execution_scope"] == "demo":
        from packages.domain.demo import MANIFEST

        today = date.fromisoformat(MANIFEST["reference_date"])
    else:
        today = store.now().date()

    def condition(code, ok, reason, evidence=None):
        conditions.append(
            {
                "code": code,
                "status": "satisfied" if ok else "unresolved",
                "reason": reason,
                "required_action": None
                if ok
                else "Review current facts and supporting evidence.",
                "evidence_refs": [{"id": i} for i in (evidence or [])],
            }
        )

    from services.api.settings import settings

    condition(
        "DEAL_ACTIVE",
        not deal.get("archived", False),
        "Archived histories cannot authorize new execution.",
    )
    condition(
        "EXECUTION_SCOPE_ENABLED",
        deal["execution_scope"] != "demo" or settings.demo,
        "Demo gates require explicit demo mode; synthetic histories never authorize real execution.",
    )
    analyses = children("analysis")
    valid = [
        a
        for a in analyses
        if commands.analysis_view(conn, tenant, deal, a)["current_for_use"]
    ]
    analysis = valid[-1] if valid else None
    condition(
        "CURRENT_ANALYSIS", analysis is not None, "Current-input analysis is required."
    )
    if analysis:
        condition(
            "COMPLETE_INPUTS",
            analysis["completeness"] != "partial",
            "Known-items-only calculations do not establish full readiness.",
        )
    evidence = {e["id"]: e for e in children("evidence")}

    def reviewed(ids):
        return bool(ids) and all(
            i in evidence
            and evidence[i]["review_status"] == "confirmed"
            and (
                not evidence[i].get("effective_from")
                or date.fromisoformat(evidence[i]["effective_from"]) <= today
            )
            and (
                not evidence[i]["valid_until"]
                or date.fromisoformat(evidence[i]["valid_until"]) >= today
            )
            and not (
                deal["execution_scope"] == "real"
                and evidence[i]["mode"] == "synthetic_demo"
            )
            for i in ids
        )

    if stage not in {"analysis", "plan_review"}:
        if analysis:
            condition(
                "CURRENT_REVIEWED_EVIDENCE",
                reviewed(analysis["input_evidence_ids"]),
                "Analysis sources must remain explicitly reviewed, applicable and unexpired.",
            )
        approvals = children("approval")
        condition(
            "CURRENT_PLAN_REVIEW",
            any(
                a["purpose"] == "plan"
                and a["decision"] == "approved"
                and a["analysis_hash"]
                == (analysis["snapshot_hash"] if analysis else None)
                for a in approvals
            ),
            "Current scoped owner plan review is required.",
        )
        accepted = set()
        milestone_hash = digest(
            [
                {
                    "id": m["id"],
                    "kind": m["kind"],
                    "schedule": m["schedule"],
                    "agreed": m["agreed"],
                }
                for m in children("milestone")
            ]
        )
        for agreement in children("agreement"):
            historic = conn.execute(
                sa.select(store.snapshots.c.data).where(
                    store.snapshots.c.tenant_id == tenant,
                    store.snapshots.c.resource_id == deal["id"],
                    store.snapshots.c.revision == agreement["accepted_revision"],
                )
            ).scalar_one_or_none()
            if (
                historic
                and commercial_hash(historic) == commercial_hash(deal)
                and agreement.get("accepted_milestone_hash") == milestone_hash
                and reviewed(agreement["evidence_ids"])
            ):
                accepted.add(agreement["party_id"])
        counterparties = {
            p["id"]
            for p in deal["parties"]
            if set(p["roles"]) & {"buyer", "supplier", "production_input"}
        }
        condition(
            "COUNTERPARTY_AGREEMENTS",
            bool(counterparties) and counterparties <= accepted,
            "Acceptance evidence must cover the current commercial terms for every relevant counterparty.",
        )
        if analysis:
            condition(
                "LIQUIDITY",
                analysis["cash_metrics"] is not None
                and number(analysis["cash_metrics"]["buffer_shortfall"]) == 0,
                "Declared cash buffer must be met across the full scenario horizon.",
            )
            scenario = store.get(conn, tenant, "scenario", analysis["scenario_id"])
            condition(
                "SCENARIO_TERMS_APPLIED",
                all(deal.get(p["path"][1:]) == p["value"] for p in scenario["patches"]),
                "Hypothetical negotiated terms must be applied and accepted before they authorize execution.",
            )
            options = [
                store.get(conn, tenant, "funding_option", i)
                for i in scenario["funding_option_ids"]
            ]
            condition(
                "FUNDING_AVAILABILITY",
                all(
                    event["status"] == "actual_verified"
                    and reviewed(event["evidence_ids"])
                    for option in options
                    for event in option["schedule"]
                    if event["kind"] == "loan_draw"
                ),
                "Proposed loans and confirmed schedules do not establish actual draw availability.",
            )
        snapshot = deal["constraints"]["cash_snapshot"]
        cash_review = bool(snapshot) and any(
            a["purpose"] == "cash_resources"
            and a["analysis_hash"] == digest(snapshot)
            and a["decision"] == "approved"
            and reviewed(a.get("evidence_ids", []))
            for a in approvals
        )
        condition(
            "VERIFIED_OPENING_RESOURCES",
            cash_review,
            "Opening cash needs its own current bank/source review.",
        )
        if snapshot and analysis and analysis["cash_metrics"]:
            reserved = sum(
                (
                    number(r["amount"]["amount"])
                    for r in commands.all_records(conn, tenant, "reservation")
                    if r["deal_id"] != deal["id"]
                    and r["status"] == "reserved"
                    and r["amount"]["currency"] == deal["reporting_currency"]
                ),
                Decimal(0),
            )
            same_currency = (
                snapshot["available"]["currency"]
                == snapshot["committed_elsewhere"]["currency"]
                == deal["reporting_currency"]
            )
            sufficient = same_currency and number(
                snapshot["available"]["amount"]
            ) - number(snapshot["committed_elsewhere"]["amount"]) - reserved >= number(
                analysis["cash_metrics"]["required_own_funds"]
            )
            condition(
                "UNCOMMITTED_OWN_FUNDS",
                sufficient,
                "Uncommitted cash in the required currency must cover scenario own-fund requirements; reference FX is not executed currency availability.",
            )
        receipts = children("receipt")
        superseded = {r["supersedes"] for r in receipts if r.get("supersedes")}
        verified = [
            r
            for r in receipts
            if r["status"] == "verified"
            and r["id"] not in superseded
            and reviewed(r["evidence_ids"])
        ]
        obligations = children("obligation")
        from packages.domain.cash_availability import native_resources_supported

        condition(
            "NATIVE_PAYMENT_RESOURCES",
            native_resources_supported(deal, obligations, verified),
            "Reference FX values do not establish spendable foreign-currency balances. Unsettled seller payments require verified resources in their payment currency.",
        )
        seller = {p["id"] for p in deal["parties"] if "seller" in p["roles"]}
        terms = {t["id"]: t for t in deal["payment_terms"]}
        milestones = {m["id"]: m for m in children("milestone")}
        calendars = {
            c["id"]: c for c in commands.all_records(conn, tenant, "business_calendar")
        }
        resources_ok = True
        for obligation in obligations:
            term = terms.get(obligation["id"])
            if not term or term["side"] != "buyer" or term["instrument"] != "advance":
                continue
            if not obligation["amount"]:
                resources_ok = False
                continue
            try:
                due = resolve_schedule(obligation["schedule"], milestones, calendars)
            except store.DomainError:
                resources_ok = False
                continue
            paid = Decimal(0)
            for receipt in verified:
                if (
                    not receipt.get("settled_at")
                    or datetime.fromisoformat(
                        receipt["settled_at"].replace("Z", "+00:00")
                    )
                    > due
                ):
                    continue
                paid += sum(
                    (
                        number(a["amount"]["amount"])
                        for a in receipt["allocations"]
                        if a["obligation_id"] == obligation["id"]
                        and a["amount"]["currency"] == obligation["amount"]["currency"]
                    ),
                    Decimal(0),
                )
            from packages.domain.settlement import due_amount

            resources_ok &= paid >= due_amount(obligation)
        condition(
            "REQUIRED_BUYER_ADVANCES",
            resources_ok,
            "Required buyer advances must be verified in sufficient amount by their agreed scenario date.",
        )
        requirements = children("requirement")
        condition(
            "REQUIREMENTS_REVIEWED",
            bool(requirements)
            and all(
                (
                    r["applicability"] == "not_applicable"
                    and reviewed(r["fulfillment_evidence_ids"])
                )
                or r["applicability"] == "applies"
                and r["fulfillment_status"] == "verified"
                and reviewed(r["fulfillment_evidence_ids"])
                and (
                    not r["review_due"] or date.fromisoformat(r["review_due"]) >= today
                )
                for r in requirements
            ),
            "Applicable rules, fulfillment and review dates must be established; no configured rule is not proof that none applies.",
        )
        if deal["business_profile"] == "producer":
            plan = deal["procurement"]
            condition(
                "PRODUCTION_CAPACITY_YIELD",
                plan["usable_yield"] is not None
                and plan["batch_quantity"] is not None
                and plan["capacity_quantity"] is not None
                and number(plan["capacity_quantity"]) >= number(plan["batch_quantity"]),
                "Production capacity and usable yield must be established for this batch.",
            )
            compatible = all(
                line["unit"] == plan["unit"] for line in deal["line_items"]
            )
            usable = (
                number(plan["batch_quantity"]) * number(plan["usable_yield"])
                if plan["batch_quantity"] is not None
                and plan["usable_yield"] is not None
                else None
            )
            condition(
                "PRODUCTION_USABLE_OUTPUT",
                compatible
                and usable is not None
                and usable
                >= sum(
                    (number(line["quantity"]) for line in deal["line_items"]),
                    Decimal(0),
                ),
                "Usable batch output must cover the declared finished goods in comparable units.",
            )
    if stage not in {"analysis", "plan_review"}:
        from packages.domain.cost_coverage import covered

        condition(
            "CASH_COST_OBLIGATIONS_COVERED",
            covered(
                deal,
                children("cost_line"),
                children("obligation"),
                children("fx_observation"),
            ),
            "Every seller-paid current charge needs sufficient native-currency obligations; a liability cannot fund several costs twice.",
        )
    if stage in {"shipment", "internal_close"}:
        reviews = [
            r
            for r in children("goods_review")
            if r["reviewed_specification_hash"] == digest(deal["line_items"])
        ]
        scopes = [s["id"] for s in deal["shipments"]] or [None]
        conformity = bool(reviews)
        for scope in scopes:
            applicable = [r for r in reviews if r["shipment_id"] in {None, scope}]
            conformity &= (
                bool(applicable)
                and applicable[-1]["status"] == "ready"
                and reviewed(applicable[-1]["evidence_ids"])
            )
        condition(
            "GOODS_CONFORMITY",
            conformity,
            "Measured conformity must cover every declared shipment and the current agreed specification.",
        )
    if stage == "internal_close":
        delivered = {
            e["shipment_id"]
            for e in children("shipment_event")
            if e["kind"] == "delivered" and reviewed(e["evidence_ids"])
        }
        condition(
            "DELIVERY_RECORDED",
            bool(deal["shipments"])
            and {s["id"] for s in deal["shipments"]} <= delivered,
            "Every declared shipment needs evidence of completed delivery before operational closure.",
        )
        obligations = children("obligation")
        from packages.domain.settlement import collectible_amount

        def resolved_balance(row):
            if row["amount"] is None:
                return False
            paid = sum(
                (
                    number(allocation["amount"]["amount"])
                    for receipt in verified
                    for allocation in receipt["allocations"]
                    if allocation["obligation_id"] == row["id"]
                ),
                Decimal(0),
            )
            return (
                row["status"] in {"settled", "written_off"}
                and collectible_amount(row) <= paid
            )

        condition(
            "WRITE_OFF_REVIEWED",
            all(
                row.get("write_off_amount") is not None
                for row in obligations
                if row["status"] == "written_off"
            ),
            "Historical write-offs need a reviewed explicit amount; receipt corrections cannot expand an approved loss.",
        )
        condition(
            "OBLIGATIONS_RESOLVED",
            bool(obligations) and all(resolved_balance(o) for o in obligations),
            "Seller liabilities, buyer balances and reimbursements must be resolved.",
        )
        costs = children("cost_line")
        condition(
            "ACTUALS_FINALIZED",
            bool(costs)
            and all(
                c["actual_amount"] is not None
                and reviewed(c.get("actual_evidence_ids", c["evidence_ids"]))
                for c in costs
            ),
            "Actual charges must replace estimates or carry reviewed settlements.",
        )
    source_map = {
        "CURRENT_ANALYSIS": analysis["input_evidence_ids"] if analysis else [],
        "CURRENT_REVIEWED_EVIDENCE": analysis["input_evidence_ids"] if analysis else [],
        "CURRENT_PLAN_REVIEW": [
            identifier
            for row in children("approval")
            if row["purpose"] == "plan"
            for identifier in row.get("evidence_ids", [])
        ],
        "COUNTERPARTY_AGREEMENTS": [
            identifier
            for row in children("agreement")
            for identifier in row["evidence_ids"]
        ],
        "VERIFIED_OPENING_RESOURCES": [
            identifier
            for row in children("approval")
            if row["purpose"] == "cash_resources"
            for identifier in row.get("evidence_ids", [])
        ],
        "REQUIRED_BUYER_ADVANCES": [
            identifier
            for row in children("receipt")
            if row["status"] == "verified"
            for identifier in row["evidence_ids"]
        ],
        "REQUIREMENTS_REVIEWED": [
            identifier
            for row in children("requirement")
            for identifier in row["evidence_ids"] + row["fulfillment_evidence_ids"]
        ],
        "GOODS_CONFORMITY": [
            identifier
            for row in children("goods_review")
            for identifier in row["evidence_ids"]
        ],
        "DELIVERY_RECORDED": [
            identifier
            for row in children("shipment_event")
            for identifier in row["evidence_ids"]
        ],
        "ACTUALS_FINALIZED": [
            identifier
            for row in children("cost_line")
            for identifier in row.get("actual_evidence_ids", row["evidence_ids"])
        ],
    }
    for entry in conditions:
        entry["evidence_refs"] = [
            {"id": identifier}
            for identifier in sorted(set(source_map.get(entry["code"], [])))
        ]
    blockers = [
        issue(c["code"], c["reason"], action=c["required_action"])
        for c in conditions
        if c["status"] != "satisfied"
    ]
    gate = {
        "gate_id": "gate_"
        + digest({"deal": deal["id"], "revision": deal["revision"], "stage": stage})[
            :24
        ],
        "stage": stage,
        "evaluated_revision": deal["revision"],
        "status": "blocked" if blockers else "ready_for_next_action",
        "conditions": conditions,
        "evidence_refs": [
            {"id": identifier}
            for identifier in sorted(
                {ref["id"] for entry in conditions for ref in entry["evidence_refs"]}
            )
        ],
        "evaluated_at": instant(),
    }
    return gate, blockers
