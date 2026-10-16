"""Canonical-contract HTTP boundary over transactional application services."""

from copy import deepcopy
import json, logging, traceback
import sqlalchemy as sa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from jsonschema import ValidationError
from services.api import auth, store, commands, storage
from services.api.settings import settings
from services.api.store import DomainError, uid, digest, get, save, meta, issue
from packages.contracts.runtime import (
    DOCUMENT,
    OPERATIONS,
    validate_request,
    validate_response,
)
from scripts.validate_contract import resolve

app = FastAPI(title="Fincathon", openapi_url=None, docs_url=None, redoc_url=None)
logger = logging.getLogger("fincathon.api")


@app.get("/openapi.json")
def openapi_document():
    return DOCUMENT


@app.get("/health")
def health():
    with store.engine.connect() as conn:
        conn.execute(sa.text("select 1"))
    from services.worker.liveness import ready

    worker_ready = ready()
    return JSONResponse(
        {
            "status": "ready" if worker_ready else "not_ready",
            "database": "postgresql",
            "worker": "ready" if worker_ready else "missing_or_stale",
            "mode": settings.mode,
        },
        status_code=200 if worker_ready else 503,
    )


def envelope(
    context,
    result,
    parent=None,
    status="completed",
    blockers=None,
    warnings=None,
    refs=None,
):
    return {
        "request_id": context["request_id"],
        "workspace_id": parent.get("workspace_id", parent["id"])
        if parent and "revision" in parent
        else None,
        "revision": parent.get("revision") if parent else None,
        "status": status,
        "output_refs": refs or [],
        "blockers": blockers or [],
        "warnings": warnings or [],
        "result": result,
    }


def error_response(error, request_id):
    return {
        "request_id": request_id,
        "code": error.code,
        "message": error.reason,
        "issues": [issue(error.code, error.reason, error.field, error.action)],
        "current_revision": error.current_revision,
        "retry_after_seconds": None,
    }


def context_for(conn, request, operation, request_id):
    context = auth.authenticate(conn, request.headers.get("authorization"))
    context.update(
        actor=context["user"]["id"],
        request_id=request_id,
        scope="demo" if settings.demo else "real",
        dataset=None,
    )
    if operation not in {
        "getSession",
        "logout",
        "selectOrganization",
        "createOrganization",
    }:
        auth.require_role(context, OPERATIONS[operation][2]["x-required-roles"])
        if not context["tenant"]:
            raise DomainError("ORGANIZATION_REQUIRED", "Select an organization.", 403)
    return context


def collection_response(conn, context, parent, kind, request):
    try:
        limit = int(request.query_params.get("limit", "25"))
    except ValueError:
        raise DomainError("INVALID_LIMIT", "Page size must be an integer.", 400)
    if not 1 <= limit <= 100:
        raise DomainError("INVALID_LIMIT", "Page size must be between 1 and 100.", 400)
    if parent and "workspace_id" in parent:
        rows = commands.children(conn, context["tenant"], kind, parent)
        rows = sorted(rows, key=lambda r: r["id"])
        cursor = request.query_params.get("cursor")
        if cursor:
            rows = [r for r in rows if r["id"] > cursor]
        page = {
            "items": rows[:limit],
            "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None,
        }
    else:
        page = store.list_records(
            conn,
            context["tenant"],
            kind,
            parent["id"] if parent else None,
            limit,
            request.query_params.get("cursor"),
        )
    if kind == "milestone" and parent:
        from packages.domain.dates import project

        milestones = {
            row["id"]: row
            for row in commands.children(conn, context["tenant"], "milestone", parent)
        }
        calendars = {
            row["id"]: row
            for row in commands.all_records(
                conn, context["tenant"], "business_calendar"
            )
        }
        for row in page["items"]:
            try:
                row.update(
                    resolved_forecast=project(row["id"], milestones, calendars),
                    resolution_issues=[],
                )
            except DomainError as error:
                row.update(
                    resolved_forecast=None,
                    resolution_issues=[issue(error.code, error.reason)],
                )
    if kind == "analysis" and parent:
        from packages.domain.comparison import rank_views

        views = rank_views(
            [
                commands.analysis_view(conn, context["tenant"], parent, row)
                for row in commands.children(
                    conn, context["tenant"], "analysis", parent
                )
            ]
        )
        by_id = {row["id"]: row for row in views}
        page["items"] = [by_id[row["id"]] for row in page["items"]]
    return envelope(context, page, parent)


