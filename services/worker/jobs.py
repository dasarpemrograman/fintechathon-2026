"""Durable job execution shared by the daemon and deterministic integration tests."""

from copy import deepcopy
from datetime import timedelta
import hashlib, json, re
import sqlalchemy as sa
from services.api import store, commands, storage
from services.api.store import DomainError, meta, digest, save, get, issue, now, instant
from packages.domain.economics import compute
from packages.domain.dependencies import (
    CALCULATOR_VERSION,
    DEPENDENCY_POLICY,
    material_ids,
    selected_fx,
    references,
)
from packages.contracts.runtime import DOCUMENT
from scripts.validate_contract import schema_validator

RESOURCE_SCHEMAS = {
    "analysis": "Analysis",
    "scenario": "Scenario",
    "evidence": "Evidence",
    "fact_candidate": "FactCandidate",
    "finance_product": "FinanceProduct",
    "funding_option": "FundingOption",
    "finance_pack": "FinancePack",
    "artifact": "Artifact",
    "document": "Document",
    "fx_observation": "FxObservation",
}
SEGMENT = {
    "analysis": "analyses",
    "scenario": "scenarios",
    "evidence": "evidence",
    "fact_candidate": "fact-candidates",
    "finance_product": "finance-products",
    "funding_option": "funding-options",
    "finance_pack": "finance-packs",
    "artifact": "artifacts",
    "document": "documents",
    "finance_options": "finance-options",
    "fx_observation": "fx-observations",
}


