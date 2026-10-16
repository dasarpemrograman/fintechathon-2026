"""Durable admission; processing happens in the independent worker."""

from copy import deepcopy
from services.api import commands, store, storage
from services.api.store import DomainError, meta, save, digest, get


def accept_job(conn, context, operation, parent, body, request=None):
    from services.api.handlers import env
    from services.api.settings import settings

    if operation in {"analyzeSandbox", "createSandboxScenario"} and parent.get(
        "deal_id"
    ):
        raise DomainError(
            "WORKSPACE_CONVERTED",
            "Use the linked Deal for analysis after conversion.",
            409,
        )
    if parent["execution_scope"] != ("demo" if settings.demo else "real"):
        raise DomainError(
            "EXECUTION_MODE_MISMATCH",
            "Start the matching normal or demo runtime before new provider/worker commands.",
            503,
        )

    kind = {
        "startDiscovery": "discovery",
        "analyzeDeal": "analysis",
        "createScenario": "scenario",
        "discoverFinanceOptions": "finance_options",
        "prepareFinancePack": "finance_pack",
        "generateDraft": "draft",
        "syncCalendar": "calendar",
        "uploadDocuments": "document_ingestion",
        "retryDocument": "document_ingestion",
        "analyzeSandbox": "analysis",
        "createSandboxScenario": "scenario",
    }[operation]
    from packages.domain.entitlements import require_feature

    deterministic_matching = (
        kind == "finance_options" and parent["execution_scope"] == "real"
    )
    if (
        kind in {"draft", "finance_pack", "discovery", "finance_options"}
        and not deterministic_matching
    ):
        require_feature(conn, context["tenant"], kind)
    if kind == "scenario" and "workspace_id" in parent:
        require_feature(conn, context["tenant"], "negotiation")
    payload = deepcopy(body)
    if deterministic_matching:
        payload["_deterministic_matching"] = True
    if operation == "retryDocument":
        from services.api.handlers import verify_parent
        from packages.adapters.extraction_cache import VERSION, lookup

        document = verify_parent(
            conn, context, "document", request.path_params["resource_id"], parent
        )
        if (
            document.get("parser_version") == VERSION
            and document.get("processed_pages", 0) > 0
        ):
            raise DomainError(
                "REEXTRACTION_NOT_REQUIRED",
                "This version has already been extracted; review its candidates instead.",
                409,
            )
        payload["document_ids"] = [document["id"]]
        payload["expected_pages"] = (
            0
            if lookup(
                conn,
                context["tenant"],
                document["content_hash"],
                parent["execution_scope"],
            )
            else 1
        )
        admitted = commands.admission(conn, context, False, payload["expected_pages"])
        if not admitted["admitted"]:
            raise DomainError("PAGE_ALLOWANCE_EXHAUSTED", admitted["reason"], 429)
        job = commands.enqueue(conn, context, parent, "document_ingestion", payload)
        return env(context, {"documents": [document], "job": job}, parent, "accepted")
    admission = commands.admission(
        conn,
        context,
        body.get("execution") == "enrich"
        or kind in {"discovery", "finance_options"}
        and not deterministic_matching,
    )
    if not admission["admitted"]:
        raise DomainError("ALLOWANCE_EXHAUSTED", admission["reason"], 429)
    scenario = None
    if operation in {"createScenario", "createSandboxScenario"}:
        if (
            body["base_revision"]["id"] != parent["id"]
            or body["base_revision"].get("revision") != parent["revision"]
        ):
            raise DomainError(
                "SCENARIO_BASE", "Scenario must use the current deal revision.", 409
            )
        hypothetical = deepcopy(parent)
        commands.patch_facts(
            conn,
            context,
            hypothetical,
            body["patches"],
            "deal" if "workspace_id" in parent else "workspace",
        )
        for identifier in body["funding_option_ids"]:
            store.assert_ref(
                conn,
                context["tenant"],
                identifier,
                "funding_option",
                parent["execution_scope"],
            )
        scenario = {
            **meta(context["tenant"], context["actor"], "scenario"),
            "base_revision": body["base_revision"],
            "patches": body["patches"],
            "funding_option_ids": body["funding_option_ids"],
            "assumption_ids": [],
            "status": "hypothetical",
        }
        save(
            conn,
            context["tenant"],
            "scenario",
            scenario,
            parent=parent["id"],
            dataset=parent["dataset_id"],
        )
        payload["scenario_id"] = scenario["id"]
    if operation == "uploadDocuments":
        import sqlalchemy as sa
        from packages.adapters.extraction_cache import lookup

        documents = []
        for filename, media, content in context.get("uploads", []):
            content_hash = storage.store_bytes(content, media)
            prior = next(
                (
                    r
                    for r in commands.children(
                        conn, context["tenant"], "document", parent
                    )
                    if r["content_hash"] == content_hash
                ),
                None,
            )
            if prior:
                documents.append(prior)
                continue
            row = {
                **meta(context["tenant"], context["actor"], "document"),
                "workspace_id": parent.get("workspace_id", parent["id"]),
                "role": body["document_role"],
                "filename": filename.replace("\\", "/").split("/")[-1][:200],
                "media_type": media,
                "size_bytes": len(content),
                "content_hash": content_hash,
                "state": "queued",
                "evidence_ids": [],
            }
            save(
                conn,
                context["tenant"],
                "document",
                row,
                parent=parent["id"],
                dataset=parent["dataset_id"],
            )
            documents.append(row)
        payload["document_ids"] = list(
            dict.fromkeys(r["id"] for r in documents if r["state"] == "queued")
        )
        active_jobs = (
            conn.execute(
                sa.select(store.jobs).where(
                    store.jobs.c.tenant_id == context["tenant"],
                    store.jobs.c.state.in_(["queued", "running"]),
                    store.jobs.c.cancelled.is_(False),
                )
            )
            .mappings()
            .all()
        )
        existing = None
        for active in active_jobs:
            if active["payload"]["parent_id"] != parent["id"]:
                continue
            overlap = set(active["payload"]["body"].get("document_ids", [])) & set(
                payload["document_ids"]
            )
            if overlap:
                existing = active
                payload["document_ids"] = [
                    i for i in payload["document_ids"] if i not in overlap
                ]
        if existing and not payload["document_ids"]:
            run = get(conn, context["tenant"], "run", existing["id"])
            return env(
                context,
                {
                    "documents": documents,
                    "job": {"run": run, "poll_url": "/v2/runs/" + run["id"]},
                },
                parent,
                "accepted",
            )
        by_id = {r["id"]: r for r in documents}
        payload["expected_pages"] = sum(
            1
            for identifier in payload["document_ids"]
            if not lookup(
                conn,
                context["tenant"],
                by_id[identifier]["content_hash"],
                parent["execution_scope"],
            )
        )
        admission = commands.admission(conn, context, False, payload["expected_pages"])
        if not admission["admitted"]:
            raise DomainError("PAGE_ALLOWANCE_EXHAUSTED", admission["reason"], 429)
    if operation == "discoverFinanceOptions":
        from services.api.handlers import verify_parent

        selected_analysis = verify_parent(
            conn, context, "analysis", body["analysis_id"], parent
        )
        if not commands.analysis_view(
            conn, context["tenant"], parent, selected_analysis
        )["current_for_use"]:
            raise DomainError(
                "STALE_ANALYSIS",
                "Recalculate current inputs before screening products.",
                409,
            )
        commands.validate_embedded_evidence(
            conn, context["tenant"], parent, body["company"]
        )
        if body.get("invoice_id") and body["invoice_id"] not in {
            invoice["id"]
            for invoice in parent["invoices"]
            if invoice["side"] == "buyer"
        }:
            raise DomainError(
                "FINANCED_INVOICE_REFERENCE", "Select a declared buyer invoice."
            )
        if body["company"]["seller_party_id"] not in {
            p["id"] for p in parent["parties"] if "seller" in p["roles"]
        }:
            raise DomainError(
                "SELLER_REFERENCE", "Company must identify the declared seller."
            )
    if operation == "prepareFinancePack":
        from services.api.handlers import verify_parent

        for name, resource in [
            ("scenario_id", "scenario"),
            ("funding_option_id", "funding_option"),
        ]:
            verify_parent(conn, context, resource, body[name], parent)
        commands.evidence_refs(conn, context["tenant"], parent, body["evidence_ids"])
    if operation == "generateDraft":
        for name, resource in [
            ("scenario_id", "scenario"),
            ("analysis_id", "analysis"),
        ]:
            from services.api.handlers import verify_parent

            verify_parent(conn, context, resource, body[name], parent)
        if body["recipient_party_id"] and body["recipient_party_id"] not in {
            p["id"] for p in parent["parties"]
        }:
            raise DomainError(
                "RECIPIENT_UNKNOWN", "Recipient must be a declared deal party."
            )
    job = commands.enqueue(conn, context, parent, kind, payload)
    if operation in {"createScenario", "createSandboxScenario"}:
        return env(context, {"scenario": scenario, "job": job}, parent, "accepted")
    if operation == "uploadDocuments":
        return env(context, {"documents": documents, "job": job}, parent, "accepted")
    return env(context, job, parent, "accepted")
