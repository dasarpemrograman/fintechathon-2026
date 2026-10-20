"""Optional one-way Calendar projection. Offline events never call Google."""

from datetime import timedelta, date, datetime
import json, os
from urllib.parse import urlencode, quote
import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from migrations.schema_v3 import connector_credentials, oauth_states, calendar_events
from services.api import store, commands
from services.api.store import DomainError, meta, save, get, digest, uid, now, issue
from services.api.secrets import cipher
from services.api.settings import settings


def access_token(conn, tenant, identifier):
    encrypted = conn.execute(
        sa.select(connector_credentials.c.ciphertext)
        .where(
            connector_credentials.c.tenant_id == tenant,
            connector_credentials.c.connection_id == identifier,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not encrypted:
        raise DomainError(
            "CALENDAR_REVOKED", "Calendar credential has been revoked.", 409
        )
    tokens = json.loads(cipher().decrypt(encrypted.encode()))
    expiry = (
        datetime.fromisoformat(tokens["expires_at"])
        if tokens.get("expires_at")
        else None
    )
    if expiry and expiry > now() + timedelta(seconds=60):
        return tokens["access_token"]
    if (
        not tokens.get("refresh_token")
        or not os.environ.get("GOOGLE_CLIENT_ID")
        or not os.environ.get("GOOGLE_CLIENT_SECRET")
    ):
        raise DomainError(
            "CALENDAR_REAUTHORIZATION_REQUIRED",
            "Calendar authorization expired; reconnect the account.",
            503,
        )
    with httpx.Client(timeout=15, trust_env=True, follow_redirects=False) as client:
        response = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            },
        )
    if response.status_code != 200:
        raise DomainError(
            "CALENDAR_REFRESH_FAILED",
            "Calendar token refresh was rejected; reconnect if authorization has been revoked.",
            503,
        )
    refreshed = response.json()
    if (
        not refreshed.get("access_token")
        or not isinstance(refreshed.get("expires_in"), int)
        or refreshed["expires_in"] <= 0
    ):
        raise DomainError(
            "CALENDAR_REFRESH_INVALID",
            "Provider returned an invalid token lifetime.",
            503,
        )
    tokens.update(
        refreshed,
        expires_at=(now() + timedelta(seconds=refreshed["expires_in"])).isoformat(),
    )
    conn.execute(
        connector_credentials.update()
        .where(
            connector_credentials.c.tenant_id == tenant,
            connector_credentials.c.connection_id == identifier,
        )
        .values(ciphertext=cipher().encrypt(json.dumps(tokens).encode()).decode())
    )
    return tokens["access_token"]


def connected(conn, tenant, identifier):
    row = get(conn, tenant, "calendar_connection", identifier)
    if row["status"] != "connected" or not row["calendar_id"]:
        raise DomainError(
            "CALENDAR_NOT_CONNECTED", "Select an active Calendar connection.", 409
        )
    return row


def projection(conn, context, parent, body):
    connection = connected(conn, context["tenant"], body["connection_id"])
    if (
        parent["execution_scope"] == "real"
        and connection["data_mode"] == "synthetic_demo"
    ):
        raise DomainError(
            "SYNTHETIC_REFERENCE",
            "Synthetic Calendar cannot be used by a real transaction.",
        )
    milestones = {
        m["id"]: m
        for m in commands.children(conn, context["tenant"], "milestone", parent)
    }
    events = []
    for identifier in body["milestone_ids"]:
        if identifier not in milestones:
            raise DomainError(
                "MILESTONE_REFERENCE", "Selected milestone is not part of this deal."
            )
        m = milestones[identifier]
        value = m["actual"] or m["forecast"] or m["agreed"] or m["proposed"]
        if value is None:
            from packages.domain.dates import project

            value = project(
                identifier,
                milestones,
                {
                    row["id"]: row
                    for row in commands.all_records(
                        conn, context["tenant"], "business_calendar"
                    )
                },
            )
        events.append(
            {
                "milestone_id": identifier,
                "title": "Export milestone: " + m["kind"].replace("_", " "),
                "date": value,
                "action": body["action"],
            }
        )
    value = {
        "deal_id": parent["id"],
        "connection_id": connection["id"],
        "calendar_id": connection["calendar_id"],
        "fact_hash": commands.fact_hash(parent),
        "events": events,
    }
    return events, digest(value)