def _auth_entry(conn, request, operation, body, request_id):
    from migrations.schema_v2 import auth_commands
    from services.api.secrets import cipher

    if operation == "getDemoIdentities":
        rows = (
            conn.execute(
                sa.select(store.users).where(
                    store.users.c.dataset_id.is_not(None),
                    store.users.c.active.is_(True),
                )
            )
            .mappings()
            .all()
            if settings.demo
            else []
        )
        return envelope(
            {"request_id": request_id},
            {"enabled": settings.demo, "users": [auth.public_user(r) for r in rows]},
        )
    if operation == "login":
        user = auth.verify_credentials(conn, body["email"], body["password"])
    else:
        if not settings.demo:
            raise DomainError("DEMO_DISABLED", "Demo entry is disabled.", 404)
        user = (
            conn.execute(
                sa.select(store.users).where(
                    store.users.c.id == body["user_id"],
                    store.users.c.dataset_id.is_not(None),
                    store.users.c.active.is_(True),
                )
            )
            .mappings()
            .first()
        )
        if not user:
            raise DomainError(
                "AUTHENTICATION_FAILED", "Demo identity unavailable.", 401
            )
    conn.execute(
        sa.select(store.users.c.id)
        .where(store.users.c.id == user["id"])
        .with_for_update()
    )
    key = request.headers["idempotency-key"]
    query = sa.select(auth_commands).where(
        auth_commands.c.actor_id == user["id"],
        auth_commands.c.operation == operation,
        auth_commands.c.key == key,
    )
    previous = conn.execute(query).mappings().first()
    from services.api.secrets import request_digest

    request_hash = request_digest(store.normalized(body))
    if previous:
        if previous["request_hash"] != request_hash:
            raise DomainError(
                "IDEMPOTENCY_CONFLICT",
                "Idempotency key was reused with changed input.",
                409,
            )
        return json.loads(cipher().decrypt(previous["receipt"].encode()))
    result = auth.create_session(conn, user, body.get("organization_id"))
    response = envelope({"request_id": request_id}, result)
    validate_response(operation, 200, response)
    conn.execute(
        auth_commands.insert().values(
            actor_id=user["id"],
            operation=operation,
            key=key,
            request_hash=request_hash,
            receipt=cipher().encrypt(json.dumps(response).encode()).decode(),
        )
    )
    return response


