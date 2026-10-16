"""Local credentials and opaque sessions; demo entry is explicitly gated."""

from datetime import timedelta
import hashlib, secrets
import sqlalchemy as sa
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from services.api.settings import settings
from services.api.store import (
    organizations,
    users,
    memberships,
    sessions,
    now,
    uid,
    DomainError,
)

hasher = PasswordHasher()


def public_user(row):
    return {k: row[k] for k in ("id", "email", "display_name")}


def membership_rows(conn, user_id):
    rows = conn.execute(
        sa.select(memberships, organizations.c.name)
        .join(organizations, organizations.c.id == memberships.c.organization_id)
        .where(memberships.c.user_id == user_id)
    ).mappings()
    return [
        {
            "id": r["id"],
            "organization_id": r["organization_id"],
            "user_id": r["user_id"],
            "organization_name": r["name"],
            "roles": r["roles"],
        }
        for r in rows
    ]


def session_view(conn, record, user):
    return {
        "user": public_user(user),
        "memberships": membership_rows(conn, user["id"]),
        "organization_id": record["organization_id"],
        "expires_at": record["expires_at"].isoformat().replace("+00:00", "Z"),
    }


def create_session(conn, user, organization_id=None):
    available = membership_rows(conn, user["id"])
    if organization_id and not any(
        m["organization_id"] == organization_id for m in available
    ):
        raise DomainError("FORBIDDEN", "Organization membership is required.", 403)
    organization_id = organization_id or (
        available[0]["organization_id"] if available else None
    )
    token = secrets.token_urlsafe(48)
    record = {
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user["id"],
        "organization_id": organization_id,
        "expires_at": now() + timedelta(hours=settings.session_hours),
    }
    conn.execute(sessions.insert().values(**record))
    return {
        "access_token": token,
        "token_type": "bearer",
        "session": session_view(conn, record, user),
    }


def verify_credentials(conn, email, password):
    user = (
        conn.execute(
            sa.select(users).where(
                sa.func.lower(users.c.email) == email.lower(), users.c.active.is_(True)
            )
        )
        .mappings()
        .first()
    )
    try:
        valid = (
            user is not None
            and user["password_hash"]
            and hasher.verify(user["password_hash"], password)
        )
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid:
        raise DomainError("AUTHENTICATION_FAILED", "Invalid credentials.", 401)
    return user


def login(conn, email, password, organization_id=None):
    return create_session(
        conn, verify_credentials(conn, email, password), organization_id
    )


def demo_login(conn, identifier):
    if not settings.demo:
        raise DomainError("DEMO_DISABLED", "Demo entry is disabled.", 404)
    user = (
        conn.execute(
            sa.select(users).where(
                users.c.id == identifier,
                users.c.dataset_id.is_not(None),
                users.c.active.is_(True),
            )
        )
        .mappings()
        .first()
    )
    if not user:
        raise DomainError("AUTHENTICATION_FAILED", "Demo identity unavailable.", 401)
    return create_session(conn, user)


def authenticate(conn, bearer):
    if not bearer or not bearer.startswith("Bearer "):
        raise DomainError(
            "AUTHENTICATION_REQUIRED", "Bearer authentication is required.", 401
        )
    token_hash = hashlib.sha256(bearer[7:].encode()).hexdigest()
    record = (
        conn.execute(
            sa.select(sessions).where(
                sessions.c.token_hash == token_hash, sessions.c.expires_at > now()
            )
        )
        .mappings()
        .first()
    )
    if not record:
        raise DomainError("SESSION_EXPIRED", "Session is invalid or expired.", 401)
    user = (
        conn.execute(
            sa.select(users).where(
                users.c.id == record["user_id"], users.c.active.is_(True)
            )
        )
        .mappings()
        .first()
    )
    if not user or user["dataset_id"] and not settings.demo:
        raise DomainError("SESSION_EXPIRED", "Session is invalid or expired.", 401)
    available = membership_rows(conn, user["id"])
    membership = next(
        (m for m in available if m["organization_id"] == record["organization_id"]),
        None,
    )
    return {
        "user": dict(user),
        "session": dict(record),
        "tenant": record["organization_id"],
        "roles": membership["roles"] if membership else [],
        "view": session_view(conn, record, user),
    }


def require_role(context, roles):
    if roles and not set(context["roles"]).intersection(roles):
        raise DomainError(
            "ROLE_FORBIDDEN", "This action requires another organization role.", 403
        )


def bootstrap(conn, email, password, name, organization):
    if len(password) < 12:
        raise DomainError("WEAK_PASSWORD", "Use at least twelve password characters.")
    identifier = uid("user")
    tenant = uid("org")
    conn.execute(
        users.insert().values(
            id=identifier,
            email=email.lower(),
            display_name=name,
            password_hash=hasher.hash(password),
            active=True,
        )
    )
    conn.execute(
        organizations.insert().values(
            id=tenant,
            name=organization,
            policy={"plan": "team", "runs": 100, "pages": 1000, "active": True},
        )
    )
    conn.execute(
        memberships.insert().values(
            id=uid("membership"),
            organization_id=tenant,
            user_id=identifier,
            roles=["owner"],
        )
    )
    return {"user_id": identifier, "organization_id": tenant}