def calendar_command(conn, context, operation, parent, body, request=None):
    from services.api.handlers import env

    tenant = context["tenant"]
    actor = context["actor"]
    if operation == "connectCalendar":
        expected = os.environ.get("GOOGLE_REDIRECT_URI")
        if not settings.demo and (
            not os.environ.get("GOOGLE_CLIENT_ID")
            or not os.environ.get("GOOGLE_CLIENT_SECRET")
            or body["redirect_uri"] != expected
        ):
            raise DomainError(
                "CALENDAR_DISABLED",
                "Configure the registered Google redirect URI and OAuth credentials before connecting.",
                503,
            )
        row = {
            **meta(tenant, actor, "calendar_connection"),
            "provider": "google",
            "calendar_id": None,
            "status": "pending",
            "data_mode": "synthetic_demo" if settings.demo else "live",
        }
        save(conn, tenant, "calendar_connection", row, dataset=context.get("dataset"))
        state = uid("oauth")
        conn.execute(
            oauth_states.insert().values(
                state=state,
                tenant_id=tenant,
                actor_id=actor,
                connection_id=row["id"],
                redirect_uri=body["redirect_uri"],
                expires_at=now() + timedelta(minutes=10),
                consumed=False,
            )
        )
        url = (
            "https://offline-calendar.example.test/authorize?state=" + state
            if settings.demo
            else "https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode(
                {
                    "client_id": os.environ["GOOGLE_CLIENT_ID"],
                    "redirect_uri": body["redirect_uri"],
                    "response_type": "code",
                    "scope": "https://www.googleapis.com/auth/calendar.events.owned",
                    "access_type": "offline",
                    "state": state,
                    "prompt": "consent",
                }
            )
        )
        return env(context, {"authorization_url": url, "state": state})
    if operation == "calendarCallback":
        state = (
            conn.execute(
                sa.select(oauth_states)
                .where(
                    oauth_states.c.state == body["state"],
                    oauth_states.c.tenant_id == tenant,
                    oauth_states.c.actor_id == actor,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if not state or state["consumed"] or state["expires_at"] <= now():
            raise DomainError(
                "OAUTH_STATE_INVALID",
                "OAuth state is absent, expired, consumed or belongs to another actor.",
                409,
            )
        row = get(conn, tenant, "calendar_connection", state["connection_id"])
        if row["data_mode"] == "synthetic_demo":
            if not settings.demo or body["code"] != "offline-demo":
                raise DomainError(
                    "DEMO_OAUTH_CODE", "Use the explicit offline Calendar fixture code."
                )
            tokens = {"fixture": True}
        else:
            with httpx.Client(timeout=15, trust_env=True) as client:
                r = client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": body["code"],
                        "client_id": os.environ["GOOGLE_CLIENT_ID"],
                        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                        "redirect_uri": state["redirect_uri"],
                        "grant_type": "authorization_code",
                    },
                )
            if r.status_code != 200:
                raise DomainError(
                    "OAUTH_EXCHANGE_FAILED",
                    "Google rejected the authorization exchange.",
                    503,
                )
            tokens = r.json()
            if not tokens.get("access_token"):
                raise DomainError(
                    "OAUTH_TOKEN_MISSING",
                    "Provider did not return a usable access token.",
                    503,
                )
        if row["data_mode"] != "synthetic_demo":
            lifetime = tokens.get("expires_in")
            if not isinstance(lifetime, int) or lifetime <= 0:
                raise DomainError(
                    "OAUTH_LIFETIME_INVALID",
                    "Provider did not return a valid token lifetime.",
                    503,
                )
            tokens["expires_at"] = (now() + timedelta(seconds=lifetime)).isoformat()
        conn.execute(
            insert(connector_credentials)
            .values(
                tenant_id=tenant,
                connection_id=row["id"],
                ciphertext=cipher().encrypt(json.dumps(tokens).encode()).decode(),
            )
            .on_conflict_do_update(
                index_elements=["tenant_id", "connection_id"],
                set_={
                    "ciphertext": cipher().encrypt(json.dumps(tokens).encode()).decode()
                },
            )
        )
        conn.execute(
            oauth_states.update()
            .where(oauth_states.c.state == state["state"])
            .values(consumed=True)
        )
        row["status"] = "connected"
        save(conn, tenant, "calendar_connection", row)
        return env(context, row)
    if operation in {"selectCalendar", "revokeCalendar"}:
        row = get(conn, tenant, "calendar_connection", request.path_params["id"])
        if operation == "selectCalendar":
            if row["status"] != "connected":
                raise DomainError(
                    "CALENDAR_NOT_CONNECTED",
                    "Complete authorization before selection.",
                    409,
                )
            if (
                row["data_mode"] == "synthetic_demo"
                and body["calendar_id"] != "synthetic-local"
            ):
                raise DomainError(
                    "DEMO_CALENDAR_ONLY", "Offline selection is synthetic-local."
                )
            if (
                row["calendar_id"]
                and row["calendar_id"] != body["calendar_id"]
                and conn.execute(
                    sa.select(calendar_events.c.milestone_id)
                    .where(
                        calendar_events.c.tenant_id == tenant,
                        calendar_events.c.connection_id == row["id"],
                    )
                    .limit(1)
                ).first()
            ):
                raise DomainError(
                    "CALENDAR_SELECTION_LOCKED",
                    "Create another connection to change calendars after owned events have been recorded.",
                    409,
                )
            row["calendar_id"] = body["calendar_id"]
        else:
            row["status"] = "revoked"
            conn.execute(
                oauth_states.update()
                .where(
                    oauth_states.c.tenant_id == tenant,
                    oauth_states.c.connection_id == row["id"],
                )
                .values(consumed=True)
            )
            encrypted = conn.execute(
                sa.select(connector_credentials.c.ciphertext).where(
                    connector_credentials.c.tenant_id == tenant,
                    connector_credentials.c.connection_id == row["id"],
                )
            ).scalar_one_or_none()
            revoke_warning = None
            if row["data_mode"] != "synthetic_demo" and encrypted:
                tokens = json.loads(cipher().decrypt(encrypted.encode()))
                token = tokens.get("refresh_token") or tokens.get("access_token")
                try:
                    with httpx.Client(
                        timeout=10, trust_env=True, follow_redirects=False
                    ) as client:
                        revoked = client.post(
                            "https://oauth2.googleapis.com/revoke",
                            data={"token": token},
                        )
                    if revoked.status_code not in {200, 400}:
                        revoke_warning = issue(
                            "REMOTE_REVOCATION_UNCONFIRMED",
                            "Local access was removed. Review the Google account grant because remote revocation was not confirmed.",
                        )
                except httpx.HTTPError:
                    revoke_warning = issue(
                        "REMOTE_REVOCATION_UNCONFIRMED",
                        "Local access was removed. Review the Google account grant because remote revocation was unavailable.",
                    )
            conn.execute(
                connector_credentials.delete().where(
                    connector_credentials.c.tenant_id == tenant,
                    connector_credentials.c.connection_id == row["id"],
                )
            )
        save(conn, tenant, "calendar_connection", row)
        return env(
            context,
            row,
            warnings=[revoke_warning]
            if operation == "revokeCalendar" and revoke_warning
            else [],
        )
    if operation == "previewCalendar":
        events, projection_hash = projection(conn, context, parent, body)
        row = {
            **meta(tenant, actor, "calendar_preview"),
            "deal_id": parent["id"],
            "connection_id": body["connection_id"],
            "projection_hash": projection_hash,
            "events": events,
            "revision": parent["revision"],
        }
        save(
            conn,
            tenant,
            "calendar_preview",
            row,
            parent=parent["id"],
            dataset=parent["dataset_id"],
        )
        return env(context, row, parent)
    if operation == "resolveCalendarConflict":
        connected(conn, tenant, body["connection_id"])
        where = (
            calendar_events.c.tenant_id == tenant,
            calendar_events.c.connection_id == body["connection_id"],
            calendar_events.c.milestone_id == body["milestone_id"],
        )
        row = conn.execute(sa.select(calendar_events).where(*where)).mappings().first()
        if not row or row["state"] != "conflict":
            raise DomainError(
                "CALENDAR_CONFLICT_REQUIRED",
                "No recorded conflict exists for this owned event.",
                409,
            )
        conn.execute(
            calendar_events.update()
            .where(*where)
            .values(
                state="external_retained"
                if body["decision"] == "keep_external"
                else "approval_required",
                projection_hash=None,
                provider_data={**row["provider_data"], "_resolved_at": store.instant()},
            )
        )
        return env(
            context,
            {
                "message": "External version retained."
                if body["decision"] == "keep_external"
                else "Create and approve a new projection before retrying."
            },
            parent,
        )
    raise DomainError("CALENDAR_OPERATION", "Unsupported Calendar command.")


def process_calendar(work):
    from packages.adapters.calendar_policy import require_live_sync

    context = {"tenant": work.tenant, "actor": work.actor}
    connection = connected(work.conn, work.tenant, work.body["connection_id"])
    require_live_sync(connection["data_mode"])
    events, projection_hash = projection(work.conn, context, work.parent, work.body)
    if projection_hash != work.body["approved_projection_hash"]:
        raise DomainError(
            "STALE_CALENDAR_APPROVAL",
            "Projection changed after review; preview and approve again.",
            409,
        )
    approvals = commands.children(work.conn, work.tenant, "approval", work.parent)
    approved = [
        a
        for a in approvals
        if a["purpose"] == "calendar_write"
        and a["decision"] == "approved"
        and a["analysis_hash"] == projection_hash
    ]
    if not approved:
        raise DomainError(
            "CALENDAR_APPROVAL_REQUIRED",
            "Record a scoped Calendar-write approval for this projection hash.",
            409,
        )
    approval = approved[-1]
    for event in events:
        existing = (
            work.conn.execute(
                sa.select(calendar_events).where(
                    calendar_events.c.tenant_id == work.tenant,
                    calendar_events.c.connection_id == work.body["connection_id"],
                    calendar_events.c.milestone_id == event["milestone_id"],
                )
            )
            .mappings()
            .first()
        )
        if (
            existing
            and existing["state"] == "approval_required"
            and approval["created_at"]
            <= existing["provider_data"].get("_resolved_at", "")
        ):
            raise DomainError(
                "CALENDAR_REAPPROVAL_REQUIRED",
                "Record a new approval after resolving the external conflict.",
                409,
            )
        effect = digest(
            {
                "tenant": work.tenant,
                "connection": work.body["connection_id"],
                "milestone": event["milestone_id"],
                "action": event["action"],
                "projection": projection_hash,
                "approval": approval["id"],
            }
        )
        payload = {
            "tenant_id": work.tenant,
            "connection_id": work.body["connection_id"],
            "deal_id": work.parent["id"],
            "projection_hash": projection_hash,
            "event": event,
        }
        work.conn.execute(
            insert(store.outbox)
            .values(
                tenant_id=work.tenant,
                id="effect_" + effect[:24],
                effect_key=effect,
                payload=payload,
                state="pending",
                receipt=None,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "effect_key"])
        )
    work.warnings.append(
        issue(
            "CALENDAR_OUTBOX_PENDING",
            "Approved projection is queued. Check the outbox receipt before claiming provider delivery.",
        )
    )