async def endpoint(request: Request):
    operation = request.scope["route"].name
    op = OPERATIONS[operation][2]
    request_id = uid("request")
    status = next(int(c) for c in op["responses"] if c.startswith("2"))
    try:
        body = {}
        uploads = []
        if request.method != "GET":
            key = request.headers.get("idempotency-key", "")
            if not 1 <= len(key) <= 200:
                raise DomainError(
                    "IDEMPOTENCY_REQUIRED", "Idempotency-Key header is required.", 400
                )
        if "requestBody" in op:
            content = op["requestBody"]["content"]
            media = next(iter(content))
            total = 0
            chunks = []
            async for chunk in request.stream():
                total += len(chunk)
                if total > 16 * 1024 * 1024:
                    raise DomainError(
                        "REQUEST_TOO_LARGE", "Request exceeds 16 MiB.", 413
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
            if media == "multipart/form-data":
                form = await request.form(
                    max_files=8, max_fields=8, max_part_size=settings.max_upload_bytes
                )
                uploads = form.getlist("files")
                try:
                    revision = int(form.get("expected_revision", "0"))
                except ValueError:
                    raise DomainError(
                        "INVALID_REVISION", "expected_revision must be an integer.", 400
                    )
                body = {
                    "expected_revision": revision,
                    "document_role": form.get("document_role"),
                    "files": [f.filename for f in uploads],
                }
            else:
                if not request.headers.get("content-type", "").startswith(
                    "application/json"
                ):
                    raise DomainError("UNSUPPORTED_MEDIA", "Use application/json.", 415)
                try:
                    body = json.loads(request._body)
                except (ValueError, UnicodeDecodeError):
                    raise DomainError(
                        "MALFORMED_REQUEST", "Request body is not valid JSON.", 400
                    )
            try:
                validate_request(operation, body, media)
            except ValidationError as error:
                raise DomainError(
                    "INVALID_INPUT",
                    error.message,
                    422,
                    "/" + "/".join(str(p) for p in error.absolute_path),
                )
        from packages.domain.context_values import validate as validate_context

        validate_context(body)
        with store.engine.begin() as conn:
            if op.get("x-public-auth"):
                response = _auth_entry(conn, request, operation, body, request_id)
            else:
                context = context_for(conn, request, operation, request_id)
                parent = None
                parent_kind = None
                scope = op["x-revision-scope"]
                path = OPERATIONS[operation][0]
                if "/workspaces/{id}" in path:
                    parent_kind = "workspace"
                elif "/deals/{id}" in path:
                    parent_kind = "deal"
                if parent_kind:
                    parent = get(
                        conn, context["tenant"], parent_kind, request.path_params["id"]
                    )
                    if (
                        request.method != "GET"
                        and parent["execution_scope"] == "demo"
                        and not settings.demo
                        and operation not in {"archiveWorkspace", "archiveDeal"}
                    ):
                        raise DomainError(
                            "DEMO_DISABLED",
                            "Historical demo records are readable, but demo commands require explicit demo mode.",
                            403,
                        )
                    context.update(
                        scope=parent["execution_scope"], dataset=parent["dataset_id"]
                    )
                if request.method == "GET":
                    response = read_operation(conn, context, operation, parent, request)
                else:
                    # Organization row serializes replay, shared cash and concurrent revision mutations.
                    if not context["tenant"]:
                        response = write_operation(
                            conn, context, operation, parent, body, request
                        )
                    else:
                        conn.execute(
                            sa.select(store.organizations.c.id)
                            .where(store.organizations.c.id == context["tenant"])
                            .with_for_update()
                        )
                        if parent_kind:
                            parent = get(
                                conn, context["tenant"], parent_kind, parent["id"]
                            )
                        where = (
                            store.commands.c.tenant_id == context["tenant"],
                            store.commands.c.actor_id == context["actor"],
                            store.commands.c.operation == operation,
                            store.commands.c.key == request.headers["idempotency-key"],
                        )
                        upload_hashes = []
                        if uploads:
                            context["uploads"] = []
                            import hashlib

                            for upload in uploads:
                                content = await upload.read(
                                    settings.max_upload_bytes + 1
                                )
                                context["uploads"].append(
                                    (upload.filename, upload.content_type, content)
                                )
                                upload_hashes.append(
                                    {
                                        "filename": upload.filename,
                                        "media_type": upload.content_type,
                                        "hash": hashlib.sha256(content).hexdigest(),
                                    }
                                )
                        previous = (
                            conn.execute(sa.select(store.commands).where(*where))
                            .mappings()
                            .first()
                        )
                        request_hash = digest(
                            {
                                "body": body,
                                "path": dict(request.path_params),
                                "uploads": upload_hashes,
                            }
                        )
                        if previous:
                            if previous["request_hash"] != request_hash:
                                raise DomainError(
                                    "IDEMPOTENCY_CONFLICT",
                                    "Idempotency key was reused with changed input.",
                                    409,
                                )
                            response = previous["response"]
                            status = previous["status"]
                        else:
                            if (
                                parent
                                and parent.get("archived")
                                and operation not in {"archiveWorkspace", "archiveDeal"}
                            ):
                                raise DomainError(
                                    "ARCHIVED_READ_ONLY",
                                    "Unarchive this workspace before changing its retained records.",
                                    409,
                                )
                            if (
                                scope in {"workspace", "deal"}
                                and body["expected_revision"] != parent["revision"]
                            ):
                                raise DomainError(
                                    "STALE_REVISION",
                                    "Expected revision does not match current revision.",
                                    409,
                                    current_revision=parent["revision"],
                                )
                            before = deepcopy(parent)
                            response = write_operation(
                                conn, context, operation, parent, body, request
                            )
                            if parent_kind:
                                parent["revision"] += 1
                                parent["snapshot_hash"] = commands.current_fact_hash(
                                    conn, context["tenant"], parent
                                )
                                if parent_kind == "deal":
                                    commands.derive_states(conn, context, parent)
                                save(
                                    conn,
                                    context["tenant"],
                                    parent_kind,
                                    parent,
                                    parent=parent.get("workspace_id"),
                                    dataset=parent["dataset_id"],
                                    snapshot=True,
                                )
                                if parent_kind == "workspace":
                                    commands.invalidate_workspace_dependents(
                                        conn, context, parent
                                    )
                                if operation != "convertToDeal":
                                    response["revision"] = parent["revision"]
                                if operation in {
                                    "patchWorkspaceFacts",
                                    "estimateSandbox",
                                    "archiveWorkspace",
                                }:
                                    response["result"] = deepcopy(parent)
                                elif operation in {"patchDealFacts", "archiveDeal"}:
                                    response["result"]["deal"] = deepcopy(parent)
                            if operation == "closeDeal":
                                response["result"]["deal"] = deepcopy(parent)
                            validate_response(operation, status, response)
                            store_value = {k: v for k, v in response.items()}
                            conn.execute(
                                store.commands.insert().values(
                                    tenant_id=context["tenant"],
                                    actor_id=context["actor"],
                                    operation=operation,
                                    key=request.headers["idempotency-key"],
                                    request_hash=request_hash,
                                    status=status,
                                    response=store_value,
                                )
                            )
                            commands.audit(
                                conn,
                                context,
                                operation,
                                before,
                                parent,
                                parent["id"] if parent else None,
                            )
            if isinstance(response, Response):
                return response
            validate_response(operation, status, response)
        return JSONResponse(
            response,
            status_code=status,
            headers={"X-Request-ID": response["request_id"]},
        )
    except DomainError as error:
        return JSONResponse(
            error_response(error, request_id),
            status_code=error.status,
            headers={"X-Request-ID": request_id},
        )
    except Exception as error:
        logger.error(
            "operation=%s request=%s exception=%s frames=%s",
            operation,
            request_id,
            type(error).__name__,
            [(f.filename, f.lineno) for f in traceback.extract_tb(error.__traceback__)][
                -5:
            ],
        )
        failure = DomainError(
            "INTERNAL_ERROR", "The operation could not produce a valid response.", 500
        )
        return JSONResponse(
            error_response(failure, request_id),
            status_code=500,
            headers={"X-Request-ID": request_id},
        )


# Implementations are separated from the HTTP boundary so workers/seeds call services.
from services.api.handlers import read_operation, write_operation

for operation, (path, method, definition) in OPERATIONS.items():
    app.add_api_route(path, endpoint, methods=[method.upper()], name=operation)
