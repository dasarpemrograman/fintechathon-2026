"""Operator-controlled live Calendar acceptance, shared by API and delivery."""

import os
from services.api.settings import settings
from services.api.store import DomainError


def live_sync_ready():
    return bool(
        os.environ.get("ALLEXPORT_CALENDAR_LIVE_ENABLED") == "true"
        and os.environ.get("ALLEXPORT_CALENDAR_ACCEPTANCE_REFERENCE", "").strip()
        and all(
            os.environ.get(name)
            for name in (
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "GOOGLE_REDIRECT_URI",
            )
        )
    )


def require_live_sync(data_mode):
    if data_mode == "synthetic_demo":
        if settings.demo:
            return
        raise DomainError(
            "DEMO_DISABLED", "Synthetic Calendar requires demo mode.", 409
        )
    if settings.demo:
        raise DomainError(
            "DEMO_CALENDAR_ONLY",
            "Demo runtimes cannot deliver to a live Calendar, even when live sync is enabled.",
            409,
        )
    if not live_sync_ready():
        raise DomainError(
            "CALENDAR_LIVE_DISABLED",
            "Live Calendar sync requires recorded acceptance and operator enablement; OAuth connection alone does not enable writes.",
            409,
        )