def google_event(event, event_id, owned_key):
    value = event["date"]
    result = {
        "id": event_id,
        "summary": event["title"],
        "visibility": "private",
        "transparency": "transparent",
        "reminders": {"useDefault": False},
        "extendedProperties": {"private": {"allexport_owner": owned_key}},
    }
    if "date" in value:
        from datetime import date, timedelta

        result.update(
            start={"date": value["date"]},
            end={
                "date": (
                    date.fromisoformat(value["date"]) + timedelta(days=1)
                ).isoformat()
            },
        )
    else:
        from datetime import datetime, timedelta

        at = datetime.fromisoformat(value["instant"].replace("Z", "+00:00"))
        result.update(
            start={"dateTime": at.isoformat(), "timeZone": value["timezone"]},
            end={
                "dateTime": (at + timedelta(minutes=15)).isoformat(),
                "timeZone": value["timezone"],
            },
        )
    return result


def event_matches(remote, expected):
    """Compare managed fields while accepting Google's equivalent UTC offsets."""
    from datetime import datetime

    def same_time(actual, wanted):
        if "date" in wanted:
            return actual.get("date") == wanted["date"] and "dateTime" not in actual
        try:
            left = datetime.fromisoformat(actual["dateTime"].replace("Z", "+00:00"))
            right = datetime.fromisoformat(wanted["dateTime"].replace("Z", "+00:00"))
            return (
                left.utcoffset() is not None
                and right.utcoffset() is not None
                and left == right
                and actual.get("timeZone") == wanted.get("timeZone")
            )
        except (KeyError, TypeError, ValueError):
            return False

    return (
        remote.get("summary") == expected["summary"]
        and same_time(remote.get("start", {}), expected["start"])
        and same_time(remote.get("end", {}), expected["end"])
        and remote.get("extendedProperties") == expected["extendedProperties"]
        and remote.get("visibility") == expected["visibility"]
        and remote.get("transparency") == expected["transparency"]
        and remote.get("reminders", {}).get("useDefault") is False
        and not remote.get("reminders", {}).get("overrides")
    )