def claim(scope=None, dataset=None):
    from services.api.settings import settings

    scope = scope or ("demo" if settings.demo else "real")
    with store.engine.begin() as conn:
        namespace = (
            sa.true()
            if dataset is None
            else sa.exists(
                sa.select(store.registry.c.id).where(
                    store.registry.c.tenant_id == store.jobs.c.tenant_id,
                    store.registry.c.id == store.jobs.c.id,
                    store.registry.c.dataset_id == dataset,
                )
            )
        )
        exhausted = (
            conn.execute(
                sa.select(store.jobs)
                .join(
                    store.organizations,
                    store.organizations.c.id == store.jobs.c.tenant_id,
                )
                .where(
                    store.jobs.c.payload["scope"].as_string() == scope,
                    namespace,
                    store.jobs.c.attempts >= 3,
                    sa.or_(
                        store.jobs.c.state == "queued",
                        sa.and_(
                            store.jobs.c.state == "running",
                            store.jobs.c.lease_until < now(),
                        ),
                    ),
                )
                .with_for_update(skip_locked=True, of=[store.jobs, store.organizations])
            )
            .mappings()
            .all()
        )
        for expired in exhausted:
            run = get(conn, expired["tenant_id"], "run", expired["id"])
            run.update(
                status="failed",
                blockers=[
                    issue(
                        "JOB_ATTEMPTS_EXHAUSTED",
                        "Three interrupted or failed attempts exhausted the job budget; inspect the run before an explicit new request.",
                    )
                ],
            )
            save(
                conn,
                expired["tenant_id"],
                "run",
                run,
                parent=expired["payload"]["parent_id"],
            )
            conn.execute(
                store.jobs.update()
                .where(
                    store.jobs.c.id == expired["id"],
                    store.jobs.c.tenant_id == expired["tenant_id"],
                )
                .values(state="failed", lease_until=None)
            )
        row = (
            conn.execute(
                sa.select(store.jobs)
                .join(
                    store.organizations,
                    store.organizations.c.id == store.jobs.c.tenant_id,
                )
                .where(
                    store.jobs.c.cancelled.is_(False),
                    store.jobs.c.attempts < 3,
                    store.jobs.c.payload["scope"].as_string() == scope,
                    sa.true()
                    if dataset is None
                    else sa.exists(
                        sa.select(store.registry.c.id).where(
                            store.registry.c.tenant_id == store.jobs.c.tenant_id,
                            store.registry.c.id == store.jobs.c.id,
                            store.registry.c.dataset_id == dataset,
                        )
                    ),
                    store.jobs.c.available_at <= now(),
                    sa.or_(
                        store.jobs.c.state == "queued",
                        sa.and_(
                            store.jobs.c.state == "running",
                            store.jobs.c.lease_until < now(),
                        ),
                    ),
                )
                .order_by(store.jobs.c.available_at)
                .with_for_update(skip_locked=True, of=[store.jobs, store.organizations])
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        conn.execute(
            store.jobs.update()
            .where(
                store.jobs.c.id == row["id"], store.jobs.c.tenant_id == row["tenant_id"]
            )
            .values(
                state="running",
                attempts=row["attempts"] + 1,
                lease_until=now() + timedelta(seconds=90),
            )
        )
        run = get(conn, row["tenant_id"], "run", row["id"])
        run["status"] = "running"
        save(conn, row["tenant_id"], "run", run, parent=row["payload"]["parent_id"])
        return dict(row)


class Work:
    def __init__(self, conn, job):
        self.conn = conn
        self.job = job
        self.tenant = job["tenant_id"]
        self.payload = job["payload"]
        self.actor = self.payload["actor"]
        self.parent = deepcopy(self.payload["snapshot"])
        self.parent["revision"] = self.payload["input_revision"]
        self.body = self.payload["body"]
        self.outputs = []
        self.blockers = []
        self.warnings = []
        self.counter = 0
        self.billable_success = False
        self.processed_pages = 0
        self.pages_seen = 0
        self.used_cache = False
        self.provider_receipts = []
        self.billing_at = store.now()

    def record_provider(self, value):
        from packages.adapters.providers import metadata

        clean = metadata(value)
        schema_validator(DOCUMENT, "ProviderReceipt").validate(clean)
        self.provider_receipts.append(clean)

    def put(self, kind, data):
        self.counter += 1
        identifier = (
            kind + "_" + digest({"job": self.job["id"], "index": self.counter})[:24]
        )
        row = {**meta(self.tenant, self.actor, kind, identifier), **data}
        if kind in RESOURCE_SCHEMAS:
            schema_validator(DOCUMENT, RESOURCE_SCHEMAS[kind]).validate(row)
        save(
            self.conn,
            self.tenant,
            kind,
            row,
            parent=self.parent["id"],
            dataset=self.parent["dataset_id"],
        )
        root = "deals" if "workspace_id" in self.parent else "workspaces"
        href = (
            "/v2/"
            + root
            + "/"
            + self.parent["id"]
            + "/"
            + SEGMENT[kind]
            + "/"
            + row["id"]
        )
        self.outputs.append({"kind": kind, "id": row["id"], "href": href})
        return row

    def input(self, kind):
        return self.payload["input_resources"].get(kind, [])

    def evidence(self, title, text, category, url=None, content_hash=None, mode=None):
        value = {
            "canonical_url": url
            or (
                "https://sources.example.test/" + category
                if self.payload["scope"] == "demo"
                else None
            ),
            "document_id": None,
            "publisher": "Fincathon synthetic source"
            if self.payload["scope"] == "demo"
            else title,
            "title": title,
            "language": "und",
            "retrieved_at": instant(),
            "published_at": None,
            "effective_from": None,
            "valid_until": None,
            "access": "success",
            "mode": mode
            or ("synthetic_demo" if self.payload["scope"] == "demo" else "live"),
            "content_hash": content_hash or hashlib.sha256(text.encode()).hexdigest(),
            "hash_scope": "retrieved_content" if content_hash else "manual_excerpt",
            "locator": "source excerpt",
            "claim": text[:8000],
            "applicability": {
                "jurisdictions": [],
                "product_attributes": [],
                "shipment_ids": [],
                "line_item_ids": [],
                "validity_reason": "Requires transaction-specific review.",
                "unknowns": [],
            },
            "limitations": ["Synthetic illustration, not current advice."]
            if self.payload["scope"] == "demo"
            else ["Retrieved content is not yet reviewed for applicability."],
            "review_status": "unreviewed",
        }
        return self.put("evidence", value)


def process_discovery(work):
    from packages.adapters.budgets import Budget
    from packages.adapters.providers import search, fx_rates, receipt
    from packages.domain.discovery import plan, source_owner
    from packages.adapters.network import fetch
    from urllib.parse import urlsplit

    body = work.body
    limits = body["budget"]
    if (
        limits["max_queries"] > 12
        or limits["max_pages"] > 20
        or limits["max_actions"] > 40
        or limits["max_provider_retries"] > 2
    ):
        raise DomainError(
            "BUDGET_LIMIT", "Discovery exceeds the configured workload caps."
        )
    remaining = Budget(limits)
    if work.payload["scope"] == "demo":
        from services.api.settings import ROOT

        sources = json.loads((ROOT / "fixtures/demo/sources.json").read_text())
        for category in body["categories"]:
            try:
                remaining.consume("query")
                remaining.consume("page")
            except DomainError as error:
                work.warnings.append(issue(error.code, error.reason))
                break
            source = sources[category]
            evidence = work.evidence(source["title"], source["text"], category)
            value = receipt("offline-fixtures", source, mode="synthetic_demo")
            value["source_refs"] = [{"id": evidence["id"]}]
            work.record_provider(value)
        work.billable_success = bool(work.outputs)
        return
    parties = work.parent.get("parties", [])
    context = work.parent
    if work.parent.get("deal_id"):
        context = get(work.conn, work.tenant, "deal", work.parent["deal_id"])
        parties = context["parties"]
    queries, warnings = plan(work.parent, body, parties)
    work.warnings += warnings

    def record_error(error, provider):
        value = getattr(error, "provider_receipt", None) or receipt(
            provider, None, mode=None, status="unavailable", limitations=[error.reason]
        )
        work.record_provider(value)

    if "fx" in body["categories"]:
        pairs = []
        if body.get("fx_base_currency") and body.get("fx_quote_currencies"):
            pairs = [(body["fx_base_currency"], body["fx_quote_currencies"])]
        else:
            currencies = set()

            def collect(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key == "currency" and isinstance(item, str):
                            currencies.add(item)
                        collect(item)
                elif isinstance(value, list):
                    for item in value:
                        collect(item)

            collect(context)
            pairs = [
                (code, [work.parent["reporting_currency"]])
                for code in sorted(currencies)
                if code != work.parent["reporting_currency"]
            ]
        if not pairs:
            work.warnings.append(
                issue(
                    "FX_PAIR_REQUIRED",
                    "Choose a reference currency pair; no foreign currency is assumed.",
                )
            )
        for base, quotes in pairs:
            try:
                remaining.consume("query")
                remaining.consume("page")
                result = fx_rates(base, quotes)
                refs = []
                for row in result["data"]:
                    evidence = work.evidence(
                        "Frankfurter reference FX " + row["base"] + "/" + row["quote"],
                        "1 "
                        + row["base"]
                        + " = "
                        + row["rate"]
                        + " "
                        + row["quote"]
                        + "; source date "
                        + row["date"]
                        + "; providers "
                        + ", ".join(row["providers"]),
                        "fx",
                        "https://api.frankfurter.dev/v2/rates",
                        result["response_hash"],
                        "live",
                    )
                    evidence.update(
                        effective_from=row["date"],
                        retrieved_at=result["fetched_at"],
                        locator="Reference rate row "
                        + row["base"]
                        + "/"
                        + row["quote"]
                        + "/"
                        + row["date"],
                        limitations=result["limitations"],
                        publisher="Frankfurter reference-rate providers",
                    )
                    save(
                        work.conn,
                        work.tenant,
                        "evidence",
                        evidence,
                        parent=work.parent["id"],
                        dataset=work.parent["dataset_id"],
                    )
                    work.put(
                        "fx_observation",
                        {
                            "base_currency": row["base"],
                            "quote_currency": row["quote"],
                            "rate": row["rate"],
                            "as_of": result["fetched_at"],
                            "source_date": row["date"],
                            "evidence_ids": [evidence["id"]],
                            "mode": "live",
                        },
                    )
                    refs.append({"id": evidence["id"]})
                result["source_refs"] = refs
                work.record_provider(result)
                work.billable_success |= bool(refs)
                if result["status"] == "partial":
                    work.warnings.append(
                        issue(
                            "FX_COVERAGE_PARTIAL",
                            "Some requested reference pairs were unavailable.",
                        )
                    )
            except DomainError as error:
                record_error(error, "frankfurter")
                work.blockers.append(issue(error.code, error.reason))
    for query in queries:
        if remaining.pages >= limits["max_pages"]:
            work.warnings.append(
                issue(
                    "DISCOVERY_BUDGET_EXHAUSTED",
                    "Remaining sources were not fetched within the approved page budget.",
                )
            )
            break
        try:
            for attempt in range(limits["max_provider_retries"] + 1):
                remaining.consume("query")
                try:
                    result = search(
                        query["query"], limits["max_pages"] - remaining.pages
                    )
                    break
                except DomainError as error:
                    record_error(error, "brave")
                    if (
                        error.code != "SEARCH_UNAVAILABLE"
                        or attempt >= limits["max_provider_retries"]
                    ):
                        raise
            work.record_provider(result)
            if result["status"] == "partial":
                work.warnings.append(
                    issue(
                        "SEARCH_NO_RESULTS",
                        "No fetched source coverage was established for this query.",
                    )
                )
            for observation in result["data"][:3]:
                try:
                    remaining.consume("page")
                    fetched = fetch(observation["url"])
                    if fetched["media_type"] == "application/pdf":
                        work.record_provider(
                            {
                                **receipt(
                                    "public-https",
                                    None,
                                    mode="live",
                                    status="partial",
                                    response_hash=fetched["hash"],
                                    limitations=[
                                        "Public PDF retrieved; use bounded document ingestion for locatable extraction before treating it as source facts."
                                    ],
                                ),
                                "source_url": fetched["url"],
                            }
                        )
                        work.warnings.append(
                            issue(
                                "PUBLIC_PDF_REVIEW_REQUIRED",
                                "A PDF requires document ingestion; search snippets are not executable quotations.",
                            )
                        )
                        continue
                    decoded = fetched["content"].decode("utf-8", errors="replace")
                    decoded = re.sub(
                        r"<(script|style)\b[^>]*>.*?</\1>",
                        " ",
                        decoded,
                        flags=re.I | re.S,
                    )
                    text = re.sub("<[^>]+>", " ", decoded)
                    evidence = work.evidence(
                        observation["title"],
                        text,
                        query["category"],
                        fetched["url"],
                        fetched["hash"],
                        "live",
                    )
                    evidence.update(
                        publisher=source_owner(fetched["url"]),
                        retrieved_at=fetched["fetched_at"],
                        locator="Retrieved response text excerpt after markup removal",
                    )
                    evidence["applicability"].update(
                        jurisdictions=[query["jurisdiction"]]
                        if query["jurisdiction"]
                        else [],
                        validity_reason="Candidate for "
                        + query["direction"]
                        + " review; applicability is not confirmed.",
                    )
                    save(
                        work.conn,
                        work.tenant,
                        "evidence",
                        evidence,
                        parent=work.parent["id"],
                        dataset=work.parent["dataset_id"],
                    )
                    value = receipt(
                        "public-https",
                        None,
                        mode="live",
                        response_hash=fetched["hash"],
                        request_id=fetched["provider_request_id"],
                    )
                    value.update(
                        source_refs=[{"id": evidence["id"]}], source_url=fetched["url"]
                    )
                    work.record_provider(value)
                    work.billable_success = True
                except DomainError as error:
                    record_error(error, "public-https")
                    work.warnings.append(issue(error.code, error.reason))
        except DomainError as error:
            work.blockers.append(issue(error.code, error.reason))
            if error.code in {
                "SEARCH_CREDENTIAL_MISSING",
                "SEARCH_AUTH_REQUIRED",
                "DISCOVERY_BUDGET_EXHAUSTED",
            }:
                break


def process_documents(work):
    from packages.adapters.documents import extract, candidates
    from packages.adapters.extraction_cache import VERSION, lookup, remember

    for identifier in work.body["document_ids"]:
        document = get(work.conn, work.tenant, "document", identifier)
        if (
            document.get("parser_version") == VERSION
            and document.get("processed_pages", 0) > 0
        ):
            work.used_cache = True
            continue
        try:
            cached = lookup(
                work.conn, work.tenant, document["content_hash"], work.payload["scope"]
            )
            if cached:
                pages = cached["pages"]
                work.used_cache = True
            else:
                pages = extract(
                    storage.read_bytes(document["content_hash"]), document["media_type"]
                )
                _, _, remaining_pages, _ = commands.allowance_state(
                    work.conn, work.tenant
                )
                if work.processed_pages + len(pages) > remaining_pages + work.body.get(
                    "expected_pages", len(work.body["document_ids"])
                ):
                    raise DomainError(
                        "PAGE_ALLOWANCE_EXHAUSTED",
                        "Extraction exceeds remaining current-period page allowance.",
                    )
                remember(
                    work.conn,
                    work.tenant,
                    document["content_hash"],
                    work.payload["scope"],
                    pages,
                )
                work.processed_pages += len(pages)
            work.pages_seen += len(pages)
            extracted = candidates(pages)
            if len(extracted) >= 500:
                work.warnings.append(
                    issue(
                        "CANDIDATE_LIMIT",
                        "At most 500 candidates are retained per document; review the original for additional facts.",
                    )
                )
            for candidate in extracted:
                # Source ownership is established by the original uploaded document.
                evidence = work.evidence(
                    "Extracted " + document["filename"],
                    candidate["original_text"],
                    "document",
                )
                evidence.update(
                    canonical_url=None,
                    document_id=identifier,
                    mode="synthetic_demo"
                    if work.payload["scope"] == "demo"
                    else "user_provided",
                    locator=candidate["locator"],
                    content_hash=document["content_hash"],
                    hash_scope="original_document",
                    parser_version=VERSION,
                    language=candidate["original_language"],
                )
                save(
                    work.conn,
                    work.tenant,
                    "evidence",
                    evidence,
                    parent=work.parent["id"],
                    dataset=work.parent["dataset_id"],
                )
                document["evidence_ids"].append(evidence["id"])
                work.put(
                    "fact_candidate",
                    {
                        "workspace_id": document["workspace_id"],
                        **candidate,
                        "source_ref": {"id": evidence["id"]},
                        "status": "unreviewed",
                        "reviewer_id": None,
                        "supersedes": None,
                    },
                )
            document["state"] = (
                "needs_review" if document["evidence_ids"] else "processed"
            )
            document.update(
                parser_version=VERSION,
                processed_pages=len(pages),
                extraction_cache_hit=bool(cached),
            )
        except DomainError as error:
            document["state"] = "needs_review"
            work.warnings.append(issue(error.code, error.reason))
        save(
            work.conn,
            work.tenant,
            "document",
            document,
            parent=work.parent["id"],
            dataset=work.parent["dataset_id"],
        )


def process_analysis(work):
    parent = deepcopy(work.parent)
    if "workspace_id" not in parent and work.body.get("scenario_id"):
        proposed = get(work.conn, work.tenant, "scenario", work.body["scenario_id"])
        commands.patch_facts(
            work.conn,
            {"tenant": work.tenant, "actor": work.actor},
            parent,
            proposed["patches"],
            "workspace",
        )
    if "workspace_id" not in parent:
        planning = parent.get("planning_inputs")
        if not planning:
            raise DomainError(
                "PLANNING_INPUTS_MISSING",
                "Add explicit product costs or other planning facts before analysis.",
            )
        parent.update(deepcopy(planning))
        parent.update(
            snapshot_hash=work.parent.get("snapshot_hash", digest(work.parent)),
            business_profile=work.parent["business_profile"],
        )
        context = {
            "tenant": work.tenant,
            "actor": work.actor,
            "scope": work.payload["scope"],
        }
        work.payload["input_resources"]["cost_line"] = commands.procurement_costs(
            context, parent
        ) + [
            {**meta(work.tenant, work.actor, "cost_line"), **c}
            for c in planning["cost_lines"]
        ]
        work.payload["input_resources"]["fx_observation"] = [
            {**meta(work.tenant, work.actor, "fx_observation"), **o}
            for o in planning["fx_observations"]
        ]
        work.payload["input_resources"]["obligation"] = [
            {
                "id": t["id"],
                "payer_party_id": t["payer_id"],
                "payee_party_id": t["payee_id"],
                "amount": t["amount"],
                "schedule": t["schedule"],
                "sequence": t.get("sequence"),
            }
            for t in planning["payment_terms"]
        ]
    scenario_id = work.body.get("scenario_id")
    scenario = None
    if scenario_id:
        scenario = get(work.conn, work.tenant, "scenario", scenario_id)
        context = {
            "tenant": work.tenant,
            "actor": work.actor,
            "scope": work.payload["scope"],
        }
        if "workspace_id" in work.parent:
            commands.patch_facts(
                work.conn, context, parent, scenario["patches"], "deal"
            )
        costs, obligations = commands.analysis_inputs(
            work.conn,
            context,
            parent,
            work.payload["input_resources"],
            scenario["patches"],
        )
        work.payload["input_resources"].update(cost_line=costs, obligation=obligations)
    else:
        scenario = work.put(
            "scenario",
            {
                "base_revision": {"id": parent["id"], "revision": parent["revision"]},
                "patches": [],
                "funding_option_ids": [],
                "assumption_ids": [],
                "status": "hypothetical",
            },
        )
    funding = [
        get(work.conn, work.tenant, "funding_option", identifier)
        for identifier in scenario["funding_option_ids"]
    ]
    work.payload["input_resources"]["fx_observation"] = selected_fx(
        parent, work.payload["input_resources"], scenario["funding_option_ids"]
    )
    result = compute(
        parent,
        work.input("cost_line"),
        work.input("obligation"),
        work.input("milestone"),
        work.input("fx_observation"),
        commands.all_records(work.conn, work.tenant, "business_calendar"),
        funding,
        work.input("receipt"),
    )
    from packages.domain.pricing import normalized_range
    from datetime import date
    from services.api.settings import ROOT

    as_of = (
        date.fromisoformat(
            json.loads((ROOT / "fixtures/demo/manifest.json").read_text())[
                "reference_date"
            ]
        )
        if work.payload["scope"] == "demo"
        else date.fromisoformat(
            work.payload.get("valuation_date", store.now().date().isoformat())
        )
    )
    result["price_range"] = normalized_range(
        parent,
        result["price_range"],
        work.input("market_observation"),
        work.input("fx_observation"),
        as_of,
        work.input("evidence"),
    )
    source_ids = material_ids(
        parent,
        work.payload["input_resources"],
        scenario["funding_option_ids"],
        commands.children(work.conn, work.tenant, "approval", parent),
        as_of,
    )
    evidence = [row for row in work.input("evidence") if row["id"] in source_ids]
    snapshot_hash = digest(
        {
            "base_deal_hash": work.parent.get("snapshot_hash", digest(work.parent)),
            "scenario": scenario,
            "funding": funding,
            "calculator_version": CALCULATOR_VERSION,
            "valuation_date": as_of.isoformat(),
            "dependency_policy": DEPENDENCY_POLICY,
        }
    )
    refs = deepcopy(work.payload.get("input_resource_refs", {}))
    refs["evidence"] = [
        ref for ref in refs.get("evidence", []) if ref["id"] in source_ids
    ]
    by_ref = {ref["id"]: ref for rows in refs.values() for ref in rows}
    for metrics in [
        result["cash_metrics"],
        result["before_financing"]["cash_metrics"],
        result["after_financing"]["cash_metrics"],
    ]:
        if metrics:
            for point in metrics.get("event_balances", []):
                reference = point["source_ref"]
                if reference and reference["id"] in by_ref:
                    point["source_ref"] = by_ref[reference["id"]]
    for cost in result.get("cost_breakdown", []):
        if cost["cost_line_ref"]["id"] in by_ref:
            cost["cost_line_ref"] = by_ref[cost["cost_line_ref"]["id"]]

    def metric_sources(kinds):
        ids = set()
        for kind in kinds:
            for record in work.input(kind):
                if kind == "cost_line" and record.get("actual_amount") is not None:
                    ids.update(
                        record.get("actual_evidence_ids", record["evidence_ids"])
                    )
                elif (
                    kind == "funding_option"
                    and record["id"] not in scenario["funding_option_ids"]
                ):
                    continue
                else:
                    ids.update(references(record))
                    ids.update(record.get("source_ids", []))
        if "funding_option" in kinds:
            ids.update(references(parent.get("invoices", [])))
        if "obligation" in kinds:
            snapshot = parent["constraints"]["cash_snapshot"]
            for approval in commands.children(
                work.conn, work.tenant, "approval", parent
            ):
                if (
                    snapshot
                    and approval["purpose"] == "cash_resources"
                    and approval["analysis_hash"] == digest(snapshot)
                ):
                    ids.update(approval.get("evidence_ids", []))
        return [ref for ref in refs.get("evidence", []) if ref["id"] in ids]

    result["numeric_lineage"] = [
        {
            "metric": metric,
            "formula": formula,
            "input_refs": [
                {"id": work.parent["id"], "revision": work.payload["input_revision"]}
            ]
            + [ref for kind in kinds for ref in refs.get(kind, [])],
            "evidence_refs": metric_sources(kinds),
            "calculator_version": CALCULATOR_VERSION,
        }
        for metric, formula, kinds in [
            (
                "seller_operating_expense",
                "Sum nonoverlapping seller-borne economic expenses; actual replaces estimated amount.",
                ["cost_line", "fx_observation"],
            ),
            (
                "contribution",
                "Buyer invoice revenue minus reimbursed advances, approved receivable write-offs, seller expenses and financing costs, plus realized receivable FX differences.",
                [
                    "cost_line",
                    "obligation",
                    "receipt",
                    "funding_option",
                    "fx_observation",
                ],
            ),
            (
                "minimum_cash",
                "Minimum chronological opening cash plus verified/forecast net cash events; debit-first when sequence unknown.",
                [
                    "obligation",
                    "receipt",
                    "milestone",
                    "funding_option",
                    "fx_observation",
                ],
            ),
            (
                "seller_floor",
                "Fixed economic cost / (1 - target contribution margin - sales-dependent cost fractions), divided by declared line quantity.",
                ["cost_line", "fx_observation", "market_observation"],
            ),
        ]
    ]
    from packages.domain.comparison import assess

    result["owner_comparison"] = assess(
        parent,
        scenario,
        result,
        work.input("obligation"),
        work.input("milestone"),
        work.input("fx_observation"),
        commands.all_records(work.conn, work.tenant, "business_calendar"),
        work.parent.get("constraints", parent["constraints"]),
        work.parent if "workspace_id" in work.parent else parent,
        work.input("receipt"),
    )
    row = work.put(
        "analysis",
        {
            "scenario_id": scenario["id"],
            "dependency_policy": DEPENDENCY_POLICY,
            "valuation_date": as_of.isoformat(),
            "snapshot_hash": snapshot_hash,
            "base_deal_hash": work.parent.get("snapshot_hash", digest(work.parent)),
            "evidence_digest": digest(evidence),
            "rule_versions": [
                {"id": r["id"]}
                for r in commands.children(
                    work.conn, work.tenant, "requirement", parent
                )
            ],
            "calculator_version": CALCULATOR_VERSION,
            **result,
            "input_evidence_ids": [r["id"] for r in evidence],
        },
    )
    work.blockers += row["blockers"]
    work.warnings += row["warnings"]
    from packages.domain.model_tasks import explain

    if work.body.get("execution") == "enrich":
        try:
            selection = explain(
                row,
                row["input_evidence_ids"],
                live=work.payload["scope"] != "demo",
                record_receipt=work.record_provider,
            )
            work.billable_success = True
            from packages.domain.artifacts import render

            content, placeholders = render(
                parent, scenario, row, "recommendation", "id"
            )
            content += "\n\nReviewed explanation sections: " + ", ".join(
                selection["sections"]
            )
            work.put(
                "artifact",
                {
                    "kind": "recommendation",
                    "scenario_id": scenario["id"],
                    "analysis_id": row["id"],
                    "template_version": "controlled-2",
                    "content_hash": digest({"content": content}),
                    "content": content,
                    "media_type": "text/plain",
                    "placeholders": placeholders,
                    "state": "draft",
                },
            )
        except DomainError as error:
            work.warnings.append(issue(error.code, error.reason))


def process_finance(work):
    if work.payload["scope"] != "demo":
        from packages.domain.finance import screen

        products = work.input("finance_product")
        if not products:
            raise DomainError(
                "FINANCE_REVIEW_REQUIRED",
                "Retrieve official product evidence and record reviewed terms before screening.",
            )
        evidence = {row["id"]: row for row in work.input("evidence")}
        options = []
        for product in products:
            result = screen(
                product, work.parent, work.body, evidence, store.now().date()
            )
            options.append(
                work.put(
                    "funding_option",
                    {
                        "product_id": product["id"],
                        **result,
                        "draw": work.body["requested_amount"],
                        "earliest_draw_milestone_id": None,
                        "schedule": [],
                        "assumptions": [
                            {
                                "status": "unreviewed",
                                "field_path": "/funding/schedule",
                                "reason": "Record explicit draw, fee and repayment terms before financed calculation; none are inferred from missing rates.",
                            }
                        ],
                        "status": "proposed",
                        "external_facility_evidence_ids": [],
                    },
                )
            )
        save(
            work.conn,
            work.tenant,
            "finance_options",
            {
                "id": "finance_options_" + digest(work.job["id"])[:24],
                "products": products,
                "options": options,
            },
            parent=work.parent["id"],
            dataset=work.parent["dataset_id"],
        )
        return
    from services.api.settings import ROOT

    catalog = json.loads((ROOT / "fixtures/demo/finance.json").read_text())
    currency = work.parent["reporting_currency"]
    terms = catalog.get(currency)
    if not terms:
        raise DomainError(
            "DEMO_PRODUCT_UNAVAILABLE",
            "No synthetic financing fixture is declared for this currency.",
        )
    evidence = work.evidence(
        "Synthetic pre-shipment finance",
        "Invented fixture terms, not a lender offer.",
        "finance",
    )
    from datetime import datetime, timedelta

    base = datetime.fromisoformat(
        work.parent["constraints"]["cash_snapshot"]["as_of"].replace("Z", "+00:00")
    )
    schedule = [
        {
            "kind": event["kind"],
            "amount": {"amount": event["amount"], "currency": currency},
            "schedule": {
                "kind": "fixed",
                "due": {
                    "instant": (
                        base + timedelta(days=event["day"], hours=event["hour"])
                    ).isoformat(),
                    "timezone": "UTC",
                },
            },
            "status": "proposed",
            "evidence_ids": [evidence["id"]],
            "sequence": event["sequence"],
        }
        for event in terms["events"]
    ]
    product = work.put(
        "finance_product",
        {
            "provider": "Synthetic Demo Facility",
            "jurisdiction": work.parent["seller_domicile"],
            "source_ids": [evidence["id"]],
            "stage": "pre_shipment",
            "eligibility_predicates": [
                {
                    "name": "Fixture-only eligibility",
                    "status": "unknown",
                    "reason": "Not a real lender decision.",
                    "evidence_ids": [evidence["id"]],
                }
            ],
            "document_requirements": [
                {
                    "name": "Business profile",
                    "basis": "provider_required",
                    "status": "missing",
                    "evidence_ids": [],
                }
            ],
            "rate": None,
            "rate_basis": None,
            "fees": [],
            "currency": currency,
            "minimum_amount": None,
            "maximum_amount": None,
            "recourse": "unknown",
            "security_requirements": [],
            "indicative_lead_days": None,
            "valid_until": None,
        },
    )
    option = work.put(
        "funding_option",
        {
            "product_id": product["id"],
            "fit": "needs_information",
            "fit_reasons": ["Hypothetical fixture, not verified lender availability."],
            "failed_predicates": [],
            "unknown_predicates": [
                "Actual lender eligibility, pricing and draw conditions"
            ],
            "draw": {"amount": terms["principal"], "currency": currency},
            "earliest_draw_milestone_id": None,
            "schedule": schedule,
            "assumptions": [
                {
                    "status": "unreviewed",
                    "field_path": "/funding",
                    "reason": "All financing terms in this fixture are synthetic.",
                }
            ],
            "status": "proposed",
            "external_facility_evidence_ids": [],
        },
    )
    work.billable_success = True
    identifier = "finance_options_" + digest(work.job["id"])[:24]
    save(
        work.conn,
        work.tenant,
        "finance_options",
        {"id": identifier, "products": [product], "options": [option]},
        parent=work.parent["id"],
        dataset=work.parent["dataset_id"],
    )
    work.outputs.append(
        {
            "kind": "funding_option",
            "id": option["id"],
            "href": "/v2/deals/"
            + work.parent["id"]
            + "/funding-options/"
            + option["id"],
        }
    )


def process_artifact(work):
    if work.payload["kind"] == "finance_pack":
        option = get(
            work.conn, work.tenant, "funding_option", work.body["funding_option_id"]
        )
        scenario = get(work.conn, work.tenant, "scenario", work.body["scenario_id"])
        kind = "finance_pack"
        analysis = next(
            (
                a
                for a in reversed(
                    commands.children(work.conn, work.tenant, "analysis", work.parent)
                )
                if a["scenario_id"] == scenario["id"]
            ),
            None,
        )
        if not analysis:
            raise DomainError(
                "ANALYSIS_REQUIRED", "Analyze the selected financing scenario first."
            )
    else:
        kind = work.body["kind"]
        scenario = get(work.conn, work.tenant, "scenario", work.body["scenario_id"])
        analysis = get(work.conn, work.tenant, "analysis", work.body["analysis_id"])
    if (
        analysis.get("base_deal_hash")
        != work.parent.get("snapshot_hash", digest(work.parent))
        or not commands.analysis_view(work.conn, work.tenant, work.parent, analysis)[
            "current_for_use"
        ]
    ):
        raise DomainError(
            "STALE_ANALYSIS", "Recalculate against current inputs before drafting.", 409
        )
    from packages.domain.artifacts import render

    rendered_deal = deepcopy(work.parent)
    commands.patch_facts(
        work.conn,
        {"tenant": work.tenant, "actor": work.actor},
        rendered_deal,
        scenario["patches"],
        "deal",
    )
    content, placeholders = render(
        rendered_deal,
        scenario,
        analysis,
        kind,
        work.body.get("language", "id"),
        work.body.get("recipient_party_id"),
        option if work.payload["kind"] == "finance_pack" else None,
    )
    pack = None
    if work.payload["kind"] == "finance_pack":
        from packages.domain.finance import preparation

        if option["id"] not in scenario["funding_option_ids"]:
            raise DomainError(
                "PACK_SCENARIO_OPTION",
                "Funding option must belong to the selected scenario.",
            )
        if not option["product_id"]:
            raise DomainError(
                "FINANCE_PRODUCT_REQUIRED",
                "Link the provider product and checklist before preparing an application pack.",
            )
        product = get(work.conn, work.tenant, "finance_product", option["product_id"])
        from datetime import date
        from services.api.settings import ROOT

        today = (
            date.fromisoformat(
                json.loads((ROOT / "fixtures/demo/manifest.json").read_text())[
                    "reference_date"
                ]
            )
            if work.payload["scope"] == "demo"
            else store.now().date()
        )
        pack = preparation(
            work.parent,
            option,
            product,
            work.body["evidence_ids"],
            {row["id"]: row for row in work.input("evidence")},
            work.input("obligation"),
            {row["id"]: row for row in work.input("milestone")},
            {
                row["id"]: row
                for row in commands.all_records(
                    work.conn, work.tenant, "business_calendar"
                )
            },
            today,
        )
        if analysis["completeness"] == "partial":
            pack["gaps"].append(
                issue(
                    "APPLICATION_ANALYSIS_PARTIAL",
                    "Resolve incomplete financial inputs before application-ready preparation.",
                )
            )
        if any(
            check["status"] != "satisfied"
            for check in analysis.get("owner_comparison", {}).get("checks", [])
        ):
            pack["gaps"].append(
                issue(
                    "APPLICATION_OWNER_CONSTRAINTS",
                    "Resolve failed or unknown owner constraints before application-ready preparation.",
                )
            )
        from packages.domain.cost_coverage import covered

        if not covered(
            work.parent,
            work.input("cost_line"),
            work.input("obligation"),
            work.input("fx_observation"),
        ):
            pack["gaps"].append(
                issue(
                    "FUNDS_USE_COVERAGE",
                    "Linked obligations must cover the declared cash costs.",
                )
            )
        pack["documents"].append(
            {
                "name": "Scenario cash-flow analysis",
                "basis": "recommended_analysis",
                "status": "present"
                if analysis["completeness"] != "partial"
                else "needs_review",
                "evidence_ids": analysis["input_evidence_ids"],
            }
        )
        pack["preparation_status"] = (
            "needs_information" if pack["gaps"] else "application_ready"
        )
        refs = {
            row["id"]: row
            for row in work.payload.get("input_resource_refs", {}).get("obligation", [])
        }
        for use in pack["funds_use_schedule"]:
            use["obligation_ref"] = refs.get(
                use["obligation_ref"]["id"], use["obligation_ref"]
            )
        content += "\n\nJadwal penggunaan dana (persiapan):\n" + "\n".join(
            use["amount"]["currency"]
            + " "
            + use["amount"]["amount"]
            + " · "
            + str(use["schedule"])
            for use in pack["funds_use_schedule"]
        )
        content += "\n\nDaftar dokumen:\n" + "\n".join(
            document["name"] + " · " + document["basis"] + " · " + document["status"]
            for document in pack["documents"]
        )
        content += "\n\nBagian yang belum lengkap:\n" + "\n".join(
            gap["reason"] for gap in pack["gaps"]
        )
    artifact = work.put(
        "artifact",
        {
            "kind": kind,
            "scenario_id": scenario["id"],
            "analysis_id": analysis["id"],
            "template_version": "controlled-2",
            "content_hash": digest({"content": content}),
            "content": content,
            "media_type": "text/plain",
            "placeholders": placeholders,
            "state": "draft",
        },
    )
    if pack is not None:
        work.put(
            "finance_pack",
            {"artifact": artifact, "funding_option_id": option["id"], **pack},
        )
        work.blockers += pack["gaps"]


def process(job):
    with store.engine.begin() as conn:
        conn.execute(
            sa.select(store.organizations.c.id)
            .where(store.organizations.c.id == job["tenant_id"])
            .with_for_update()
        )
        current_job = (
            conn.execute(
                sa.select(store.jobs).where(
                    store.jobs.c.id == job["id"],
                    store.jobs.c.tenant_id == job["tenant_id"],
                )
            )
            .mappings()
            .one()
        )
        run = get(conn, job["tenant_id"], "run", job["id"])
        if current_job["state"] not in {"running", "queued"}:
            return run
        if current_job["attempts"] != job["attempts"] + 1:
            return run
        if current_job["cancelled"]:
            run["status"] = "cancelled"
        else:
            work = Work(conn, job)
            try:
                from services.api.settings import settings

                if job["payload"]["scope"] == "demo" and not settings.demo:
                    raise DomainError(
                        "DEMO_DISABLED", "Demo workers require explicit demo mode.", 403
                    )
                from packages.domain.entitlements import policy_view

                if (
                    run["usage"]["chargeable"]
                    or job["payload"]["kind"] in {"draft", "finance_pack"}
                ) and not policy_view(conn, job["tenant_id"])[-1]:
                    raise DomainError(
                        "ENTITLEMENT_EXPIRED",
                        "New provider work is paused; the prior records remain available.",
                        429,
                    )
                handler = {
                    "discovery": process_discovery,
                    "document_ingestion": process_documents,
                    "analysis": process_analysis,
                    "scenario": process_analysis,
                    "finance_options": process_finance,
                    "draft": process_artifact,
                    "finance_pack": process_artifact,
                }.get(job["payload"]["kind"])
                if handler is None:
                    from packages.adapters.calendar import process_calendar

                    process_calendar(work)
                else:
                    handler(work)
                run.update(
                    output_refs=work.outputs,
                    blockers=work.blockers,
                    warnings=work.warnings,
                    status="partial" if work.blockers or work.warnings else "succeeded",
                    data_modes=[
                        "synthetic_demo"
                        if job["payload"]["scope"] == "demo"
                        else "live"
                        if job["payload"]["kind"] == "discovery" and work.outputs
                        else "user_provided"
                    ],
                )
            except DomainError as error:
                if getattr(error, "provider_receipt", None):
                    work.record_provider(error.provider_receipt)
                run.update(
                    status="partial" if work.outputs else "failed",
                    output_refs=work.outputs,
                    blockers=[issue(error.code, error.reason)],
                    warnings=work.warnings,
                )
            parent = get(
                conn,
                job["tenant_id"],
                job["payload"]["parent_kind"],
                job["payload"]["parent_id"],
            )
            if parent["revision"] != job["payload"]["input_revision"]:
                run["warnings"].append(
                    issue(
                        "STALE_INPUT",
                        "Outputs bind an older revision and cannot replace the current plan.",
                    )
                )
                run["status"] = "partial"
            elif job["payload"]["parent_kind"] == "deal":
                if (
                    job["payload"]["kind"] in {"analysis", "scenario"}
                    and work.outputs
                    and run["status"] != "failed"
                ):
                    parent["states"]["analysis"] = (
                        "analyzed_partial" if run["blockers"] else "analyzed_complete"
                    )
                parent["revision"] += 1
                parent["snapshot_hash"] = commands.current_fact_hash(
                    conn, job["tenant_id"], parent
                )
                commands.derive_states(conn, {"tenant": job["tenant_id"]}, parent)
                save(
                    conn,
                    job["tenant_id"],
                    "deal",
                    parent,
                    parent=parent["workspace_id"],
                    dataset=parent["dataset_id"],
                    snapshot=True,
                )
            if job["payload"]["parent_kind"] == "workspace":
                current_hash = commands.current_fact_hash(
                    conn, job["tenant_id"], parent
                )
                if parent.get("snapshot_hash") != current_hash:
                    parent["snapshot_hash"] = current_hash
                    parent["revision"] += 1
                    save(
                        conn,
                        job["tenant_id"],
                        "workspace",
                        parent,
                        dataset=parent["dataset_id"],
                        snapshot=True,
                    )
                commands.invalidate_workspace_dependents(
                    conn, {"tenant": job["tenant_id"]}, parent
                )
            if (
                run["usage"]["chargeable"]
                and run["status"] in {"succeeded", "partial"}
                and (work.billable_success or work.processed_pages)
            ):
                identifier = "usage_" + job["id"]
                from packages.domain.entitlements import allocations

                charged_allocations, version = allocations(
                    conn,
                    job["tenant_id"],
                    1 if work.billable_success else 0,
                    work.processed_pages,
                    at=work.billing_at,
                )
                row = {
                    "allocations": charged_allocations,
                    "catalog_version": version,
                    "billing_at": work.billing_at.isoformat(),
                    **meta(
                        job["tenant_id"], job["payload"]["actor"], "usage", identifier
                    ),
                    "run_id": job["id"],
                    "enriched_runs": 1 if work.billable_success else 0,
                    "document_pages": work.processed_pages,
                }
                if get(conn, job["tenant_id"], "usage", identifier, False) is None:
                    save(
                        conn,
                        job["tenant_id"],
                        "usage",
                        row,
                        parent=job["payload"]["parent_id"],
                        dataset=parent["dataset_id"],
                    )
                run["usage"].update(
                    charged_runs=row["enriched_runs"],
                    charged_pages=work.processed_pages,
                    reason="Successful provider work/pages metered once by job identity.",
                )
            if job["payload"]["kind"] == "discovery" and not work.outputs:
                run["data_modes"] = []
            run["provider_receipts"] = work.provider_receipts
            run["usage"].update(
                processed_pages=work.pages_seen, cache_hit=work.used_cache
            )
            if work.used_cache and job["payload"]["scope"] != "demo":
                run["data_modes"] = (
                    ["cached", "user_provided"] if work.processed_pages else ["cached"]
                )
        save(conn, job["tenant_id"], "run", run, parent=job["payload"]["parent_id"])
        conn.execute(
            store.jobs.update()
            .where(
                store.jobs.c.id == job["id"], store.jobs.c.tenant_id == job["tenant_id"]
            )
            .values(state=run["status"], lease_until=None)
        )
    return run


def run_once(scope=None, dataset=None):
    job = claim(scope, dataset)
    if not job:
        return None
    try:
        from services.worker.heartbeat import heartbeat

        with heartbeat(job):
            return process(job)
    except Exception as error:
        import logging, traceback

        logging.error(
            "job_failure job=%s request=%s type=%s frames=%s",
            job["id"],
            job["payload"].get("request_id", "legacy"),
            type(error).__name__,
            [
                (frame.name, frame.lineno)
                for frame in traceback.extract_tb(error.__traceback__)
            ][-8:],
        )
        with store.engine.begin() as conn:
            state = "queued" if job["attempts"] < 2 else "failed"
            conn.execute(
                store.jobs.update()
                .where(
                    store.jobs.c.id == job["id"],
                    store.jobs.c.tenant_id == job["tenant_id"],
                )
                .values(
                    state=state,
                    lease_until=None,
                    available_at=now() + timedelta(seconds=2),
                )
            )
            if state == "failed":
                run = get(conn, job["tenant_id"], "run", job["id"])
                run.update(
                    status="failed",
                    blockers=[
                        issue(
                            "WORKER_FAILURE",
                            "Worker could not produce a valid persisted result; inspect correlated diagnostics.",
                        )
                    ],
                )
                save(
                    conn,
                    job["tenant_id"],
                    "run",
                    run,
                    parent=job["payload"]["parent_id"],
                )
        raise
