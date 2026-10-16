"""Reviewed product screening and preparation; never a lender decision."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
from packages.domain.economics import number, resolve_schedule
from services.api.store import issue, DomainError


def reviewed(ids, evidence, today):
    return bool(ids) and all(
        identifier in evidence
        and evidence[identifier]["review_status"] == "confirmed"
        and (
            not evidence[identifier].get("effective_from")
            or date.fromisoformat(evidence[identifier]["effective_from"]) <= today
        )
        and (
            not evidence[identifier].get("valid_until")
            or date.fromisoformat(evidence[identifier]["valid_until"]) >= today
        )
        for identifier in ids
    )


def screen(product, parent, request, evidence, today):
    failed = []
    unknown = []
    company = request["company"]
    requested = request.get("requested_amount")
    if not reviewed(product["source_ids"], evidence, today):
        unknown.append("Current product terms need reviewed source evidence.")
    if product["valid_until"] and date.fromisoformat(product["valid_until"]) < today:
        failed.append("Product terms have expired.")
    if product["jurisdiction"] != parent["seller_domicile"]:
        failed.append("Exporter jurisdiction differs from product eligibility.")
    stage = request.get("funding_stage")
    if stage is None:
        unknown.append("Required financing stage is unknown.")
    elif product["stage"] != "working_capital" and product["stage"] != stage:
        failed.append("Product stage cannot fund the required stage.")
    entity = company.get("entity_type")
    eligible = product.get("eligible_entity_types")
    if not entity or not eligible:
        unknown.append("Legal entity eligibility needs confirmation.")
    elif entity.casefold() not in {value.casefold() for value in eligible}:
        failed.append("Legal entity is not eligible.")
    terms = [
        term
        for term in parent["payment_terms"]
        if term["side"] == "buyer"
        and (
            request.get("invoice_id") is None
            or term["invoice_id"] == request["invoice_id"]
        )
    ]
    terms = [term for term in terms if term["instrument"] != "advance"] or terms
    instruments = product.get("eligible_instruments")
    if not instruments or not terms:
        unknown.append("Eligible payment instrument is unconfirmed.")
    elif any(term["instrument"] not in instruments for term in terms):
        failed.append("LC/open-account or other payment instrument is incompatible.")
    if not requested or not product["currency"]:
        unknown.append("Requested amount or product currency is missing.")
    elif requested["currency"] != product["currency"]:
        failed.append("Requested native currency is unsupported.")
    else:
        for field, comparison, reason in [
            (
                "minimum_amount",
                lambda value, limit: value < limit,
                "Requested amount is below the minimum.",
            ),
            (
                "maximum_amount",
                lambda value, limit: value > limit,
                "Requested amount exceeds the maximum.",
            ),
        ]:
            limit = product[field]
            if limit and (
                limit["currency"] != requested["currency"]
                or comparison(number(requested["amount"]), number(limit["amount"]))
            ):
                failed.append(reason)
    tenor = request.get("requested_tenor_days")
    if tenor is None:
        unknown.append("Requested tenor is missing.")
    else:
        if (
            product.get("minimum_tenor_days") is None
            and product.get("maximum_tenor_days") is None
        ):
            unknown.append("Product tenor limits need confirmation.")
        if (
            product.get("minimum_tenor_days") is not None
            and tenor < product["minimum_tenor_days"]
        ):
            failed.append("Tenor is below the product minimum.")
        if (
            product.get("maximum_tenor_days") is not None
            and tenor > product["maximum_tenor_days"]
        ):
            failed.append("Tenor exceeds product maturity limits.")
    if product["rate"] is None or product["rate_basis"] not in {
        "annual_simple",
        "monthly_simple",
        "flat_total",
    }:
        unknown.append("Rate or executable rate basis is missing/unsupported.")
    if product["recourse"] == "unknown":
        unknown.append(
            "Recourse obligations require confirmation from the provider terms."
        )
    for fee in product["fees"]:
        if fee["amount"] is None and (fee["rate"] is None or fee["basis"] != "draw"):
            unknown.append("A financing fee cannot yet be calculated.")
    for predicate in product["eligibility_predicates"]:
        if predicate["status"] == "failed":
            failed.append(predicate["name"] + ": " + predicate["reason"])
        elif predicate["status"] != "satisfied" or not reviewed(
            predicate["evidence_ids"], evidence, today
        ):
            unknown.append(
                predicate["name"] + ": reviewed eligibility evidence is missing."
            )
    if not reviewed(company["registration_evidence_ids"], evidence, today):
        unknown.append("Reviewed business registration is missing.")
    if not reviewed(company["financial_evidence_ids"], evidence, today):
        unknown.append("Reviewed financial statements are missing.")
    security = {
        item["name"].casefold(): item for item in company.get("security_predicates", [])
    }
    for requirement in product["security_requirements"]:
        predicate = security.get(requirement.casefold())
        if predicate and predicate["status"] == "failed":
            failed.append("Security requirement failed: " + requirement)
        elif (
            not predicate
            or predicate["status"] != "satisfied"
            or not reviewed(predicate["evidence_ids"], evidence, today)
        ):
            unknown.append("Security requirement needs evidence: " + requirement)
    for document in product["document_requirements"]:
        if document["basis"] == "provider_required" and (
            document["status"] != "present"
            or not reviewed(document["evidence_ids"], evidence, today)
        ):
            unknown.append("Provider-required document: " + document["name"])
    if product["indicative_lead_days"] is None:
        unknown.append("Lead time and draw conditions require confirmation.")
    if request.get("required_by") is None:
        unknown.append("Required draw date is not specified.")
    elif product["indicative_lead_days"] is not None:
        required = request["required_by"]
        deadline = (
            date.fromisoformat(required["date"])
            if "date" in required
            else datetime.fromisoformat(
                required["instant"].replace("Z", "+00:00")
            ).date()
        )
        if deadline < today + timedelta(days=product["indicative_lead_days"]):
            failed.append("Indicative lead time misses the required draw date.")
    return {
        "fit": "incompatible"
        if failed
        else "needs_information"
        if unknown
        else "potentially_suitable",
        "fit_reasons": failed + unknown
        or [
            "Reviewed declared criteria match; lender approval and actual disbursement are separate."
        ],
        "failed_predicates": failed,
        "unknown_predicates": unknown,
    }


def preparation(
    parent,
    option,
    product,
    selected_evidence,
    evidence,
    obligations,
    milestones,
    calendars,
    today,
):
    selected = set(selected_evidence)
    documents = deepcopy(product["document_requirements"])
    gaps = []
    for document in documents:
        if document["status"] == "present" and (
            not set(document["evidence_ids"]) <= selected
            or not reviewed(document["evidence_ids"], evidence, today)
        ):
            document["status"] = "needs_review"
        if document["basis"] == "provider_required" and document["status"] != "present":
            gaps.append(
                issue(
                    "PROVIDER_DOCUMENT_MISSING",
                    "Review provider-required document: " + document["name"],
                )
            )
    if not documents:
        gaps.append(
            issue(
                "PROVIDER_CHECKLIST_UNKNOWN",
                "Confirm the provider-required checklist rather than assuming no documents are needed.",
            )
        )
    if option["fit"] != "potentially_suitable":
        gaps.append(
            issue(
                "FINANCE_FIT_UNRESOLVED",
                "Resolve failed or unknown fit predicates before application-ready preparation.",
            )
        )
    if not reviewed(product["source_ids"], evidence, today) or (
        product["valid_until"] and date.fromisoformat(product["valid_until"]) < today
    ):
        gaps.append(
            issue("FINANCE_TERMS_REVIEW", "Review current provider terms and pricing.")
        )
    if any(
        fee["unknowns"]
        or fee["amount"] is None
        and (fee["rate"] is None or fee["basis"] != "draw")
        for fee in product["fees"]
    ):
        gaps.append(
            issue("FINANCE_FEE_MISSING", "Review all financing fees and their bases.")
        )
    if product["rate"] is None or product["rate_basis"] is None:
        gaps.append(
            issue(
                "FINANCE_RATE_MISSING",
                "No rate is inferred for application preparation.",
            )
        )
    if product["recourse"] == "unknown":
        gaps.append(
            issue(
                "FINANCE_RECOURSE_UNKNOWN",
                "Confirm recourse and settlement obligations before application-ready preparation.",
            )
        )
    if option["draw"] is None:
        gaps.append(
            issue(
                "REQUESTED_AMOUNT_MISSING", "Confirm the requested amount and currency."
            )
        )
    draws = [event for event in option["schedule"] if event["kind"] == "loan_draw"]
    repayments = [
        event for event in option["schedule"] if event["kind"] == "principal_repayment"
    ]
    settlement_dates = []
    for assignment in option.get("receivable_assignments", []):
        obligation = next(
            (row for row in obligations if row["id"] == assignment["obligation_id"]),
            None,
        )
        if obligation:
            try:
                settlement_dates.append(
                    resolve_schedule(obligation["schedule"], milestones, calendars)
                )
            except DomainError:
                pass
    tenor = None
    try:
        if draws and (repayments or settlement_dates):
            tenor = max(
                0,
                (
                    max(
                        [
                            resolve_schedule(event["schedule"], milestones, calendars)
                            for event in repayments
                        ]
                        + settlement_dates
                    )
                    - min(
                        resolve_schedule(event["schedule"], milestones, calendars)
                        for event in draws
                    )
                ).days,
            )
    except DomainError:
        tenor = None
    if not any(
        event["kind"] in {"finance_cost", "withheld_fee", "interest"}
        for event in option["schedule"]
    ):
        gaps.append(
            issue(
                "FINANCING_COST_SCHEDULE_MISSING",
                "Record explicit financing costs, including a sourced zero if the facility is genuinely free.",
            )
        )
    if tenor is None:
        gaps.append(
            issue(
                "FINANCING_SCHEDULE_MISSING",
                "Confirm draw, maturity and repayment schedules.",
            )
        )
    sellers = {party["id"] for party in parent["parties"] if "seller" in party["roles"]}
    uses = [
        {
            "obligation_ref": {"id": row["id"]},
            "amount": row["amount"],
            "schedule": row["schedule"],
        }
        for row in obligations
        if row["payer_party_id"] in sellers
        and row["amount"] is not None
        and row["status"] not in {"settled", "written_off"}
    ]
    if any(
        row["payer_party_id"] in sellers and row["amount"] is None
        for row in obligations
    ):
        gaps.append(
            issue(
                "FUNDS_USE_AMOUNT_UNKNOWN",
                "Resolve unknown seller liabilities before application preparation.",
            )
        )
    if not uses:
        gaps.append(
            issue("FUNDS_USE_REVIEW", "Confirm the requested funds-use schedule.")
        )
    return {
        "requested_amount": option["draw"],
        "purpose": "Export working capital preparation only",
        "tenor_days": tenor,
        "documents": documents,
        "provider_urls": sorted(
            {
                evidence[identifier]["canonical_url"]
                for identifier in product["source_ids"]
                if identifier in evidence and evidence[identifier].get("canonical_url")
            }
        ),
        "source_evidence_ids": selected_evidence,
        "gaps": gaps,
        "preparation_status": "needs_information" if gaps else "application_ready",
        "funds_use_schedule": uses,
    }