def deliver_effect(conn, row):
    from packages.adapters.calendar_policy import require_live_sync

    p = row["payload"]
    tenant = p["tenant_id"]
    connection = connected(conn, tenant, p["connection_id"])
    require_live_sync(connection["data_mode"])
    event = p["event"]
    owned_key = digest(
        {
            "tenant": tenant,
            "connection": connection["id"],
            "milestone": event["milestone_id"],
        }
    )
    event_id = owned_key
    where = (
        calendar_events.c.tenant_id == tenant,
        calendar_events.c.connection_id == connection["id"],
        calendar_events.c.milestone_id == event["milestone_id"],
    )
    prior = conn.execute(sa.select(calendar_events).where(*where)).mappings().first()
    payload = google_event(event, event_id, owned_key)
    payload["extendedProperties"]["private"]["allexport_projection"] = p[
        "projection_hash"
    ]
    state = "delivered"
    receipt = {
        "provider_id": event_id,
        "data_mode": connection["data_mode"],
        "action": event["action"],
    }
    if connection["data_mode"] == "live":
        receipt["acceptance_reference"] = os.environ[
            "ALLEXPORT_CALENDAR_ACCEPTANCE_REFERENCE"
        ].strip()
    if event["action"] != "insert" and not prior:
        raise DomainError(
            "CALENDAR_EVENT_NOT_OWNED",
            "Updates and deletes require recorded app ownership.",
            409,
        )
    if connection["data_mode"] == "synthetic_demo":
        if not settings.demo:
            raise DomainError(
                "DEMO_DISABLED", "Synthetic delivery is disabled in normal mode."
            )
        if prior and prior["state"] == "conflict":
            state = "conflict"
        receipt["etag"] = '"offline-' + digest(payload)[:16] + '"'
    else:
        headers = {
            "Authorization": "Bearer " + access_token(conn, tenant, connection["id"])
        }
        base = (
            "https://www.googleapis.com/calendar/v3/calendars/"
            + quote(connection["calendar_id"], safe="")
            + "/events"
        )
        with httpx.Client(timeout=15, trust_env=True, follow_redirects=False) as client:
            if event["action"] == "insert":
                response = client.post(
                    base, json=payload, headers=headers, params={"sendUpdates": "none"}
                )
                if response.status_code == 409:
                    response = client.get(base + "/" + event_id, headers=headers)
                    if (
                        response.status_code == 200
                        and response.json()
                        .get("extendedProperties", {})
                        .get("private", {})
                        .get("allexport_owner")
                        != owned_key
                    ):
                        raise DomainError(
                            "CALENDAR_OWNERSHIP_CONFLICT",
                            "Provider event ID is not owned by this projection.",
                            409,
                        )
            else:
                headers["If-Match"] = prior["etag"] or "unmatched"
                if prior["state"] == "approval_required":
                    external = client.get(
                        base + "/" + event_id,
                        headers={"Authorization": headers["Authorization"]},
                    )
                    if (
                        external.status_code != 200
                        or external.json()
                        .get("extendedProperties", {})
                        .get("private", {})
                        .get("allexport_owner")
                        != owned_key
                    ):
                        raise DomainError(
                            "CALENDAR_OWNERSHIP_CONFLICT",
                            "The external event is not app owned.",
                            409,
                        )
                    headers["If-Match"] = (
                        external.headers.get("etag")
                        or external.json().get("etag")
                        or "unmatched"
                    )
                response = (
                    client.delete(
                        base + "/" + event_id,
                        headers=headers,
                        params={"sendUpdates": "none"},
                    )
                    if event["action"] == "delete"
                    else client.patch(
                        base + "/" + event_id,
                        json=payload,
                        headers=headers,
                        params={"sendUpdates": "none"},
                    )
                )
            if response.status_code == 412:
                external = client.get(
                    base + "/" + event_id,
                    headers={"Authorization": headers["Authorization"]},
                )
                if external.status_code == 200 and event_matches(external.json(), payload):
                    response = external
                else:
                    state = "conflict"
            if (
                response.status_code == 200
                and event["action"] == "insert"
                and not event_matches(response.json(), payload)
            ):
                state = "conflict"
            if response.status_code not in (200, 201, 204, 412) and not (
                event["action"] == "delete" and response.status_code in (404, 410)
            ):
                raise DomainError(
                    "CALENDAR_PROVIDER_UNAVAILABLE",
                    "Calendar delivery did not receive a successful provider receipt.",
                    503,
                )
            receipt["etag"] = response.headers.get("etag") or (
                response.json().get("etag")
                if response.content and response.status_code in (200, 201)
                else None
            )
    receipt.update(status=state, delivered=state == "delivered")
    values = {
        "tenant_id": tenant,
        "connection_id": connection["id"],
        "milestone_id": event["milestone_id"],
        "provider_id": event_id,
        "etag": receipt["etag"],
        "projection_hash": p["projection_hash"],
        "state": state
        if state == "conflict"
        else "deleted"
        if event["action"] == "delete"
        else "delivered",
        "provider_data": payload,
    }
    conn.execute(
        insert(calendar_events)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["tenant_id", "connection_id", "milestone_id"],
            set_={
                k: v
                for k, v in values.items()
                if k not in {"tenant_id", "connection_id", "milestone_id"}
            },
        )
    )
    conn.execute(
        store.outbox.update()
        .where(store.outbox.c.tenant_id == tenant, store.outbox.c.id == row["id"])
        .values(state=state, receipt=receipt)
    )
    return receipt


