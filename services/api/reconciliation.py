"""Evidence-backed settlement, baseline comparison and conditional closure."""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from services.api import commands, store
from services.api.store import DomainError, meta, digest, save, issue
from packages.domain.economics import (
    compute,
    number,
    output,
    convert,
    resolve_schedule,
    cost_amount,
)
from packages.domain.settlement import due_amount, approved_loss, collectible_amount


def current_receipts(rows):
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r["status"] == "verified" and r["id"] not in superseded]


def reconciliation_input_hash(conn, tenant, parent):
    return digest(
        {
            "facts": commands.current_fact_hash(conn, tenant, parent),
            "actuals": commands.children(conn, tenant, "cost_line", parent),
            "receipts": commands.children(conn, tenant, "receipt", parent),
        }
    )


def reconcile_command(conn, context, operation, parent, body):
    from services.api.handlers import env, verify_parent
    from packages.domain.workflow import readiness

    tenant = context["tenant"]
    actor = context["actor"]
    dataset = parent["dataset_id"]
    child = lambda kind: commands.children(conn, tenant, kind, parent)
    if operation == "calculateBuyerRisk":
        scenario = verify_parent(conn, context, "scenario", body["scenario_id"], parent)
        hypothetical = deepcopy(parent)
        commands.patch_facts(conn, context, hypothetical, scenario["patches"], "deal")
        fraction = number(body["receipt_fraction"])
        if fraction > 1:
            raise DomainError(
                "INVALID_RECEIPT_FRACTION", "Receipt fraction cannot exceed one."
            )
        if body["kind"] == "unpaid":
            fraction = Decimal(0)
        elif body["kind"] in {"on_time", "delayed"}:
            fraction = Decimal(1)
        obligations = deepcopy(child("obligation"))
        verified = current_receipts(child("receipt"))
        sellers = {p["id"] for p in parent["parties"] if "seller" in p["roles"]}
        fx = child("fx_observation")
        exposure = Decimal(0)
        warnings = []
        if any(
            o.get("amount") and o["amount"]["currency"] != parent["reporting_currency"]
            for o in obligations
        ):
            warnings.append(
                issue(
                    "CURRENCY_AVAILABILITY_UNVERIFIED",
                    "Reference FX values exposures only; actual spendable balances and executed conversions in each payment currency require separate verification.",
                )
            )
        for obligation in obligations:
            if obligation["payee_party_id"] not in sellers or not obligation["amount"]:
                continue
            if obligation["status"] == "written_off":
                continue
            owed = collectible_amount(obligation)
            paid = sum(
                (
                    number(a["amount"]["amount"])
                    for r in verified
                    for a in r["allocations"]
                    if a["obligation_id"] == obligation["id"]
                ),
                Decimal(0),
            )
            remaining = max(Decimal(0), owed - paid)
            # Only future/unsettled portions are stressed. Persisted receipts are untouched.
            reduced = remaining * fraction
            exposure += convert(
                {
                    "amount": output(remaining - reduced),
                    "currency": obligation["amount"]["currency"],
                },
                parent["reporting_currency"],
                fx,
            )
            deductions = number(obligation["amount"]["amount"]) - collectible_amount(
                obligation
            )
            obligation["amount"]["amount"] = output(paid + reduced + deductions)
            if body["delay_days"] and body["kind"] != "on_time":
                try:
                    at = resolve_schedule(
                        obligation["schedule"],
                        {m["id"]: m for m in child("milestone")},
                        {
                            c["id"]: c
                            for c in commands.all_records(
                                conn, tenant, "business_calendar"
                            )
                        },
                    ) + timedelta(days=body["delay_days"])
                    obligation["schedule"] = {
                        "kind": "fixed",
                        "due": {
                            "instant": at.isoformat(),
                            "timezone": parent["owner_timezone"],
                        },
                    }
                except DomainError as error:
                    warnings.append(issue(error.code, error.reason))
        funding = [
            verify_parent(conn, context, "funding_option", i, parent)
            for i in scenario["funding_option_ids"]
        ]
        result = compute(
            hypothetical,
            child("cost_line"),
            obligations,
            child("milestone"),
            fx,
            commands.all_records(conn, tenant, "business_calendar"),
            funding,
            verified,
        )
        return env(
            context,
            {
                "kind": body["kind"],
                "cash_metrics": result["cash_metrics"],
                "remaining_exposure": {
                    "amount": output(exposure),
                    "currency": parent["reporting_currency"],
                },
                "warnings": warnings
                + result["warnings"]
                + [
                    issue(
                        "STRESS_NOT_PROBABILITY",
                        "This deterministic stress is not a default probability or recoverability prediction.",
                    )
                ],
            },
            parent,
        )
    if operation == "closeDeal":
        reconciliations = child("reconciliation")
        selected = next(
            (
                r
                for r in reversed(reconciliations)
                if r["reconciliation_hash"] == body["reconciliation_hash"]
            ),
            None,
        )
        if not selected:
            raise DomainError(
                "RECONCILIATION_REQUIRED",
                "Select a persisted reconciliation before closure.",
                409,
            )
        gate, blockers = readiness(conn, context, parent, "internal_close")
        if selected["reconciliation_hash"] != reconciliation_input_hash(
            conn, tenant, parent
        ):
            blockers.append(
                issue(
                    "STALE_RECONCILIATION",
                    "Inputs changed after reconciliation; reconcile again.",
                )
            )
        blockers += selected["unresolved_disputes"]
        if blockers:
            gate["status"] = "blocked"
            gate["conditions"].append(
                {
                    "code": "RECONCILIATION_CURRENT",
                    "status": "unresolved",
                    "reason": "Current reconciliation must resolve all disputes and missing baseline reviews.",
                    "required_action": "Reconcile current inputs and review outstanding conditions.",
                    "evidence_refs": [],
                }
            )
            parent["states"]["internal_closure"] = "reconciling"
        else:
            parent["states"]["internal_closure"] = "closed"
        return env(
            context,
            {"deal": deepcopy(parent), "gate": gate},
            parent,
            "blocked" if blockers else "completed",
            blockers,
        )
    commands.evidence_refs(conn, tenant, parent, body["actual_evidence_ids"])
    if len({digest(row) for row in body["adjustments"]}) != len(body["adjustments"]):
        raise DomainError(
            "DUPLICATE_ADJUSTMENT",
            "A reconciliation cannot apply one adjustment twice.",
            409,
        )
    for adjustment in body["adjustments"]:
        obligation = verify_parent(
            conn, context, "obligation", adjustment["obligation_id"], parent
        )
        commands.evidence_refs(
            conn, tenant, parent, adjustment["agreement_evidence_ids"]
        )
        if any(
            store.get(conn, tenant, "evidence", i)["review_status"] != "confirmed"
            for i in adjustment["agreement_evidence_ids"]
        ):
            raise DomainError(
                "ADJUSTMENT_REVIEW_REQUIRED",
                "Settlement and write-off evidence requires explicit confirmation.",
            )
        if (
            not obligation["amount"]
            or obligation["amount"]["currency"] != adjustment["amount"]["currency"]
        ):
            raise DomainError(
                "SETTLEMENT_CURRENCY",
                "Adjustment requires a known matching obligation currency.",
            )
        paid = sum(
            (
                number(a["amount"]["amount"])
                for r in current_receipts(child("receipt"))
                for a in r["allocations"]
                if a["obligation_id"] == obligation["id"]
            ),
            Decimal(0),
        )
        amount = number(adjustment["amount"]["amount"])
        if amount <= 0:
            raise DomainError(
                "ADJUSTMENT_AMOUNT", "An adjustment must be greater than zero."
            )
        prior = [
            a for row in child("reconciliation") for a in row.get("adjustments", [])
        ]
        if any(digest(a) == digest(adjustment) for a in prior):
            raise DomainError(
                "DUPLICATE_ADJUSTMENT",
                "This evidence-backed adjustment is already recorded.",
                409,
            )
        remaining = collectible_amount(obligation) - paid
        if adjustment["kind"] == "write_off":
            if number(adjustment["amount"]["amount"]) != remaining:
                raise DomainError(
                    "WRITE_OFF_BALANCE",
                    "Reviewed write-off must equal the outstanding balance.",
                )
            obligation["status"] = "written_off"
            obligation["write_off_amount"] = {
                "amount": format(
                    approved_loss(obligation) + number(adjustment["amount"]["amount"]),
                    "f",
                ),
                "currency": adjustment["amount"]["currency"],
            }
            obligation.setdefault("settlement_deductions", []).append(
                deepcopy(adjustment)
            )
            obligation["evidence_ids"] = list(
                dict.fromkeys(
                    obligation["evidence_ids"] + adjustment["agreement_evidence_ids"]
                )
            )
            save(
                conn,
                tenant,
                "obligation",
                obligation,
                parent=parent["id"],
                dataset=dataset,
            )
        elif adjustment["kind"] == "settlement":
            from services.api.review_handlers import receipt_command

            if not body["actual_evidence_ids"]:
                raise DomainError(
                    "SETTLEMENT_PROOF_REQUIRED",
                    "Settlement needs actual payment evidence distinct from an agreement.",
                )
            receipt = receipt_command(
                conn,
                context,
                "recordReceipt",
                parent,
                {
                    "received_amount": adjustment["amount"],
                    "value_date": adjustment["value_date"],
                    "allocations": [
                        {
                            "obligation_id": obligation["id"],
                            "amount": adjustment["amount"],
                        }
                    ],
                    "evidence_ids": body["actual_evidence_ids"],
                },
            )["result"]
            receipt_command(
                conn,
                context,
                "verifyReceipt",
                parent,
                {
                    "receipt_id": receipt["id"],
                    "disposition": "verified",
                    "evidence_ids": body["actual_evidence_ids"],
                    "settled_at": adjustment.get("settled_at"),
                    "fx_observation_id": adjustment.get("fx_observation_id"),
                },
            )
        else:
            from services.api.settlement_adjustments import adjust

            adjust(
                conn,
                context,
                parent,
                obligation,
                adjustment,
                body["actual_evidence_ids"],
                remaining,
            )
    from services.api.review_handlers import refresh_settlement_states

    refresh_settlement_states(conn, context, parent)
    analyses = child("analysis")
    if not analyses:
        raise DomainError(
            "BASELINE_REQUIRED",
            "A preserved initial analysis is required before reconciliation.",
            409,
        )
    approved = {
        a["analysis_hash"]
        for a in child("approval")
        if a["purpose"] == "plan" and a["decision"] == "approved"
    }
    approved_analyses = [a for a in analyses if a["snapshot_hash"] in approved]
    initial = analyses[0]
    latest = approved_analyses[-1] if approved_analyses else initial
    disputes = (
        []
        if approved_analyses
        else [issue("BASELINE_UNAPPROVED", "No owner-approved baseline is recorded.")]
    )
    if any(
        row["status"] == "written_off" and not row.get("write_off_amount")
        for row in child("obligation")
    ):
        disputes.append(
            issue(
                "WRITE_OFF_REVIEW_REQUIRED",
                "Review the explicit historical loss amount before final contribution or closure.",
            )
        )
    costs = child("cost_line")
    variances = []
    # Compare with the immutable calculated amounts, never today's mutable
    # estimate. Both baselines remain reproducible even after a quote edit.
    import sqlalchemy as sa

    reporting = parent["reporting_currency"]
    for cost in costs:
        actual_native = cost["actual_amount"]
        actual = None
        if actual_native:
            value = cost_amount(cost, reporting, child("fx_observation"))
            actual = (
                {"amount": output(value), "currency": reporting}
                if value is not None
                else None
            )
            if value is None:
                disputes.append(
                    issue(
                        "ACTUAL_FX_REQUIRED",
                        "Select the reviewed executed conversion for actual charge: "
                        + cost["component_key"],
                    )
                )
        revision = conn.execute(
            sa.select(store.records["cost_line"].c.revision).where(
                store.records["cost_line"].c.tenant_id == tenant,
                store.records["cost_line"].c.id == cost["id"],
            )
        ).scalar_one()
        for baseline_kind, baseline_analysis in [
            ("initial", initial),
            ("latest_approved", latest),
        ]:
            prior = next(
                (
                    row
                    for row in baseline_analysis.get("cost_breakdown", [])
                    if row["cost_line_ref"]["id"] == cost["id"]
                ),
                None,
            )
            baseline = prior["reporting_amount"] if prior else None
            difference = None
            if baseline and actual:
                difference = {
                    "amount": output(
                        number(actual["amount"]) - number(baseline["amount"])
                    ),
                    "currency": reporting,
                }
            variances.append(
                {
                    "baseline_kind": baseline_kind,
                    "baseline_analysis_hash": baseline_analysis["snapshot_hash"],
                    "cost_line_ref": {"id": cost["id"], "revision": revision},
                    "category": "freight"
                    if "freight" in cost["category"]
                    else "new_charge",
                    "baseline": baseline,
                    "actual": actual,
                    "difference": difference,
                    "evidence_ids": cost["evidence_ids"],
                }
            )
        if actual_native is None:
            disputes.append(
                issue(
                    "ACTUAL_CHARGE_MISSING",
                    "Actual charge remains unresolved: " + cost["component_key"],
                )
            )
    selected_scenario = store.get(conn, tenant, "scenario", latest["scenario_id"])
    selected_funding = [
        store.get(conn, tenant, "funding_option", i)
        for i in selected_scenario["funding_option_ids"]
    ]
    verified_funding = [
        option
        for option in selected_funding
        if option["schedule"]
        and all(event["status"] == "actual_verified" for event in option["schedule"])
    ]
    if len(verified_funding) != len(selected_funding):
        disputes.append(
            issue(
                "FINANCING_ACTUALS_UNVERIFIED",
                "Proposed facility costs and cash are not verified financing actuals.",
            )
        )
    dimension_rows = []
    from packages.domain.variance import dimensions

    for baseline_kind, baseline_analysis in [
        ("initial", initial),
        ("latest_approved", latest),
    ]:
        refs = [
            ref
            for row in baseline_analysis.get("numeric_lineage", [])
            for ref in row["input_refs"]
        ]
        parent_ref = next((ref for ref in refs if ref["id"] == parent["id"]), None)
        original = (
            conn.execute(
                sa.select(store.snapshots.c.data).where(
                    store.snapshots.c.tenant_id == tenant,
                    store.snapshots.c.resource_id == parent["id"],
                    store.snapshots.c.revision == parent_ref["revision"],
                )
            ).scalar_one_or_none()
            if parent_ref
            else None
        )
        fx_pairs = []
        for observation in child("fx_observation"):
            ref = next((ref for ref in refs if ref["id"] == observation["id"]), None)
            historic = (
                conn.execute(
                    sa.select(store.snapshots.c.data).where(
                        store.snapshots.c.tenant_id == tenant,
                        store.snapshots.c.resource_id == observation["id"],
                        store.snapshots.c.revision == ref["revision"],
                    )
                ).scalar_one_or_none()
                if ref
                else None
            )
            fx_pairs.append(
                (
                    observation["id"],
                    historic["rate"] if historic else None,
                    observation["rate"],
                    observation["quote_currency"] + "/" + observation["base_currency"],
                    observation["evidence_ids"],
                )
            )
        rows = dimensions(
            original,
            parent,
            child("goods_review"),
            child("obligation"),
            child("receipt"),
            fx_pairs,
            None,
        )
        baseline_fee = baseline_analysis["after_financing"]["funding_cost"]
        actual_fee = (
            sum(
                (
                    convert(event["amount"], reporting, child("fx_observation"))
                    for option in verified_funding
                    for event in option["schedule"]
                    if event["kind"] in {"finance_cost", "withheld_fee", "interest"}
                ),
                Decimal(0),
            )
            if len(verified_funding) == len(selected_funding)
            else None
        )
        before = baseline_fee["amount"] if baseline_fee else None
        after = output(actual_fee) if actual_fee is not None else None
        rows.append(
            {
                "category": "financing",
                "resource_ref": {"id": parent["id"]},
                "baseline_value": before,
                "actual_value": after,
                "difference": output(number(after) - number(before))
                if before is not None and after is not None
                else None,
                "unit": reporting,
                "basis": "Verified financing fees and interest; proposed facilities remain unknown actuals.",
                "evidence_ids": [
                    i
                    for option in verified_funding
                    for event in option["schedule"]
                    for i in event["evidence_ids"]
                ],
            }
        )
        dimension_rows.extend(
            [
                {
                    **row,
                    "baseline_kind": baseline_kind,
                    "baseline_analysis_hash": baseline_analysis["snapshot_hash"],
                }
                for row in rows
            ]
        )
    result = compute(
        parent,
        costs,
        child("obligation"),
        child("milestone"),
        child("fx_observation"),
        commands.all_records(conn, tenant, "business_calendar"),
        verified_funding,
        child("receipt"),
    )
    gate, blockers = readiness(conn, context, parent, "internal_close")
    row = {
        **meta(tenant, actor, "reconciliation"),
        "initial_baseline_hash": initial["snapshot_hash"],
        "latest_approved_baseline_hash": latest["snapshot_hash"],
        "reconciliation_hash": reconciliation_input_hash(conn, tenant, parent),
        "variances": variances,
        "dimensions": dimension_rows,
        "unresolved_obligation_ids": [
            o["id"]
            for o in child("obligation")
            if o["status"] not in {"settled", "written_off"}
        ],
        "unresolved_disputes": disputes,
        "actual_contribution": result["after_financing"]["contribution"]
        if not disputes
        else None,
        "closure_gate": gate,
        "adjustments": body["adjustments"],
    }
    save(conn, tenant, "reconciliation", row, parent=parent["id"], dataset=dataset)
    parent["states"]["internal_closure"] = "reconciling"
    return env(context, row, parent)