def deliver_once():
    """Stable provider IDs survive a crash; a bounded retry never implies delivery."""
    with store.engine.begin() as conn:
        row = (
            conn.execute(
                sa.select(store.outbox)
                .where(
                    store.outbox.c.state == "pending",
                    store.outbox.c.available_at <= now(),
                )
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        attempts = row["attempts"] + 1
        try:
            result = deliver_effect(conn, row)
            conn.execute(
                store.outbox.update()
                .where(
                    store.outbox.c.tenant_id == row["tenant_id"],
                    store.outbox.c.id == row["id"],
                )
                .values(attempts=attempts, last_error=None)
            )
            return result
        except (DomainError, httpx.HTTPError) as error:
            code = (
                error.code
                if isinstance(error, DomainError)
                else "CALENDAR_NETWORK_UNAVAILABLE"
            )
            retryable = not isinstance(error, DomainError) or error.status == 503
            state = "pending" if retryable and attempts < 3 else "failed"
            conn.execute(
                store.outbox.update()
                .where(
                    store.outbox.c.tenant_id == row["tenant_id"],
                    store.outbox.c.id == row["id"],
                )
                .values(
                    state=state,
                    attempts=attempts,
                    available_at=now() + timedelta(seconds=2**attempts),
                    last_error=code,
                    receipt={"failure_code": code, "delivered": False},
                )
            )
            return {"status": state, "failure_code": code, "delivered": False}
